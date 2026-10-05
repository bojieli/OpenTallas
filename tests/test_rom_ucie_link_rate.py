"""ot_rom_ucie_link sustains its byte rate at a fractional cycles-per-record (the bucket keeps its remainder).

Before the fix the token bucket was capped at one record, so a link at 3.25 cycles per 512-B record refilled to the
cap in 4 cycles and dropped the quarter: it ran at 4 cycles per record, 19% under its rate.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LINK = ROOT / "rtl/rom/ot_rom_oneshot_allreduce.sv"
TB = ROOT / "rtl/test/tb_rom_ucie_link_rate.sv"


def run(tmp_path, lat, flit, num, den, cycles):
    if not shutil.which("iverilog"):
        pytest.skip("iverilog not installed")
    exe = tmp_path / "sim"
    subprocess.run(["iverilog", "-g2012", "-o", str(exe), "-s", "tb_rom_ucie_link_rate",
                    f"-Ptb_rom_ucie_link_rate.LAT={lat}", f"-Ptb_rom_ucie_link_rate.FLIT_BYTES={flit}",
                    f"-Ptb_rom_ucie_link_rate.BPC_NUM={num}", f"-Ptb_rom_ucie_link_rate.BPC_DEN={den}",
                    f"-Ptb_rom_ucie_link_rate.CYCLES={cycles}", str(LINK), str(TB)], check=True)
    out = subprocess.run(["vvp", "-n", str(exe)], capture_output=True, text=True, check=True).stdout
    m = re.search(r"RATE cycles=(\d+) sent=(\d+) recv=(\d+) bad=(\d+) lat=(-?\d+) cr_lat=(-?\d+)", out)
    assert m, out
    return dict(zip(("cycles", "sent", "recv", "bad", "lat", "cr_lat"), map(int, m.groups())))


@pytest.mark.parametrize("lat,flit,num,den", [
    (142, 512, 15758, 100),    # V4.1 T1 board link: 13 lanes x 13.18 GB/s at 1.087 GHz, 3.249 cycles per record
    (228, 512, 16971, 100),    # V4.1 T2 rack cable: 14 lanes, 3.017 cycles per record
    (11, 512, 8485, 100),      # 7 lanes: 6.034 cycles per record
    (12, 64, 20, 1),           # 3.2 cycles per 64-B record
    (12, 64, 3780, 1),         # UCIe in the package TP bench: many records per cycle, one accepted per cycle
])
def test_sustained_rate(tmp_path, lat, flit, num, den):
    cycles = 20000
    r = run(tmp_path, lat, flit, num, den, cycles)
    ideal = min(cycles, cycles * num / (flit * den))
    # a full bucket at reset may add one record; the rate itself must not lose the fractional remainder
    assert ideal - 1 <= r["sent"] <= ideal + 2, (r, ideal)
    assert r["recv"] == r["sent"] and r["bad"] == 0
    assert r["lat"] == lat and r["cr_lat"] == lat


def test_old_cap_would_round_up():
    """The defect this guards: a one-record cap turns 3.249 cycles per record into 4 (20000 / 4 = 5000 records, not 6155)."""
    num, den, flit = 15758, 100, 512
    cost, cap_old = flit * den, max(num, flit * den)
    tokens, sent = cap_old, 0
    for _ in range(20000):
        s = tokens >= cost
        sent += s
        tokens = min(cap_old, tokens - (cost if s else 0) + num)
    assert sent == 5000
