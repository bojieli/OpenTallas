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
| **MEASURED release**: successor PC + rotated layout, multi-block attention, Qwen 1 KV head/die | **1,162.5** | **1,002.9** |
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
3. **Qwen packed-INT8 stream is rejected by the bound svg S1 feed** (`q_*` runs FAIL at every pace). This is a die-integrity defect. Qwen was therefore measured BF16-widened at TP-8 rows/SM (R = m_TP4/32; HBM-RATE-DROP 2a), and INT8 = BF16w span - blocks/2 x per-block cadence + 256. That rule is an affine law (fixed 108 + 88/block, residual <=14), and the LM head uses the same law.
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

## Files

- `cycles.json`: scenarios and the per-class table (grade, used vs price, critical-path cycles).
- `measured_rel.json`: the exact `--measured` input.
- `units/` (att serial, coll, idxdma, su, smhbm = successor p80).
- `units_variants/`: att_mb (used in the release row), smhbm_p96, smhbm_h9b_bound.
- Bench and runs: branch `claude/toksim-hbm-smhbm-1019` (`results/rtl/toksim_hbm_smhbm_1019/runs`).
- Fleet: `ot-epyc5:/srv/opentallas-scratch/claude/toksim-smhbm-1019/out`, `ot-epyc6:/srv/opentallas-scratch/claude/toksim-hbm`.
