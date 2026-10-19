# MU3 host-plane combined regression pickup

Source: GEN mu3 `3158fce1e` plus CLOSED hslot/HWIN/memory/bench overlay `1e057b7bf`; Verilator 5.050. Existing nine legs launched 12:29 PT; no new simulations. Logs copied only for terminal legs.

| Leg | Verdict |
| --- | --- |
| lep_base | PASS (including expected mutant rejection) |
| lep_mut3 | PASS (including expected mutant rejection) |
| lep_mut2 | PASS (including expected mutant rejection) |
| lep_regr | PASS (including expected mutant rejection) |
| lep_nh | PASS (including expected mutant rejection) |
| hwin | PASS: MU_HWIN_GATE PASS, rc0; includes actual die-master lint |
| host | PASS (including expected mutant rejection) |
| prog | PASS (including expected mutant rejection) |
| seqhost | LIVE: core two positives/five faults/three mutants/lint expected; nested leaf regressions compiling |

HWIN eighth terminal collected from original ep7 unit `oth-ubuntu-4120652-1792438136`, exit zero. Seqhost original unit `oth-ubuntu-4120668-1792438136`/shell4120668 still runs at the same directory. Its own AR46-user/92-start and MTP11-user/22-start positives PASS with user0-identical, zero-latency-vs-plain and all KD tags. All five fault cases PASS; mutants1/2/5 fail their intended check; three changed-module lints clean. The original script now recursively runs `reg_host` then `reg_hwin`; no ninth terminal gate verdict yet. Preserve build objects. `seqhost_partial.log` is explicitly nonterminal; a fresh collector must replace it with final log only after SEQHOST_MU_GATE and LEG rc appear. No new simulation was launched by this pickup.

Selected runtime source SHA256 hashes and full seqhost source manifest are retained. `8e9b03d6`/`519dab74` earlier identifiers are Git blobs, not SHA256. Actual native clock/fanout/PG/contact/timing and hardened-parent source/geometry integration remain open. Passing host-plane legs cannot qualify full-token single-user/multi-user or authorize automatic GENmu4 bind/adoption. Original strict-positive token failures and source gaps remain preserved in b14d4cf879 and the independent strict terminal packet.
