"""FABLE-DIE-QC-R 11-16: clock_spef.py writes the die clock tree as exact-length RC (no gcell snap), so two copies of one
region tree get the same parasitics wherever they sit."""
import json
import re
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).parent / "clock_spef.py"


def _kit(tmp, dx, dy, mirror):
    """root -> r1 -> b1 -> {r2 -> b2 -> port t_a (above), r3 (same row, other column)}; moved by (dx, dy), y-mirrored"""
    my = (lambda y: -y) if mirror else (lambda y: y)
    sites = {"r1": [0.0, 0.0], "b1": [100.0, 0.0], "r2": [100.0, 50.0], "b2": [160.0, 90.0], "r3": [30.0, 0.0]}
    sites = {k: [x + dx, my(y) + dy] for k, (x, y) in sites.items()}
    v = """module ctree (root, t_a);
  input root;
  output t_a;
  CKINVDCx16_ASAP7_75t_R r1 (.A(root), .Y(rn1));
  CKINVDCx16_ASAP7_75t_R b1 (.A(rn1), .Y(n1));
  CKINVDCx16_ASAP7_75t_R r2 (.A(n1), .Y(rn2));
  CKINVDCx16_ASAP7_75t_R r3 (.A(n1), .Y(rn3));
  CKINVDCx16_ASAP7_75t_R b2 (.A(rn2), .Y(n2));
  assign t_a = n2;
endmodule
"""
    tree = dict(sites=sites, taps=[dict(port="t_a", xy=[160.0 + dx, my(140.0) + dy])],
                nodes={"0": dict(parent=None, x=dx, y=dy)})
    (tmp / "c.v").write_text(v)
    (tmp / "t.json").write_text(json.dumps(tree))
    out = tmp / "o.spef"
    subprocess.run([sys.executable, "-I", str(TOOL), str(tmp / "c.v"), str(tmp / "t.json"), str(out)], check=True)
    return out.read_text()


def _nets(s):
    out = {}
    for m in re.finditer(r"\*D_NET (\S+) (\S+)\n(.*?)\*END", s, re.S):
        res = sorted(round(float(x.split()[3]), 6) for x in m.group(3).split("*RES\n")[1].strip().split("\n"))
        out[m.group(1)] = (round(float(m.group(2)), 4), res)
    return out


def test_lengths_layers_and_stacks(tmp_path):
    n = _nets(_kit(tmp_path, 0.0, 0.0, False))
    assert set(n) == {"ck_rn1", "ck_n1", "ck_rn2", "ck_n2"}          # rn3 has no sink; the root net is the ideal driver
    c8, c9 = 1.03962e-1, 9.28446e-2
    assert abs(n["ck_rn1"][0] - 100 * c8) < 1e-3                      # straight M8
    assert abs(n["ck_n1"][0] - (70 * c8 + 50 * c9)) < 1e-3            # trunk to the r3 column + M9 branch to r2
    assert abs(n["ck_rn2"][0] - (60 * c8 + 40 * c9)) < 1e-3
    assert abs(n["ck_n2"][0] - (50 * c9)) < 1e-3 or abs(n["ck_n2"][0] - 50 * c9) < 1e-3
    assert 0.0979 in n["ck_rn2"][1] and 0.0916 in n["ck_rn2"][1] and 0.0063 in n["ck_rn2"][1]


def test_copy_moved_off_the_gcell_grid_and_mirrored_is_identical(tmp_path):
    a = _nets(_kit(tmp_path, 0.0, 0.0, False))
    (tmp_path / "b").mkdir()
    b = _nets(_kit(tmp_path / "b", 2471.04 + 3.7, 513.33, True))
    assert set(a) == set(b)
    for k in a:
        assert abs(a[k][0] - b[k][0]) < 1e-3
        assert all(abs(p - q) < 1e-5 for p, q in zip(a[k][1], b[k][1]))
