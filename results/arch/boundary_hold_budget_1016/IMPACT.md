# Boundary hold budget: impact study (STA only, no re-routes)

**Method**
- Tool: `bh_probe.tcl` (OpenROAD/OpenSTA, `openroad/orfs:asap7lock`), run on EPYC4 through ot-run.
- Inputs per route: its own `6_final.odb` + SPEF + `6_final.sdc` + the route's `signoff.sdc`.
- Timing is checked at FF hold and TT setup, before and after the proposed boundary min delays (C = U = 25 ps).
- Every input→D and register→output path is traced, and the delay of the cells on it is attributed to hold padding (HB* and BUF instances named `*hold*`), other buffering, or logic.
- Capture/launch after the rule = the native S+R / O−R from the view's TT Liberty, minus the padding the new requirement no longer needs (pad × min(1, FF slack-after / pad)). No other change is assumed.
- Views: 82 views bound by (or candidates for) the current die contracts, plus COLL ctl2 v7. 44 probed; the rest have no routed ODB left (EPYC1 retired) or no run.

## 1. Closed tiles stay closed (hold only relaxes)

- 43/44 views: input→register and register→output FF hold slack each rose by exactly C+U = 50 ps, and register-to-register is unchanged. Setup lines are untouched (TT identical by construction).
- Exception: qkd_cdc_wleaf (physical/ref_tile/qkd_cdc_wleaf_ref/views/qkd_cdc_wleaf). FF before {'ws': 1.7190415757539768e-13, 'i2r': 1.417394, 'r2o': 5.51173, 'r2r': 0.171904}, after {'ws': -8.787973126977988e-11, 'i2r': 66.491508, 'r2o': -86.343987, 'r2r': 0.171904}. This is a CDC leaf: its second clock's ports were given the core_clk credit by the probe. It is outside the rule (section 4: single synchronous clock).
- Views with FF WNS < 0 before / after (qualifying): 0 / 0.

## 2. In-die native-FAIL views: which fail only because of hold padding

| class | views | meaning |
|---|---:|---|
| A_padding_only | 3 | every over-budget pin passes once the surplus padding is gone. A re-route under hold_budget die is expected to pass native |
| B_insertion_spread | 10 | boundary spread > 80 ps or early capture clock (S+R far above the port→D delay). Needs re-tiling or a clock split, not this rule |
| B_logic_at_pin | 4 | logic cells between pin and register: the pin is not registered. Needs an RTL pin register |
| B_pinflop_wire | 8 | a buffered wire (the inhold pad/driver at the pin, then 100–150 ps TT of wire) before the flop. This is the same mechanism H-REACH measured as the slew limit. The rule's flop-first pins (inhold=false, flop anchored at the pin) remove it structurally, but this STA cannot prove it: a re-route under hold_budget die must confirm |

| class | cell | view | spread | capture now → est. | launch now → est. | over-budget input pins by cause | over-budget outputs by cause |
|---|---|---|---:|---:|---:|---|---|
| A_padding_only | dsfd_su_t_pin | s81su_pinns_ref | 62.9 | 188.9 → 187.4 | 240.2 → 164.6 | {} | {'pad': 426} |
| A_padding_only | ot_hgi_coll_ctl_v5_q2 | hcoll_v5_ctl2 | None | 197.3 → 133.1 | None → 173.9 | {'pad': 1} | {} |
| A_padding_only | ot_hgi_sv_lane2 | hgi_sv_lane2_pf | 41.5 | 175.5 → 175.5 | 230.2 → 166.2 | {} | {'pad': 4} |
| B_insertion_spread | dsfd_coll_cbr | dsfd_coll_cbr_m5 | 27.6 | 225.8 → 225.8 | 322.2 → 322.2 | {'wire_buffer': 39} | {'wire_buffer': 136, 'pad': 1, 'clock': 1} |
| B_insertion_spread | dsfd_coll_ces0 | dscoll_ces0_cxsp | 90.6 | 450.2 → 450.2 | 317.9 → 317.9 | {'wire_buffer': 39} | {'pad': 12, 'wire_buffer': 37} |
| B_insertion_spread | dsfd_coll_ct | dsfd_coll_ct_rt | 88.6 | 515.9 → 515.9 | 367.6 → 367.6 | {'pad': 129, 'wire_buffer': 957, 'clock': 8} | {'wire_buffer': 711, 'clock': 19, 'pad': 21} |
| B_insertion_spread | dsfd_mtp_hrow_cbe | hrow5_cbe_cx | 98.5 | 505.9 → 427.4 | 399.0 → 83.5 | {'wire_buffer': 680, 'clock': 180, 'pad': 10} | {'pad': 971} |
| B_insertion_spread | dsfd_mtp_hrow_cbw | hrow5_cbw_cx | 89.2 | 440.4 → 440.4 | 422.8 → 76.5 | {'wire_buffer': 823, 'clock': 131, 'pad': 8} | {'pad': 991} |
| B_insertion_spread | dsfd_su_t_qbe | s81su_qbe_sp8_ref | 82.4 | 375.6 → 375.6 | 406.4 → 364.8 | {'wire_buffer': 176, 'clock': 4} | {'pad': 96, 'wire_buffer': 87} |
| B_insertion_spread | ot_p2h_head | p2h_head_ref | 181.4 | 289.2 → 289.2 | 413.1 → 413.1 | {'logic': 3, 'wire_buffer': 23, 'pad': 503} | {'wire_buffer': 253, 'clock': 7, 'pad': 71} |
| B_insertion_spread | ot_s81_hc_crootr_f | s81hc_crrfw_ref | 71.2 | 497.0 → 497.0 | 429.2 → 429.2 | {'wire_buffer': 2836, 'clock': 2} | {'wire_buffer': 2281} |
| B_insertion_spread | ot_s81_hc_crootr_r | s81hc_crrrw_ref | 101.5 | 393.3 → 393.3 | 365.6 → 365.6 | {'wire_buffer': 1628, 'pad': 29} | {'wire_buffer': 591, 'clock': 122, 'pad': 99} |
| B_insertion_spread | ot_s81_hc_cseq | s81hc_cseq_ref | 34.1 | 162.5 → 162.5 | 263.7 → 263.7 | {} | {'wire_buffer': 66, 'clock': 1, 'pad': 2} |
| B_logic_at_pin | dsfd_su_t_swe | s81su_swe_sp8_ref | 46.1 | 294.2 → 294.2 | 266.4 → 266.4 | {'logic': 62, 'pad': 18} | {'wire_buffer': 28} |
| B_logic_at_pin | ot_hgi_seq_be | hgi_seq_be | 27.0 | 255.1 → 255.1 | 337.4 → 196.0 | {'logic': 13, 'pad': 4} | {'pad': 1538} |
| B_logic_at_pin | ot_hgi_seq_fe | hgi_seq_fe | 49.2 | 311.8 → 311.8 | 358.1 → 335.0 | {'logic': 1, 'wire_buffer': 1} | {'logic': 35, 'pad': 273} |
| B_logic_at_pin | qkd_cdc_wleaf | qkd_cdc_wleaf_ref | 35.6 | 397.0 → 397.0 | 173.2 → 164.5 | {'logic': 1} | {} |
| B_pinflop_wire | dsfd_coll_cbq0 | dsfd_coll_cbq0_m5 | 46.3 | 218.6 → 218.6 | 247.6 → 247.6 | {'wire_buffer': 2, 'pad': 1} | {'wire_buffer': 2} |
| B_pinflop_wire | dsfd_qbank_S | s81fill2_qbank_s | 12.8 | 303.5 → 272.6 | 222.1 → 119.0 | {'wire_buffer': 1} | {'pad': 2} |
| B_pinflop_wire | dsfd_vm_be_sl | dsfd_vm_be_sl | 27.8 | 258.7 → 258.7 | 214.4 → 121.9 | {'pad': 2, 'wire_buffer': 1} | {} |
| B_pinflop_wire | ot_hdc_v41x_idx_hslice | ot_hdc_v41x_idx_hslice_m5 | 46.5 | 205.3 → 205.3 | 216.2 → 196.5 | {'wire_buffer': 3} | {} |
| B_pinflop_wire | ot_hgi_sv_lane2 | hgi_sv_lane2 | 38.6 | 451.8 → 451.8 | 344.1 → 191.7 | {'wire_buffer': 3} | {'pad': 696} |
| B_pinflop_wire | ot_s81_hc_crootr_w | s81hc_crrww_ref | 45.4 | 276.4 → 276.4 | 250.6 → 250.6 | {'wire_buffer': 1213} | {'wire_buffer': 81} |
| B_pinflop_wire | ot_su12_sfu | sfu_lane_ring3_rt | 23.4 | 417.6 → 417.6 | 242.2 → 62.8 | {'wire_buffer': 2} | {'pad': 7} |
| B_pinflop_wire | qkd_embgw | qkd_embgw | 69.6 | 178.8 → 178.8 | 312.0 → 226.6 | {} | {'pad': 1071, 'wire_buffer': 1} |

Not probed (38; routed ODB gone with EPYC1, or no run): dsfd_coll_ces0, dsfd_coll_cesn, dsfd_coll_lane_w, dsfd_mtp_hrow_ing, dsfd_su_t_ctl, dsfd_su_t_kvp, dsfd_su_t_kvq, dsfd_su_t_pin, dsfd_su_t_qbe, dsfd_su_t_qbt, dsfd_su_t_swe, dsfd_vm_be_sl, hgi_mtp_native, ot_hcoll_port, ot_hdc_v41x_idx_hslice, ot_hgi_coll_tkm_tile, ot_hgi_dma_back, ot_hgi_sv_head, ot_s81_hc_ccf, ot_s81_hc_ccr, ot_s81_hc_cntree, ot_s81_hc_cpin, ot_s81_hc_crootr_r, ot_s81_hc_crootr_t, ot_s81_hc_crootr_w, ot_s81_hc_crooty_w, ot_s81_hc_crx, ot_s81_hc_cseq, ot_s81_hc_pad_f8, ot_s81_hc_pad_meta2, ot_s81_hc_pad_r5, qkd_kvwq_leaf_s_w129_m

## 3. Native-PASS views: the margin returned

| cell | capture now → est. | launch now → est. | removable input pad FF ps (total) | removable output pad FF ps (total) |
|---|---:|---:|---:|---:|
| dsfd_mtp_hrow_hub | 180.2 → 132.0 | 198.5 → 144.3 | 71183 | 23 |
| dsfd_qbank_N | 184.5 → 184.5 | 121.3 → 80.5 | 0 | 3485 |
| dsfd_qbank_S | 132.3 → 120.9 | 182.1 → 159.7 | 4671 | 31184 |
| dsfd_su_t_kve | 128.0 → 128.0 | 155.5 → 108.0 | 2632 | 6103 |
| dsfd_su_t_kvr | 124.2 → 113.8 | 183.1 → 183.1 | 3505 | 1635 |
| dsfd_su_t_kvt | 169.4 → 117.2 | 219.2 → 111.2 | 64422 | 300075 |
| ot_hgi_seq_au | 169.7 → 169.7 | 213.4 → 73.0 | 397 | 0 |
| ot_s81_hc_caq | 123.4 → 123.4 | 183.7 → 135.7 | 0 | 550 |
| ot_s81_hc_ccr | 129.6 → 129.6 | 188.6 → 154.4 | 339 | 16602 |
| ot_s81_hc_cntree | 128.6 → 107.5 | 149.5 → 77.2 | 14857 | 1628 |
| ot_s81_hc_crootr_f | 180.2 → 138.9 | 192.5 → 102.1 | 70402 | 171965 |
| ot_s81_hc_crootr_f | 181.1 → 138.2 | 190.8 → 105.3 | 78538 | 183670 |
| ot_s81_hc_crx | 133.3 → 133.3 | 217.7 → 217.7 | 3343 | 20651 |
| ot_s81_hc_cryys | 165.6 → 165.6 | 197.3 → 105.4 | 0 | 16778 |
| qfd_chead_e | 186.6 → 159.8 | 192.3 → 122.4 | 10402 | 88919 |
| qfd_chead_w | 184.9 → 154.5 | 191.0 → 154.2 | 8537 | 87281 |
| qfd_cst_n | 162.5 → 148.2 | 197.2 → 197.2 | 8360 | 52307 |
| qfd_cst_s | 161.0 → 141.0 | 189.7 → 103.2 | 8029 | 60112 |
| qkd_kvwq_ctl_bin | 160.5 → 131.2 | 197.3 → 158.6 | 15167 | 26065 |

## 4. Die side: hold buffering the budget implies

- Neighbour skew Δ = 0 ps (sender earlier than receiver by Δ): 28/62210 receiving pins need die-level delay. Mean 0.0 ps FF per pin (≈ 0.00 HB4xp67), max 5.1 ps.
- Neighbour skew Δ = 40 ps (sender earlier than receiver by Δ): 4583/62210 receiving pins need die-level delay. Mean 0.4 ps FF per pin (≈ 0.01 HB4xp67), max 45.1 ps.
- Neighbour skew Δ = 80 ps (sender earlier than receiver by Δ): 38368/62210 receiving pins need die-level delay. Mean 13.4 ps FF per pin (≈ 0.35 HB4xp67), max 85.1 ps.
- Today, tile-level named hold padding on these views is 709 ns on 62762 inputs (11.3 ps/pin) and 1618 ns on 43751 outputs (37.0 ps/pin), at FF.
  - Every link pays sender-out plus receiver-in padding unconditionally.
  - These figures count only cells named as hold padding. Structural pads re-sized by the flow and repair BUFx2 chains not named `hold*` are excluded, so the true figure is higher.
- Unpadded receiver hold need (H−R at FF after removing surplus pads): worst per view max 5.1 ps, median of view medians -64.2 ps.

**Theoretical bound for a fully re-routed flop-first pin.** The measured rows above still carry the routes' residual non-pad buffering. A flop-first pin has:
- input→D at FF of about 5–15 ps (wire only);
- capture-flop offset (c − L_min) of at most about spread/2;
- t_hold of about 0–10 ps.

So need ≈ +10 ps worst. At Δ = 80 ps that means about 90 ps FF (about 2.4 HB4xp67, or a relay launch-min of about 115 ps) on each such link bit, and 0 at Δ ≤ ~0. Forwarded-clock F1 hops have Δ matched by construction, so they need ≈ 0.

This is placed once per link, in the relay station or a die-net hold cell, and only where die FF STA reports a shortfall. Today two pads are paid on every link: about 11 ps/pin on inputs plus 37 ps/pin on outputs, counting only cells named as hold padding, which undercounts.

## 5. Notes

- Launch estimates for 3 of the 3 class-A views and 17 other views (22243 outputs) come from the views' FF Liberty, not from traced paths, because the probe's output trace failed with STA-2201 on those tiles (see `launch_lib_estimated` in impact.json). The estimate removes 1.4 × max(0, FF launch-min − 40 ps), where 40 ps ≈ DFFHQNx1 clk→QN plus INV at FF and 1.4 is the TT/FF pad ratio used by `hbm_die_relay_sta.py`. These estimates are indicative only and are never used to bind.
- 30 in-die native-FAIL views and 8 PASS views were not probed:
  - 24 had routes on the retired EPYC1;
  - 6 have no ODB left in their run directories.
- Probe sources are in `probe/` (bh_probe.tcl, bh_run.py, analyse.py, report.py, libscan.py, etm_probe.tcl/etm_run.sh).
