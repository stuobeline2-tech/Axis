# FIXTURES — SYNTHETIC, NOT REAL DATA

Everything in this directory is invented for testing and is labelled as such. It exists here,
under `test/`, and **never** under `data/` or `metrics/`, which hold real values or nothing (§2.1).

`sample-denials.csv` is a made-up claims export used to prove the pipeline runs. No practice, payer
relationship, patient or dollar figure in it is real. `Payer A`/`Payer B` are deliberately not the
names of real insurers, so the file cannot be mistaken for a real export at a glance.
