"""kit_preflight._preprocess keeps code after `else/`endif on the same line (S81 seqhost dsdv_sh_lk names its host
instance as "`endif u_h (...)"; the old directive regex took u_h as a directive name and dropped it, so
kit_contract.macro_instances failed every u_h.host... macro path; KIT-WAVE-7 10-31)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_preflight as KP  # noqa: E402

SRC = """module m;
`ifdef A
    ta #(.P(1))
`elsif B
    tb #(.P(2))
`else
    tc #(.P(3))
`endif u_h (.x(y));
`ifdef A wire w0; `else wire w1; `endif
endmodule
"""


def test_endif_trailing_instance_name_kept():
    out = KP._preprocess(SRC, set())
    assert "tc #(.P(3))" in out and "u_h (.x(y))" in out and "ta" not in out and "tb" not in out, out
    assert "wire w1;" in out and "w0" not in out, out


def test_endif_trailing_instance_name_taken_branch():
    out = KP._preprocess(SRC, {"B"})
    assert "tb #(.P(2))" in out and "u_h (.x(y))" in out and "tc" not in out, out


def test_ifdef_and_define_names_still_consumed():
    out = KP._preprocess("`define Q\n`ifdef Q\nkeep\n`endif\n`ifndef Q\ndrop\n`endif\n", set())
    assert "keep" in out and "drop" not in out and "Q" not in out, out
