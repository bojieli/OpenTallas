import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import hdc_v41_engram_shipped as ES  # noqa: E402
import hdc_v41_engram_rom_plan as RP  # noqa: E402
import rtl_hdc_v41_engram_gather_campaign as campaign  # noqa: E402


def test_shipped_tables_are_the_released_layout():
    t = ES.shipped_tables()
    rec = ES.check_against_released_layout(t)
    assert rec["primes_offsets_multipliers_equal"]
    assert [int(r) for r in t.primes.reshape(2, -1).sum(1)] == [384006168, 384016682]
    # the multipliers keep every 17-bit id's product below 2^64 (the RTL's exactness condition)
    assert int(t.multipliers.max()) * ((1 << ES.ID_W) - 1) < (1 << 64)


def test_generated_package_and_hash_unit_are_current():
    assert ES.emit_package() == ES.PKG.read_text()
    assert ES.emit_hash() == ES.HASH_OUT.read_text()


def test_generated_hash_differs_from_the_reduced_source_only_where_declared():
    red = ES.HASH_SRC.read_text()
    for a, b in ES._EDITS:
        red = red.replace(a, b)
    gen = ES.HASH_OUT.read_text()
    assert gen.split("\n", 1)[0] == red.split("\n", 1)[0]
    assert gen.endswith(red.split("\n", 1)[1])


def test_row_decode_matches_a_direct_ieee_reading():
    """The golden decode on every (code, scale byte): exact value rounded once to BF16."""
    codes = np.tile(np.arange(256), 256).reshape(256, 256)          # row = scale byte
    got = ES.decode_rows(codes, np.arange(256))
    for s in (0, 1, 6, 7, 8, 100, 127, 200, 254, 255):
        for c in (0x00, 0x80, 0x01, 0x07, 0x08, 0x7E, 0xFE, 0x7F, 0xFF, 0x3C):
            v = G.E4M3[c] * 2.0 ** (s - 127)
            f = np.array([v], dtype=np.float64).astype(np.float32)
            exp = int((G.bits(G.to_bf16(f))[0]) >> 16)
            assert int(got[s, c]) == exp, (s, c)


def test_row_content_is_deterministic():
    a = ES.row_bytes(1, 384006167)
    assert a == ES.row_bytes(1, 384006167) and len(a[0]) == 256 and 0 <= a[1] < 256
    assert ES.splitmix64(0) == 0xE220A8397B1DCDAF


def test_rom_plan_record_is_current():
    rec = json.loads(RP.OUT.read_text())
    assert rec == json.loads(json.dumps(RP.plan()))
    org = rec["organisation"]
    assert org["row_group_macros"] == 33 and org["gather_port"]["beats_per_row"] == 8
    assert org["bytes_read_per_token"] == 12672


def test_campaign_record_is_current_and_passes():
    rec = json.loads(campaign.OUT.read_text())
    assert rec["status"] == "pass"
    for name, mode in rec["modes"].items():
        assert mode["pass"] and mode["element_mismatches"] == 0, name
        assert mode["elements_compared"] == mode["tokens"] * 2 * 24 * 256, name
        assert mode["hash_errors"] == 0 and mode["hash_checked"] == mode["tokens"], name
    assert rec["tokens_by_stream"]["reduced_workload_prompt_and_gold"] > 0
    muts = rec["mutations"]
    assert muts and all(m["caught"] != bool(m.get("control")) for m in muts)
    for name, digest in rec["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
