# Independent rerun of the original MTP campaigns 14/15/19/20 (mtp-lead, 2026-10-09)

Source: main merge 628000701 (codex/mtp-numerical-repair bfd8bcf8b merged; `ROLLBACK_RING_DYN` default 1). Host ot-epyc4,
Verilator 5.050. Fixtures regenerated here (`mtp_exact_wavefront2.py prepare --order deep --rollback-ring-dyn`) from the reduced
V4.1 checkpoint (sha in hashes.txt) and the golden token sequence `gold.json`; stage2_cfg.svh and every cfg_stage2_deep file are
byte-identical to Codex's fixtures for L14 and L19.

| Campaign | Run | Result | Cycles |
|---|---|---|---|
| 14 | L14 deep order (MR-5), WFC wave 1, explicit ROLLBACK_RING_DYN(1) | PASS, out 0 / state 0 mismatches | 428,093 |
| 14 (default) | same, no parameter override (core default) | PASS | 428,093 |
| 15 | L14, wf wave 0 negative | FAIL as required (1 protocol fault, payload/state exact) | 428,088 |
| 19 | L19 deep order, WFC wave 1 | PASS | 237,482 |
| 20 | L19, wf wave 0 negative | FAIL as required | 237,477 |

All four match Codex's receipts (results/rtl/mtp_ring_dyn_20261009/four_campaign_gate.json) cycle for cycle. Decision recorded in
results/arch/mtp_status_20261009/STATUS.md: the ring address stays in RTL (the program cannot express pos mod 8).
Scope: reduced 2-stage vehicle; not the native full-shape program (ShapeLayout does not emit ring-8 yet).
