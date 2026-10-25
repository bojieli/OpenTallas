# S81/PORTFIX core_conns findings (2026-10-25)

Derived core connectivity (physical/die_plan/s81/core_conns_derive.py -> physical/die_plan/s81/inputs/core_conns_derived.json, yosys on the repo RTL, cores black-boxed, DIRECT core-core / core-port nets only) for the 14 hard-core types CORE_CONNS did not list. Consumed by G0C, every one of them has core ports on the far face from their partner (core_faces ERROR, mean cos < -0.1). Not consumed yet (gen_plan_v4.PF_DERIVED_USE = empty) so G0/G0C stay at 0; each type needs a core re-pin / re-site by its owner + GEOM review, then its module goes into PF_DERIVED_USE.

| type | ports facing away |
|---|---|
| bk_sel__t2 | 15 |
| col_h10_r0_p1__t1 | 109 |
| col_h10_r0_p4__t1 | 109 |
| col_h10_r1__t1 | 102 |
| col_h10_r2__t1 | 88 |
| col_h9_r0_p1__t1 | 94 |
| col_h9_r0_p2__t1 | 94 |
| col_h9_r0_p3__t1 | 94 |
| col_h9_r0_p4__t1 | 94 |
| col_h9_r0_p5__t1 | 94 |
| col_h9_r0_p6__t1 | 94 |
| col_h9_r1__t1 | 84 |
| col_h9_r2__t1 | 75 |
| gunit__t1 | 14 |

Listed examples (check.py prints 5 per type):

```
ERROR [core_faces] type bk_sel__t2 core u_bk_sel.u_sel.g_q[0].u_q port t_o: 354 pins on face W face away from its partner(s) u_bk_sel.u_sel.u_c: mean cos -1.00, 354 pins on the far side (re-pin to face E)
ERROR [core_faces] type bk_sel__t2 core u_bk_sel.u_sel.g_q[1].u_q port t_o: 354 pins on face W face away from its partner(s) u_bk_sel.u_sel.u_c: mean cos -1.00, 354 pins on the far side (re-pin to face E)
ERROR [core_faces] type bk_sel__t2 core u_bk_sel.u_sel.g_q[2].u_q port f_c: 66 pins on face N face away from its partner(s) u_bk_sel.u_sel.u_c: mean cos -0.13, 66 pins on the far side (re-pin to face E)
ERROR [core_faces] type bk_sel__t2 core u_bk_sel.u_sel.g_q[2].u_q port f_cr: 1 pins on face N face away from its partner(s) u_bk_sel.u_sel.u_c: mean cos -0.13, 1 pins on the far side (re-pin to face E)
ERROR [core_faces] type bk_sel__t2 core u_bk_sel.u_sel.g_q[2].u_q port lane: 515 pins on face N face away from its partner(s) u_bk_sel.u_sel.u_g: mean cos -0.11, 515 pins on the far side (re-pin to face E)
ERROR [core_faces] type col_h10_r0_p1__t1 core u_r0.u_bn3 port e_r0: 63 pins on face S face away from its partner(s) u_r0.u_e3: mean cos -0.71, 63 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h10_r0_p1__t1 core u_r0.u_bn3 port e_st: 2 pins on face S face away from its partner(s) u_r0.u_e3: mean cos -0.71, 2 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h10_r0_p1__t1 core u_r0.u_bs2 port i_cfg: 54 pins on face S face away from its partner(s) u_r0.u_s2: mean cos -0.89, 54 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h10_r0_p1__t1 core u_r0.u_bs2 port i_go: 1 pins on face S face away from its partner(s) u_r0.u_s2: mean cos -0.89, 1 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h10_r0_p1__t1 core u_r0.u_bs3 port i_x0: 283 pins on face S face away from its partner(s) u_r0.u_t3: mean cos -1.00, 283 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h10_r0_p4__t1 core u_r0.u_bn3 port e_r0: 63 pins on face S face away from its partner(s) u_r0.u_e3: mean cos -0.71, 63 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h10_r0_p4__t1 core u_r0.u_bn3 port e_st: 2 pins on face S face away from its partner(s) u_r0.u_e3: mean cos -0.71, 2 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h10_r0_p4__t1 core u_r0.u_bs2 port i_cfg: 54 pins on face S face away from its partner(s) u_r0.u_s2: mean cos -0.89, 54 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h10_r0_p4__t1 core u_r0.u_bs2 port i_go: 1 pins on face S face away from its partner(s) u_r0.u_s2: mean cos -0.89, 1 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h10_r0_p4__t1 core u_r0.u_bs3 port i_x0: 283 pins on face S face away from its partner(s) u_r0.u_t3: mean cos -1.00, 283 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h10_r1__t1 core u_r1.u_bs6 port o_cfg: 54 pins on face N face away from its partner(s) u_r1.u_e6: mean cos -0.74, 54 pins on the far side (re-pin to face S)
ERROR [core_faces] type col_h10_r1__t1 core u_r1.u_bs6 port o_go: 1 pins on face N face away from its partner(s) u_r1.u_e6: mean cos -0.74, 1 pins on the far side (re-pin to face S)
ERROR [core_faces] type col_h10_r1__t1 core u_r1.u_bs6 port o_x0: 283 pins on face N face away from its partner(s) u_r1.u_e6: mean cos -0.74, 283 pins on the far side (re-pin to face S)
ERROR [core_faces] type col_h10_r1__t1 core u_r1.u_bs6 port o_x1: 266 pins on face N face away from its partner(s) u_r1.u_e6: mean cos -0.74, 266 pins on the far side (re-pin to face S)
ERROR [core_faces] type col_h10_r1__t1 core u_r1.u_bs8 port i_x0: 283 pins on face S face away from its partner(s) u_r1.u_t6: mean cos -0.91, 283 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h10_r2__t1 core u_r2.u_bn13 port e_r0: 63 pins on face S face away from its partner(s) u_r2.u_e13: mean cos -0.86, 63 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h10_r2__t1 core u_r2.u_bn13 port e_st: 2 pins on face S face away from its partner(s) u_r2.u_e13: mean cos -0.86, 2 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h10_r2__t1 core u_r2.u_bs11 port i_x0: 283 pins on face S face away from its partner(s) u_r2.u_t8: mean cos -0.86, 283 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h10_r2__t1 core u_r2.u_bs11 port i_x1: 266 pins on face S face away from its partner(s) u_r2.u_t8: mean cos -0.86, 266 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h10_r2__t1 core u_r2.u_e13 port busy: 1 pins on face N face away from its partner(s) u_r2.u_bn13: mean cos -0.86, 1 pins on the far side (re-pin to face S)
ERROR [core_faces] type col_h9_r0_p1__t1 core u_r0.u_bs1 port i_cfg: 54 pins on face S face away from its partner(s) u_r0.u_s1: mean cos -0.89, 54 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h9_r0_p1__t1 core u_r0.u_bs1 port i_go: 1 pins on face S face away from its partner(s) u_r0.u_s1: mean cos -0.89, 1 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h9_r0_p1__t1 core u_r0.u_bs1 port i_x0: 283 pins on face S face away from its partner(s) u_r0.u_bs0, u_r0.u_t1: mean cos -0.26, 283 pins on the far side (re-pin to face W)
ERROR [core_faces] type col_h9_r0_p1__t1 core u_r0.u_bs1 port i_x1: 266 pins on face S face away from its partner(s) u_r0.u_bs0, u_r0.u_t1: mean cos -0.26, 266 pins on the far side (re-pin to face W)
ERROR [core_faces] type col_h9_r0_p1__t1 core u_r0.u_bs2 port i_x0: 283 pins on face S face away from its partner(s) u_r0.u_t2: mean cos -0.91, 283 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h9_r0_p2__t1 core u_r0.u_bs1 port i_cfg: 54 pins on face S face away from its partner(s) u_r0.u_s1: mean cos -0.89, 54 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h9_r0_p2__t1 core u_r0.u_bs1 port i_go: 1 pins on face S face away from its partner(s) u_r0.u_s1: mean cos -0.89, 1 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h9_r0_p2__t1 core u_r0.u_bs1 port i_x0: 283 pins on face S face away from its partner(s) u_r0.u_bs0, u_r0.u_t1: mean cos -0.26, 283 pins on the far side (re-pin to face W)
ERROR [core_faces] type col_h9_r0_p2__t1 core u_r0.u_bs1 port i_x1: 266 pins on face S face away from its partner(s) u_r0.u_bs0, u_r0.u_t1: mean cos -0.26, 266 pins on the far side (re-pin to face W)
ERROR [core_faces] type col_h9_r0_p2__t1 core u_r0.u_bs2 port i_x0: 283 pins on face S face away from its partner(s) u_r0.u_t2: mean cos -0.91, 283 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h9_r0_p3__t1 core u_r0.u_bs1 port i_cfg: 54 pins on face S face away from its partner(s) u_r0.u_s1: mean cos -0.89, 54 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h9_r0_p3__t1 core u_r0.u_bs1 port i_go: 1 pins on face S face away from its partner(s) u_r0.u_s1: mean cos -0.89, 1 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h9_r0_p3__t1 core u_r0.u_bs1 port i_x0: 283 pins on face S face away from its partner(s) u_r0.u_bs0, u_r0.u_t1: mean cos -0.26, 283 pins on the far side (re-pin to face W)
ERROR [core_faces] type col_h9_r0_p3__t1 core u_r0.u_bs1 port i_x1: 266 pins on face S face away from its partner(s) u_r0.u_bs0, u_r0.u_t1: mean cos -0.26, 266 pins on the far side (re-pin to face W)
ERROR [core_faces] type col_h9_r0_p3__t1 core u_r0.u_bs2 port i_x0: 283 pins on face S face away from its partner(s) u_r0.u_t2: mean cos -0.91, 283 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h9_r0_p4__t1 core u_r0.u_bs1 port i_cfg: 54 pins on face S face away from its partner(s) u_r0.u_s1: mean cos -0.89, 54 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h9_r0_p4__t1 core u_r0.u_bs1 port i_go: 1 pins on face S face away from its partner(s) u_r0.u_s1: mean cos -0.89, 1 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h9_r0_p4__t1 core u_r0.u_bs1 port i_x0: 283 pins on face S face away from its partner(s) u_r0.u_bs0, u_r0.u_t1: mean cos -0.26, 283 pins on the far side (re-pin to face W)
ERROR [core_faces] type col_h9_r0_p4__t1 core u_r0.u_bs1 port i_x1: 266 pins on face S face away from its partner(s) u_r0.u_bs0, u_r0.u_t1: mean cos -0.26, 266 pins on the far side (re-pin to face W)
ERROR [core_faces] type col_h9_r0_p4__t1 core u_r0.u_bs2 port i_x0: 283 pins on face S face away from its partner(s) u_r0.u_t2: mean cos -0.91, 283 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h9_r0_p5__t1 core u_r0.u_bs1 port i_cfg: 54 pins on face S face away from its partner(s) u_r0.u_s1: mean cos -0.89, 54 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h9_r0_p5__t1 core u_r0.u_bs1 port i_go: 1 pins on face S face away from its partner(s) u_r0.u_s1: mean cos -0.89, 1 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h9_r0_p5__t1 core u_r0.u_bs1 port i_x0: 283 pins on face S face away from its partner(s) u_r0.u_bs0, u_r0.u_t1: mean cos -0.26, 283 pins on the far side (re-pin to face W)
ERROR [core_faces] type col_h9_r0_p5__t1 core u_r0.u_bs1 port i_x1: 266 pins on face S face away from its partner(s) u_r0.u_bs0, u_r0.u_t1: mean cos -0.26, 266 pins on the far side (re-pin to face W)
ERROR [core_faces] type col_h9_r0_p5__t1 core u_r0.u_bs2 port i_x0: 283 pins on face S face away from its partner(s) u_r0.u_t2: mean cos -0.91, 283 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h9_r0_p6__t1 core u_r0.u_bs1 port i_cfg: 54 pins on face S face away from its partner(s) u_r0.u_s1: mean cos -0.89, 54 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h9_r0_p6__t1 core u_r0.u_bs1 port i_go: 1 pins on face S face away from its partner(s) u_r0.u_s1: mean cos -0.89, 1 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h9_r0_p6__t1 core u_r0.u_bs1 port i_x0: 283 pins on face S face away from its partner(s) u_r0.u_bs0, u_r0.u_t1: mean cos -0.26, 283 pins on the far side (re-pin to face W)
ERROR [core_faces] type col_h9_r0_p6__t1 core u_r0.u_bs1 port i_x1: 266 pins on face S face away from its partner(s) u_r0.u_bs0, u_r0.u_t1: mean cos -0.26, 266 pins on the far side (re-pin to face W)
ERROR [core_faces] type col_h9_r0_p6__t1 core u_r0.u_bs2 port i_x0: 283 pins on face S face away from its partner(s) u_r0.u_t2: mean cos -0.91, 283 pins on the far side (re-pin to face N)
ERROR [core_faces] type col_h9_r1__t1 core u_r1.u_n14 port fi: 1 pins on face N face away from its partner(s) u_r1.u_n15: mean cos -0.32, 1 pins on the far side (re-pin to face E)
ERROR [core_faces] type col_h9_r1__t1 core u_r1.u_n15 port fo: 1 pins on face S face away from its partner(s) u_r1.u_n14: mean cos -0.32, 1 pins on the far side (re-pin to face W)
ERROR [core_faces] type col_h9_r1__t1 core u_r1.u_n17 port b: 66 pins on face N face away from its partner(s) u_r1.u_n18: mean cos -0.50, 66 pins on the far side (re-pin to face E)
ERROR [core_faces] type col_h9_r1__t1 core u_r1.u_n17 port fi: 1 pins on face N face away from its partner(s) u_r1.u_n18: mean cos -0.50, 1 pins on the far side (re-pin to face E)
ERROR [core_faces] type col_h9_r1__t1 core u_r1.u_n18 port fo: 1 pins on face S face away from its partner(s) u_r1.u_n17: mean cos -0.50, 1 pins on the far side (re-pin to face W)
ERROR [core_faces] type col_h9_r2__t1 core u_r2.u_e13 port xb_data: 1024 pins on face N face away from its partner(s) u_r2.u_t8, u_r2.u_t8__payload: mean cos -0.76, 1024 pins on the far side (re-pin to face S)
ERROR [core_faces] type col_h9_r2__t1 core u_r2.u_s10 port ce5: 1 pins on face W face away from its partner(s) u_r2.u_c10_5: mean cos -1.00, 1 pins on the far side (re-pin to face E)
ERROR [core_faces] type col_h9_r2__t1 core u_r2.u_s10 port ce6: 1 pins on face W face away from its partner(s) u_r2.u_c10_6: mean cos -1.00, 1 pins on the far side (re-pin to face E)
ERROR [core_faces] type col_h9_r2__t1 core u_r2.u_s10 port q5: 48 pins on face W face away from its partner(s) u_r2.u_c10_5: mean cos -1.00, 48 pins on the far side (re-pin to face E)
ERROR [core_faces] type col_h9_r2__t1 core u_r2.u_s10 port q6: 48 pins on face W face away from its partner(s) u_r2.u_c10_6: mean cos -1.00, 48 pins on the far side (re-pin to face E)
ERROR [core_faces] type gunit__t1 core u_gunit.u_l4r port eps_c: 32 pins on face W face away from its partner(s) u_gunit.u_l4: mean cos -0.99, 32 pins on the far side (re-pin to face E)
ERROR [core_faces] type gunit__t1 core u_gunit.u_l4r port r_f: 1 pins on face W face away from its partner(s) u_gunit.u_l4: mean cos -0.99, 1 pins on the far side (re-pin to face E)
ERROR [core_faces] type gunit__t1 core u_gunit.u_l4r port r_v: 1 pins on face W face away from its partner(s) u_gunit.u_l4: mean cos -0.99, 1 pins on the far side (re-pin to face E)
ERROR [core_faces] type gunit__t1 core u_gunit.u_l5 port vi_n: 276 pins on face N face away from its partner(s) face S (xtier_i1): mean cos -0.13, 276 pins on the far side (re-pin to face E)
ERROR [core_faces] type gunit__t1 core u_gunit.u_l5 port vo_n: 276 pins on face N face away from its partner(s) face S (xtier_o1): mean cos -0.13, 276 pins on the far side (re-pin to face E)
```
