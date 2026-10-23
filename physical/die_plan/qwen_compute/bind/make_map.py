"""Qwen compute: as-built instance -> plan partition map (BINDER 10-23), written to asbuilt_map.json.

CB16 clusters: as-built c16_<col>_<k>, k = 0..3 bottom-far, bottom-near, top-near, top-far (r56 place.tcl y order; the
bottom pair is placed MX, so cluster row 0 faces the slice in both halves, as gen_plan.unit_rect assumes); tile
u_t_<c>_<r> and its column station u_fab.u_x_<c>_<r> -> quad c_<col>_<half><kind>_<c//2><r//2>.  The CB fabric's other
cells are transport (asbuilt.json).  Slices dvs_<col>: the s8 flat parent's children by gen_plan LEAF_REGION / SOFT.
"""
import json
from pathlib import Path

HK = ["bf", "bn", "tn", "tf"]
rules = []
for k, hk in enumerate(HK):
    for cq in (0, 1):
        for rq in (0, 1):
            c, r = f"[{2 * cq}{2 * cq + 1}]", f"[{2 * rq}{2 * rq + 1}]"
            rules.append([rf"c16_([WE]\d)_{k}\.(u_t_{c}_{r}|u_fab\.u_x_{c}_{r})", rf"c_\1_{hk}_{cq}{rq}"])
    rules.append([rf"c16_([WE]\d)_{k}\.u_fab\.\$not\$.*", rf"c_\1_{hk}_00"])      # far_n strap complement
S = r"dvs_([WE]\d)\.u_core\.u_sub\."
SL = [("u_fdn", "fw"), ("u_fup", "fe"), ("u_fn", "hc1"), ("u_frs", "st_a"), ("u_fs", "stm"), ("u_stm", "stm"),
      ("u_rp", "ctl"), ("u_ctl", "ctl"), ("u_suvm", "su_c"), ("u_red", "su_c"), ("u_sc", "sc"), ("u_tap", "tap"),
      ("u_btab", "st_a"), ("u_r[0-3]", "st_a"), ("u_r[4-7]", "st_b"),
      ("u_(lrly|head|exp|rcp|rsq)[0-3]", "su_l0"), ("u_(lrly|head|exp|rcp|rsq)[4-7]", "su_l1"),
      (r"\$or\$.*", "ctl")]
for leaf, reg in SL:
    rules.append([S + leaf, rf"sl_\1_{reg}"])
for h in range(4):
    rules.append([S + rf"u_x(h{h}|l{h}_\d)", rf"sl_\1_hc{h}"])
# collective (QC-FIX coll split, gen_plan COLL_INST_SEG / coll census map): faces S1/S2 -> coll_s, S0 -> coll_n, P/R
# faces + u_collective + u_shared + gearbox + UCIe PHY + bumps -> coll_core; coll_f0-5 are ft-only (plan lanes)
CO = r"io_collective\.u_io\."
rules += [[CO + r"g_face\[[34]\]\..*", "coll_s"], [CO + r"g_face\[2\]\..*", "coll_n"], [r"io_collective\..*", "coll_core"]]
parts = {"io_ucie": "coll_core", "bump_pkg_s0": "coll_core", "bump_pkg_s1": "coll_core", "bump_die_ps": "coll_core",
         "io_serdes": "io_serdes", "io_serdes_1": "io_serdes_1", "io_serdes_2": "io_serdes_2", "ucie_kv": "ucie_kv",
         "tt_ctlm": "tt_ctlm", "native59": "native59",
         **{x: "glue" for x in ("d2d_rom", "sys_face", "embed_prov", "mu_ctxrx", "mu_dhobs", "bump_fwd_epoch",
                                "bump_fwd_lrst")}}
Path(__file__).with_name("asbuilt_map.json").write_text(json.dumps({"parts": parts, "rules": rules}, indent=1) + "\n")
