# qfd_tt_ctlm_dv_safe5c — QW-CTLM5 (LEAD3-QW 10-19): safe5 + core clock entry on the S face

PARALLEL variant of safe5 (regions). Only change: **ck_core N x194.5 -> S x216.333** (centre of the core pin band: tl[1087:0] + pw[74:0], tl[1087:544] / pw shifted +0.648 um) and **rst_n N -> S x350.901**, so every core pin flop sits in one S band beside its root, and the core root enters from the S neighbour that tl feeds (neighbour-matched boundary). Targets the hidden safe4 core pin-flop spread (TT 192 / FF 166 ps, N root 560 um from the S tl band). Die GEN must deliver ck_core on S.

Branch claude/qw-ctlm5-1019 (base claude/qw-f16ctlm-port-1019 e5e2d03d2 = CTLM4 d60ab0461 + F16WTN/CALR port).
Parallel fallback without placement regions: qfd_tt_ctlm_dv_safe5n (identical otherwise).

## What safe3/safe4 failed and why (classified 10-19 21:30-23:00)
1. **clock_rule "per-root measurement coverage differs from clock_ports"** (all four gates): NOT a kit declaration error.
   tools/closure_loop/ck_insertion.py aborted on `u_hr/ck_pm0` (h16c raw SRAM clock pin, landed_raw: its ETM has no arcs ->
   `missing unique active clock edge`, rule 609270c0a), so no GATE_CK_DOMAIN was produced. Fixed in the tool (this branch:
   arc-less hard-child clock pins are recorded `OT_MC_RAW_NOARC` and skipped; they stay judged by the landed body
   OT_LANDED RAW_PIN). Re-measured on the safe4 CTS database: ck_core boundary TT 844.8-1036.4 / FF 698.3-864.6 ps,
   ck_hr boundary TT 311.1-558.8 / FF 255.1-459.8 ps -> the hidden verdict is a **pin-flop spread FAIL** on both roots.
2. **wire_reach 85 stages / command_stage 612 um**: u_hr's outputs program_obs[75:0] / command_stage[5:0] leave h16c on its
   E face (x734.4, y57-78) and were pinned on the N face (x606-717): 520-612 um unregistered.
3. **cross_clock hr->core -158.1 ps** (u_lpl_5 = ss5): the hr root launches ~207 ps after core (ck_hr is co-timed with the
   h16c ck_head reference: source latency 491 + tree), plus a 346 ps buffered wire inside u_lpl_5_r, on the D2/K1
   single-cycle (no multicycle) window with the 210 ps inter-clock reserve.

## safe5 changes
| # | Change | Edges |
|---|--------|-------|
| a | program_obs + command_stage N -> **E face** M4 y56.08-71.82, beside u_hr's E outputs (reach ~45 um) | 0 |
| b | **D 4 / E = K = 2 landings + LANDING-CONTRACT L5 multicycle** (-setup 2 -hold 3 ring -> read, lp.py standard): window -2T + t_hold < dL < 2T - t_cq - t_setup absorbs the regional phase | +1 per landing: outputs +6, tl +3, kok/kwd/native_ret +6 |
| c | F16WTN / PRIVATE_CALR ports (claude/qw-f16ctlm-port-1019): f16_auth[82:0] / f16_obs[37:0] N x504-530 (land from hr), f16_st[16:0] / table_req[8:0] E y72-77 (u_thru); params 0 in this kit | 0 |
| d | pw lands from **core** (port_regions pw core) at S x333.8-349.8 right after tl: u_gi reads pw (F16 port), so an hr pw needed two 6-deep 75-b pads (900 flops); now u_gi direct, one landing to u_hr/u_go | pw +3 (was +4) |
| e | lp mut_landing_net dh (bench MUT 1/2 on an observable landing; landing 0 would be the quiet pw) | - |

Outline 777.6 x 561.6 unchanged; macros / h16c / OPROM row unchanged. Record: results/arch/landed_parent_1018/qfd_tt_ctlm_dv_lpf
(31 landings, 0 pads, ring flops 7,298). Die GEN must re-slot the moved pins, bind f16_* and take the record offsets.

## Safe-design checklist (owner 10-19)
| # | Item | Result |
|---|------|--------|
| 1 | Pins registered, reset landed | PASS (PINREG / keep_pin_regs; lp regional reset runs depth 3, landing_reset_lead). |
| 2 | Reach <= 405 um | fixed: program_obs / command_stage beside u_hr (612 -> ~45 um); gate lint decides the rest. |
| 3 | Fanout <= 32 kept copies | inherited (lp_reset_copies + same_edge_reset_copies max 32, CALPIPE kept selectors). |
| 4 | Depth <= ~600 ps | inherited FIREDQ; gate WARN 605 ps op_user -> infl (16 levels) open, watch. |
| 5 | Storage > 2 kb in SRAM | waived-with-reason: landing rings 7,298 flops as 24-bit local rings (no dual-clock SRAM macro exists; each ring is its own small hierarchy, no runtime-indexed wide array). |
| 6 | Floorplan | unchanged from safe4 (p192 SRAMs 5.21/um, 43.2 lattice, 53% fill, aspect 1.38). |
| 7 | Clock | regional roots + landed crossings (D4/K2 L5); **open risk: pin-flop spread (safe4 re-measure core 192/166, hr 248/205 TT/FF)** -> this gate measures it for real now. |
| 8 | Schedule | static; +1 edge per landing priced in the record compiler block (GEN re-derives lane ages). |

Benches (Verilator 5.050, fleet ep6, source 6076a900d+): see bench_witness/ when committed (lp lockstep MUT0 PASS / 1 2 4 5 FAIL,
prog landed lockstep, opseg landed L0 PASS / L1 L2 FAIL, run_mu_ctlm all, run_mu_opseg pass+mut).
Gate: pre_route_gate --remote auto --cts with this branch's tools (ck_insertion fix). Not critical.
