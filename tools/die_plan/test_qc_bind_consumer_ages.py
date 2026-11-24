import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qc_bind_consumer_ages as ages


def write_bind(path, mutate=None):
    rows = []
    for side in "WE":
        for site in range(6):
            for lane in range(8):
                req = 28 if lane < 4 else 16
                resp = 27 if lane < 4 else {"W": 20, "E": 23}[side]
                for param in ("ML", "CROM_ML"):
                    rows.append(dict(inst=f"dvs_{side}{site}.u_core.u_sub.u_lrly{lane}",
                                     param=param, req=[req], resp=[resp], torn=False,
                                     design_loop=0, landed_loop=req + resp, required=req + resp))
    if mutate:
        mutate(rows)
    seam = dict(CS_TXS=7, CS_RXV=7, CS_RXP=7, CS_X3S=8, SC_TX=8, SC_X3=8)
    (path / "param_regen.json").write_text(json.dumps(
        {"record": {"D2D_TXDP_C": "32'h15011213", "D2D_SEAM_C": seam}}))
    (path / "bind_latency_consumers.json").write_text(json.dumps({"contracts": rows}))


def test_qc_consumer_receipt_uses_logical_port_order_and_per_lane_ages(tmp_path):
    write_bind(tmp_path, lambda rows: rows[1].update(req=[29], resp=[26]))
    report = ages.derive(tmp_path)
    assert report["d2d_txdp_port_order"] == [19, 18, 1, 21]
    assert report["su_mem_read_ages"]["W0"][0]["crom_request"] == 29
    west = report["su_mem_read_ages"]["W0"]
    east = report["su_mem_read_ages"]["E5"]
    assert [west[i]["memory_read_extra"] for i in range(8)] == [55] * 4 + [36] * 4
    assert [east[i]["memory_read_extra"] for i in range(8)] == [55] * 4 + [39] * 4


def test_reject_stale_or_mismatched_return_contract(tmp_path):
    write_bind(tmp_path, lambda rows: rows[1].update(resp=[26]))
    with pytest.raises(ValueError, match="ages disagree"):
        ages.derive(tmp_path)
    write_bind(tmp_path, lambda rows: rows.pop(1))
    with pytest.raises(ValueError, match="missing ML or CROM_ML record"):
        ages.derive(tmp_path)

def test_native_beat_requires_same_bits_and_same_arrival():
    sinks = {"dst[4]": ("src[0]", 13), "dst[5]": ("src[1]", 13)}
    assert ages.common_bit_age(sinks, "dst", "src", 2, sink_offset=4) == 13
    sinks["dst[5]"] = ("src[1]", 14)
    with pytest.raises(ValueError, match="unequal bit arrivals"):
        ages.common_bit_age(sinks, "dst", "src", 2, sink_offset=4)
    sinks["dst[5]"] = ("src[2]", 13)
    with pytest.raises(ValueError, match=r"expected src\[1\]"):
        ages.common_bit_age(sinks, "dst", "src", 2, sink_offset=4)
