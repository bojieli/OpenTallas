# HBM-CORES-KITS-5 split3: bit-level cut map (2026-10-28)

COORD ruling 19:53 (DEFAULT YES): opt-in format; whole-bus maps byte-identical.

## Problem
split3 `ctl` and `opstore_a` kits stopped with MAP_AMBIGUOUS (results/hbm_cores_kits_2/split3_map_rootcause.json).
The remainder RTL tops (rest_wrap.py) regroup the cut bits under as-built names. Example: 16 per-lane plan
`ro_x[32]` buses are one RTL `u_core_e_rox[512]`. Another: plan `ro_x_{n,s,e,w}[128]` are halves of RTL
`u_core_ro_x_{e,w}[256]`. The cut map in canonical_ports_split.json only lists whole-bus renames.

## Fix
* `physical/die_plan/hbm/cores/harden/split_bitmap.py` (split builder side). Elaborate the master
  (`split3_master_elab.ys`: proc, memory_map, flatten, opt_clean; leaf blocks are blackboxes). Map each plan cut bit to
  the RTL top bit on the SAME NET. The RTL bit is found through the rest_wrap u_x connections.
  The result is written to the opt-in sidecar `canonical_bitmap_split.json`.
* `gen_core_kit_hbm.build_wrapper` takes a slice list `[[rtl port, port lsb, plan lsb, n], ...]` as a cmap value.
  Each sliced port gets one internal wire and range assigns. Every plan output bit and every sliced RTL input bit
  must be driven exactly once, otherwise PORT_MISMATCH. Dict (whole-bus) values follow the old code path.
  gen reads the sidecar only for type_ids listed there and requires verdict PASS.

## Results (CHECKED unless marked)
| piece | plan buses / bits | sliced buses | map verdict | RTL inputs uncovered | kit gen |
|---|---|---|---|---|---|
| ctl | 108 / 11819 | 76 | PASS | 0 | OK (was MAP_AMBIGUOUS) |
| opstore_a | 29 / 7534 | 6 | PASS | 0 | OK (was MAP_AMBIGUOUS) |

Whole-bus entries that were already in canonical_ports_split.json are re-proved SAME_NET. That includes the earlier
width guess `g_operand_0_u_group_sw_d -> u_core_b_rr`.

Entries that are NOT proved by net identity (see bitmap_check_*.json notes):
* `NARROW`: ctl io_word 470 of 471 bits; opstore_a vm_waddr 144 of 384 bits. These use ascending order of the master
  bits that the piece reaches. That is the rest_wrap.py ordering rule. UNCHECKED against the cut tool, whose input
  data (--net/--elab) is gone.
* `CONST_NET`: ctl stage_mask is a master constant, so the old whole-bus entry is kept.
* `BY_ELIMINATION` (opstore_a): `glue[4]` maps to u_core_io_r[3:0], `glue_1` maps to u_core_u_engine_u_memory_fault,
  and constant-net `g_operand_0_u_group_sw_mask` maps to stage_mask. Each is the only free RTL bit group of that
  direction and width. UNCHECKED by net, because the cut names `glue*` carry no hierarchical name.

Byte identity: see byte_identity.txt. The opstore_b kit (whole-bus) was regenerated with the main gen and with the
new gen. The 79 generated files match exactly (diff -r is 0 lines; the wrapper md5 is the same).
Tests: test_split_bitmap_hbm.py (11) and the hbm_arch_cores suite: 36 passed.
KIT_PREFLIGHT --contract: pins_canonical / module_closure / master_slice PASS on all 3 kits.
The remaining FAILs are not from the map:
* ctl `clock_pin_geometry`: io.tcl clk_pe/clk_pw/clk_lg pin 0.024x0.192 < 0.048x0.48. This is the c25a multi-clock
  pin size issue.
* opstore_a and opstore_b `macro_*`: no staged MACRO_PLACEMENT_TCL. The opstore_b baseline fails the same way.
