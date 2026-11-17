"""WAVE-FLOW-R 11-17 (FABLE-FLOW-0300 items 4, 5): the fail key scopes the tools digest to the failed stage / the files the failure names,
LAUNCH-REFUSED is recorded once per key, and a pin with no rt manifest falls back to the tree's own base instead of 'not readable'."""
import json

import kit_wave as KW
import tool_skew as TS

WHY = ("INFRA: infra (python exception / plan-schema refusal in the kit tool: tool or source skew) @gen: "
       "Traceback File \"/x/tools/die_plan/gen_phys.py\", line 9 ValueError: no RTL header for blackbox")


def cfg():
    return {"dies": {"qc": {"src_sha": "s", "_src_overlay": "o", "_plan_sha": "p", "event": "e", "enabled": True}}}


def rec():
    return {"die": "qc", "item": "sle_sc_v3", "block_sha": "b", "stage": "gen"}


def test_groups_and_named_files():
    assert KW.tools_group("gen") == "gen" and KW.tools_group("kit_rtl") == "bind" and KW.tools_group("place") == ""
    assert KW.failed_tool_files("no tool named here") == []


def test_tools_change_outside_the_failed_files_does_not_release(monkeypatch):
    calls = []

    def digest(root=None, group="", files=None):
        calls.append((group, tuple(files or ())))
        return "files-same" if files else "closure-" + str(len(calls))
    monkeypatch.setattr(KW, "stage_tools_digest", digest)
    monkeypatch.setattr(KW, "failed_tool_files", lambda why, root=None: ["tools/die_plan/gen_phys.py"])
    st = {}
    KW.note_fail_key(cfg(), st, rec(), "INFRA", WHY)
    assert st["fail_keys"]["qc|sle_sc_v3"]["tool_files"] == ["tools/die_plan/gen_phys.py"]
    bl, why, chg = KW.fail_key_gate(cfg(), st, "qc", "sle_sc_v3", "b")
    assert bl and chg == []
    assert calls[-1] == ("gen", ("tools/die_plan/gen_phys.py",))


def test_named_file_change_releases(monkeypatch):
    seq = iter(["v1", "v2"])
    monkeypatch.setattr(KW, "stage_tools_digest", lambda root=None, group="", files=None: next(seq))
    monkeypatch.setattr(KW, "failed_tool_files", lambda why, root=None: ["tools/die_plan/gen_phys.py"])
    st = {}
    KW.note_fail_key(cfg(), st, rec(), "INFRA", WHY)
    bl, why, chg = KW.fail_key_gate(cfg(), st, "qc", "sle_sc_v3", "b")
    assert not bl and chg == ["tools"]


def test_refusal_logged_once_per_key():
    src = open(KW.__file__).read()
    assert 'st.setdefault("refused_once", {})' in src and "recorded once" in src


def test_pin_without_manifest_falls_back_to_tree_base(tmp_path):
    rt = tmp_path / "rt"
    rt.mkdir()
    rel = "tools/die_plan/gen.py"
    (rt / "base11111111.manifest.json").write_text(json.dumps({"files": {rel: "h1"}}))
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / ".src-manifest.json").write_text(json.dumps({"main_sha": "base11111111" + "0" * 28, "files": {rel: "h1"}}))
    res = TS.check_die("s81", str(tree), tmp_path, {}, tools_sha="deadbeefdead" + "0" * 28, rt_root=str(rt))
    assert res["measured"] and res["ok"]
    res = TS.check_die("s81", str(tmp_path / "nope"), tmp_path, {}, tools_sha="deadbeefdead" + "0" * 28, rt_root=str(rt))
    assert not res["measured"] and "missing" in res["why"]


def test_second_identical_failure_closes_the_key_against_tool_changes(monkeypatch):
    seq = {"v": "t1"}
    monkeypatch.setattr(KW, "stage_tools_digest", lambda root=None, group="", files=None: seq["v"])
    monkeypatch.setattr(KW, "failed_tool_files", lambda why, root=None: [])
    st = {}
    KW.note_fail_key(cfg(), st, rec(), "INFRA", WHY)
    seq["v"] = "t2"                                    # a tools change relaunches the first time (sig_n 1)
    assert KW.fail_key_gate(cfg(), st, "qc", "sle_sc_v3", "b")[2] == ["tools"]
    KW.note_fail_key(cfg(), st, rec(), "INFRA", WHY)   # failed again, same stage and error
    assert st["fail_keys"]["qc|sle_sc_v3"]["sig_n"] == 2
    seq["v"] = "t3"
    bl, why, chg = KW.fail_key_gate(cfg(), st, "qc", "sle_sc_v3", "b")
    assert bl and chg == []                            # tool change no longer releases
    c = cfg(); c["dies"]["qc"]["src_sha"] = "s2"       # a named input does
    assert KW.fail_key_gate(c, st, "qc", "sle_sc_v3", "b")[2] == ["src"]


def test_hub_statvfs_is_replaceable_for_fixed_host_state(monkeypatch):
    import types
    monkeypatch.setattr(KW, "_HUB_STATVFS", lambda p: types.SimpleNamespace(f_bavail=500, f_frsize=2**30))
    assert KW.hub_disk_low({}) == ""
