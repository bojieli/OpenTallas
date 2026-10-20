# QW-DIECLASS 10-19: Qwen compute die GRT / STA / CLK failure classes

Lane QW-DIECLASS (parent LEAD3-QW). This is a read-only analysis of existing fleet reports. Nothing was rerun.

- Run of record: **dv2f19g2** (GEN2, src a5ea12ae2), `ot-epyc6:/srv/opentallas-scratch/claude/mu-die-qw/dv2f19g2/chain`.
  - GRT overflow 7089.
  - TT WNS -14320 ps, with 80125 of 320046 endpoints violating.
  - FF worst -16501 ps, with 102008 endpoints violating.
  - QCLK rA FAIL (intra / landed / drift).
  - HOLD BUDGET FAIL.
- Comparison: **dh2diag1** (dv2f18dh2 diagnostic), `ot-epyc6:/srv/opentallas-scratch/claude/qw-diechain2/dh2diag1/chain`.
  - TT -9818 ps, with 17246 endpoints violating.
  - FF -19170 ps, with 96204 endpoints violating.
- dv2f19g2j (B variant) died after the dieclk FAIL, with no GRT (DIE_REPAIR FAIL). GEN3 supersedes it. It is recorded here only and was not relaunched.
- GEN3 **dv2f19g3r** is alive on ep6 (unit oth-ubuntu-2592872; PDN docker 2 h, at PGCHECK VSS at 21:25). Its STA is to be classified against this table.

## Root cause (one structural defect explains GRT M4, CLK intra, and most of the STA)

The rA die clock tree (`chain_dieclk.sh`, forwarded spine `clk_rx/pll_d2d[0]`, 766 region trees, "local_root median") builds region-tree leaf nets that run straight across hard blocks without buffers.

- `die_repeaters.long_wires.rpt` lists **281 `dc_r*` clock nets longer than 1 mm**:
  - 119 of them are longer than 2 mm.
  - The worst is `dc_r343_L1/Y`, 2471.8 um. That equals the width of a CB16 column (2445 um).
  - These wires have up to 9.8 ns of wire delay each.
  - `ckb_rom/pll_ck[0]` adds 2837.8 um / 12.96 ns.
- die_repeaters skips clock pins, so nothing ever buffers these nets.
- The tool names them `n_dc_*`, and `grt.tcl` marks only `^n_(clk_|fck_|rst_)` as special. So the signal router routes them as signals, straight through capacity-0 M4 gcells.
- Consequences:
  - Regions r17-r19, r24-r27, r32-r35 and r123 have 16 CB16 `ck_c#r#` pins plus rst_field repeaters. They get insertion of 29-34 ns, against a spine median of 17-19 ns. Slices sit at 19-24 ns.
  - The rst_field-only regions at x = 9.4 / 24.3 mm (r114, r219, r225, r234, r343, r350, r656, ...) get 26-33 ns.
  - Neighbour regions therefore differ by 3-15 ns. Every unlanded link between them fails TT setup or FF hold by that amount.
- Example: `c16_E3_2` (region r34) has an arrival of 33.7-33.9 ns, while the abutting `dvs_E3` (r109) is at 22.8 ns. Hence CB16 -> SLICE2E fails TT by -10574 ps, and SLICE2E -> CB16 fails FF by -8866 ps.

GRT 7089 is identical in dv2f19g2 and dh2diag1, but the two runs are not on the same placement:

| | dv2f19g2 | dh2diag1 |
|---|---|---|
| floorplan_pdn.odb md5 | 4665728236ee | f8c7e41996b2 |
| Routed nets | 645474 | 671209 |
| Wirelength | 146.29 m | 146.65 m |
| Per-layer demand | differs | differs |

The overflow is still identical because it is structural. The 2D congestion report contains the same 5058 edges in both runs, and they belong to the same 10 die-clock nets on the same 5 y rows. Both runs build that clock-tree geometry the same way, and it does not depend on the signal placement.

## Class table (dv2f19g2; counts = violating endpoints; worst in ps; dh2diag1 in brackets)

| class | count TT / FF | worst TT / FF | example path | fix lane |
|---|---|---|---|---|
| **GRT-G1** die-clock leaf nets `n_dc_r{234,350,343,225,114,219}_L*` (10 nets, ~506 gcells each) routed across capacity-0 M4 gcells over CB16 columns, rows y=2.1/7.5/8.8/15.4/16.7 mm | M4 5050 + M5 8 = 5058 overflow [identical] | cap 0 / usage 1 | `n_dc_r234_L11` (8059,16699) | QW-GEN3 die_clock_config: block-aware region trees, leaves in channels or on M7+, buffered every 160-405 um; make `n_dc_*` special/CTS-routed |
| **GRT-G2** M6 1315 (max H 46) and M8 716 (max H 38): 3D layer-assignment overflow, not in the 2D rpt. route.guide density is hottest on the SERDES0 597-bit relay buses `n_serdes0_{rx,tx}__r2/r3` at x 0.78-0.92 mm, y 14.1-15.1 mm (rlyh/landh_597 104x60 faces) and on `n_lnk_x3__r2` at (0.29, 23.0) mm. Location is inferred, not measured | 2031 overflow [identical] | - | `n_serdes0_rx__r2` 168 guides/gcell M6 | QW-GEN3 relay plan: split 597-bit relays / widen faces (<=6 pins/um) |
| **CLK-C1** intra-region spread > 80 ps, 38/655 regions: CB16-column regions r17-19, r24-27, r32-35, r123, plus rst_field regions r114/r219/r225/r234/r343/r350/r656 | 38 regions | r32 435/533, r34 461/528, r33 452/514 | `dc_r343_L1` 2471.8 um, 9.8 ns | QW-GEN3 die_clock_config (same fix as G1) |
| **CLK-C2** landed FAIL: 446 owed links / 186347 neighbour bits, 8 no-root | 446 links | - | land_owed_rA.json | QW-GEN3 / QW-SLICE3 (182 slice-pair in-face owed) |
| **CLK-C3** lane drift > T/2 on 3/153 lanes | 3 | 424.6 | `dvw_io_collective_cmd_free` | QW-GEN3 die_clock_config (forwarded-lane tap) |
| **STA-1** CB16 <-> SLICE2 links (both stand-ins); neighbour-region skew from C1 | 26752 / 46428 | -10574 / -8866 [-9068 / -7610] | `c16_E3_2/rs[117] -> dvs_E3/rs_n0[117]` | QW-GEN3 clocks (C1) + QW-CB16FULL landed parent (A0 leaves: QW-CLUSTER3-A0) |
| **STA-2** CB16 <-> CB16 (adjacent instances in a column on different regions, e.g. W5_2 r2 23.3 ns vs W5_3 r3 20.3 ns) | 22692 / 25007 | -2607 / -2463 [-326 / -807] | `c16_W5_2/bco2[146] -> c16_W5_3/bc2[146]` | QW-CB16FULL (landed inter-instance crossings) + QW-GEN3 clocks |
| **STA-3** SLICE2 <-> SLICE2 chain (dvs_Wn <-> Wn+1, E <-> W) | 22602 / 24922 | -2545 / -2480 [TT 0 / -312] | `dvs_W1/cmd_eo[108] -> dvs_W0/cmd_wi[108]` | QW-SLICE3 (landed slice parent) + QW-GEN3 clocks |
| **STA-4** reset-field repeater hops across regions (`rstt_rst_field` -> rst_field / CB16 / slice / land), launched in 33 ns regions, captured in 18.7 ns regions 25 um away | 431 / 1081 | **-14320** / -11998 [-9818 / -8611] | `rstt_rst_field_8619 (r33, 33.5 ns) -> rstt_rst_field_8620 (r629, 18.8 ns)` | QW-GEN3: rst_field clocks from the local region (C1 fix) + Q.STA.GEN.7 |
| **STA-5** reset seq/io/sync into foreign clocks (rst_io -> serdes/relays, rst_seq_ctlm, rstseq -> rst_io, rstsync -> fwd_s) | 18 / 28 | -2102 / -2010 | `rstt_rst_io_2 -> io_serdes_1/rst_n` (stream 21.3 ns vs serdes 18.9 ns) | QW-GEN3 Q.STA.GEN.7 (reset landing); seq_ctlm hops -> QW-CTLM5 |
| **STA-6** die relay -> landing chains (`rly_dvw_*` lanes) | 2246 / 2 | -2951 / -7 [-2288] | `rly_dvw_st_wi_21/b[656] -> rly_dvw_st_wi_22/a[656]` | QW-GEN3 / QW-SLICE3 landings (Q.STA.GEN.8) |
| **STA-7** collective IO (stand-in) <-> serdes-face relays/landings (face_ck serdes 19.3 ns vs stream) | 1711 / 1196 | -1872 / -1447 [-358 / -421] | `io_collective/out_data[373] -> rly_dvw_rd_wi_0/a[373]` | QW-GEN3 landings (Q.STA.GEN.1 / .8) |
| **STA-8** slice2_e x0 face -> hop-0 landings | 1102 / 0 | -820 / - | `dvs_E0/ard_eo[2] -> rly_dv_x0_ar_ard_0/a[2]` | QW-SLICE3 (182 in-face owed) |
| **STA-9** d2d_rom edge (stream__early group; land/ucie_kv <-> d2d_static) | 2448 / 1685 | -256 / -217 [-250 / -217] | `rly_lnk_x3_1/b[61] -> d2d_rom/x3[61]` | QW-GEN3 Q.STA.GEN.2 early tap d2d_rom |
| **STA-10** sys_face / embed_prov relays | 123 / 1060 | -78 / -181 | `embed_prov/embed_code_q[504] -> rly_dvw_embed_prov_*_0` | QW-GEN3 Q.STA.GEN.2 sys_face tap |
| **STA-11** CDC ucie (0.9 ns) -> stream (17.4 ns) into collective IO stand-in, unlanded | 0 / 1 | - / **-16501** [-19170] | `io_ucie/tx_up -> io_collective/ucie_up[0]` | QW-GEN3 clock contract: landed crossing for ucie_up |
| **STA-12** landing -> SERDES PHY hold | 0 / 597 | - / -13 | `rly_serdes0_tx_2/b[155] -> io_serdes/tx_flit[155]` | QW-GEN3 io_hold_margin >= 0.03 on serdes landh_597 |
| **STA-13** n59 kv slot | 0 / 1 | - / -5 | `rly_lnk_kv_x3_slot_2 -> native59/kv_x3_slot[0]` | QW-N59-4 |
| **REACH** over_reach(425) 642 nets | 642 | 600 um | sys_face 353 (<=590 um), `rly_dvw_tt_ctlm_*` 125 (<=600 um), dc_ 326 (clock), others 38 | ctlm lanes -> QW-CTLM5; sys_face -> QW-GEN3 relay plan; dc_ -> G1 |
| **HOLD-BUDGET** SKEW_GT80 93 link classes, 250 skew_fail, 415 tap_mismatch, 95 violators | - | demand 134.8 ns | slice2_e -> c16 (12 links, 8890 ps delta) | consequence of C1 + C2 (QW-GEN3) |

Both totals check out: the TT rows sum to 80125 and the FF rows to 102008.

Other lanes:
- Stream (QW-STREAM2) has no class of its own here. Stream and tload are not bound in GEN2: they are inside the SLICE2 stand-in (Q.STA.SLICE.3).
- A0 leaves are inside the CB16 stand-in.

## dv2f19g2 vs dh2diag1

TT got worse in dv2f19g2: 80125 violators against 17246.
- The new failures are CB16-CB16 (22692 vs 2578) and SLICE-SLICE (22602 vs 0).
- dh2diag1 ran with clock rC. dv2f19g2 runs rA (forwarded spine with region trees).
- rA puts adjacent CB16 / slice instances on separate region trees, and those trees differ by up to 15 ns. So the rA clock config is the regression.
- GRT is unchanged between the two runs, and so is the long-wire set (identical counts).

## Data

- `data/sta_classes_<run>_<tt|ff>.tsv`: class, violating/total endpoints, worst slack, example path.
- `data/clock_regions_dv2f19g2.txt`: the 30 slowest regions, with median arrival, spread, bbox and sink families.
- `data/grt_m4_overflow_dv2f19g2.txt`: 2D congestion nets and rows.
- `scripts/`: the parsers that ran on ep6 (python3 -I, read-only):
  - `sta.py`: grt_*_summary.rpt + blocks.tsv + bind.json no_view.
  - `cong.py`: congestion rpt.
  - `reg.py` / `arr.py`: rA arrivals_tt.tsv + clknets.tsv.
  - `guide.py`: route.guide density.
  - `tree.py`: spec_rA trees.
