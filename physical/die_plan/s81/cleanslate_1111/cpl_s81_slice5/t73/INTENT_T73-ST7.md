# INTENT T73-ST7 (CPL-S81-SLICE-5, DO_NOT_COUNT) - ot_s81sl_leaf__t73, base BASE_1200 b5faa1ba, on ST4 3fc469806972
Form: S81-LEAF-CYC quad form (e46e22c3d777: CS_HI_D/GS 1, CS_HO_D/GS 1, CS_H_G 4; one hi + one ho register per 4-lane quad
u_vp.g_hig[g]/g_hog[g]). Positions only for the cores; lanes are identical hcpost cores, so lane index -> slot is a permutation.
Dataflow: leafdn_i0 (S, 597 b) -> vn_a/vn_b -> vp glue -> quad register (street) -> 4 lanes (W-face r/y inputs);
lanes o/vo/fault (18 b/lane, E face) -> quad ho register -> glue -> vn hw_d. vs hub -> ve_m 1484 b, vsw 642 b, vq 542 b.
Arrangement: ST4 W/A ft streets and the W cores kept. Street B kept 147 um; ve_m/ve_s/vsw/vs/rxsf/rxsb lifted 86.4 um: S landing strip y 0-129.6 for the ft7/ft8/ft0-5 S windows (they landed under ve_m/ve_s);
vn/vq/b0/b1 at ST4. vn|g_ln station street x 1125.36-1166.4 (41 um).
Lanes: 2 columns x 1166.4 / 1321.92 (gap 41.04), rows y 8.64 + k*155.52 (gaps 41.04), 8.64 lattice; quad g = lanes 4g..4g+3 on rows 2g,2g+1
(2x2). Quad hi/ho site on the street at x 1145.88, y = quad centre pulled <= 60 um toward the vn pins.
Reach (LEAF-CYC criteria): vn pin -> quad <= 810 through the glue flop, quad -> lane <= 405.
Pin cycles (approved, S81-ARCH-RTL-2 a754fcbe5bd7f2b5d): vs -> vq +1 station (CS_U_D 1, 7 buses), leafdn_i0 -> vs 1 -> 2 stations;
applied after the positions composer as a separate station patch (pc.py), since they change station counts.
