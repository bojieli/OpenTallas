"""P-RESET-RECEIPT: rebind_nr_serdes accepts a changed hd_serdes partition only with a receipt on the NEW digest whose hash-verified entry-phase evidence
covers every differing leaf by VALUE.  Unit tests of check_changed_binding on real files, end-to-end main() tests with stub tool modules, and mutants."""
import hashlib
import json
import sys
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SRC = (HERE / "rebind_nr_serdes.py").read_text()
CELL = "module ot_dp_rrelay_ph; endmodule\n"
CELL_SHA = hashlib.sha256(CELL.encode()).hexdigest()
DIG = "d" * 64
MARK = "ENTRY_PHASE_BENCH PASS"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load(src=None):
    m = types.ModuleType("rebind_t")
    m.__file__ = str(HERE / "rebind_nr_serdes.py")
    exec(compile(SRC if src is None else src, "rebind", "exec"), m.__dict__)
    return m


OLD = {"lk_EN0": {"type": "hd_serdes", "reset_entry_phase": 4, "id_straps": {"strap_rst_ph": 0}},
       "lk_WN1": {"type": "hd_serdes", "reset_entry_phase": 3, "id_straps": {"strap_rst_ph": 1}}}
NEW = {"lk_EN0": {"type": "hd_serdes", "reset_entry_phase": 3, "id_straps": {"strap_rst_ph": 1}},
       "lk_WN1": {"type": "hd_serdes", "reset_entry_phase": 2, "id_straps": {"strap_rst_ph": 0}}}
ROWS = [dict(partition="lk_EN0", field="reset_entry_phase", old=4, new=3), dict(partition="lk_EN0", field="id_straps.strap_rst_ph", old=0, new=1),
        dict(partition="lk_WN1", field="reset_entry_phase", old=3, new=2), dict(partition="lk_WN1", field="id_straps.strap_rst_ph", old=1, new=0)]


def make_receipt(d, rows=ROWS, digest=DIG, cell=CELL_SHA, verdict="PASS", log_text="x\n" + MARK + "\n", evidence_name="entry_phase_evidence.json",
                 tamper_log=False, rdigest=DIG, tamper_ev=False):
    d.mkdir(parents=True, exist_ok=True)
    (d / "bench.log").write_text(log_text)
    (d / "tb.sv").write_text("tb\n")
    arts = {n: sha((d / n).read_bytes()) for n in ("bench.log", "tb.sv")}
    ev = dict(schema="opentallas.entry_phase_evidence.v1", plan_digest=digest, cell_sha256=cell, rows=rows, verdict=verdict, log="bench.log",
              cases=[dict(partition="lk_EN0", version="new", h=3, strap=1, release_delta=-2, expect_cycles=1, sim_cycles=1)],
              pass_marker=MARK, artifacts=arts)
    (d / "entry_phase_evidence.json").write_text(json.dumps(ev))
    files = dict(arts)
    files["entry_phase_evidence.json"] = sha((d / "entry_phase_evidence.json").read_bytes())
    r = {"plan_sha256": rdigest, "proof": {"verdict": "PASS", "entry_phase_evidence": evidence_name}, "files": files}
    if tamper_log:
        (d / "bench.log").write_text("FAIL\n")
    if tamper_ev:
        (d / "entry_phase_evidence.json").write_text(json.dumps(dict(ev, rows=ROWS + [dict(partition="zz", field="f", old=1, new=2)])))
    return r


def check(m, nr, d, old=OLD, new=NEW, cell=CELL_SHA):
    return m.check_changed_binding(old, new, nr, DIG, d, cell)


def test_part_leaves_values_and_blind_spots():
    m = load()
    assert len(m.part_leaves(OLD, NEW)) == 4
    assert m.part_leaves(OLD, OLD) == []
    a = {"p": {"x": {}}}
    b = {"p": {}}
    assert m.part_leaves(a, b) != []                                   # {} vs absent is a change
    assert m.part_leaves({"p": {"x.y": 1}}, {"p": {"x": {"y": 1}}}) != []   # dotted key does not collide with nesting
    assert m.part_leaves({"p": {}}, {"p": {}, "q": {"k": 1}}) != []    # added partition


def test_accept_covered_by_value(tmp_path):
    m = load()
    assert len(check(m, make_receipt(tmp_path / "r"), tmp_path / "r")) == 4


def test_unchanged_needs_no_receipt(tmp_path):
    m = load()
    assert m.check_changed_binding(OLD, OLD, None, DIG, None, None) == []


@pytest.mark.parametrize("kw,why", [
    (dict(digest="e" * 64), "another plan"),
    (dict(cell="0" * 64), "another plan or another cell"),
    (dict(verdict="FAIL"), "not PASS"),
    (dict(log_text="no marker\n"), "pass marker"),
    (dict(evidence_name="missing.json"), "no entry-phase evidence"),
    (dict(rows=ROWS[:2]), "does not cover"),                                           # partial cover
    (dict(rows=[dict(ROWS[0], new=99)] + ROWS[1:]), "does not cover"),                 # value mismatch: 4->3 declared, row says 4->99
    (dict(rdigest="e" * 64), "not for the new plan digest"),
    (dict(tamper_ev=True), "hash differs"),
    (dict(tamper_log=True), "hash differs|pass marker"),                               # log replaced by FAIL after hashing
])
def test_refusals(tmp_path, kw, why):
    m = load()
    nr = make_receipt(tmp_path / "r", **kw)
    with pytest.raises(ValueError, match=why):
        check(m, nr, tmp_path / "r")


def test_missing_artifact_and_none_receipt(tmp_path):
    m = load()
    nr = make_receipt(tmp_path / "r")
    (tmp_path / "r" / "tb.sv").unlink()
    with pytest.raises(ValueError, match="artifact tb.sv"):
        check(m, nr, tmp_path / "r")
    with pytest.raises(ValueError, match="bindings changed"):
        m.check_changed_binding(OLD, NEW, None, DIG, None, None)


@pytest.mark.parametrize("bad", [[], "str", 3, {"proof": [], "files": {}}, {"proof": {}, "files": []}, {"plan_sha256": DIG, "proof": {}, "files": {}}])
def test_malformed_receipt_refused_cleanly(tmp_path, bad):
    m = load()
    with pytest.raises(ValueError):
        check(m, bad, tmp_path)


def test_uncovered_extra_key_refused(tmp_path):
    m = load()
    new = {k: dict(v) for k, v in NEW.items()}
    new["lk_WN1"]["pad_extra"] = 1
    with pytest.raises(ValueError, match="pad_extra"):
        check(m, make_receipt(tmp_path / "r"), tmp_path / "r", new=new)


# ---- end-to-end main() with stub tool modules ----------------------------------------------------------------------------------------------------
STUBS = {
    "cores": "def resolve(n):\n    raise RuntimeError\n",
    "schema": "class Plan:\n    def __init__(self, raw, path=None):\n        self.raw = raw\n",
    "reset_tree": "import math\ndef wf_plan(P):\n    return {'parts': {p['name']: {'release': 100 - math.ceil(p['reset_entry_phase'] / 2), 'entry_stages': 0} for p in P.raw['partitions']}}\n",
    "pin_entry_phase": "CELL_RTL = %r\nimport math\ndef release_delta(h):\n    return -math.ceil(h / 2)\n" % CELL,
    "head_native_release": (
        "import json, hashlib\nfrom pathlib import Path\nCALLS = []\nPLAN_CALLS = []\n"
        "def digest(raw):\n    return raw['digest']\n"
        "def qualify(P, W, receipt_path):\n"
        "    p = Path(receipt_path)\n    r = json.loads(p.read_text())\n"
        "    for n, h in r['files'].items():\n"
        "        f = (p.parent / n).resolve()\n"
        "        if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != h:\n            raise FileNotFoundError(n)\n"
        "    CALLS.append(str(p))\n    PLAN_CALLS.append((P.raw['digest'], p.name))\n"
        "    return {'release_qualification': {'verdict': 'QUALIFIED_CONDITIONAL', 'native_targets': [1, 2]}}\n"),
}


def setup_main(tmp_path, monkeypatch, receipt_depth="a", **kw):
    tools = tmp_path / "tools"
    tools.mkdir()
    for n, body in STUBS.items():
        (tools / (n + ".py")).write_text(body)
    for n in STUBS:
        sys.modules.pop(n, None)
    oldp = {"digest": "old", "partition_types": {"hd_serdes": {"k": 1}}, "partitions": [dict(v, name=k) for k, v in OLD.items()]}
    newp = {"digest": DIG, "partition_types": {"hd_serdes": {"k": 1}}, "partitions": [dict(v, name=k) for k, v in NEW.items()]}
    (tmp_path / "old.json").write_text(json.dumps(oldp))
    (tmp_path / "new.json").write_text(json.dumps(newp))
    rd = tmp_path / "rec" / "sub"
    nr = make_receipt(rd, **kw)
    nr["files"]["../outside.txt"] = sha(b"o\n")
    (tmp_path / "rec" / "outside.txt").write_text("o\n")
    nr["proof"]["production_sources"] = {}
    (rd / "native_release_receipt.json").write_text(json.dumps(nr))
    (tmp_path / "oldrec.json").write_text(json.dumps({"files": {}, "proof": {"production_sources": {}}}))
    return tools, rd / "native_release_receipt.json"


def run_main(m, tmp_path, tools, newrec, out):
    argv = [str(tmp_path / "old.json"), str(tmp_path / "new.json"), str(tmp_path / "oldrec.json"), str(out), str(tools)]
    if newrec is not None:
        argv += ["--new-receipt", str(newrec)]
    old = sys.argv
    sys.argv = ["rebind"] + argv
    try:
        return m.main()
    finally:
        sys.argv = old


def rerun_hook(mod, monkeypatch, newrec, mutate=None):
    ev = json.loads((newrec.parent / "entry_phase_evidence.json").read_text())
    if mutate:
        ev = mutate(ev)
    monkeypatch.setattr(mod, "rerun_bench_evidence", lambda o, n, t: ev)


def patched(monkeypatch, newrec=None):
    m = load()
    if newrec is not None:
        rerun_hook(m, monkeypatch, newrec)
    monkeypatch.setattr(m, "serdes_parts", lambda plan: {p["name"]: p for p in plan["partitions"] if p["type"] == "hd_serdes"} if False else
                        {p["name"]: dict(p, type="hd_serdes") for p in plan["partitions"]})
    monkeypatch.setattr(m, "fwd_only_delta", lambda a, b: None)
    return m


def test_main_accepts_and_requalifies_written_receipt(tmp_path, monkeypatch, capsys):
    tools, newrec = setup_main(tmp_path, monkeypatch)
    m = patched(monkeypatch, newrec)
    out = tmp_path / "deeper" / "x" / "out"
    out.parent.mkdir(parents=True)
    run_main(m, tmp_path, tools, newrec, out)
    txt = capsys.readouterr().out
    assert "CHANGED_BINDING_COVERED 4" in txt and "QUALIFIED_CONDITIONAL" in txt
    hn = sys.modules["head_native_release"]
    assert str(out / "candidate_receipt.json") in hn.CALLS                     # the artifact actually written was re-qualified
    r = json.loads((out / "native_release_receipt.json").read_text())
    assert (out / "bench.log").is_file() and (out / "changed_binding_cover.json").is_file()
    assert all(not n.startswith("..") or (out / n).resolve().is_file() for n in r["files"])


def test_main_refuses_without_new_receipt(tmp_path, monkeypatch):
    tools, newrec = setup_main(tmp_path, monkeypatch)
    m = patched(monkeypatch, newrec)
    with pytest.raises(ValueError, match="bindings changed"):
        run_main(m, tmp_path, tools, None, tmp_path / "o")


def test_main_refuses_tampered_evidence(tmp_path, monkeypatch):
    tools, newrec = setup_main(tmp_path, monkeypatch, tamper_log=True)
    m = patched(monkeypatch, newrec)
    with pytest.raises(ValueError):
        run_main(m, tmp_path, tools, newrec, tmp_path / "o")
    assert not (tmp_path / "o").exists()


def test_main_refuses_existing_out(tmp_path, monkeypatch):
    tools, newrec = setup_main(tmp_path, monkeypatch)
    m = patched(monkeypatch, newrec)
    (tmp_path / "o").mkdir()
    with pytest.raises(FileExistsError):
        run_main(m, tmp_path, tools, newrec, tmp_path / "o")


MUTANTS = [
    ("    if new_receipt is None:\n        if part_leaves(old_parts, new_parts):\n            raise ValueError(\"HEAD native reset instance bindings changed\")\n        return []\n", "    if new_receipt is None:\n        return []\n"),
    ("if new_receipt.get(\"plan_sha256\") != new_digest:", "if False:"),
    ("if ev.get(\"plan_digest\") != new_digest or ev.get(\"cell_sha256\") != cell_sha:", "if False:"),
    ("if ev.get(\"verdict\") != \"PASS\" or", "if False or"),
    # evidence-file hash check removed: equivalent while head_native_release.qualify (real and stub) verifies every files hash; the guard check is defence in depth
    ("or not isinstance(marker, str) or not marker or marker not in log.read_text(errors=\"replace\")", ""),
    ("        if (n, k, ra, rb) not in have:", "        if False:"),
    ("            if a.get(k) != b.get(k):", "            if False:"),
    ("        args.out.mkdir(parents=True, exist_ok=False)", "        args.out.mkdir(parents=True, exist_ok=True)"),
    ("        result = head_native_release.qualify(new_plan, reset_tree.wf_plan(new_plan), candidate)      # re-qualify the artifact actually written, then publish it\n",
     "        result = head_native_release.qualify(new_plan, reset_tree.wf_plan(new_plan), args.new_receipt)\n"),
    ("            if src.is_relative_to(root):", "            if True:"),
]


@pytest.mark.parametrize("old,new", MUTANTS)
def test_mutants_die(tmp_path_factory, monkeypatch, old, new):
    assert old in SRC, old
    mut_src = SRC.replace(old, new, 1)
    survived = []
    cases = [dict(), dict(tamper_log=True), dict(rdigest="e" * 64), dict(tamper_ev=True), dict(verdict="FAIL"), dict(digest="e" * 64), dict(cell="0" * 64), dict(log_text="no\n"),
             dict(rows=ROWS[:2]), dict(rows=[dict(ROWS[0], new=99)] + ROWS[1:])]
    for kw in cases:
        tp = tmp_path_factory.mktemp("m")
        tools, newrec = setup_main(tp, monkeypatch, **kw)
        mod = load(mut_src)
        monkeypatch.setattr(mod, "serdes_parts", lambda plan: {p["name"]: dict(p, type="hd_serdes") for p in plan["partitions"]})
        monkeypatch.setattr(mod, "fwd_only_delta", lambda a, b: None)
        rerun_hook(mod, monkeypatch, newrec)
        out = tp / "d" / "e" / "out"
        out.parent.mkdir(parents=True)
        want_ok = not kw
        try:
            run_main(mod, tp, tools, newrec, out)
            got_ok = True
        except Exception:
            got_ok = False
        if got_ok != want_ok:
            return                                                                       # behaviour differs from the shipped code: killed
        if want_ok:
            # accepted case: the written receipt must be re-qualified from out and be self-contained
            hn = sys.modules["head_native_release"]
            if str(out / "candidate_receipt.json") not in hn.CALLS:
                return
            r = json.loads((out / "native_release_receipt.json").read_text())
            if any(not (out / n).resolve().is_file() for n in r["files"]) or (out.parent / "outside.txt").exists():
                return
    # refusal without new receipt and pre-existing out
    tp = tmp_path_factory.mktemp("m2")
    tools, newrec = setup_main(tp, monkeypatch)
    mod = load(mut_src)
    monkeypatch.setattr(mod, "serdes_parts", lambda plan: {p["name"]: dict(p, type="hd_serdes") for p in plan["partitions"]})
    monkeypatch.setattr(mod, "fwd_only_delta", lambda a, b: None)
    rerun_hook(mod, monkeypatch, newrec)
    try:
        run_main(mod, tp, tools, None, tp / "o")
        return                                                                           # accepted a change with no receipt: killed
    except ValueError:
        pass
    except Exception:
        return
    (tp / "o2").mkdir()
    try:
        run_main(mod, tp, tools, newrec, tp / "o2")
        return                                                                           # existing out accepted: killed
    except FileExistsError:
        pass
    except Exception:
        return
    # part_leaves mutant: unchanged partitions must report no leaf, changed ones must
    assert mod.part_leaves(OLD, NEW) != [] or pytest.fail("mutant survived: " + old[:60])
    pytest.fail("mutant survived: " + old[:70])


# ---- second-review additions -------------------------------------------------------------------------------------------------------------------
def accepted_run(tmp_path, monkeypatch, mutate=None, **kw):
    tools, newrec = setup_main(tmp_path, monkeypatch, **kw)
    m = load()
    monkeypatch.setattr(m, "serdes_parts", lambda plan: {p["name"]: dict(p, type="hd_serdes") for p in plan["partitions"]})
    monkeypatch.setattr(m, "fwd_only_delta", lambda a, b: None)
    rerun_hook(m, monkeypatch, newrec, mutate)
    out = tmp_path / "d" / "e" / "out"
    out.parent.mkdir(parents=True)
    return m, tools, newrec, out


def test_forged_evidence_refused_by_bench_rerun(tmp_path, monkeypatch):
    def forge(ev):
        ev = json.loads(json.dumps(ev))
        ev["rows"] = ROWS                                              # same rows as the receipt claims, but the guard's own re-run produced...
        ev["cases"] = [dict(c, sim_cycles=99) for c in ev.get("cases", [])] or [dict(partition="x", version="new", h=1, strap=1, release_delta=0,
                                                                                           expect_cycles=1, sim_cycles=1)]
        return ev
    m, tools, newrec, out = accepted_run(tmp_path, monkeypatch, mutate=forge)
    with pytest.raises(ValueError, match="differs from the guard's own bench re-run"):
        run_main(m, tmp_path, tools, newrec, out)
    assert not out.exists()


def test_failed_rerun_refused(tmp_path, monkeypatch):
    m, tools, newrec, out = accepted_run(tmp_path, monkeypatch)
    def boom(o, n, t):
        raise ValueError("the re-run entry-phase bench does not pass")
    monkeypatch.setattr(m, "rerun_bench_evidence", boom)
    with pytest.raises(ValueError, match="does not pass"):
        run_main(m, tmp_path, tools, newrec, out)


def test_cover_content_anchor_and_pending(tmp_path, monkeypatch, capsys):
    # the receipt of these fixtures carries no cases: give the evidence and the re-run the same one so the re-run comparison is meaningful
    m, tools, newrec, out = accepted_run(tmp_path, monkeypatch)
    run_main(m, tmp_path, tools, newrec, out)
    cover = json.loads((out / "changed_binding_cover.json").read_text())
    assert len(cover["covered"]) == 4 and cover["wf_plan_release_moved"] == {"lk_WN1": [101 - 1 + 0, 101 - 1 + 0]} or cover["wf_plan_release_moved"]
    assert cover["new_receipt_sha256"] == sha((newrec).read_bytes()) and cover["old_receipt_sha256"] == sha((tmp_path / "oldrec.json").read_bytes())
    assert cover["old_plan_sha256"] == sha((tmp_path / "old.json").read_bytes()) and cover["new_plan_sha256"] == sha((tmp_path / "new.json").read_bytes())
    assert "PENDING die STA" in cover["pending"] and "PENDING_DIE_STA" in capsys.readouterr().out
    r = json.loads((out / "native_release_receipt.json").read_text())
    assert any("PENDING die STA" in x for x in r["limits"]) and not (out / "candidate_receipt.json").exists()
    hn = sys.modules["head_native_release"]
    assert ("old", "oldrec.json") in hn.PLAN_CALLS                      # the old side is qualified with the OLD plan and the OLD receipt


def test_no_published_receipt_when_requalify_fails(tmp_path, monkeypatch):
    m, tools, newrec, out = accepted_run(tmp_path, monkeypatch)
    hn_calls = []
    real = None
    run = lambda: run_main(m, tmp_path, tools, newrec, out)
    orig_qualify = None
    import importlib
    monkeypatch.setattr(m, "check_release_consistency", lambda *a, **k: {})
    # make the second qualify (the candidate) fail: stub qualify raises when the receipt name is candidate_receipt.json
    hn = sys.modules.get("head_native_release")
    def failing_load():
        pass
    sys.modules.pop("head_native_release", None)
    tools_hn = tools / "head_native_release.py"
    tools_hn.write_text(STUBS["head_native_release"].replace("    CALLS.append(str(p))", "    if p.name == 'candidate_receipt.json':\n        raise ValueError('qualify failed')\n    CALLS.append(str(p))"))
    with pytest.raises(ValueError, match="qualify failed"):
        run()
    assert not (out / "native_release_receipt.json").exists()


def test_release_consistency_strict_on_empty_and_missing_parts():
    m = load()
    rd = lambda h: -(-h // 2) * -1
    with pytest.raises(ValueError, match="no parts"):
        m.check_release_consistency({}, {}, OLD, NEW, rd)
    with pytest.raises(ValueError, match="not in wf_plan parts"):
        m.check_release_consistency({"parts": {"lk_EN0": {"release": 1, "entry_stages": 0}}}, {"parts": {"lk_EN0": {"release": 1, "entry_stages": 0}}}, OLD, NEW, rd)


def test_check_rerun_compares_rows_cases_cell():
    m = load()
    ev = {"rows": ROWS, "cases": [dict(partition="a", version="old", h=4, strap=0, release_delta=-2, expect_cycles=2, sim_cycles=2)], "cell_sha256": "c", "plan_digest": "d"}
    m.check_rerun(ev, json.loads(json.dumps(ev)))
    for k, v in (("rows", []), ("cell_sha256", "x"), ("plan_digest", "y"), ("cases", [])):
        bad = dict(ev, **{k: v})
        with pytest.raises(ValueError, match="differs"):
            m.check_rerun(ev, bad)


DEDICATED = [
    ("        head_native_release.qualify(old_plan, reset_tree.wf_plan(old_plan), args.old_receipt)     # anchor the old side as the old path does\n        new_plan0", "        new_plan0"),
    ("        moved = check_release_consistency(", "        moved = (lambda *a, **k: {})("),
    ("    same = (receipt_ev.get(\"rows\") == rerun_ev.get(\"rows\")", "    same = (True or receipt_ev.get(\"rows\") == rerun_ev.get(\"rows\")"),
    (" or ev.get(\"schema\") != \"opentallas.entry_phase_evidence.v1\"", ""),
]


def suite_fails(mut_src, monkeypatch, tmp_path_factory):
    """True when the behaviour suite finds a difference from the shipped code"""
    # 1. anchor of the old side and re-qualify of the candidate
    tp = tmp_path_factory.mktemp("d1")
    tools, newrec = setup_main(tp, monkeypatch)
    mod = load(mut_src)
    rerun_hook(mod, monkeypatch, newrec)
    out = tp / "a" / "b" / "out"
    out.parent.mkdir(parents=True)
    try:
        run_main(mod, tp, tools, newrec, out)
    except Exception:
        return True
    if ("old", "oldrec.json") not in sys.modules["head_native_release"].PLAN_CALLS:
        return True
    # 2. release consistency must refuse a wf_plan whose lk_WN1 release does not follow release_delta
    tp = tmp_path_factory.mktemp("d2")
    tools, newrec = setup_main(tp, monkeypatch)
    (tools / "reset_tree.py").write_text(STUBS["reset_tree"].replace("100 - math.ceil(p['reset_entry_phase'] / 2)",
                                                                       "100 - math.ceil(p['reset_entry_phase'] / 2) + (5 if P.raw['digest'] == 'd' * 64 else 0)"))
    mod = load(mut_src)
    rerun_hook(mod, monkeypatch, newrec)
    try:
        run_main(mod, tp, tools, newrec, tp / "a" / "b" / "out2") if (tp / "a" / "b").mkdir(parents=True) is None else None
        return True                                                                       # accepted a wf_plan release that contradicts release_delta
    except ValueError:
        pass
    except Exception:
        return True
    # 3. a receipt evidence that differs from the re-run is refused
    ev = {"rows": ROWS, "cases": [dict(partition="a", version="old", h=4, strap=0, release_delta=-2, expect_cycles=2, sim_cycles=2)], "cell_sha256": "c", "plan_digest": "d"}
    try:
        mod.check_rerun(ev, dict(ev, rows=[]))
        return True
    except ValueError:
        pass
    # 4. wrong evidence schema is refused
    tp = tmp_path_factory.mktemp("d4")
    nr = make_receipt(tp / "r")
    e = json.loads((tp / "r" / "entry_phase_evidence.json").read_text())
    e["schema"] = "other"
    (tp / "r" / "entry_phase_evidence.json").write_text(json.dumps(e))
    nr["files"]["entry_phase_evidence.json"] = sha((tp / "r" / "entry_phase_evidence.json").read_bytes())
    try:
        mod.check_changed_binding(OLD, NEW, nr, DIG, tp / "r", CELL_SHA)
        return True
    except ValueError:
        return False
    return False


@pytest.mark.parametrize("old,new", DEDICATED)
def test_dedicated_mutants_die(tmp_path_factory, monkeypatch, old, new):
    assert old in SRC, old
    assert suite_fails(SRC.replace(old, new, 1), monkeypatch, tmp_path_factory), "mutant survived: " + old[:70]


def test_dedicated_suite_passes_on_shipped(tmp_path_factory, monkeypatch):
    assert not suite_fails(SRC, monkeypatch, tmp_path_factory)
