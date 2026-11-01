d44o = d44n (die_plan.json 243ff7d018ba UNCHANGED, core_conns.json e689ac2475d8) + core_macros.json 3bca79b4624e
(DIE-HBM-53 10-31, OWNER 07:1x one-block NO_RECIPE plan event; base core_macros 0aec701442c6 = d44n).
Static SRAM sites (core_macros_fix --static, S.json = results/die_hbm_1031/dhbm53/q3/S3.json from mkS3.py) for the 2 q3 coll
cores whose macro positions were UNKNOWN:
 - ot_hfd_coll_q3_body_core 578.88x1054.08: 11 SRAMs (6 x 1r1w_256x256 issuer mem lo/hi + 5 x 1rw_256x64 meta/u_flow), one
   column centred on the clock entry x 289.44, split below/above the island [285.12,522.72,293.76,531.36] (q2n2 body form
   without the link banks).
 - ot_hfd_coll_q3_edge_core 216x1054.08: 12 x 1r1w_64x512 (u_link0..2 g_bank[0..3]), the r15 k3m centred column in abutted
   pairs with 10.848 channels, split around the island [103.68,522.72,112.32,531.36]; W/E pin faces keep ~22.4-um bands.
Names = yosys flatten of the plain-path kit RTL (views @e9fac1f891ac / @9bacba9ba155). Outlines / pins / clock entries unchanged.
G0 966 -> 964 WARN, G0C 1183 -> 1181 WARN, errors 2 / 10 unchanged: exact new 0, gone 2 (clock_entry_macro "macro positions
UNKNOWN" for q3 body/edge) [g0/g0*_delta.txt]. Kits (plain autopilot gen, recipes_b2 rows + hand clock wrappers): q3 vm/edge/
body GEN_OK, GEN_LINT PASS issues 0, KIT_PREFLIGHT --contract PASS issues 0 (results/die_hbm_1031/dhbm53/q3/gen5.tsv); renders
viewed (q3/png).
