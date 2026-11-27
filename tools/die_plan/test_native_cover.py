"""G0 requires changed_binding_cover.json when hd_serdes partitions differ from the band base (blocking by default, opt-out OT_NATIVE_COVER_REQUIRED=0 is an advisory)."""
import json
from pathlib import Path

import pytest

import check as C

SRC = (Path(__file__).parent / "check.py").read_text()


def plan(*phases):
    return {"partition_types": {"hd_serdes": {"module": "ot_s81hd_serdes"}},
            "partitions": [{"name": n, "type": "hd_serdes", "reset_entry_phase": h} for n, h in phases] + [{"name": "x", "type": "other", "reset_entry_phase": 1}]}


BASE = plan(("lk_EN0", 4), ("lk_WN1", 3), ("lk_WN2", 2))
NEW = plan(("lk_EN0", 3), ("lk_WN1", 2), ("lk_WN2", 2))


def rec(tmp_path, covered=("partitions[lk_EN0].reset_entry_phase", "partitions[lk_WN1].reset_entry_phase"), raw=None, write=True):
    d = tmp_path / "r"
    d.mkdir(exist_ok=True)
    (d / "native_release_receipt.json").write_text("{}")
    if write:
        (d / "changed_binding_cover.json").write_text(raw if raw is not None else json.dumps({"covered": list(covered)}))
    return d / "native_release_receipt.json"


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv("OT_NATIVE_COVER_REQUIRED", "1")


def test_default_is_blocking(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_NATIVE_COVER_REQUIRED", raising=False)
    assert "is missing" in C.native_cover_error(NEW, BASE, rec(tmp_path, write=False))
    assert "no native reset receipt" in C.native_cover_error(NEW, BASE, None)
    (tmp_path / "ok").mkdir()
    assert C.native_cover_error(NEW, BASE, rec(tmp_path / "ok")) is None
    assert C.native_cover_optout_advisory(NEW, BASE) is None                       # no advisory unless the opt-out is set


def test_opt_out_is_logged_as_an_advisory(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_NATIVE_COVER_REQUIRED", "0")
    assert C.native_cover_error(NEW, BASE, rec(tmp_path, write=False)) is None
    assert C.native_cover_error(NEW, BASE, None) is None
    adv = C.native_cover_optout_advisory(NEW, BASE)
    assert "OT_NATIVE_COVER_REQUIRED=0" in adv and "lk_EN0" in adv
    assert C.native_cover_optout_advisory(BASE, BASE) is None                      # nothing differs: nothing to report
    assert C.native_cover_optout_advisory(NEW, None) is None


def test_no_band_base_or_no_difference(tmp_path, on):
    assert C.native_cover_error(NEW, None, rec(tmp_path, write=False)) is None
    assert C.native_cover_error(BASE, BASE, rec(tmp_path, write=False)) is None
    other = json.loads(json.dumps(NEW))
    other["partitions"][-1]["reset_entry_phase"] = 9                           # a non-serdes partition changed: not this check's business
    assert C.native_cover_error(other, NEW, rec(tmp_path, write=False)) is None


def test_covered_difference_passes(tmp_path, on):
    assert C.native_cover_error(NEW, BASE, rec(tmp_path)) is None


@pytest.mark.parametrize("kw,why", [
    (dict(write=False), "is missing"),
    (dict(covered=("partitions[lk_EN0].reset_entry_phase",)), "does not cover differing partition"),
    (dict(raw="not json"), "malformed"),
    (dict(raw=json.dumps({"covered": 5})), "malformed"),
    (dict(raw=json.dumps({})), "malformed"),
])
def test_refusals(tmp_path, on, kw, why):
    assert why in C.native_cover_error(NEW, BASE, rec(tmp_path, **kw))


def test_no_receipt_with_difference_errors(on):
    assert "no native reset receipt" in C.native_cover_error(NEW, BASE, None)


@pytest.mark.parametrize("old,new", [
    ("    if _os.environ.get(\"OT_NATIVE_COVER_REQUIRED\") == \"0\" or band_raw is None:\n        return None\n", "    if band_raw is None:\n        return None\n"),
    ("    if not differing:\n        return None\n", ""),
    ("    if not cover.is_file():\n", "    if False:\n"),
    ("    missing = [n for n in differing if n not in covered]\n    if missing:\n", "    missing = []\n    if missing:\n"),
    ("a.get(n) != b.get(n)", "False"),
])
def test_mutants_die(tmp_path_factory, monkeypatch, old, new):
    assert old in SRC, old
    ns = {"__name__": "mut", "Path": Path}
    start = SRC.index("def native_cover_error(")
    end = SRC.index("def run(raw, png=None,")
    exec(compile(SRC[start:end].replace(old, new, 1), "m", "exec"), ns)
    fn = ns["native_cover_error"]

    def call(f, *args):
        try:
            return f(*args)
        except Exception as e:                                                   # a crash is a behaviour difference too
            return "EXC " + type(e).__name__

    def outcome(f, env):
        if env:
            monkeypatch.setenv("OT_NATIVE_COVER_REQUIRED", "1")
        else:
            monkeypatch.setenv("OT_NATIVE_COVER_REQUIRED", "0")
        mk = lambda **kw: rec(tmp_path_factory.mktemp("c"), **kw)
        return [call(f, NEW, BASE, mk(write=False)), call(f, NEW, BASE, mk(covered=("partitions[lk_EN0].reset_entry_phase",))),
                call(f, NEW, BASE, mk()), call(f, BASE, BASE, mk(write=False)), call(f, NEW, BASE, None)]

    assert outcome(fn, True) != outcome(C.native_cover_error, True) or outcome(fn, False) != outcome(C.native_cover_error, False), "mutant survived: " + old[:60]


def test_run_wires_the_check():
    assert "_ca = native_cover_optout_advisory(raw, band_base)" in SRC and "R.warn(\"native_reset_cover\", _ca)" in SRC
    assert "_ce = native_cover_error(raw, band_base, native_reset_receipt)" in SRC and 'R.err("native_reset_cover", _ce)' in SRC
