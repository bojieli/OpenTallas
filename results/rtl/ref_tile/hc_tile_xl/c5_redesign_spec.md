# hc_tile_xl c5 redesign spec (ot_hgi_hc_tile)

Status: SPEC ONLY. Nothing here is implemented, routed, closed or qualified. No c5 job has been submitted.
Author: Claude/el1013-hbm-hc c4-verdict, 2026-10-13 PT. Branch `claude/el1013-hbm-hc-c5`.

## 1. What c4 measured (hc_tile_xl-c4-550082537-hs, NEEDS_RTL, NOT CLOSED, run preserved)

Run: ot-epyc1tb `/srv/opentallas/claude/closure-loop/hc_tile_xl-c4-550082537-hs`. Verdict STA =
`cl/routed_ioref.a1_meas/meas_{ss,ff}.tcl` (6_final.odb + 6_final.sdc + SPEF, propagated clock, kit signoff.sdc,
io_ref_routed appended). Period re-checked in a read-only replay: `DIAG_PERIOD 833.333`. Evidence copied to
`c4_verdict_diag/` (verdict `OT_*` lines, stall report, DRC report, my replay Tcl and logs).

| check | worst | endpoints | TNS |
|---|---|---|---|
| TT setup | -294.75 ps | 1,192 D pins (1,202 paths incl. macro pins and ports) | -140.8 ns |
| FF hold | -21.45 ps | 33 D pins; 89 endpoints incl. 56 SRAM `wd_in` pins | -0.344 ns |
| DRC | 11 | | |
| SS sensitivity | -611 ps | 2,668 | |

The verdict's `violating_d_pins` counts `*/D` only: the hold count that matters is 89, not 33.

### 1a. TT setup: wire length across the tile, not skew, not a macro clk->q, not a reference artifact

| class | worst | n | startpoint -> endpoint | data path | launch / capture clock |
|---|---|---|---|---|---|
| reg->macro | -294.75 | 24 | `hr_tl[32]` -> `g_win[2].u_w.g_mac.g_s[3].u_m/w_addr_in[1]` | 1,041 ps: 5 gates + 9 buffers, three buffer stages of 209 / 189 / 135 ps | 1,004.0 / 1,003.2 (skew -0.8) |
| reg->macro | -290.37 | 13 | `u_st.w_addr[0]` -> `g_win[3]...g_s[3].u_m/r_ce_in` | 977 ps: 11 gates (subtract, compare) + 157 / 146 / 122 ps wire stages | 1,064.5 / 1,030.5 (-34) |
| reg->reg | -245.07 | 161 | `hr_tl[*]` -> `g_win[*].u_w.valid[*]`, `received_sectors[*]` | same cone as row 1 | |
| reg->reg | -200.86 | 644 | `base_q[0]` -> `g_win[3].u_w.issued_reqs[1]`, `valid`, `hbase_r`, `received_sectors` | 921 ps: 14 gates (base + soff adder, range check) + 313 ps wire | 1,035.0 / 993.5 (-41.5) |
| in->reg | -222.39 | 237 | `hq_rdy[2]` -> `g_win[2].e0[38]/D` (also `e1`, `cnt`, `hv`, `rm`) | 715 ps from the port: 472 ps in 4 wire buffers, then 6 gates | ext 1,275.4 = 166.7 + 1,018.7 + 90; capture 1,007.4 |
| reg->out | -240.23 | 55 | `g_win[2].e0[18]` -> `hq_addr[74]` (also `hq_tag`) | 741 ps: one inverter + 7 wire buffers (223 / 150 / 144 ps) | launch 1,034.2; ref 1,026.2 |

Clock skew on the failing paths is 1 to 42 ps. The boundary reference is consistent with the flops it constrains
(input reference 1,018.7 against capture 1,007.4; output reference 1,026.2 against launch 1,034.2), so the
routed-insertion SDC is not the cause. No failing path starts at a macro clock pin. The -294.75 figure is correct.

Cause: one flop hop is asked to cross 250 to 480 um and then do 5 to 14 logic levels.
- N face (y = 725.76) carries hq_* / hr_*; the four windows sit at y 250..480, x 22..232 (0, 1) and x 424..634 (2, 3).
- S face (y = 0) carries c_*; `base_q`, `soff_q`, `nwk_q` are S-face pin flops feeding all four windows.
- `e0` is the registered hq output, but its D cone comes from the window, so the placer put it at the window,
  640 ps of wire from its N pin. The header comment ("hq_rdy only moves FIFO pointer flops") is not true of the
  netlist: `pop` muxes all 46 bits of `e0 <= e1`.
- `u_st.w_addr` (centre column) -> `wsel` compare / `w_addr - bnd` -> window SRAM read address is one hop.

### 1b. FF hold: skew between neighbouring spine leaves; outputs are clean

| class | worst | n | example |
|---|---|---|---|
| reg->reg | -21.45 | 22 | `g_ml3.wcap[2205]` -> `wd[157]/D`: launch 800.1, capture 859.0 (59 ps skew), data 65.7 ps |
| reg->macro | -13.83 | 56 | `g_xm[1].dl_q[1][14]` -> `g_xm[1].u_x/wd_in[142]`; `hr_dl[*]` -> window `wd_in[*]` |
| in->reg | -9.15 | 11 | `hr_data[980]` -> `hr_dl[980]/D`: reference flop 823.3, this flop 849.2 |
| reg->out | +0.97 worst (MET) | 0 | `o_nv[0]` is +23.73 |

The launch and capture leaves of the worst path differ by one HB4 pad (`clkbuf_sp_L548_p*` 2 pads, `L528_p*` 3):
the spine's per-leaf padding, set from placement estimates, leaves +-40 to 60 ps after routing. Input pin flops
arrive over 779..868 ps at FF (89 ps spread) against a 50 ps hold allowance.

`window R2O=12@-36.1` in the job reason is NOT the sign-off result. `closure_loop.py` (~line 4212) reads
`ot_hold_stall_cts.rpt`, the residue of the in-flow hold repair at the CTS stage (chunks 1,418 -> 625 -> 12 -> 12
endpoints, stalled at -36.1 on `o_nv` / `o_xa` / `o_wa`, measured against the CTS-stage reference), and prints its
classes next to the routed FF number. At sign-off those 12 outputs are positive. The guard fired because -36.1 is
not shallower than -21.45 + 2.

### 1c. DRC 11: a hole in the child abstract's own-layer OBS, not the y[255] stub, not congestion

All 11 (5 Metal Spacing, 3 Short, 3 EOL; 10 on M6, 1 on M4) are against `u_st.g_lg.g_grp[1].u_lg` and `g_grp[2].u_lg`
at tile x 272.10..272.29, y 239.9..240.6 and 412.7..413.3: the same leaf-local spot (12.90..13.09, 23.9..24.6) in two
instances. The leaf LEF has M6 OBS rects ending at x 12.947 and one covering 12.947..13.139 only up to y 23.84; the
pocket above it (192 nm wide, three M6 tracks) is open, and the tile router ran M6 through it. The y[255] stub that
c4 changed is on the E face at local (138.0, 85.95). GRT usage is 25 to 29% per layer. DRT sat at 11 to 14 for 30+
iterations. This is an exporter defect (child_lint already warns "916 of 917 face pins partly under a same-layer OBS
rect ... edge-band decomposition"): fix it in the shared exporter on main, do not edit the kit LEF by hand.

### 1d. History: the tile has never been near closure

| job | result |
|---|---|
| hc_tile-sys-* (ot_hgi_hc_unit, 8 jobs) | EARLY_FAIL_HOLD x3, EARLY_FAIL_SETUP -1,068 ps, FLOORPLAN_MARGIN, bench fail, cancelled |
| hc_tile_ref-c1 | lint fail / cancelled |
| hc_tile_xl-c2-8612208d7 | FLOORPLAN_MARGIN (bank_distance) |
| hc_tile_xl-c3-fb689be40 | TT -266.5, FF -47.2 (stale hold script), DRC 20 |
| hc_tile_xl-c3-fb689be40-hs | REFUSED (y[255] stub) |
| hc_tile_xl-c4-550082537-hs | TT -294.75, FF -21.45, DRC 11 |

c4 did not regress; c3 and c4 are the same design with the same three defects. The CLOSED `hfd_hc_tilexl-cons1011-*`
jobs are block `hfd_hc_tile_xl`, the legacy envelope, not this tile.

## 2. Decision

Setup fails by 295 ps on about 1,200 endpoints in five cones that each cross the tile. That is not a small miss on
a sound block, so no hold cells, no LVT, no SDC change, no outhold cells. The fix is structural and has three parts:
a hardened window leaf, a registered tile boundary on the N and S faces, and a full own-layer OBS in child abstracts.

## 3. Redesign

### 3a. New hardened leaf `ot_hgi_hc_win` (hardened once, 4 instances a tile, identical)

Contents, all per window k:
- `ot_hdc_v41x_weight_window` (4 x `ot_sram_1r1w_128x256_m1_r2c2`, control, `valid`, `received_sectors`).
- Input pin flops, no logic before them: hr lane (v, tag 11, beat 2, data 256), control (start, release, base 35,
  soff 35, nwk 8, own bound 16, next bound 16), read request (w_re, w_addr 16).
- `hbm_base = base + soff` registered in the leaf before the window uses it (cuts the 14-level cone).
- Read decode after the pin flops: `sel = w_addr >= bnd_k && w_addr < bnd_next`, `rom_addr = w_addr - bnd_k`.
- Raw capture `wcap` (1,024) beside the macros, then `rom_q & {1024{sel_q}}` in registered face outputs. The tile
  ORs four leaves (one OR4 level) into `wd`. This removes the `g_sl.oh` select fanout (-46.5 ps today).
- Registered outputs: request (v, addr 35, len 3, tag 7) with a one-credit return, ready, fault.

| quantity | value |
|---|---|
| flops | about 1,950 (wcap 1,024; hr 270; valid 128; pin and control about 250; request, counters about 280) |
| macros | 4 x 94.824 x 41.04 = 15,567 um2 |
| outline (to confirm with `ref_tile gen`) | 216.0 x 151.2 um = 32,659 um2; macro 47.7% of outline |
| signal pins | about 1,470: rom_q 1,024 + sel on the face toward the centre column; hr 270 and request 46 + credit on the N-side face; control 147 on the S-side face; w_re / w_addr 17 toward the centre; ready, fault 2 |
| pin density | rom_q on M4 across a 151.2 um face: 1,025 / 3,150 tracks = 0.33; hr + request on M5 across 216 um: 317 / 4,500 = 0.07 (limit 0.55) |
| clock | own CTS, about 1,950 flops + 4 macro clock pins; insertion exported in the lib and added to `ot_ref_child_ins` in the tile's spine_ins.tcl |
| top layer | M5 for the new leaf (default for new die leaves); the tile then has M6 and M7 free above it |

Its own kit `physical/ref_tile/hc_win_ref` and closure job come first; the tile job consumes its views, as it
consumes `hc_lanes_ref` today.

### 3b. Tile `ot_hgi_hc_tile`

Sub-elements: 4 x `ot_hdc_v41x_hcp_lanes` (unchanged, centre column), 4 x `ot_hgi_hc_win` (west pair, east pair,
y 250..560), 2 x x-memory macros (unchanged, S side).

Flops left at tile level: about 5,700 (r_sum 1,024; sum_out 1,024; wd 1,024; xcap + xd 1,024; x lane flops 600;
u_st 400; new face flops about 600). One spine, under the 8,000 guideline. 11,931 today.

Boundary plan:
- N face: hr_* captured in tile flops at the pins (the existing `hr_dl`, `hr_tl`, `hr_bl`, `hr_vl`, kept), then one
  wire-only hop to the leaf's pin flops (<= 480 um is too far for wire + logic, fine for wire + setup on a full
  period). The 2-entry request FIFO moves to the N face as tile flops, fed by the leaf's registered request with a
  credit; `hq_rdy` then meets only the FIFO pointer and `e0`/`e1` muxes, all local to the pins.
- S face: c_* captured at the pins (kept), one wire-only hop to the leaf's control pin flops. `t_rdy` / `t_flt`
  registered at the S face from the leaves' registered outputs.
- W / E faces: unchanged (TIR 1, TOR 1).
- Rule for every new path: a flop -> wire -> flop hop carries no logic; logic sits between flops inside one element.

Clock plan: tile spine for about 5,700 flops, 2 macro pins and 8 child clock pins, each child balanced with its
exported insertion. Face flops of one face hang from spine leaves of one branch, target arrival spread <= 40 ps a
face (today 89 ps, hold allowance 50). No change to period, uncertainty or hold margin.

Cut numbers (tile level, M4 pitch 48 nm, M5 48 nm):
- leaf -> centre column, per leaf: 1,025 b over 151.2 um = 0.33 of M4 tracks.
- N face: 1,284 pins over 656.64 um of M5 = 0.094. S face: 921 over 656.64 um = 0.067. W and E: 1,066 each over
  725.76 um of M4 + M6 = 0.040.
- N face -> window rows: 4 x 317 b = 1,268 b in two 216 um corridors of M5 = 0.14.

### 3c. Shared tool (main first, then daemon sync): child abstract own-layer OBS

The exporter must cover the child's own top layer completely except pin stubs (no sub-min-space pockets), and
child_lint needs a failing check for an interior own-layer pocket narrower than a legal wire + two spacings. Then
re-export `hc_lanes_ref` views from the existing routed leaf (no leaf re-route). Owner: export-SDC / views stream.

## 4. Cycle delta and what must be re-measured

| change | cycles | where it lands |
|---|---|---|
| read request registered in the leaf (TML 3 -> 4; x path gets a matching stage) | +1 | `SYS_LAT` once, via `TTML` |
| hr lane: tile face flop + leaf pin flop | +1 a response | window fill only |
| request: leaf output register + N-face FIFO | +1 a request | window fill only |
| control and ready / fault relays | +1 to +2 each way | start / release; the parent's S_RW hold must cover it |

Streaming rate is unchanged. Expected case 15 (HC.HC_MIX_POST, the priced scalar POST): 540 -> about 541 to 548
cycles, ratio 1.002 to 1.015 against the immutable 540 (gate <= 1.10, i.e. <= 594). This is an estimate. It must be
measured with the production-shape bench at the c5 source; the 540/540 qualification at 550082537 does not carry over.

## 5. Gates for c5 (none met yet)

1. `ot_hgi_hc_win` leaf: TT >= 0, FF >= 0, DRC 0, child_lint clean, exported insertion.
2. Exporter OBS fix on main; `hc_lanes_ref` views re-exported; child_lint passes with no pocket warning.
3. Tile RTL: Verilator 5.050 lint; `hc_sys_exact` PASS 18 records / 693 words; `mut_mp`, `mut_post`, `mut_xl` FAIL.
4. Case 15 cycles <= 594, recorded against the 540 price.
5. Tile job `hc_tile_xl-c5-<commit>-hs` in the c4 job's shape: TT >= 0, FF >= 0, DRC 0, textbook_lint without the
   clock_domain and boundary warnings. Also fix the two c4 submit warnings: the two runtime part-selects
   (`wqs[wsel_q*W*32 +: W*32]` disappears with the OR; the window's `segment*BURST_MAX+beat` write select becomes a
   decoded one-hot) and the outline utilisation 35.8% (re-derive after the leaves are sized).

## 6. Open points

- Leaf outline and pin faces are computed from macro sizes and counts, not yet from `ref_tile gen`.
- Whether the 4-leaf arrangement keeps the tile at 656.64 x 725.76 (the B2 quarter helper assumes it) is unverified.
- The parent's S_RW hold length and `SYS_LAT` expression need the new terms; the bench decides.
- B2 direction (two SYS bank tiles a quarter): this spec keeps the tile's ports and faces, so it does not change that.
