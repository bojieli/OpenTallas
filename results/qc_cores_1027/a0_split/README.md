# QC-CORES-1: A0 NK/NL hard-core split plan (2026-10-27)

Scope: qfd_tile_nk_a0c (720 copies) and qfd_tile_nl_a0c (48 copies). This is a plan only: no P&R was run. The plan waits on a GEOM REQ verdict.

Labels: CHECKED = recomputed here from the data. UNCHECKED = taken from another lane's file and not recomputed.

## 1. FF-pruning review (Codex raw_leaf_kit, 11646 vs 12030 FF)

- **Where the FFs were lost (CHECKED).** ORFS `1_synth` runs OpenROAD `eliminate_dead_logic`. In run_pgfix it reported "Removed 576 unused instances and 576 unused nets":
  - 1_2_yosys.v holds 12030 DFF (11085 DFFHQN + 945 DFFASRHQN).
  - 1_synth.odb holds 11646.
  - The loss is not GPL/DPL "physical optimization", as the Codex README states.
- **Which FFs (CHECKED; name diff in intel2 qccores1-1027/a0/ff_removed.txt).** All 384 removed FFs have no path to any leaf output:
  - 192 = `u_ls.g_grp[0..3].g_lane[*].g_candidate_mul.u_mul.g_inreg.{a_r,b_r}[0..15]`. These are the low 16 bits of 12 of the 32-bit operand registers.
  - 128 = `u_ls.s3_w[*]`, half of 256.
  - 64 = `u_ls.s3_x[*]`, half of 128.
- **Verdict.** The pruning preserved the function at the leaf ports: removing unobservable state cannot change any output.
  - The claim "192 required input captures lost" is wrong as a functional claim. Those registers capture input bits whose values never reach an output.
  - The ffpg successor force-keeps all 12030 (A0GATE ff 12030, pg_bad 0, in_port_flops 390; CHECKED from a0_gate_cts.txt). That keeps 384 dead FFs as clock sinks, costing area and clock load. It does not fix a bug.
  - The correct structure: remove the dead operand bits in the RTL (candidate_mul low halves, unused s3_w/s3_x halves), or accept dead-logic elimination and gate on the post-elimination FF count plus a leaf LEC.
  - UNCHECKED: whether these bits are also dead in the uncut native LSL. If they are live there, the raw-fault cut dropped an observation path, and that would be a real bug.
- **ffpg leaf after route (CHECKED, signoff.log 10-26 01:47).** NOT SIGNED:
  - TT setup -90.89, FF hold -17.53, DRV fail.
  - sdc_lint FAIL: split_d min input delay of 40 ps.
  - ff_ref_missing.
  - Its clk pin is on the E edge (pins.json x=115.248 y=62.988), which violates 12.8a.

## 2. Structural split (hardened once, each run <= 400k cells)

| sub-core | cells | per NK / NL | copies on die | state |
|---|---|---|---|---|
| ot_qwen_tile_lsl_rawfault_m3 (LSL rawleaf) | 58,386 mapped / 76,731 raw (CHECKED size_gate.json, source.json) | 8 / 8 | 6,144 | unsigned (above); re-kit with centre clk |
| ot_qwen_tile_romleaf | view on main, gate PASS 10-16 (UNCHECKED cells) | 10 / 10 | 7,680 | pre-12.3 view, clk on W edge (LEF 0,21.756) -> re-kit |
| ot_qwen_tile_node | PROVISIONAL_NOT_A_VIEW on main | 1 / 0 | 720 | no real view; clk on E edge |
| NK parent (soft + islands) | 64,205 cells / 16,592 FF (mapped sha 3423d4c0 matches parent_actual_synth.json, CHECKED) | 1 | 720 | LEC running (below) |
| NL parent | 61,550 / 15,561 (UNCHECKED, Codex json) | 1 | 48 | - |

- Consistency (CHECKED arithmetic): flat NK 677,672 = 64,205 + 8 x 76,731 + 381 (0.06%). The split covers the whole flat count.
- NK and NL share the rawleaf and romleaf masters (same type names in both parent synth jsons, CHECKED). Whether the netlists are identical is UNCHECKED.
- The parent RTL still carries the 42/41 external clock taps (-DOT_A0_CK_TAPS42). The plan replaces them with one centre entry.

## 3. Outline and clock plan (a0_split_plan.py; renders a0_split_plan_{nk,nl}.png, viewed)

- The outline (457.92 x 1157.76) and all child placements are taken unchanged from the Codex parent packet. Every child already passed the halo audit.
- **E0, one centre entry:** (228.96, 578.88), in the 67-um ROM channel. It has an M9->M5 island (12.8a) and replaces the 42/41 taps.
- **Balanced in-core H-tree (12.8b, pushdown islands 12.2a1):**
  - L1: +-245 um vertical, ending at (228.96, 333.88) in the channel and (228.96, 823.88) in the 20-um LSL row gap.
  - L2: from S, +-130 um vertical, ending at (228.96, 203.88) and (228.96, 463.88).
  - L2: from N, +-130 um horizontal in the row gap, ending at (98.96, 823.88) and (358.96, 823.88).
  - 0 islands fall inside a child or its 5.4 um halo (CHECKED script).
- Max distance from E0 to a child clk pin today: 652 um. Leaf legs run 0..271 um, because the child pins are on edges.
- PASS-COND items for review:
  - (i) Children re-kit with centre clk pins, so the leaf legs equalise.
  - (ii) The N0/N1 leaf legs cross over the LSL children. The child OBS must leave M6 free, or the legs must run in the row gaps.
  - (iii) The L1/L2 islands sit inside the Codex bus corridor x 200.66-257.26. They take sites, not tracks; capacity must be re-deducted.
  - (iv) Latency against 250 TT is not estimated (UNCHECKED). Early taps from the children's real views are allowed (12.3 v5.0).

## 4. LEC plan for the composed core vs the original RTL

1. Parent: cut-RTL (children black-boxed) vs the mapped parent, run with tools/die_plan/lec.py@262d07038. Running at intel2 /srv/opentallas-scratch2/claude/qccores1-1027/a0/lec_nk_parent/lec.
2. Each child: routed netlist vs its RTL (rawleaf: rawleaf_keep.v; romleaf/node: on re-kit).
3. The cut identity, original LSL == wrapper(u_lh) o rawleaf. Codex has this only at netlist level (whole-graph identity + 2^50 cone SAT). It still needs an RTL-level LEC of the original ot_qwen_tile_lsl against the cut-RTL composition.
