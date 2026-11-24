# KV-RCOLL-PHASE handoff (11-23 21:3x PST)
Job: check RCOLL 215 reset re-attachments vs phase/predecessor; name cause of A3f EMIT reset errors (kv3_hroot, kv3_io_ft_v1).
Done: census epyc11 /srv/opentallas-scratch2/claude/kv-rcoll-phase/rcoll_census.{tsv,json} (scripts census.py why.py solve.py xref.py there).
- 215 moves: depth same 215, predecessor same 0, tap same 0, kind differs 51; same-pred sibling in reach only 4; 0 touch raw-branch nodes.
- RCOLL absent from A3f/A3g (pre-RCOLL nodes 211/215).
- Cause of the 2 errors: stale landing_raw_branches / stored collector_tree after the A3 grow (io_ft_v1 solve 175 vs 173 relays, t15 D=rst_rl_58; hroot old t11 site is now t12 D=rst_rl_79). Fix = landing_remap anchor on 2 types (KV-ALLFIX).
Waiting: A3g strict bind EMIT (epyc10 grow/gate_A3g/bind1.log) to confirm.
