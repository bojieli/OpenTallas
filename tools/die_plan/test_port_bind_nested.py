"""HEAD-BIND-4 2026-10-27 (COORD ruling on HEAD-CORE-R13 ASK4): nested leaf-pin port-bind + per-instance ID straps.
    python3 -m pytest -q tools/die_plan/test_port_bind_nested.py
The OLD hd_serdes wrapper (committed evidence results/arch/head_rtl5_1026/cand/gen/ot_s81hd_serdes.sv: ot_pdie_serdes u_phy
with only .rx/.tx bound, 514-b coll_o0_d into the 512-b rx) passed the die-top port-bind; the nested check must FAIL it."""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import gen_rtl  # noqa: E402
import gen_phys  # noqa: E402
import port_bind_gate as PBG  # noqa: E402
import schema as S  # noqa: E402
import sdc_lint  # noqa: E402
import straps as STR  # noqa: E402

PLAN = ROOT / "physical/die_plan/s81_head/die_plan.json"
OLD_SERDES = ROOT / "results/arch/head_rtl5_1026/cand/gen/ot_s81hd_serdes.sv"


def _src(*rel):
    return [(ROOT / r).read_text(errors="replace") for r in rel]


def test_nested_fails_on_old_unbound_serdes_form():
    r = PBG.nested_check({"ot_s81hd_serdes.sv": OLD_SERDES.read_text(), "ot_dp_cells.sv": gen_rtl.CELLS},
                         _src("rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv"))
    assert r["verdict"] == "FAIL"
    unb = set(r["examples"]["unbound"])
    for pn in ("clk", "rst", "st", "pma_tx", "pma_tck", "pma_rx", "pma_rck"):
        assert f"ot_s81hd_serdes.u_phy (ot_pdie_serdes).{pn}" in unb
    assert any("u_phy (ot_pdie_serdes).rx: port 512 b" in x for x in r["examples"]["width_mismatch"])


@pytest.fixture(scope="module")
def gen_new(tmp_path_factory):
    raw = S.load(str(PLAN))
    out = tmp_path_factory.mktemp("gen")
    files = gen_rtl.write_rtl(raw, out, str(ROOT), ["hd_serdes", "hd_tile"], plan_path=PLAN)
    return raw, out, files


def test_nested_passes_new_serdes_and_tile(gen_new):
    raw, out, _ = gen_new
    src = []
    for tn in ("hd_serdes", "hd_tile"):
        src += _src(*raw["partition_types"][tn]["sources"])
    wr = {p.name: p.read_text() for p in out.glob("*.sv") if p.name != "s81_head_top.sv"}
    r = PBG.nested_check(wr, src)
    assert r["verdict"] == "PASS", r["examples"]
    assert "ot_s81hd_serdes_link u_phy" in (out / "ot_s81hd_serdes.sv").read_text()
    # removing one leaf binding of the new form is caught again (nothing silently passes)
    bad = dict(wr)
    bad["ot_s81hd_serdes.sv"] = bad["ot_s81hd_serdes.sv"].replace(".pma_rck(pma_rck)", ".pma_rck()")
    r2 = PBG.nested_check(bad, src)
    assert r2["verdict"] == "FAIL" and "ot_s81hd_serdes.u_phy (ot_s81hd_serdes_link).pma_rck" in r2["examples"]["unbound"]


def test_die_top_ties_only_declared_straps_per_instance(gen_new):
    raw, out, _ = gen_new
    top = (out / "s81_head_top.sv").read_text()
    man = json.loads((out / "parent_id_straps.json").read_text())
    assert set(man["types"]) == {"hd_tile"} and len(man["instances"]) == 264
    vals = sorted((v["strap_row0"]["value"], v["strap_ten"]["value"]) for v in man["instances"].values())
    assert sum(t for _, t in vals) == 253 and vals.count((0, 0)) == 11
    assert len({r for r, t in vals if t}) == 253          # every used tile its own bundle row
    mods = {t["module"]: tn for tn, t in raw["partition_types"].items()}
    aud = STR.audit_top_ties(top, man, mods)
    assert aud["verdict"] == "PASS" and len(aud["rows"]) == 2 * 264
    aud2 = STR.audit_top_ties(top.replace(".strap_ten(1'd1)", ".i(565'd0)", 1), man, mods)
    assert aud2["verdict"] == "FAIL"
    w = (out / "ot_s81hd_tile_p.sv").read_text()
    assert "ot_s81hd_strap" not in w and ".row0(strap_row0)" in w and ".ten(strap_ten)" in w


def test_schema_requires_exact_instance_straps():
    raw = json.loads(PLAN.read_text())
    assert S.validate(raw) == []
    bad = copy.deepcopy(raw)
    p = next(p for p in bad["partitions"] if p["type"] == "hd_tile")
    del p["id_straps"]["strap_ten"]
    assert any("id_straps" in e for e in S.validate(bad))
    bad = copy.deepcopy(raw)
    next(p for p in bad["partitions"] if p["type"] == "hd_tile")["id_straps"]["strap_ten"] = 2
    assert any("does not fit" in e for e in S.validate(bad))
    bad = copy.deepcopy(raw)
    bad["partition_types"]["hd_tile"]["id_straps"][0]["width"] = 16
    assert any("not an approved ID strap" in e for e in S.validate(bad))


def test_kit_sdc_false_paths_the_straps():
    P = S.Plan(S.load(str(PLAN)), PLAN)
    txt = gen_phys.sdc(P, "hd_tile", None)
    assert "set_false_path -from [get_ports {strap_row0 strap_ten}]" in txt
    ctx = sdc_lint.kit_context(P, "hd_tile")
    assert ctx["straps"] == ["strap_row0", "strap_ten"]
