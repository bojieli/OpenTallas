# HBM-CORES-KITS-20 (2026-10-29): why route-stage repair sees 13-24 slew violations and sign-off sees 1,477-7,496

Kits: RING `epyc2:/srv/opentallas-scratch2/claude/hbm-cores-kits-17/kits/ring_keep_eco/kit` (ot_hfd_coll_q2_hard_v8g__ring_ag),
bdring `epyc2:/srv/opentallas-scratch2/claude/hbm-cores-kits-18/bd/ot_hgi_sm_xload_cl2_bdring_0c99d1c898e0-_k18`.
Inputs adopted (not redone): KITS-19 per-pin slew dump (`epyc2 hbm-cores-kits-19/slew`), Codex cores_a violating-net dump
(`epyc2 codex-hbm-rcfix-1355/{ring,bd}_routes.json`).

## Same netlist, two parasitic models (CHECKED)

All numbers come from the same routed `6_final.odb` with the same TT libraries and SDC. The only difference between runs is the
parasitics: `estimate_parasitics -global_routing` with the kit `setRC_rcx.tcl`, which is what the route-stage `repair_design` uses, versus
`read_spef 6_final.spef` (RCX, `rcx_patterns.rules`), which is what sign-off uses. Running the GRT estimate on `5_1_grt.odb` instead gives
per-net values identical to running it on `6_final.odb` (bdring, 770/770 nets: same driver, same pin count, same slew), so no repair
between GRT and finish changed these nets. The scripts are `slew/p6.tcl` (MODE=grtfinal|spef, net wire/pin C from report_net),
`slew/wl.py` (routed length and via count from the ODB wires) and `slew/ana.py`.

| on the SPEF-violating nets | RING (160 nets / 1,473 pins) | bdring (770 nets / 7,370 pins) |
|---|---|---|
| GRT-estimate pins > 320 ps | 0 | 0 |
| wire C SPEF / GRT (p10/p50/p90) | 1.007 / 1.150 / 1.475 | 1.306 / 1.694 / 2.195 |
| pin C SPEF / GRT | 1.000 | 1.000 |
| slew SPEF / GRT, violating pins, median | 1.386 | 1.632 (all pins: 1.445) |
| SPEF wire C per routed um, fF (p50) | 0.172 | 0.207 |
| GRT wire C per routed um, fF (p50) | 0.147 | 0.121 |
| violating pins on nets with fanout > 24 | 1,232 (84 %, 33 nets) | 6,026 (82 %, 246 nets) |
| violating pins on nets with fanout > 64 | 1,005 (68 %, 21 nets, max fo 155) | 1,987 (27 %, 51 nets, max fo 98) |

The SPEF sees 1.15-1.7x more wire C than the GRT estimate on these nets. Pin C matches exactly. The per-layer `set_layer_rc` C in
`setRC_rcx.tcl` (M2-M5 0.098-0.168 fF/um) is the clock-arrival fit, and `set_layer_rc` has no per-class (signal) form. The file's own
FLOW-RC-1 note already records that the GRT signal-slew estimate is optimistic on dense, via-heavy nets, and that this is "handled by
the routed-RCX DRV gate + placement max-wire repair". The routed-RCX step is only a gate, though: no `repair_design` ever runs on the
actual SPEF.

## Root cause

1. **HBM kit generator (die-local).** `physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py` emits neither `SLEW_MARGIN`/`CAP_MARGIN`
   nor a fanout cap. The route-stage log runs a bare `repair_design -verbose`. The other three generators all use the shared core-flow
   DRV basis:
   - KV `gen_core_kit_kv.py`: `set_max_fanout 64` at PRE_RESIZE, PRE_CTS and PRE_GRT, plus `SLEW_MARGIN 20` / `CAP_MARGIN 20`;
     64 is the shared `signoff.py` FANOUT_MAX.
   - S81 and QC generators: `SLEW_MARGIN 20` / `CAP_MARGIN 20`.

   HBM therefore repairs against the optimistic estimate with zero guard band and leaves un-split placer buffers. Examples:
   BUFx10 driving 85-99 loads over about 260 um routed with about 450 vias. These nets carry 68-84 % of the RING violations.
2. **Shared flow (FLOW).** No step repairs on the actual SPEF after routing, so whatever the GRT estimate misses reaches sign-off.

Estimate before build (GRT-estimate pins over the margin-reduced limit, out of the SPEF-violating pins). These come from the p3 per-pin
dumps and are an analytic proxy (UNCHECKED as repair outcomes):

| SLEW_MARGIN | RING | bdring |
|---|---|---|
| 20 | 737 / 1,473 | 1,623 / 7,370 |
| 30 | 1,270 / 1,473 | 4,159 / 7,370 |
| 40 | 1,449 / 1,473 (but 31,811 pins flagged) | 6,506 / 7,370 |

A blanket margin alone cannot close bdring without heavy over-buffering. The fanout cap removes the long high-fanout trees.

## Build test (launched 14:2x, about 65 min each, epyc2 via ot-run)

Copies of bdring _k18 differ only in the DRV basis (`max_fanout.tcl` sourced at PRE_RESIZE and at PRE_GRT via core_grt_pre.tcl):
- `hbm-cores-kits-20/bd/bdring_k20va`: fanout 64 plus SLEW/CAP margin 20 (the exact KV basis). Unit oth-ubuntu-1301360-1793308746.
- `hbm-cores-kits-20/bd/bdring_k20vb`: fanout 64 plus SLEW/CAP margin 30. Unit oth-ubuntu-1301796-1793308747.

Collect: `signoff/signoff.json` drv slew TT/FF against the _k18 baseline (7,496 / 6,501), plus setup_tt (_k18: -22.43), hold_ff and
insertion.

# qwdec_v1 post-CTS hold -28.98 ps / 2,736 r2r (input: Codex KITS12/14/18 diagnosis, related skew 41.64 ps, tree-wide)

Census by endpoint class (KITS-19 `epyc2 hbm-cores-kits-19/qwhold/census.tsv`, FF, 4_cts.odb, CHECKED): every failing path is
zero-logic flop->INV->flop (4 points). The classes are u_dec.value_pipe stage->stage (914, worst -29.0), aq/bq g_line.line shift
lines (829 + 386), and aq g*_sig stages (about 330). F4 (`f4_chain_leaf.tcl`, which puts chain launch and capture on one leaf) logged
`pairs 27592 moved 3411 skipped 14581 far 8474`. A read-only re-run of its chain walk on 4_cts.odb (`qwdec/f4_probe.tcl`) puts
2,717 of the 2,736 failing endpoints on F4 chains. 1,319 of them are on chains longer than OT_F4_MAX = 16, which F4 skips outright.
The other 1,398 are on short chains that F4 rejected as far (more than 20 um from the head leaf) or because the leaf was full.

Structural variant: an opt-in `OT_F4_SEG` in f4_chain_leaf.tcl (`qwdec/f4_seg.tcl`, default 0 = unchanged). It cuts long chains
into segments of 8 flops, each segment on the leaf of its own head, so only every 8th pair crosses leaves.
Estimate: up to about 1,300 of the 2,736 endpoints are removed, which brings the count under the 2,000-endpoint post-CTS gate; the
rest are left to the GRT measured-arrival hold repair (UNCHECKED).
- `epyc2 hbm-cores-kits-20/qw/qwdec_k20qa`: OT_F4_SEG 8. Unit oth-ubuntu-1367736-1793309013.
- `qwdec_k20qb`: OT_F4_SEG 8 plus OT_F4_MAX_UM 30. Unit oth-ubuntu-1368473-1793309014.

Collect: the `OT_F4` / `OT_F4_SEG` lines in 4_1_cts.log, then hold_gate.log (post-CTS FF WNS and endpoints), then sign-off.
