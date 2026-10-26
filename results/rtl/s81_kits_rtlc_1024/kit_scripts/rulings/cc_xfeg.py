import sys
f = sys.argv[1] + "/physical/die_plan/s81/gen_plan_v4.py"; s = open(f).read()
a = '''        "u_eng.u_h1": _cc(**{"in_w,out_res": ["core:u_eng.u_e"]}),
    },
}'''
b = '''        "u_eng.u_h1": _cc(**{"in_w,out_res": ["core:u_eng.u_e"]}),
    },
    # S81-KITS-RTLC 10-24 (ruling c): the slice hub C xfin -> eg copy link (ot_s81sl_slice_c1x / c3x xe_*): the re-pinned
    # xfin table carries e_v / e_c / e_hh / e_kk / e_dd (N face, M5) and eg reads them on i_*
    **{k: {"u_c.u_xf": _cc(**{"e_v,e_c,e_hh,e_kk,e_dd": ["core:u_c.u_eg"]}),
           "u_c.u_eg": _cc(**{"i_v,i_c,i_hh,i_kk,i_dd": ["core:u_c.u_xf"]})} for k in ("C:xrt1", "C:xrt3")},
}'''
assert s.count(a) == 1; open(f, "w").write(s.replace(a, b)); print("ok")
