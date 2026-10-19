# hnx_hcq_hub_safe_1019: safe successor of the HC quarter hub (hnx_hcq_hub_1019)

Lane LEAD-HBM / LH-P3UNITS/HUB, 2026-10-19. Branch `claude/hnx-hub-safe-1019`.
Spec source: `physical/hbm_next/hc/specs/hnx_hcq_hub_safe_1019.json`.
PARALLEL variant (same RTL, wider band): `hnx_hcq_hub_safe_b389_1019`. Bind whichever closes first and cancel the other.

## Why a structural redesign

- n1 (`hnx_hcq_hub_1019-n1-c8a284b41`) ended FLOORPLAN_MARGIN on wire_reach: one beat-control register drove four faces.
- n2 (`hnx_hcq_hub_1019-n2-3af689b62`) ended EARLY_FAIL_HOLD at FF. The endpoint was `result[721]` port -> `result_q[721]`.
- The n2 cause was physical. One clock tree covered the whole 734.4 um square: 48,778 registers, 9.6 % utilisation. Every pin flop was anchored on its own face, on all four faces.
- So the input pin flops had a clock spread of 151 ps at TT and 134 ps at FF, against the 80 ps limit. With the die hold reference (L_min 759.5 ps), the far-face capture flops failed hold by -95.7 ps at the initial FF check, and by -70.8 ps after 33k hold buffers.
- There is no indexed storage on this path (`HUB_N2_SUCCESSOR_BRIEF.md`, commit df784b971).

## The structure

1. **One central standard-cell band (pin registers included).**
   - Every synthesized standard cell is placed by global placement inside one central band: 345.6 x 345.6 um at (194.4..540.0) here, 388.8 at (172.8..561.6) in the b389 kit.
   - Tie cells stay outside.
   - The band is a global-placement region only. `physical/hbm_next/hc/hub_band_gpl.tcl` creates it at PRE_GLOBAL_PLACE, and `hub_band_dpl.tcl` removes it at PRE_DETAIL_PLACE. No region reaches the legaliser, which matters because the 10-19 P3 ATT gate crashed DPL inside an EXCLUSIVE region.
   - Pin flops are not anchored at the faces (no `io_flop_at_pins`).
   - The single clock tree therefore serves a compact register mass instead of four faces 734 um apart.
   - Every face pin is one registered hop of at most ~390 um from the band: <= 194.4 um perpendicular plus <= 194.4 um along the face.
   - The collar carries only pin wires and their repeaters.
2. **s_i pin register (RTL, `ot_hnx_hc_qcen` SIREG 1).**
   - The 2,049-b chunk-sum input used to drive the level-1 adders' A1 decode/compare logic straight from the port, which broke safe-design item 1. It now lands in a pin flop.
   - **Zero added edges:**
     - the level-1 adders run LAT 6 (the standard LAT-6 cuts A, B, C; only the D cut after the sentinel LZC goes);
     - the leaf valid and the lane-fault pipe move one edge;
     - so ps_v / ps / ps_f leave on the same edge as before.
   - Bit-exact: ot_hdc_fp32_add_lat is the same adder for every cut choice.
   - SIREG 0 (the default) is the n2 RTL bit for bit.
3. **DRLY 2.** The n2 kit ran the qhub default DRLY 1. The benched U-ring form (tb_hnx_hc_eng4 `HC_DRLY=2`, `HC_XRLY=1`, `HC_QDRLY=2`), the d4g hub kit `hbm_hcq_hub_1017` and the root's QDRLY 2 all use 2. The view now matches the bench and the root's fixed ps edge.
4. **SRAM on the 43.2 lattice.** The programme SRAM (174.7 x 70.5 um) sits at (259.2, 302.4), inside the band. n2 had it at (280.8, 332.64), which is off the lattice.
5. **Reset.**
   - rst_n lands in 2 registered stages (kit `reset_landing`).
   - The kept relay copies are split to <= 32 loads (`reset_relay_split.max_loads 32`, ot_rst_copies.tcl). n2 had about 8,048 asynchronous loads on ~15 relay flops.
6. **Boundary.** io_hold_margin 0.03 (>= 0.025); hold_budget die. Pins, faces and outline are unchanged from n2, so the die contract is unchanged.

## SAFE-DESIGN checklist (owner 10-19, 8 items)

| # | item | result |
|---|---|---|
| 1 | Pins registered; reset lands in 2 stages | **fixed**. Every input lands in a flop: s_i is now pin-registered (SIREG 1); hc_q, qcen and the F20 target were already registered (n2 pin_regs reason). Every output leaves a flop (lg_rq/lg_wq/x_wave/gathered/ps/wc/bd/rstb/status). rst_n uses the 2-stage reset_landing. |
| 2 | Reach <= 405 um per cycle | **fixed** by placement: all registers are in the central band, and face pin <-> band flop is <= ~390 um. The n2 face-anchored flops made N-face rr_q -> S-face x_wave about 700 um in one edge. |
| 3 | Fanout <= ~32 | **fixed** for the reset: relay copies are split to <= 32 loads. The per-face beat-control copies (ot_hnx_hc_xbrep, kept by name) and the 4 kept ingest-control copies (c_wv/c_xv/c_j/c_a) are unchanged. |
| 4 | Depth <= ~600 ps / 20 levels | PASS-expected. The tree adders keep 7 cuts per level except level 1 (6 cuts after the new pin flop, the standard LAT-6 split). The gate's logic-depth lint and TT setup confirm it. |
| 5 | Storage > 2 kb in SRAM; no long flop delay lines | PASS. The programme is already a 1024x256 SRAM. result_q/rr_q/s_q are single captures, not arrays. done_cal (8x19), order (12x23) and the leaf-valid pipe (1-b) are below 2 kb. The FP32 tree registers are arithmetic cuts, not alignment delay lines. The 6,144-b BEATS1 assembly is not instantiated (BEATS 4). |
| 6 | Macros on lattice, channels, util 40-60 %, aspect <= 2:1, full std band | **fixed / waived**: SRAM on the 43.2 lattice with a 5.4 halo; one contiguous band; aspect 1:1. Band utilisation is ~42 % (345.6 band, ~50k um2 incl. SRAM) or ~33 % (b389). Tile utilisation stays ~9.6 % (fill_reason.pin_bound): there are 10.1k literal face pins (N 2,854), so faces must be >= 476 um at 6 pins/um, and the die slot is the bank-ring hole. Face pin density is <= 3.9 pins/um. |
| 7 | Clock: centre or regional roots, spread <= 80 TT+FF, io_hold_margin >= 0.03 | **fixed** structurally. There is one root, entering at the W-face centre (pin centred by the generator) with a ~194 um trunk to the band. Its sinks are all inside one compact band, so the pin-flop spread is that of a 345.6 um register mass, not of four faces 734 um apart. io_hold_margin is 0.03. The `--cts` gate measures TT/FF spread. |
| 8 | Static schedule; every added cycle priced | PASS. **0 added edges** (SIREG is absorbed by the level-1 adder). HC_MIX row II 250 and every root/bank/VM edge are unchanged. The DRLY 2 binding equals the benched form (the n2 kit's DRLY 1 was a view/bench mismatch, now removed). NOTICE in lanes/HBM-NEXT-CMTP.md. |

Face regions with landed crossings were considered and rejected for this tile. Data enters on one face and leaves on another two edges later: lg_rr on N -> rr_q -> x_wave on W/N/E/S, and result on S -> result_q -> store -> lg_wq on E. With every pin flop anchored at its face, those hops are about 700 um. Making them safe would need a relay or landing stage on each crossing: +1 edge on the VM tap, the bank links and the root links, and a re-derived root and VM schedule. The central band keeps 0 edges and satisfies reach. The remaining regional-clock fallback is a cluster parent (face tiles + core tile), for the case where the band's spread measures above 80.

## Benches (Verilator 5.050, fleet; bundle `b_bb0f6ffe1`)

- `hnx_hcq_exact` q_n4s + q_d4g: PASS. `hnx_hcq_mut7/8/9`: FAIL, with committed witnesses (hc_q is unchanged; ot-epyc4 run 12:05 confirms them).
- `hnx_hc_ring_rows_sireg` (s0): the ring lockstep with SIREG 1, N = 1, 2, 3, 4, 6, 8. Expect `HNX_HC_RING SIREG=1 MUT=0 PASS 6/6` and HC_MIX cycles identical to e0.
- `hnx_hc_ring_mut5_sireg` (s5): the SIREG landing without the leaf-valid delay must FAIL. Witness: `results/arch/hbm_next_1019/units/hc/witness/s5_n4.log`.
- `hnx_hc_ring_mut1`: unchanged witness `e1_n4.log`.

## Gate

`--cts --remote auto` for both kits, launched 10-19 ~12:10 (see `pending_results.txt`). Accept when:

- GRT overflow is 0;
- pin-flop spread is <= 80 at TT and FF;
- the gpl log shows `HNX_HUB_BAND gpl region` and the DPL log shows `band region removed`;
- the layout PNG shows the band.

Then commit `gate_result.json` with the kit, add the s0/s5 witnesses, and submit with submit_exact (not a critical tile).
