# S81-GOTAG-SETUP-1115 (11-15 14:25) DONE: diagnosis posted, no jobs running
Kit: epyc10 /srv/opentallas-scratch2/claude/s81-seam-rst-1115/pilot/pg (4_cts.odb). My STA scripts + outputs: epyc10 /srv/opentallas-scratch2/claude/s81-gotag-setup-1115/ (p1/p3/p4.tcl, *.out; run.sh = Fable's docker openroad, read-only).
Finding: not go_tag specific, not an artefact. It is the IFN half-cycle input face (RTL param IFN=1, RF-J DIE-S81-52 11-03) of all 8 element cores, fed by grid-tap macros (cfg7_seq s*, qbank_S bs*).
Open: fix = sender-to-element tap affinity (+ measured tap window); needs DIE-S81-92 / S81-TAPROWS decision.
## 14:42 pilot A result (r160): sender cores on element early core tap = ZERO-SUM, does not close. h9a/h10a on epyc10 s81-gotag-setup-1115/ (4_cts.odb, p5*.out). h9a GRT stopped (ot-heavy-stop). Next: NEEDS-FABLE on chain budget.
