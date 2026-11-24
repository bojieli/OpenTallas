"""PIPE-SEATS (type_relay_sites.py --pipes): bind ot_dp_dly delay pipes get one even-hop seat per stage and bit"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent.parent


def _geom(path, bits=2, y0=100.0):
    rows = ["D\t0\t0\t500\t400"]
    cid, nets = 0, []

    def cell(name, x, y):
        nonlocal cid
        cid += 1
        rows.append(f"C\t{cid}\tS\tDFFHQNx1_ASAP7_75t_R\t{x - 0.5}\t{y - 0.1}\t{x + 0.5}\t{y + 0.1}\t{name}")
        return cid
    for b in range(bits):
        y = y0 + 50.0 * b
        chain = [cell(f"src{b}$_DFF_P_", 0.0, y)]
        for j, x in enumerate((20.0, 25.0)):
            chain.append(cell(f"u_bound.u_d3_u_c_x.r\\[{j}\\]\\[{b}\\]$_DFF_P_", x, y))
        chain.append(cell(f"u_bound.u_d3_u_c_x.q\\[{b}\\]$_DFF_P_", 30.0, y))
        chain.append(cell(f"dst{b}$_DFF_P_", 400.0, y))
        for a, c in zip(chain, chain[1:]):
            nets.append(f"N\tn{a}\ti{a}\ti{c}")
    Path(path).write_text("\n".join(rows + nets) + "\n")


def _run(tmp_path, *extra):
    geom, base, out, rep = (tmp_path / n for n in ("g.tsv", "p.json", "o.json", "r.json"))
    _geom(geom)
    base.write_text(json.dumps({"partition_types": {"t": {"relay_sites": {"keep": [1, 2]}}}}) + "\n")
    subprocess.run([sys.executable, str(HERE / "type_relay_sites.py"), str(SRC), str(geom), str(base), "t", str(out), str(rep),
                    "--macro-halo", "-1", *extra], check=True, capture_output=True, text=True)
    return json.loads(out.read_text())["partition_types"]["t"]["relay_sites"], json.loads(rep.read_text())


def test_pipes_get_even_stage_seats_per_bit(tmp_path):
    rs, rep = _run(tmp_path, "--pipes")
    assert rs["keep"] == [1, 2]
    for b, y in ((0, 100.0), (1, 150.0)):
        got = [rs[f"u_d3_u_c_x.r[0][{b}]"], rs[f"u_d3_u_c_x.r[1][{b}]"], rs[f"u_d3_u_c_x.q[{b}]"]]
        assert [p[0] for p in got] == [100.0, 200.0, 300.0] and all(p[1] == y for p in got)
    assert rep["by_kind"] == {"pipe": 6} and rep["hop"]["pipe"] == 100.0


def test_pipes_off_by_default(tmp_path):
    rs, rep = _run(tmp_path)
    assert list(rs) == ["keep"] and rep["relay_flops"] == 0
