# DS SV full native composition, source 59a (collected 2026-10-14 by Claude hbm-group-B3)

tb_hgi_su_native_prod, -DSV -DWIDE N=512 M=128 LV=7 LWB=18 LQ=8, DS vectors, ot-epyc4 unit 2489395 (scratch deleted after collection).
- HGI_SU_NATIVE_PROD PASS, 44,936 sink-sector words exact (2 cases).
- THROUGHPUT case 0: service 7,719 vs price 2,912 = 2.651 (stage 5,186 / compute 2,976 / drain 3,839).
  The monolithic VM/SU chain on the same DS vectors measures 2,718 / 2,912 = 0.933: the native SV packet path
  (scalar native VM staging) is the throughput defect, not the SU body. Case 1 (SINK_UNSTAGED) 1,157 / 457 = 2.532, exactness only.
- No mutant in this run; no qualification, no cost acceptance. Diagnostic for the SU.VOP native vehicle.
