# S81 DeepSeek ROM layer die: die-level iteration

Lead: s81-die-iter (log /home/ubuntu/claude-takeover-20261007/el1011-s81die.log, prefix [s81-die-iter]).
Contract: results/arch/hier_contract_1011/s81.json, v13 (HC split around the corridor; v7 at a82dfd1c6). Generator: tools/dsrom_s81_fulldie.py (gen r8 / rev r9).
Recipe: s81_layer1_v4.opts (= v3 + --relay-progress --sstn-ccpad --pin-need), plus --cfifo-colck added by the chain.
Chain: tools/s81/die_iter_chain.sh: GEN -> clock plan (clock-only CTS, tools/budgets/clock_plan.py) -> balanced kit
(tools/s81/die_sta.py) -> PLACE -> full-die GRT -> STA TT / FF / SS on the GRT parasitics + IR on the spine and field windows.
Die checklist (academic validation, no flat DRT): legal floorplan from real abstracts, GRT overflow 0, TT setup >= 0,
FF hold >= 0, IR <= 35 mV, channels >= 20 um (the hub column abut gaps are 21.6 um).

## Plan (i3, layer1, 2026-10-12 02:30 PT, source 4c8acb002)

| check | result |
|---|---|
| overlaps / outside the die / pin clashes | 0 / 0 / 0 |
| instances | 58,338 |
| placed area | 409.4 mm2 (47.7 % of the die) |
| hub column | re-stacked: SU (W-grown, top 9,439.2) / 21.6 / VM 9,460.8-12,191.0 / 21.6 / capture 12,212.64 / 21.6 / gather 12,363.84 |
| contract | v7: sp_vm h 2,730.216 (VM FE v5), capture / gather / wfc / collective origins +120.96 um, rep/hrow 2,998.08 x 1,769.04 |
| SU-VM wide face-to-face groups | centred on the span the two blocks share (--peer-span-centre), which fixes the i1 102.8 um hop |

Floorplan: i3_plan/floorplan.{json,svg}.

## Die runs

| run | die | host / dir | status | GRT overflow | TT setup WNS / TNS | FF hold WNS / TNS | SS (sensitivity) | IR spine / field |
|---|---|---|---|---|---|---|---|---|
| c1 | layer1 | EPYC1 s81-die-iter/c1 | GEN/PLACE/CLOCK_PLAN/KIT done 03:27 PT; GRT running (about 12 h, kit = old die_sta) | TBD | TBD | TBD | TBD | spine/field from pre-fix src: PDN-0175 (superseded by ir_m948) |
| c1e | layer1e (Engram home: eng_SE in the SE service slot) | EPYC4 s81-die-iter/c1e (src_c1e2 = 4c8acb002 + the fixes below, per-pin kit) | plan 3 PASS (0 overlaps / 0 outside / 0 pin clashes, 59,077 inst); chain started 03:14; KIT 05:07 PT, GRT running EPYC4 | TBD | TBD | TBD | TBD | TBD |
| i3h | hrow-tx legality (SE slot under dsfd_mtp_hrow 2,998.08 x 1,769.04) | EPYC1 s81-die-iter/i3h_plan | done: 0 overlaps / 0 outside / 0 pin clashes, 58,338 inst; margin lint TT reach PASS (max 518.4 <= 674 um), SS reach 504 um: 128 hops of 518.4 um (y_rt_<c>_24b_1, one per column) | - | - | - | - | - |
| r4f (reference, 10-10) | layer1, r9 pre-v4 | EPYC3 cont-takeover/s81-r4d/r4f | done | 0 | -16.9 ps / -11.13 ns (1,018 paths, 1,008 of them return relays y_rt_*b) | -107.3 ps / -58,911 ns (2.32 M paths, raw die relays) | -63.9 ps | - |
| rp7 | layer1 margin lint, recipe v5 (= v4 + --rt-strip 40), main 6df7157ba | EPYC4 s81-die-iter/rp7 | 0 overlaps / 0 outside / 0 pin clashes; SS reach violations 128 -> 0; far-side 1 (f_hb_collective_t_hc_y_2048_3071_hc_s_7, 22.0 um back vs 20 slack) | - | - | - | - | - |
| ir_m948 | layer1 / layer1e IR (main 948f2da01, M8/M9 pitch on grid) | EPYC1 s81-die-iter/ir_m948_{layer1,layer1e} | PDN-0175 gone | - | - | - | - | spine 63.6 mV VDD / 73.4 mV VSS (FAIL > 35; worst node sp_vm clip, then the g_hb_hc_s_wq_d_vm stations); field PSM-0069: 42 unconnected 6.46 um qbanks (bn/bs) + 231 window-edge M7 stubs |
| ir_pdn2 (v5) | layer1 IR, die PDN contract v2 (claude/el1012-s81pdn da4a35f97 on 412dc16fc, opts v4) | EPYC1 s81pdn/v5 | **PASS <= 35 mV**: PDN PASS, PSM connectivity PASS (0 unconnected) | - | - | - | - | inner window: spine **16.7 VDD / 28.0 VSS mV**, field **29.5 / 31.4 mV** (static, peak power; 2-pitch guard band excluded) |
| c3 | layer1, contract v11 (HC HIER2 slab 1,816.56 x 12,630.216), v5 recipe, main f13695e45; c1/c2 (pre-IR-fix src) killed | EPYC1 s81-die-iter/c3 | plan check: 0 overlaps / 0 outside / 0 pin clashes (56,802 inst), reach 0, far-side 1; relay/station clock pins 34,317 / 0 missing (c2 odb) | running (GRT ~12 h) | TBD | TBD | TBD | IR PDN v2 + OT_IR_INNER; after STA: die_sens.sh = OCV bound (0.95/1.05) and cap x1.40 / x2.44 (region-DRT error bar) TT/FF; region DRT staged only at GRT overflow 0 |
| v12 plan | layer1, contract v12 (HC split: sp_hc_s 1,816.56 x 12,053.44 + NEW sp_hc_t 1,816.56 x 5,186.16 below the corridor; cth 576.72 x 740.88; bgq28 501.12; svcj 64.8 x 43.2), v5 recipe | localhost check | 0 overlaps / 0 outside / 0 pin clashes (56,851 inst), reach 0, far-side 1 (same hc_s_7 22 um); hc_s<->hc_t 6 crossings x 1,512 um, 7 stations each | staged: tools/s81/die_chain_launch.sh <v12 sha> c4 (after c3 reports) | - | - | - | ctrl gate (warn=phys) 16 findings: +dsfd_sp_hc_c t_tf/f_tr placeholders, +dsfd_sp_hc_t no RTL (HC lead splits dsfd_sp_hc after ctile_14/36/56) |
| v13 plan | layer1, contract v13 (SU SM stops: sp_su_s 1,890 x 10,022.4, hub stack + corridor +3,952.8 N; HC 10/12 rows; ces 302.4 x 341.28; crooty v3; cth sub_layout; P2 draft-A slots), v5 recipe | localhost check | 0 overlaps / 0 outside / 0 pin clashes (57,015 inst), reach 0, far-side 1 (hc_s_7 22 um); ctrl gate 16 findings (same as v12) | c5 staged/launched (see log) | - | - | - | ctrl gate (warn=phys) 16 findings |

CTS plan: TBD from c1/clock/plan.json.gz (sinks, planned share, skew per tree).

## Fixes in this iteration

1. **TT -16.9 (return relays g_rt_*b -> y_rt_*b, a 526 um stage).** Recipe v4 places relays so that none sits on the far
   side of its driver and every return-class hop stays within reach (--relay-progress --sstn-ccpad --pin-need). c1 STA
   will verify this.
2. **FF -107.3 (cf<c> cr -> y_xa_<c>_0_0).** The r4f kit balanced the colck cfifo with the plain view's 263 ps scalar
   insertion and its 263.8 ps ck -> co arc; the colck view's arc is 54.0 ps. As a result the column relays were clocked
   about 100 ps after the cfifo's cr-side launch flops. Three changes in tools/s81/die_sta.py fix this:
   - 8d03d75da: the kit binds the colck view itself.
   - 4e8027659: an alternate view uses its own calib insertion.
   - s81-die-iter 10-12: a block with more than one clock pin in the plan is balanced per clock pin, using the ETM's
     own min/max_clock_tree_path (cr: FF 164.9 min / SS 388.5 max / TT 251.3).

   No false paths and no masking: the die tree delivers each pin early by the insertion behind that pin.
   Verification: the r4f GRT SPEF re-timed at FF with the corrected balance (A) and as it was (B):
   s81-die-iter/hold_verify on EPYC4. Both runs use the same SPEF, libs and netlist; 9 min, 26 GB each.

   | FF hold (r4f SPEF) | as it was (B) | corrected balance (A) |
   |---|---|---|
   | WNS / TNS | -107.3 ps / -58,911 ns | -103.7 ps / -55,745 ns |
   | y_xa (cfifo cr -> first column relay) worst | -107.3 | -32.9 |
   | y_xb worst | -89.7 | -32.3 |
   | endpoints < -50 ps | 36,150 | 4,093 |
   | violating endpoints | 2,320,945 | 2,252,452 |

   The cfifo class is closed down to the common relay floor (about -33 ps: interim relays, 50 ps hold uncertainty,
   15 ps hold, a few um of wire). The new worst endpoint is a different class: hco_SW -> xsco_SW at -103.7 ps (unchanged
   between A and B). In that class the hub m2l end block launches o[*] with a 110.5 ps ETM arc into an interim
   dsfd_xstg_515 2.8 um away. The kit balances hco on its 152 ps scalar, while its lib's ck min_clock_tree_path is
   123.0 ps. This is the next die-top hold class.
3. **layer1e plan assertion (d10_eng_SE).** The control-plane start blocks on the eng_SE slab searched only stripS,
   which lies above the SE service slot. They now stand in the slot box first (engS / hrowS, as the fwd-iface sink ends
   do).

4. **SS reach, return leaves (128 x 515.0 um, bn<c> -> y_rt_<c>_<n>b_0).** The top slot's L-lane qbank sits on the frame
   top edge; its return leaf runs east along that edge over a packed frame (q element, then the cfg / sstn row 262 um
   down, full of relays), so relay 0 fell to the TT tier. --rt-strip 40 lets return-tree relays use the channel strip
   above the frame: every rt_127_24b relay now places in the column-reach tier, reach violations 0 (rp7).
5. **FF hold, die relays fed by closed end blocks.** Generic receiver hold pad (tools/s81/die_sta.py hold_pad_sites):
   every interim glue input driven by a closed hend within 100 um binds '<master>__hp' (120 ps FF in-stage delay
   chain, x1.4 TT / x1.9 SS on setup); dsfd_xstg i timed against cw. r4f SPEF FF (hold_verify/D, emulated pad set):
   hco_SW -> xsco_SW -103.7 -> +16.3, hr_W -> f_hr_W*_o_1 -77.9 -> +42.1, hl_W -> g_hl_W*_o_sp_collective_0 -77.6 -> +42.4 ps.
   New worst: hqe_SW -> svc_SW -51.3 (closed -> closed), then the interim relay floor about -33 ps.

## Open

- IR: closed at contract v2 (ir_pdn2 row; die PDN contract below). Open: dynamic droop (PSM is static; the run uses
  peak = 4x average power), layer1e not re-run, field margin 3.6 mV at the dsfd_node rows (n26_*).
- far-side 1: f_hb_collective_t_hc_y_2048_3071_hc_s_7 (forwarded hub station, 22.0 um back).
- hqe_SW -> svc_SW FF hold -51.3 (closed svc input; pad belongs in the svc view or a die-top pad stage).

- Hold class hco_SW -> xsco_SW (-103.7): balance single-clock closed views on their lib min_clock_tree_path at FF
  (hco 123.0 instead of 152, worth about 29 ps), and add hold buffering on the die-top net, because the hop is 2.8 um.
- c1 ran its kit with the earlier die_sta (src_8d764f310). After its GRT, re-run the kit with main die_sta and repeat
  the FF STA on the c1 SPEF.
- i3h: the hrow-tx slot is legal, so contract v7 stands (no v8). The 128 SS-reach hops (518.4 > 504 um) are the TT
  return-relay class that v4 targets; TT reach passes.

- Die-relay hold beyond the cfifo class (r4f: y_xb 167k, y_rt*b 79k, y_rt*a 52k, y_cfg 29k, y_cc 15k paths): the relays
  still have interim views (0 ps insertion), so the die-top region route has to carry hold buffering on the relay inputs.
  Sign-off follows the AMENDMENT item 2: routed per region.
- ctrl port audit: 13 findings, recorded as warnings (OT_S81_CTRL_GATE_WARN=phys). Other streams own them.

## Die PDN contract v2 (el1012-s81pdn, 2026-10-12)

Layer contract kept: tiles PG on M6, element / parent straps M7, die grid M8/M9. Budget: 35 mV = 5 % of VDD 0.7 V,
static, at peak power (inst_power, 4x the average the --avg run uses).

| quantity | spine window | field window | design value |
|---|---|---|---|
| power / density (peak) | 2.75 W, 0.146 W/mm2 (sp_vm 0.94 W on its 0.90 mm2 clip = 1.05 W/mm2) | 21.5 W, 1.32 W/mm2 (q element 0.253 W / 0.113 mm2 = 2.24 W/mm2) | - |
| bumps | every core bump PG: 45 um array, VDD and VSS each on a 63.64 um lattice (1 per 4,050 um2) | same | field 7.6 mA, q element 13 mA per bump |
| die M8 / M9 | per-net pitch 9.092 um (bump pitch / 7), 0.48 um wide: 5.3 % per net per layer | same | via89 at every same-net crossing |
| M7 -> M8 | element M7 stripes 10.8 um per net; via78 at each same-net crossing (1 per 98 um2 per net) | same | - |
| thin blocks | stations dsfd_hstnh 17.256 h: local die-M8 at 9.092 | qbank 6.456 h: local M8 3.312; rstg 8.616 h: 4.752; relays 17.256 h: 9.092 offset 0.5 | rule: h - 0.6 < 2 x 9.092 + 0.48 -> local die-M8 straps, 4 straps (2 per net) inside the block |
| result (inner window) | 16.7 / 28.0 mV | 29.5 / 31.4 mV | <= 35 mV |

No denser spine grid and no extra power domain for sp_vm: its density (1.05 W/mm2) is below the field's, and the field
grid closes there. What the three ir_m948 failures were and what changed (tools/dsrom_s81_fulldie.py case_irm):

1. Spine 63.6 / 73.4 mV: PSM puts an instance's whole current on ONE node (case_psmt: 54.8 vs 2.4 mV for the same
   1 W). The worst nodes were the centres of the sp_vm clip (0.94 W) and of the hstnh stations. Every block above
   64.8 um is now modelled as 43.2 um current tiles (4 M7 pitches, area share of its power each). Generated blocks keep
   their M7 lattice. Real abstracts (the q element) are cut into tiles that carry their own M7 PG rects.
2. Field PSM-0069: 6.456 um qbanks were crossed by at most one die M8 strap per net, and often by none. They now get
   local die-M8 straps by the thin-block rule above. pdngen `-cells` is an unanchored regex (`dsfd_rstg` took the
   rstg tiles -> PDN-0217), so every macro-grid cell name is now anchored `^name$`.
3. Window edge: the solved window now has 2 bump pitches of the surrounding die on every side and is judged inside
   (OT_IR_INNER). Without the guard band, the first VSS bump column sat 63.6 um in from the cut, and the field's edge
   q elements read 40.2 mV against 29.7 mV in the interior (v4).

Runs (EPYC1 /srv/opentallas-scratch/claude/s81pdn/): v1 = tiles + thin rule (spine 16.9 / 27.7 mV, field PDN-0217);
v1f = anchored grids (field PSM PASS, 57.9 / 71.9 mV at the q element centres); v4 = real-abstract tiles (field
29.7 / 40.2 mV, edge column); v5 = guard band (table above).


## Collection at 2026-10-12 18:42 PT

Source-pinned raw status and GRT tails: `collect_20261012/summary.json` and sibling logs.
All three runs remain in GRT; no final overflow or STA/cap-sensitivity verdict exists.

| Run | Contract | GRT progress | IR spine VDD/VSS (mV) | IR field VDD/VSS (mV) |
|---|---|---|---|---|
| c3 | v11 | extra iteration24/30 |16.70 /28.01 |29.53 /31.38 |
| c4 | v12 | extra iteration9/30 |16.70 /28.01 |29.53 /31.38 |
| c5 | v13 | extra iteration5/30 |14.38 /15.65 |29.53 /31.38 |

Values above are inner-window IR against35mV. Existing chains run nominal TT/FF/SS,
OCV0.95/1.05, and cap sensitivity x1.40/x2.44 after GRT; do not duplicate these jobs.
V14 integration requests are recorded in `results/arch/hier_contract_1011/s81_v14_requests.json`;
v14 is not published. HC crossing needs fd2920 (forward3056 including controls), replacing
v13 fd1128; the current runs therefore do not validate the widened HC split.
