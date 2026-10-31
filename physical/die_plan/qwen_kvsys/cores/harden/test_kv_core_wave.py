"""AUTOBUILD-PIPE-2 10-31: KV core_kit adapter (kv_core_wave.py) + kit_wave core_kit_cmds with the KV config block."""
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
spec = importlib.util.spec_from_file_location("kcw", HERE / "kv_core_wave.py")
kcw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kcw)
sys.path.insert(0, str(REPO / "tools/autopilot"))
import kit_wave  # noqa: E402

KV_CORE_KIT = {   # the dies.qwen_kvsys.core_kit block (kit_wave.json); see the READY note
    "views_cmd": "python3 physical/die_plan/qwen_kvsys/cores/harden/kv_core_wave.py views --plan {plan} --out {views}",
    "gen_cmd": "python3 physical/die_plan/qwen_kvsys/cores/harden/kv_core_wave.py gen --views {views} --view {view} "
               "--out {out} --plan {plan} {args}",
    "runner": "{kit}/run_kit_kv.sh",
    "args": ["--fp-root", "/x/fp"],
}


def mkplan(tmp):
    (tmp / "pins").mkdir()
    (tmp / "pins/a.json").write_text('{"pins": [1]}')
    (tmp / "pins/b.json").write_text('{"pins": [2]}')
    (tmp / "pins/c.json").write_text('{"pins": [3]}')
    plan = {"partition_types": {
        "kv3_hub_Wi": {"hard_cores": [
            {"inst": "host__qkd_hr_a", "module": "qkd_hr_a", "pins_file": "pins/a.json"},
            {"inst": "host__qkd_hr_b_0", "module": "qkd_hr_b", "pins_file": "pins/b.json"},
            {"inst": "host__qkd_hr_b_1", "module": "qkd_hr_b", "pins_file": "pins/b.json"},
            {"inst": "host__signed", "module": "qkd_signed", "pins_file": "pins/c.json", "lef": "x.lef", "lib": "x.lib"}]},
        "kv3_hub_C": {"hard_cores": [{"inst": "kvs_ctl", "module": "qkd_kvs_ctl", "pins_file": "pins/c.json"}]}}}
    p = tmp / "plan_c.json"
    p.write_text(json.dumps(plan))
    root = tmp / "rtl"
    for m in ("qkd_hr_a", "qkd_hr_b"):
        (root / m).mkdir(parents=True)
        (root / m / f"{m}.sv").write_text(f"module {m}(); endmodule\n")
        (root / m / f"{m}_core.json").write_text(json.dumps({
            "module": m, "type": "kv3_hub_Wi", "inst": f"host__{m}" if m == "qkd_hr_a" else "host__qkd_hr_b_1",
            "files": [f"/gone/wt/kv-host-regen-1/rtl/{m}/{m}.sv", "/gone/wt/kv-host-regen-1/physical/m/x_bb.v"]}))
    return p, root


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12]


def test_views_one_per_module_pin_table(tmp_path):
    p, root = mkplan(tmp_path)
    v = kcw.plan_views(str(p), [str(root)])
    got = {x["module"]: x for x in v["view_list"]}
    assert sorted(got) == ["qkd_hr_a", "qkd_hr_b"]
    assert got["qkd_hr_a"]["view"] == f"qkd_hr_a@{sha(tmp_path / 'pins/a.json')}"
    assert got["qkd_hr_b"]["insts"] == ["host__qkd_hr_b_0", "host__qkd_hr_b_1"] and got["qkd_hr_b"]["hr"]
    assert [x["module"] for x in v["no_recipe"]] == ["qkd_kvs_ctl"]        # no core json -> no view (PLAN)


def test_view_key_matches_kit_wave_probe_core_views(tmp_path):
    p, root = mkplan(tmp_path)
    v = kcw.plan_views(str(p), [str(root)])
    # kit_wave PROBE_PLAN: sha256(<plan dir>/pins_file)[:12] per module; a module with >1 table -> '<m>__v<sha>'
    names = kit_wave.core_view_names({"qkd_hr_a": "b1"}, {"qkd_hr_a": [sha(tmp_path / "pins/a.json")]})
    assert names == {"qkd_hr_a": "b1"}
    assert v["view_list"][0]["view"].split("@")[1] == sha(tmp_path / "pins/a.json")


@pytest.mark.parametrize("item,mod", [("qkd_hr_b", "qkd_hr_b"), ("qkd_hr_a__v{a}", "qkd_hr_a")])
def test_core_kit_cmds_kv_block_and_picker(tmp_path, item, mod):
    p, root = mkplan(tmp_path)
    views = tmp_path / "core_views.json"
    views.write_text(json.dumps(kcw.plan_views(str(p), [str(root)])))
    item = item.format(a=sha(tmp_path / "pins/a.json"))
    ck = dict(KV_CORE_KIT, views=str(views))
    vp, vcmd, gcmd, find, runner = kit_wave.core_kit_cmds(ck, "/src", str(p), str(tmp_path), str(tmp_path / "W"), item)
    assert vp == str(views) and vcmd == "" and runner == "{kit}/run_kit_kv.sh"
    assert "kv_core_wave.py gen --views" in gcmd and "--fp-root /x/fp" in gcmd
    assert gcmd.rstrip().endswith("--fp-root /x/fp") and f"--plan {p}" in gcmd
    pick = gcmd.split("VIEW=$(", 1)[1].split(") && echo", 1)[0]
    out = subprocess.run(["bash", "-c", pick], capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip().startswith(mod + "@"), out.stderr
    _, vcmd2, *_ = kit_wave.core_kit_cmds(KV_CORE_KIT, "/src", str(p), str(tmp_path), str(tmp_path / "W"), item)
    assert vcmd2.startswith("python3 physical/die_plan/qwen_kvsys/cores/harden/kv_core_wave.py views --plan ")


def test_picker_kvs_ctl_has_no_view(tmp_path):
    p, root = mkplan(tmp_path)
    views = tmp_path / "core_views.json"
    views.write_text(json.dumps(kcw.plan_views(str(p), [str(root)])))
    _, _, gcmd, _, _ = kit_wave.core_kit_cmds(dict(KV_CORE_KIT, views=str(views)), "/src", str(p), str(tmp_path),
                                             str(tmp_path / "W"), "qkd_kvs_ctl")
    pick = gcmd.split("VIEW=$(", 1)[1].split(") && echo", 1)[0]
    out = subprocess.run(["bash", "-c", pick], capture_output=True, text=True)
    assert out.returncode != 0 and "CORE_VIEW FAIL qkd_kvs_ctl" in out.stderr
    assert kit_wave.classify("gen", out.stderr)[0] == "PLAN"


def gen_setup(tmp_path, proof=True):
    p, root = mkplan(tmp_path)
    repo = tmp_path / "repo"
    (repo / "rtl/qkd_hr_a").mkdir(parents=True)
    (repo / "physical/m").mkdir(parents=True)
    (repo / "physical/m/x_bb.v").write_text("module x(); endmodule\n")
    (repo / "physical/m/x.lef").write_text("")
    (repo / "physical/m/x_ff.lib").write_text("")
    (repo / "physical/m/x_tt.lib").write_text("")
    views = tmp_path / "v.json"
    views.write_text(json.dumps(kcw.plan_views(str(p), [str(root)])))
    fp = tmp_path / "fp" / "qkd_hr_a"
    fp.mkdir(parents=True)
    (fp / "eq_rc.txt").write_text("post rc=0\nmut rc=1\nemitted_v rc=0\n" if proof else "post rc=0\nmut rc=0\n")
    (fp / "qkd_hr_a.v").write_text("module qkd_hr_a(); endmodule\n")
    (fp / "hr_face_ports.json").write_text("{}")
    view = f"qkd_hr_a@{sha(tmp_path / 'pins/a.json')}"
    return views, view, repo


def test_gen_repoints_sources_and_builds_recipe_cmd(tmp_path, monkeypatch):
    views, view, repo = gen_setup(tmp_path)
    seen = {}
    monkeypatch.setattr(kcw.subprocess, "run", lambda cmd: seen.setdefault("cmd", cmd) and type("R", (), {"returncode": 0}))
    rc = kcw.main(["gen", "--views", str(views), "--view", view, "--out", str(tmp_path / "gen"), "--kit-rtl", "/k",
                   "--fp-root", str(tmp_path / "nofp"), "--fp-root", str(tmp_path / "fp"), "--repo", str(repo),
                   "--two-mode-grt"])
    assert rc == 0
    c = seen["cmd"]
    assert c[c.index("--hr-face-ports") + 1] == str(tmp_path / "fp/qkd_hr_a")
    assert c[c.index("--plan-inst") + 1] == "host__qkd_hr_a" and c[-1] == "--two-mode-grt"
    assert c[c.index("--util") + 1] == "0.6" and c[c.index("--sigmax") + 1] == "M5"
    cj = json.load(open(c[c.index("--core-json") + 1]))
    assert cj["files"] == [str(tmp_path / "rtl/qkd_hr_a/qkd_hr_a.sv"), str(repo / "physical/m/x_bb.v")]
    assert c[c.index("--kit-rtl") + 1] == "/k"


def test_gen_kit_rtl_auto_from_black_boxes(tmp_path, monkeypatch):
    views, view, repo = gen_setup(tmp_path)
    seen = {}
    monkeypatch.setattr(kcw.subprocess, "run", lambda cmd: seen.setdefault("cmd", cmd) and type("R", (), {"returncode": 0}))
    assert kcw.main(["gen", "--views", str(views), "--view", view, "--out", str(tmp_path / "gen"),
                     "--fp-root", str(tmp_path / "fp"), "--repo", str(repo)]) == 0
    c = seen["cmd"]
    kr = Path(c[c.index("--kit-rtl") + 1])
    hm = json.load(open(kr / "kv3_hub_Wi/kit_rtl.json"))["hard_macros"]
    assert list(hm) == ["x"] and hm["x"]["lef"] == str(repo / "physical/m/x.lef")
    assert hm["x"]["libs"] == [str(repo / "physical/m/x_ff.lib"), str(repo / "physical/m/x_tt.lib")]
    (repo / "physical/m/x.lef").unlink()
    with pytest.raises(SystemExit) as e:
        kcw.main(["gen", "--views", str(views), "--view", view, "--out", str(tmp_path / "gen2"),
                  "--fp-root", str(tmp_path / "fp"), "--repo", str(repo)])
    assert "NO_RECIPE qkd_hr_a: memory macro view" in str(e.value)


def test_gen_fails_closed_without_pass_proof(tmp_path):
    views, view, repo = gen_setup(tmp_path, proof=False)
    with pytest.raises(SystemExit) as e:
        kcw.main(["gen", "--views", str(views), "--view", view, "--out", str(tmp_path / "gen"), "--kit-rtl", "/k",
                  "--fp-root", str(tmp_path / "fp"), "--repo", str(repo)])
    assert str(e.value).startswith("NO_RECIPE qkd_hr_a: no PASS hr face proof")
    assert kit_wave.classify("gen", str(e.value))[0] == "PLAN"


def test_gen_fails_closed_on_missing_source(tmp_path):
    views, view, repo = gen_setup(tmp_path)
    (repo / "physical/m/x_bb.v").unlink()
    with pytest.raises(SystemExit) as e:
        kcw.main(["gen", "--views", str(views), "--view", view, "--out", str(tmp_path / "gen"), "--kit-rtl", "/k",
                  "--fp-root", str(tmp_path / "fp"), "--repo", str(repo)])
    assert "NO_RECIPE qkd_hr_a: 1 core json sources not found" in str(e.value)
