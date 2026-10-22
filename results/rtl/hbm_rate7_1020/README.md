# HBM-RATE7 (10-20): rate fixes rebased on origin/main, re-verified, composed, GEN2e5 bind delta

Branch `claude/hbm-rate7-1020` = origin/main (c0768b96a) + merge `claude/hbm-pretree3-1020` (9c676918f) + merge
`claude/hbm-collfuse2-1020` (ef2c973e5; prod_compile RECS conflict = both additive, kept both) + cherry-picks (`-x`) of the
rate-fix commits of `claude/hbm-smxl2-1020` (TOKSIM-HBM-smhbm 4383c03a8.. -> SMXL2 bd894467d; 1916a43ac skipped: its
toksim-hbm import is older than pretree3's) and of `claude/hbm-smint8w-1020` (QINT8 6dcf0de0f.. -> QINT8B 68410eee7).
The older GEN2e die-lineage commits on those branches (10-17..10-19 16:42) are NOT carried: main already holds their
successors. Conflicts resolved: tb_toksim_smhbm.sv (PTRACE + i8v_n both kept), ot_hbm_accel_smh_attn.sv (main's
ENABLE_INT8 1 = hard SAFE tile comment + INT8W param), qwen_sm_mv_unit.py (main's hard-tile file list + i8w rtl string).
No closure_loop / ref_tile / common_flow / hier_contract / tt_views file touched -> no Gate-Rule trailer needed.

## Re-verification on the rebased tree (Verilator 5.050, ot-run unpinned)
| bench | rebased result | original lane result |
|---|---|---|
| SMXL xl_dsA_f200 (MC3, XSLOT+OPEN_IL, FETCH 200) | PASS 42/42, GO 95/95 exact, 18,429 | 18,429 |
| SMXL xl_dsB_f200 | PASS 24/24, GO 169/169 exact, 21,941 | 21,941 |
| SMXL mutant IMUT4 dsA | FAIL 18/42 numerically at identical GO (witness) | FAIL |
| INT8W unit L0 qkv/o/gu/down (wide front) | 4/4 PASS bit-exact, calendar 3156/1916/7764/4484, cmd+pkt SHA identical | identical SHA |
| INT8 narrow regression (main hard tile ENABLE_INT8 1) | 4/4 PASS, 4700/2948/13916/7564 | same calendar |
| INT8W mutants wbit halfswap nopkt late tag sign noswap half | all 8 FAIL (witness logs) | FAIL |
`smxl_rebased/`, `i8w_rebased/` (runner fix: run_qwen_i8w_unit.sh now archives ot_smh_int8_tile.sv, needed by main's
ENABLE_INT8 1 hard tile).

## Composed census (`census/`, census --measured info_banklat_all --bw 98 --bridge 1 + HBM-SUFIX delta rule)
Inputs = PRETREE3 m_pt3_tp8 + DS SM.MATVEC from SMXL2 measured_pt3_xl + Qwen SM.MATVEC from QINT8B m_i8w + Qwen
COLL.ALL_REDUCE_SUM / SU.VOP from COLLFUSE2 m_p3 (each touches disjoint unit classes).
| input | DS tok/s | Qwen tok/s |
|---|---|---|
| m_base (PRETREE3 reproduction) | 1148.8 | 1000.7 |
| m_xl_i8 (+SMXL, +INT8W) | 1341.1 | 1001.5 |
| m_all (+COLLFUSE2 L1 fuse + TP-8 rows) | **1341.1** | **1011.3** |
COLLFUSE2's standalone 1022.8 used the BF16w SM law; with the measured INT8W SM the composed Qwen is 1011.3.
Qwen TP-8 row stays PROVISIONAL until the MUT_FORCE witnesses land (pending_results HBM-RATE7).

## Next lever probe: HBM supply pace (`pace/`)
pc64_dsB PASS 21,842 (vs 21,941 at pace 80: -0.5 %); pc72_dsA and pc64_dsA FAIL issuer fault cycle 9619 (49/95 GO, the
distinct-row routed-expert fetch law). Pace 80 is NOT the binding SM constraint -> no rate lever there (REJECTED).

## DS gap to 1,600-1,700 (m_all critical path, 868.6k sched / 894.8k token cycles; 1,650 needs ~727k)
SM.MATVEC 242k crit (780 recs), COLL.ALL_GATHER 174k (445 crit; 280 expert_intermediate gathers x 276 = 77k),
SU.VOP 102k, COLL.GROUP_REDUCE_MCAST 72k, ATT.PV 41k, COLL.TOPK_MERGE 39k, FUSED.HC_PRE_NORM 30k, ATT.QK 28k, ROW_GATHER 22k.
Known measured/priced levers sum to ~-30..40k (VMEARLY gq IA1 ~-18k, COLL L4 RS->AG cut-through ~-8k, L5 ~-2k, SU
scalar bypass): ~1,400 tok/s. 1,600+ needs a structural change on the AG/SM chain (e.g. batching the 7 per-layer
expert-intermediate gathers into one record, or overlapping AG with the consuming SM).

## GEN2e5 bind delta
`tools/hbm_die_v16/d4g_layers/l24_sm_xslot_i8w.py` (after l23): svg XSLOT=1 OPEN_IL=1, xc XSLOT=1, sm INT8W=1 (+ deps);
parameter-only, ports/edges unchanged; op_xb bound through descriptor[206:200] on the existing cp_svg desc edges.
`l24_report_on_gen2e4_pre_relay_l23.json`: changed 48 on GEN2e4 pre_relay + l23, re-application 0, l15.apply PASS.
Handed to HBM-DIE7 (lanes/HBM-DIE7.md NOTICE). Owed: master re-synth + PRE-GATE native32 census before any gate.
