"""HBM-MU-QUAD-3: opt-in schema support for the PATH-HBM R8-R13 internal_stations station-model keys
(top-level "station_model_keys": true).   python3 -m pytest -q tools/die_plan/test_station_model_keys.py"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())

BASE = {"conn": "u_a.q|u_b", "from_um": [10.0, 10.0], "to_um": [300.0, 20.0], "regs_um": [[150.0, 10.0]],
        "launch": "u_a.q", "capture": "u_b", "note": "test"}
# one station per R8-R13 key family, shapes as in the HBM planS2 / planU2 plans
MODEL = [
    dict(BASE, bits=142, bits_parallel=568, serial_k=4),                                   # R8 k-cycle exchange
    dict(BASE, bits=1235, bits_parallel=2470, serial_k=2, r9_segments=[0, 0], r11_cc_serial=True),
    dict(BASE, bits=14, r9_segments=[0, 1],
         r10={"face": "N", "fend": "from", "bus": "L0_o", "ivx": [0.0, 400.0], "ivy": [0.0, 800.0],
              "pin_frac": 1.0, "bcast": False}),
    dict(BASE, bits=1, bits_parallel=1, serial_k=3, r9_segments=[1, 1], r10_we_chain=True,
         r10={"face": "E", "fend": "to", "bus": "L13_i", "ivx": [0.0, 864.0], "ivy": [1.0, 7.0],
              "pin_frac": 0.95, "bcast": True}),
    dict(BASE, bits=21, r9_share=1.0, r13_face_affine=True, r13="mcast", r9_segments=[0, 0]),
]


def plan(stations, opt=True):
    p = copy.deepcopy(EX)
    if opt is not None:
        p["station_model_keys"] = opt
    p["partition_types"]["mid"]["internal_stations"] = copy.deepcopy(stations)
    return p


def test_plain_stations_valid_either_way():
    plain = [dict(BASE, bits=8)]
    assert schema.validate(plan(plain, opt=None)) == []
    assert schema.validate(plan(plain, opt=True)) == []


def test_default_rejects_model_keys():
    errs = schema.validate(plan(MODEL, opt=None))
    for k in ("serial_k", "bits_parallel", "r9_segments", "r11_cc_serial", "r10", "r10_we_chain", "r9_share",
              "r13_face_affine", "r13"):
        assert any(f"unknown key '{k}'" in e for e in errs), k
    assert schema.validate(plan(MODEL, opt=False)) == errs     # explicit false = default strict


def test_opt_in_accepts_model_keys():
    assert schema.validate(plan(MODEL)) == []


def test_opt_in_still_strict_on_types_and_unknown_keys():
    bad = [dict(BASE, bits=4, bits_parallel=8, serial_k=0),               # serial_k >= 1
           dict(BASE, bits=4, r9_segments=[0]),                           # two segments
           dict(BASE, bits=4, r9_segments=[0, "1"]),
           dict(BASE, bits=4, r13="other"),
           dict(BASE, bits=4, r11_cc_serial=1),
           dict(BASE, bits=4, r9_share=1.5),
           dict(BASE, bits=4, r10={"face": "X", "fend": "from", "bus": "b"}),
           dict(BASE, bits=4, r10={"face": "N", "fend": "from", "bus": "b", "extra": 1}),
           dict(BASE, bits=4, r99_new=True)]
    for st in bad:
        assert schema.validate(plan([st])), st
    assert any("serial_k: 0 < 1" in e for e in schema.validate(plan([bad[0]])))
    p = plan([dict(BASE, bits=4)]); p["station_model_keys"] = "yes"
    assert any("station_model_keys" in e for e in schema.validate(p))


def test_opt_in_consistency_serial_word():
    errs = schema.validate(plan([dict(BASE, bits=141, bits_parallel=568, serial_k=4)]))
    assert any("ceil(bits_parallel 568 / serial_k 4) = 142" in e for e in errs)
    assert any("ceil" in e for e in schema.validate(plan([dict(BASE, bits=143, bits_parallel=568, serial_k=4)])))
    assert schema.validate(plan([dict(BASE, bits=190, bits_parallel=568, serial_k=3)])) == []   # ceil(568/3)
    assert any("together" in e for e in schema.validate(plan([dict(BASE, bits=4, serial_k=2)])))
    assert any("together" in e for e in schema.validate(plan([dict(BASE, bits=4, bits_parallel=8)])))
