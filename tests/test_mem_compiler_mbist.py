"""Quick checks of the memory BIST / repair RTL (rtl/dft/ot_mbist_*.sv, ot_rom_secded_dec.sv).

The full evidence is tools/rtl_mbist_campaign.py -> results/rtl/mbist_campaign.json;
these tests re-run a representative slice so a regression shows up in `pytest`.
"""
from __future__ import annotations

import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/mem_compiler"))

import ecc  # noqa: E402
import rtl_mbist_campaign as C  # noqa: E402

need_verilator = pytest.mark.skipif(shutil.which("verilator") is None, reason="verilator not installed")
need_yosys = pytest.mark.skipif(shutil.which("yosys") is None, reason="yosys not installed")


def test_bira_reference_allocations():
    # a must-repair column (fails in 3 > R rows) plus a full row
    ev = [(r, 1 << 9) for r in range(10)] + [(22, (1 << 64) - 1)]
    assert C.bira_ref(ev) == {"ok": True, "rows": [22], "cols": [9]}
    # three full rows cannot be repaired with two spare rows and two spare columns
    ev = [(r, (1 << 64) - 1) for r in (3, 20, 45)]
    assert C.bira_ref(ev)["ok"] is False
    # scattered single cells: the cheapest allocation is used
    ev = [(10, 1 << 2), (10, 1 << 25), (33, 1 << 2), (50, 1 << 40)]
    r = C.bira_ref(ev)
    assert r["ok"] and len(r["rows"]) + len(r["cols"]) == 3


@need_verilator
def test_dft_lint_clean():
    for top, files, params in (("ot_mbist_ctrl", C.DFT[:2], []), ("ot_mbist_sram_collar", [C.DFT[2]], []),
                               ("ot_mbist_rom_collar", [C.DFT[3]], []),
                               ("ot_rom_secded_dec", [C.DFT[4]], ["-GK=256"])):
        p = subprocess.run(["verilator", "--lint-only", "-Wall", *params, "--top-module", top,
                            *map(str, files)], capture_output=True, text=True)
        assert p.returncode == 0, p.stderr


@need_verilator
def test_secded_rtl_matches_reference(tmp_path):
    k = 64
    rng = random.Random(3)
    d = rng.getrandbits(k)
    cw = ecc.encode(d, k)
    n = ecc.codeword_bits(k)
    lines = [(cw, d, 0)] + [(cw ^ (1 << i), d, 1) for i in range(n)] + \
            [(cw ^ (1 << i) ^ (1 << ((i + 7) % n)), d, 2) for i in range(n)]
    vec = tmp_path / "v.txt"
    vec.write_text("".join(f"{a:x} {b:x} {s}\n" for a, b, s in lines))
    obj = tmp_path / "obj"
    subprocess.run(["verilator", "--cc", "--exe", "--build", "-Wno-fatal", f"-GK={k}", "--top-module", "tb_secded",
                    "-Mdir", str(obj), str(C.DFT[4]), str(C.TB_SEC), str(C.HARNESS),
                    "-CFLAGS", '-DVTOP_HEADER=\\"Vtb_secded.h\\" -DVTOP=Vtb_secded'], check=True, capture_output=True)
    out = subprocess.run([str(obj / "Vtb_secded"), f"+VEC={vec}"], check=True, capture_output=True, text=True).stdout
    assert f"vectors={len(lines)} errors=0" in out


@need_verilator
def test_mbist_detects_and_repairs(tmp_path):
    spec = C.rom_gen.spec_from_sheet(C.MACROS / C.M2 / f"{C.M2}.json")
    words = [ecc.encode(random.Random(1).getrandbits(64) ^ a, 64) for a in range(spec.words)]
    rec = C.rom_gen.personalise_instance(spec, words, "trom_r0_c0", tmp_path / "rom")
    obj = tmp_path / "obj"
    subprocess.run(["verilator", "--cc", "--exe", "--build", "-Wno-fatal", "+define+OT_MEM_FAULTS",
                    "--top-module", "tb_mbist", "-Mdir", str(obj), *map(str, C.DFT), *map(str, C.MODELS),
                    str(C.TB), str(C.HARNESS), "-CFLAGS", '-DVTOP_HEADER=\\"Vtb_mbist.h\\" -DVTOP=Vtb_mbist'],
                   check=True, capture_output=True)
    cases = [
        ([], {0: "pass", 1: "pass"}, "match"),
        ([C.f(0, "COL_SA", 0, C.col(0, 9, 1), v=1), C.f(0, "ROW_SA", 22, v=0)], {0: "repaired", 1: "pass"}, "match"),
        ([C.f(1, "CFIN", 10, 30, 9, 30, 1)], {0: "pass", 1: "repaired"}, "match"),
        ([C.f(0, "ROW_SA", r, v=1) for r in (3, 20, 45)], {0: "unrepairable", 1: "pass"}, "match"),
        ([C.f(2, "ROW_SA", 7, v=0)], {0: "pass", 1: "pass"}, "mismatch"),
    ]
    for i, (faults, want, rom) in enumerate(cases):
        ff = tmp_path / f"{i}.faults"
        ff.write_text("".join(f"{x['macro']} {C.KIND[x['kind']]} {x['row']} {x['col']} {x['aggr_row']} "
                              f"{x['aggr_col']} {x['value']}\n" for x in faults))
        out = subprocess.run([str(obj / "Vtb_mbist"), f"+FAULTS={ff}", f"+ROMSIG={rec['signature_crc32']}",
                              f"+OT_ROM_DIR={tmp_path / 'rom'}", "+TRACE"],
                             check=True, capture_output=True, text=True).stdout
        r = C.parse(out)
        assert {m: r["sram"][m]["status"] for m in (0, 1)} == want, (i, out[-2000:])
        assert r["rom"]["status"] == rom
        assert r["fuse_rotate_ok"]
        for m in (0, 1):
            if want[m] != "unrepairable":
                assert r["functional_mismatches"][m] == 0
            if m in r["ana"]:
                ref = C.bira_ref(r["events"][m])
                assert (r["ana"][m]["ok"], r["ana"][m]["rows"], r["ana"][m]["cols"]) == \
                       (ref["ok"], ref["rows"], ref["cols"])


@need_yosys
def test_dft_synthesizes(tmp_path):
    dft = ROOT / "rtl/dft"
    jobs = [
        ("ot_mbist_ctrl", ["ot_mbist_bira.sv", "ot_mbist_ctrl.sv"], "-set DMAX 16 -set E 3 -set AMAX 8 -set RMAX 6 -set CMAX 4"),
        ("ot_mbist_sram_collar", ["ot_mbist_sram_collar.sv"], "-set DW 16 -set DMAX 16 -set CMAX 4"),
        ("ot_mbist_rom_collar", ["ot_mbist_rom_collar.sv"], "-set DW 16"),
        ("ot_rom_secded_dec", ["ot_rom_secded_dec.sv"], "-set K 16"),
    ]
    for top, files, params in jobs:
        stat = tmp_path / f"{top}.stat"
        script = "; ".join([*(f"read_verilog -sv {dft / f}" for f in files), f"chparam {params} {top}",
                            f"synth -top {top} -flatten", f"tee -o {stat} stat"])
        subprocess.run(["yosys", "-q", "-p", script], check=True, capture_output=True, timeout=900)
        assert "Number of cells" in stat.read_text()


def test_committed_campaign_record_passes():
    rec = ROOT / "results/rtl/mbist_campaign.json"
    if not rec.is_file():
        pytest.skip("campaign record not generated")
    d = json.loads(rec.read_text())
    assert d["status"] == "pass"
    assert d["scenarios_passed"] == d["scenario_count"]
    for kind, v in d["single_fault_coverage"].items():
        assert v["detected"] == v["injected"], kind
