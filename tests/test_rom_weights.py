"""ROM-WEIGHTS-1119: released checkpoint bytes -> ROM via maps -> physical read-back against the checkpoint."""
from __future__ import annotations

import json
import random
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/mem_compiler"))

import rom_gen  # noqa: E402


def write_checkpoint(d: Path, tensors: dict[str, tuple[str, list[int], bytes]], shards: int = 2) -> None:
    """A minimal multi-shard safetensors snapshot (format: u64 header length, JSON header, raw data)."""
    d.mkdir(parents=True, exist_ok=True)
    names = sorted(tensors)
    weight_map = {}
    for s in range(shards):
        mine = names[s::shards]
        hdr, blob = {}, b""
        for n in mine:
            dtype, shape, data = tensors[n]
            hdr[n] = {"dtype": dtype, "shape": shape, "data_offsets": [len(blob), len(blob) + len(data)]}
            blob += data
        raw = json.dumps(hdr).encode()
        raw += b" " * (-len(raw) % 8)
        fn = f"model-{s + 1:05d}-of-{shards:05d}.safetensors"
        (d / fn).write_bytes(struct.pack("<Q", len(raw)) + raw + blob)
        weight_map.update({n: fn for n in mine})
    (d / "model.safetensors.index.json").write_text(json.dumps({"weight_map": weight_map}))


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    d = tmp_path_factory.mktemp("romw")
    spec = rom_gen.RomSpec("t_romw", 32, 72, 4)       # 64 payload bits (4 BF16 lanes) + 8 dead bits, like 4096x72
    rom_gen.compile_macro(spec, d)
    rnd = random.Random(11)
    tensors = {"a.bf16": ("BF16", [6, 40], bytes(rnd.getrandbits(8) for _ in range(6 * 40 * 2))),
               "b.i8": ("I8", [5, 24], bytes(rnd.getrandbits(8) for _ in range(5 * 24))),
               "c.f8": ("F8_E4M3", [3, 16], bytes(rnd.getrandbits(8) for _ in range(3 * 16)))}
    snap = d / "snap"
    write_checkpoint(snap, tensors)
    return d, spec, snap, tensors, d / "t_romw" / "t_romw.json"


def build(env, roms, name, **extra):
    d, spec, snap, _, sheet = env
    sp = d / f"{name}.spec.json"
    sp.write_text(json.dumps({"schema": rom_gen.WEIGHTS_SPEC_SCHEMA, "macro": str(sheet), "lane_bits": 16,
                              "roms": roms, **extra}))
    out = d / name
    return rom_gen.weights_build(sp, snap, out), out / "weights.manifest.json"


def test_rowmajor_bytes_unchanged_and_full_readback(env):
    d, spec, snap, tensors, sheet = env
    man, mp = build(env, [{"instances": ["u_a"], "segments": [{"tensor": "a.bf16", "row0": 1, "rows": 3, "col0": 8, "cols": 16}]}],
                    "plain")
    rows = [int(x, 16) for x in (mp.parent / man["instances"][0]["viamap"]).read_text().split()]
    words = rom_gen.read_back(spec, rows)
    # independent: the released bytes of rows 1..3, cols 8..23, BF16 little-endian, 4 per 64-bit word
    raw = tensors["a.bf16"][2]
    payload = b"".join(raw[(r * 40 + 8) * 2:(r * 40 + 24) * 2] for r in (1, 2, 3))
    want = [int.from_bytes(payload[i:i + 8], "little") for i in range(0, len(payload), 8)]
    assert words[:len(want)] == want and not any(words[len(want):])
    res = rom_gen.weights_verify(mp, snap, full=True, macro_sheet=sheet)
    assert res["verdict"] == "PASS" and res["words_checked"] == spec.words, res


def test_pingpong_skew_roworder_and_mixed_dtypes(env):
    d, spec, snap, tensors, sheet = env
    roms = [{"instances": ["u_p_0", "u_p_1"], "skew": 3, "skew_mod": 2,
             "segments": [{"tensor": "b.i8", "row0": 0, "rows": 5, "col0": 0, "cols": 24, "row_order": [4, 0, 3, 1, 2]},
                          {"tensor": "c.f8", "row0": 1, "rows": 2, "col0": 4, "cols": 8}]},
            {"instances": ["u_q"], "segments": [{"tensor": "a.bf16", "row0": 5, "rows": 1, "col0": 0, "cols": 40}]}]
    man, mp = build(env, roms, "pp")
    assert [r["instance"] for r in man["instances"]] == ["u_p_0", "u_p_1", "u_q"]
    # independent physical model: logical stream L, physical P[p][j] = L[(p - 3*(j%2)) % N][j], instance = p % 2
    b, c = tensors["b.i8"][2], tensors["c.f8"][2]
    stream = b"".join(b[r * 24:(r + 1) * 24] for r in (4, 0, 3, 1, 2)) + b"".join(c[r * 16 + 4:r * 16 + 12] for r in (1, 2))
    n = 2 * spec.words
    stream += bytes(n * 8 - len(stream))
    lane = lambda g, j: int.from_bytes(stream[g * 8 + 2 * j:g * 8 + 2 * j + 2], "little")
    for i, rec in enumerate(man["instances"][:2]):
        rows = [int(x, 16) for x in (mp.parent / rec["viamap"]).read_text().split()]
        got = rom_gen.read_back(spec, rows)
        for a in range(spec.words):
            p = 2 * a + i
            assert got[a] == sum(lane((p - 3 * (j % 2)) % n, j) << (16 * j) for j in range(4))
    assert rom_gen.weights_verify(mp, snap, full=True, macro_sheet=sheet)["verdict"] == "PASS"


def test_corrupt_via_and_changed_checkpoint_fail(env, tmp_path):
    d, spec, snap, tensors, sheet = env
    man, mp = build(env, [{"instances": ["u_c"], "segments": [{"tensor": "a.bf16", "row0": 0, "rows": 3, "col0": 0, "cols": 40}]}],
                    "corrupt")
    rec = man["instances"][0]
    vm = mp.parent / rec["viamap"]
    rows = [int(x, 16) for x in vm.read_text().split()]
    a, bit = 17, 5                                      # one wrong via of a payload bit
    r, s = divmod(a, spec.mux)
    rows[r] ^= 1 << (bit * spec.mux + s)
    digits = (spec.cols + 3) // 4
    text = "".join(f"{x:0{digits}x}\n" for x in rows)
    vm.write_text(text)
    rec["viamap_sha256"] = rom_gen.hashlib.sha256(text.encode()).hexdigest()   # a re-hashed (consistent) wrong mask
    mp.write_text(json.dumps(man))
    res = rom_gen.weights_verify(mp, snap, full=True, macro_sheet=sheet)
    assert res["verdict"] == "FAIL" and any("addr 17" in e for e in res["errors"]), res
    # a different checkpoint (one byte of the tensor changed) fails the read-back too
    t2 = dict(tensors)
    raw = bytearray(tensors["a.bf16"][2]); raw[0] ^= 1
    t2["a.bf16"] = ("BF16", [6, 40], bytes(raw))
    write_checkpoint(tmp_path / "snap2", t2)
    man2, mp2 = build(env, [{"instances": ["u_d"], "segments": [{"tensor": "a.bf16", "row0": 0, "rows": 3, "col0": 0, "cols": 40}]}],
                      "orig")
    res2 = rom_gen.weights_verify(mp2, tmp_path / "snap2", full=True, macro_sheet=sheet)
    assert res2["verdict"] == "FAIL"


def test_deterministic_and_bounds(env):
    roms = [{"instances": ["u_x"], "segments": [{"tensor": "b.i8", "row0": 0, "rows": 5, "col0": 0, "cols": 24}]}]
    m1, _ = build(env, roms, "det1")
    m2, _ = build(env, roms, "det2")
    assert m1["viamap_set_sha256"] == m2["viamap_set_sha256"] and m1["content_signature"] == m2["content_signature"]
    too_big = [{"instances": ["u_y"], "segments": [{"tensor": "a.bf16", "row0": 0, "rows": 6, "col0": 0, "cols": 40},
                                                   {"tensor": "a.bf16", "row0": 0, "rows": 6, "col0": 0, "cols": 40}]}]
    with pytest.raises(ValueError, match="exceed"):
        build(env, too_big, "big")
    with pytest.raises(ValueError, match="outside"):
        build(env, [{"instances": ["u_z"], "segments": [{"tensor": "a.bf16", "row0": 5, "rows": 2, "col0": 0, "cols": 4}]}], "oob")
    with pytest.raises(ValueError, match="pin"):
        build(env, roms, "pin", checkpoint={"index_sha256": "0" * 64})


def test_zero_rows_inside_a_permuted_block(env):
    d, spec, snap, tensors, sheet = env
    order = [2, None, 0, None, 1]                       # e.g. a partly valid bundle in the element's row order
    man, mp = build(env, [{"instances": ["u_z0", "u_z1"], "skew": 1, "skew_mod": 4,
                           "segments": [{"tensor": "b.i8", "row0": 2, "rows": 3, "col0": 0, "cols": 24, "row_order": order}]}],
                    "zrows")
    b = tensors["b.i8"][2]
    stream = b"".join(bytes(24) if r is None else b[(2 + r) * 24:(3 + r) * 24] for r in order)
    n = 2 * spec.words
    stream += bytes(n * 8 - len(stream))
    for i, rec in enumerate(man["instances"]):
        got = rom_gen.read_back(spec, [int(x, 16) for x in (mp.parent / rec["viamap"]).read_text().split()])
        for a in range(spec.words):
            p = 2 * a + i
            assert got[a] == sum(int.from_bytes(stream[((p - (j % 4)) % n) * 8 + 2 * j:((p - (j % 4)) % n) * 8 + 2 * j + 2],
                                                "little") << (16 * j) for j in range(4))
    assert rom_gen.weights_verify(mp, snap, full=True, macro_sheet=sheet)["verdict"] == "PASS"
    with pytest.raises(ValueError, match="exactly once"):
        build(env, [{"instances": ["u_bad"], "segments": [{"tensor": "b.i8", "row0": 0, "rows": 2, "col0": 0, "cols": 24,
                                                          "row_order": [0, 0]}]}], "badorder")


def test_s81hd_spec_rows_order_and_names(tmp_path):
    import rom_weight_specs as ws
    rm = {"schema": "opentallas.s81.head-row-map.v1", "vocabulary": 129280, "rows_per_bundle": 128,
          "ranks": [{"rank": 3, "slots": [{"part": "tW0o0", "slot": 0, "weight_row0": 129152, "weight_rows": 128},
                                          {"part": "tW0o1", "slot": 1, "weight_row0": 1000, "weight_rows": 70},
                                          {"part": "tE5b0", "slot": 2, "weight_row0": None, "weight_rows": 0}]}]}
    p = tmp_path / "row_map.json"
    p.write_text(json.dumps(rm))
    spec = ws.s81hd_spec(p, 3)
    roms = spec["roms"]
    assert len(roms) == 15 and spec["macro"] == "ot_rom_4096x274_m8" and spec["payload_bits"] == 256
    assert roms[0]["instances"] == ["hd_r3_tW0o0_a0_0", "hd_r3_tW0o0_a0_1"] and roms[4]["instances"][0] == "hd_r3_tW0o0_b_0"
    assert all(r["skew"] == 11 for r in roms)
    # partly valid bundle: A0 32 rows, A1 32, A2 6, A3 none; B keeps the k-major 32q+k order with zero rows past 70
    a = [r["segments"] for r in roms[5:9]]
    assert [s[0]["rows"] if s else 0 for s in a] == [32, 32, 6, 0] and a[2][0]["row0"] == 1064
    order = roms[9]["segments"][0]["row_order"]
    assert len(order) == 128 and order[:8] == [0, 32, 64, None, 1, 33, 65, None]
    assert order.count(None) == 58 and sorted(r for r in order if r is not None) == list(range(70))
    assert all(not r["segments"] for r in roms[10:])                    # dark slot: all-zero ROMs
