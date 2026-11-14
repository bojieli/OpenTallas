# TL-QCTAIL1 (2026-11-14 05:13 PST)
Target: qfd_dv_s8_station_tail1 hard core (162x162, 5 SRAM, pins cores/st_a/qfd_dv_s8_station_tail1_pins.json from zz_s29_qc103_s2.json in epyc9 wt/qc-s29-tree2). Kits via gen_core_kit_qc (scratchpad mk_tail1.py, mk_tail1b.py; base on TL-QCSTAV2 mk_region.py, no wrapper, default params). Form A util 0.5 (rk), form B util 0.4 (rkb). Dirs /srv/opentallas-scratch2/claude/tl-qctail1/{rk,rkb}/qfd_dv_s8_station_tail1/kits/qfd_dv_s8_station_tail1_synth0 (epyc9,epyc7,epyc10,intel1,epyc2). Launched via ot-run from epyc7 (pids 299876/299878), both admitted on intel1. Logs epyc7 tl-qctail1/logs/{rk,rkb}.log.
NEXT: on pass -> AUTO-RESIGN row, ask KIT-OPS-3 for prov_view_sources, RESULT.
Form C: epyc9 rkb copy, client epyc7 pid 1876081, log epyc7 tl-qctail1/logs/rkb_epyc9.log (11-14 06:14).
11-14 06:51: forms rk/rkb FAIL face_guard (flt_* unregistered). New forms rkw (epyc9, util .5, client epyc7 pid 701752) and rkwb (epyc10, util .4, pid 701754) with pin-register wrapper; logs epyc7 tl-qctail1/logs/rkw.log rkwb.log. Old epyc9 form killed.
11-14 10:18: rkw routed: DRC0 setup+17.9 hold-1.47(3 int). ECO1 running epyc2 eco_rkw (pid 2810283 epyc7). rkwb util.4 parallel form in route.
11-14 10:22: ECO now on ko4copy (ko4-eco + cap_estimate.py) eco_rkw3, queued epyc2, pid 103243 epyc7. rkwb parallel.
11-14 10:32: rkw ECO moved to intel1 (pid 3472648 epyc7); rkwb ECO epyc2 (pid 2667225). rkwb hold: 20 port (adv) + 3 internal -3.91.
