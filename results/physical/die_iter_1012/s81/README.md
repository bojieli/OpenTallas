# S81 DeepSeek ROM layer die: die-level iteration

Lead: s81-die-iter (log /home/ubuntu/claude-takeover-20261007/el1011-s81die.log, prefix [s81-die-iter]).
Contract: results/arch/hier_contract_1011/s81.json, v7 (main a82dfd1c6). Generator: tools/dsrom_s81_fulldie.py (gen r8 / rev r9).
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

- IR: spine 63.6 / 73.4 mV at the sp_vm clip (power concentrated on the clipped VM abstract); field PSM-0069 because a
  6.46 um qbank's M7 stripes can miss the 9.092 um-pitch die M8 strap of one net -> glue-row follow-pin grid (M2/M5) or
  M8 PG on short abstracts; window-edge M7 stubs need clipping to strap crossings.
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
