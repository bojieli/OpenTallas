"""S81-COL-ROWS 11-17: ordered station rows for a wide rank (ist_rows.py) and its opt-in wiring in kit_istations.py."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ist_rows as IR  # noqa: E402
from ft_bit_sites import validate_slot  # noqa: E402


def test_ir1_rank_is_117_ten_bit_groups_over_180_um_same_y():
    sites = IR.ordered_rows(1166, (757.0, 1226.88))                    # 1,166 payload + 1 epoch = 1,167 flops
    assert len(sites) == 1167
    xs = sorted({round(x, 3) for x, _ in sites})
    assert len(xs) == 117 and abs(xs[0] - (757.0 - 90)) < 1e-6 and abs(xs[-1] - (757.0 + 90)) < 1e-6
    ys = [y for _, y in sites]
    assert abs((min(ys) + max(ys)) / 2 - 1226.88) < 1e-6                 # centred on the planned y, no plan change
    assert max(ys) - min(ys) <= 10 * 0.27                                # ten rows high
    assert len(set(sites)) == 1167                                       # no two bits on one site


def test_bits_are_ordered_along_the_face():
    sites = IR.ordered_rows(300, (500.0, 100.0))
    gx = [sites[g * 10][0] for g in range(31)]
    assert gx == sorted(gx)                                              # group g left of group g+1
    for g in range(30):
        col = [sites[g * 10 + k] for k in range(10)]
        assert len({x for x, _ in col}) == 1 and [y for _, y in col] == sorted(y for _, y in col)


def test_no_two_cells_overlap():
    sites = IR.ordered_rows(1166, (0.0, 0.0))
    w, h = IR.CELL_UM
    cols = {}
    for x, y in sites:
        cols.setdefault(round(x, 6), []).append(y)
    xs = sorted(cols)
    assert all(b - a >= w - 1e-9 for a, b in zip(xs, xs[1:]))            # columns at least one cell apart
    for ys in cols.values():
        ys.sort()
        assert all(b - a >= h - 1e-9 for a, b in zip(ys, ys[1:]))         # rows at least one row apart


def test_e_w_face_runs_the_columns_along_y():
    sites = IR.ordered_rows(300, (50.0, 600.0), "y")
    gy = [sites[g * 10][1] for g in range(31)]
    assert gy == sorted(gy) and abs(sorted(gy)[0] - (600.0 - 90)) < 1e-6


def test_apply_only_when_opted_in_and_wide_and_collinear():
    e = {"conn": "in: frame_int_o0", "regs_um": [[1069.0, 1226.88], [757.0, 1226.88], [445.0, 1226.88]]}
    assert IR.apply_ordered_rows(e, 1166, {}) is e                       # default: unchanged object
    out = IR.apply_ordered_rows(e, 1166, {"OT_IST_ROWS": "1"})
    assert out is not e and len(out["bit_sites_um"]) == 3 and len(out["bit_sites_um"][0]) == 1167
    assert "bit_sites_um" not in e                                       # input entry not mutated
    validate_slot(dict(width=1166, stations=4, bit_sites_um=out["bit_sites_um"], bit_site_cell_um=out["bit_site_cell_um"]))
    assert IR.apply_ordered_rows(e, 200, {"OT_IST_ROWS": "1"}) is e      # narrow rank
    diag = {"regs_um": [[0, 0], [10, 10]]}
    assert IR.apply_ordered_rows(diag, 1166, {"OT_IST_ROWS": "1"}) is diag
    pre = dict(e, bit_route="per_bit")
    assert IR.apply_ordered_rows(pre, 1166, {"OT_IST_ROWS": "1"}) is pre


def test_kit_istations_calls_it_before_the_exact_bank_check():
    s = (HERE / "kit_istations.py").read_text()
    assert "import ist_rows as IR" in s
    assert s.index("e = IR.apply_ordered_rows(e, W)") < s.index("exact = exact_banks(e, W)")
