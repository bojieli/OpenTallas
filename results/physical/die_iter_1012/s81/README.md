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
| c1 | layer1 | EPYC1 s81-die-iter/c1 | GRT running (about 12 h) | TBD | TBD | TBD | TBD | TBD |
| c1e | layer1e (Engram home: eng_SE in the SE service slot) | EPYC4 s81-die-iter/c1e | relaunched 02:35 (first plan hit an assertion at d10_eng_SE, fix below) | TBD | TBD | TBD | TBD | TBD |
| i3h | hrow-tx legality (SE slot under dsfd_mtp_hrow 2,998.08 x 1,769.04) | EPYC1 s81-die-iter/i3h_plan | queued | - | - | - | - | - |
| r4f (reference, 10-10) | layer1, r9 pre-v4 | EPYC3 cont-takeover/s81-r4d/r4f | done | 0 | -16.9 ps / -11.13 ns (1,018 paths, 1,008 of them return relays y_rt_*b) | -107.3 ps / -58,911 ns (2.32 M paths, raw die relays) | -63.9 ps | - |

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
   s81-die-iter/hold_verify on EPYC4. Result: TBD.
3. **layer1e plan assertion (d10_eng_SE).** The control-plane start blocks on the eng_SE slab searched only stripS,
   which lies above the SE service slot. They now stand in the slot box first (engS / hrowS, as the fwd-iface sink ends
   do).

## Open

- Die-relay hold beyond the cfifo class (r4f: y_xb 167k, y_rt*b 79k, y_rt*a 52k, y_cfg 29k, y_cc 15k paths): the relays
  still have interim views (0 ps insertion), so the die-top region route has to carry hold buffering on the relay inputs.
  Sign-off follows the AMENDMENT item 2: routed per region.
- ctrl port audit: 13 findings, recorded as warnings (OT_S81_CTRL_GATE_WARN=phys). Other streams own them.
