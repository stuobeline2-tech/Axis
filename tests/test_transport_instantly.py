import json, os, pathlib, tempfile, unittest
from unittest.mock import MagicMock, patch

from axisbridge import transport_instantly as ti


def _artifact(**kw):
    base = dict(to="office@cypress.example", prospect_id="SYNTH-cypress", org_name="Cypress Counseling",
                sequence="SEQUENCE_5", step=1, step_id="SEQUENCE_5.1", subject="3 clinicians at Cypress",
                reply_in_thread=False, body="Hi Dana,\n\nBody text.\n\nAnthony", status="AWAITING_SEND_GATE")
    base.update(kw)
    return base


def _write(outbox, artifact, name=None):
    outbox.mkdir(parents=True, exist_ok=True)
    (outbox / (name or f"{artifact['prospect_id']}-{artifact['sequence']}-{artifact['step']}.json")).write_text(json.dumps(artifact))


class ConnectGate(unittest.TestCase):
    def test_missing_api_key_raises_connect_gate_error(self):
        os.environ.pop(ti.API_KEY_ENV, None)
        with self.assertRaises(ti.ConnectGateError) as cm:
            ti._api_key()
        self.assertIn("Never paste it into a chat", str(cm.exception))

    def test_missing_eaccount_raises_connect_gate_error(self):
        os.environ.pop("AXISBRIDGE_INSTANTLY_EACCOUNT", None)
        with self.assertRaises(ti.ConnectGateError):
            ti.resolve_eaccount("SEQUENCE_1")

    def test_sequence_6_uses_its_own_mailbox_env_var(self):
        os.environ["AXISBRIDGE_INSTANTLY_EACCOUNT"] = "anthony@axisbridgemedical.com"
        os.environ["AXISBRIDGE_INSTANTLY_EACCOUNT_SEQ6"] = "anthony@axisbridge-followup.com"
        try:
            self.assertEqual(ti.resolve_eaccount("SEQUENCE_1"), "anthony@axisbridgemedical.com")
            self.assertEqual(ti.resolve_eaccount("SEQUENCE_6"), "anthony@axisbridge-followup.com")
        finally:
            for k in ["AXISBRIDGE_INSTANTLY_EACCOUNT", "AXISBRIDGE_INSTANTLY_EACCOUNT_SEQ6"]:
                os.environ.pop(k, None)


class DryRun(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.outbox = self.d / "outbox"
        ti.THREAD_STORE = self.d / "threads.json"
        ti.SEND_LOG = self.d / "send_log.jsonl"
        ti.LEDGER = self.d / "ledger.csv"
        os.environ["AXISBRIDGE_INSTANTLY_EACCOUNT"] = "anthony@axisbridgemedical.com"

    def tearDown(self):
        os.environ.pop("AXISBRIDGE_INSTANTLY_EACCOUNT", None)

    def test_dry_run_makes_zero_network_calls_and_writes_no_ledger(self):
        _write(self.outbox, _artifact())
        with patch.object(ti.InstantlyClient, "__init__", side_effect=AssertionError("must not construct a client in dry run")):
            res = ti.send_batch(self.outbox, dry_run=True)
        self.assertEqual(len(res["sent"]), 1)
        self.assertFalse(ti.LEDGER.exists())
        self.assertFalse(ti.THREAD_STORE.exists())

    def test_dry_run_does_not_move_files_out_of_outbox(self):
        _write(self.outbox, _artifact())
        ti.send_batch(self.outbox, dry_run=True)
        self.assertEqual(len(list(self.outbox.glob("*.json"))), 1)


class LiveSendMocked(unittest.TestCase):
    """Never calls the real API. requests.Session.request is mocked at the transport boundary."""

    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.outbox = self.d / "outbox"
        ti.THREAD_STORE = self.d / "threads.json"
        ti.SEND_LOG = self.d / "send_log.jsonl"
        ti.LEDGER = self.d / "ledger.csv"
        os.environ[ti.API_KEY_ENV] = "test-key-not-real"
        os.environ["AXISBRIDGE_INSTANTLY_EACCOUNT"] = "anthony@axisbridgemedical.com"

    def tearDown(self):
        os.environ.pop(ti.API_KEY_ENV, None)
        os.environ.pop("AXISBRIDGE_INSTANTLY_EACCOUNT", None)

    def _mock_response(self, status=200, json_body=None):
        r = MagicMock()
        r.status_code = status
        r.ok = 200 <= status < 300
        r.content = b"{}" if json_body is not None else b""
        r.json.return_value = json_body or {}
        r.text = json.dumps(json_body) if json_body else ""
        return r

    def test_step1_sends_new_and_records_thread_ledger_and_moves_file(self):
        _write(self.outbox, _artifact())
        with patch("requests.Session.request", return_value=self._mock_response(200, {"id": "email-abc-123"})) as m:
            res = ti.send_batch(self.outbox, dry_run=False, skip_gate=True)
        self.assertEqual(res["sent"], [f"{'SYNTH-cypress'}-SEQUENCE_5-1.json"])
        self.assertEqual(m.call_args.kwargs["json"]["to_address"], "office@cypress.example")
        called_url = m.call_args.args[1]
        self.assertEqual(called_url, "https://api.instantly.ai/api/v2/emails")
        threads = json.loads(ti.THREAD_STORE.read_text())
        self.assertEqual(threads["SYNTH-cypress:SEQUENCE_5"]["email_id"], "email-abc-123")
        ledger = ti.LEDGER.read_text()
        self.assertIn("SYNTH-cypress", ledger)
        self.assertIn("contacted", ledger)
        self.assertEqual(list(self.outbox.glob("*.json")), [])
        self.assertTrue((self.outbox / "sent" / "SYNTH-cypress-SEQUENCE_5-1.json").exists())

    def test_followup_step_refuses_without_a_prior_thread(self):
        _write(self.outbox, _artifact(step=2, step_id="SEQUENCE_5.2", subject=None, reply_in_thread=True))
        with patch("requests.Session.request") as m:
            res = ti.send_batch(self.outbox, dry_run=False, skip_gate=True)
        m.assert_not_called()
        self.assertEqual(len(res["skipped"]), 1)
        self.assertIn("no prior thread", res["skipped"][0][1])
        self.assertFalse(ti.LEDGER.exists())

    def test_followup_step_replies_into_the_recorded_thread(self):
        ti.THREAD_STORE.parent.mkdir(parents=True, exist_ok=True)
        ti.THREAD_STORE.write_text(json.dumps({"SYNTH-cypress:SEQUENCE_5":
            {"email_id": "email-abc-123", "subject": "3 clinicians at Cypress", "eaccount": "anthony@axisbridgemedical.com"}}))
        _write(self.outbox, _artifact(step=2, step_id="SEQUENCE_5.2", subject=None, reply_in_thread=True))
        with patch("requests.Session.request", return_value=self._mock_response(200, {"id": "email-def-456"})) as m:
            res = ti.send_batch(self.outbox, dry_run=False, skip_gate=True)
        self.assertEqual(len(res["sent"]), 1)
        sent_payload = m.call_args.kwargs["json"]
        self.assertEqual(sent_payload["reply_to_uuid"], "email-abc-123")
        self.assertNotIn("to_address", sent_payload)

    def test_a_failed_send_is_logged_and_never_written_to_the_ledger(self):
        _write(self.outbox, _artifact())
        with patch("requests.Session.request", return_value=self._mock_response(400, {"error": "bad request"})):
            res = ti.send_batch(self.outbox, dry_run=False, skip_gate=True)
        self.assertEqual(len(res["failed"]), 1)
        self.assertFalse(ti.LEDGER.exists(), "a failed API call must never produce a ledger row")
        self.assertTrue((self.outbox / "SYNTH-cypress-SEQUENCE_5-1.json").exists(), "failed sends stay in outbox, not moved to sent/")

    def test_retries_on_429_then_succeeds(self):
        _write(self.outbox, _artifact())
        responses = [self._mock_response(429), self._mock_response(200, {"id": "email-x"})]
        with patch("requests.Session.request", side_effect=responses) as m, patch("time.sleep"):
            res = ti.send_batch(self.outbox, dry_run=False, skip_gate=True)
        self.assertEqual(m.call_count, 2)
        self.assertEqual(len(res["sent"]), 1)

    def test_gives_up_after_max_retries_and_logs_the_raw_body(self):
        _write(self.outbox, _artifact())
        with patch("requests.Session.request", return_value=self._mock_response(503, {"error": "down"})), patch("time.sleep"):
            res = ti.send_batch(self.outbox, dry_run=False, skip_gate=True)
        self.assertEqual(len(res["failed"]), 1)
        self.assertIn("503", res["failed"][0][1])

    def test_missing_eaccount_skips_without_any_network_call(self):
        os.environ.pop("AXISBRIDGE_INSTANTLY_EACCOUNT", None)
        _write(self.outbox, _artifact())
        with patch("requests.Session.request") as m:
            res = ti.send_batch(self.outbox, dry_run=False, skip_gate=True)
        m.assert_not_called()
        self.assertEqual(len(res["skipped"]), 1)


class VerifyConnectionMocked(unittest.TestCase):
    def setUp(self):
        os.environ[ti.API_KEY_ENV] = "test-key-not-real"

    def tearDown(self):
        os.environ.pop(ti.API_KEY_ENV, None)

    def test_verify_connection_lists_accounts(self):
        r = MagicMock(status_code=200, ok=True, content=b"{}",
                      json=MagicMock(return_value={"items": [{"email": "anthony@axisbridgemedical.com"}]}))
        with patch("requests.Session.request", return_value=r):
            out = ti.verify_connection()
        self.assertTrue(out["ok"])
        self.assertEqual(out["accounts"][0]["email"], "anthony@axisbridgemedical.com")

    def test_verify_connection_surfaces_the_real_error_body_on_failure(self):
        r = MagicMock(status_code=401, ok=False, text='{"error":"invalid api key"}')
        with patch("requests.Session.request", return_value=r):
            with self.assertRaises(ti.TransportError) as cm:
                ti.verify_connection()
        self.assertIn("invalid api key", str(cm.exception))


class HtmlRendering(unittest.TestCase):
    def test_html_is_escaped(self):
        html = ti._to_html("Hi <script>alert(1)</script>\n\nBody")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


class PresendReentry(unittest.TestCase):
    def test_a_real_send_reruns_the_js_presend_gate_and_refuses_on_failure(self):
        d = pathlib.Path(tempfile.mkdtemp())
        outbox = d / "outbox"; outbox.mkdir()
        with patch("subprocess.run") as m:
            m.return_value = MagicMock(returncode=1, stdout="FAIL check 3")
            with self.assertRaises(ti.TransportError):
                ti.run_presend_gate(outbox)
        m.assert_called_once()
        self.assertIn("node", m.call_args.args[0][0])
        self.assertIn("presend.mjs", m.call_args.args[0][1])


if __name__ == "__main__":
    unittest.main(verbosity=1)
