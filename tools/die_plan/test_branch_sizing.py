"""PATH-S81-PD10: branch_sizing (12.8 d1) slows the faster branch of an unequal H-tree split from plan geometry only."""
import math
import branch_sizing as BS


def _lib(r_ohm, cap, d0=10.0):
    sl = [5.0, 500.0]
    ld = [1.0, 2000.0]
    rows = [[d0 + 0.69 * r_ohm / 1000 * c for c in ld] for _ in sl]
    tr = [[5.0 + 2.2 * r_ohm / 1000 * c for c in ld] for _ in sl]
    return dict(delay=(sl, ld, rows), trans=(sl, ld, tr), cap=cap)


def _tree(short_um):
    # root node n0 -> two level-1 legs (each 2 reps) -> level-1 nodes -> one driver each
    cells, nets = {}, []
    cells["ckm_n0"] = dict(x=0.0, y=0.0)
    for side, L in (("0", 900.0), ("1", short_um)):
        sgn = -1 if side == "0" else 1
        prev = "ckm_n0"
        for k in (1, 2):
            c = f"ckm_r1_h{side}_{k}"
            cells[c] = dict(x=sgn * L * k / 3, y=0.0)
            nets.append(dict(drv=prev, loads=[c], level=1)) if prev != "ckm_n0" else None
            prev = c
        nd = f"ckm_n1_h{side}"
        cells[nd] = dict(x=sgn * L, y=0.0)
        nets.append(dict(drv=prev, loads=[nd], level=1))
        cells[f"ckm_d_{side}_0_0"] = dict(x=sgn * (L + 50), y=0.0)
        nets.append(dict(drv=nd, loads=[f"ckm_d_{side}_0_0"], level=11))
    nets.append(dict(drv="ckm_n0", loads=["ckm_r1_h0_1", "ckm_r1_h1_1"], level=0))
    return cells, nets


def test_faster_branch_downsized_and_spread_shrinks():
    libs = {m: _lib(300.0 * 24 / int(''.join(ch for ch in m.split('_')[0][4:] if ch.isdigit())), 0.5 * int(''.join(ch for ch in m.split('_')[0][4:] if ch.isdigit())))
            for m in BS.SIZES}
    widths = {m: 1.0 for m in BS.SIZES}
    cells, nets = _tree(600.0)
    rec = BS.size_branches(cells, nets, libs, 0.002, 0.18, BS.SIZES[0], 1.0, 0.27, widths, slew_max=1e9)
    assert rec["model_driver_input_spread_sized_ps"] < rec["model_driver_input_spread_full_ps"]
    sized = {c for c, v in cells.items() if v.get("lib")}
    assert sized and all("_h1" in c for c in sized), sized       # only the short (fast) branch is slowed
    assert all(cells[c]["lib"] in BS.SIZES[1:] for c in sized)


def test_equal_branches_untouched():
    libs = {m: _lib(300.0 * 24 / int(''.join(ch for ch in m.split('_')[0][4:] if ch.isdigit())), 0.5 * int(''.join(ch for ch in m.split('_')[0][4:] if ch.isdigit())))
            for m in BS.SIZES}
    cells, nets = _tree(900.0)
    rec = BS.size_branches(cells, nets, libs, 0.002, 0.18, BS.SIZES[0], 1.0, 0.27, {m: 1.0 for m in BS.SIZES})
    assert rec["cells_resized"] == 0 and math.isclose(rec["model_driver_input_spread_sized_ps"], 0.0, abs_tol=1e-6)
