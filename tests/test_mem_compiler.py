"""Tests of the ASAP7 SRAM / ROM compilers (tools/mem_compiler)."""
from __future__ import annotations

import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/mem_compiler"))

import asap7  # noqa: E402
import ecc  # noqa: E402
import rom_gen  # noqa: E402
import sram_gen  # noqa: E402

INDEX = ROOT / "physical/asap7_memory_macros/index.json"


def test_bitcells_are_the_measured_drc_clean_cells():
    cells = asap7.bitcells()
    assert cells["sram_6t"]["area_um2"] == pytest.approx(0.023328)
    assert cells["rom_via"]["area_um2"] == pytest.approx(0.005832)


def test_calibration_macro_reproduces_published_efficiency():
    sheet = sram_gen.compile_macro(sram_gen.SramSpec("cal", 2048, 128, 4))
    # the calibrated dimension makes the unsnapped core exactly 0.788; snapping costs < 1%
    core = sheet["area"]["core_width_um"] * sheet["area"]["core_height_um"]
    assert sheet["area"]["data_array_area_um2"] / core == pytest.approx(asap7.published_macro_efficiency(), rel=1e-9)
    assert abs(sheet["area"]["array_efficiency"] - asap7.published_macro_efficiency()) < 0.01


def test_committed_library_matches_generator(tmp_path):
    """Regenerating the library reproduces every committed view byte for byte."""
    committed = json.loads(INDEX.read_text())
    subprocess.run([sys.executable, str(ROOT / "tools/mem_compiler/build_library.py"), "--out", str(tmp_path)],
                   check=True, capture_output=True)
    fresh = json.loads((tmp_path / "index.json").read_text())
    assert set(fresh["macros"]) == set(committed["macros"])
    for name, entry in committed["macros"].items():
        assert fresh["macros"][name]["views"] == entry["views"], name


def test_rom_views_are_content_independent(tmp_path):
    spec = rom_gen.RomSpec("t_rom", 256, 72, 8)
    rom_gen.compile_macro(spec, tmp_path / "a")
    views = {p.name: p.read_bytes() for p in (tmp_path / "a/t_rom").iterdir() if p.suffix in (".lef", ".lib", ".v")}
    rng = random.Random(3)
    r1 = rom_gen.personalise_instance(spec, [rng.getrandbits(72) for _ in range(256)], "i1", tmp_path / "p")
    r2 = rom_gen.personalise_instance(spec, [rng.getrandbits(72) for _ in range(256)], "i2", tmp_path / "p")
    assert r1["viamap_sha256"] != r2["viamap_sha256"] and r1["signature_crc32"] != r2["signature_crc32"]
    rom_gen.compile_macro(spec, tmp_path / "b")
    for name, data in views.items():
        assert (tmp_path / "b/t_rom" / name).read_bytes() == data


def test_via_map_round_trip():
    spec = rom_gen.RomSpec("t", 64, 10, 4)
    rng = random.Random(1)
    words = [rng.getrandbits(10) for _ in range(64)]
    rows = rom_gen.via_map(spec, words)
    assert len(rows) == 16 and all(r < (1 << 40) for r in rows)
    assert rom_gen.read_back(spec, rows) == words


@pytest.mark.parametrize("k", [8, 64, 96, 256, 264])
def test_secded_corrects_every_single_and_flags_doubles(k):
    rng = random.Random(k)
    n = ecc.codeword_bits(k)
    for _ in range(20):
        d = rng.getrandbits(k)
        w = ecc.encode(d, k)
        assert ecc.decode(w, k) == (d, "ok")
        for i in range(n):
            assert ecc.decode(w ^ (1 << i), k) == (d, "corrected")
        i, j = rng.sample(range(n), 2)
        assert ecc.decode(w ^ (1 << i) ^ (1 << j), k)[1] == "uncorrectable"


def test_fast_signature_equals_bit_serial_crc():
    rng = random.Random(7)
    for width in (32, 72, 266):
        words = [rng.getrandbits(width) for _ in range(40)]
        assert ecc.signature_fast(words, width) == ecc.signature(words, width)


def test_single_via_defect_changes_signature():
    rng = random.Random(9)
    words = [rng.getrandbits(72) for _ in range(128)]
    base = ecc.signature_fast(words, 72)
    for _ in range(50):
        a, b = rng.randrange(128), rng.randrange(72)
        bad = list(words)
        bad[a] ^= 1 << b
        assert ecc.signature_fast(bad, 72) != base


def test_rom_macro_is_denser_than_sram_and_reported_against_the_model():
    idx = json.loads(INDEX.read_text())["macros"]
    rom = idx["ot_rom_8192x266_m8"]
    sram = idx["ot_sram_1rw_2048x128_m4"]
    assert rom["density_mb_per_mm2"] > 4 * sram["density_mb_per_mm2"]
    cmp_ = rom["analytical_model_comparison"]["N7"]
    assert cmp_["measured_asap7_rom_cell_to_sram_cell_ratio"] == pytest.approx(0.25)
    for key in ("density_ratio_macro_over_model", "bandwidth_ratio_macro_over_model"):
        assert cmp_[key] > 0


def test_corners_order_and_repair_pins():
    sheet = sram_gen.compile_macro(sram_gen.SramSpec("r", 256, 64, 4, spare_rows=2, spare_cols=2))
    t = sheet["timing"]
    assert t["ff"]["clk_to_q_ps"] < t["tt"]["clk_to_q_ps"] < t["ss"]["clk_to_q_ps"]
    names = [p.name for p in sram_gen.pins_for(sram_gen.SramSpec("r", 256, 64, 4, spare_rows=2, spare_cols=2))]
    assert {"rr_en", "rr_addr", "cr_en", "cr_sel"} <= set(names)


@pytest.mark.skipif(shutil.which("verilator") is None, reason="verilator not installed")
def test_behavioural_models_lint_clean():
    for name in json.loads(INDEX.read_text())["macros"]:
        v = ROOT / "physical/asap7_memory_macros" / name / f"{name}.v"
        for extra in ([], ["+define+OT_MEM_FAULTS"]):
            proc = subprocess.run(["verilator", "--lint-only", "-Wall", *extra, str(v)], capture_output=True, text=True)
            assert proc.returncode == 0, (name, proc.stderr[:2000])
