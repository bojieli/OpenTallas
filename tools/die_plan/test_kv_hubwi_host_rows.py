"""KV-D23-HUBWI: kv_hubwi_host_rows.py applies the clustered-host row class or changes nothing."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_hubwi_host_rows as R  # noqa: E402

VIEWS = "physical/die_plan/qwen_kvsys/views_x"
MODS = {"qkd_hr_cdc_ch": ["host__qkd_hr_cdc_ch"], "qkd_hr_phy_adp": ["host__qkd_hr_phy_adp_0", "host__qkd_hr_phy_adp_1"]}


def _lef(m, pins, size=(10.0, 20.0)):
    body = "".join(f"  PIN {p}\n    DIRECTION INPUT ;\n  END {p}\n" for p in pins)
    return (f"MACRO {m}\n  SIZE {size[0]} BY {size[1]} ;\n  PIN VDD\n  END VDD\n  PIN VSS\n  END VSS\n{body}END {m}\n")


def _tree(tmp_path, lef_pins=("ck", "d[0]", "d[1]"), size=(10.0, 20.0)):
    tree = tmp_path / "tree"
    pdir = tree / "physical/die_plan/qwen_kvsys/plan_of_record"
    (pdir / "pins").mkdir(parents=True)
    hd = tree / R.HOST_DIR
    for f in R.LEAF_PREFER:
        (tree / f).parent.mkdir(parents=True, exist_ok=True)
        (tree / f).write_text("module leaf(); endmodule\n")
    rows, inst_txt = [], []
    for m, insts in MODS.items():
        (hd / "wrappers_s" / m).mkdir(parents=True)
        (hd / "wrappers_s" / m / f"{m}.sv").write_text(f"module {m}(); endmodule\n")
        vd = tree / VIEWS / m
        vd.mkdir(parents=True)
        (vd / f"{m}.lef").write_text(_lef(m, lef_pins, size))
        (vd / f"{m}_tt.lib").write_text("library(x){}\n")
        (pdir / "pins" / f"{m}.json").write_text(json.dumps(dict(pins=[dict(name=n) for n in ("ck[0]", "d[0]", "d[1]")])))
        for i in insts:
            rows.append(dict(inst=i, module=m, origin_um=[0, 0], outline_um=[10.0, 20.0], orient="R0",
                             pins_file=f"pins/{m}.json", physical_inst="u_bound.u_host." + i, physical_master=m))
            inst_txt.append(f"  {m} {i} (\n    .ck(ck_a)\n  );\n")
    (hd / "parent.sv").write_text("module qkd_host_root_admission_obsx_bo1_c45 ();\n" + "".join(inst_txt) + "endmodule\n")
    plan = dict(partition_types=dict(kv3_hub_Wi=dict(hard_cores=rows + [dict(inst="other", module="qkd_x")])))
    ab = dict(files=["a.sv", R.HOST_OLD], prefer=[R.HOST_OLD, "b.sv"], portbind_prefer=["c.sv"])
    return tree, pdir, plan, ab


def test_rows_applied(tmp_path):
    tree, pdir, plan, ab = _tree(tmp_path)
    p, a, rep = R.apply(copy.deepcopy(plan), copy.deepcopy(ab), tree, VIEWS, pdir)
    hcs = p["partition_types"]["kv3_hub_Wi"]["hard_cores"]
    assert [h.get("lef") for h in hcs] == [f"{VIEWS}/qkd_hr_cdc_ch/qkd_hr_cdc_ch.lef"] + \
        [f"{VIEWS}/qkd_hr_phy_adp/qkd_hr_phy_adp.lef"] * 2 + [None]
    assert hcs[0]["lib"].endswith("qkd_hr_cdc_ch_tt.lib") and "KV-D23-HUBWI" in hcs[0]["note"]
    new = R.HOST_DIR + "/parent.sv"
    assert a["files"] == ["a.sv", new] and a["prefer"] == [new, "b.sv"]
    wr = [f"{R.HOST_DIR}/wrappers_s/{m}/{m}.sv" for m in MODS]
    assert a["portbind_files"] == wr and a["portbind_prefer"] == ["c.sv"] + wr + list(R.LEAF_PREFER)
    assert rep["cycles_changed"] == 0 and len(rep["rows"]) == 3
    # geometry of a hard core is never touched
    for h0, h1 in zip(plan["partition_types"]["kv3_hub_Wi"]["hard_cores"], hcs):
        assert all(h0.get(k) == h1.get(k) for k in ("origin_um", "outline_um", "orient", "pins_file", "physical_inst"))


@pytest.mark.parametrize("break_it,word", [
    (lambda tree, plan, ab: (tree / R.HOST_DIR / "parent.sv").write_text("module x(); endmodule\n"), "parent.sv has 0"),
    (lambda tree, plan, ab: plan["partition_types"]["kv3_hub_Wi"]["hard_cores"][0].update(physical_inst="u_bound.u_x"),
     "physical_inst"),
    (lambda tree, plan, ab: plan["partition_types"]["kv3_hub_Wi"]["hard_cores"][1].update(outline_um=[10.0, 21.0]),
     "LEF SIZE"),
    (lambda tree, plan, ab: (tree / VIEWS / "qkd_hr_cdc_ch/qkd_hr_cdc_ch.lef").write_text(
        _lef("qkd_hr_cdc_ch", ("ck", "d[0]", "e[1]"))), "LEF pins != plan"),
    (lambda tree, plan, ab: (tree / VIEWS / "qkd_hr_phy_adp/qkd_hr_phy_adp_tt.lib").unlink(), "view missing"),
    (lambda tree, plan, ab: (tree / R.HOST_DIR / "wrappers_s/qkd_hr_cdc_ch/qkd_hr_cdc_ch.sv").unlink(), "wrapper missing"),
    (lambda tree, plan, ab: ab["files"].remove(R.HOST_OLD), "asbuilt.files"),
    (lambda tree, plan, ab: (tree / R.LEAF_PREFER[1]).unlink(), "leaf prefer missing"),
    (lambda tree, plan, ab: plan["partition_types"]["kv3_hub_Wi"]["hard_cores"][0].update(lef="x.lef"), "already binds"),
])
def test_fail_closed(tmp_path, break_it, word):
    tree, pdir, plan, ab = _tree(tmp_path)
    break_it(tree, plan, ab)
    p0, a0 = copy.deepcopy(plan), copy.deepcopy(ab)
    with pytest.raises(R.RowError, match=word):
        R.apply(plan, ab, tree, VIEWS, pdir)
    assert plan == p0 and ab == a0          # nothing changed on a refusal


def test_cli_writes_only_on_pass(tmp_path):
    tree, pdir, plan, ab = _tree(tmp_path)
    (pdir / "plan_c.json").write_text(json.dumps(plan))
    (pdir / "asbuilt_vN.json").write_text(json.dumps(ab))
    args = ["--tree", str(tree), "--plan", str(pdir / "plan_c.json"), "--asbuilt", str(pdir / "asbuilt_vN.json"),
            "--views", VIEWS, "--out-plan", str(tmp_path / "p.json"), "--out-asbuilt", str(tmp_path / "a.json")]
    assert R.main(args) == 0 and (tmp_path / "p.json").is_file()
    (tree / R.HOST_DIR / "parent.sv").write_text("module x(); endmodule\n")
    assert R.main(args[:-4] + ["--out-plan", str(tmp_path / "p2.json"), "--out-asbuilt", str(tmp_path / "a2.json")]) == 2
    assert not (tmp_path / "p2.json").exists()
