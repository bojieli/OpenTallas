"""The full-shape shard gate must refuse partial or numerically close results."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools.v41_fullshape_shard_compare import _digest, compare_chain, compare_layer, validate_golden_chain


def _pair(directory: Path, context: int, layer: int, arrays: dict, meta: dict):
    stem = f"ctx{context}_L{layer:02d}"
    np.savez(directory / f"{stem}.npz", **arrays)
    (directory / f"{stem}.json").write_text(json.dumps(meta))


def _fixture(tmp_path: Path):
    gd, rd, src = (tmp_path / name for name in ("golden", "rtl", "source"))
    for d in (gd, rd, src):
        d.mkdir()
    (src / "core.sv").write_text("source pin")
    pin = hashlib.sha256((src / "core.sv").read_bytes()).hexdigest()
    for layer in (0, 1):
        h = np.arange(8, dtype=np.float32).reshape(2, 4) + layer
        o = h + 1
        arrays = {"h_in": h, "pre_in": np.zeros(2, dtype=np.float32),
                  "h_out": o, "pre_out": np.zeros(2, dtype=np.float32),
                  "win0": np.arange(16, dtype=np.uint8)}
        gm = {"context": 200000, "position": 199999, "layer": layer,
              "input_sha256": _digest(h, arrays["pre_in"]),
              "output_sha256": _digest(o, arrays["pre_out"])}
        rm = {"context": 200000, "position": 199999, "layer": layer, "cycles": 100 + layer,
              "golden_input_sha256": gm["input_sha256"], "source_sha256": {"core.sv": pin}}
        _pair(gd, 200000, layer, arrays, gm)
        _pair(rd, 200000, layer, arrays, rm)
    return gd, rd, src


def test_exact_chain_and_cycle_scope(tmp_path):
    gd, rd, src = _fixture(tmp_path)
    assert validate_golden_chain(gd, 200000, [0, 1], src)["status"] == "golden_valid"
    result = compare_chain(gd, rd, 200000, [0, 1], src)
    assert result["status"] == "bit_exact"
    assert result["rtl_cycles_sum"] == 201
    assert "head excluded" in result["cycle_scope"] or "head" in result["cycle_scope"]


def test_signed_zero_bit_flip_fails(tmp_path):
    gd, rd, src = _fixture(tmp_path)
    stem = rd / "ctx200000_L00"
    with np.load(stem.with_suffix(".npz")) as z:
        arrays = {key: z[key].copy() for key in z.files}
    arrays["pre_out"][0] = np.float32(-0.0)
    np.savez(stem.with_suffix(".npz"), **arrays)
    with pytest.raises(ValueError, match="pre_out: bit mismatch"):
        compare_layer(gd, rd, 200000, 0, src)


def test_missing_state_or_stale_source_fails(tmp_path):
    gd, rd, src = _fixture(tmp_path)
    stem = rd / "ctx200000_L00"
    with np.load(stem.with_suffix(".npz")) as z:
        arrays = {key: z[key].copy() for key in z.files if key != "win0"}
    np.savez(stem.with_suffix(".npz"), **arrays)
    with pytest.raises(ValueError, match="omitted golden arrays"):
        compare_layer(gd, rd, 200000, 0, src)
    arrays["win0"] = np.arange(16, dtype=np.uint8)
    np.savez(stem.with_suffix(".npz"), **arrays)
    (src / "core.sv").write_text("changed")
    with pytest.raises(ValueError, match="source pin stale"):
        compare_layer(gd, rd, 200000, 0, src)


def test_missing_cycle_and_broken_chain_fail(tmp_path):
    gd, rd, src = _fixture(tmp_path)
    meta_path = rd / "ctx200000_L00.json"
    meta = json.loads(meta_path.read_text())
    meta["cycles"] = 0
    meta_path.write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="positive integer"):
        compare_layer(gd, rd, 200000, 0, src)
    meta["cycles"] = 100
    meta_path.write_text(json.dumps(meta))
    gpath = gd / "ctx200000_L01.json"
    g = json.loads(gpath.read_text())
    g["input_sha256"] = "0" * 64
    gpath.write_text(json.dumps(g))
    with pytest.raises(ValueError, match="golden input digest"):
        compare_chain(gd, rd, 200000, [0, 1], src)


def test_individually_exact_shards_with_broken_layer_chain_fail(tmp_path):
    gd, rd, src = _fixture(tmp_path)
    for directory in (gd, rd):
        stem = directory / "ctx200000_L01"
        with np.load(stem.with_suffix(".npz")) as z:
            arrays = {key: z[key].copy() for key in z.files}
        arrays["h_in"][0, 0] += np.float32(1)
        np.savez(stem.with_suffix(".npz"), **arrays)
    gm_path = gd / "ctx200000_L01.json"
    gm = json.loads(gm_path.read_text())
    with np.load(gd / "ctx200000_L01.npz") as z:
        gm["input_sha256"] = _digest(z["h_in"], z["pre_in"])
    gm_path.write_text(json.dumps(gm))
    rm_path = rd / "ctx200000_L01.json"
    rm = json.loads(rm_path.read_text())
    rm["golden_input_sha256"] = gm["input_sha256"]
    rm_path.write_text(json.dumps(rm))
    assert compare_layer(gd, rd, 200000, 1, src)["status"] == "bit_exact"
    with pytest.raises(ValueError, match="preceding layer output"):
        compare_chain(gd, rd, 200000, [0, 1], src)
