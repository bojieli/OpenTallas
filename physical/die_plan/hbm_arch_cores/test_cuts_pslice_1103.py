"""DIE-HBM-61/CUTS 11-03: pslice_c5 dictionary-path cut recipes (pin-cycles lever, OWNER 18:5x).
The cut recipes read the tree (the pgcol r5 producer is wrapped in generate g_p there), keep every default of the shared
programme RTL, and remap the plan's as-built macro names u_c.u_p -> u_c.g_p.u_p (macro_inst_sub)."""
import csv, json, re
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
P = REPO / "rtl/hbm_accel/generic/adapters/static_su/programme"


def _rec():
    return json.loads((HERE / "recipes_b2.json").read_text())


def test_dcut_recipes_params_and_cycles():
    rows = list(csv.DictReader(open(REPO / "physical/die_plan/hbm/reform_1103/cycles/cuts_pslice.tsv"), delimiter="\t"))
    for key, dk in (("ot_hbm_su_programme_pslice_c5__dcut3", 3), ("ot_hbm_su_programme_pslice_c5__dcut4", 4)):
        r = _rec()[key]
        p = r["params"]
        assert p["SB"] == 2470 and p["DRLY"] + p["DBREG"] + (1 if p["DGRP"] > 0 else 0) == dk
        assert r["read_at_commit"] is False and r["top"] == "ot_hbm_su_programme_pslice_c5"
        assert r["files"] == _rec()["ot_hbm_su_programme_pslice_c5"]["files"]
        out = [x for x in rows if x["core"] == key and x["port_or_bus"].startswith("busy")]
        assert out and out[0]["plus_cycles"] == f"+{dk}"


def test_macro_inst_sub_maps_every_plan_macro_to_tree_scope():
    cm = json.loads((REPO / "physical/die_plan/hbm/plan_of_record/d44v/core_macros.json").read_text())
    names = [m["name"] for m in cm["cores"]["ot_hbm_su_programme_pslice_c5"]["macros"]]
    sub = _rec()["ot_hbm_su_programme_pslice_c5__dcut3"]["macro_inst_sub"]
    for n in names:
        for pat, repl in sub:
            n = re.sub(pat, repl, n)
        assert re.fullmatch(r"u_fcore\.g_c\[\d\]\.u_c\.g_p\.u_p\.g_m4\.(dt|ix)\[0\]\.mem\.g\[\d+\]\.mem", n), n
    assert len(names) == 100


def test_cut_params_default_off():
    s = (P / "ot_hbm_su_programme.sv").read_text()
    assert "parameter integer DRLY=0, DBREG=0, DGRP=0" in s
    assert "parameter integer BANKS=1, OG=2, GRP=0, RS=4, MUT=0, BREG=0" in s
    g = (P / "ot_hbm_su_programme_pgcol.sv").read_text()
    assert g.count("DRLY=0, DBREG=0, DGRP=0") == 2      # pgcol + pslice_c5 cluster top
    # pslice_c5 trunk form and the S/L leaf masters do not set the cuts
    assert ".DRLY(" not in g[g.index("`else\n// DIE-HBM-57/PSLICE"):]
    for m in ("ot_hbm_su_programme_pgcol_s", "ot_hbm_su_programme_pgcol_l"):
        blk = g[g.index("module " + m + "("):]
        assert ".DRLY(" not in blk[:blk.index("endmodule")]
