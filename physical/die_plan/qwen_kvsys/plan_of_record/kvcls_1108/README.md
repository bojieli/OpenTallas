# kvcls_1108 (KV-TYPES-4, 2026-11-08): KV type class fixes as one plan event on main plan_c (md5 48fdd735)

Build (repo root):
  python3 -I tools/die_plan/ring_band_spread.py PD/plan_c.json PD/eW_sidecar.json OUT/<type>.plan.json OUT/<type>.rep.json --types <type>   (per type, in parallel)
  python3 -I tools/die_plan/ring_band_merge.py PD/plan_c.json OUT plan_c.c1.json report_c1.json
  python3 -I PD/kvcls_1108/event.py plan_c.c1.json plan_c.kvcls.json

C1 LANDING-RING-DENSITY: every landing ring >= 192 bits at ring_ff spread 7 (sizer steps down to legal), 30 types / 190 bands
in this first cut (report_c1.json); sys_SD/sys_SD_v1 excluded (band cannot grow in the 30-um E strip; TYPE-SAFE-1 channel/pin
class), kv3_io_ft excluded (counted). The remaining slow types (hgi_v3/v5-v8, hub_C/Ei/Wi/Wo, pv_v2..v7/v12) join when their
per-type runs finish.
C2 kv3_io_ft_v1: clock.ft_hop_lockup {types:[kv3_io_ft_v1]} + landing_status_reg true (PIN CYCLES 0 data, status fault +1).
Output plan md5: see plan_c.kvcls.md5 (fleet copy epyc4 /srv/opentallas-scratch3/claude/kv-types-4/ev/por/plan_c.json).
