import json, os, pathlib, re, tempfile, unittest
from datetime import date

from axisbridge import config, claims, routing, scarcity, templates, taxonomies
from axisbridge import outreach_engine as oe
from axisbridge import inbox_monitor as im
from axisbridge import lead_engine as le

ADDR = "Axisbridge Medical Staffing, 71-75 Shelton Street, London WC2H 9JQ"


def _lead(**kw):
    base = dict(lead_id="k1", practice_name="Cypress Counseling", city="Austin",
                state_code="TX", state="Texas", credential="LCSW", clinician_count=3,
                payer="Blue Cross Blue Shield of Texas", denial_reason="90837 downcoded to 90834",
                contact_email="office@cypress.example", email_verified=True,
                entity_type="org", enumeration_months=24, first_name="Dana")
    base.update(kw)
    return base


class Exclusions(unittest.TestCase):
    def test_icp_exclusions_match(self):
        for name in ["Tarrant County LMHA", "Gateway Community Service Board",
                     "DBHDD Region 3", "NAMI Georgia", "Harris Center Community Mental Health",
                     "Broward County Health District", "St. Mary's Hospital Behavioral"]:
            self.assertTrue(le.EXCLUDE_RE.search(name), name)

    def test_private_practices_not_excluded(self):
        for name in ["Cypress Counseling PLLC", "Dana Whitfield LCSW",
                     "Blue Oak Psychiatry", "Peachtree Family Therapy"]:
            self.assertIsNone(le.EXCLUDE_RE.search(name), name)

    def test_facility_taxonomies_excluded(self):
        rec = {"taxonomies": [{"code": "261QM0801X"}]}
        self.assertEqual(le._matching_taxonomy(rec), "EXCLUDED")

    def test_facility_code_wins_over_a_wanted_code(self):
        rec = {"taxonomies": [{"code": "261QM0801X"}, {"code": "1041C0700X"}]}
        self.assertEqual(le._matching_taxonomy(rec), "EXCLUDED")


class Clustering(unittest.TestCase):
    def _rec(self, npi, name, addr1="100 Main St", enum="2023-01-15", code="1041C0700X", org=True):
        return {"number": npi, "enumeration_type": "NPI-2" if org else "NPI-1",
                "basic": {"organization_name": name if org else None,
                          "first_name": "Dana", "last_name": "Whitfield",
                          "enumeration_date": enum},
                "taxonomies": [{"code": code}],
                "addresses": [{"address_purpose": "LOCATION", "address_1": addr1,
                               "city": "AUSTIN", "state": "TX", "postal_code": "787011234",
                               "telephone_number": "512-555-0100"}]}

    def test_colocated_npis_collapse_to_one_lead(self):
        recs = [self._rec("1", "Cypress Counseling PLLC"),
                self._rec("2", "Cypress Counseling PLLC"),
                self._rec("3", "Cypress Counseling PLLC", addr1="100 Main Street")]
        leads = le.cluster(recs)
        self.assertEqual(len(leads), 2, "address_1 normalisation is literal; 'St' != 'Street'")
        big = max(leads, key=lambda l: l["clinician_count"])
        self.assertEqual(big["clinician_count"], 2)
        self.assertEqual(big["entity_type"], "org")

    def test_practice_over_ten_clinicians_dropped(self):
        recs = [self._rec(str(i), "Big Group") for i in range(11)]
        self.assertEqual(le.cluster(recs), [])

    def test_lmha_named_record_dropped(self):
        self.assertEqual(le.cluster([self._rec("9", "Tarrant County LMHA")]), [])

    def test_lead_carries_source_and_timestamp(self):
        lead = le.cluster([self._rec("1", "Cypress Counseling PLLC")])[0]
        self.assertIn("npiregistry", lead["source_url"])
        self.assertTrue(lead["retrieved_at"].endswith("Z"))
        self.assertEqual(lead["source_dataset"], "nppes")
        self.assertEqual(lead["denial_reason"], "90837 downcoded to 90834")


class Routing(unittest.TestCase):
    def test_all_six_branches(self):
        cases = [
            (_lead(has_open_billing_job_posting=True), "SEQUENCE_4"),
            (_lead(prior_sequence="SEQUENCE_1", ever_replied=False, days_since_sequence_ended=120), "SEQUENCE_6"),
            (_lead(entity_type="org", clinician_count=4), "SEQUENCE_5"),
            (_lead(entity_type="individual", clinician_count=1, enumeration_months=12), "SEQUENCE_2"),
            (_lead(entity_type="individual", clinician_count=1, enumeration_months=24), "SEQUENCE_1"),
            (_lead(entity_type="individual", clinician_count=1, enumeration_months=60), "SEQUENCE_3"),
        ]
        for lead, want in cases:
            self.assertEqual(routing.assign_sequence(lead)[0], want, lead)

    def test_premium_specialty_overrides_the_36_month_band(self):
        lead = _lead(entity_type="individual", clinician_count=1, enumeration_months=90, credential="PMHNP")
        self.assertEqual(routing.assign_sequence(lead)[0], "SEQUENCE_1")

    def test_job_posting_trigger_beats_everything(self):
        lead = _lead(has_open_billing_job_posting=True, entity_type="org", clinician_count=6,
                     enumeration_months=12)
        self.assertEqual(routing.assign_sequence(lead)[0], "SEQUENCE_4")


class TemplateIntegrity(unittest.TestCase):
    def test_no_template_contains_a_price_or_a_booking_link(self):
        for name, steps in templates.SEQUENCES.items():
            for s in steps:
                low = s.body.lower()
                for tok in ["$2,400", "$1,900", "$7,200", "$1,500", "$93,900",
                            "calendly", "book a call", "schedule a call", "free trial", "discount"]:
                    self.assertNotIn(tok.lower(), low, f"{name}.{s.step} contains {tok!r}")

    def test_abdikarim_never_named_in_outreach(self):
        for name, steps in templates.SEQUENCES.items():
            for s in steps:
                self.assertNotIn("abdikarim", s.body.lower(), f"{name}.{s.step}")

    def test_only_step_one_carries_a_subject(self):
        for name, steps in templates.SEQUENCES.items():
            for s in steps:
                if s.step == 1:
                    self.assertTrue(s.subject, f"{name}.1 needs a subject")
                else:
                    self.assertIsNone(s.subject, f"{name}.{s.step} must reply in-thread")
                    self.assertTrue(s.reply_in_thread)

    def test_every_variable_used_is_one_the_engine_can_supply(self):
        known = set(oe.variables_for(_lead()))
        for name, steps in templates.SEQUENCES.items():
            for s in steps:
                for v in oe.VAR_RE.findall(s.body + (s.subject or "")):
                    self.assertIn(v, known, f"{name}.{s.step} uses unknown {{{{{v}}}}}")

    def test_clinician_count_only_appears_in_sequence_5(self):
        for name, steps in templates.SEQUENCES.items():
            for s in steps:
                if "{{clinician_count}}" in s.body + (s.subject or ""):
                    self.assertEqual(name, "SEQUENCE_5", f"{name}.{s.step}")

    def test_reply_c_d_e_are_absent_not_invented(self):
        self.assertNotIn("REPLY_C", templates.REPLIES)
        self.assertEqual(set(templates.INCOMPLETE_REPLIES), {"REPLY_C", "REPLY_D", "REPLY_E"})


class Rendering(unittest.TestCase):
    def setUp(self):
        os.environ[config.FOOTER_ADDRESS_ENV] = ADDR
        self._sub = claims.load()
        for c in self._sub.values():
            c["substantiated"] = True
        scarcity.LEDGER = pathlib.Path(tempfile.mkdtemp()) / "slots.json"

    def tearDown(self):
        os.environ.pop(config.FOOTER_ADDRESS_ENV, None)

    def test_footer_refused_without_a_real_postal_address(self):
        os.environ.pop(config.FOOTER_ADDRESS_ENV, None)
        with self.assertRaises(oe.RenderRefused) as cm:
            oe.footer()
        self.assertIn("CAN-SPAM", str(cm.exception))

    def test_first_name_falls_back_to_there(self):
        self.assertEqual(oe.variables_for(_lead(first_name=None))["first_name"], "there")

    def test_other_empty_variables_refuse_rather_than_invent(self):
        with self.assertRaises(oe.RenderRefused) as cm:
            oe.substitute("Hi {{first_name}} at {{practice_name}}", oe.variables_for(_lead(practice_name="")))
        self.assertIn("practice_name", str(cm.exception))

    def test_rendered_email_carries_footer_and_optout(self):
        art = oe.render(_lead(), "SEQUENCE_5", templates.SEQUENCE_5[0], register=self._sub)
        self.assertTrue(art["body"].endswith(f"{ADDR}\n{config.FOOTER_OPTOUT}"))
        self.assertIn("Reply STOP to opt out.", art["body"])
        self.assertEqual(art["subject"], "3 clinicians at Cypress Counseling")
        self.assertEqual(art["status"], "AWAITING_SEND_GATE")

    def test_followup_steps_have_no_subject(self):
        art = oe.render(_lead(), "SEQUENCE_5", templates.SEQUENCE_5[1], register=self._sub)
        self.assertIsNone(art["subject"])
        self.assertTrue(art["reply_in_thread"])

    def test_guard_blocks_injected_price_and_booking_link(self):
        for bad in ["Our price is $2,400 a month.", "Book a call here.", "Ask for Abdikarim.",
                    "Two week trial available."]:
            with self.assertRaises(oe.RenderRefused, msg=bad):
                oe._guard("Hi there\n" + bad, "TEST.1")


class ClaimsGate(unittest.TestCase):
    def test_unsubstantiated_claim_blocks_its_step(self):
        with self.assertRaises(claims.UnsubstantiatedClaim) as cm:
            claims.assert_sendable("SEQUENCE_1.1")
        self.assertIn("most_practices_sitting_on_4_to_8k", str(cm.exception))
        self.assertIn("NOT rewritten", str(cm.exception))

    def test_scarcity_claim_is_the_only_substantiated_one_by_default(self):
        reg = claims.load()
        subs = [k for k, v in reg.items() if v.get("substantiated")]
        self.assertEqual(subs, ["audit_slots_four_per_state_month"])

    def test_render_refuses_a_blocked_step(self):
        os.environ[config.FOOTER_ADDRESS_ENV] = ADDR
        with self.assertRaises(claims.UnsubstantiatedClaim):
            oe.render(_lead(), "SEQUENCE_1", templates.SEQUENCE_1[0])
        os.environ.pop(config.FOOTER_ADDRESS_ENV, None)

    def test_steps_with_no_claims_are_sendable(self):
        for step_id in ["SEQUENCE_1.3", "SEQUENCE_2.1", "SEQUENCE_3.3", "SEQUENCE_5.1", "SEQUENCE_5.3"]:
            claims.assert_sendable(step_id)


class Scarcity(unittest.TestCase):
    def setUp(self):
        scarcity.LEDGER = pathlib.Path(tempfile.mkdtemp()) / "slots.json"

    def test_four_slots_then_refusal(self):
        for i in range(4):
            scarcity.claim("TX", f"lead{i}")
        self.assertEqual(scarcity.remaining("TX"), 0)
        with self.assertRaises(scarcity.SlotsExhausted) as cm:
            scarcity.claim("TX", "lead5")
        self.assertIn("would make that sentence false", str(cm.exception))

    def test_states_have_independent_caps(self):
        for i in range(4):
            scarcity.claim("TX", f"t{i}")
        self.assertEqual(scarcity.remaining("FL"), 4)

    def test_claiming_the_same_lead_twice_is_idempotent(self):
        scarcity.claim("GA", "x")
        scarcity.claim("GA", "x")
        self.assertEqual(scarcity.used("GA"), 1)


class InboxMonitor(unittest.TestCase):
    def setUp(self):
        d = pathlib.Path(tempfile.mkdtemp())
        im.SUPPRESSION, im.ESCALATIONS, im.STATUS_LOG = d / "sup.csv", d / "esc.jsonl", d / "log.jsonl"
        self._sub = claims.load()
        for c in self._sub.values():
            c["substantiated"] = True

    def test_stop_suppresses_immediately_and_never_escalates(self):
        out = im.handle({"lead_id": "k1", "from": "Doc@Example.com", "body": "STOP"})
        self.assertEqual(out["action"], "SUPPRESS")
        self.assertTrue(out["halt_sequence"])
        self.assertIn("doc@example.com", im.SUPPRESSION.read_text().lower())
        self.assertFalse(im.ESCALATIONS.exists(), "an opt-out must never wait in a queue")

    def test_stop_variants(self):
        for body in ["stop", "Please remove me from your list", "unsubscribe me",
                     "do not email me again", "opt me out"]:
            self.assertEqual(im.classify(body), "STOP", body)

    def test_reply_a_refused_when_the_baa_file_does_not_exist(self):
        os.environ.pop(im.BAA_PATH_ENV, None)
        out = im.handle({"lead_id": "k1", "from": "d@e.com", "body": "Yes please send the BAA"},
                        register=self._sub)
        self.assertEqual(out["action"], "ESCALATE")
        self.assertIn("attachment that is not there", out["reason"])

    def test_reply_a_sends_and_notifies_when_the_baa_exists(self):
        f = pathlib.Path(tempfile.mkdtemp()) / "baa.pdf"
        f.write_bytes(b"%PDF-1.4")
        os.environ[im.BAA_PATH_ENV] = str(f)
        try:
            out = im.handle({"lead_id": "k1", "from": "d@e.com", "body": "Yes, send it over"},
                            register=self._sub)
            self.assertEqual(out["action"], "SEND")
            self.assertEqual(out["status"], "AUDIT_AGREED")
            self.assertEqual(out["notify"], ["Abdikarim"])
            self.assertEqual(out["body"], templates.REPLY_A)
        finally:
            os.environ.pop(im.BAA_PATH_ENV, None)

    def test_hipaa_question_beats_a_yes_in_the_same_sentence(self):
        self.assertEqual(im.classify("yes but where is your team located?"), "REPLY_B")

    def test_reply_b_blocked_while_its_legal_claim_is_unsubstantiated(self):
        out = im.handle({"lead_id": "k1", "from": "d@e.com", "body": "Is this HIPAA compliant?"})
        self.assertEqual(out["action"], "ESCALATE")
        self.assertIn("legal assurance", out["reason"])

    def test_reply_c_escalates_because_the_template_was_truncated(self):
        out = im.handle({"lead_id": "k1", "from": "d@e.com", "body": "We already have a billing company"},
                        register=self._sub)
        self.assertEqual(out["action"], "ESCALATE")
        self.assertIn("truncated", out["reason"])

    def test_pricing_question_escalates_and_never_quotes_a_price(self):
        out = im.handle({"lead_id": "k1", "from": "d@e.com", "body": "How much do you charge?"},
                        register=self._sub)
        self.assertEqual(out["action"], "ESCALATE")
        self.assertIsNone(out["template"])

    def test_unmatched_halts_the_sequence(self):
        out = im.handle({"lead_id": "k1", "from": "d@e.com", "body": "Who is this?"}, register=self._sub)
        self.assertTrue(out["halt_sequence"])


class EmailVerification(unittest.TestCase):
    def test_syntax_failures_rejected_without_network(self):
        for bad in [None, "", "not-an-email", "a@b", "a@@b.com"]:
            ok, _ = le.verify_email(bad)
            self.assertFalse(ok, bad)

    def test_mx_lookup_against_a_domain_with_no_records(self):
        ok, why = le.verify_email("someone@example.invalid")
        self.assertFalse(ok)
        self.assertIn("MX", why)


class TaxonomySet(unittest.TestCase):
    def test_shortfall_is_reported_not_hidden(self):
        w = taxonomies.shortfall_warning()
        self.assertIsNotNone(w, "the set is a reconstruction and must say so until replaced")
        self.assertIn("RECONSTRUCTION", w)

    def test_all_six_categories_present(self):
        for c in taxonomies.CATEGORIES:
            self.assertTrue(taxonomies.by_category(c), c)

    def test_codes_are_well_formed_and_unique(self):
        codes = [t.code for t in taxonomies.CODES]
        self.assertEqual(len(codes), len(set(codes)))
        for c in codes:
            self.assertRegex(c, r"^\d{6}[A-Z0-9]{4}X$|^\d{3}[A-Z]{1,2}\d{5}X$|^\d{9}X$|^[0-9A-Z]{10}$")


if __name__ == "__main__":
    unittest.main(verbosity=1)


class BookingGuardBoundaries(unittest.TestCase):
    """Regression: 'cal.com' matched inside 'axisbridgemedical.com' and refused every email."""

    def test_own_domain_does_not_trip_the_booking_guard(self):
        for ok in ["https://www.axisbridgemedical.com/privacy",
                   "https://axisbridgemedical.com",
                   "see medical.com/notes", "typical.company/x"]:
            oe._guard("Hi there\n" + ok, "TEST.1")     # must not raise

    def test_real_booking_links_still_blocked(self):
        for bad in ["https://calendly.com/anthony", "https://cal.com/anthony",
                    "https://meetings.hubspot.com/x", "book a call with me",
                    "schedule a demo", "pick a time here"]:
            with self.assertRaises(oe.RenderRefused, msg=bad):
                oe._guard("Hi there\n" + bad, "TEST.1")

    def test_privacy_url_appears_in_the_footer_when_set(self):
        os.environ[config.FOOTER_ADDRESS_ENV] = ADDR
        os.environ[config.FOOTER_PRIVACY_ENV] = "https://www.axisbridgemedical.com/privacy"
        try:
            f = oe.footer()
            self.assertIn("Privacy notice: https://www.axisbridgemedical.com/privacy", f)
            self.assertTrue(f.rstrip().endswith(config.FOOTER_OPTOUT))
        finally:
            os.environ.pop(config.FOOTER_ADDRESS_ENV, None)
            os.environ.pop(config.FOOTER_PRIVACY_ENV, None)

    def test_footer_omits_privacy_line_when_unset_so_the_gate_catches_it(self):
        os.environ[config.FOOTER_ADDRESS_ENV] = ADDR
        os.environ.pop(config.FOOTER_PRIVACY_ENV, None)
        try:
            self.assertNotIn("Privacy notice", oe.footer())
        finally:
            os.environ.pop(config.FOOTER_ADDRESS_ENV, None)
