#!/usr/bin/env python3
"""W11: the 1.2 GHz forms of the ring reader control and the quarter join against their compare forms.

ot_hdc_v41x_idx_kctl_ring and ot_hdc_v41x_idx_quarter_join were restructured for 0.833 ns (registered
flags, down-counters, early reads).  This gate extracts the compare forms from REF_COMMIT (7361f422,
before the change), renames them *_ref, and runs each pair in lockstep in Verilator: one stimulus drives
both, every output port is compared on every cycle, and any difference fails.  Configurations: the die
shape (NPC 32, WB 128, GA 120, AW 30, HW 23) at three seeds, a small ROB (WB 32, GA 24), heavy
back-pressure with long scans, and the join with random commands (including illegal skips and commands
while busy) and random stream / consumer back-pressure.  A mutant of each (one operator changed) must
FAIL.  Writes results/rtl/w11_ring_lockstep.json.
"""
from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import re
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/w11_ring_lockstep.json"
REF_COMMIT = "7361f422aab60007c0f1fafb7c1db59183a21f19"
V = "rtl/hdc/v41x/"
KCTL = V + "ot_hdc_v41x_idx_kstream_ring.sv"
JOIN = V + "ot_hdc_v41x_idx_quarter_join.sv"
KS = V + "ot_hdc_v41x_idx_kstream.sv"
PREFIX = "rtl/hdc/ot_hdc_prefix.sv"
TB_K = "rtl/test/tb_w11_kctl_lockstep.sv"
TB_J = "rtl/test/tb_w11_join_lockstep.sv"
CPP = "rtl/test/w11_lockstep.cpp"
SOURCES = [KCTL, JOIN, KS, PREFIX, TB_K, TB_J, CPP, "tools/w11_ring_lockstep.py"]
RE = re.compile(r"W11_(KCTL|JOIN)_LOCKSTEP (PASS|FAIL) (\S+)=(\d+) cycles=(\d+) (?:requests=(\d+) )?beats=(\d+) mismatches=(\d+)")

KCTL_RUNS = [
    ("die_seed1", {}, 1), ("die_seed2", {}, 2), ("die_seed3", {}, 3),
    ("wb32", {"WB": 32, "GA": 24, "HW": 20, "AW": 24, "RDYP": 40, "DRP": 30, "RSPP": 40}, 1),
    ("backpressure_long", {"RDYP": 25, "DRP": 15, "RSPP": 30, "MAXK": 40000, "NSCAN": 400}, 1),
]
JOIN_RUNS = [("join_random", {"NCMD": 200}, 1)]
MUTANTS = {
    "kctl_lookahead": (KCTL, ": (eg[pf] < GA);", ": (eg[pf] <= GA);", {"NSCAN": 100}),
    "join_last": (JOIN, "(rem[q]>=17 && rem[q]<=32)", "(rem[q]>=17 && rem[q]<32)", {"NCMD": 40}),
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def module_text(path: str, commit: str | None, name: str, rename: str | None) -> str:
    src = (subprocess.run(["git", "show", f"{commit}:{path}"], cwd=ROOT, check=True, capture_output=True,
                          text=True).stdout if commit else (ROOT / path).read_text())
    i = src.index(f"module {name}")
    e = src.index("endmodule", i) + len("endmodule")
    body = src[i:e]
    if rename:
        body = body.replace(f"module {name}", f"module {rename}", 1)
    return "`timescale 1ns/1ps\n" + body + "\n"


def build(tmp: Path, top: str, files: list[Path], params: dict, tag: str) -> Path:
    obj = tmp / f"obj_{tag}"
    cmd = ["verilator", "--cc", "--exe", "--build", "-O2", "-j", "4", "-Wno-fatal", "-Wno-lint", "-Wno-WIDTH",
           "-Wno-UNOPTFLAT", "-Wno-TIMESCALEMOD", "--top-module", top, "--prefix", "Vtop",
           *[f"-G{k}={v}" for k, v in params.items()], "--Mdir", str(obj),
           *map(str, files), str(ROOT / CPP)]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return obj / "Vtop"


def run(exe: Path, seed: int) -> dict:
    t0 = time.time()
    out = subprocess.run([str(exe), f"+verilator+seed+{seed}"], capture_output=True, text=True, timeout=7200).stdout
    m = RE.search(out)
    if not m:
        return {"passed": False, "raw": out[-400:]}
    return {"passed": m.group(2) == "PASS", m.group(3): int(m.group(4)), "cycles": int(m.group(5)),
            **({"requests": int(m.group(6))} if m.group(6) else {}), "beats": int(m.group(7)),
            "mismatches": int(m.group(8)), "wall_seconds": round(time.time() - t0, 1)}


def main() -> int:
    pins = {p: sha(ROOT / p) for p in SOURCES}
    cases, mutants = [], {}
    with tempfile.TemporaryDirectory(prefix="w11ls-") as td:
        tmp = Path(td)
        kref = tmp / "kctl_ref.sv"; kref.write_text(module_text(KCTL, REF_COMMIT, "ot_hdc_v41x_idx_kctl_ring",
                                                                  "ot_hdc_v41x_idx_kctl_ring_ref"))
        knew = tmp / "kctl_new.sv"; knew.write_text(module_text(KCTL, None, "ot_hdc_v41x_idx_kctl_ring", None)
                                                     + module_text(KCTL, None, "ot_hdc_v41x_idx_kdec", None))
        jref = tmp / "join_ref.sv"; jref.write_text(module_text(JOIN, REF_COMMIT, "ot_hdc_v41x_idx_quarter_join",
                                                                  "ot_hdc_v41x_idx_quarter_join_ref"))
        jnew = tmp / "join_new.sv"; jnew.write_text(module_text(JOIN, None, "ot_hdc_v41x_idx_quarter_join", None))
        jobs = [("kctl_ring", n, p, sd, [ROOT / TB_K, ROOT / PREFIX, kref, knew], "tb_w11_kctl_lockstep") for n, p, sd in KCTL_RUNS]
        jobs += [("quarter_join", n, p, sd, [ROOT / TB_J, jref, jnew], "tb_w11_join_lockstep") for n, p, sd in JOIN_RUNS]
        for mname, (path, old, new, params) in MUTANTS.items():
            src = knew if path == KCTL else jnew
            text = src.read_text()
            assert text.count(old) == 1, mname
            mut = tmp / f"{mname}.sv"; mut.write_text(text.replace(old, new))
            files = [ROOT / TB_K, ROOT / PREFIX, kref, mut] if path == KCTL else [ROOT / TB_J, jref, mut]
            top = "tb_w11_kctl_lockstep" if path == KCTL else "tb_w11_join_lockstep"
            jobs.append(("mutant", mname, params, 1, files, top))

        def one(j):
            unit, name, params, seed, files, top = j
            return j, run(build(tmp, top, files, params, name), seed)

        with cf.ThreadPoolExecutor(max_workers=len(jobs)) as ex:
            for (unit, name, params, seed, files, top), r in ex.map(one, jobs):
                if unit == "mutant":
                    path, old, new, _ = MUTANTS[name]
                    mutants[name] = {"change": f"{old} -> {new}", "failed_as_required": not r["passed"], **r}
                else:
                    cases.append({"name": name, "unit": unit, "parameters": params, "seed": seed, **r})
    assert {p: sha(ROOT / p) for p in SOURCES} == pins, "a source changed while the gate ran"
    ok = all(c["passed"] for c in cases) and all(m["failed_as_required"] for m in mutants.values())
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    rec = {
        "schema": "w11_ring_lockstep_v1",
        "status": "pass" if ok else "fail",
        "git_head": head,
        "reference_commit": REF_COMMIT,
        "simulator": "Verilator " + subprocess.run(["verilator", "--version"], capture_output=True,
                                                   text=True).stdout.split()[1],
        "cases": cases,
        "negative_controls": mutants,
        "claim": ("Port-for-port, cycle-for-cycle equality of the 1.2 GHz forms with the compare forms under the "
                  "benches' random stimulus; the kctl_ring form is exact for every scan whose block counts fit the "
                  "HW-bit block counter (all the address space holds), which the benches' scans do."),
        "sources_sha256": pins,
    }
    if OUT.exists():
        raise SystemExit(f"{OUT} exists; records are never overwritten")
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    print(rec["status"], [(c["name"], c["passed"], c["cycles"]) for c in cases], {k: v["failed_as_required"] for k, v in mutants.items()})
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
