"""Checkpoint-backed physical QE bank ownership, depth and inverse layout."""
import json
from pathlib import Path

import numpy as np
import pytest

from tools import v41_qe_local_tile_bank as B


def test_local_slot_one_read_port_and_depth():
    for name, nrows in (("wq_a", 320), ("exp110.w1", 576)):
        seen = set()
        beat_ports = {}
        for row in range(nrows):
            for block in range(160):
                loc = B.local_slot(name, row, block)
                key = (loc["macro_id"], loc["macro_row"], loc["half_lane"])
                assert key not in seen
                seen.add(key)
                beat_ports.setdefault(loc["qtile_beat"], set()).add(loc["physical_id"])
                assert loc["macro_row"] < B.DEPTH
        assert len(beat_ports) == nrows * 20
        assert all(len(ports) == (4 if name.startswith("exp") else 8)
                   for ports in beat_ports.values())


def test_real_checkpoint_tile_roundtrip_and_sparse_claim(tmp_path: Path):
    source_dir = Path("/tmp/codex_v41_fullshape_golden/images/ctx200000_L00_r0")
    if not (source_dir / "w.wq_a.bin").is_file():
        pytest.skip("source-pinned rank0 image unavailable")
    source = B.ROOT / "results/rtl/hdc_v41x_fullshape_200k_l0_rank0_image.json"
    result = B.pack_tile(source, source_dir, tmp_path)
    assert result["full_die_supported"] is False
    assert result["physical_macro_bytes_allocated"] == 4_489_216
    assert result["valid_macro_words"] == 97_280
    assert result["padded_macro_words"] == 33_792
    assert result["physical_bytes_read_per_two_ops"] == 4_515_520
    assert result["source_checkpoint_bytes"] == 3_206_720
    assert result["required_simultaneous_ports"] == {"fp8": 8, "fp4": 7}
    fp4_ports = result["qtile_skew_port_witnesses"]["exp110.w1"]
    assert fp4_ports["macro_row_conflicts"] == 0
    assert fp4_ports["macro_read_transactions"] == 80_640
    assert fp4_ports["ideal_synchronous_macro_reads"] == 46_080
    assert fp4_ports["physical_bytes_read"] == 2_761_920
    assert result["ecc_generated"] is False
    image = np.stack([np.fromfile(tmp_path / m["image_file"], np.uint8).reshape(B.DEPTH,B.FILE_BYTES)
                      for m in result["macros"]])
    manifest = json.loads(source.read_text())
    sources = {name:B.Q.source_matrix(manifest,source_dir,name) for name in B.MATRICES}
    B.verify_tile(image,sources)
    fp4 = B.local_slot("exp110.w1", 0, 1)
    assert image[fp4["macro_id"],fp4["macro_row"],17:33].tolist() == \
           sources["exp110.w1"][0][0,16:32].tolist()
    damaged = image.copy()
    damaged[fp4["macro_id"],fp4["macro_row"],17] ^= 1
    with pytest.raises(AssertionError,match="FP4 paired local tile readback"):
        B.verify_tile(damaged,sources)


def test_record_is_pinned_and_refuses_full_die():
    r=json.loads((B.ROOT/"results/rtl/v41x_qe_local_tile_bank_l0.json").read_text())
    assert r["tool_sha256"] == B.digest(Path(B.__file__))
    assert r["source_manifest_sha256"] == B.digest(B.ROOT/r["source_manifest"])
    assert r["logical_stream_manifest_sha256"] == B.digest(B.ROOT/r["logical_stream_manifest"])
    assert r["full_die_supported"] is False
    assert len(r["unsupported_full_die_reasons"]) >= 4
    assert len({m["physical_id"] for m in r["macros"]}) == B.MACROS
    assert all(m["read_ports"] == 1 and m["serves_clusters"] == [B.TILE] for m in r["macros"])
