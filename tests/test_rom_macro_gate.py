"""ROM-MACRO (owner 2026-10-25): ROM content is via-map data of a generated macro, never synthesised logic.

* tools/mem_compiler/rom_infer_gate.py fails a netlist that holds a read-only memory >= 1 kbit (proc_rom case table
  or an initialised read-only array), and passes RAMs and small decode functions;
* tools/mem_compiler/rom_gen.py verify is the per-content functional check: via maps against the weight image.
"""
import json
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "mem_compiler"))


import rom_gen  # noqa: E402
import rom_infer_gate as gate  # noqa: E402
MACRO = ROOT / "physical" / "asap7_memory_macros_v2" / "ot_rom_4096x72_m8" / "ot_rom_4096x72_m8.json"


def _b(n, w=32):
    return format(n, f"0{w}b")


def mem_cell(words, width, wr, init=False, memid="\\m"):
    p = {"SIZE": _b(words), "WIDTH": _b(width), "RD_PORTS": _b(1), "WR_PORTS": _b(wr), "MEMID": memid,
         "INIT": ("01" * (words * width // 2)) if init else "x" * 8}
    return {"type": "$mem_v2", "parameters": p, "attributes": {"src": "t.sv:1.1-2.2"}}


def design(**cells):
    return {"modules": {"top": {"cells": cells}}}


def test_content_table_fails_ram_and_decode_pass():
    d = design(w=mem_cell(1024, 64, 0, init=True), dec=mem_cell(16, 8, 0, memid="$auto$proc_rom"),
               ram=mem_cell(512, 128, 1), iram=mem_cell(64, 32, 1, init=True))
    res = gate.check_design(d)
    v = {r["cell"]: (r["kind"], r["verdict"]) for r in res["memories"]}
    assert v == {"w": ("ROM", "FAIL"), "dec": ("ROM", "INFO"), "ram": ("RAM", "OK"), "iram": ("RAM+INIT", "WARN")}
    assert res["verdict"] == "FAIL" and res["rom_bits_failed"] == 65536
    assert gate.check_design(design(ram=mem_cell(512, 128, 1)))["verdict"] == "PASS"
    assert gate.check_design(d, min_bits=1 << 20)["verdict"] == "PASS"     # threshold is explicit


def test_gate_cli_exit_code(tmp_path):
    bad, good = tmp_path / "bad.json", tmp_path / "good.json"
    bad.write_text(json.dumps(design(t=mem_cell(256, 61, 0))))
    good.write_text(json.dumps(design(t=mem_cell(256, 61, 1))))
    assert gate.main(["--mem-json", str(good)]) == 0
    assert gate.main(["--mem-json", str(good), str(bad), "--json", str(tmp_path / "r.json")]) == 1
    r = json.loads((tmp_path / "r.json").read_text())
    assert r[str(bad)]["verdict"] == "FAIL" and r[str(good)]["verdict"] == "PASS"


def _personalise(tmp_path, n_words=5000, seed=7):
    random.seed(seed)
    img = tmp_path / "w.hex"
    img.write_text("".join(f"{random.getrandbits(64):016x}\n" for _ in range(n_words)))
    spec = rom_gen.spec_from_sheet(MACRO)
    tiles = rom_gen.tile_image(rom_gen.read_hex(img), 64, spec, 64, "secded")
    out = tmp_path / "p"
    recs = [rom_gen.personalise_instance(spec, ws, f"w_r{r}_c{c}", out) for (r, c), ws in sorted(tiles.items())]
    man = {"macro": spec.name, "ecc": "secded", "image": str(img), "image_sha256": rom_gen.asap7.sha256_file(img),
           "data_bits": 64, "tile_data_bits": 64, "instances": recs, "content_signature": rom_gen.die_signature(recs)}
    mp = out / "w.personalisation.json"
    mp.write_text(json.dumps(man))
    return spec, img, mp


def test_verify_passes_the_content_and_catches_one_via(tmp_path):
    spec, img, mp = _personalise(tmp_path)
    res = rom_gen.verify_personalisation(mp)
    assert res["verdict"] == "PASS" and res["instances"] == 2 and res["words_checked"] == 2 * spec.words
    man = json.loads(mp.read_text())
    vm = mp.parent / man["instances"][0]["viamap"]
    rows = vm.read_text().split()
    rows[5] = format(int(rows[5], 16) ^ (1 << 9), f"0{len(rows[5])}x")       # one via flipped
    text = "".join(r + "\n" for r in rows)
    vm.write_text(text)
    assert "via map hash" in rom_gen.verify_personalisation(mp)["errors"][0]
    man["instances"][0]["viamap_sha256"] = rom_gen.hashlib.sha256(text.encode()).hexdigest()   # forged hash
    mp.write_text(json.dumps(man))
    errs = rom_gen.verify_personalisation(mp)["errors"]
    assert any("words differ" in e for e in errs) and any("BIST signature" in e for e in errs)


def test_verify_rejects_a_different_content_file(tmp_path):
    _, img, mp = _personalise(tmp_path)
    other = tmp_path / "other.hex"
    other.write_text(img.read_text().replace("\n", "\n", 1)[:-17] + "0000000000000000\n")
    assert rom_gen.verify_personalisation(mp, other)["verdict"] == "FAIL"


@pytest.mark.parametrize("f", ["ot_rom_4096x72_m8.lef", "ot_rom_4096x72_m8_tt.lib", "ot_rom_4096x72_m8_ff.lib"])
def test_macro_views_hold_no_content(f):
    text = (MACRO.parent / f).read_text()
    assert "viamap" not in text.lower()          # content lives only in the per-instance via map


# ---- declared-logic allowlist (OWNER D-ROM-2 = (a), 2026-10-25 20:26) ----
def _rom(words, width, init, src="t.sv:1.1-2.2"):
    p = {"SIZE": _b(words), "WIDTH": _b(width), "RD_PORTS": _b(1), "WR_PORTS": _b(0), "MEMID": "$auto$proc_rom",
         "INIT": init}
    return {"type": "$mem_v2", "parameters": p, "attributes": {"src": src} if src else {}}


def _entry(init, words=256, width=8, src="t.sv"):
    import hashlib
    return dict(id="t_tab", module="t_mod", table="case table", src=src, words=words, width=width,
                sha256=hashlib.sha256(init.encode()).hexdigest(), reason="test")


def test_declared_table_passes_other_content_fails():
    init = "".join(random.Random(1).choice("01") for _ in range(256 * 8))
    other = init[:-1] + ("0" if init[-1] == "1" else "1")                 # one bit edited
    allow = [_entry(init)]
    ok = gate.check_design(design(t=_rom(256, 8, init)), allowlist=allow)
    assert ok["verdict"] == "PASS" and ok["declared"] == ["t_tab"]
    assert ok["memories"][0]["verdict"] == "DECL"
    assert gate.check_design(design(t=_rom(256, 8, other)), allowlist=allow)["verdict"] == "FAIL"
    assert gate.check_design(design(t=_rom(256, 8, init)))["verdict"] == "FAIL"           # no allowlist = raw check
    # same bits, other shape -> FAIL; other source file -> FAIL; no src attribute (kit netlists) -> hash decides
    assert gate.check_design(design(t=_rom(128, 16, init)), allowlist=allow)["verdict"] == "FAIL"
    assert gate.check_design(design(t=_rom(256, 8, init, src="w.sv:3.1-9.9")), allowlist=allow)["verdict"] == "FAIL"
    assert gate.check_design(design(t=_rom(256, 8, init, src="")), allowlist=allow)["verdict"] == "PASS"
    # a declared table beside an undeclared one: the design still FAILs on the undeclared one only
    mix = gate.check_design(design(t=_rom(256, 8, init), w=_rom(256, 8, other)), allowlist=allow)
    assert mix["verdict"] == "FAIL" and mix["n_fail"] == 1


def test_repo_allowlist_is_well_formed_and_cli_uses_it(tmp_path):
    entries = gate.load_allowlist()
    ids = [e["id"] for e in entries]
    assert len(ids) == len(set(ids)) >= 7
    assert {(e["words"], e["width"]) for e in entries} >= {(512, 65), (512, 14), (256, 61), (128, 49), (1024, 10),
                                                            (64, 32)}
    assert not any(e["words"] == 32 and e["width"] == 32 for e in entries)   # KV dcal is D-ROM-3, never declared
    bad = tmp_path / "allow.json"
    bad.write_text(json.dumps({"tables": [dict(entries[0], reason="")]}))
    with pytest.raises(SystemExit):
        gate.load_allowlist(bad)
    init = "".join(random.Random(2).choice("01") for _ in range(256 * 8))
    al = tmp_path / "a.json"
    al.write_text(json.dumps({"tables": [_entry(init)]}))
    mj = tmp_path / "mem.json"
    mj.write_text(json.dumps(design(t=_rom(256, 8, init))))
    assert gate.main(["--mem-json", str(mj), "--allowlist", str(al)]) == 0
    assert gate.main(["--mem-json", str(mj), "--allowlist", str(al), "--no-allowlist"]) == 1
    assert gate.main(["--mem-json", str(mj)]) == 1                           # repo list does not hold this content
