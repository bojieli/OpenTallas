LP exact mapped-flop correspondence continuation, 2026-10-29 18:47 takeover

The four missing KEEP names are actual physical DFF renames. trace.json records
each cell, ports and source netlist hash. trace_renames.py reproduces the census;
a missing-QN-driver mutant exits1. This structural census is not formal proof.

hints.json proposes four gate-to-gold correspondences. The LEC tool must prove
them; no waiver, reset extension, RTL change or cycle change is introduced.
The official prior result remains KEEP FAIL (34012/34024 compare points,4 missing).

Saved-AIG diagnostic prove_renames.py reuses exact hunt-none64 source/gate AIGs
and the3509 previously proved relations as untrusted proposals. The first replay
omitted correspond()'s normalized array/alias namespace.108 profile keys dropped,
causing2610 compare failures; namespace_fail.json retains that HARNESS failure.
The corrected replay applies production normalization/alias/relayout transforms
before transfer_profile, then jointly re-proves all proposals and compares every
point. A first correction encountered an old helper API; failure directory kept.

Current run: intel2:/srv/opentallas-scratch2/claude/codex-s81-lp-1847/proof_v2
ot-run unit oth-ubuntu-2790330-1793325213,32GB/2threads. tool_identity.json pins
the exact runtime helper snapshot. The repository tool gained packed-vector
relayout protection during takeover; the snapshot includes that merged fix.
No LP PLACE/CTS/route is authorized by this diagnostic. An exactness PASS still
needs the official fresh kit gate before physical adoption.

18:59 result: corrected replay all3509+4 rename proposals jointly inductive,
zero dropped. KEEP3742/3742, zero missing. Compare34012/34024 remains12diff
(all endpoint fault/pv/pnak/ok copies). This closes the physical rename cause
but does not establish full exactness. The actual source uses same-edge p_take
copies ok_f,ok_f3,ok_f2; golden s2v was paired to f3 while gate retained another
copy. Successor proof_v3 adds two untrusted both-side copy relations and an
inverted-copy negative control. No RTL or cycle changes; current job running.
