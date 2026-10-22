# TOKSIM-HBM: HBM d4g single-user decode, measured per-unit cycles (10-19)

Lane TOKSIM-HBM (owner request 18:18). Branch `claude/toksim-hbm-1019`. All benches ran on Verilator 5.050 on the fleet through unpinned ot-run, were bit-exact against independent goldens, and had their mutants FAIL. Clock: one 833 ps stream edge. tok/s = 1 / (cycles x 833 ps).

Method: every record of the composed d4g static schedule (`d4g_reprice3b`, row `info_banklat_all`) that has a measured law
gets its measured start->retire cycles, and the SAME static schedule is re-run
(`tools/hgi_sim/toksim_hbm_census_1019.py --measured`). Classes without a measurement keep their model cost and are graded `model`.

## Result

| scenario | DS AR tok/s | Qwen3-8B AR tok/s |
|---|---:|---:|
| price of record (H9b 45.03 B/edge/SM) | 1,206.3 | 407.0 |
| price, successor 98 B/edge (HBM-ROTLAYOUT) | 1,421.9 | 795.0 |
| **MEASURED release (TOKEN-LEAD 10-20, combined)**: the row below + **SU.VOP measured** (HBM-SUFIX, as-built SU, no pre-tree) | **1,109.7** | **372.2** |
| measured, SU.VOP still model: successor PC + rotated layout, multi-block attention, Qwen 1 KV head/die, **Qwen SM.MATVEC measured on packed INT8** (HBM-QINT8, 10-20) | 1,162.5 | 776.3 |
| same, but Qwen SM.MATVEC from the BF16w affine law (superseded) | 1,162.5 | 1,002.9 |
| measured, same but serial attention calendar | 1,129.2 | 966.5 |
| measured, successor at the old 96-edge cadence, serial attention | 1,105.9 | 885.7 |
| measured, BOUND H9b controller (GEN2e3 die as built) | 998.9 | 537.4 |

Share of the release token's unit cycles (`used`) by grade:

| design | measured-on-bound | measured-not-bound | model |
|---|---:|---:|---:|
| DS | 12.3% | 63.8% | 24.0% |
| Qwen | 10.6% | 80.8% | 8.6% |

`measured-not-bound` means one of two things. Either the RTL is the newest bench-passing version but is not bound in the GEN2e3 `die.v` (the successor PC controller, the COLL v8x/v7 issuers, the HC fused benches), or the figure is a lower bound (ROW_NORM). Details are in `cycles.json` `per_class`.

## Biggest classes (release; cycles per token, measured vs price at 98 B/edge)

DS: SM.MATVEC 488k vs 193k (2.53x), COLL.ALL_GATHER 203k vs 235k (0.86x), SU.VOP 176k (model), DMA.LOAD 109k (model),
HC_MIX 84k vs 93k, GROUP_REDUCE_MCAST 72k vs 59k (1.22x), ATT.PV 42k vs 67k, ATT.QK 28k vs 41k.
Qwen: SM.MATVEC 687k vs 981k (0.70x), ROW_NORM 163k vs 26k (6.4x, lower bound), ALL_REDUCE_SUM 132k vs 106k (1.24x),
ATT.PV 61k vs 189k, ATT.QK 45k vs 96k, SFU.GLU 17k vs 4k (3.8x).

## Findings

1. **SM.MATVEC with the successor controller and rotated layout.** The bench is `tb_toksim_smhbm.sv`: the die composition with `TOKSIM_PC=safe`, i.e. 4 x `ot_hbm_svc_pc_ctrl_leaf_cfg_safe`, and `SMB_BSCALE 1`. It sustains a static block cadence of 80/64+8 = 88 edges per 64-line block, which is 98.9 B/edge/SM and matches HBM-ROTLAYOUT's >=98. Every DS and Qwen shape PASSes at p80. The MC3 structure gives identical cycles. The same controller with the as-built layout FAILs at p96 (`a_qkv_p96`). The bound H9b needs p180-p220.
2. **DS SM.MATVEC is 2.5x its price** even at 98.9 B/edge. The cause is per-op overhead, not bandwidth: 1,095 small records per token, each paying a serial x-store load before its first GO plus the GO lead. OP_GAP 256 -> 16 changes almost nothing. This is the x-load term that HBM-VMEARLY-XL attacks (measured 1421 -> 441 edges on layer 5). It is not folded in here: the change is compiler-only and the composition does not yet carry it.
3. **Qwen packed INT8 (HBM-QINT8, 10-20).** The bound die rejected every packed-INT8 calendar because the svg feed's S1 consumer copy
   (`ot_hbm_svc_sm_feed_programmed_rel_id`) checked the compiler's command fields against the RAW packet, while the SM consumes the
   two BF16 halves its INT8 converter emits 2/3 edges later. Fix on `claude/hbm-qint8-1019`: the copy models the converter from a
   PREL programme-word mark (bit 118). Measured directly on the fix (successor p80, rotated, TP-8 rows, bit-exact, mutants FAIL):
   qkv48 3,646 / o128 2,544 / gu192 13,438 / down128 6,910 cycles (span + 256), LM head 81,166 (affine 126 + 136/block).
   INT8 is **SM-bound at 136 edges per 64-packed-line block** (2 edges a packed line: the SM front issues 64 codes/edge), not HBM-bound
   (8,704 B/136 = 64 B/edge/SM). The earlier law (BF16w span - blocks/2 x 88) assumed HBM-bound INT8 and was 1.5x optimistic:
   Qwen SM.MATVEC 687k -> 1,037k cycles/token, Qwen 1,002.9 -> **776.3 tok/s**. `units_variants/smhbm_int8.json`, `measured_rel_int8.json`.

4. **Qwen TP-8 holds 1 KV head per die.** The kv1 attention records are dropped (`drop_tags`).
5. **Attention.** The multi-block calendar (HBM-ATTN-MB/MB2, current SM master, compiler only) gives DS QK 726 / PV 773 and Qwen QK 1245 / PV 1689.
   - The SU merge measured 100 edges on `tb_su_static_arithmetic` (PASS). The ring all-gather 82 + top levels 109 stay model.
   - Qwen PV excludes the 16-SM merge, which has no on-die owner, so it is a lower bound.
6. **ROW_NORM.** d4g has no D4096 norm engine. The bound reducer chain alone takes >=1832 / 529 / 271 edges, against the 175 / 125 the price assumes. This is a lower bound.
7. **SU.VOP is still model.** The fork-A compiler `prod_compile.py` fails golden on every record. The cause is in the compiler, not the RTL or the bench: `su_top_compile` vectors PASS on the same `tb_toksim_su_top` build at die parameters. Next step: diff the `prod_compile` op/fill images against `su_top_compile`.

## Pending

- IDX.INDEX quad lockstep. It was killed twice in the build (exit 143). It was relaunched at 200 GB as `ot-epyc9:/srv/opentallas-scratch/claude/toksim-idxdma/out/idx_quad3` (pending_results).
- DMA.LOAD needs a chain bench. DMA.FENCE and COLL.ROW_GATHER are unmeasured.
- SU.VOP compiler fix (item 7).
- VMEARLY x-load/COLL early issue: re-measure SM.MATVEC with a double-buffered x-store once the compiler rule lands.

## TOKEN-LEAD combined row (10-20)

`combined_1020/`: `measured_rel_i8_su.json` = `measured_rel_int8.json` (HBM-QINT8) with SU.VOP from `units/su.json` (HBM-SUFIX);
census `--measured --bw 98 --bridge 1` on ot-epyc6 (`rel98_i8_su.json`), row info_banklat_all: **DS 1,109.7 / Qwen 372.2 tok/s**.
Grades (`cycles_rel98_i8_su.json`, units = coll/idxdma/su + att_mb + smhbm_int8), share of used unit cycles:
DS measured-on-bound 31.3% + measured-not-bound 58.7% = 90.0% measured, model 10.0%;
Qwen 57.8% + 41.0% = 98.8% measured, model 1.2% (the Qwen crit attribution is still broken, see HBM-SUFIX coll note).
Qwen is SU-reduction bound as built (softmax ~1.6M of 3.22M cycles): the pre-tree bind (HBM-PRETREE2) is the lever.

## Files

- `cycles.json`: scenarios and the per-class table (grade, used vs price, critical-path cycles).
- `measured_rel.json`: the exact `--measured` input.
- `units/` (att serial, coll, idxdma, su, smhbm = successor p80).
- `units_variants/`: att_mb (used in the release row), smhbm_p96, smhbm_h9b_bound.
- Bench and runs: branch `claude/toksim-hbm-smhbm-1019` (`results/rtl/toksim_hbm_smhbm_1019/runs`).
- Fleet: `ot-epyc5:/srv/opentallas-scratch/claude/toksim-smhbm-1019/out`, `ot-epyc6:/srv/opentallas-scratch/claude/toksim-hbm`.

## HBM-SUFIX (10-20): SU.VOP measured, ROW_NORM cause, COLL classification

Branch `claude/hbm-sufix-1019`. Files: `units/su.json`, `units_variants/su_rownorm_pretree.json`, `sufix/recompose_su.json`, `sufix/coll_classify.json`.

**(a) SU.VOP compiler bug, fixed.** `prod_compile.py` had six defects:
- `LIN` was 32 instead of 28. The lane writes 28 edges after emit at MLAT 4 / LEAF 1.
- Unused operand streams had vb 0, so quarters 1..3 read outside their own quarter. That raised the slice `st_id_fault`, which explains why only q1..q3 faulted.
- Control lines went to 0 after the last emit. The lane takes each stage's op fields from the LIVE line (lane header), so `co_dst` was 0 at OUT and nothing was written.
- The fill pin edge was E+RR+3 instead of E+RR+2.
- The RF drain was one edge early. It must be strictly after the RF commit, as in `su_top_compile`.
- The per-row RF scalar was taken once per issue, although one issue spans several rows. Rows now get their own issues, and `ni` is set per issue.

There is also one compiler workaround for an RTL mismatch. The SIDE pipe is built at MLAT 3 while the bound lane runs at MLAT 4, so side elements are now spaced (lane depth - side depth + 1) apart. The RTL lever is a side pipe at the lane's MLAT.

Result:
- 32/32 record programmes PASS bit-exact on the bound `ot_hbm_su_static_top` (mr10 = die-bound SRD 12 / SWD 10, Verilator 5.050).
- The +MUT_DATA mutant FAILs (`results/rtl/toksim_hbm_su_1019/suvop/runs/mutant`).
- Coverage of the class model_sum: DS 89.6%, Qwen 95.0%.
- Light VOPs sit at about their price (80-105 vs 85-101).
- Reductions are 2-38x their price. The as-built reducer takes ONE lane operand per quarter per edge, because GEN2e3 die.v has no pre-tree. Examples, measured vs price in stream edges:
  - DS q_norm.ss: 835 vs 209
  - DS attend max640: 664 vs 202
  - Qwen softmax.exp_sum (8 x 8192): 22,316 vs 590
  - Qwen softmax.max: 22,243 vs 399

No compiler schedule can beat 16,384 operand-edges per quarter. Caveat: the golden is the calendar's chain/tree order (exact against the independent NumPy golden in that order), not yet checked against the model's softmax/norm reduction order.

**(b) ROW_NORM.** The cause is the same ingress limit: 128 LOAD + 1024 ADD_EXT + 127 TREE command slots per quarter for d4096. It is not rsqrt or a re-launch. The best compiler-only schedule is still 8.3x the price. The lever is the closed HH-6 pre-tree (`hbm_su_pretree_s_1018-p3`), which is not bound in die.v (H.STA.BLK.16.6, LEAD2-HBM). Benched at the ROW_NORM shapes, bit-exact: d4096 672 / q 491 / k 477 vs 200 / 150 / 150. What remains is the fixed serial chain: pre-tree 80, two RF transits of 45, rsqrt 74. The next lever is a reducer -> rsqrt -> broadcast scalar bypass (about -100).

**(c) COLL 1.24x.** Qwen ALL_REDUCE runs 6 dependent TP8 hypercube steps at about 178-193 each, against a TP4 calibration price. Reduce-scatter publishes 0.5 word/edge, and the TX calendar uses 4 of 5 slots. In DS GROUP_REDUCE_MCAST the switch crossings are on price; the endpoint serialisation is not.
- L1 (fuse the last RS with the first AG) is compiler-only: Qwen +9.8 tok/s.
- L1..L5 gives DS 1184 / Qwen 1031.
- See `sufix/coll_classify.json`.

**Recomposition** (census `--measured`, bw 98, bridge 1; deltas against the 1163.0 / 1003.3 base):

| row | DS AR tok/s | Qwen AR tok/s |
|---|---:|---:|
| TOKSIM-HBM release, SU.VOP model | 1163.0 | 1003.3 |
| + SU.VOP measured (as-built SU, no pre-tree) | **1110.1** | **417.5** |
| + ROW_NORM on the HH-6 pre-tree (not bound) | 1110.1 | 429.3 |
| estimate: pre-tree for ALL SU reductions (unmeasured) | ~1150 | ~990 |

On the die as built, Qwen is SU-reduction bound: softmax is about 1.6M of 2.87M cycles per token. Binding the pre-tree (with a MAX mode for softmax.max) is the release-critical lever.
