# HBM core continuation 2026-10-30

Source branch `codex/hbm-cores-1030`, base `97602b9dda5`.

- Kit generator native bus/bit rows normalized with shared canonical helper: `f2f1dbde7`. Five existing focused pin checks PASS on fleet Python 3.14. Local Python 3.10 cannot parse an existing f-string; no source defect inferred.
- Ring d31t k26c **NOT SIGNED**: TT -10.34 ps /25 endpoints, FF +3.58 ps, slew227 TT/153 FF, DRC0/antenna0, related-pair40.93/37.71 ps, face2224 PASS. Critical `pin_p[1][278] -> rr_d[47]` traverses BUFx2 trees with54/64 fanout, contributing214 ps. Data-drive fixes from4CTS: slew margin20->50 with fanout64 or32; no RTL/clock/boundary/cycle change.
- BD k26s **FAIL**: three DPL overlaps after hold repair +10 ps. Resized clock-sink flops were locked FIRM by old GRT-CLK-LOCK. Clone changes only that block to main FLOW6 overlap-aware lock; original failure retained.
- Query d32q `8685b722456c` GEN PASS, preflight PASS0. N593 pins now span142um at4.2/um; E7.3/um remains a budget WARN (COORD10-27). Own plan/context personally viewed; independent GEOM concurs PASS-COND PLACE+GRT only. Actual review required before CTS.
- Selector A/B: independent current geometry FAIL, r2r906.88/9091 captures vs823.66/5496. Gq2 fill and its buffer on opposite corners; quarter locality plus same-edge control copies under development by `selector` helper. No route release.
- SU lane_exp0_id old440.64x207.36 GEOM FAIL: aspect2.125, reset pin distance165.83, r2r580.01/370 captures. Parent owns414.72 outline/center-entry/reset event. Existing6 SRAMs94.824x41.064 atx64.8/172.8/280.8,y53.724/118.812 fit newoutline unchanged.
- Collar native name crash fixed; d32q then exposes separate extra c_done__W input. Parent bind trace confirms W pin is selected actual c_done; parent removing historical N copy in same event. No alias invented.

## Live own jobs

All use ot-run; host paths are under `/srv/opentallas-scratch2/claude/codex-hbm-cores-1030`.

| Host | Dir | Unit | Check |
|---|---|---|---|
| epyc2 | bd_lockfix | oth-ubuntu-1235586-1793357018 | run_codex1030.log/.rc |
| epyc2 | ring_slew50 | oth-ubuntu-1301524-1793357189 | run_codex1030.log/.rc |
| epyc2 | ring_fan32 | oth-ubuntu-1303322-1793357190 | run_codex1030.log/.rc |
| intel1 | query | oth-ubuntu-2607577-1793357272 | place_geom.log/.rc and kits/*/rev |

Inherited jobs remain untouched: GQL068dba/7e7e2a DRT, HCOL1 after hold+3.45, selectorA/B diagnosticGRT, opstoreA/B, topkLEC, HBM1080 placement, QCOREk26q/HCOLk26q.
