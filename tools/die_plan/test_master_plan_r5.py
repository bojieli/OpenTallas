"""MASTER-PLAN-R5: commensurate die H-tree lattice (nodes on channel crosses, pitch = core-array multiple)."""

import master_plan as MP  # noqa: E402


def _array(nx=12, ny=8, pw=100.0, ph=200.0, cw=80.0, chh=180.0, x0=50.0, y0=50.0):
    cores = []
    for i in range(nx):
        for j in range(ny):
            x, y = x0 + i * pw, y0 + j * ph
            cores.append((x, y, x + cw, y + chh, "p", f"c{i}_{j}", "tile"))
    return cores


def test_array_repeat_and_axis_on_channels():
    cores = _array()
    assert abs(MP.array_repeat(cores, 0) - 100.0) < 1e-6
    r = MP.commensurate_axis(cores, 0.0, 1300.0, 0, 4, 100.0, grid=1.0, margin=2.0)
    assert r and len(r["leaves_um"]) == 4
    # every node coordinate (root, level-1, leaves) is in a channel (between cores), not inside one
    vals = [r["root_um"]] + [r["root_um"] + s * r["arms_um"][0] for s in (-1, 1)] + r["leaves_um"]
    for v in vals:
        assert not any(c[0] < v < c[2] for c in cores), v
    # below the root (which may bridge an array break) arms are integer multiples of half the repeat
    # (leaf pitch = k x repeat), nested (no interleave)
    assert all(abs(m - round(m)) < 1e-6 for m in r["arm_multiples_of_half_repeat"][1:])
    assert all(l == 0 for l in r["bridge_arms"])
    assert r["arms_um"][0] > r["arms_um"][1]


def test_lattice_tree_axes_equal_paths_no_core_cells():
    cores = _array()
    rx = MP.commensurate_axis(cores, 0.0, 1300.0, 0, 4, 100.0, grid=1.0, margin=2.0)
    ry = MP.commensurate_axis(cores, 0.0, 1700.0, 1, 4, 200.0, grid=1.0, margin=2.0)
    parts = [("p", (0.0, 0.0, 1300.0, 1700.0))]
    gate, nodes = MP.lattice_tree([], [(0, 0), (1, 1)], parts, [c[:4] for c in cores], axes=(rx["leaves_um"],
                                                                                             ry["leaves_um"]),
                                  snap_um=0.5)
    assert gate["path_len_um"]["spread"] == 0.0
    assert gate["bindings"].get("in_core_conflict", 0) == 0
    assert gate["leg_repeaters_in_core"] == 0
    assert gate["verdict"] == "PASS"


def test_parse_tree_lattice_default_unchanged():
    assert MP.parse_tree_lattice("8x8") == (8, 8)
    assert MP.parse_tree_lattice("c4x4") == ("c", 4, 4)
    assert MP.parse_tree_lattice("commensurate:8x4") == ("c", 8, 4)
