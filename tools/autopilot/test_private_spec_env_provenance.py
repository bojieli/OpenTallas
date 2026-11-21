"""FLOW-PROC-A 11-21 (FABLE-FLOW-0800 class a): kit_wave.py private-spec builds a private kit spec from the item's wave spec (env, gen args,
flow_tag computed now); only plan / tree / overlay differ, A/B env changes must name keys + reason; run_kit.sh's ENV-PROVENANCE check
(env_provenance.py) refuses place on a hand-built kit or an undeclared env difference."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_provenance as EP      # noqa: E402
import kit_wave as KW            # noqa: E402
from test_kit_wave import cfg    # noqa: E402

D, I = "qwen_kvsys", "kv3_pc"


def wave_cfg(src="/srv/x/src_kv"):
    c = cfg()
    d = c["dies"][D]
    d.update(src=src, flow_tag="flow-kv-1", die_gen_env={"OT_PGCAP": "1", "OT_PLACE_MAX_FANOUT": "24",
                                                          "OT_SIGNED_VIEW_SHA": src + "/physical/die_plan/qwen_kvsys/plan_of_record/sv.json"})
    d.setdefault("item_env", {})[I] = {"OT_CBC_REACH_UM": "300"}
    return c


def test_private_spec_keeps_wave_env_and_rewrites_tree_paths(tmp_path):
    c = wave_cfg()
    wave = KW.spec_for(c, D, I, "intel2")
    sp = KW.private_spec(c, D, I, "intel2", plan=str(tmp_path / "plan_c.json"), tree=str(tmp_path / "tree"), lane="FAM-X")
    assert sp["private"]["wave_env"] == wave["gen_env"]
    assert sp["gen_env"]["OT_PGCAP"] == "1" and sp["gen_env"]["OT_FLOW_TAG"] == "flow-kv-1" and sp["gen_env"]["OT_CBC_REACH_UM"] == "300"
    assert sp["gen_env"]["OT_SIGNED_VIEW_SHA"].startswith(str(tmp_path / "tree") + "/")
    assert sp["private"]["plan_derived"] == ["OT_SIGNED_VIEW_SHA"]
    assert sp["plan"] == str(tmp_path / "plan_c.json") and sp["src"] == str(tmp_path / "tree")
    assert sp["gen_args"] == wave["gen_args"] and "/private/FAM-X/" in sp["work"]
    assert EP.env_diff(sp["private"]["wave_env"], sp["gen_env"]) == ["OT_SIGNED_VIEW_SHA"]


def test_ab_needs_reason_and_is_declared():
    c = wave_cfg()
    with pytest.raises(ValueError):
        KW.private_spec(c, D, I, "intel2", ab=["OT_PGCAP=0"])
    with pytest.raises(ValueError):
        KW.private_spec(c, D, I, "intel2", ab=["PGCAP=0"], why="x")
    sp = KW.private_spec(c, D, I, "intel2", ab=["OT_PGCAP=", "OT_GPL_SPARSE_UTIL=0.4"], why="A/B: pg cap off")
    assert "OT_PGCAP" not in sp["gen_env"] and sp["gen_env"]["OT_GPL_SPARSE_UTIL"] == "0.4"
    assert sp["env_ab"] == {"keys": ["OT_GPL_SPARSE_UTIL", "OT_PGCAP"], "why": "A/B: pg cap off"}


def decl(sp, spec_path):
    return KW.env_provenance_decl(sp, spec_path)


def test_judge_wave_private_ab_and_hand_built(tmp_path):
    c = wave_cfg()
    sp = KW.private_spec(c, D, I, "intel2", tree=str(tmp_path / "tree"))
    (tmp_path / "spec.json").write_text(json.dumps(sp))
    rec = decl(sp, tmp_path / "spec.json")
    assert rec["source"] == "private-spec"
    assert EP.judge(rec, None)[0] is True
    # a hand edit of the env (lepe proof7: OT_CBC_REACH_UM, OT_PLACE_MAX_TRANSITION missing) is refused before place, warned after
    bad = dict(rec, env={k: v for k, v in rec["env"].items() if k != "OT_CBC_REACH_UM"})
    ok, lines = EP.judge(bad, None)
    assert ok is False and "OT_CBC_REACH_UM" in lines[0] and "wave=300" in lines[0]
    assert EP.judge(bad, None, placed=True)[0] is True
    # the same difference declared as A/B with a reason passes
    assert EP.judge(dict(bad, ab={"keys": ["OT_CBC_REACH_UM"], "why": "reach A/B"}), None)[0] is True
    assert EP.judge(dict(bad, ab={"keys": ["OT_CBC_REACH_UM"], "why": ""}), None)[0] is False
    # no record: refused outside a kit-wave root, a legacy wave kit passes
    assert EP.judge(None, None, kit_path="/srv/s/claude/lanes/hd_lep0N/shelf_bf")[0] is False
    assert EP.judge(None, None, kit_path="/srv/s/runs/s81/kit-wave/s81/E/items/t1/gen/t1")[0] is True
    # a flow canary reference kit (FLOW-CANARY-1121) is a flow test, not a design proof
    assert EP.judge(None, None, kit_path="/srv/s/claude/flow-canary/runs/s81_3ed_1121/gen/slice_station__t12")[0] is True
    # a copied spec.json run with run-item outside the wave state dir is 'unregistered'
    wave = KW.spec_for(c, D, I, "intel2")
    rec_u = decl(wave, tmp_path / "spec.json")
    assert rec_u["source"] == "unregistered" and EP.judge(rec_u, None)[0] is False
    # config.mk hand edit after run-item: refused on a private kit, a note on a wave kit
    rec_c = dict(rec, config_ot={"OT_PGCAP": "1"})
    assert EP.judge(rec_c, "export OT_PGCAP = 0\n")[0] is False
    assert EP.judge(dict(rec_c, source="wave", wave_env=rec["env"]), "export OT_PGCAP = 0\n")[0] is True


def test_wave_attempt_is_wave_source(tmp_path, monkeypatch):
    monkeypatch.setattr(KW, "AP_DIR", tmp_path)
    jd = tmp_path / "kit_wave" / "k" / "a1"
    jd.mkdir(parents=True)
    sp = KW.spec_for(wave_cfg(), D, I, "intel2")
    (jd / "spec.json").write_text(json.dumps(sp))
    rec = KW.env_provenance_decl(sp, jd / "spec.json")
    assert rec["source"] == "wave" and rec["env"] == rec["wave_env"]
    ok, lines = EP.judge(rec, None)
    assert ok and lines[0].startswith("ENV-PROVENANCE PASS: source wave") and "env=wave " in lines[0] + " "


def test_stale_private_spec_refused_at_run_item():
    c = wave_cfg()
    sp = KW.private_spec(c, D, I, "intel2")
    assert KW.private_spec_stale(sp, cfg=c) == ""
    c["dies"][D]["die_gen_env"]["OT_PLACE_MAX_FANOUT"] = "16"          # the die config moved on after the spec was made
    why = KW.private_spec_stale(sp, cfg=c)
    assert "stale private spec" in why and "OT_PLACE_MAX_FANOUT" in why


def test_check_cli_and_config_ot(tmp_path):
    k = tmp_path / "lanes" / "kit"
    k.mkdir(parents=True)
    (k / "config.mk").write_text("export OT_PGCAP = 1\noverride export OT_X := a b\nexport DESIGN = d\n")
    assert EP.config_ot((k / "config.mk").read_text()) == {"OT_PGCAP": "1", "OT_X": "a b"}
    env = dict(os.environ)
    r = subprocess.run([sys.executable, "-I", EP.__file__, "check", str(k)], capture_output=True, text=True, env=env)
    assert r.returncode == EP.REFUSE_RC and "ENV-PROVENANCE FAIL" in r.stdout
    rec = {"source": "private-spec", "die": D, "item": I, "env": {"OT_PGCAP": "1"}, "wave_env": {"OT_PGCAP": "1"}}
    import base64
    b = base64.b64encode(json.dumps(rec).encode()).decode()
    assert subprocess.run([sys.executable, "-I", EP.__file__, "write", str(k), "--b64", b], capture_output=True).returncode == 0
    assert json.loads((k / EP.RECORD).read_text())["config_ot"]["OT_PGCAP"] == "1"
    r = subprocess.run([sys.executable, "-I", EP.__file__, "check", str(k)], capture_output=True, text=True)
    assert r.returncode == 0 and "ENV-PROVENANCE PASS" in r.stdout


def _gen_phys():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "die_plan"))
    import gen_phys
    return gen_phys


def test_runner_block_and_refresh_entry():
    gp = _gen_phys()
    assert 'env_provenance.py" check "$K"' in gp.RUN_KIT and "exit 14" in gp.RUN_KIT
    import kit_flow_refresh as KFR
    assert ("kit+", "env_provenance.py", "tools/autopilot/env_provenance.py") in KFR.ALWAYS


def test_host_bind_out_src_manifest_flags(tmp_path):
    """FAM-QC-COLL / FABLE-FIX-S81-LEAF-R5 edited a config copy for host, bind_out and src_manifest; these are flags now"""
    c = wave_cfg()
    sp = KW.private_spec(c, D, I, "intel2", host="epyc10", bind_out=str(tmp_path / "bind"), src_manifest="off")
    assert sp["gen_host"] == "epyc10" and sp["hosts"][0] == "epyc10" and sp["place_prefer"][0] == "epyc10" and sp["roam_hosts"] == ["epyc10"]
    assert sp["kit_rtl"]["bind_out"] == str(tmp_path / "bind")
    assert sp["src_manifest"] == "off" and sp["src_manifest_hash"] == ""
    assert sp["gen_env"] == sp["private"]["wave_env"]                    # none of them is an env difference
    assert KW.private_spec(c, D, I, "intel2", src_manifest="on")["src_manifest"] != "off"
    with pytest.raises(ValueError):
        KW.private_spec(c, D, I, "intel2", src_manifest="maybe")


def test_missing_hub_ot_run_override_falls_back(monkeypatch):
    c = wave_cfg()
    c["ot_run"] = "/nonexistent/ot-run-wave"
    sp = KW.private_spec(c, D, I, "intel2")
    assert sp["ot_run"] == KW.OT_RUN and "ot_run_note" in sp


def test_config_from_hub_when_not_local():
    class R:
        returncode, stdout = 0, '{"dies": {}}'
    calls = []
    txt = KW.private_config_text(None, "intel2", read=lambda AP: "", ssh=lambda argv, **k: (calls.append(argv), R())[1])
    assert txt == '{"dies": {}}' and calls[0][-2] == "intel2" and "show HEAD:autopilot/kit_wave.json" in calls[0][-1]
    assert KW.private_config_text(None, "intel2", read=lambda AP: '{"dies": {"x": {}}}', ssh=None) == '{"dies": {"x": {}}}'


def _fake_rt(root, sha):
    d = root / sha[:12]
    (d / "tools" / "autopilot").mkdir(parents=True)
    (d / "tools" / "autopilot" / "rt_launch_tree.sh").write_text("#\n")
    (root / f"{sha[:12]}.manifest.json").write_text(json.dumps({"sha": sha}))
    return d


def test_private_rt_declared_and_recorded(tmp_path, monkeypatch):
    sha = "36f47f8037" + "ab" * 15
    d = _fake_rt(tmp_path, sha)
    assert KW.private_rt_fields(sha[:12], rt_root=tmp_path) == {"tools_rt": str(d), "tools_sha": sha}
    with pytest.raises(ValueError):
        KW.private_rt_fields("zz", rt_root=tmp_path)
    with pytest.raises(ValueError):
        KW.private_rt_fields("0123456789ab", rt_root=tmp_path)
    with pytest.raises(ValueError):                      # 12-hex dir of another commit
        KW.private_rt_fields(sha[:12] + "ff", rt_root=tmp_path)
    real = KW.private_rt_fields
    monkeypatch.setattr(KW, "private_rt_fields", lambda s, **k: real(s, rt_root=tmp_path))
    c = wave_cfg()
    wave = KW.spec_for(c, D, I, "intel2")
    sp = KW.private_spec(c, D, I, "intel2", rt=sha[:12], lane="FLOW-X")
    assert sp["tools_rt"] == str(d) and sp["tools_sha"] == sha and "gen_tools_manifest_sha" not in sp
    assert sp["private"]["rt"]["sha"] == sha and sp["private"]["rt"]["rt"] == str(d)
    assert sp["gen_env"] == wave["gen_env"]              # --rt is no env change: ENV-PROVENANCE passes unchanged
    rec = KW.env_provenance_decl(sp, tmp_path / "spec.json")
    assert rec["tools_sha"] == sha and rec["rt_declared"]["sha"] == sha and rec["source"] == "private-spec"
    assert EP.env_diff(rec["wave_env"], rec["env"]) == []
    assert "rt" not in KW.private_spec(c, D, I, "intel2")["private"]
