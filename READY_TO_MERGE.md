HARD token successor is ready for source review and one admitted -cx route; no main merge requested.

Branch: codex/mtp-wfc-hard-20261009. Physical source: 2588ae8d7.
RTL: rtl/dsrom_sys/mtp/ot_dsrom_wfc_tok_r3.sv, HARD_READ defaults to 0; new dsfd_wfc_tok_hard wrapper selects 1.
Bench: rtl/dsrom_sys/mtp/tb/tb_mtp_rom_tok_hard.sv; tools/dsrom_wfc_token_hard_gate.py.
Model: tools/uarch_model.py: dsrom_wfc_token_hard_model (written before RTL/build).
Gate: EPYC1TB admitted 4 GB, exact 636 reads/376 hits/120 stale epochs/20 invalid high users/24 bubbles PASS; omitted-epoch mutant fails on read277. Full8-user/16-slot table, continuous II1. Failed frontend evidence retained.
Recipe: tools/closure_loop/jobs/mtp-wfc_tok-hard-2588ae8d7-tc-cx.json, plan tools/s81_ph/s81_ph_wfc_token_hard_plan.py; one162x151.2um master, no macro,60/25ps unchanged, TT>=0/FF>=0/DRC0 with SS sensitivity. No physical claim yet.
Cost: four responseedges, +3original/+2r3 cycles (2.5ns nominal1.2GHz). Request snapshot at bank-read E2; dependent reads fence DRAFT visibility. Fixed-response port has four in-flight slots and no response backpressure.
Integration remaining: match SOURCE prompt metadata and minimum SOURCE exact gate before adoption. V14 VMX READPIPE2/TXQ8 remains markov_route ownership; original WFC untouched.
Historical r3/tokpipe rc1 failures are superseded by existing8a/9f exact gates; current passing harness is retained.
