"""T51-NETSRC 11-10: opt-in plan type kit_source.parent_netlist (hash-pinned mapped parent netlist, children black boxes)."""
import gzip
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bound_macro_paths as BMP  # noqa: E402
import gen_phys as G  # noqa: E402
import kit_preflight as KP  # noqa: E402

NET = """module t__p(clk, a, y);
  input clk; input a; output y;
  wire n1;
  t__p_native_w t__p_native_w (.clk(clk), .p00000(a), .p00001(n1));
  BUFx2_ASAP7_75t_R \\u_bound.u_b (.A(n1), .Y(y));
endmodule
"""


def _type(path, sha, **kw):
    return dict(module="t__p", hard_cores=[dict(inst="t__p_native_w", module="t__p_native_w", lef="v/w.lef",
                                                origin_um=[0, 0], outline_um=[1, 1])],
                kit_source=dict(parent_netlist=str(path), sha256=sha, **kw))


def _net(tmp_path, text=NET, gz=True):
    p = tmp_path / ("p.v.gz" if gz else "p.v")
    p.write_bytes(gzip.compress(text.encode()) if gz else text.encode())
    return p, hashlib.sha256(text.encode()).hexdigest()


def test_absent_is_none(tmp_path):
    assert G.kit_source_text(dict(module="m"), "t", tmp_path) is None
    assert G.stage_kit_source(dict(module="m"), "t", tmp_path, tmp_path) is None
    assert not (tmp_path / G.KIT_SOURCE_RECEIPT).exists()


def test_stage_and_receipt(tmp_path):
    p, sha = _net(tmp_path)
    kd = tmp_path / "kit"
    (kd / "rtl").mkdir(parents=True)
    (kd / "rtl" / "t__p_bound.sv").write_text("module t__p_bound(); endmodule\n")
    rec = G.stage_kit_source(_type(p, sha), "t", kd, tmp_path)
    assert rec["staged"] == "/work/rtl/t__p__kit_source.v" and rec["sha256"] == sha
    assert (kd / "rtl" / "t__p__kit_source.v").read_text() == NET
    assert rec["black_boxes"] == ["t__p_native_w"] and rec["bound_rtl_reference"] == ["t__p_bound.sv"]
    assert json.loads((kd / G.KIT_SOURCE_RECEIPT).read_text())["schema"] == G.KIT_SOURCE_SCHEMA


@pytest.mark.parametrize("bad,match", [
    ("0" * 64, "!= plan pin"),
    ("short", "64-hex sha256"),
])
def test_hash_refusal(tmp_path, bad, match):
    p, _ = _net(tmp_path, gz=False)
    with pytest.raises(ValueError, match=match):
        G.kit_source_text(_type(p, bad), "t", tmp_path)


def test_missing_and_bad_contents(tmp_path):
    with pytest.raises(FileNotFoundError):
        G.kit_source_text(_type(tmp_path / "nope.v", "a" * 64), "t", tmp_path)
    p, sha = _net(tmp_path, NET.replace("module t__p(", "module other("))
    with pytest.raises(ValueError, match="exactly 1"):
        G.kit_source_text(_type(p, sha), "t", tmp_path)
    p, sha = _net(tmp_path, NET + "module t__p_native_w(clk); input clk; endmodule\n")
    with pytest.raises(ValueError, match="black boxes"):
        G.kit_source_text(_type(p, sha), "t", tmp_path)


def test_netlist_scope_resolves_module_named_instance(tmp_path):
    # the split netlist names each child instance after its module: a valid top-level path there, not in a wrapper
    p, sha = _net(tmp_path)
    t = _type(p, sha)
    assert BMP.unplaceable("t", t, G.kit_source_text(t, "t", tmp_path)[1]) == []
    assert BMP.unplaceable("t", t, "module t__p(); t__p_bound u_bound (); endmodule\n")


def _kit(tmp_path, verilog):
    kd = tmp_path / "kit"
    (kd / "rtl").mkdir(parents=True, exist_ok=True)
    (kd / "config.mk").write_text(f"export DESIGN_NAME = t__p\nexport VERILOG_FILES = {verilog}\n")
    return kd


def test_preflight_kit_source(tmp_path):
    kd = _kit(tmp_path, "/work/rtl/t__p__kit_source.v")
    (kd / "rtl" / "t__p__kit_source.v").write_text(NET)
    sha = hashlib.sha256(NET.encode()).hexdigest()
    (kd / "kit_source.json").write_text(json.dumps(dict(staged="/work/rtl/t__p__kit_source.v", sha256=sha)))
    assert KP.check(kd)["checks"]["kit_source"]["verdict"] == "PASS"
    (kd / "rtl" / "t__p__kit_source.v").write_text(NET + "\n")
    assert "!= pin" in KP.check(kd)["checks"]["kit_source"]["errors"][0]
    (kd / "rtl" / "t__p__kit_source.v").unlink()
    assert "not staged" in KP.check(kd)["checks"]["kit_source"]["errors"][0]


def test_preflight_unchanged_without_receipt(tmp_path):
    kd = _kit(tmp_path, "/work/rtl/a.v")
    (kd / "rtl" / "a.v").write_text("module t__p(); endmodule\n")
    assert "kit_source" not in KP.check(kd)["checks"]
