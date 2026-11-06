"""COORD 11-02 19:2x (d) (FLOW-22): UNEXPANDED_CHILD_ETM counts as covered when every child ETM is its SIGNED
child's own export (at its own signed tag, COORD 11-06 05:2x); otherwise the clock coverage stays NOT RUN (fail closed)."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signoff as S  # noqa: E402

TAG = "flow-20261102-r-kv"
LIB = """library (child_tt) { time_unit : "1ps";
cell (child) { is_macro_cell : true;
  pin (clk) { clock : true;
    timing () { timing_type : max_clock_tree_path; cell_rise (scalar) { values ("250.0"); } }
    timing () { timing_type : min_clock_tree_path; cell_rise (scalar) { values ("220.0"); } } } } }
"""


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(tmp, tag=TAG, verdict="SIGNED", lec="EQUIVALENT", view_status="signoff", lib_sha=None, prov=True):
    kit = tmp / "kit"
    (kit / "macros").mkdir(parents=True)
    lib = kit / "macros" / "child_tt.lib"
    lib.write_text(LIB)
    d = tmp / "child_resign"
    (d / "signoff").mkdir(parents=True)
    (d / "lec").mkdir()
    so = d / "signoff" / "signoff.json"
    so.write_text(json.dumps(dict(verdict=verdict, name="child")))
    (d / "lec" / "lec.json").write_text(json.dumps(dict(verdict=lec)))
    (d / "PROVENANCE.json").write_text(json.dumps(dict(kind="resign", verdict="SIGNED", flow_tag=tag, src_commit="a" * 40,
                                                       routed_db="x.odb", build_commit="b" * 40, lec="lec/lec.json")))
    if prov:
        (kit / "macros" / "child.provenance.json").write_text(json.dumps(dict(
            type="child", views_status=view_status, flow_tag=tag,
            export=dict(signoff=str(so), signoff_sha256=sha(so), files_sha256={"child_tt.lib": lib_sha or sha(lib)}))))
    return kit, lib


def coverage(lib, tag=TAG):
    r = S.clock_model_coverage([lib], {"child", "DFFHQNx1_ASAP7_75t_R"})
    assert r["status"] == "UNEXPANDED_CHILD_ETM" and r["verdict"] == "NOT RUN"
    return S.apply_signed_child_etms(r, tag)


def test_signed_child_etm_at_same_tag_is_covered(tmp_path):
    kit, lib = build(tmp_path)
    r = coverage(lib)
    assert r["status"] == "SIGNED_CHILD_ETM" and r["verdict"] == "PASS"
    ev = r["models"][0]["signed_child_etm"]
    assert ev["flow_tag"] == TAG and ev["lec_verdict"] == "EQUIVALENT" and ev["flow_basis"].endswith("PROVENANCE.json")


def test_unsigned_child_stays_not_run(tmp_path):
    kit, lib = build(tmp_path, verdict="NOT SIGNED")
    r = coverage(lib)
    assert r["status"] == "UNEXPANDED_CHILD_ETM" and r["verdict"] == "NOT RUN"
    assert "child verdict" in r["signed_child_etm_misses"][0]


def test_child_counts_at_its_own_signed_tag(tmp_path):
    # COORD 11-06 05:2x: a frozen child view signed at an older tag counts (libs = its export, LEC EQ)
    kit, lib = build(tmp_path, tag="flow-20261101-m-kv")
    r = coverage(lib)
    assert r["verdict"] == "PASS"
    ev = r["models"][0]["signed_child_etm"]
    assert ev["flow_tag"] == "flow-20261101-m-kv" and ev["parent_flow_tag"] == TAG


def test_other_tag_child_without_equivalent_lec_stays_not_run(tmp_path):
    kit, lib = build(tmp_path, tag="flow-20261101-m-kv", lec="NOT_EQUIVALENT")
    assert coverage(lib)["verdict"] == "NOT RUN"


def test_child_without_signed_tag_stays_not_run(tmp_path):
    kit, lib = build(tmp_path, tag="")
    assert coverage(lib)["verdict"] == "NOT RUN"


def test_unknown_parent_tag_stays_not_run(tmp_path, monkeypatch):
    kit, lib = build(tmp_path)
    assert coverage(lib, tag=None)["verdict"] == "NOT RUN"


def test_etm_not_from_that_signoff_stays_not_run(tmp_path):
    kit, lib = build(tmp_path, lib_sha="0" * 64)
    r = coverage(lib)
    assert r["verdict"] == "NOT RUN" and "sha256 differs" in r["signed_child_etm_misses"][0]


def test_incomplete_view_or_no_provenance_or_lec_stays_not_run(tmp_path):
    for i, kw in enumerate((dict(view_status="incomplete: x"), dict(prov=False), dict(lec="NOT_EQUIVALENT"))):
        kit, lib = build(tmp_path / str(i), **kw)
        assert coverage(lib)["verdict"] == "NOT RUN", kw


def test_consumed_coverage_reads_flow_tag_env(tmp_path, monkeypatch):
    kit, lib = build(tmp_path)
    rec = tmp_path / "libraries.json"
    rec.write_text(json.dumps(dict(status="LOADED", libraries=[dict(path="/work/macros/child_tt.lib", sha256=sha(lib))])))
    monkeypatch.delenv(S.FLOW_TAG_ENV, raising=False)
    assert S.consumed_clock_model_coverage(rec, {"kit": str(kit)}, ["child"])["verdict"] == "NOT RUN"
    monkeypatch.setenv(S.FLOW_TAG_ENV, TAG)
    r = S.consumed_clock_model_coverage(rec, {"kit": str(kit)}, ["child"])
    assert r["verdict"] == "PASS" and r["models"][0]["consumed_liberty"] == "/work/macros/child_tt.lib"


def test_resign_passes_its_tag_to_signoff():
    src = (Path(__file__).resolve().parent / "resign.py").read_text()
    assert "OT_FLOW_TAG=a.tag" in src
