import re
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import budget_clock as B


def standin(n=3):
    return "\n".join(["module leaf (clk, clk_t1, i, o);", "  input clk;", "  input clk_t1;",
                      "  input [2:0] i;", "  output [2:0] o;"] +
                     [f"  {B.FLOP} f{k} (.CLK(clk), .D(i[{k % 3}]), .QN(o[{k % 3}]));" for k in range(n)] +
                     ["endmodule", ""])


def test_clock_load_does_not_scale_with_budget_flop_count():
    for n in (3, 3000):
        text, census = B.convert(standin(n))
        assert census == dict(flops=n, clock_ports=2, used_clock_ports=1)
        assert len(re.findall(r"\.A\(clk\)", text)) == 1
        assert len(re.findall(r"\.CLK\(budget_ck_0\)", text)) == n
        assert ".CLK(clk)" not in text
        # The clock-only die model sees one fixed first-buffer load per port,
        # including unused ports, rather than thousands of bare DFF CLK pins.
        assert text.count(B.CELL) == 2


@pytest.mark.parametrize("change", [
    lambda s: s.replace("endmodule", "  BUFx2_ASAP7_75t_R real_logic (.A(i[0]), .Y(o[0]));\nendmodule"),
    lambda s: s.replace(".CLK(clk)", ".CLK(private_clock)"),
    lambda s: s.replace("input clk;", "input unrelated;"),
])
def test_non_budget_or_undeclared_clock_rejected(change):
    with pytest.raises(ValueError):
        B.convert(change(standin()))


def test_converter_never_replaces_routed_views_or_existing_artifacts(tmp_path):
    source = tmp_path / "source" / "leaf"
    source.mkdir(parents=True)
    (source / "6_final.v").write_text(standin())
    (source / "6_final.spef").write_text("physical evidence")
    dest = tmp_path / "out"
    with pytest.raises(ValueError, match="routed"):
        B.prepare(source.parent, dest, 250, 202.5)
    assert not dest.exists()
    (source / "6_final.spef").unlink()
    record = B.prepare(source.parent, dest, 250, 202.5)
    assert record["insertion_ps"] == dict(TT=250, FF=202.5)
    assert "capacitance : 3;" in (dest / "local_clock_TT.lib").read_text()
    assert 'cell_rise (scalar) { values ("250.0"); }' in (dest / "local_clock_TT.lib").read_text()
    assert 'cell_rise (scalar) { values ("202.5"); }' in (dest / "local_clock_FF.lib").read_text()
    with pytest.raises(ValueError, match="overwrite"):
        B.prepare(source.parent, dest, 250, 202.5)


def test_invalid_model_numbers_and_double_conversion_fail():
    for value in (-1, 0, float("inf"), float("nan")):
        with pytest.raises(ValueError):
            B.liberty(value)
    converted, _ = B.convert(standin())
    with pytest.raises(ValueError, match="already"):
        B.convert(converted)
