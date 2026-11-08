# QC-TYPES-10/FWS 11-08: sle_fw_v3 S-export START with re-rooted reset (plan event plan_qc53v4x_fws)

Base: plan_qc53v4w (sha256 e5dc7eacb745). Result: plan_qc53v4x_fws (sha256 e2e1be455b50).
Only `partition_types.sle_fw_v3.clock` changes; `fws_delta.json` is the composable delta.

## Class
v4u (qc53v4u) gave the sle_fw_v3 writer START W=3 on 14 exports. The two S-face exports, cws0_o at (535,3) and
x_st_a_fe_o at (467,3), stayed at W=0. Each is one hop of 752 / 820 um from the START source cland_rstart_in at
(620,670).

The cause is geometric. rst_root_n is the arst_n pin register at the W face (8,837). Every depth-1 relay lies
within 380 um of it (x <= 358). The S face is 1361 um from the root, so a stage next to it cannot take a depth-1
reset inside 405 um. No arrangement of phase-1 stages can reach it.

## Form
1. **Reset follows START.** The two S branches get W=3 and three stages, the same as the 14 v4u branches.
   Stage i takes an existing depth-(i+1) relay of the type's reset tree: rst_rl_102 (depth 1), rst_rl_15
   (depth 2), rst_rl_18 (depth 3). The face flop keeps its depth-4 reset. With r = rst_root_n and
   s = cland_rstart_in:

       q0(t+1) = r(t-1) & s(t)
       q1(t+1) = r(t-2) & q0(t)
       q2(t+1) = r(t-3) & q1(t)
       f(t+1)  = r(t-4) & q2(t)

   So f(t+1) = r(t-4) & s(t-3). That is exactly the v4w W=0 face, f(t+1) = r(t-4) & s(t), with START delayed 3
   edges. The receiver K is +3 and payload cycles are +0, the same binder rule (K_new = K + W - R) as every W branch.
   - Paths run straight south: cws0_o stages at x 534.6, x_st_a_fe_o stages at x 469.8, y 632/421/211.
   - START hops: cws0_o 123/211/211/208 um, x_st_a_fe_o 188/211/211/211 um.
   - Stage raw flights: cws0_o 379/313/271 um, x_st_a_fe_o 314/248/206 um. All are <= 380 um (design target);
     the rule is 405 um.
2. **Face reset leaves.** In v4w one relay, u_cland_rst_cmd_ei at (311,337), resets every FSTART face flop of the
   type over 321-1219 um (rsf_o 1162, rsn_o 1072, x_ctl_o 1219, cws0_o 558, x_st_a_fe_o 490). Each of the 16 faces
   now gets its own `landing_local_resets` leaf (the DIE-HEAD-38 R1 / fstart_reset_leaves form): D is the depth-3
   relay nearest the face, and the leaf sits half way. Leaf hops are <= 188.7 um. The generator checks
   depth(raw)+1 == depth(old reset), so no release edge moves. Cost: 0 cycles, +16 flops.

## Pin cycles (price_fws.py on the binder's own strap_ties)
| crossing | receiver | strap | v4w -> v4x |
|---|---|---|---|
| sl_E5_hc0__cws0__2 (sl_E5_fw.cws0_o) | sl_E5_su_l1.cws0_i | strap_ca_k_cws0_i | 25 -> 28 (+3) |
| sl_E5_st_a__x_st_a_fe__1 (sl_E5_fw.x_st_a_fe_o) | sl_E5_su_l1.x_st_a_fe_i | strap_ca_k_x_st_a_fe_i | 25 -> 28 (+3) |

Every other strap value of every instance is identical. No lane or latency key changes.

## Proofs
Files: validate.txt, compare.txt, check_tail.txt, bind_tail.txt, bench.log, rtl_diff_vs_bind_v4w.txt.
- **validate:** PASS (0 errors).
- **G0C:** FAIL 29 -> FAIL 29 errors (the same 29 as v4w), findings identical 581/581, clean types 114 -> 114.
- **Count dry vs v4w:** types 119, designs 31 and pin rows identical.
- **Strict bind** (asbuilt_reach.json + r8_reach.json of v4w): rc 0, errors 0, 377 partitions, 1921 crossings, 11568 straps.
- **RTL diff vs bind_v4w** (paths normalised): only two files change.
  - qfd_qc_sle_fw.sv (sle_fw_v3): 6 writer relays and 16 leaves added, 16 face reset pins rewired.
  - qwen_compute_bound_top.sv: the 2 strap ties strap_ca_k_cws0_i / strap_ca_k_x_st_a_fe_i, 25 -> 28.
  - Every other type .sv is identical. Five cb* .sv differ only in source-path comments, because the bind ran from a
    private farm. The reset_tree.json files differ only in provenance and bound sha.
- **Bench (bench_fws.py, bench.log).** The START/reset cone of all 16 FSTART faces is cut from the strict-bind RTL
  (v4w 69 cells, v4x 106 cells) and run on the real cells with iverilog, 39,940 cycles of random rst_root_n and
  START. Results:
  - S faces: new == v4w with START delayed 3.
  - The other 14 faces: new == v4w.
  - Mutants caught: S stage bypass; S stage reset one phase too shallow; S stage reset one phase too deep;
    S face leaf one depth short; W and N face leaf one depth deep (ag_eo, x_ctl_o).
  - On a W or N face, a leaf one depth SHORT is logically equivalent and is not a mutant. The phase-1 stages already
    AND in r(t-2..t-4).

Tools: mk_fws.py (constructor, never edits its input), run_v4x.sh, run_bind_v4x.sh, price_fws.py, bench_fws.py,
render_fws.py (form_fws.png).
