# Physical-feasibility review of all open elements, 2026-10-10 (hardcore-1010)

The owner asked for this review on 2026-10-10. It covers the 62 elements the registry lists as open (8765/api/elements), plus the newly added HBM-generic, MTP, KV-die and tree-top blocks. Each one is checked against an established-accelerator checklist:

| item | check |
|---|---|
| (a) | registered boundaries, with pin flops anchored at the pins |
| (b) | no wide single-register fanout |
| (c) | reset goes through ot_rst_relay |
| (d) | credit links or skid buffers on long wires |
| (e) | banked SRAM rather than flop arrays |
| (f) | no single-cycle wire longer than 504 µm |
| (g) | one clock root per tile, balanced face taps, lockups on cross-root hops |
| (h) | utilisation of 55–60% or less, a sane aspect ratio, and macro gaps of at least 12 µm |
| (i) | memory reads that tolerate latency |

Every RISK verdict was posted as a fix line in the owning stream's log. The cheap structural fixes run as dual-track lines (`-fe-` / `-fb-` `-cl` jobs).

## Counts

| slice | rows | OK | RISK-high | RISK-med | other |
|---|---:|---:|---:|---:|---|
| E: HBM die tiles (hfd_*), wide VM lanes, Option-A blocks | 23 | 0 | 5 | 18 | 2 of the high rows are superseded |
| F: HBM generic units, idx, row gather, DMA, codec, CP burst, ALL_GATHER | 27 | 1 | 9 | 10 | 8 refer to README.md |
| G: DS ROM, MTP (MX1, WFC credit, head340, coll_core) | 14 | 0 | 8 | 6 | |
| H: Qwen ROM, KV die, tree-top | 24 | 5 | 6 | 11 | 2 superseded |
| **total** | **88** | **6** | **28** | **45** | |

## Top risks

1. **Flop arrays behind wide one-cycle selects, item (e).** These are the dominant class:
   - ot_hgi_dma_front: about 200k flops, and yosys ran out of memory.
   - hgi_idx_topk_full, with a 2048-way select.
   - ot_hgi_sm_pub, with a 256-way select.
   - wfc_cr: a 24x513 landing buffer that has never been routed.
   - The VM wide-lane queues RP/W2: about 71k flops per 32 lanes, with a multi-port procmux.
   - ot_hgi_su_ctlw.
   - qfd_sp_su64_sfu: the rowbuf.
   - qfd_tt_ctlm: a 64x1,024 program store.
2. **One register driving a wide enable, item (b).**
   - The coll_ct/cb credit-relay pointer drives about 4k loads.
   - The seq_su state drives the enable of the 1,024-bit hq register.
   - The TU session compare drives the enables of 8 x 545 bits.
   - The hcoll control signals drive the whole 545-bit word.
3. **Flat compute blocks that synthesis cannot finish.**
   - hfd_idx_score: 512 FP32 adders in one block (fix: harden the 8-head chunk as its own view).
   - ot_hgi_hc_unit: only the small flop version was ever routed (fix: route the SRAM die version).
4. **Unhardened collective features, item (a).** ROW_GATHER is tied off in hfd_coll, the overlapped ALL_GATHER sits in no view, the CP fetch burst needs pins at 20.8 b/µm, and the MX1 collar is unregistered at the CP die.
5. **Floorplan.**
   - hfd_su_tile_xl: GRT congestion in its 100 µm strip.
   - markov/head340: single-cycle 700 µm wires, 6 µm macro gaps, and no exact bench.
   - pqc_spine_screen: a fixed-latency VM read across stations (ds-1010 is fixing it).

## Fixes launched by this review

| job | slice | fix |
|---|---|---|
| hfd_su_tilexl-fe-03b760b60-sw147-tc-{hm10-pd55,hm0-pd45}-cl | E | strip widened to 147.3 µm |
| VM wide lanes, RTL a3e0d3e86 | E | per-lane queues; not routed, because no die view binds RP/W2 yet |
| hc_unit-fe-fd116bc60-{a,b}-die-macro-tc-cl | F | ot_hgi_hc_die with 48 SRAM macros |
| dsfd_coll_ct-fe-34c4ded32-{rslps,rsl}-tc-cl | G | 8 replicated relay pointers, 0 cycles |
| dsfd_coll_cb-fe-34c4ded32-rsltrep-tc-cl | G | 8 replicated relay pointers, 0 cycles |
| qfd_seq_su-fe{a,b}-f3e3d6b6f-tc-hm0-cl | H | PSRAM plus HQ2 two-word head, 0 cycles |
| qkd_ahub-fe{a,b}-5736e945a | H | valid-only resets on the attention-hub adders |

This review also found a real RTL bug on main: ot_hgi_vm_core with RP=0 leaves the CE signal at x under iverilog. It is fixed at claude/hardcore-c-1010@93f2ee279.

## Per-slice rows

### hardcore-1010 feasibility sweep, group E: HBM die tiles / views (2026-10-10 18:50 PT)

Owners: hbm-phys-1010 (hfd_* views, [su]/[sfu]/[att]/[cg]/[fp]) and hbm-phys-vm8 (VM8 halves). Evidence: job state
~/.local/state/closure_loop/jobs/, owner log hbm-phys-1010.log + hbm-phys-1010/COLLECT_*.md, RTL at each element's latest job commit.
Checklist: (a) registered pins, (b) wide fanout, (c) ot_rst_relay, (d) credit/skid on long wires, (e) storage in SRAM,
(f) <=504 um a cycle, (g) clock roots / lockups, (h) util / aspect / pins / macro gaps, (i) latency-tolerant reads.

| element | target | owner | verdict | failing items (evidence) | fix | fix status |
|---|---|---|---|---|---|---|
| hfd_su_tile_xl | HBM accel (SU 512 tiles) | hbm-phys-1010 [su] | RISK-high | (h) GRT-0116 on 9d898f118: M3 65 % average, 2,420 overflow, 659 mm of wire in a 187 x 164 um tile; the 100.224-um register strip carries the 1,743-b bc pass-through, 2,514 pin flops + 2,199 lockups and faces 2,253 lane-macro W-face pins (M4 7.8 b/um). The four routes before it died in GPL / DPO / DPL (4.4 % movable area beside FIRM pin flops). (a)/(g) OK: every pin is a pin flop, negedge lockups on bc_out / acc_out, reset rides the bc chain as a registered bit | widen the strip to 147.312 um (tile 234.144 x 164.16, as [sfu] did in 18d5bc494). RTL is identical; bc pins drop to 3.8 b/um/layer. Quarter impact: the tile pitch grows 47 um ([su] quarter template) | LAUNCHED hfd_su_tilexl-fe-03b760b60-sw147-tc-{hm10-pd55,hm0-pd45}-cl (claude/hardcore-fe-e-1010@03b760b60); posted to owner |
| VM wide lanes (ot_hgi_vm_unit RP / W2 32-lane groups) | HBM accel (hfd_hgi_vm*) | hgi-1010/b (RTL), hbm-phys-1010 [svc] (view) | RISK-high | elaboration: rqq / w2qq were 2-D arrays written from a for-loop over lanes = one memory with RPL / W2L write ports (the 24-deep procmux class that stalled c85592d7f > 3 h). (e) W2 queue = W2 x LQ x 279 flops: 71 k flops a 32-lane group, 143 k at RP / W2 64. (c) rst_n fans out straight to every queue. (d)/(i) OK: credit per lane, any-latency in-order response | per-lane generate queues: each lane has its own 1-write-port array, overflow OR-reduced combinationally, so fault timing is identical (fixes the elaboration class). Still open: (e) move the 256-b W2 payload into per-group SRAM, or size LQ to the measured lane round trip; ot_rst_relay on the unit | RTL claude/hardcore-fe-e-vm-1010@a3e0d3e86 (tb_hgi_vm_lanes PASS, MUT 9 FAIL); posted to hgi-1010/b and [svc]. No route: the RP / W2 view has no die binding yet |
| ot_hgi_su_ctlw (SU WIDE=1 "wide tiles") | HBM accel | hgi-1010 (route assigned to grp C) | RISK-high | same 2-D for-loop queue: dq_s[0:31][0:LQ-1] written as dq_s[b][dq_t[b]] inside a for-loop (peers/ot_hgi_su_unit.sv:1120/1207). It has never been routed | per-lane generate queue (same pattern as the VM fix) before the grp C route | posted to hgi-1010 + grp C |
| hfd_sfu_tile | HBM accel (SFU half width) | hbm-phys-1010 [sfu] | RISK-med | (h) 5de7c4132 failed FLOORPLAN_MARGIN: util 62.5 % and N/S M7 pins at 15.6 b/um. The owner fixed this in 18d5bc494 (strip 147.312, tile 315.36 x 332.64, util ~54 %, pins <= 7.8 b/um); that route is RUNNING. The tile is twice the SU tile's height, so the SU congestion class is less likely here | none beyond the owner's line. If GRT overflows, apply the same strip / height growth | none (owner line live) |
| hfd_sfu (flat quarter) | HBM accel | hbm-phys-1010 [sfu] | RISK-high (superseded) | (f)/(b) flat r24p quarter: post-place TT -2,117 ps over 3,040 endpoints (1,123-ps flat insertion); route crashes | already restructured as 16 tiled hfd_sfu_tile (the R25GQ quarter bench PASSES on r25gqn ports, 2fc33fc00). It waits on the tile view | none (owner) |
| hfd_su_tile (non-xl) | HBM accel | hbm-phys-1010 [su] | RISK-high (superseded) | (h) DRT-0255 / DRT-0073 pin access beside the lane macro, and macro_edge pins behind the lane | superseded by hfd_su_tile_xl (row above) | see the tile_xl row |
| hfd_hc | HBM accel (HC 4 quarters) | hbm-phys-1010 [cg] | RISK-med | (h) 32 macro slivers of 10.37 um (7eea45363 FLOORPLAN_MARGIN); fixed in b9a0074bd (pair gap >= 12 um), hm10 and hm0 RUNNING. (a)/(g) OK: 88 closed lanes, 22 ICGs, 62 negedge lockups, xroot exact bench + cg-late mutant | none beyond the owner's line | none (owner line live) |
| hfd_coll | HBM accel | hbm-phys-1010 (+hgi-1010) | RISK-med | (h) SRAM sliver of 6.07 um (rx[3]/rx[6]) worked around with sliver_block.tcl (a blockage, not a re-placement); lvt-slv / lvt-slv2 NEEDS_HUMAN synth/place, plus a TritonCTS segfault in separateMacroRegSinks. (e) the tu_endpoint has 12 flop arrays | lead decision 17:32: the PHY packer moves out to the per-link hfd_lk_ep, so hfd_coll will be re-cut. Re-place its SRAMs on a >= 12 um grid at that re-cut instead of blocking the sliver | posted to owner |
| hfd_attn_half_hi | HBM accel (attention 32 tiles) | hbm-phys-1010 [att] | RISK-med | (h) v2 GRT congestion on the xp / cf / i / o PORT nets, whose pins overlap their bank's M1-M6 OBS; v2g d4bae12ea moves the pin banks 1.92 um off the faces. (a)/(c) OK: every port is an ot_attn_bpipe bank and reset travels as a pipelined packet bit. 10 fails, mostly flow | none beyond v2g / cgvalid | none (grp C: no fallback; live lines) |
| hfd_attn_half_lo | HBM accel (attention 32 tiles) | hbm-phys-1010 [att] | RISK-med | same as hi; its first global_route ran > 3.5 h (ks 1,102-b + k 1,041-b + ci / ri 1,618-b banks); cgvalid b9a0fdfcc failed on a missing module (branch drift) | none beyond v2g; d34009fe2 cgvalid live | none |
| hfd_vm_ne_e | HBM accel | hbm-phys-1010 [vm8] | RISK-med | (g) the main failure class is CTS hold floods from the face-tap clock plan (bfp: TT -96.3 core->face lockup, fixed in c5808a547). (h) die face 7.3-7.8 b/um, E-W cross face 9.6, N-S 13.9 b/um (> 6 target). (c) rst is synchronised on c_ckw0, then rst_n fans out flat (small: about 3 reset always blocks in the slice) | bfq 328df2a09 set is live. Lower the N-S face pin density (13.9 b/um) by moving N-S buses to M7 / a longer edge, if the N-S halves hold-flood again | posted to owner |
| hfd_vm_ne_w | HBM accel | hbm-phys-vm8 | RISK-med | as ne_e; inner E-W cross face 9.6 b/um | as ne_e | posted |
| hfd_vm_nw_e | HBM accel | hbm-phys-vm8 | RISK-med | as ne_w (inner) | as ne_e | posted |
| hfd_vm_nw_w | HBM accel | hbm-phys-1010 | RISK-med | as ne_e (outer, die face 7.3 b/um) | as ne_e | posted |
| hfd_vm_se_e | HBM accel | hbm-phys-1010 | RISK-med | as ne_e (outer) | as ne_e | posted |
| hfd_vm_se_w | HBM accel | hbm-phys-1010 | RISK-med | (h) the vm8vt sew GRT-0116 was the slice macro block; 328df2a09 widens the gaps to 28.08 um and the pitch to 69.12 um | owner fix live | none |
| hfd_vm_sw_e | HBM accel | hbm-phys-1010 | RISK-med | as ne_w (inner); lvt route attempt 2 after a host loss | as ne_e | posted |
| hfd_vm_sw_w | HBM accel | hbm-phys-1010 | RISK-med | as ne_e (outer, W face 7.82 b/um, the densest die face); r2 calibrated; insertion spread 42..288 ps TT (g) | as ne_e | posted |
| Option-A SM 32 (SM tile / front / be) | HBM accel | hbm-phys-1010 [cg] / fill9 | RISK-med | be_eg / be_wg CLOSED at TC. tile_eg hold flood is (g)+(e): 110 k hold endpoints at the SRAM wd_in / r_addr_in pins (macro clock 59 ps late); front_c i8ob EARLY_FAIL_HOLD with 77.8 k buffers | 4362cee96 adds a negedge lockup before each SRAM macro plus an ENREG ICG enable (owner, accepted) | none (owner) |
| Option-A attention 32 | HBM accel | hbm-phys-1010 [att] | RISK-med | the same hfd_attn_half_hi/lo masters (lead 07:51), so the risk is the two rows above | - | - |
| Option-A SU 512 (hfd_su quarter, 8 x 16 tiles) | HBM accel | hbm-phys-1010 [su] | RISK-high (blocked) | the quarter is not routed: it needs a closed tile_xl view (row 1). Quarter bench PASS at SETTLE 28 (a77a262d2) | tile fix above; the quarter template must take the 234.144-um tile if the fe line closes first | posted |
| Option-A SFU half width (hfd_sfu R25GQ quarter) | HBM accel | hbm-phys-1010 [sfu] | RISK-med | the quarter waits on the tile view; r25gqn port bench PASS | - | none |
| Option-A HC 4 | HBM accel | hbm-phys-1010 [cg] | RISK-med | = hfd_hc row | - | none |
| Option-A index lanes 36 | HBM accel | hgi-1010 / hbm-phys-1010 [idx] | RISK-med | g12 / l16 benches stuck in an -Os compile of a 152 MB unit (an elaboration-size smell, same class as the VM 2-D queues); the IDX lane views are in slice hfd_idx_* (another group) | check the idx lane queues for 2-D for-loop arrays before the route | posted |

## Notes
- hfd_su_tile_xl: congestion (5_1_grt.log on ot-epyc4) is M3 65.4 %, M5 34.7 %, M7 17.3 %; total overflow 2,420 (H 11 / V 18 max). The demand is vertical, inside
  the strip: 1,743 bc bits S->N, plus horizontal stubs from the strip flops to the lane macro's W-face pins. The SFU tile hit the same pattern and widened its
  strip to 147.312 um, the widest the 480-um in-tile hop rule allows. The SU tile takes that width: 147.312 + 86.832 = 234.144 um (542 x 0.432).
  tools/hbm_hub_quarter_gen.py emit_tile_io was reused unchanged (it reproduces the r25gpht4 io_place.tcl byte for byte at 100.224).
- VM wide lanes: the per-lane generate keeps the queue semantics bit for bit (push/pop/full/ovf as before; the sticky overflow is an OR of per-lane sticky
  flags, so status timing is unchanged). Benches: tb_hgi_vm_lanes MUT 0 PASS (2 read + 2 write groups + DMA + packets, exact; rates 0.970 / 0.491 equal
  hgi-1010/b's), MUT 9 (new: lane queue read at the tail) FAIL errors=16321. Not yet read: MUT 5 (core response group, must FAIL) and the yosys proc+memory stat of the old vs new unit at RP 32 / W2 32, both at ot-epyc2:/srv/opentallas-scratch/claude/fe-e/vm/{bench_m5.txt,yo_orig.*,yo_new.*} (run under ot-heavy --mem 32; done marker: done).
- ot_hgi_su_ctlw has the same 2-D for-loop queue (dq_s). grp C's fallback route should apply the per-lane generate first, or it will repeat the VM elaboration stall.
- VM8 halves: there is no cheap fix to add. The live bfq set (16 routes on 328df2a09) carries the clock plan / macro gap fixes. The structural residue is N-S face
  pin density (13.9 b/um), to watch.

### hardcore-1010 feasibility sweep, group F: HBM generic units (2026-10-10 ~18:45 PT)

Checklist (a)-(i) per FEASIBILITY.md. Evidence: RTL on main fd116bc60, latest loop job state, owner log (hgi-1010 / hbm-phys-1010).
Branch claude/hardcore-fe-f-1010 @ fd116bc60 (no RTL change; job specs only).

| element | target | owner | verdict | failing items (a-i, evidence) | fix | fix status |
|---|---|---|---|---|---|---|
| ot_hgi_hc_unit | HBM | hgi-1010/d | RISK-high | (e) every routed job is the W8 flop form: x memory and weight windows in flops (~0.5 Mb at W32). hc_unit_a has sat in yosys on ot-pve1 for 14 h; b is NEEDS_HUMAN calibrate. (c) no ot_rst_relay. The specs have no benches. | Route the production die block ot_hgi_hc_die (W32, WMACRO=1, XMACRO=1: 32x 128x256 + 16x 1024x256 macros, on main since 24629ede4) with OT_WW_MACRO, halo 6.48 (gaps 12.96). Bench: run_hc_unit.sh VIA_LANE exact plus MUT_MP / MUT_POST. Then add ot_rst_relay. | **launched** hc_unit-fe-fd116bc60-{a 1800x1500 PD.50, b 2200x1800 PD.45}-die-macro-tc-cl; posted to owner (also: kill the hung pve1 yosys) |
| ot_hgi_dma_front | HBM | hgi-1010/c | RISK-high | (e) lane FIFOs `lq` 512x274 plus od/cur_d/dd_r/wl, ~200k flops total; variant b was OOM-killed in yosys, a is stuck in calibrate. (b) sf/kmask drive 32x4x256 conv muxes; a 128:1 AND-OR crossbar drives 32x280 `wl`. (c) raw rst_n resets ~18k data bits. (f) the 32-lane crossbar is one cycle across 700-820 um. (a)(d) OK. | Cheap: drop reset on the data bits (dd_r/wl/dq) and add ot_rst_relay (4 regions). Structural: 4 per-stack slices of 8 lanes, each lane FIFO in an SRAM macro, a 2-stage registered stack-to-bank crossbar. | posted to owner (the cheap fix alone does not cure the yosys blow-up, so not launched) |
| ot_hgi_sm_pub | HBM | hgi-1010 (adapters) | RISK-high | (e)/(b) 256 entries x (256+256 b + a 4-deep sent FIFO), ~200k flops; a 256-way priority grant then a 256:1 x 290 b mux in one cycle. pub_b has sat in global_place on pve1 for 7 h. (c) no relay. (a) OK. | Structural: one 8-slot collector per SM with a local registered grant, a 2-level registered tree arbiter (32 to 4 to 1), entry data in SRAM, ot_rst_relay. Kill the hung pve1 route. | posted to owner |
| hfd_idx_score | HBM | hgi-1010/g | RISK-high | (e)/(h) the L4 tap is one flat block of 512 FP32-add engines: lane12 yosys OOM in `share`, lane8 11.5 h in synth -flatten. The bench needs 115 GB (jobs declared 60). The per-slot i_index fix merged at 18:27; the F1 L24 keep frame is still wrong (2,624 of 10,928). | Harden the 8-head chunk (ot_hdc_v41x_idx_chunk_l) as its own view; the tap becomes 4 chunks + idx_tail + front end. Cancel the flat lane4/lane8 jobs. peak_ram_gb >= 120. | posted to owner (structural; no job exists for the chunk line) |
| hgi_idx_topk_full | HBM | hgi-1010 (fill9-idx) | RISK-high | (e) MAX_K 2048 systolic c_key/c_val (85 b x 2048) in flops, ~1.23 M cells; sys1/sys2 post-CTS TT -1674 / -1428 (176k endpoints). (c) rst -> t_clr recovery -478/-533. (d) out_ready -> out_score -485. (b) se2 leaf 5,440 loads. | (b)(c)(d) are covered by the live f9a/f9b (RST_RELAY + OUT_SKID + leaf NT 4). (e) needs a structural change: a streaming radix-histogram threshold select with an SRAM candidate store. | live line covers the cheap items; structural item posted to owner |
| hfd_idx_t4_join | HBM | hgi-1010 | RISK-med | False CLOSED (TT/FF +1e42 sentinel, revoked 18:25); the same route's 6_finish shows SS async recovery -141 (local sync rn -> credits). (a) in->reg 20 levels (tap valid -> occupancy / overflow compare -> fault). (b) combinational `fire` drives 609 enables. (c) local sync, not ot_rst_relay. | Fix the SDC clock binding (owner), register the overflow compare, ot_rst_relay in place of rs1/rs2 (or a non-reset `credits`). | posted to owner |
| hfd_idx_sel_native_qend | HBM | hgi-1010 (fill9-idx) | RISK-med | (h) flow only: PDN-0179 from 10 um RTLMP gaps, a sliver lint, the ck pin off the width table. The RTL is clean (registered inputs, credit pulses, READLAT 2 macro capture). (c) local sync. | Macro channels >= 12 um | live (hbm_idx_qend_f9a/f9b-0bf2e922d) |
| ot_hgi_quant_vm_transport_p | HBM | hgi-1010/c | RISK-med | pp50 TT -98.85 / FF -17.9. (c) no ot_rst_relay. The e02c1820f source (result FIFO in one 64x512 SRAM, unreset payloads) passes rtl_boundary (13/4 levels). | Add ot_rst_relay only if the route shows a reset-removal class. | live (pp55-e02c1820f) |
| ot_hgi_sm_xload | HBM | hgi-1010 (fill9-xv) | RISK-med | Fixed on fc210e160: 32 ot_sram_1r1w_128x256 macros with registered pins, command pin flop, ot_rst_relay, gaps 12.96 / 40 um, rtl_boundary PASS. main still has the flop version. | Merge xv on closure. | live (xload_sram_a-f9a-r2 / b-f9b) |
| ot_hbm_norm_engine_view | HBM | hgi-1010 (fill9-nc) | RISK-med | (h) in_x 8,192 b on the N face = 16.9 b/um/layer (fixed by pm1400: ~3 b/um/layer). (c) a single local 2-flop sync `rs[1]` drives the whole engine reset. (f) at 1,400 um, capture flop -> engine is one stage over 504 um. | ot_rst_relay (4 regions) and a second in_x/wl_d register stage; the BCAST/RET wire budget absorbs it (0 cycles). | live pm1400 covers (h); relay + stage posted to owner |
| ot_hbm_accel_smh_tile_eg | HBM | hbm-phys-1010 | RISK-med | (b) cloned-ICG enable fanout (-545 on CTS). (c) raw rst_n into every smh_kreg, which resets all W data bits. (h) 77% util after the 225k-buffer hold flood (a flow cause: CTS on SS libs, 75 ps margin). Bench = grep of a pinned run.out, not a live transaction bench. | kreg valid-only reset + per-tile ot_rst_relay (ANR pattern), in ot_hbm_accel_smh.sv kreg/kregk (lines 365-397). Add a live transaction bench. | live TC/HM0.010 routes; reset fix posted to owner |
| ot_hbm_accel_smh_tile_wg | HBM | hbm-phys-1010 | RISK-med | Same RTL as eg. np-ref EARLY_FAIL_HOLD -300.4 (112.9k buffers, 114k endpoints); 68% util at geom 362.88. | Same as eg | live smtc-hm10-f9a; posted to owner |
| ROW_GATHER HW (ot_hgi_coll_rgx/_src/_sink, coll_ep RGXHW=1) | HBM | hgi-1010/d | RISK-high | Never hardened: hfd_coll's view uses RGXHW=0, so it is tied off on the die. The block itself is sound: (e) reorder ring in 2x 128x256 macros, pin flops, credit-gated sink. Inherited (e): endpoint FIFOs at full depth are ~2.5 Mb of flops (the view is cut to depth 4). | RGXHW=1 in coll_hgi/rtl/spec.json plus a view route; endpoint FIFOs to SRAM before a full-depth view. | posted to owner |
| overlapped ALL_GATHER (coll_ep PIPE=1) | HBM | hgi-1010/b | RISK-high | (e) parking pk[4][512] x 545 b = ~1.1 Mb of flops with multiple writers per queue (cannot map to 1-port macros as written); gs_p is also flops. Not in any physical view (PIPE=0). | One parking SRAM bank per delivery lane (one writer each) with per-lane linked heads, or PPK 64 plus credit back-pressure on early peers (still exact). | posted to owner |
| CP fetch burst (ot_hgi_loader_cp BURST=1 in hfd_loader HGI view) | HBM | hgi-1010 + hbm-phys svc | RISK-high | (h) loader view pin density 20.8 b/um (N/M5) and 14.3 (E/M4) against a target of 6; cb42c244a/e58b7cadc NEEDS_HUMAN calibrate. (b) head-run detect is a 7-step chained 16:1 mux + 37-bit add/compare in one cycle (feeds m_req_len / fq_h). | Spread or narrow the lq[4x350] bus (2 beats, or a longer face); precompute a "next sector contiguous" bit at push so the run becomes a priority encode. | posted to owner |
| FP8 x-path (ot_hgi_sm_xload block-dot) | HBM | hgi-1010/d | RISK-med | Not on main (WIP 4f3113004). (e)/(b) qb[8][2128] = 17 kb of flops, all read in parallel, with a whole-array synchronous clear. Conflicts with xv's SRAM xload. | Rebase on the xv SRAM xload; qb as a per-slot valid bit plus a banked macro (clear = valid reset only). | posted to owner |
| FP8 KV-row (fmt 7) | HBM | hgi-1010/d | RISK-med (unbuilt) | No fmt-7 RTL on main. The existing FP8 E4M3 row path in att_unit is banked with one writer per bank. | Reuse the closed att_sector_codec as the KV-row encoder. | posted to owner |
| att_sector_codec | HBM | hgi-1010 (Codex hbm_flow) | OK (process gap) | CLOSED TT +69.12 / FF +24.04 / DRC 0, 320x320, util 40, rtl_boundary PASS. But the job had no bench, it is only on codex/hbm-flow-20261010 (a9bcfe9d0), and nothing on main instantiates it. | Merge to main with an exact bench (all BF16 patterns + raw FP8) and MUT_ADDR; bind into ot_hgi_att_unit. | posted to owner |
| ot_hbm_tu_retry_phy_port | HBM | ds-1010 | see README.md | README.md. Update: fb-b (LVT) EARLY_FAIL_SETUP -482 (6,814 endpoints); fb-a still running. | README.md | grp B fb live |
| ot_ha2_truecredit_rx_s_phys | HBM | hbm-phys-1010 | see README.md | README.md (closed sibling rx_phys). Update: cplh hm0-f9a TT -25.81 / FF +2.48; the hm10 route crashed (NEEDS_HUMAN). | README.md | n/a |
| ot_hcoll_port | HBM | hgi-1010 | see README.md | README.md. Update: fb-7ea0839ae a/b/c running; rfetch -r2 NEEDS_RTL (lockstep bench rc=1). | README.md | grp B fb live |
| ot_hbm_native_frame_station_rb_NO3 | HBM | hgi-1010 | see README.md | README.md. Update: pinflop-bd6a6f982 NEEDS_RTL (pin_span bench); corepins f8 running. | README.md | owner line live |
| ot_hbm_native_frame_station_rb_NO3_split | HBM | hardcore-1010 | see README.md | README.md (NO3 two-station fallback). Update: fb a440/b440 EARLY_FAIL_SETUP -631 (3,528 endpoints, route-period 730); c520 running. | README.md | grp B |
| ot_hgi_su_ctl | HBM | hgi-1010 | see README.md | README.md. Update: fb-r2 TT -93.8 / FF +12.9, lvt-r2 TT -67.1. Production SU is ot_hgi_su_ctlw (not touched; another agent routes it). | README.md | grp C |
| ot_hgi_vm_unit | HBM | hgi-1010 | see README.md | README.md. Update: fba/fbb NEEDS_RTL (bench_vm_core_exact rc=1); fill9-xv ECC0 jobs are the line. | README.md | grp C |
| ot_gpu_rf_visibility_fence_p | HBM | hgi-1010 | see README.md | README.md. Update: every PINRET job (c484ee344 f9a/f9b, fb-02359f0c7) is NEEDS_HUMAN calibrate synth_or_place: the pinret_bank hook is still failing before placement. | README.md | grp C |
| ot_hbm_accel_smh_front_c | HBM | hbm-phys-1010 | see README.md (now RISK-high) | README.md. Update: the successor i8ob-e56a62aba-nrd-hm010 is EARLY_FAIL_HOLD (77.8k buffers, 37.7k endpoints, -45.3); 0ee1dea33-f9a NEEDS_HUMAN cts_segv. Same kreg full-data reset as the smh tiles. | Valid-only kreg reset + ot_rst_relay (as for the tiles). | posted to owner |

Counts (27 rows): OK 1, RISK-high 9 (hc_unit, dma_front, sm_pub, idx_score, idx_topk, ROW_GATHER, ALL_GATHER PIPE, CP fetch burst, smh_front_c), RISK-med 10, README-referenced 8 (smh_front_c is counted under RISK-high).

Notes:
- hc_unit launch: no RTL change. ot_hgi_hc_die (unit + HBM lane client) already defaults to WMACRO=1 / XMACRO=1 / W32 and is the die form. Every earlier route was the W8 flop unit. Outlines are first guesses (macros ~0.32 mm2, plus the W32 HCP); there is no cell count yet.
- Hung fleet jobs (owner's call): hgi_adp_hc_unit_a (pve1 yosys 14 h), hgi_adp_pub_b (pve1 global_place 7 h), idx_score flat lane4/lane8.

### hardcore-1010 feasibility G: DeepSeek ROM + MTP (2026-10-10 18:50 PT)

Evidence used: the registry rows (127.0.0.1:8765), job state (~/.local/state/closure_loop/jobs), `rtl_boundary.py check` on
each latest spec (fleet yosys 0.68), RTL greps on origin/main 27e43c7c4 plus the source branches, the ct crpb path_summary
(EPYC2), and the owner logs (ds-1010, mtp-wfc-1010, mtp-head-1010, mtp-mx1-1010, mtp-dsbind-1010, bf-mtp-1010, s81-*).
A cross-slice finding: **no block in this slice uses `ot_rst_relay`.** It was added to rtl/lib on 10-10 and is not
instantiated anywhere yet. Item (c) is therefore judged on what each block does instead: a local sync, a kept reset tree,
or the raw port.

| element | target | owner | verdict | failing items (a-i, evidence) | fix | fix status |
|---|---|---|---|---|---|---|
| dsfd_coll_ct | DS ROM | ds-1010 | RISK-high | (b) the worst routed class is crpb TT -66.17 / FF -0.47 (SS -185.8, 16 levels): rx.rp[*] -> 8:1 landing mux x553 -> tx.l_data enable. Three pointer flops and `send` each fan out to about 4k loads. (e) Each relay holds 8x553 landing flops (4 relays, about 18k flops). (c) One synced rst_s[1] flop clears the whole tile. (a) PASS (0/0 levels). | **RSL=8** in ot_s81ph_cr_relay: 8 kept one-hot read/write pointer copies, each driving only its 70-bit slice (AND-OR select). The tx data register loads every cycle and is sampled only with l_valid. 0 cycles. RSL=0 is byte-identical. | **launched** dsfd_coll_ct-fe-34c4ded32-rslps-tc-cl (= crps PS=1 + RSL) and dsfd_coll_ct-fe-34c4ded32-rsl-tc-cl (= crpb + RSL). Owner lines crps/crpb untouched. |
| dsfd_coll_cb | DS ROM | ds-1010 | RISK-high | (b) It uses the same ot_s81ph_cr_relay x4 (lanes 0/4), so it carries the same rp -> 553-bit class. TREP already fixed the ts_r -> 2,100 t_vm fanout. crpt calibrate died on EPYC1tb (killed in the CTS-only run, infra, nothing re-dropped). (c) Single reset flop. | RSL=8 on top of crpt (TREP). The owner should also re-drop crpt, which died on infra and not on the design. | **launched** dsfd_coll_cb-fe-34c4ded32-rsltrep-tc-cl. Re-drop posted to the owner. |
| dsfd_coll_ce | DS ROM | ds-1010 | RISK-high | (b)/(f) ppar -> 8 spread SRAM FIFOs -> pop -> 2x547-bit enables over 680 um (-794); PULL is the live fix. crpld calibrate was killed by admit (infra). (c) Single reset flop over the whole tile. It has no cr_relay, so RSL does not apply. | Keep PULL (crplc running EPYC3). Re-drop crpld. If PULL misses: ot_rst_relay per FIFO region, and a kept per-FIFO pop copy. | posted to owner |
| dsfd_selt_q2 | DS ROM | ds-1010 | RISK-med | (a) PASS. The last failures are flow crashes (io_flop_at_pins side bug, PDN master); both are fixed. (e) Landing queues lq[Q][DM] are flops, but small (DM=4). | none new; frprck4a/b live; see README.md | none (README.md) |
| dsrom_mtp_head_full340_A | DS ROM (MTP) | mtp-wfc / mtp-head | RISK-high | It is a composite of driver x340 + glue x85 + die inventory, and the driver is the risk (row below). Die: the inter-frame Markov buses needed hop-fix stations (mk20 assert, 617c188cc). Fitting full340 at the real 600x600 driver needs >= 20 head dies, not 12. **Neither head340 job spec has an exact bench** (bench [] + no_bench_reason), so a closure cannot auto-merge. | Add the mb gate (75ccbb9b3 --hard NB4 + mut1/mut2) to the mkglue/mkdrv specs on the next drop. Price 20 head dies. | posted to owner |
| ot_dsrom_markov_head_driver | DS ROM (MTP) | ds-1010 / mtp-head | RISK-high | (h) mkdrv-a: weights.m0/m1 macro gap 6 um (< 12). (f) rg1s EF_HOLD: I2R r_hb spread 700 um, so one cycle exceeds 504 um. (a) rg1a TT +88.32 / FF -89.74, reg -> OUTPUT hold against the signoff -657 reference. pin1a died on a route.sh pin-region bug ('^clk$=top:300-300' HIGH must exceed LOW). pin1b has been routing on PVE1 since 08:13 (10 h at load ~227, likely stalled). (e) data[8]x256 + vector[16]x256 are about 6k flops. | Split r_hb into 2 kept copies per macro side, plus a relay stage on the 700 um I2R hop (+1 cycle). Fix the pin-region syntax (clk window 299-301). Check pin1b for a stall and move it off PVE1. | posted to owner |
| ot_dsrom_markov_bundle_glue (head340 glue) | DS ROM (MTP) | mtp-head | RISK-med | 588 south pins on a 600 um face is about 1 pin/um (fine). The PPL-0093 clock window was fixed (795005ac4). mkglue-a has routed on PVE1 for 10 h. The spec has no bench. | Add the bench; watch the PVE1 stall. | posted to owner |
| ot_dsrom_window_source_ctl | DS ROM | ds-1010 / mtp-wfc | RISK-med | Best TT +79.27 / FF -7.63 (hold only). (c) rst_s2 fanout 4,862: the RST_TREE line (kept per-unit copies, ot_rst_relay-equivalent) is live. (e) mtag/muser [128] mirror is about 4k flops; it is a CAM, with pre-decoded kept write enables. | none new (rsttree + pinroot routing EPYC3) | none |
| ot_mtp_p2_prefix_path | DS ROM (MTP) | mtp-wfc | RISK-med | rb4-s TT +9.66 / FF -25.69: the KEEPWIRES ECO is live and the -cl fb lvt-hm20 is routing. The OLK variant (fill-9) went EARLY_FAIL_HOLD at CTS -100.3 (9,392 ep), so falling-edge lockups flood hold: drop that line. (i) P2 in_r ready across die stations AT RISK (mtp-fixlat-1011 B owns it). | none new; see README.md | none (README.md) |
| ot_v41_pqc_spine_screen | DS ROM | ds-1010 | RISK-high | (i) PQ_VMR x_q is a FIXED 1-edge VM read across 2 die stations (lat-audit BUG-latent). The XRV fix is in [ds-1010/pqc] (diff bench PASS; +13 cyc per Q node). pq_r128 crashed twice on a missing c1r128 terminal json (flow); f3fddfb0b is calibrating. Best FF -76.95 (r16). | XRV meta FIFO + outstanding cap (owner, live) | none (owner live) |
| hfd_cmdproc_s_mtp_native_mx1 (+ emit_queue_mx1, transaction_cp_join_mx1, hgi_mtp_xlate) | HBM (DS MTP) | mtp-mx1 / hgi-1010 | RISK-high | SUPERSEDED into ot_hgi_cp_die MTP=2, where the collar sits **in unregistered form**. (a) rtl_boundary in->reg **15 levels** (the limit is 16), and f_mtp 517 / t_mtp 197 are die nets. (f)/(g) The xl half-cycle hop crosses about 700 um (FT10 -254.7 / -110.5); FT11 (+2 cyc on xl) is routing. | Put pin-flop stations on f_mtp / t_mtp at the CP-die boundary (+1 cycle each way). Keep the MX1 face-root fix. | posted to hgi-1010 + mtp-mx1 |
| dsfd_wfc_cr (WFC credit ports, kit VM_LINK) | DS ROM (MTP) | mtp-wfc / ds-1010 | RISK-high | (e) The link-in landing is ot_link_credit_rx DEPTH 24 x 513 in **flops** (12.3k), and (b) a 5-bit rp drives the 24:1 x513 mux (the ct class, 3x deeper). (c) rst[0] goes straight into the credit FIFOs (no sync or relay). (g) The ck / ckv (1.2 / 0.9 GHz) ports ride hub stations clocked by the slab domain (lat-audit CDC open). (i) The vmx 5-bit wout is capped at 27: exact, but 1.46x cycles. Never routed. | Landing -> ot_fifo_sram_fwft (banked SRAM, 2-deep output skid). ot_rst_relay per domain. One clock domain per station chain, or a CDC FIFO at the kit edge. | posted to owner |
| DS MTP on the HBM die (hfd_mtp / MD-7 ports) | HBM | mtp-mx1 / hgi-1010 | RISK-med | hfd_mtp_x_stop and hgi_mtp_native are CLOSED. The die view carries 1,358 x_stop pins against the 1,319 native-facade pins; MD-7 t_mtp/f_mtp ECO pins have no RTL port in the cmdproc / su_red / router / coll wrappers. | Reconcile the facade at adoption. Add the ports with pin flops (no stub re-routes). | posted to owner |
| S81 coll_core credit split (cb/ce/ct + coll_lane_w + coll_mtp_ep) | DS ROM | ds-1010 | RISK-med | coll_lane_w is CLOSED (lcrpd sliver 7.42 um was superseded by a closed sibling). For cb/ce/ct see the rows above. dsfd_coll_mtp_ep 8/8: (e) 2x lrx_rtt D20 x 512 is about 10k flops; it uses ot_dsrom_mtp_rstsync, not a relay; its binding is PARKED (channel decision). | When binding the mtp_ep, put the lrx_rtt landing in SRAM (D >= 20) | posted to owner |

## Notes

**RSL fix (34c4ded32, claude/hardcore-fe-g-1010, based on fill-9 27f4d045b + main).**
- The ct crpb path_summary (routed, EPYC2) has 8 of its top 10 setup classes inside the cr_relay: rx.rp/n/v_q -> tx.l_data or rx.mem. None of them is a pin wire.
- crps (PS=1) moves the pin wire onto its own cycle, but it leaves this internal class alone. RSL is orthogonal, so it stacks on both.
- Benches (EPYC1tb, ot-heavy, tb_s81ph_coll_sys at the crps define set + RSL): RSL+PS PASS and RSL (no PS) PASS, both at 3,011 cycles (= the PS baseline, so 0 cycles). MUT_RSL FAIL (798 errs) and CR_CRED FAIL (536).
- Mutant OT_S81PH_MUT_RSL: the slice-0 read-pointer copy advances one cycle late.

**Reset (c), slice-wide.** Every S81 tile here resets from one synced flop (coll tiles rst_s[1], mtp rstsync, wfc_cr raw
port). Only wsrc has a replicated tree. That is not yet a proven failure class for these tiles (no reset path in the ct
top 10), so it is RISK-med everywhere. It moves to RISK-high if a recovery/removal path shows up.

### hardcore-1010 feasibility sweep, group H: Qwen ROM + KV die + tree-top (2026-10-10 ~20:00 PT)

Evidence comes from four places: the job states in `~/.local/state/closure_loop/jobs/`, the run-dir `path_summary` / `early_fail` / `corner_sta` files, `qwen-1010.log` and `kv-die.log`, and the RTL at each element's latest job commit (grepped for flop arrays and `ot_rst_relay`).

Checklist: (a) registered pins, (b) wide fanout, (c) ot_rst_relay, (d) credit/skid on long wires, (e) storage in SRAM, (f) <= 504 um per cycle, (g) clock roots and lockups, (h) util / aspect / pins / macro gaps, (i) latency-tolerant reads.

(c) applies to every row below: no element in this slice uses `ot_rst_relay`. They use local kept reset leaves instead (LRST, ot_nhb_rst_leaf, station resets). That is acceptable where the reset classes close; it is flagged only where reset paths show up in the failures.

Branch `claude/hardcore-fe-h-1010` @ 5736e945a (on top of `claude/hardcore-d-1010`).

| element | target | owner | verdict | failing items (evidence) | fix | fix status |
|---|---|---|---|---|---|---|
| qfd_seq_su (seq_su_bi) | Qwen ROM | qwen-1010/a | RISK-high | **(b)** My fallback fba-0ef4d7781 routed TT -131 (979 endpoints). fbb hit post-CTS -537. Both fail on the same path: `u_ctrl.st -> skip/issue -> load -> hq_fill`, which drives the enable of the **1,024-b head register `hq`** (26 levels, cell 1,004 ps). Second class: `st -> o_cnt` (25 levels). **(e)** Program store is 64 x 1,024 flops; already fixed by PSRAM in fba/fbb, which cut the failing endpoints from ~34k to 1.6k | **HQ2**: the FIFO head becomes two words. The fill enable comes only from registers (fq_n, hc), and decode reads hq/hq1 through a registered pointer. Same words on the same edges, 0 cycles. Verilator lockstep: PASS with 600 loads / 800 reads; overwrite mutant FAILS. Still open for a: the `st -> skip -> o_cnt` enable (register the skip decision like ICUT does) | LAUNCHED `qfd_seq_su-fea-f3e3d6b6f-tc-hm0-cl` (RVT) and `qfd_seq_su-feb-f3e3d6b6f-tc-hm0-cl` (LVT), both on 518.4² with PSRAM+HQ2. Posted to a. README/d.md row stands |
| qfd_tt_ctlm (ctlm_i) | Qwen ROM | qwen-1010/a | RISK-high | **(e)+(b)** `ot_qfd_tt_ctlm_i.sv` carries its own copy of the same controller: `prog_mem [0:63] x 1,024` flops and the same `load -> hq_fill -> 1,024-b hq` enable. That is the seq_su failure class above. ctlm_i_{a,b}-955329f22 are live. wide1036/1296 are NEEDS_RTL (bench_wide_slot_prebuild_model rc=1) | Port PSRAM + HQ2 (the two parameters in ot_qfd_seq_su_bi.sv; mechanical) | posted to a (not launched: a's 955329f22 routes are live; port when they show the class) |
| qfd_tile | Qwen ROM | qwen-1010/c | RISK-high | (b)/(c) reset tree to every adder cut bundle; (g)/(h) zero-logic adder hop beside the setup-critical LZC; CTS hold repair stalls with 40k endpoints | ANR, see README/d.md | live: tile-fba/fbb-0ef4d7781 (benches pass) + c's rpx{c,d} |
| qfd_tile_e | Qwen ROM | qwen-1010/c | RISK-high | as qfd_tile; best TT -37 / FF -24 | ANR, see d.md | live: tile_e-fba-0ef4d7781 |
| qfd_io_collective | Qwen ROM | qwen-1010/c | RISK-med | Internals close; the misses are output/input ports only (TT -32.9, FF -9.5). (e) flop-array FIFOs: `mem[PW] x N*DEPTH`, `ib`, `hd`. (h) 760x760 at 14.5 % util: oversized and sparse, so the clock insertion is long. The loop bug I reported is fixed (drive, FRESH-ECO-DIR); a hold ECO is running on the VT-swap pass (TT +10.15) | Short term: the ECO closes it. Structural: per-face IO tiles with their own pin flops and clock sub-root; SRAM FIFOs (d.md) | none (ECO live) |
| qfd_sp_su64_sfu | Qwen ROM | qwen-1010/a (Codex runs) | RISK-high | `bv_acc_{a,b}-93a04cdc8`: **yosys exit -9** (synthesis out of memory) twice. 777 x 2,058 um tile. (e) `ot_qfd_su_master.rowbuf[511:0] x NWD` flop array, plus the SFU/reduce trees in one flat synth | Move rowbuf to an SRAM macro (64x512 / 256x256 existing), or synth with a hierarchy split (keep_hierarchy on the SFU lanes). Declare the real synth peak RAM in the job | posted to owner; bv_e{a,b}-50a21e381 live |
| qfd_sp_vector_memory | Qwen ROM | qwen-1010 | RISK-med | 7 fails, mostly flow: MPL-0003 "no valid tilings for mixed cluster" (macro placer), and route crashes. (h) **1,036.8 x 6,220.8 um, aspect 6:1**. (e) the bv RTL keeps a `mem[511:0] x DEPTH` flop path beside the SRAM macros (param-dependent) | Fixed macro placement Tcl instead of RTLMP (as done for res_slot/seq_su); reduce the aspect toward 3:1 if the bv_w1036/1166 routes congest | posted; bv_w1036/w1166-b3ebf9422 live |
| qfd_sp_band_lanes | Qwen ROM | qwen-1010/c | RISK-med | (h) `_t` variant FLOORPLAN_MARGIN: S/M5 20.8 b/um, W/M4 15.4 b/um. q4_a-53ed21e8b: DRC 0, TT +151 / FF -11.4, hold ECO running. Pin fix works | Use the q4 pin plan for every variant; drop `_t` | none (q4 lines live) |
| qfd_coll_xfifo_l8 (+ _b) | Qwen ROM | qwen-1010/c | RISK-med | Post-route hold ECO ran > 24 h twice (STALE-24H cancels). (e) async FIFO storage as flops (`ot_qwen_async_fifo_w.mem`, `cdc_ch.ib`), which floods hold at the CDC boundary. (g) two clock roots | Latch/SRAM storage for the async FIFO body, or HM10 + LVT recipe; keep the CDC gray pointers in flops | posted; l8q_{a,b}-a3ede03cb-f9a live |
| qfd_sp_constants_sequencer_sys_v_t | Qwen ROM | qwen-1010/a | OK (flow) | Routed TT +14.21 / FF +4.16 / DRC 0 twice. It is NEEDS_RTL only because the ttb_routed_at_TC check failed (LVT corner bug, fixed in eee75ddd7). The rvt re-run is live | none | none |
| qfd_io_host | Qwen ROM | qwen-1010/c (host fork) | RISK-high | Pre-route: A -1,224, B -1,314, C -2,337 ps (127k endpoints). Worst paths are `rbin -> u_eng.bv[130][55]`, `bk[160][8]`, and `qo_slot -> u_ox.mem[0][142]`: (e) large flop arrays written through wide decoders, (b) | c's QPIPE (+2 ingest edges) line A/B-6640463e9 is live. If it is still deep: bv/bk/ox mem to banked SRAM (1R1W macros), with the write decode registered | posted (QPIPE live) |
| ot_qkvd_kv_end (qkd_d2d) | Qwen ROM (KV die) | qwen-1010/b | RISK-med | best d2d_a TT -61 / FF -3.9. (e) `ot_qkvd_fifo.mem` link FIFO as flops; (d) credit counters present (lcred/ocred/owed) | 765c8c422 link-FIFO RTL fix is live; if hold floods, put the FIFO body in SRAM | none (live) |
| ot_qkvd_rom_end (qfd_d2d_rom) | Qwen ROM | qwen-1010/b | RISK-med | d2d_rom_a: hold ECO 15.5 h on 76k endpoints with no progress (hold flood on the flop FIFOs, (e)); 4b7c66f54 combo ECO TT -22.4 | As kv_end: SRAM FIFO body | none (df9afb422 / 4b7c66f54 live) |
| ot_qwen_nearhbm_attn_hub_p (qkd_ahub) | Qwen ROM (KV die) | qwen-1010/b | RISK-med (IDLE) | ahub_b TT -1.67 / **FF -25.11**, 3,857 hold pins on the adders' zero-logic cut hops (`s1_code -> u_cb.r`, `u_cc.r -> y`), the same class as qfd_tile. It was routed with the pre-eee75ddd7 LVT corner bug (ttb check failed). It had no live job. (e) `pb[511:0] x 256` has 4 write and 64 read ports: not an SRAM candidate, keep it | ANR: the 4 adders become ot_hdc_fp32_add_lat_nr (via ot_hdc_fp32_add_lat_sel), bit-identical | LAUNCHED `qkd_ahub-fea-5736e945a-tc-hm10-cl` (RVT) and `qkd_ahub-feb-5736e945a-tc-hm10-cl` (LVT, fixed libs). Benches: lint, gate record, add_nr_exact7 + HMUT mutant |
| ot_qwen_nearhbm_head_h (qkd_rhead) | Qwen ROM (KV die) | qwen-1010/b | RISK-med | First trials (rhead_b/c) are live. Shared `ot_qwen_nearhbm_attn_stack_h.sv` declares large flop arrays (`sc_mem 128 x 4096`, `zc 32 x 2048`, `w 32 x 1024`). The 531 x 544 tile cannot hold them, so they are presumably generated out at this parameterisation; that is unverified | Confirm the instantiated storage in the synth report; if `zc` / `w` are present, move them to SRAM | posted |
| ot_qwen_nearhbm_ectl_h | Qwen ROM (KV die) | qwen-1010/b | OK | Block CLOSED (ectl_b, TT +13.15 / FF +7.46). ectl_c-31a4f64a0 is TT -28.7 / FF -0.4; that is the successor with req_* pin flops at the pins. The earlier (a) failure (`req_t` wire 629 ps) was fixed | none | none |
| qkd_kvwq tiles (leaf / grp / ctl_bin / ctl) | Qwen ROM (KV die) | qwen-1010/b | OK | leaf_s_w129_m, grp_b and ctl_bin_h are CLOSED; adopted plan 128 leaves + 4 ctl. kvwq_ctl_b: FF -0.17 only (not in the adopted plan) | none | none |
| row engines d / e / p | Qwen ROM (KV die) | kv-die | superseded | Pre-route -3,581 / -4,366 (flat engines) were the reason for re-cut H; bound superseded | - | - |
| qfd_sp_tree_top_b (r22ks tree-top) | Qwen ROM | qwen-1010/a | RISK-med | (h) FLOORPLAN_MARGIN on 525b811bb: W/M4 20.8 b/um, N/M5 15.4 b/um, on a 777.6 x 3,732 strip (aspect 4.8:1). The r22ko4 plan of record has no sp_tree_top (ctlm takes its role); r22ks still needs it (despan fix in the generator) | If r22ks stays a candidate: spread the W-face groups over M4+M6 / lengthen the face (as the q4 band_lanes pin fix did) | posted |
| qfd_tt_up4 | Qwen ROM | qwen-1010/a | OK | CLOSED (TT +219.95 / FF +18.95) | - | - |
| qfd_tt_ctl | Qwen ROM | qwen-1010/a | superseded | CTS hold flood (59k endpoints); superseded by ctlm / ctlm_i | - | - |
| qfd_tt_ctlm_wide1036 / 1296 | Qwen ROM | qwen-1010/a (Codex) | RISK-med | NEEDS_RTL: bench_wide_slot_prebuild_model rc=1 (bench / model failure, not physical) | Owner: fix the prebuild model or retire (ctlm_i is the line) | posted |

**Counts:** OK 5 (sys_v_t, ectl_h, kvwq tiles, tt_up4, the closed ctrl_ready PCs). RISK-high 6 (seq_su, ctlm_i, tile, tile_e, su64_sfu, io_host). RISK-med 11. Superseded 2.

**Launched (4 jobs, 2 elements):** `qfd_seq_su-fea/feb-f3e3d6b6f-tc-hm0-cl` and `qkd_ahub-fea/feb-5736e945a-tc-hm10-cl`. My earlier tile-fba/fbb and tile_e-fba lines are left running.

**Bench note:** Icarus re-evaluates `wire x = f(args)` only when the function's arguments change. The ICUT readiness function reads module nets inside `rdy_x`, so under Icarus it goes stale and the controllers' own ICUT assertion fires spuriously.
- The seq_su lockstep bench now runs under Verilator (`rtl/test/run_seq_su_bi_lockstep.sh`).
- My fba/fbb PSRAM benches ran under Icarus, and the base controllers there made no progress. Those PASS results are therefore weak evidence.
- The PSRAM equivalence is re-proven under Verilator: 800 reads, 600 loads.
