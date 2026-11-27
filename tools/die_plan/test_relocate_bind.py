"""relocate_bind.py: HDL bytes stay receipt-consistent (QC-TYPES-R3 11-18: 17/130 N3 receipts broke on comment rewrites)."""
import hashlib, json, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import relocate_bind as RB
import bind_stream as BS

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _receipt(sv):
    tree = {"root": "u_rst_root", "taps": {"0": ["a"]}}
    rec = dict(schema="opentallas.bound_reset_source.v1", plan_type=sv.stem, bound_module=sv.stem, tree=tree,
               tree_sha256=RB._digest(tree), bound_rtl_sha256=sha(sv))
    sv.with_suffix(".reset_tree.json").write_text(json.dumps(rec, indent=1) + "\n")


def _fixture(tmp):
    old, new, bind = tmp / "old", tmp / "new", tmp / "bind"
    for t in (old, new):
        (t / "rtl").mkdir(parents=True)
        (t / "rtl" / "leaf.sv").write_text("module leaf; endmodule\n")
        (t / ".src-manifest.sha256").write_text("x\n")
    (bind / "rtl").mkdir(parents=True)
    c = bind / "rtl" / "tc.sv"          # comment-only: yosys source-location notes
    c.write_text(f"module tc;\n  assign a = b;  // {old}/rtl/leaf.sv:3.1\nendmodule\n")
    k = bind / "rtl" / "tk.sv"          # path in code
    k.write_text(f'module tk;\n  initial $readmemh("{old}/rtl/leaf.sv", m);\nendmodule\n')
    _receipt(c); _receipt(k)
    (bind / "bind.f").write_text(f"{old}/rtl/leaf.sv\n")
    return old, new, bind


def test_tree_keeps_comment_hdl_and_rehashes_code_hdl(tmp_path):
    old, new, bind = _fixture(tmp_path)
    before_c = sha(bind / "rtl" / "tc.sv"); before_k_receipt = (bind / "rtl" / "tk.reset_tree.json").read_text()
    out = tmp_path / "out"
    RB.main(["tree", str(old), str(new), str(bind), str(out)])
    assert sha(out / "rtl" / "tc.sv") == before_c                       # bytes untouched
    assert str(new) in (out / "rtl" / "tk.sv").read_text()              # code path relocated
    assert str(new) in (out / "bind.f").read_text()
    assert RB.receipt_errors(out) == []
    assert (bind / "rtl" / "tk.reset_tree.json").read_text() == before_k_receipt   # source bind never edited
    r = json.loads((out / "RELOCATED.json").read_text())
    assert r["hdl_comment_only_kept"] == ["rtl/tc.sv"] and r["receipts_rehashed"] == ["rtl/tk.reset_tree.json"]


def test_check_receipts_flags_comment_rewrite(tmp_path):
    old, new, bind = _fixture(tmp_path)
    sv = bind / "rtl" / "tc.sv"; sv.write_text(sv.read_text().replace(str(old), str(new)))   # the old tool's behaviour
    assert [b[0] for b in RB.receipt_errors(bind)] == ["tc.reset_tree.json"]


def test_self_pass(tmp_path):
    old, new, bind = _fixture(tmp_path)
    out = tmp_path / "out"
    RB.main(["tree", str(old), str(new), str(bind), str(out)])
    (out / "bind_report.json").write_text(json.dumps({"rtl": f"{bind}/rtl/tk.sv"}))
    RB.main(["self", str(bind), str(bind), str(out)])
    assert str(out) in (out / "bind_report.json").read_text() and RB.receipt_errors(out) == []


def test_tree_writes_given_path_not_realpath_and_also_prefix(tmp_path):
    """epyc2 N4 11-18: kw45 was a symlink to scratch3; the bind must name the fleet-wide (given) path, and kit_rtl lists that
    used the realpath spelling of the previous tree are rewritten via --also."""
    real = tmp_path / "s3"; real.mkdir(); link = tmp_path / "s2"; link.symlink_to(real)
    old, new, bind = _fixture(real)
    prev = real / "prev"; (prev / "rtl").mkdir(parents=True); (prev / "rtl" / "leaf.sv").write_text("module leaf; endmodule\n")
    (bind / "kit.f").write_text(f"{prev}/rtl/leaf.sv\n")            # realpath spelling of an earlier tree
    out = link / "out"
    RB.main(["tree", str(old), str(link / "new"), str(bind), str(out), "--also", str(prev)])
    txt = (real / "out" / "bind.f").read_text() + (real / "out" / "kit.f").read_text()
    assert str(link / "new") + "/rtl/leaf.sv" in txt and str(real / "new") not in txt and str(prev) not in txt
    assert RB.receipt_errors(real / "out") == []


def _scoped_capture(tmp_path):
    old, new, bind = _fixture(tmp_path)
    producer = tmp_path / "unmounted-producer"
    station = bind / "native_internal_stations" / "tk"
    station.mkdir(parents=True)
    (station / "kit_rtl.json").write_text(json.dumps({"files": [f"{producer}/rtl/tk.sv", f"{old}/rtl/leaf.sv"]}))
    cells = bind / "rtl" / "bind_cells.sv"
    cells.write_text("module cells; endmodule\n")
    plan = old / "rtl" / "leaf.sv"
    ctx = BS.start(bind, {"asbuilt_sha256": sha(plan)}, plan, plan)
    typ = BS.write_type(ctx, "tk", "tk", 1, [bind / "rtl" / "tk.sv"], [plan], [], cells, {"u_tk": "#(.N(17))"})
    rec = bind / BS.DIR / "tk.json"
    rec.write_text(json.dumps(typ).replace(str(bind), str(producer)))
    (bind / "bind_report.json").write_text(json.dumps({"probe_only": {"requested": ["tk"]},
                                                      "plan_sha256": sha(plan)}))
    BS.mark_ended(ctx)
    return old, new, bind, producer, rec


def test_scoped_capture_survives_tree_then_self_relocation(tmp_path):
    old, new, bind, producer, rec = _scoped_capture(tmp_path)
    orig = json.loads(rec.read_text())
    original_context = sha(bind / BS.DIR / BS.CTX)
    original_receipt = sha(bind / "rtl" / "tk.reset_tree.json")
    out = tmp_path / "out"
    RB.main(["tree", str(old), str(new), str(bind), str(out)])
    intermediate = json.loads((out / BS.DIR / rec.name).read_text())
    assert intermediate["context_sha256"] == sha(out / BS.DIR / BS.CTX) != original_context
    RB.main(["self", str(producer), str(bind), str(out)])
    assert BS.instance_params(out, "tk", "tk") == {"u_tk": "#(.N(17))"}
    after, = BS.records(out, "tk", require_live=False)
    assert after["run_id"] == orig["run_id"] and after["written"] == orig["written"]
    assert after["plan_sha256"] == orig["plan_sha256"]
    assert after["files"][str(out / "rtl" / "tk.reset_tree.json")] != original_receipt
    assert BS.records(out, "tk") == []  # a moved scoped receipt never becomes live
    assert sha(bind / BS.DIR / BS.CTX) == original_context
    assert sha(bind / "rtl" / "tk.reset_tree.json") == original_receipt
    assert json.loads(rec.read_text()) == orig
    marker = out / "RELOCATED.json"
    before_retry = marker.read_bytes()
    RB.main(["self", str(producer), str(bind), str(out)])
    assert marker.read_bytes() == before_retry


def test_scoped_self_failure_after_retie_restores_staged_origin(tmp_path, monkeypatch):
    old, new, bind, producer, _ = _scoped_capture(tmp_path)
    out = tmp_path / "out"
    RB.main(["tree", str(old), str(new), str(bind), str(out)])
    marker = out / "RELOCATED.json"
    files = {p: p.read_bytes() for p in out.rglob("*") if p.is_file()}
    retie = RB._retie_stream

    def fail_after_retie(*args, **kwargs):
        assert retie(*args, **kwargs) == ["tk.json"]
        assert not marker.exists()
        assert BS.instance_params(out, "tk", "tk") == {"u_tk": "#(.N(17))"}
        raise ValueError("injected retie failure")

    cmd = ["self", str(producer), str(bind), str(out)]
    with monkeypatch.context() as inject:
        inject.setattr(RB, "_retie_stream", fail_after_retie)
        with pytest.raises(ValueError, match="injected retie failure"):
            RB.main(cmd)
    assert {p: p.read_bytes() for p in out.rglob("*") if p.is_file()} == files
    assert "pass2_self" not in json.loads(marker.read_text())
    RB.main(cmd)
    assert not json.loads(marker.read_text())["pass2_self"]["receipt_mismatch"]
    assert BS.instance_params(out, "tk", "tk") == {"u_tk": "#(.N(17))"}


@pytest.mark.parametrize("corrupt", ["input_bytes", "context_digest"])
def test_scoped_capture_refuses_unproven_source(tmp_path, corrupt):
    old, new, bind, _, rec = _scoped_capture(tmp_path)
    if corrupt == "input_bytes":
        (bind / "native_internal_stations" / "tk" / "kit_rtl.json").write_text("{}")
    else:
        record = json.loads(rec.read_text())
        record["context_sha256"] = "a" * 64
        rec.write_text(json.dumps(record))
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="bind stream source"):
        RB.main(["tree", str(old), str(new), str(bind), str(out)])
    assert not out.exists()
