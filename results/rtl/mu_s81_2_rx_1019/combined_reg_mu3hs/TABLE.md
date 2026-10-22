# MU3 host-plane combined regression pickup

Source: GEN mu3 `3158fce1e` plus CLOSED hslot/HWIN/memory/bench overlay `1e057b7bf`; Verilator 5.050. Existing nine legs launched 12:29 PT; no new simulations. Logs copied only for terminal legs.

| Leg | Verdict |
| --- | --- |
| lep_base | PASS (including expected mutant rejection) |
| lep_mut3 | PASS (including expected mutant rejection) |
| lep_mut2 | PASS (including expected mutant rejection) |
| lep_regr | PASS (including expected mutant rejection) |
| lep_nh | PASS (including expected mutant rejection) |
| hwin | LIVE; preserve existing job |
| host | PASS (including expected mutant rejection) |
| prog | PASS (including expected mutant rejection) |
| seqhost | LIVE; preserve existing job |

Live host: ot-epyc7; directory `/srv/opentallas-scratch/claude/refill-1225/S81REG/src_mu3_hs/out/<leg>`. HWIN currently testing bad-D cases; seqhost actual AR programme progressing past edge 1,196,060. Passing leaf regressions do not qualify full-token SU/MU.
