"""The KV ingest reference (tools/kv_ingest_ref.py): V4.1 wire records against the golden's quantisers
and the Codex row profiles (runtime/prefill), and the placement against runtime/prefill/v41_hbm_placement."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

import hdc_golden as G  # noqa: E402
import hdc_golden_v41 as G4  # noqa: E402
import kv_ingest_ref as R  # noqa: E402


def _vectors(n, width, seed, lo=-12, hi=12):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        x = (rng.standard_normal(width) * np.exp2(rng.integers(lo, hi))).astype(np.float32)
        if i % 5 == 0:
            x[::7] = 0.0
            x[1::11] = -0.0
        out.append(x)
    return out


def test_fp8_code_roundtrip_on_the_golden_grid():
    rng = np.random.default_rng(1)
    x = (rng.standard_normal(20000) * 10.0 ** rng.integers(-4, 3, 20000)).astype(np.float32)
    x[:6] = [0.0, -0.0, 448.0, 480.0, 2 ** -10, 1e9]
    f = G.to_fp8(x)
    assert np.array_equal(R.fp8_value(R.fp8_code(f)), f)


def test_index_key_record_is_lossless():
    for x in _vectors(60, 128, 2):
        assert np.array_equal(G.bits(R.decode_ikey(R.encode_ikey(x))), G.bits(G4.qdq_fp4_e8m0(x)))


def test_window_record_is_lossless():
    for x in _vectors(30, 512, 3):
        assert np.array_equal(G.bits(R.decode_window(R.encode_window(x))), G.bits(G4.qdq_fp8(x)))


def test_compressed_record_is_lossless():
    # the E4M3 group scale amax / 6 must be finite in E4M3 (|x| <= 2,688); the golden does not clamp it
    for x in _vectors(30, 512, 4, -12, 6):
        assert np.array_equal(G.bits(R.decode_ckv(R.encode_ckv(x))), G.bits(G4.qdq_fp4_e4m3(x)))


@pytest.mark.xfail(strict=True, reason="R-P5 (saturating E4M3 row scale, decided on branch worktree-agent-ab5912eff5bdb5981 @41259b66) is in tools/kv_ingest_ref.py on main but not in main's hdc_golden_v41.qdq_fp4_e4m3; strict so the gate flips when the golden adopts it")
def test_compressed_record_saturates_its_scale_above_2688():
    """R-P5: above |x| = 2,688 the E4M3 group scale saturates at 448 and the codes clamp at +-6."""
    for x in _vectors(20, 512, 6, 10, 16):
        assert np.max(np.abs(x)) > 2688
        rec = R.encode_ckv(x)
        assert np.array_equal(G.bits(R.decode_ckv(rec)), G.bits(G4.qdq_fp4_e4m3(x)))
        assert np.max(R.fp8_value(np.frombuffer(rec[256:], dtype=np.uint8))) <= 448


def test_records_parse_under_the_codex_profiles():
    """Our encoders emit the Codex row profiles' byte order, and the window / index products are exact in
    BF16, so the profiles' rational values equal the golden's BF16 values (the 'where do index / window
    products round' question has no rounding to decide)."""
    from runtime.prefill.v41_aux_kv_rows import parse_index_row, parse_window_row
    from runtime.prefill.v41_main_kv_row import parse_main_row
    for x in _vectors(10, 512, 5, -12, 6):
        w = parse_window_row(R.encode_window(x))
        assert np.array_equal(np.array([float(v) for v in w.exact_values], dtype=np.float32) + 0.0, G4.qdq_fp8(x) + 0.0)
        k = x[:128]
        ik = parse_index_row(R.encode_ikey(k))
        assert np.array_equal(np.array([float(v) for v in ik.exact_values], dtype=np.float32) + 0.0,
                              G4.qdq_fp4_e8m0(k) + 0.0)
        m = parse_main_row(R.encode_ckv(x))
        assert m.e2m1_codes == tuple(b for byte in R.encode_ckv(x)[:256] for b in (byte & 15, byte >> 4))


def test_main_row_placement_matches_the_codex_four_die_map():
    """ROWS mode (die g mod 4, stack (g / 4) mod 4, dense local rows at a 9-sector pitch) lands every main
    row at the Codex placement's address when the descriptor carries that region's base."""
    from runtime.prefill.v41_hbm_placement import Placement
    pl = Placement(max_context=4096)
    for r in range(0, 4096, 13):
        a = pl.compressed("main", 20, r)
        for die in range(4):
            sl = R.row_slot(r, 4, die, 4)
            assert (sl is not None) == (a.die == die)
            if sl is not None:
                stack, local = sl
                assert stack == a.stack
                assert a.byte == pl.regions[(die, stack, "main", 20)].base + local * 9 * R.SECTOR


def test_index_key_image_matches_streamer_superblock_boundaries():
    """The index streamer reads 17 consecutive 4-KB blocks per 1,024 local keys.

    Exercise both code-block and super-block transitions after the four-die,
    four-stack interleave. A linear 96-byte row map cannot pass this check.
    """
    image = np.zeros(2 * 17 * 4096, dtype=np.uint8)
    for local in (0, 63, 64, 1023, 1024):
        global_row = (local // 16) * 16 * 4 * 4 + local % 16
        assert R.row_slot(global_row, 4, 0, 4) == (0, local)
        record = bytes([local % 251 + 1] * 64 + [local % 251 + 2] * 4)
        image = R.ikey_image(len(image) // R.SECTOR, [record], global_row,
                             base=0, stride=0, ndie=4, die=0, ns=4, init=image)
        superblock, key = divmod(local, 1024)
        block = superblock * 17 * 4096
        code = block + (1 + key // 64) * 4096 + (key % 64) * 64
        scale = block + key * 4
        assert image[code:code + 64].tobytes() == record[:64]
        assert image[scale:scale + 4].tobytes() == record[64:]


def test_full_context_index_placement_matches_ingest_and_streamer():
    """Physical addresses agree at 64-key and 1,024-key block boundaries."""
    from runtime.prefill.v41_hbm_placement import Placement
    placement = Placement()
    for local in (0, 63, 64, 1023, 1024, 32767, 65535):
        for die in range(4):
            for stack in range(4):
                global_row = (local // 16 * 16 + stack * 4 + die) * 16 + local % 16
                assert R.row_slot(global_row, 4, die, 4) == (stack, local)
                address = placement.compressed("index", 20, global_row)
                region = placement.regions[(die, stack, "index", 20)]
                superblock, key = divmod(local, 1024)
                block = region.base + superblock * 17 * 4096
                assert (address.die, address.stack) == (die, stack)
                assert address.byte == block + (1 + key // 64) * 4096 + key % 64 * 64
                assert address.scale_byte == block + key * 4
