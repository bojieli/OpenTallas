# HARD-REVIEW 10-18: dsfd_coll_lane_w / dsfd_coll_lane_e (S81 collective die-link lane tile)

Read-only post-mortem. This review submitted nothing, edited nothing and ran nothing on the fleet.

## Verdict (summary)

- **On the current die: YES.** In the p4l plan, `ot_s81sl_slice_lepw / lepe / lepe_nh` instantiate 2 lane tiles in each end slice (s_0S, s_0N, s_7S, s_7N), so each die has 16 lane tiles. The strict bind cbe82edee lists them as the coll_lane RTL of record (lanes/S81-LINKTO.md, lanes/S81-DIE7.md).
- **Root cause.** The repeated attempts do NOT come from one structural flaw that the team kept patching around. The W tile closed twice (10-07 TT +17.9/FF +11.9; 10-13 TT +24.3/FF +17.4). Each closed view was then invalidated by an **upstream RTL/contract change**: the LCR credit faces, the slot growth to 432 x 337 um, and now CH_BOARD 700. Each change restarted the physical iteration. The physical difficulty that does exist is real and structural. The tile is a **two-way pass-through for 553/515-bit streams across 432 um of a 2 x 5 SRAM array**. Its logic collapses onto one pin face, so the far macro column's 640-bit words and the opposite-face buses must cross 22 um macro-row channels and the single central vertical channel at the M5 cap. That geometry produced the GRT failures and the later macro-edge DRC failures. The E variant has never closed in 14 attempts. Twice it repeated a problem the W kit had already solved: macro orientation and pin edge facing the centre channel.
- **_lt variant.** It changes **function, not closure**: CH_BOARD 400 -> 700 (ACK timeout 1,479 > the 1,106-cycle switched RTT), LCR 1 as instantiated by p4l, and a clock spine. It does **not** address the closure history, and it is a partial **regression**. It took the "rt" geometry (halo 2.16, no SRAM edge strip) instead of the cxea3 geometry that actually closed (halo 5.4 + `dscoll_cx/sram_edge_strip.tcl`, which cured DRC 21 / DRC 7).
- **Verdict: CAN CONVERGE.** The element does not need to be abandoned. The single change that gets there: build **one** lane kit (W), using the exact closed cxea3 geometry (strip + 5.4 halo) plus the spine, and produce E only as an exact MY of it (macros included).
- **Risk: MED.** The W lt route is running now and may hit DRC at the SRAM edges. E gate3 is pending. The fail rate across the history is high, but the failure modes are known.

## (a) Every route attempt (closure-daemon state `~/.local/state/closure_loop/jobs/*coll_lane*`, 69 jobs)

Phase A, 10-06/07: first tile split of the coll_m1 slab, source `1df7cf9a9`; outline 253.8 x 340.2.

| job | variant | verdict | class | key number |
|---|---|---|---|---|
| s81ph-dsfd_coll_lane_w-1df7cf9a9 | v2 split | NEEDS_RTL | setup | SS -940.9 / FF -94.6 |
| s81ph-dsfd_coll_lane_e-1df7cf9a9 | v2 split | NEEDS_HUMAN | flow | route crashed x2 |
| ..._w/_e-752a48488 | | CANCELLED | - | - |
| s81ph-dsfd_coll_lane_w-34b3e75dd | | NEEDS_RTL | setup | SS -971.0 / FF -128.1 |
| ..._e-34b3e75dd, _w/_e-46f583118, _w-a53f40362 | | CANCELLED | - | - |
| s81ph-dsfd_coll_lane_e-a53f40362 | | NEEDS_HUMAN | flow | route crashed x2 |
| s81ph-dsfd_coll_lane_w-ac313d866-wide | wide lanes contract | NEEDS_RTL | setup | SS -456.3 / FF -30.2 (barrel shift) |
| s81ph-dsfd_coll_lane_e-ac313d866-wide | wide | NEEDS_RTL | setup | SS -553.1 / FF -2.1 |
| ..._e-ea4ac869f-head, _e-7aa6f7358-pipeline | | CANCELLED | - | - |
| s81b-coll_lane_{ww,we,ne}-fmt1-9581a871a / -mm-9ac26e269 / -mm2-9ac26e269 (9 jobs) | FMT1 gearbox + EP PIPE2 | CANCELLED | - | superseded by -tt |
| **s81b-coll_lane_ww-fmt1-mm2-9ac26e269-tt** | FMT1 + PIPE2, TT | **CLOSED** | - | TT +17.91 / FF +11.88 / DRC 0 (SS -374) |
| s81b-coll_lane_we-fmt1-mm2-9ac26e269-tt | E | NEEDS_RTL | setup+hold | TT -194.8 / FF -173.4 |
| s81b-coll_lane_ne-fmt1-mm2-9ac26e269-tt | E | NEEDS_HUMAN | congestion | GRT-0116 |
| s81ph-dsfd_coll_lane_e-7aa6f7358-pipeline-tt | E | NEEDS_HUMAN | congestion | GRT-0116 |
| s81ph-dsfd_coll_lane_e-ea4ac869f-head-tt | E | NEEDS_RTL | setup+hold | TT -155.4 / FF -106.1 |
| s81ph-dsfd_coll_lane_e-a53f40362-tt | E | NEEDS_RTL | setup+hold | TT -480.3 / FF -89.2 |
| s81ph-dsfd_coll_lane_e-ac313d866-wide-tt | E | NEEDS_RTL | setup+hold | TT -389.0 / FF -148.0 |
| s81ph-dsfd_coll_lane_w-a53f40362-tt | | NEEDS_RTL | setup | TT -269.1 / FF -39.1 |
| s81ph-dsfd_coll_lane_w-ac313d866-wide-tt | | NEEDS_HUMAN | flow | crashed x2 |

After this phase the 10-08 decision was: E positions use W mirrored (MY), and the E route chain was retired (CRITICAL_PATH.md:32; MISS_DOSSIER.md:322).

Phase B, 10-08..11: mirrorref, then the LCR credit faces (redesign-ds / ds-1010).

| job | variant | verdict | class | key number |
|---|---|---|---|---|
| s81ph-..._w-mirrorref-8dcf713ff-tc-hm25 | | CANCELLED | - | mem estimate |
| s81ph-..._w-mirrorref-8dcf713ff-tc-hm25-r20 | | NEEDS_RTL | setup+hold | TT -80.8 / FF -23.6 |
| s81b-coll_lane_ww-lcra/lcrb-21f1f9381 | LCR | CANCELLED | - | superseded by WFREE landing |
| lcra/lcrb-a17b27437 | LCR | NEEDS_HUMAN | flow | calibrate synth/place error |
| lcra-851328e6c | LCR | EARLY_FAIL_HOLD | hold | CTS hold -87.0, 22,970 buf, 14,321 ep in margin |
| lcrb-851328e6c | LCR | EARLY_FAIL_HOLD | hold | -85.2, 14,248 ep |
| lcrpa-851328e6c, lcrpc-851328e6c | LCR+pins | NEEDS_HUMAN | flow | calibrate synth/place error |
| lcrpb-851328e6c | | CANCELLED | flow | io_flop_at_pins side bug |
| lcrpd-64d47d89b | | FLOORPLAN_MARGIN | DRC/fp | 7.42 um macro sliver |
| lcrpe-1f349bb9c | RXPIPE probe | EARLY_FAIL_HOLD | hold | -50.6 (setup class exp_seq -560 -> RXPIPE d01d0e577) |
| lcrpf-fe478ca46 | | EARLY_FAIL_HOLD | hold | -44.6 |
| lcrpg-2826bcc41 | | EARLY_FAIL_HOLD | hold | -49.8 (setup ch_b limit mux -470 -> TOREG 1d40f2491) |
| lcr0ctl-2e2e05cd5 | LCR 0 control | EARLY_FAIL_HOLD | hold | -64.2 (the control has the same hold signature -> not caused by LCR) |
| lcrph / lcrpw-5c3beb8be | | EARLY_FAIL_HOLD | hold | -92.7 / -174.8 |
| lcrpi-83e0257a8 | | EARLY_FAIL_HOLD | hold | -68.4 |
| lcrpx-83e0257a8 | | NEEDS_RTL | setup | TT -67.4 / FF -15.4 (li_d 553 output flops skipped by io_flop_at_pins, 240 ps wire -> f73b66054) |
| lcrpj / lcrpk-daff468d4 | | EARLY_FAIL_HOLD | hold | -196.1 (buffer cap 30,829) / -191.1 |
| lcrpy-daff468d4 | | EARLY_FAIL_SETUP | setup | post-CTS TT -425.9, 1,798 ep |
| lcrpz-f73b66054 | | NEEDS_RTL | setup | TT -94.9 / FF -7.9 |
| s81b-coll_lane_ww-fmt1-mm2-9ac26e269-tt-arch | | CANCELLED | - | already CLOSED |

Phase C, 10-12/13: ref_tile kit. The 10 SRAMs no longer fit the slot, so contract v8 (a9c66fb9d) grew the outline to 432.0 x 336.96.

| job | variant | verdict | class | key number |
|---|---|---|---|---|
| dscoll_lane_w_rt-rtg-bdce12658 | rt | NEEDS_RTL | flow | bench_lint (SRAM blackbox missing) |
| dscoll_lane_w_rt-rtg-0fdf6f3c2 | rt | REFUSED | flow | kit.env RLAYERS |
| dscoll_lane_w_rt-rtg-0fdf6f3c2-g2 | rt M5 cap | EARLY_FAIL_CONGESTION | congestion | GRT-0116 (replay word split across both columns) |
| dscoll_lane_w_rt-rtm-c57fb7c06 | one memory per column | EARLY_FAIL_CONGESTION | congestion | 13k markers over W SRAM column (0 M5 cap above macros) |
| dscoll_lane_w_rt-rtm-3368582fd (+ -hs) | grt_macro_top_layer | NEEDS_RTL | hold | TT +24.9 / FF -14.7 (u_ski.out_d -> u_rb wd_in leaf skew) |
| dscoll_lane_w_rt-rth-79fa61520 | HM 30 ps | NEEDS_RTL | DRC | TT +15.5 / FF +8.7 / **DRC 21** |
| dscoll_lane_w_cxea-cxea-d8b0f7a0e | cxea | NEEDS_RTL | DRC | TT +15.5 / FF +8.7 / DRC 21 |
| dscoll_lane_w_cxea-cxea2-f22cf02e5 | | EARLY_FAIL_HOLD | hold | -19.5 plateau (guard false positive) |
| dscoll_lane_w_cxea-cxea2-f22cf02e5-efb | | NEEDS_RTL | DRC | TT +24.8 / FF -4.0 / DRC 7 (M4 stubs over macro OBS) |
| **dscoll_lane_w_cxea-cxea3-a011f9e61** | M5 no-entry strip + halo 5.4 | **CLOSED** | - | TT +24.34 / FF +17.42 / DRC 0, auto-merged 22566e03c |

Phase D, 10-18: the lt kits (CH_BOARD 700 + LCR 1, branch claude/s81-linkto-1018).

| job / gate | verdict | class | key number |
|---|---|---|---|
| gate 6b4725cef (W, CTS, no spine) | FAIL | spread | TT/FF pin-flop spread 164.7 / 150.1 ps |
| W gate2 (spine) | WARN 0 fail | - | spread 27.3 / 33.4 ps, GRT ovf 0, setup +38 / hold -65 pre-repair |
| **dscoll_lane_w_lt-lt-9356760de** | RUNNING (route.a1 on ot-epyc4 since 18:06; benches and witnesses passing beside it) | - | - |
| E gate2 (R0 macros) | FAIL | congestion | trial GRT ovf 6 on M5, centre channel x~226 |
| E gate3 (MY macros, 13ec0b8dd) | RUNNING (pid 3189256, ot-epyc5, log empty) | - | - |

Totals: about 33 W and about 22 E non-closed routes, about 25 of them cancelled or superseded. Real failures by class: setup 14, hold (CTS non-converge or FF) 16, congestion 6, DRC 4, flow/kit/tool 11.

## (b) Physical facts (lt kit = rt geometry)

- **Outline** 432.0 x 336.96 um, aspect 1.28:1. The original slot was 253.8 x 340.2; it grew in v8 because 10 SRAMs at the channel rules did not fit.
- **Macros.** There are 10 x `ot_sram_1r1w_512x128_m4_r2c2` (174.1 x 29.7 um, OBS through M4) in 2 columns x 5 rows. The columns sit at x 31.5 (u_rb, the replay buffer) and x 225.9 (u_fifo, the receive FIFO), at a y pitch of 51.84, which leaves **22 um row channels** and one ~13 um central vertical channel. The y pitch is not on the 43.2 um lattice (offtrack 0). Each memory is 512 x (FFW = 10+1+552+32 = 595 bits), so each word is split across 5 macros. Macros are 51,776 um2 of a 145,567 um2 outline; std cells are 10,496 um2, for a fill of 43%.
- **Pins.** 2,304 in total. In W: W face 1,090 over 198 um (5.5/um: rx 515 + tx 512 + tf) and E face 1,175 over 236 um (5.0/um: lo_d 553 + li_d 553 + handshakes + flt). N face carries ck/rs/chb. These are partial faces at <= 6/um, so they are within the rule. E is the x-mirror.
- **Register mass.** The density PNG shows the logic piled into the **W half** and the W gutter (density up to ~1.0 at the W column and centre row channels). The E half, including the u_fifo column and the E (core) face, is nearly empty of cells. The core-face buses (lo_d in, li_d out, 553 b each) therefore travel ~300-400 um through the 22 um row channels. In lcrpx this cost 240 ps of wire on li_d.
- **Clock.** The single root ck has 15,495 sinks plus 10 macro clock pins. Without the spine the pin-flop spread was 164.7 / 150.1 ps (FAIL). With the spine (N centre entry) it is 27.3 / 33.4 ps, at insertion 531.8 / 433.4 ps. The pin sits at x~162 um for W. For E it sits at x~217 um (centre), which is not the mirror of W (expected ~270 um). That is worth a look in gate3.
- **High fanout.** `rst_s[1]` has 6,837 loads (951 flops), from an async reset on every datapath register. `u_ski.rp[1]` has 4,426 loads: the LCR 8-deep x 553-bit landing FIFO's read-pointer mux, which is a wide-mux broadcast.
- **Logic depth.** `u_ep.snd -> in_ready` is 17 levels, ~648 ps, the go-back-N sender acceptance. Earlier classes were already fixed in RTL: the FMT0 gearbox barrel shift (-456/-553 -> FMT1 + PIPE2), exp_seq classification (-560 -> RXPIPE), and the ch_b timeout limit mux (-470 -> TOREG).
- **CDC.** None: one clock. tf is a forwarded buffered clock. rx is registered at the pin.
- **Trial GRT (W lt).** M2 29.7%, M3 12.1%, overflow 0.
- **E gate2.** Overflow 6 at the M5 centre channel x~226, at the u_rb column's rd_out/wd_in LEF pin edge. With R0 macros in a mirrored tile, the macro pin edge faced the centre channel instead of the outer channel.

## (c) Root cause, separated from symptoms

1. **Primary reason for the attempt count: contract churn after closure.** This is process, not a physical flaw. W closed on 10-07 (fmt1-mm2-tt) and was re-opened by LCR credit faces (10-10) and by slot growth to 432 x 337 (v8, 10-12). It closed again on 10-13 (cxea3) and was re-opened by CH_BOARD 700 + LCR 1 in the p4l instantiation (10-18). About 25 of the jobs were cancelled or superseded, not failed.
2. **The real structural difficulty.** The tile is a **bidirectional wide pass-through with one logic centre**. The die stream enters and leaves on the W face; the core stream enters and leaves on the E face. Between them sit the link endpoint (CRC32, go-back-N, gearbox) and two 512 x 595-bit memories, each split into 5 macros and stacked in a column. Placement puts the logic next to the die face, where the gearbox and CRC connect. So the E column's 640-bit read/write words and the E-face 1,106-bit core buses must cross the macro array through 22 um row channels and one central vertical channel, with M5 as the only layer above the M4-OBS macros. Every physical failure class follows from that:
   - congestion over the W column at the M5 cap (rtm, 13k markers);
   - the replay word split across columns (rtg-g2);
   - DRC at the vertical SRAM edges in the central channel (rth / cxea DRC 21, cxea2 DRC 7);
   - li_d wire delay (lcrpx);
   - E ovf 6 at x~226.
3. **Hold series (phase B, 13 jobs).** This was a flow and kit artefact, not the LCR RTL: the LCR-0 control job failed identically. CTS hold repair could not converge, with ~14k endpoints in margin. The fixes were flow-wide: macro clock clustering (45d7c6d79), io_flop_at_pins fixes, HM 30. After those, hold stopped being the blocker.
4. **E-specific.** The E kit has been rebuilt as a separate floorplan three times. On 10-07 it hit setup, hold and GRT. On 10-18 it ran with R0 macros, and its macro pin edges were not mirrored. A true MY copy of the closed W was decided on 10-08 and is still the right answer.
5. **The lt variant does not touch causes 2-4.** Its changes are functional: CH_BOARD 700 widens the timeout counter 10 -> 11 bits (TOREG keeps it registered), and LCR 1 matches p4l. It also **drops the cxea3 fixes**, `sram_edge_strip.tcl` and halo 5.4 -> 2.16, and goes back to the rt geometry that ended at DRC 21. The W lt route could therefore repeat rth's DRC 21 at the SRAM edges.

Symptoms the retries chased: hold-repair plateaus, HM tweaks, the halo / sliver lint, GRT layer caps, mirrorref / mem estimates, io_flop_at_pins classification.

Structural content that was actually fixed:
- the gearbox format (FMT1);
- the EP pipelining (PIPE2, RXPIPE, TOREG);
- one memory per column;
- the M5 strip.

## (d) Redesign / convergence

**CAN CONVERGE. Do not abandon.** The architecture is acceptable: a reliable link layer at an off-die boundary is allowed under hbm-static-onchip, and W closed twice with this partition and outline.

**Single change (now, zero cycles, zero area):** port cxea3's closure geometry into the lt kit (`sram_edge_strip.tcl` + `--macro-place-halo 5.4`, keeping the spine). Then make dscoll_lane_e_lt an exact MY transform of the W lt kit (macros, pin plan, clock pin x position, strip), or bind the W view mirrored as decided on 10-08. If the W lt route ends DRC > 0 at the SRAM edges, this is the fix. Apply it to E before E gate3 goes on to route.

**Structural improvement if the tile re-opens again (optional, for robustness, about +1 cycle each way and no outline change):**
- Put the rx FIFO (u_fifo) column on the core-face side and the replay buffer on the die-face side. They already are. Then pull the core-side logic (LCR landing FIFO, li skid, fifo read path) **next to the E face** as its own placement region (a region constraint or a separate leaf), so that only the 595-bit endpoint <-> fifo interface crosses the array, once, in a registered hop.
- Make the endpoint a 2-region tile: a die-side leaf (gearbox + CRC + replay) and a core-side leaf (landing + rx fifo), each with its own local clock root and a landed seam (the 10-18 landed-regions standard). This removes the single 15.5k-sink root and the 300-400 um core buses.
- Replicate `rst_s` per region, and drop async reset on datapath registers. Split `u_ski.rp` per 128-bit slice.

Cost: +1-2 cycles on each lane direction, against a ~553-cycle switched crossing, so a negligible rate effect. Area unchanged; the macros already set the outline.

**Process fix:** freeze the lane tile contract (CH_BOARD, LCR, ports) before the next route. Any further protocol parameter should be a strap or a register, not RTL, so a closed view survives. The CH_BOARD change could have been a static strap input, as ch_b already is.

Not structural, recorded as a residual risk: with a 1,106-cycle switched round trip, a 512-entry go-back-N replay window cannot sustain back-to-back streaming. The measured TOKEN-XDIE-S81 calendar passes (12,096 exact, 0 late), so the per-token collective traffic fits.

## Evidence paths

- Closure-daemon job states: `/home/ubuntu/.local/state/closure_loop/jobs/{s81ph-dsfd_coll_lane_*,s81b-coll_lane_*,dscoll_lane_w_*}.json`
- PNGs (extracted from origin/claude/s81-linkto-1018 to `/tmp/hr_colllane/`):
  - W lt floorplan `/tmp/hr_colllane/physical_ref_tile_dscoll_lane_w_lt_gate_layout_floorplan.png` (repo: `physical/ref_tile/dscoll_lane_w_lt/gate_layout/floorplan.png`)
  - W lt density `/tmp/hr_colllane/physical_ref_tile_dscoll_lane_w_lt_gate_layout_density.png`
  - E gate2 floorplan / density / congestion `/tmp/hr_colllane/results_rtl_s81_linkto_1018_e_gate2_r0_{floorplan,density,congestion}.png` (repo: `results/rtl/s81_linkto_1018/e_gate2_r0/`)
- Gate results: `physical/ref_tile/dscoll_lane_w_lt/gate_result.json`, `results/rtl/ref_tile/dscoll_lane_w_lt/gate_cts_6b4725cef/gate_findings.txt`, `results/rtl/s81_linkto_1018/e_gate2_r0/gate_result.json` (branch claude/s81-linkto-1018)
- Kits: `physical/ref_tile/dscoll_lane_w_lt/`, `physical/ref_tile/dscoll_lane_e_lt/`, `physical/ref_tile/dscoll_lane_w_cxea/` (closed geometry: `pre_grt.tcl` sources `physical/dscoll_cx/sram_edge_strip.tcl`, `kit.env` halo 5.4)
- RTL: `rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.sv`, `rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep.sv`
- Key commits: 1df7cf9a9 (v2 split), 08952d15e (CLOSED fmt1), a9c66fb9d (slot growth v8), c57fb7c06 / 3368582fd (column / M5 cap), a011f9e61 + 4efdbef2c (cxea3 CLOSED), d01d0e577 RXPIPE, 1d40f2491 TOREG, f73b66054 io_flop_at_pins, ea0ea3515 / 00a7a6872 (lt CH_BOARD 700), 13ec0b8dd (E MY)
- Lanes: `/home/ubuntu/claude-takeover-20261007/lanes/S81-LINKTO.md`, `RELEASE_TREE.md` lines 44-45, `MISS_DOSSIER.md` lines 322 and 534, `CRITICAL_PATH.md` line 32
- E gate3 log (empty, process alive): `/home/ubuntu/scratch/s81-linkto2/gate3_e.log`
