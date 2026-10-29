# Fresh NL gate LEC takeover

Source base d7eb2d8813 (QC-A0-KITS-11); fresh mapped parent gate from
intel1 codex-qc-nl-lec-1029/reset_newgate, built 02:00 PDT. Sources untouched.

Transferred assumptions are not accepted without proof. Diagnostic `refresh.py`
rechecks all assumptions from predecessor model, rejects 57 refuted gold KV
address-prep relations and proves remaining 12,513 jointly. Actual complete
comparison then proves 31,580 / 31,685, with 105 address-prep differences.
This is **FAIL**, not a complete equivalence claim.

`fresh.py` regenerates all correspondence from the actual fresh gold/gate AIGs,
then proves seven existing guarded-zero KV nb_t relations and the full miter.
Job intel1 unit oth-ubuntu-1934993-1793267664, run directory
/srv/opentallas-scratch2/claude/codex-qc-nl-lec-0251/fresh.

No RTL, clock, constraints or latency changes. No P&R permitted on this diagnostic.
