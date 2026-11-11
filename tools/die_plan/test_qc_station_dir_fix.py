"""qc_station_dir_fix: out-bus face->leaf chains are flipped (clones too); in buses, leaf-first and face-launched
entries stay; only those bytes move; idempotent."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qc_station_dir_fix as F


def _type():
    return {"outline_um": [1235.52, 2531.52],
            "buses": [{"name": "y_o00", "dir": "out", "face": "S"}, {"name": "x_i0", "dir": "in", "face": "S"},
                      {"name": "z_o1", "dir": "out", "face": "S"}, {"name": "w_o2", "dir": "out", "face": "S"}],
            "internal_stations": [
                {"conn": "bus:y_o00", "from_um": [138.92, 0.0], "to_um": [86.496, 1129.991],
                 "regs_um": [[43.2, 224.64], [43.2, 535.68], [43.2, 855.36]], "bits": 515,
                 "launch": "u_t00.n_y", "capture": "face flop"},
                {"conn": "bus:x_i0", "from_um": [100.0, 0.0], "to_um": [90.0, 1100.0],
                 "regs_um": [[50.0, 300.0], [50.0, 700.0]], "launch": "face", "capture": "u_t00.s_x"},
                {"conn": "bus:z_o1", "from_um": [90.0, 1100.0], "to_um": [100.0, 0.0],
                 "regs_um": [[50.0, 700.0], [50.0, 300.0]], "launch": "u_t00.n_z", "capture": "face flop"},
                {"conn": "bus:w_o2", "from_um": [100.0, 0.0], "to_um": [90.0, 1100.0],
                 "regs_um": [[50.0, 300.0], [50.0, 700.0]], "launch": "face bus w_o2", "capture": "u_t00.w"}]}


def _text():
    P = {"die": {"name": "qwen_compute"}, "partition_types": {"cbf_a": _type(), "cbf_b": _type(),
                                                             "other": {"outline_um": [1, 1]}}}
    return json.dumps(P, separators=(",", ":")) + "\n"


def test_flip_signature_only():
    text = _text()
    out, done, skipped = F.apply(text)
    assert [(d[0], d[2]) for d in done] == [("cbf_a", "bus:y_o00"), ("cbf_b", "bus:y_o00")] and not skipped
    q = json.loads(out)
    for tn in ("cbf_a", "cbf_b"):
        e = q["partition_types"][tn]["internal_stations"]
        assert e[0]["from_um"] == [86.496, 1129.991] and e[0]["to_um"] == [138.92, 0.0]
        assert e[0]["regs_um"] == [[43.2, 855.36], [43.2, 535.68], [43.2, 224.64]]
        assert e[1:] == _type()["internal_stations"][1:]
    assert all(max(d[5]) <= 405 for d in done) and [d[4] for d in done] == [list(reversed(d[5])) for d in done]
    assert len(out) == len(text) and out.endswith("\n")


def test_idempotent_and_filter():
    out, _, _ = F.apply(_text())
    out2, done2, _ = F.apply(out)
    assert out2 == out and done2 == []
    _, d, _ = F.apply(_text(), types={"cbf_b"})
    assert [x[0] for x in d] == ["cbf_b"]
