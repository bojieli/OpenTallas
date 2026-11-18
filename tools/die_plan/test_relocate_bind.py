"""relocate_bind.py: HDL bytes stay receipt-consistent (QC-TYPES-R3 11-18: 17/130 N3 receipts broke on comment rewrites)."""
import hashlib, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import relocate_bind as RB

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
