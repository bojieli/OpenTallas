HBM-ATTGAP cross-SM ATT.PV merge on the SU lane store (tb_su_static_arithmetic, real N512 SU lanes + pinned store, MLAT4/ALAT3/LEAF1),
20 RTL sub-run PV nodes (unit/L2_s32_pos.nodes.npz), pairwise tree pad 32. Driver tools/hbm_layer_vehicle/run_att_gap.sh SKIP_UNIT=1 MEM_SU=400 @c501ae160,
Verilator 5.050, ot-epyc6 /srv/opentallas-scratch/claude/hbm-attgap6/run/merge (collected 10-19 06:06 by TW4-HBM).
pos.log: SU_ARITH PASS (163,840 outputs, 327,680 checks, II 1). Witnesses: mut_ADDR / mut_PHASE / mut_DATA / mut_ORDER all FAIL (SU_ARITH ERROR).
