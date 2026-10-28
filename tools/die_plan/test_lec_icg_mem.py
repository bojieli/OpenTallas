"""LEC-FPREG-7 10-27 (S81 dsfd_cfifo_crs4, 72 replicas: legacy LEC UNPROVEN 'icg gold: ... u_cg.u_icg GCLK reaches
$mem_v2 ... bank.WR_CLK'): icg_to_enable models a rising-edge clocked $mem_v2 port on a gated clock as the same port
on the root clock with its write / read enables ANDed with ENA | SE (the flop rule).  Refused, never approximated:
falling-edge or unclocked write port on GCLK, a clocked read port with a reset, a second write port on another clock.
    python3 -m pytest -q tools/die_plan/test_lec_icg_mem.py"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec  # noqa: E402

CLK, EN, WE, WA, WD, Q, GCLK, WE2 = 2, 3, 4, 5, 6, 7, 10, 11


def _design(tmp_path, wr_pol="1", wr_ce="1", rd_ce="0", rd_srst="0", two_wr=False, rd_on_gclk=False):
    ports = {"clk": ("input", [CLK]), "en": ("input", [EN]), "we": ("input", [WE]), "wa": ("input", [WA]),
             "wd": ("input", [WD]), "we2": ("input", [WE2]), "q": ("output", [Q])}
    nwr = 2 if two_wr else 1
    mem = {"type": "$mem_v2", "parameters": {
        "WIDTH": "00000000000000000000000000000001", "SIZE": "00000000000000000000000000000010",
        "ABITS": "00000000000000000000000000000001", "WR_PORTS": format(nwr, "032b"), "RD_PORTS": format(1, "032b"),
        "WR_CLK_ENABLE": wr_ce * nwr, "WR_CLK_POLARITY": "1" * (nwr - 1) + wr_pol,
        "RD_CLK_ENABLE": rd_ce, "RD_CLK_POLARITY": "1"},
        "port_directions": {"WR_CLK": "input", "WR_EN": "input", "WR_ADDR": "input", "WR_DATA": "input",
                            "RD_CLK": "input", "RD_EN": "input", "RD_ADDR": "input", "RD_DATA": "output",
                            "RD_SRST": "input", "RD_ARST": "input"},
        "connections": {"WR_CLK": [GCLK] + ([CLK] if two_wr else []), "WR_EN": [WE] + ([WE2] if two_wr else []),
                        "WR_ADDR": [WA] * nwr, "WR_DATA": [WD] * nwr, "RD_CLK": [GCLK if rd_on_gclk else CLK],
                        "RD_EN": [WE2], "RD_ADDR": [WA], "RD_DATA": [Q], "RD_SRST": [rd_srst], "RD_ARST": ["0"]}}
    icg = {"type": "ICGx1_ASAP7_75t_R", "parameters": {},
           "port_directions": {"CLK": "input", "ENA": "input", "SE": "input", "GCLK": "output"},
           "connections": {"CLK": [CLK], "ENA": [EN], "SE": ["0"], "GCLK": [GCLK]}}
    mod = {"attributes": {"top": "00000000000000000000000000000001"},
           "ports": {n: {"direction": d, "bits": b} for n, (d, b) in ports.items()},
           "cells": {"u_icg": icg, "bank": mem},
           "netnames": {n: {"bits": b} for n, (d, b) in ports.items()} | {"gclk": {"bits": [GCLK]}}}
    src = tmp_path / "in.json"
    src.write_text(json.dumps({"modules": {"top": mod}}))
    return src, tmp_path / "out.json"


def _mem(dst):
    return json.loads(Path(dst).read_text())["modules"]["top"]["cells"]


def test_gated_write_port_moves_to_root_clock_with_gated_enable(tmp_path):
    src, dst = _design(tmp_path)
    st = lec.icg_to_enable(src, dst, "gold")
    cells = _mem(dst)
    pc = cells["bank"]["connections"]
    assert pc["WR_CLK"] == [CLK] and "u_icg" not in cells and st["gated_mem_ports"] == 1
    a = [c for c in cells.values() if c["type"] == "$_AND_" and c["connections"]["Y"] == pc["WR_EN"]]
    assert len(a) == 1 and {a[0]["connections"]["A"][0], a[0]["connections"]["B"][0]} == {EN, WE}
    assert pc["RD_EN"] == [WE2] and pc["RD_CLK"] == [CLK]      # read port on the root clock: untouched


def test_gated_clocked_read_port_gets_gated_read_enable(tmp_path):
    src, dst = _design(tmp_path, rd_ce="1", rd_on_gclk=True)
    st = lec.icg_to_enable(src, dst, "gold")
    cells = _mem(dst)
    pc = cells["bank"]["connections"]
    a = [c for c in cells.values() if c["type"] == "$_AND_" and c["connections"]["Y"] == pc["RD_EN"]]
    assert pc["RD_CLK"] == [CLK] and len(a) == 1 and st["gated_mem_ports"] == 2
    assert {a[0]["connections"]["A"][0], a[0]["connections"]["B"][0]} == {EN, WE2}


@pytest.mark.parametrize("kw,why", [
    (dict(wr_pol="0"), "not rising-edge clocked"),
    (dict(wr_ce="0"), "not rising-edge clocked"),
    (dict(rd_ce="1", rd_on_gclk=True, rd_srst=WE), "with a reset"),
    (dict(two_wr=True), "different clocks"),
])
def test_uncovered_memory_ports_are_refused(tmp_path, kw, why):
    src, dst = _design(tmp_path, **kw)
    with pytest.raises(lec.Unproven, match=why):
        lec.icg_to_enable(src, dst, "gold")
