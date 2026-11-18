"""check.py --tap-sinks (KV-D23-PC 11-18): G0 tap load on measured sinks, kit split (nearest + cap within reach)."""
import json
from pathlib import Path
import schema
import taps
import check


class Rep:
    def __init__(self):
        self.errs, self.warns = [], []

    def err(self, cls, msg, **kw):
        self.errs.append(msg)

    def warn(self, cls, msg, **kw):
        self.warns.append(msg)


def plan(added, cap=100, radius=200.0):
    r = json.loads((Path(__file__).parent / "examples/tiny_plan.json").read_text())
    r["partition_types"]["src"]["clock"].update(tap_mode="grid+explicit", added_taps=added, tap_max_sinks=cap, tap_radius_um=radius)
    return schema.Plan(r)


def dump(tmp_path, pts, root="clk"):
    f = tmp_path / "sinks.txt"
    f.write_text("".join(f"{root} {x} {y} DFFHQNx1_ASAP7_75t_R u{i}\n" for i, (x, y) in enumerate(pts)) +
                 "clk_c0 10.0 10.0 MACRO u_core\nfclk_in_x[0] 10.0 10.0 DFFHQNx1_ASAP7_75t_R u_f\n")
    return f


def test_reader_keeps_only_clk_tap_roots(tmp_path):
    f = dump(tmp_path, [(1.0, 2.0), (3.0, 4.0)], root="clk_t3")
    assert check.read_measured_sinks(f) == [(1.0, 2.0, 1.0), (3.0, 4.0, 1.0)]


def test_reader_bins_json(tmp_path):
    f = tmp_path / "b.json"
    f.write_text(json.dumps({"bin_um": 10.8, "bins": [[5.4, 5.4, 7]]}))
    assert check.read_measured_sinks(f) == [(5.4, 5.4, 7.0)]


def test_overloaded_tap_is_an_error(tmp_path):
    P = plan([])
    x, y = taps.grid_explicit_sites(P, "src")[0][1:]
    R = Rep()
    out = check.check_tap_sink_measured(P, R, [f"src={dump(tmp_path, [(x, y)] * 150)}"], severity="error")
    assert out["src"]["sinks"] == 150
    if len(taps.grid_explicit_sites(P, "src")) == 1:
        assert out["src"]["over"] == 1 and R.errs and "[tapload]" in R.errs[0]


def test_added_tap_takes_the_overload(tmp_path):
    P0 = plan([])
    grid = taps.grid_explicit_sites(P0, "src")
    x, y = grid[0][1:]
    far = (x + 150.0, y) if x + 150.0 < P0.types["src"]["outline_um"][0] - 20 else (x - 150.0, y)
    pts = [(x, y)] * 90 + [far] * 90
    R0 = Rep()
    o0 = check.check_tap_sink_measured(P0, R0, [f"src={dump(tmp_path, pts)}"])
    P1 = plan([dict(name=f"clk_t{len(grid)}", xy=list(far))])
    R1 = Rep()
    o1 = check.check_tap_sink_measured(P1, R1, [f"src={dump(tmp_path, pts)}"])
    assert o1["src"]["taps"] == o0["src"]["taps"] + 1
    assert o1["src"]["over"] == 0 and not R1.errs and o1["src"]["max_load"] <= 100


def test_bad_spec_is_reported(tmp_path):
    R = Rep()
    check.check_tap_sink_measured(plan([]), R, ["nosuchtype=x"])
    assert R.errs and "bad --tap-sinks" in R.errs[0]
