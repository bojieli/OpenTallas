#!/usr/bin/env python3
"""LAYERBENCH-HBM: fast local checks of layer_images.py (no Verilator).

  PYTHONPATH=tools python3 tools/hbm_layer_vehicle/test_layer_images.py [--programme ds_rank0_program.json]
      [--boundary slice_sw/boundary.json] [--die die.v]
1. quarter command layout = the die's pgp_SW__command wiring (die.v slices) and su_top_compile.Prog encoders;
2. vop_golden reproduces su_arith_compile's independent golden for every baseline op (same seed, same immediates);
3. DS L0 end to end: emitted SU programmes drive only slice input ports, no placement conflict, RAW order kept,
   lower_columns' expected.mem == the merged quarter lines (column image round trip by the image compiler).
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "hbm_static"))
from hbm_layer_vehicle import layer_images as LI  # noqa: E402


def t_layout(die):
    pos, lo = {}, 0
    for k in ("red", "rf", "vmw", "vmr", "control"):
        pos[k] = (lo, lo + LI.Q_W[k] - 1)
        lo += LI.Q_W[k]
    assert lo == LI.SB_W
    if die and Path(die).exists():
        t = Path(die).read_text()
        want = {"control": ["2421", "680"], "red_cmd": ["73", "0"], "rf_rd_cmd": ["127", "74"]}
        for port, (hi, l) in want.items():
            assert re.search(rf"\.{port}\(pgp_SW__command\[{hi}:{l}\]\)", t), port
        assert re.search(r"\.vmr_cmd\(pgp_SW__command\[499:440\]\)", t) and pos["vmr"] == (440, 679)
        assert re.search(r"\.vmw_cmd\(pgp_SW__command\[205:128\]\)", t) and pos["vmw"] == (128, 439)
    import su_top_compile as STC
    P = STC.Prog(2)
    P.vmr_cmd(0, 0, 3, 0x1234, 11, 77)
    P.vmw_cmd(1, 0, 5, 0, 13, 99, 0x2345, 0xa5)
    Q = LI.QLine()
    Q.vmr(0, 3, 0x1234, 11, 77)
    Q.vmw(1, 5, 0, 13, 99, 0x2345, 0xa5)
    assert Q.f["vmr"][0] == P.vmr[0][0] and Q.f["vmw"][1] == P.vmw[1][0]
    print("layout OK")


def t_golden():
    import su_arith_compile as SAC
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([sys.executable, str(HERE.parent / "hbm_static/su_arith_compile.py"), d], check=True,
                       cwd=str(HERE.parent / "hbm_static"))
        seed = np.array([int(x, 16) for x in Path(d, "seed.mem").read_text().split()], np.uint32).view(np.float32)
        gold = np.array([int(x, 16) for x in Path(d, "gold.mem").read_text().split()], np.uint32)
    data = seed.reshape(512, 512)
    a, b, c, dd = (data[k * 64:(k + 1) * 64].ravel() for k in range(4))
    base = dict(a_rnd=0, a_relu=0, a_min=0, c_clip=0, m1=0, m2=0, qm=0, ad=0, e1=0, e2=0, rnd=0,
                imm1=0x3fa00000, imm2=0x3ec00000, imm3=0x3f400000)
    name = dict(cx_arnd="a_rnd", cx_arelu="a_relu", cx_amin="a_min", cx_cclip="c_clip", cp_m1="m1", cm_m1="m1",
                cm_m2="m2", cm_qm="qm", ca_ad="ad", cs_e1="e1", ce_e2="e2", co_rnd="rnd")
    for t, (op, mods) in enumerate(SAC.OPS):
        sut = dict(base, **{name[k]: v for k, v in mods.items()})
        got = LI.vop_golden(sut, dict(A=a, B=b, C=c, D=dd))
        # qm lane parity is per global lane (512 wide): rebuild per row
        if sut["qm"] in (3, 4):
            got = np.concatenate([LI.vop_golden(sut, dict(A=a[i * 512:(i + 1) * 512], B=b[i * 512:(i + 1) * 512],
                                                          C=c[i * 512:(i + 1) * 512], D=dd[i * 512:(i + 1) * 512]))
                                  for i in range(64)])
        want = gold[t * 32768:(t + 1) * 32768]
        assert np.array_equal(got, want), (op, int((got != want).sum()))
    print(f"golden OK ({len(SAC.OPS)} ops)")


def t_layer(programme, boundary):
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([sys.executable, "-m", "hbm_layer_vehicle.layer_images", "--design", "ds", "--layer", "0",
                        "--programme", str(programme), "--boundary", str(boundary), "--out", d], check=True,
                       env={"PYTHONPATH": str(HERE.parent), "PATH": "/usr/bin:/bin"})
        m = json.loads(Path(d, "manifest.json").read_text())
        rep = json.loads(Path(d, "replay.json").read_text())
        bnd = json.loads(Path(boundary).read_text())
        ins = {e["name"] for e in bnd["inputs"]}
        assert {e["port"] for e in rep["events"] if e["k"] == "D"} <= ins
        assert not m["placement_conflicts"]
        em = [r for r in m["records"] if r["status"] == "emitted"]
        assert len(em) >= 8, len(em)
        assert all(not any("raw_hazard" in x for x in r.get("reasons", [])) for r in em)
        for k, p in enumerate(m["su_programmes"]):
            exp = Path(d, "images", f"su_prog{k:02d}", "cols", "expected.mem").read_text().split()
            src = Path(d, "images", f"su_prog{k:02d}", "quarter.mem").read_text().split()
            assert exp == src and len(src) == p["edges"] <= LI.EDGES_MAX
        chk = sum(1 for e in rep["events"] if e["k"] == "C")
        print(f"layer OK: {len(em)} SU records emitted in {len(m['su_programmes'])} programmes, {chk} VM checks, "
              f"counts {m['counts']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--programme", default=str(LI.DS_PROGRAMME))
    ap.add_argument("--boundary", default="/home/ubuntu/scratch/layerbench-hbm/slice_sw/boundary.json")
    ap.add_argument("--die", default="/home/ubuntu/scratch/hd4g-gen2/full_smoke/pb/die.v")
    a = ap.parse_args()
    t_layout(a.die)
    t_golden()
    if Path(a.programme).exists() and Path(a.boundary).exists():
        t_layer(a.programme, a.boundary)
    else:
        print("layer test SKIPPED (programme / boundary not present)")
    print("TEST_LAYER_IMAGES PASS")


if __name__ == "__main__":
    main()
