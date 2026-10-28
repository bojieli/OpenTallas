# MESO-STRAP-1 (2026-10-28 00:07-03:10 PDT): OWNER 12.15a count straps + tie-VALUE audit (rule 1.8, 12.14a)

Branch claude/meso-strap-1028 (on main a65712f2d5). Runs: intel2:/srv/opentallas-scratch2/claude/meso-strap-1.
Every piece is opt-in (`count_aligned.strap_form`); the parameter form and the old ring stay the default.

## What is built
- RTL `rtl/common/ot_dp_clk_landing_ca.sv`: `ot_meso_ring_ca` takes K on an input (`k_s`); the parameter wrapper
  `ot_dp_clk_landing_ca #(K)` feeds a constant (Verilator bench identical to MESO-COUNT-2, k-induction K=2 PROVEN).
  New `ot_dp_clk_landing_cas` (K on `strap_k[log2 D+3:0]`, DEPTH stays a parameter) and `ot_dp_landing_origin_s`
  (PAD / EDGE_FALL on straps). The pins are quasi-static: no pin register. The ready TIMEOUT now covers every K residue
  (91 D4 / 171 D8 cycles instead of max(K,0)+...). This is the one intended difference: fault timing at bring-up only.
- `count_align_bind.strap_ties`: per-type pins (strap_ca_k_<bus>, strap_ca_pad, strap_ca_efall, strap_ca_tsel,
  strap_ca_root) and per-instance tie values. `clock_landings` (strap form) emits one design per type, and the parent
  writes a `W'b...` literal on each pin. Plan: `types[].count_straps`, like id_straps: not a plan bus; kit SDC
  set_false_path -from; die_trial free ports.
- Tie-VALUE audit (straps.py, COORD addition): `audit_count_strap_values` (RTL literal == bind value) and
  `audit_netlist_strap_values` (one TIEHI/TIELO per bit, its own net, pattern == bind value). A missing tie, a
  non-literal, a wrong width or a wrong value is a G0 ERROR. It runs in bind.py and in gen_rtl (gen rtl --clock-landing).
- `strap_lec.py`: LEC per (master, used constant variant). The gate is the strap master with the variant's
  constants tied. The gold is that copy's parameter wrapper, with the master's TIMEOUT. Leaf cores are everted black
  boxes. Proof: yosys equiv_make + equiv_struct + equiv_simple + equiv_induct. `--mutant` flips one tie bit, and the
  result must be NOT equivalent.

## Numbers (own runs, CHECKED-own, UNCHECKED-indep)
- HEAD part map (head_part plan_edgepad, die-head-3 regions_part, `head_part_run.sh`): 16 types after straps. Before,
  the parameter form needed 21 types at PAD 0. 326 instances, 22 LEC variants, 3,224 tied bits, 0 residual split.
  compose 16->16 lc_err 0; gen rtl rc 0. Tie-value audit PASS 3,224 bits. Flipping one bit
  (lk_WN2.strap_ca_k_coll_i0) or dropping a pin gives FAIL G0 ERROR (`head_audit_mut.py`).
- HEAD LEC (`head_part_strap_lec_partial.log`, run continues in intel2 .../head/lec_full): 17/22 variants EQUIVALENT,
  covering 320 of 326 copies. 12/12 flipped-tie mutants are NOT equivalent, 0 fail. Still running at 03:05: hd_lep0N,
  hd_spn v0-v3 and 4 mutants.
- KV (DIE-KV-5 partition-frame spice bind + hm_r26q9c, `kv_straps.py`): 51 types, 160 instances, 117 LEC variants
  (= DIE-KV-5). Tied bits are 23,101: D8 rings need 7-bit K, and DIE-KV-5's 21,854 assumed 6. 3 types stay split
  (kv3_pc_v1, kv3_pc_v3, kv3_phy_v1). In each, the copies differ in the relay rx/tx role, and that role changes the pin
  list. So 54 types remain. KV LEC was not run because no KV landed (clock-landing) plan exists yet.
- Formal strap form with K free-but-constant (fv_ca2_strap*.sby): the mutants are caught 8/8 (K, FREERUN, NO_GUARD,
  NO_TAG at D4 and D8). The bounded BMC is clean for 260 frames (32.5 T) at D4 P3 E2 (69 min). k-induction is
  UNDECIDED at depth 250 (not inductive). The BMC at 620 frames did not finish in 2 h, so the sweep was stopped.
  An unbounded all-K proof is NOT done: it needs helper invariants that tie the tags to strap_k.
