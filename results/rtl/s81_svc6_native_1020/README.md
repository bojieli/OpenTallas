hgrp native pre-gate audit

Existing mapped hgrp_ns synthesis source snapshot500137c72ed8d5bd6216b74a47f02434ac30b492d5c49d64c9ee73f406da5b64. Netlist SHA256640f4675ac37c86528842a007c2ec399f4d370c03546260b5001e47351d40fd6 (remote ep8 ref_gate/s81svc_attn_hgrp_ns-20261019-212709). Existing textbook.json already shows reset4269, d1_bank[0]1538 and per-head u_rc.q[12]1042/1041 loads. These violate the binding32-load rule. Gate clock spread25.0/23.2 and TT placement setup79.7ps/hold12.6ps do not admit this source. No submission.

Stricter diagnostic uses existing mapped netlist (no new synthesis), current textbook_lint.py with hf_report/hf_max/hf_port_refuse/hf_reset_refuse/hf_refuse all32. Running on fleet off drained ep8; result pending. Changes to tool thresholds here are command-line audit parameters, not changes to gate defaults.

Structural follow-up: replicate group D1 bank controls and per-head load-mode controls as kept copies at bounded consumer chunks; replace oversized stationary storage/skew rings with SRAM-backed native implementation; distribute equal-age reset leaves<=32. Every changed candidate needs bit-exact bench, static cycle price, and actual mapped census before any layout gate.

Terminal strict census: 3,196 drivers exceed32 loads. Most are inside the head datapath; see summary.json family counts and native32.json full refusal list. The runner exited0 in warn mode, but the binding audit verdict is FAIL. Root control replication alone is insufficient.
