# FABLE-FIX-S81-COL specs for S81-COL-CLK-IMPL (2026-11-16 00:5x PST)

Owner of the decisions: FABLE-FIX-S81-COL. Implementer: S81-COL-CLK-IMPL. Pilot type: col_h9_r2__t1__clce45cab5__pv7a260fc0.
MEASURED = my STA / logs. INFERENCE is marked. Evidence dirs: epyc7 /srv/opentallas-scratch3/claude/fable-fix-s81-col/an (routed census pv7a260fc0b, CTS reads cts_old / cts_x3, ffh_old / ffh_x3), x1..x3 (CTS experiments); epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-col (f2s_gen.sh, f2s2 = running F2r pilot).

## Spec 0. The four-part clock form: exact diffs (what X3 and the f2s2 pilot kit carry)

All four were applied to a generated kit, after gen, before any stage ran. In main's tools they must come from plan keys.

| # | kit diff (exact) | plan key today | what IMPL has to do |
|---|---|---|---|
| 1 nearest tap | config.mk: delete the lines `export OT_TAP_GROUP_RE = (?:^|[/.])(u_lpad_[A-Za-z0-9_]+)[/.]` and `export OT_TAP_PAIR_AFFINITY = 1`; replace `export OT_TAP_MAX_SINKS = 1500` by `= 3000`. The OT_TAP_PAIR_RADIUS/GROUP/MERGE/UM/DEPTH lines may stay (inert without OT_TAP_PAIR_AFFINITY) | clock.tap_group {re}, clock.tap_pair_affinity {}, clock.tap_max_sinks | rows only (sent to DIE-S81-92 00:4x): drop tap_group and tap_pair_affinity, tap_max_sinks 3000, on the 216 col types. No code |
| 2 ROM lead | core_latency.txt: every row `u_bound.u_u_c<k>_<j> clk 0 grid` becomes `... clk 255 grid` (35 rows on r2; awk: `$1 ~ /u_u_c[0-9]+_[0-9]+$/ && $2=="clk" {$3=255}`). tap_balance.tcl then hangs the ROM clk pin at target - 255 = 195 ps | none | new type key, proposal `clock.core_pin_lead_ps: [{"module_re": "ot_rom_.*", "pin": "clk", "lead_ps": 255}]`, applied in gen_phys.core_latency_files AFTER the rows are built (legacy path and mean-contract path): rise_ps += lead; write the lead into core_latency.json per row (basis "declared_lead"); FF file: lead x 0.81 (FF/TT of BUFx4 chains, MEASURED 21.9 vs about 17.8 ps a stage is not measured: use the ratio of the kit's OT_VCLK_FF / OT_VCLK_TT = 364.5 / 450). schema.py + die_plan.schema.json + one test. The SDC must NOT change: the lead is a physical pin arrival, the ROM has no internal tree |
| 3 early core sources | config.mk: append `export OT_TAP_CORE_ETAP = 1` and `export OT_TAP_CORE_SRC = tree` | none (gen_phys sets ETAP for s81_head hd_tile only) | type key, proposal `clock.core_etap: "tree"` -> gen_phys exports both lines. Without it (X1) 54 of 79 core pins miss the target by up to 190 ps because the tap-root padding also delays the cores; with it 66 of 79 are within 20 ps |
| 4 full-cycle reset relay | rtl/bind_cells.sv: module ot_dp_rrelay_nl body becomes `always @(posedge clk) q <= d;` (gen_phys.reset_relay_full(kit/rtl)) | partition_types[T].reset_relay_full (exists, S81-RCK-4) | rows only: true on the 216 col types |

Numbers to reproduce (CTS stage, 4_1_cts.odb, placement RC, set_wire_rc signal cap x1.45, TT libs, sign-off SDC; script an/cts_sta.sh; FF: an/ffh.sh with core_taps_ff.sdc, 25 ps hold uncertainty, non-port reg starts):

| | TT setup endpoints / WNS | FF hold endpoints / WNS | tap mean insertion | core pins outside +/-20 |
|---|---|---|---|---|
| wave kit attempt_2 | 1,476 / -380.6 | 1,712 / -137.8 | 247..744 | 12 of 79 |
| X1 (1 + 2) | 138 / -217.0 | not read | 387..518 | 54 |
| X3 (1 + 2 + 3) | 144 / -199.8 | 108 / -70.6 | 387..481 | 13 |

Accept test for the IMPL branch: a kit generated from the main tree with the keys has byte-equal config.mk lines and core_latency.txt rows to the table above, and its 4_1_cts.log ends with tap means inside 380..490.
Caution: do not hang the s<k> cores earlier (S lead). X3 carried +40 on s10/s12: go_tag -182 -> -128 but e<k>_u_w sh_free -> s ef went -61 -> -120. Zero-sum; leave s at the target.

## Spec 1. Reset copies (u_d<n>_6_Y): two-level copy tree

MEASURED routed: u_d7_6_Y.q -> u_d7_6_Y_r<k> 19 endpoints, worst -151.2: 1,246 um, 21 buffers, 729 ps data, launch-minus-capture clock 185. Copy -> RESETN of u_y_rt_24a_5: 55 endpoints, -106.2, 867 um, 717 ps. X3 (clock fixed, unrepaired): -199.8 on 22. So it is distance: one flop (last stage of ot_dp_dly D=6, placed where GPL puts it, (1045,170)) feeds 68 region copies over a 1,443 x 1,227 um type in one cycle.
Form: reset_replicate gains a second level. Driver `ot_dp_dly #(.W(1),.D(n)) u_x` becomes common part D(n-2), then one ot_dp_rrelay per COARSE region (grid 600 um: at most 3 x 3), then one ot_dp_rrelay per FINE region (grid 300, as today) fed by the coarse copy of its cell. Stages from S to every load stay n (same LATCHECK, same bind_verify transport count). Requires n >= 3; on n = 2 keep today's form.
- Plan key: reset_replicate[i].coarse_grid_um = 600 (absent = today's single level, byte-identical).
- Names: u_x_c<ix>_<iy> (coarse), fine copies keep u_x_r<k>.
- Hops (geometry, INFERENCE at the measured 0.71 ps/um routed): common -> coarse <= 900 um only if the common flop sits in a corner; coarse -> fine <= 600 um = 426 ps; fine -> load <= 600 um. To bound the first hop, the common part's last flop and the coarse copies need sites: emit for each coarse copy a FIRM site at the centre of its cell (istations.tcl / relay_mid style, existing OT_RELAY_MID hooks), and none for the common part (GPL then puts it at the centroid of 9 fixed sinks: <= 720 + 610 = 1,330 um corner to corner halves to <= 665 um).
- If the first hop is still over 600 um on the pilot: move one more stage down (common D(n-3), a 2 x 1 mid level). n = 7 leaves room.
Accept: pilot at sign-off, no endpoint of u_d*_Y* below -42 TT; FF hold >= 0 on the copy chain; LATCHECK 873/873; G0 no new functional error.
Rows: DIE-S81-92 (reset_replicate rows of the 216 col types get coarse_grid_um 600 after the tool merges).

## Spec 2. go_tag (cfg7_seq s<k> -> element half e<k>_u_w/go_tag, falling-edge capture)

MEASURED routed: 4 endpoints on r2 (2 nets x 2 bits... s12 -> e12_u_w -119.8, s10 -> e10_u_w -101.1), sibling kit -142.6. Path: s clk pin 174, clk -> go_tag 383 (uncompensated core insertion 271 + clk-q), net 444 um with 7 buffers 260 ps, element clk_c pin at -65 (falling edge at 351), library setup 346.5. Same face on r2, IFN = 1: cfg_d worst -2.7, xs_q0 +0.8, xs_q1 +8.0 (4,832 pins per type sit at the edge of the gate). h10 types are worse (FABLE-PD-S81-1515: -94 PE).
Decision: the structural form is the full-cycle input face, IFN = 0 halves (Spec 3). It gives 416.5 ps to all 4,832 pins. Not chosen: s earlier (zero-sum with ef, see Spec 0 caution); a station (+1 cycle on 13 families); net repair alone (needs 0.32 ps/um on 444 um, INFERENCE not reachable below 0.5).
Until the halves exist, one kit-side step is still needed on IFN = 0 too (go_tag[1] nets are 36 fF, slew 142 in h10): the 16 go_tag nets per type get a max-length rule of 60 um in the kit (OT_MAXWIRE_UM applies 100 to all nets; add a per-net-pattern override, proposal env OT_MAXWIRE_NETS_RE='go_tag' OT_MAXWIRE_NETS_UM=60 read by grt_maxwire.tcl). IMPL: small tcl change + test; rows = item_env on col types.
Accept: with IFN = 0 halves, face setup >= -42 TT on every element input pin at sign-off, FF non-port hold >= 0.

## Spec 3. IFN = 0 element halves (hw / he), stopped at the hold limit

State MEASURED (epyc10 /srv/opentallas-scratch2/claude/s81-gotag-setup-1115/core/hwC, heC; branch claude/s81-gotag-setup-1115 @39e537ae34 has `.IFN(0)` in delta_romq_split_1106.py and the 4 col frame sources): both stopped in do-5_1_grt at `OT_HOLD_STRUCTURAL stage=grt: FF hold ws -152.00 ps, 2705 true failing endpoints (limits: ws >= -100 ps, endpoints <= 2000)` (he: -164.56, 2,846). TT setup at that point +0.8 / -4.7 (SS label in the log line). Input contract used: in_min -81.26 (earliest FF data change +280 ps after the core clk pin, vclk_FF 361.26), in_max 617.61.
Cause: the rising-edge capture flops of the input face sit at the core's full insertion (FF 282-324 hw, 403-474 he), data may change at +280. That is a real hold need of up to about 190 ps on about 2,400 inputs per half, not a tool artefact.
Form (two parts, both in the half-core kit, no RTL change beyond .IFN(0)):
 (a) Input-face flops on a shallow clock branch. The face flops (the first rising-edge flop behind each data input pin) get their clock from an early point of the core tree so that their insertion is 300-370 ps TT (hw: leave at its 330-390). Mechanism: the kit's pin-register hooks (pin_reg_split.tcl / ot_pin_regs.tcl / pinreg_pad.tcl: IMPL to confirm the exact knob; if none fits, a clock_taps-style re-hang of the listed CK pins onto the level-2 clock net before CTS). Effect, arithmetic on the measured numbers: he hold need 474 - 280 = 194 falls to about (370 x 0.81) - 280 = 20 ps; setup at the face: data latest at next edge + 250 against capture at 833 + 300 = +283 before library setup; face flop -> core logic loses up to 185 ps of its cycle (the he half had +24.7 TT before: read this, it is the risk).
 (b) Remove the structural stop for these two kits: OT_HOLD_STOP_PS = -1000000 and the endpoint limit off (owner 11-14: such limits are deleted; the S81 wave die_gen_env already carries OT_HOLD_STOP_PS). The residual (<= 60 ps on the inputs) is padded by the normal FF hold repair inside the macro.
 Order: (b) alone is NOT the form (190 ps x 2,800 inputs = about 15,000 delay cells in a half that closed at +24.7).
 Contract: keep in_min -81.26 / in_max 617.61; go_tag pins in_max +50 more (arrive up to next edge + 300).
Accept per half: DRC 0, TT setup >= -42, FF non-port hold >= 0, lib setup_rising / hold_rising on every data input (no falling arcs left), tb_qxpq_go_boundary IFN 0 and its mutant PASS, LEC. Then DIE-S81-92 takes the two views + the .IFN(0) branch as F2b rows; the type pilot r2 is regenerated on them.
If (a) costs the half its internal setup: fallback = keep the face at core depth, split pads half in the macro (to 100 ps) and half as a later parent tap for the senders bs<k> / s<k>-go_tag only (declared pin offset, like Spec 0 row 2, +90 ps on dsfd_qbank_S ck); bs -> element setup had +0.8 routed at IFN = 1, so +416 covers it.

## Not decided here
- Element e<k>_u_w sh_free / bank_free -> s<k>/ef: +43.7 routed at baseline, -52..-61 at X1 CTS unrepaired (412 um nets, 2 buffers). Expected to close with TT setup repair on the main tree; read on the main-tree pilot before any action.
- Hold after the four-part form at route: 108 endpoints, -70.6 at CTS before any repair. Read at sign-off.
