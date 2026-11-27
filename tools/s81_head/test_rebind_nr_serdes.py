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
    ns = {"__name__": "rebind_t"}
    exec(compile(SRC if src is None else src, "rebind", "exec"), ns)
    m = types.SimpleNamespace()
    m.__dict__.update(ns)
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
    "reset_tree": "def wf_plan(P):\n    return {}\n",
    "pin_entry_phase": "CELL_RTL = %r\nimport math\ndef release_delta(h):\n    return -math.ceil(h / 2)\n" % CELL,
    "head_native_release": (
        "import json, hashlib\nfrom pathlib import Path\nCALLS = []\n"
        "def digest(raw):\n    return raw['digest']\n"
        "def qualify(P, W, receipt_path):\n"
        "    p = Path(receipt_path)\n    r = json.loads(p.read_text())\n"
        "    for n, h in r['files'].items():\n"
        "        f = (p.parent / n).resolve()\n"
        "        if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != h:\n            raise FileNotFoundError(n)\n"
        "    CALLS.append(str(p))\n"
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


def patched(monkeypatch):
    m = load()
    monkeypatch.setattr(m, "serdes_parts", lambda plan: {p["name"]: p for p in plan["partitions"] if p["type"] == "hd_serdes"} if False else
                        {p["name"]: dict(p, type="hd_serdes") for p in plan["partitions"]})
    monkeypatch.setattr(m, "fwd_only_delta", lambda a, b: None)
    return m


def test_main_accepts_and_requalifies_written_receipt(tmp_path, monkeypatch, capsys):
    tools, newrec = setup_main(tmp_path, monkeypatch)
    m = patched(monkeypatch)
    out = tmp_path / "deeper" / "x" / "out"
    out.parent.mkdir(parents=True)
    run_main(m, tmp_path, tools, newrec, out)
    txt = capsys.readouterr().out
    assert "CHANGED_BINDING_COVERED 4" in txt and "QUALIFIED_CONDITIONAL" in txt
    hn = sys.modules["head_native_release"]
    assert str(out / "native_release_receipt.json") in hn.CALLS                     # the artifact actually written was re-qualified
    r = json.loads((out / "native_release_receipt.json").read_text())
    assert (out / "bench.log").is_file() and (out / "changed_binding_cover.json").is_file()
    assert all(not n.startswith("..") or (out / n).resolve().is_file() for n in r["files"])


def test_main_refuses_without_new_receipt(tmp_path, monkeypatch):
    tools, newrec = setup_main(tmp_path, monkeypatch)
    m = patched(monkeypatch)
    with pytest.raises(ValueError, match="bindings changed"):
        run_main(m, tmp_path, tools, None, tmp_path / "o")


def test_main_refuses_tampered_evidence(tmp_path, monkeypatch):
    tools, newrec = setup_main(tmp_path, monkeypatch, tamper_log=True)
    m = patched(monkeypatch)
    with pytest.raises(ValueError):
        run_main(m, tmp_path, tools, newrec, tmp_path / "o")
    assert not (tmp_path / "o").exists()


def test_main_refuses_existing_out(tmp_path, monkeypatch):
    tools, newrec = setup_main(tmp_path, monkeypatch)
    m = patched(monkeypatch)
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
    ("        result = head_native_release.qualify(new_plan, reset_tree.wf_plan(new_plan), accepted)       # re-qualify the artifact actually written",
     "        result = head_native_release.qualify(new_plan, reset_tree.wf_plan(new_plan), args.new_receipt)"),
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
            if str(out / "native_release_receipt.json") not in hn.CALLS:
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
