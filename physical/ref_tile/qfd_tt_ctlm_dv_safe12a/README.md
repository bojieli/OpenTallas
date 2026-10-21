# qfd_tt_ctlm_dv_safe12a -- QKO-CTLM 10-21: Q.STA.TTC.4 CTLM successor of safe10c

Geometry, macros, children (h16c u_hr + closed wtn), pins and recipe = safe10c (Codex a4723fd52).
Netlist = rtl/qwen_dv/lp9e_rr (lp9d_npl + tools/qwen_dv/replica_role_split.py; record replica_role_split_record.json).

## safe10c/d CTS verdict (agidock128 ref_gate/qfd_tt_ctlm_dv_safe10{c,d}-20261021-094151)
placed TT WNS -829 / -866 ps, 2000+ failing reg->reg endpoints; clock_rule ck_core pin_spread 122.8 (insertion 880 ps), ck_hr 222.4.
Worst path u_6176 (x549) -> kept fan-out copy u_68475 (x221, between the CAL SRAM columns, pulled there by its 11 mux-select
loads) -> back E (x545) for 9 control loads -> OA21 u_39701 (x229, inputs from two other mixed copies) -> u_6466 (x552):
22 levels + ~900 ps of wire, two W<->E round trips in one cycle.  Cause: the native generator fills identical fan-out copies in
sink order, so one copy drives both a W datapath mux-select bank and E control logic.

## Fix (structural, function unchanged)
replica_role_split.py: for each replica group (same cell type, same input nets) re-deal the pooled sinks so every copy is
role-coherent (control-only or mux-select-only, mux selects in instance order), cap 32 (MUX S = 2): 45 groups, 2428 sink pins
re-pointed, +24 identical copies, 0 nets newly over 32.  tools/qwen_dv/rr_equiv.py: all non-cell lines identical, every
re-pointed pin reads a structurally identical driver (recursive canonical hash), 0 mismatches.

## SAFE checklist
1 pins: unchanged | 2 reach: removes the W<->E copy round trips | 3 fanout: max 32 kept, copies role-coherent
| 4 depth: unchanged logic, wire share cut | 5 storage: unchanged macros on lattice | 6 floorplan: fill 45/43 % | 7 clock: regional
ck_core/ck_hr + L5 landings | 8 reset: unchanged regional reset runs.
Pair safe12a/12b: bind first to close.
