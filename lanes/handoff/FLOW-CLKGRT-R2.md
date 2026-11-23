# FLOW-CLKGRT-R2 handoff (Opus 5.5; successor of FLOW-CLKGRT-1121). CURRENT 2026-11-21 ~11:2x PST
Goal: clock nets keep near-CTS routes through congestion GRT. Work dir epyc8 /srv/opentallas-scratch2/claude/flow-clkgrt-1121
(h/ harness, out/ results); lane clone epyc10 same path /repo.

## Done
- main 6eeda31903 (predecessor): kit_wave.py private-spec --rt SHA.
- main e338085d61: clock-first GRT opt-in, gen env OT_GRT_CLOCK_FIRST=1 (tools/die_plan/grt_clock_first.tcl, gen_phys
  grt_clock_first_cfg/install, allow_congestion re-armed after the merge read_segments; test_grt_clock_first.py). Off = kit unchanged.

## A/B (KV hroot D25d a5 4_cts_pre_tt copy, 30 it; read from .seg via h/sta_seg.tcl + h/ff_seg.tcl, no re-route)
| arm | overflow | clock-net len vs clock-only | t9 spread | max ins | TT setup/hold | FF internal hold |
| nondr | 385 (10/4) | 46 nets >20um, max +148 | 266 | 655 | -644/-402 | -177, 759 viol |
| clkfirst (no reserve) | 336 (6/3) | +0 | 170 | 410 | -770/-331 | -87, 541 |
| hook (reserve) | 385 (8/3) | +4 um total | 170 | 409 | -624/-331 | -86, 542 |
| base | pending (it ~24/30 at 11:20) | | | | | |
- Remaining t9 170 ps is not a GRT detour (clock routes equal the clock-only route).
- Harness note: arm.tcl usage-report step died GRT-0116 on clkfirst/hook r1 (allow_congestion reset by read_segments); fixed in
  h/arm.tcl; hook r2 rerun = oth-ubuntu-2522200-1795285340 (log out/hook.log; r1 kept as hook_r1.log/.seg).

## Next
1. base done (waiter) -> summ.py out base; resaware same. Default-on only if hook/clkfirst overflow <= base and FF hold not worse.
   If clkfirst (no reservation) beats hook on overflow at equal clock, push OT_GRT_CLOCK_FIRST_RESERVE=0 as the recommended form.
2. Proof on FABLE-FIX-KV-HUB-R2 b1 kit (not generated yet; bind B2): A/B copy via private-spec --ab OT_GRT_CLOCK_FIRST=1 --rt e338085d6155.

## 11:5x PST update
- base 424 / t9 244 / ins 483 / TT -660,-474 / FF int -170,693; resaware 423 / 138 / 371 / -627,-305 / -79,476 (ORFS knob ENABLE_RESISTANCE_AWARE, kits set 0).
- hook r2 rerun: route OK (385), harness report died GRT-0116 again: global_route re-parses -allow_congestion on EVERY call, so
  set_allow_congestion before it is useless; harness now passes -allow_congestion on -end_incremental. Flow impact none: ORFS
  -end_incremental behaves the same with and without the hook.
- hook_ra arm (clock-first + -resistance_aware) running, waiter; result in out/hook_ra.log (re-report from out/hook_ra/*.seg via
  h/run_seg.sh + h/run_ffseg.sh if the report step dies). Combo in a kit = OT_GRT_CLOCK_FIRST=1 + ENABLE_RESISTANCE_AWARE=1.
- Real-kit A/B: private-spec qwen_kvsys kv3_hub_C --ab OT_GRT_CLOCK_FIRST=1, intel2 pid 72363 (log ~/tmp/clkgrt_hubC_ab.out),
  spec ~/coord/autopilot/private_specs/FLOW-CLKGRT-R2/qwen_kvsys_kv3_hub_C_1121113302; control wave kw-qwenkv-kv3hubC-1-76966.

## 13:0x PST update
- WINNER hook_ra = clock-first + resistance-aware: overflow 382 / t9 92 ps / max ins 331 / TT -609,-232 (TNS -27.5 ns vs base -23.5) /
  FF int -60, 332 viol. Pushed opt-in main 79210da191: OT_GRT_CLOCK_FIRST_RES_AWARE=1 (with OT_GRT_CLOCK_FIRST=1).
- hub_C private A/B failed at gen: rt a137 gen_phys needs kvd23_hubc_views/kv_cland_w549_ew_bf94f/provenance.json absent in D26 tree (tool skew).
- Real-kit A/B NOW: kv3_hg_v1p2 private-spec --ab OT_GRT_CLOCK_FIRST=1 (clock-first only; RES_AWARE not in this kit), run-item intel2 pid 2574938,
  log ~/tmp/clkgrt_hgv1p2_ab.out, kit epyc8 .../KV-D26/private/FLOW-CLKGRT-R2/kv3_hg_v1p2_1121123820/gen/kv3_hg_v1p2 (place 12:57 PST).
  Control = wave kw-qwenkv-kv3hgv1p2-3-87352. Re-arm: ot-wait --kit <kit> --host epyc8 --stage grt --poll 300.
  Compare from final 5_1_grt.odb: TT setup, FF hold, GRT overflow, clock tap spread. Then default switch (gen_phys default OT_GRT_CLOCK_FIRST=1)
  only if no worse; RES_AWARE default needs its own real-kit run (TNS rose on hroot).

## 11-22 03:xx PST -- DEFAULT SWITCHED
- main 8ba65785b1: gen_phys default OT_GRT_CLOCK_FIRST=1 (=0 opts out); RES_AWARE opt-in. Decision table in post 11-22 RESULT.
- hd_spn a5 3-way: epyc7 flow-clkgrt-1121/head_spn/out (base, hook_ra, Codex) + out_cf (base, plain hook, mine).
- hg_v1p2 private kits both ended exit 2 DPL-0033 (repair wire buffers, central channel; geometry). Harness base control on its CTS
  still running epyc8 out_hg (waiter): pre-repair overflow control vs 565,769 (cf) / 553,144 (combined). Informational only.
- Next: watch first new-gen kits (5_1_grt.log OT_GRT_CLOCK_FIRST lines, GRT runtime); revert to opt-in on any hook error class.

## 11-22 17:3x PST
- Watch 04:49-16:23: 9 default-on kits through GRT, 0 hook failures (S81 serdes/slice_station/col x3, KV io_cor_v1, tt_ctlm). Watch re-armed (scratchpad cf_poll.sh + cf_scan_host.sh on rtx-pro).
