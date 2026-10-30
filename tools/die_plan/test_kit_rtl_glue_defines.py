"""FLOW-KITFAIL-2 10-29: two shared kit-rtl gaps reported by S81-KITS-A.
(a) bind.py kit-rtl left the bind's native-glue helpers (OUT/rtl/native_glue/ot_bind_native_<h>.sv) out of kit_rtl.f
    -> kit_preflight module_closure FAIL on ot_s81sl_kv_leaf__t1..t5.
(b) gen.py phys --kit-rtl wrote VERILOG_DEFINES from the plan type only, not the as-built defines the bind elaborated
    with (kit_rtl.json "defines") -> LP lint `nxt_rw2' implicitly declared (exists only under OT_COLL_NATIVE32)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind  # noqa: E402
import gen_phys as GP  # noqa: E402

H = "0158c812471d0fb2954ece1b"


def _bind_out(tmp):
    out = tmp / "out"
    (out / "rtl" / "native_glue").mkdir(parents=True)
    (out / "rtl" / "native_glue" / f"ot_bind_native_{H}.sv").write_text(f"module ot_bind_native_{H}(input a, output y);\nassign y = a;\nendmodule\n")
    return out


def test_kit_rtl_appends_native_glue_the_kit_instantiates(tmp_path):
    out = _bind_out(tmp_path)
    bound = tmp_path / "bound.sv"
    bound.write_text(f"module b(input a, output y);\n    ot_bind_native_{H} g_x_1 (.a(a), .y(y));\nendmodule\n")
    fl, added = bind.kit_native_glue("t1", [bound], out)
    assert added == [f"ot_bind_native_{H}"]
    assert fl == [bound, (out / "rtl" / "native_glue" / f"ot_bind_native_{H}.sv").resolve()]
    # idempotent: a filelist that already carries the helper is unchanged
    assert bind.kit_native_glue("t1", fl, out) == (fl, [])


def test_kit_rtl_without_native_glue_is_unchanged_and_missing_helper_fails(tmp_path):
    out = _bind_out(tmp_path)
    plain = tmp_path / "plain.sv"
    plain.write_text("module p(input a, output y);\nassign y = a;\nendmodule\n")
    assert bind.kit_native_glue("t1", [plain], out) == ([plain], [])
    bad = tmp_path / "bad.sv"
    bad.write_text("module q; ot_bind_native_ffffffffffffffffffffffff g_1 (); endmodule\n")
    with pytest.raises(bind.BindError, match="native glue"):
        bind.kit_native_glue("t1", [bad], out)


def _kit(tmp, defines, src):
    kd = tmp / "kit"
    kd.mkdir()
    (kd / "kit_rtl.json").write_text(json.dumps({"defines": defines}))
    s = kd / "leaf.sv"
    s.write_text(src)
    return kd / "kit_rtl.f", [s]


def test_kit_rtl_defines_used_by_the_kit_sources_reach_verilog_defines(tmp_path):
    f, files = _kit(tmp_path, ["DSFD_PQ_STATIC_X2", "OT_COLL_NATIVE32", "OT_COLL_NATIVE32_OFF"],
                    "module m;\n`ifdef OT_COLL_NATIVE32\n wire nxt_rw2;\n`endif\nendmodule\n")
    kd = GP.kit_rtl_defines(f, files)
    assert kd == ["OT_COLL_NATIVE32"]
    assert GP.type_verilog_defines({"verilog_defines": ["A"]}, kd) == ["-DSYNTHESIS", "-DA", "-DOT_COLL_NATIVE32"]


def test_kit_rtl_defines_unused_or_absent_keep_old_defines(tmp_path):
    f, files = _kit(tmp_path, ["OT_COLL_NATIVE32"], "module m; wire a; endmodule\n")
    assert GP.kit_rtl_defines(f, files) == []
    assert GP.kit_rtl_defines(tmp_path / "none" / "kit_rtl.f", files) == []
    assert GP.type_verilog_defines({"verilog_defines": ["A"]}, []) == GP.type_verilog_defines({"verilog_defines": ["A"]})
