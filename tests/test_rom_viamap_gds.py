"""ROM via map -> GDS overlay -> die merge -> read back (tools/mem_compiler/rom_viamap_gds.py)."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/mem_compiler"))

import rom_gen  # noqa: E402
import rom_viamap_gds as vg  # noqa: E402


@pytest.fixture(scope="module")
def rom(tmp_path_factory):
    d = tmp_path_factory.mktemp("rom")
    spec = rom_gen.RomSpec("t_rom", 64, 16, 8)
    rom_gen.compile_macro(spec, d)
    sheet = d / "t_rom" / "t_rom.json"
    rnd = random.Random(7)
    recs = []
    for i, seed in enumerate((1, 2, 1)):          # instances 0 and 2 share one image
        words = [random.Random(seed * 1000 + a).getrandbits(16) for a in range(64)]
        recs.append(rom_gen.personalise_instance(spec, words, f"u_rom{i}", d / "vm"))
    man = d / "vm" / "p.personalisation.json"
    man.write_text(json.dumps({"macro": "t_rom", "instances": recs}))
    return d, sheet, man, spec


def die_gds(path: Path, dbu: float = 4000.0, top: str = "TOP") -> None:
    path.write_bytes(vg.lib_header(dbu, "die") + vg.rec(vg.BGNSTR, 2, vg.i2(*([1970, 1, 1, 0, 0, 0] * 2)))
                     + vg.rec(vg.STRNAME, 6, top.encode()) + vg.rec(vg.ENDSTR, 0) + vg.rec(vg.ENDLIB, 0))


def def_text(m, orients):
    comps = "\n".join(f"- u_rom{i} t_rom + PLACED ( {int(x * 2000)} {int(y * 2000)} ) {o} ;"
                      for i, (x, y, o) in enumerate(orients))
    return f"UNITS DISTANCE MICRONS 2000 ;\nCOMPONENTS {len(orients)} ;\n{comps}\nEND COMPONENTS\n"


ORIENTS = [(10.0, 20.0, "N"), (60.0, 20.0, "FS"), (10.0, 80.0, "FN")]


def merged(rom, tmp_path, orients=ORIENTS):
    d, sheet, man, _ = rom
    m = vg.Macro(sheet)
    die, df, out = tmp_path / "die.gds", tmp_path / "p.def", tmp_path / "out.gds"
    die_gds(die)
    df.write_text(def_text(m, orients))
    info = vg.merge(die, "TOP", df, m, man, d / "vm", out)
    return m, die, df, out, info


def test_overlay_readback_equals_hex(rom, tmp_path):
    d, sheet, _, spec = rom
    m = vg.Macro(sheet)
    g = tmp_path / "u.gds"
    vg.write_overlay(m, d / "vm" / "u_rom0.viamap.hex", g)
    rows = vg.readback_overlay(m, g)
    assert rows == vg.read_viamap(d / "vm" / "u_rom0.viamap.hex", m)
    # and the words the macro would read are the programmed words
    words = [random.Random(1000 + a).getrandbits(16) for a in range(64)]
    assert rom_gen.read_back(spec, rows)[:64] == words


def test_merge_dedups_images_and_verifies_all_orientations(rom, tmp_path):
    m, die, df, out, info = merged(rom, tmp_path)
    assert info["instances_merged"] == 3 and info["unique_images"] == 2
    res = vg.verify(out, "TOP", df, m, rom[2], rom[0] / "vm")
    assert res["verdict"] == "PASS" and res["instances_checked"] == 3


@pytest.mark.parametrize("orient", ["N", "S", "FN", "FS", "W", "E"])
def test_each_orientation(rom, tmp_path, orient):
    m, die, df, out, _ = merged(rom, tmp_path, [(5.0, 5.0, orient), (50.0, 5.0, orient), (5.0, 50.0, orient)])
    assert vg.verify(out, "TOP", df, m, rom[2], rom[0] / "vm")["verdict"] == "PASS"


def test_wrong_orientation_or_flipped_via_fails(rom, tmp_path):
    m, die, df, out, _ = merged(rom, tmp_path)
    # the same GDS judged against a DEF that says FN instead of N must not pass
    df2 = tmp_path / "wrong.def"
    df2.write_text(def_text(m, [(10.0, 20.0, "FN")] + ORIENTS[1:]))
    assert vg.verify(out, "TOP", df2, m, rom[2], rom[0] / "vm")["verdict"] == "FAIL"
    # one flipped via in the hex
    vm = rom[0] / "vm" / "u_rom1.viamap.hex"
    good = vm.read_text()
    try:
        rows = good.split()
        rows[3] = f"{int(rows[3], 16) ^ 1:0{len(rows[3])}x}"
        vm.write_text("\n".join(rows) + "\n")
        man = json.loads(rom[2].read_text())
        for r in man["instances"]:
            if r["instance"] == "u_rom1":
                import hashlib
                r["viamap_sha256"] = hashlib.sha256(vm.read_text().encode()).hexdigest()
        mp = tmp_path / "m2.json"
        mp.write_text(json.dumps(man))
        res = vg.verify(out, "TOP", df, m, mp, rom[0] / "vm")
        assert res["verdict"] == "FAIL" and "1 via" in res["failures"][0][1]
    finally:
        vm.write_text(good)


def test_merge_refuses_unmapped_instance_and_stale_hash(rom, tmp_path):
    d, sheet, man, _ = rom
    m = vg.Macro(sheet)
    die, df = tmp_path / "die.gds", tmp_path / "p.def"
    die_gds(die)
    df.write_text(def_text(m, ORIENTS + [(90.0, 90.0, "N")]))   # u_rom3 has no via map
    with pytest.raises(ValueError, match="no via map"):
        vg.merge(die, "TOP", df, m, man, d / "vm", tmp_path / "o.gds")
    bad = json.loads(man.read_text())
    bad["instances"][0]["viamap_sha256"] = "0" * 64
    mp = tmp_path / "bad.json"
    mp.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="SHA-256"):
        vg.merge(die, "TOP", df, m, mp, d / "vm", tmp_path / "o.gds")


def test_real8_roundtrip():
    for v in (0.00025, 1e-6 / 4000, 1.0, 0.0, 123.5):
        assert vg.real8_dec(vg.real8_enc(v)) == pytest.approx(v, rel=1e-12)


def test_klayout_reads_the_same_vias(rom, tmp_path):
    """Independent reader: KLayout (pip module) flattens the merged die and finds exactly the hex's vias."""
    db = pytest.importorskip("klayout.db")
    m, die, df, out, _ = merged(rom, tmp_path, [(10.0, 20.0, "N"), (60.0, 20.0, "N"), (10.0, 80.0, "N")])
    ly = db.Layout()
    ly.read(str(out))
    top = ly.cell("TOP")
    got = set()
    it = top.begin_shapes_rec(ly.layer(vg.V1_LAYER, vg.V1_DT))
    while not it.at_end():
        c = it.shape().bbox().transformed(it.trans()).center()
        got.add((round(c.x * ly.dbu, 3), round(c.y * ly.dbu, 3)))
        it.next()
    want = set()
    for i, (x, y, _o) in enumerate([(10.0, 20.0, 0), (60.0, 20.0, 0), (10.0, 80.0, 0)]):
        rows = vg.read_viamap(rom[0] / "vm" / f"u_rom{i}.viamap.hex", m)
        for r, c in vg.via_cells(rows):
            cx, cy = m.centre_um(r, c)
            want.add((round(x + cx, 3), round(y + cy, 3)))
    assert got == want and len(got) > 100
