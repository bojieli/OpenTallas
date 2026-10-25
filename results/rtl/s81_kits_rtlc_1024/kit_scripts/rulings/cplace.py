import sys
f = sys.argv[1] + "/physical/die_plan/s81/gen_plan_v4.py"; s = open(f).read()
a = '''    "C:xrt1": dict(cores=_C_COMMON + [dict(inst="u_c.u_xr", module="ot_s81sl_xrt1", plan_core="xg_xr", cells=67849,
                                           lef=_rt("s81sl_xrt1", "ot_s81sl_xrt1"))], gaps=_C_GAPS),
    "C:xrt3": dict(cores=_C_COMMON + [dict(inst="u_c.u_xr", module="ot_s81sl_xrt3", plan_core="xg_xr", cells=78456,
                                           lef=_rt("s81sl_xrt3_b", "ot_s81sl_xrt3"))], gaps=_C_GAPS),'''
b = '''    # S81-KITS-RTLC 10-24 (ruling c): explicit hub-C placement = the former shelf rows (cap | xr | eg) with xfin moved
    # under eg (centred, 17.28 um gap): the xfin -> eg copy link (core_conns C:xrt*: xf e_* N face -> eg i_* S face)
    # faces its partner in every type; y-mirror only (the shelf packer never chose an x mirror for the hub C types)
    "C:xrt1": dict(cores=_C_COMMON + [dict(inst="u_c.u_xr", module="ot_s81sl_xrt1", plan_core="xg_xr", cells=67849,
                                           lef=_rt("s81sl_xrt1", "ot_s81sl_xrt1"))], gaps=_C_GAPS,
                   place={"u_c.u_cap": (34.56, 34.56), "u_c.u_xr": (388.8, 34.56), "u_c.u_xf": (751.68, 34.56),
                          "u_c.u_eg": (717.12, 233.28)}, mirrors=((False, False), (False, True))),
    "C:xrt3": dict(cores=_C_COMMON + [dict(inst="u_c.u_xr", module="ot_s81sl_xrt3", plan_core="xg_xr", cells=78456,
                                           lef=_rt("s81sl_xrt3_b", "ot_s81sl_xrt3"))], gaps=_C_GAPS,
                   place={"u_c.u_cap": (34.56, 34.56), "u_c.u_xr": (388.8, 34.56), "u_c.u_xf": (1010.88, 34.56),
                          "u_c.u_eg": (976.32, 233.28)}, mirrors=((False, False), (False, True))),'''
assert s.count(a) == 1; open(f, "w").write(s.replace(a, b)); print("ok")
