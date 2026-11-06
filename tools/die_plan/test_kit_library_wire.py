"""KW-FIX-22 11-06: kit-rtl --library-profile caller wiring (bind.py kit-rtl + fresh_kit partition override).

Class: a captured (SRC28) as-built library silently built OLD RTL even though a candidate profile and new defines were
given.  These tests fail on stale RTL: with a profile the kit filelist must carry the candidate source, never the
captured original, and kit_rtl.json must record the profile receipt + the define union.  Without the flag the kit is
unchanged.  python3 -m pytest tools/die_plan/test_kit_library_wire.py
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402
import kit_library_profile as L  # noqa: E402

EX = HERE / "examples" / "bind_tiny"
HAVE_YOSYS = bool(os.environ.get("OT_BIND_YOSYS")) or bool(shutil.which("docker"))
needs_yosys = pytest.mark.skipif(not HAVE_YOSYS, reason="no Yosys (OT_BIND_YOSYS) and no docker")
MARK = "kw22_candidate_marker"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def candidate(tmp_path, original="leaves.sv", defines=("OT_KW22_CANDIDATE",)):
    """candidate copy of a captured source: same modules (lf_a now reaches an added helper) + a profile pinning both"""
    old = EX / original
    text = old.read_text()
    mods = sorted(set(re.findall(r"^module\s+(\w+)", text, re.M)))
    if original == "leaves.sv":
        text = text.replace("else o <= i + ID[7:0];", "else o <= w_c;\n    wire [7:0] w_c;\n"
                            f"    {MARK} u_c (.a(i + ID[7:0]), .y(w_c));")
        text += f"module {MARK} (input wire [7:0] a, output wire [7:0] y);\n    assign y = a;\nendmodule\n"
    new = tmp_path / "cand" / original
    new.parent.mkdir(parents=True, exist_ok=True)
    new.write_text(text)
    newmods = sorted(set(re.findall(r"^module\s+(\w+)", text, re.M)))
    doc = dict(schema=L.SCHEMA, type="ta", defines=list(defines), proof="fixture proof", model={"cycles": 1},
               bound_body_policy=L.POLICY,
               replacements=[dict(original=original, replacement=str(new), original_sha256=sha(old),
                                  replacement_sha256=sha(new), original_modules=mods, replacement_modules=newmods)])
    prof = tmp_path / f"profile_{Path(original).stem}.json"
    prof.write_text(json.dumps(doc))
    return prof, new


@pytest.fixture(scope="module")
def bound(tmp_path_factory):
    plan = EX / "die_plan_lanes.json"
    out = tmp_path_factory.mktemp("kw22") / "o"
    for c in ("elab", "bind"):
        assert bind.main([c, str(plan), "--out", str(out), "--mem", "4"]) == 0
    top = next((out / "rtl").glob("*_bound_top.sv")).read_text()
    inst = re.findall(r"^\s*\w+ #\(.*?\) (\w+) \(", top, re.M)[0]
    return plan, out, inst


def kit(bound, kd, *extra):
    plan, out, inst = bound
    return bind.main(["kit-rtl", str(plan), "--out", str(out), "--type", "ta", "--instance", inst,
                      "--kit", str(kd), *extra])


def files(kd):
    return [str(Path(f).resolve()) for f in (Path(kd) / "kit_rtl.f").read_text().split()]


@needs_yosys
def test_profile_replaces_captured_rtl_in_kit(bound, tmp_path):
    """the class: without the wiring the captured leaves.sv (old RTL) is built; with --library-profile it must not be"""
    stale = str((EX / "leaves.sv").resolve())
    assert kit(bound, tmp_path / "k0") == 0
    assert stale in files(tmp_path / "k0")                       # captured library = the stale source today
    prof, new = candidate(tmp_path)
    assert kit(bound, tmp_path / "k1", "--library-profile", str(prof)) == 0
    fl = files(tmp_path / "k1")
    assert stale not in fl, "stale captured RTL still in the kit filelist"
    assert str(new.resolve()) in fl
    assert MARK in (new.read_text()) and any(MARK in Path(f).read_text() for f in fl)
    man = json.loads((tmp_path / "k1" / "kit_rtl.json").read_text())
    base = json.loads((tmp_path / "k0" / "kit_rtl.json").read_text())
    assert man["defines"] == list(base["defines"]) + ["OT_KW22_CANDIDATE"]
    rec = man["library_profile"]
    assert rec["profile_sha256"] == sha(prof) and rec["captured_bind_unchanged"] is True
    sel = man["library_profile_selected"]
    assert len(sel) == 1 and sel[0]["replacement"] == str(new.resolve()) and MARK in sel[0]["modules"]
    assert "lf_a" in sel[0]["modules"]


@needs_yosys
def test_no_profile_kit_is_byte_identical(bound, tmp_path):
    assert kit(bound, tmp_path / "a") == 0
    assert kit(bound, tmp_path / "b") == 0
    ja = (tmp_path / "a" / "kit_rtl.json").read_text().replace(str(tmp_path / "a"), "K")
    jb = (tmp_path / "b" / "kit_rtl.json").read_text().replace(str(tmp_path / "b"), "K")
    assert ja == jb and "library_profile" not in ja
    assert [Path(f).name for f in files(tmp_path / "a")] == [Path(f).name for f in files(tmp_path / "b")]


@needs_yosys
def test_profile_failures_are_closed(bound, tmp_path):
    # a replacement the kit closure never reaches (par.sv is dissolved, not a ta leaf) refuses: nothing selected
    prof, _ = candidate(tmp_path, original="par.sv")
    assert kit(bound, tmp_path / "k2", "--library-profile", str(prof)) != 0
    assert not (tmp_path / "k2" / "kit_rtl.f").exists()
    # a tampered candidate (hash differs) refuses before the closure
    prof, new = candidate(tmp_path)
    new.write_text(new.read_text() + "// edited after pinning\n")
    assert kit(bound, tmp_path / "k3", "--library-profile", str(prof)) != 0
    assert not (tmp_path / "k3" / "kit_rtl.f").exists()
    # a profile for another type refuses
    prof, new = candidate(tmp_path)
    doc = json.loads(prof.read_text()); doc["type"] = "other"; prof.write_text(json.dumps(doc))
    assert kit(bound, tmp_path / "k4", "--library-profile", str(prof)) != 0


def test_verify_refuses_stale_pick_or_original(tmp_path):
    old, new = str(tmp_path / "old.sv"), str(tmp_path / "new.sv")
    rec = dict(replacements=[dict(original=old, replacement=new, replacement_sha256="0" * 64,
                                  replacement_modules=["leaf", "helper"])])
    rows = bind.kit_library_verify("t", rec, [new], {"leaf": new}, [new])
    assert rows[0]["modules"] == ["leaf"]
    for cl, picks, fl, dd in [([new, old], {"leaf": new}, [new], None),          # original still in the closure
                              ([new], {"leaf": old}, [new], None),               # module picked from the original
                              ([new], {"leaf": new}, [new, old], None),          # original in the final filelist
                              ([new], {"leaf": new}, [new], {"c": dict(original=old)}),   # original as a dedup copy
                              ([], {}, [], None)]:                               # replacement never selected
        with pytest.raises(bind.BindError):
            bind.kit_library_verify("t", rec, cl, picks, fl, dd)


def test_select_updates_index_prefer_wide_and_defines(tmp_path):
    old = tmp_path / "old.sv"; old.write_text("module leaf(input a,output y); assign y=a; endmodule\n")
    new = tmp_path / "new.sv"; new.write_text("module leaf(input a,output y); assign y=~a; endmodule\n")
    doc = dict(schema=L.SCHEMA, type="t", defines=["CAND"], proof="p", model={"cycles": 1}, bound_body_policy=L.POLICY,
               replacements=[dict(original=str(old), replacement=str(new), original_sha256=sha(old),
                                  replacement_sha256=sha(new), original_modules=["leaf"], replacement_modules=["leaf"])])
    prof = tmp_path / "p.json"; prof.write_text(json.dumps(doc))
    idx, prefer, wide, defs, rec = bind.kit_library_select(str(prof), "t", {"leaf": [str(old)]}, [str(old)],
                                                           {"leaf": [str(old)], "x": [str(old)]}, ["ORIG"], tmp_path)
    assert idx["leaf"] == [str(new)] and prefer == [str(new)]
    assert wide == {"leaf": [str(new)]}                          # the stale file is gone from the repo-wide fallback
    assert defs == ["ORIG", "CAND"] and rec["defines"] == defs
    with pytest.raises(bind.BindError):
        bind.kit_library_select(str(prof), "other", {"leaf": [str(old)]}, [], {}, [], tmp_path)


def test_fresh_kit_forwards_library_profile(tmp_path):
    import fresh_kit as F
    from test_kit_istations import BOUND
    import kit_topology as KT
    source = F.HERE.parents[1]
    plan = tmp_path / 'plan.json'
    plan.write_text(json.dumps(dict(partition_types=dict(t=dict(
        buses=[dict(name='i_a', dir='in', width=1, kind='data')], contents=[], internal_stations=[])))))
    bound_dir = tmp_path / 'bound'; bound_dir.mkdir()
    KT.write_bind_receipt(json.loads(plan.read_text()), bound_dir)
    prof = tmp_path / 'lib.json'; prof.write_text('{}')
    seen = []

    def factory(record_selected):
        def run(cmd, **kwargs):
            name = Path(cmd[2]).name
            if name == 'kit_topology.py':
                return subprocess.run(cmd, **kwargs)
            if name == 'bind.py':
                seen.append(cmd)
                rtl = Path(cmd[cmd.index('--kit')+1]); rtl.mkdir()
                (rtl / 't_part_bound.sv').write_text(BOUND)
                man = dict(bound_module='t_part_bound', files=[str(rtl / 't_part_bound.sv')])
                if record_selected:
                    man['library_profile_selected'] = [dict(replacement='x')]
                (rtl / 'kit_rtl.json').write_text(json.dumps(man))
                (rtl / 'kit_rtl.f').write_text(str(rtl / 't_part_bound.sv')+'\n')
                return subprocess.CompletedProcess(cmd, 0, 'fixture\n')
            raise RuntimeError('stop after kit_rtl (fixture)')
        return run
    ov = dict(bind_out=str(bound_dir), reset_mode='native', library_profile=str(prof))
    with pytest.raises(Exception):
        F.prepare(source, 'partition', plan, tmp_path / 'f1', type_name='t', overrides=ov, run=factory(True))
    cmd = seen[-1]
    assert cmd[cmd.index('--library-profile') + 1] == str(prof.resolve())
    rec = json.loads((tmp_path / 'f1' / 'fresh_kit.json').read_text())
    assert rec['error'] == 'stop after kit_rtl (fixture)' and 'kit_rtl' in [x['name'] for x in rec['stages']]
    # kit-rtl that ignored the profile (no selection record) is refused right after the kit_rtl stage
    with pytest.raises(ValueError, match='library profile'):
        F.prepare(source, 'partition', plan, tmp_path / 'f2', type_name='t', overrides=ov, run=factory(False))
    # no profile: the bind.py command carries no flag
    F_ov = dict(bind_out=str(bound_dir), reset_mode='native')
    with pytest.raises(Exception):
        F.prepare(source, 'partition', plan, tmp_path / 'f3', type_name='t', overrides=F_ov, run=factory(False))
    assert '--library-profile' not in seen[-1]


def test_profile_original_from_repo_wide_index(tmp_path):
    """S81-RCK-3 11-06: the S81 serdes decoder top is a captured child outside the manifest index (taken from the
    unique repo-wide file); its profile row must be accepted and replace it everywhere, not fail 'absent from index'."""
    old = tmp_path / "old.sv"; old.write_text("module leaf(input a,output y); assign y=a; endmodule\n")
    new = tmp_path / "new.sv"; new.write_text("module leaf(input a,output y); assign y=~a; endmodule\n")
    doc = dict(schema=L.SCHEMA, type="t", defines=["CAND"], proof="p", model={"cycles": 1}, bound_body_policy=L.POLICY,
               replacements=[dict(original=str(old), replacement=str(new), original_sha256=sha(old),
                                  replacement_sha256=sha(new), original_modules=["leaf"], replacement_modules=["leaf"])])
    prof = tmp_path / "p.json"; prof.write_text(json.dumps(doc))
    assert bind.library_profile_unindexed(str(prof), {}, {"leaf": [str(old)]}, tmp_path) == {"leaf": [str(old)]}
    # ambiguous or different repo-wide file: left unindexed, so apply still refuses it
    assert bind.library_profile_unindexed(str(prof), {}, {"leaf": [str(old), str(new)]}, tmp_path) == {}
    assert bind.library_profile_unindexed(str(prof), {}, {"leaf": [str(new)]}, tmp_path) == {}
    idx, _, wide, _, _ = bind.kit_library_select(str(prof), "t", {}, [], {"leaf": [str(old)]}, [], tmp_path)
    assert idx["leaf"] == [str(new)] and wide == {"leaf": [str(new)]}
    with pytest.raises(bind.BindError, match="absent"):
        bind.kit_library_select(str(prof), "t", {}, [], {"leaf": [str(new)]}, [], tmp_path)


def test_fresh_kit_preserved_bound_reset(tmp_path):
    """S81-RCK-3 11-06: kit_rsync on a bound native reset writes no kit_rsync record (it preserves the verified reset);
    fresh_kit must record that instead of KeyError, and still refuse a reset_expected it cannot check."""
    import fresh_kit as F
    from test_kit_istations import BOUND
    import kit_topology as KT
    source = F.HERE.parents[1]
    plan = tmp_path / 'plan.json'
    plan.write_text(json.dumps(dict(partition_types=dict(t=dict(
        buses=[dict(name='i_a', dir='in', width=1, kind='data')], contents=[], internal_stations=[])))))
    bound_dir = tmp_path / 'bound'; bound_dir.mkdir()
    KT.write_bind_receipt(json.loads(plan.read_text()), bound_dir)

    def run(cmd, **kwargs):
        name = Path(cmd[2]).name
        if name == 'bind.py':
            rtl = Path(cmd[cmd.index('--kit')+1]); rtl.mkdir()
            (rtl / 't_part_bound.sv').write_text(BOUND)
            (rtl / 'bound_reset.json').write_text('{}')
            (rtl / 'kit_rtl.json').write_text(json.dumps(dict(bound_module='t_part_bound', files=[str(rtl / 't_part_bound.sv')])))
            (rtl / 'kit_rtl.f').write_text(str(rtl / 't_part_bound.sv')+'\n')
            return subprocess.CompletedProcess(cmd, 0, 'fixture\n')
        if name == 'kit_rsync.py':
            return subprocess.CompletedProcess(cmd, 0, '{"preserved_bound_native_reset": true}\n')
        raise RuntimeError('stop after reset (fixture)')
    ov = dict(bind_out=str(bound_dir), reset_mode='canonical')
    with pytest.raises(RuntimeError, match='stop after reset'):
        F.prepare(source, 'partition', plan, tmp_path / 'f1', type_name='t', overrides=ov, run=run)
    rec = json.loads((tmp_path / 'f1' / 'fresh_kit.json').read_text())
    assert rec['reset_context']['actual'] == 'preserved_bound_native_reset'
    with pytest.raises(ValueError, match='bound native reset preserved'):
        F.prepare(source, 'partition', plan, tmp_path / 'f2', type_name='t', run=run,
                  overrides=dict(ov, reset_expected=dict(depth=2)))
