# Uncontended ot-epyc1tb chain logs (chain.rc=0; collected 2026-10-04, logs only, tool sha256 95462beb)
- Every single-stage job PASS in all three plans (base 39, AR256 37, AR256-poison 37; 113 exit.json).
- base: composed 171,090 cycles == reference, pairs L18/head PASS, but verify rc=1 (entry_state_composition_ok=false, composed_full_token_exact=false).
- AR256: 144,522 cycles; verify rc=1 without poison; poison plan rc=1 (chain_covers_every_stage=false); final verdict with poison rc=0, composed_full_token_exact=true.
- The base/AR256 rc=1 is under diagnosis by another agent; nothing here re-interprets it. Per-job runs/ (85 MB) remain on ot-epyc1tb:/srv/opentallas-scratch/claude/layer-parallel-sim/runs.
