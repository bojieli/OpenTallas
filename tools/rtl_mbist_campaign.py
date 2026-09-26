#!/usr/bin/env python3
"""Memory BIST and repair campaign: March C- detection, BIRA repair, ROM signature, SECDED.

Builds rtl/test/tb_mbist.sv once under Verilator -- one shared
rtl/dft/ot_mbist_ctrl.sv testing two compiled SRAM macros
(ot_sram_1rw_256x64_m4_r2c2, ot_sram_1r1w_512x128_m4_r2c2) and one compiled
ROM (ot_rom_1024x72_m8, SECDED-encoded random content personalised by
tools/mem_compiler/rom_gen.py) -- with the macros' fault model enabled, and
runs every scenario below by injecting faults into the behavioural macro
models.  For each scenario it records the injected faults, the per-macro
BIST status, the BIRA allocation (cross-checked against a Python reference
BIRA run on the same failure-event stream), the post-repair functional
read-back and the fuse-chain rotation.  The SECDED decoder is checked
exhaustively over single-bit errors and over every double error of one word,
for K = 64 and K = 256, against tools/mem_compiler/ecc.py.

Writes results/rtl/mbist_campaign.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/mem_compiler"))
import ecc  # noqa: E402
import rom_gen  # noqa: E402

OUT = ROOT / "results/rtl/mbist_campaign.json"
MACROS = ROOT / "physical/asap7_memory_macros"
DFT = [ROOT / f"rtl/dft/{n}.sv" for n in ("ot_mbist_bira", "ot_mbist_ctrl", "ot_mbist_sram_collar",
                                          "ot_mbist_rom_collar", "ot_rom_secded_dec")]
M0, M1, M2 = "ot_sram_1rw_256x64_m4_r2c2", "ot_sram_1r1w_512x128_m4_r2c2", "ot_rom_1024x72_m8"
MODELS = [MACROS / n / f"{n}.v" for n in (M0, M1, M2)]
TB = ROOT / "rtl/test/tb_mbist.sv"
TB_SEC = ROOT / "rtl/test/tb_secded.sv"
HARNESS = ROOT / "rtl/test/mbist_harness.cpp"
LINT_FLAGS = ("-Wall",)

GEOM = {0: {"rows": 64, "bits": 64, "mux": 4, "spare_rows": 2, "spare_cols": 2},
        1: {"rows": 128, "bits": 128, "mux": 4, "spare_rows": 2, "spare_cols": 2}}
KIND = {"SA0": 1, "SA1": 2, "TF_UP": 3, "TF_DOWN": 4, "CFIN": 5, "CFID": 6, "CFST": 7,
        "AF_NONE": 8, "AF_ALIAS": 9, "AF_MULTI": 10, "ROW_SA": 11, "COL_SA": 12}
STATUS = {0: "not_run", 1: "pass", 2: "repaired", 3: "unrepairable"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def col(m: int, b: int, s: int) -> int:
    return b * GEOM[m]["mux"] + s


def f(m: int, kind: str, r: int = 0, c: int = 0, ar: int = 0, ac: int = 0, v: int = 0) -> dict:
    return {"macro": m, "kind": kind, "row": r, "col": c, "aggr_row": ar, "aggr_col": ac, "value": v}


# ---------------------------------------------------------------------------
# scenarios
# ---------------------------------------------------------------------------

def single_fault_scenarios(m: int) -> list[dict]:
    R, B = GEOM[m]["rows"], GEOM[m]["bits"]
    v = col(m, 7, 2)
    out = [
        ("SA0", [f(m, "SA0", 5, col(m, 3, 1))]),
        ("SA1", [f(m, "SA1", R - 1, col(m, B - 1, 3))]),
        ("TF_UP", [f(m, "TF_UP", 17, col(m, 11, 0))]),
        ("TF_DOWN", [f(m, "TF_DOWN", 18, col(m, 12, 3))]),
        ("CFIN_up_aggr_below", [f(m, "CFIN", 10, v, 9, v, 1)]),
        ("CFIN_down_aggr_above", [f(m, "CFIN", 10, v, 11, v, 0)]),
        ("CFIN_up_aggr_above", [f(m, "CFIN", 10, v, 11, v, 1)]),
        ("CFIN_down_aggr_below", [f(m, "CFIN", 10, v, 9, v, 0)]),
        ("CFID_up_to0_aggr_below", [f(m, "CFID", 12, v, 3, v, 0b01)]),
        ("CFID_up_to1_aggr_above", [f(m, "CFID", 12, v, 30, v, 0b11)]),
        ("CFID_down_to0_aggr_above", [f(m, "CFID", 12, v, 31, v, 0b00)]),
        ("CFID_down_to1_aggr_below", [f(m, "CFID", 12, v, 2, v, 0b10)]),
        ("CFST_a0_v0", [f(m, "CFST", 14, v, 20, col(m, 9, 1), 0b00)]),
        ("CFST_a0_v1", [f(m, "CFST", 14, v, 8, col(m, 9, 1), 0b10)]),
        ("CFST_a1_v0", [f(m, "CFST", 14, v, 21, col(m, 9, 1), 0b01)]),
        ("CFST_a1_v1", [f(m, "CFST", 14, v, 6, col(m, 9, 1), 0b11)]),
        ("CFIN_same_row_other_word", [f(m, "CFIN", 20, col(m, 5, 1), 20, col(m, 5, 0), 1)]),
        ("CFID_same_row_other_word", [f(m, "CFID", 20, col(m, 5, 2), 20, col(m, 5, 3), 0b01)]),
        ("CFST_same_row_other_word", [f(m, "CFST", 21, col(m, 6, 0), 21, col(m, 6, 1), 0b10)]),
        ("AF_NONE", [f(m, "AF_NONE", 7)]),
        ("AF_ALIAS", [f(m, "AF_ALIAS", 12, 0, 13)]),
        ("AF_MULTI", [f(m, "AF_MULTI", 30, 0, 31)]),
        ("ROW_SA0", [f(m, "ROW_SA", 40, v=0)]),
        ("ROW_SA1", [f(m, "ROW_SA", 41, v=1)]),
        ("COL_SA0", [f(m, "COL_SA", 0, col(m, 9, 2), v=0)]),
        ("COL_SA1", [f(m, "COL_SA", 0, col(m, B - 2, 1), v=1)]),
    ]
    return [{"name": f"m{m}_{n}", "faults": fl, "fault_class": n.split("_")[0] if not n.startswith(("ROW", "COL"))
             else n[:6], "expect": {"sram": {m: "repaired"}}} for n, fl in out]


def repair_scenarios() -> list[dict]:
    s = []
    s.append({"name": "m0_rows_only", "faults": [f(0, "ROW_SA", 5, v=1), f(0, "ROW_SA", 40, v=0)],
              "expect": {"sram": {0: "repaired"}, "rows": 2, "cols": 0}})
    s.append({"name": "m0_cols_only", "faults": [f(0, "COL_SA", 0, col(0, 17, 2), v=1),
                                                 f(0, "COL_SA", 0, col(0, 50, 0), v=0)],
              "expect": {"sram": {0: "repaired"}, "rows": 0, "cols": 2}})
    s.append({"name": "m0_must_col_and_must_row", "faults": [f(0, "COL_SA", 0, col(0, 9, 1), v=1),
                                                             f(0, "ROW_SA", 22, v=0)],
              "expect": {"sram": {0: "repaired"}, "rows": 1, "cols": 1}})
    s.append({"name": "m0_sparse_mixed", "faults": [f(0, "SA1", 10, col(0, 2, 0)), f(0, "SA1", 10, col(0, 25, 0)),
                                                    f(0, "SA1", 33, col(0, 2, 0)), f(0, "SA1", 50, col(0, 40, 3))],
              "expect": {"sram": {0: "repaired"}}})
    s.append({"name": "m0_unrepairable_three_rows", "faults": [f(0, "ROW_SA", 3, v=1), f(0, "ROW_SA", 20, v=0),
                                                               f(0, "ROW_SA", 45, v=1)],
              "expect": {"sram": {0: "unrepairable"}}})
    s.append({"name": "m0_unrepairable_three_cols", "faults": [f(0, "COL_SA", 0, col(0, 1, 0), v=1),
                                                               f(0, "COL_SA", 0, col(0, 30, 1), v=1),
                                                               f(0, "COL_SA", 0, col(0, 60, 3), v=0)],
              "expect": {"sram": {0: "unrepairable"}}})
    s.append({"name": "m0_unrepairable_scattered", "faults": [f(0, "SA1", r, col(0, b, 0))
                                                              for r, b in ((1, 1), (9, 9), (17, 17), (25, 25),
                                                                           (33, 33))],
              "expect": {"sram": {0: "unrepairable"}}})
    s.append({"name": "m0_spare_faults_unused", "faults": [f(0, "SA0", 64, col(0, 0, 0)),
                                                           f(0, "ROW_SA", 65, v=1),
                                                           f(0, "COL_SA", 0, 64 * 4 + 1, v=1)],
              "expect": {"sram": {0: "pass"}}})
    s.append({"name": "m0_spare_row1_faulty_row0_used", "faults": [f(0, "ROW_SA", 5, v=1), f(0, "ROW_SA", 65, v=0)],
              "expect": {"sram": {0: "repaired"}, "rows": 1}})
    s.append({"name": "m0_spare_row0_faulty_and_used", "faults": [f(0, "ROW_SA", 5, v=1), f(0, "SA0", 64, col(0, 4, 2))],
              "expect": {"sram": {0: "unrepairable"}},
              "note": "known limitation: the BIRA allocates spares without testing them first, so a defective "
                      "spare is caught by the verification pass and the macro is reported unrepairable"})
    s.append({"name": "m1_cols_only", "faults": [f(1, "COL_SA", 0, col(1, 100, 3), v=1),
                                                 f(1, "COL_SA", 0, col(1, 3, 0), v=0)],
              "expect": {"sram": {1: "repaired"}, "rows": 0, "cols": 2}})
    s.append({"name": "m1_must_col_and_must_row", "faults": [f(1, "COL_SA", 0, col(1, 64, 1), v=0),
                                                             f(1, "ROW_SA", 99, v=1)],
              "expect": {"sram": {1: "repaired"}, "rows": 1, "cols": 1}})
    s.append({"name": "m1_two_rows_two_cols", "faults": [f(1, "COL_SA", 0, col(1, 64, 1), v=0),
                                                         f(1, "COL_SA", 0, col(1, 65, 2), v=1),
                                                         f(1, "ROW_SA", 99, v=1), f(1, "AF_NONE", 7)],
              "expect": {"sram": {1: "repaired"}, "rows": 2, "cols": 2}})
    s.append({"name": "m0_programmed_all_four_backgrounds", "faults": [f(0, "CFIN", 10, col(0, 30, 2), 9,
                                                                               col(0, 30, 2), 1)],
              "plusargs": ["+BG=f"], "expect": {"sram": {0: "repaired"}},
              "note": "background register reprogrammed through cfg: solid, checkerboard, row and column "
                      "stripes, so the March C- program runs four times"})
    s.append({"name": "m0_programmed_mats_plus", "faults": [f(0, "SA0", 44, col(0, 12, 3))],
              "plusargs": ["+ALG1=90c0", "+ALG2=d090", "+ALG3=0", "+ALG4=0", "+ALG5=0"],
              "expect": {"sram": {0: "repaired"}},
              "note": "program register reloaded with MATS+ {(w0); up(r0,w1); down(r1,w0)}: 5N per pass"})
    s.append({"name": "m0_repair_under_stall", "faults": [f(0, "COL_SA", 0, col(0, 9, 1), v=1),
                                                          f(0, "ROW_SA", 22, v=0)], "hold": True,
              "expect": {"sram": {0: "repaired"}, "rows": 1, "cols": 1}})
    return s


def rom_scenarios(rows: list[int]) -> list[dict]:
    def bit(r, c):
        return (rows[r] >> c) & 1
    c1 = next(c for c in range(576) if bit(3, c) == 1)
    c0 = next(c for c in range(576) if bit(4, c) == 0)
    return [
        {"name": "rom_via_missing", "faults": [f(2, "SA0", 3, c1)], "expect": {"rom": "mismatch"}},
        {"name": "rom_via_extra", "faults": [f(2, "SA1", 4, c0)], "expect": {"rom": "mismatch"}},
        {"name": "rom_wordline_open", "faults": [f(2, "ROW_SA", 7, v=0)], "expect": {"rom": "mismatch"}},
        {"name": "rom_bitline_short", "faults": [f(2, "COL_SA", 0, 17, v=1)], "expect": {"rom": "mismatch"}},
    ]


# ---------------------------------------------------------------------------
# reference BIRA (same algorithm as rtl/dft/ot_mbist_bira.sv)
# ---------------------------------------------------------------------------

def bira_ref(events: list[tuple[int, int]], R: int = 2, C: int = 2, E: int = 6) -> dict:
    entries: list[list[int]] = []   # [row, mask] in slot order (None = free)
    slots: list[list[int] | None] = [None] * E
    must = 0
    ncols = 0
    unrep = False
    for row, vec in events:
        if unrep:
            continue
        vp = vec & ~must
        if not vp:
            continue
        tm = [s[1] if s else 0 for s in slots]
        tv = [s is not None for s in slots]
        hit = False
        for i, s in enumerate(slots):
            if s and s[0] == row:
                hit = True
                tm[i] |= vp
        tm.append(0 if hit else vp)
        tv.append((not hit) and vp != 0)
        newmust = 0
        for c in range(128):
            if sum(1 for i in range(E + 1) if tv[i] and (tm[i] >> c) & 1) > R:
                newmust |= 1 << c
        npop = bin(newmust).count("1")
        if ncols + npop > C:
            unrep = True
            continue
        tm = [t & ~newmust for t in tm]
        tv = [tv[i] and tm[i] != 0 for i in range(E + 1)]
        free = [i for i in range(E) if not tv[i]]
        if tv[E] and not free:
            unrep = True
            continue
        must |= newmust
        ncols += npop
        slots = [[slots[i][0] if slots[i] else row, tm[i]] if tv[i] else None for i in range(E)]
        if tv[E]:
            slots[free[0]] = [row, tm[E]]
    if unrep:
        return {"ok": False, "rows": [], "cols": []}
    best = None
    for s in range(1 << E):
        if any((s >> i) & 1 and slots[i] is None for i in range(E)):
            continue
        if bin(s).count("1") > R:
            continue
        cm = 0
        for i in range(E):
            if slots[i] and not (s >> i) & 1:
                cm |= slots[i][1]
        if bin(cm).count("1") + ncols > C:
            continue
        cost = bin(s).count("1") + bin(cm).count("1")
        if best is None or cost < best[0]:
            best = (cost, s, cm)
    if best is None:
        return {"ok": False, "rows": [], "cols": []}
    _, s, cm = best
    rows = sorted(slots[i][0] for i in range(E) if (s >> i) & 1)
    cols = sorted(c for c in range(128) if ((must | cm) >> c) & 1)
    return {"ok": True, "rows": rows, "cols": cols}


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def parse(out: str) -> dict:
    res: dict = {"sram": {}, "ana": {}, "events": {0: [], 1: []}}
    for m, st, rep in re.findall(r"SRAM m=(\d) status=(\d) rep=([0-9a-f]+)", out):
        res["sram"][int(m)] = {"status": STATUS[int(st)], "repair_register": rep}
    m = re.search(r"ROM m=0 status=(\d) sig=([0-9a-f]+) exp=([0-9a-f]+)", out)
    res["rom"] = {"status": "match" if m.group(1) == "1" else "mismatch", "signature": m.group(2),
                  "expected": m.group(3)}
    res["bist_pass"], res["bist_cycles"] = map(int, re.search(r"BIST pass=(\d) cycles=(\d+)", out).groups())
    for m_, n in re.findall(r"FUNC m=(\d) mismatches=(\d+)", out):
        res.setdefault("functional_mismatches", {})[int(m_)] = int(n)
    res["fuse_rotate_ok"] = bool(int(re.search(r"FUSE rotate_ok=(\d)", out).group(1)))
    for m_, row, vec in re.findall(r"FAILEV m=(\d) row=(\d+) vec=([0-9a-f]+)", out):
        res["events"][int(m_)].append((int(row), int(vec, 16)))
    for g in re.finditer(r"ANA m=(\d) ok=(\d) unrep=(\d) events=(\d+) must_cols=(\d+) rr_en=([01]+) "
                         r"rr_addr=([0-9a-f]+) cr_en=([01]+) cr_sel=([0-9a-f]+)", out):
        m_ = int(g.group(1))
        rr_en, rr_addr, cr_en, cr_sel = int(g.group(6), 2), int(g.group(7), 16), int(g.group(8), 2), int(g.group(9), 16)
        rows = sorted((rr_addr >> (7 * k)) & 0x7F for k in range(2) if (rr_en >> k) & 1)
        cols = sorted((cr_sel >> (7 * k)) & 0x7F for k in range(2) if (cr_en >> k) & 1)
        res["ana"][m_] = {"ok": g.group(2) == "1", "online_unrepairable": g.group(3) == "1",
                          "events": int(g.group(4)), "must_repair_cols": int(g.group(5)), "rows": rows, "cols": cols}
    return res


def run(scratch: Path) -> dict:
    # ROM content: random 64-bit data, SECDED to 72 bits, personalised into a via map
    spec = rom_gen.spec_from_sheet(MACROS / M2 / f"{M2}.json")
    rng = random.Random(7)
    data = [rng.getrandbits(64) for _ in range(spec.words)]
    words = [ecc.encode(d, 64) for d in data]
    romdir = scratch / "rom"
    rec = rom_gen.personalise_instance(spec, words, "trom_r0_c0", romdir)
    rows = rom_gen.via_map(spec, words)
    assert rom_gen.read_back(spec, rows) == words
    romsig = rec["signature_crc32"]

    obj = scratch / "obj"
    cflags = '-DVTOP_HEADER=\\"Vtb_mbist.h\\" -DVTOP=Vtb_mbist'
    subprocess.run(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "+define+OT_MEM_FAULTS",
                    "--top-module", "tb_mbist", "-Mdir", str(obj), *map(str, DFT), *map(str, MODELS), str(TB),
                    str(HARNESS), "-CFLAGS", "-O1", "-CFLAGS", cflags], check=True, capture_output=True)
    exe = obj / "Vtb_mbist"

    scen = [{"name": "fault_free", "faults": [], "expect": {"sram": {0: "pass", 1: "pass"}, "rom": "match"}}]
    for m in (0, 1):
        scen += single_fault_scenarios(m)
    scen += repair_scenarios()
    scen += rom_scenarios(rows)
    scen.append({"name": "all_macros_faulty", "faults": [f(0, "COL_SA", 0, col(0, 9, 1), v=1),
                                                         f(1, "ROW_SA", 50, v=0), f(1, "CFIN", 3, 9, 2, 9, 1),
                                                         f(2, "ROW_SA", 100, v=1)],
                 "expect": {"sram": {0: "repaired", 1: "repaired"}, "rom": "mismatch"}})
    results = []
    for sc in scen:
        ff = scratch / f"{sc['name']}.faults"
        ff.write_text("".join(f"{x['macro']} {KIND[x['kind']]} {x['row']} {x['col']} {x['aggr_row']} "
                              f"{x['aggr_col']} {x['value']}\n" for x in sc["faults"]))
        args = [str(exe), f"+FAULTS={ff}", f"+ROMSIG={romsig}", f"+OT_ROM_DIR={romdir}", "+TRACE"]
        if sc.get("hold"):
            args.append("+HOLD")
        args += sc.get("plusargs", [])
        out = subprocess.run(args, check=True, capture_output=True, text=True).stdout
        r = parse(out)
        exp = sc["expect"]
        checks = {}
        for m in (0, 1):
            want = exp.get("sram", {}).get(m, "pass")
            checks[f"m{m}_status"] = r["sram"][m]["status"] == want
            if r["sram"][m]["status"] in ("pass", "repaired"):
                checks[f"m{m}_functional_readback_clean"] = r["functional_mismatches"][m] == 0
            ref = bira_ref(r["events"][m])
            if m in r["ana"]:
                a = r["ana"][m]
                checks[f"m{m}_bira_matches_reference"] = (a["ok"] == ref["ok"] and a["rows"] == ref["rows"]
                                                         and a["cols"] == ref["cols"])
                r["ana"][m]["reference"] = ref
        checks["rom"] = r["rom"]["status"] == exp.get("rom", "match")
        checks["fuse_chain_rotation"] = r["fuse_rotate_ok"]
        if "rows" in exp:
            mm = next(iter(exp["sram"]))
            checks["rows_used"] = len(r["ana"].get(mm, {}).get("rows", [])) == exp["rows"]
        if "cols" in exp:
            mm = next(iter(exp["sram"]))
            checks["cols_used"] = len(r["ana"].get(mm, {}).get("cols", [])) == exp["cols"]
        detected = {m: r["sram"][m]["status"] != "pass" for m in (0, 1)}
        detected["rom"] = r["rom"]["status"] == "mismatch"
        r.pop("events")
        results.append({"name": sc["name"], "faults": sc["faults"], "hold": bool(sc.get("hold")),
                        "plusargs": sc.get("plusargs", []),
                        "expect": {k: ({str(a): b for a, b in v.items()} if isinstance(v, dict) else v)
                                   for k, v in exp.items()},
                        "note": sc.get("note"), "detected": {str(k): v for k, v in detected.items()},
                        "result": {"sram": {str(k): v for k, v in r["sram"].items()},
                                   "bira": {str(k): v for k, v in r["ana"].items()},
                                   "rom": r["rom"], "bist_pass": r["bist_pass"], "bist_cycles": r["bist_cycles"],
                                   "functional_mismatches": {str(k): v for k, v in
                                                             r["functional_mismatches"].items()},
                                   "fuse_rotate_ok": r["fuse_rotate_ok"]},
                        "checks": checks, "pass": all(checks.values())})

    # SECDED
    sec = {}
    for k in (64, 256):
        rng = random.Random(k)
        lines = []
        n = ecc.codeword_bits(k)
        for w in range(4):
            d = rng.getrandbits(k)
            cw = ecc.encode(d, k)
            lines.append((cw, d, 0))
            for i in range(n):
                lines.append((cw ^ (1 << i), d, 1))
            if w == 0:
                for i in range(n):
                    for j in range(i + 1, n):
                        lines.append((cw ^ (1 << i) ^ (1 << j), d, 2))
        for cw, d, st in lines:
            got = ecc.decode(cw, k)
            assert got[1] == ("ok", "corrected", "uncorrectable")[st] and (st == 2 or got[0] == d)
        vec = scratch / f"secded_{k}.txt"
        vec.write_text("".join(f"{cw:x} {d:x} {st}\n" for cw, d, st in lines))
        o = scratch / f"objs{k}"
        cf = '-DVTOP_HEADER=\\"Vtb_secded.h\\" -DVTOP=Vtb_secded'
        subprocess.run(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", f"-GK={k}",
                        "--top-module", "tb_secded", "-Mdir", str(o), str(ROOT / "rtl/dft/ot_rom_secded_dec.sv"),
                        str(TB_SEC), str(HARNESS), "-CFLAGS", "-O1", "-CFLAGS", cf], check=True, capture_output=True)
        so = subprocess.run([str(o / "Vtb_secded"), f"+VEC={vec}"], check=True, capture_output=True, text=True).stdout
        mm = re.search(r"SECDED K=(\d+) vectors=(\d+) errors=(\d+)", so)
        singles = 4 * (n + 1)
        sec[str(k)] = {"codeword_bits": n, "vectors": int(mm.group(2)), "errors": int(mm.group(3)),
                       "clean_and_single_error_vectors": singles, "double_error_vectors": n * (n - 1) // 2,
                       "pass": int(mm.group(3)) == 0 and int(mm.group(2)) == len(lines)}

    # lint
    lint = {}
    for top, files, params in (("ot_mbist_ctrl", DFT[:2], []), ("ot_mbist_sram_collar", [DFT[2]], []),
                               ("ot_mbist_sram_collar", [DFT[2]], ["-GPORTS=1", "-GNSR=0", "-GNSC=0"]),
                               ("ot_mbist_rom_collar", [DFT[3]], []),
                               ("ot_rom_secded_dec", [DFT[4]], ["-GK=256"])):
        p = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, *params, "--top-module", top,
                            *map(str, files)], capture_output=True, text=True)
        lint[f"{top}{''.join(params)}"] = {"returncode": p.returncode,
                                            "messages": p.stderr.strip().splitlines()[:10]}

    fault_cov = {}
    for res in results:
        for flt in res["faults"]:
            if flt["macro"] in (0, 1) and len(res["faults"]) == 1:
                key = flt["kind"]
                fault_cov.setdefault(key, {"injected": 0, "detected": 0, "repaired": 0})
                fault_cov[key]["injected"] += 1
                fault_cov[key]["detected"] += int(res["detected"][str(flt["macro"])])
                fault_cov[key]["repaired"] += int(res["result"]["sram"][str(flt["macro"])]["status"] == "repaired")
    return {
        "schema": "opentallas.mbist-campaign.v1",
        "status": "pass" if all(r["pass"] for r in results) and all(v["pass"] for v in sec.values())
        and all(v["returncode"] == 0 for v in lint.values()) else "fail",
        "claim_boundary": "cycle-accurate Verilator simulation of the BIST/repair RTL against the compiled "
                          "macros' behavioural models with injected faults; the fault model is the one in "
                          "tools/mem_compiler/behav.py, not a defect simulation of a layout",
        "algorithm": "March C- (reset default of ot_mbist_ctrl), solid background: {(w0); up(r0,w1); "
                     "up(r1,w0); down(r0,w1); down(r1,w0); (r0)}",
        "macros": {"m0": M0, "m1": M1, "m2": M2},
        "rom_personalisation": rec,
        "scenario_count": len(results),
        "scenarios_passed": sum(r["pass"] for r in results),
        "single_fault_coverage": fault_cov,
        "scenarios": results,
        "secded": sec,
        "verilator_lint": lint,
        "input_sha256": {str(p.relative_to(ROOT)): sha(p)
                         for p in (*DFT, *MODELS, TB, TB_SEC, HARNESS, Path(__file__),
                                   ROOT / "tools/mem_compiler/ecc.py", ROOT / "tools/mem_compiler/rom_gen.py")},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as t:
        result = run(Path(t))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    bad = [r["name"] for r in result["scenarios"] if not r["pass"]]
    print(result["status"], f"{result['scenarios_passed']}/{result['scenario_count']} scenarios",
          "secded", {k: v["pass"] for k, v in result["secded"].items()}, "failing:", bad)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
