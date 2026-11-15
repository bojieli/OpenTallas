# SIGNED-TERMINAL-1115 handoff (11-15 14:4x PST)
Fix: branch claude/signed-terminal-1115 @e66a29d91bc (READY posted, GATE main=f846153278a pass=6/6). Merge -> wave treats SIGNED-UNVERSIONED as signed (terminal).
Exported 7 signed items missing from AGIdock INDEX (AGI /archive/opentallas-signed-1114/<die>/<el>/{6_final.*,signoff.json}; rtx /home/ubuntu/signed-export-1114/<die>/<el>/; INDEX rows on both, status ARCHIVED-BOTH-NO-VIEWPACK, sha256 equal rtx vs AGI):
s81/slice_station__t6__cl0755c26e 3c1052f8dbdf; s81/slice_station__t27 d3173fbd70a8; s81/slice_station__t49 e630166e76aa; s81/slice_station__t42__clcf44e680 b121dfb4ac89; qwen_compute/slw_su_l0__cl1e5219ea 877cf0d354aa; qwen_compute/slw_su_l0__cl1a1c1f8f 9f815318ca06; qwen_compute/sle_su_l0__cl086d85ba a9dbb5eaba65.
Other 13 of the 20 already in INDEX by element name (11-14 records): hd_st_n4, hd_mesh_e, hd_tile, t8, t22, t26, t24__cl66b71008, t24__cleece78ec, t30__cl1653104c, t40__cl1ea9de02, t40__clc8fb2c8c, t42__cl4bd1432c, t6__cl54a9ceeb.
Relaunches after sign-off: 63 across 18 items (plan_h2_2249 8, B6gsl 21, B6gE 18, HEAD source_plan 12, QC zz_s29 4); 9 items (t22 t24eece t26 t30 t40x2 t42cl4bd t8) have different block keys B6gsl vs B6gE (legit change); others not provable (state keeps last attempt per block).
Export script: rtx /home/ubuntu/st1115_export.sh, log /home/ubuntu/st1115_export.log.
