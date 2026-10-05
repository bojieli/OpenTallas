#!/usr/bin/env python3
"""Run the minimum-component slices of one DSpark MTP step (tools/dsrom_dspark_step_slices.py) on the
as-built V4.1 core (rtl/test/tb_hdc_core_v41_mtp_slice.sv) and compose the step analytically.

Each slice is one section of the ITER program simulated alone from the ISA model's state, checked bit for bit
(heads, vector memory, KV SRAM, ACCEPT count).  No model inference.  Composition: the step's cycles are the
sum of its sections' cycles, minus the per-slice fixed cost a contiguous program does not pay (each slice's
start runs the 8-cycle DYN pass and its END; measured on an END-only slice, the "null" slice), plus one
start/END.  Sections are serial on the core (each slice drains before END), so the sum is an upper bound on
the contiguous program by at most the cross-section overlap the drain removes.

    python3 tools/dsrom_dspark_step_slices_rtl.py --slices DIR --run-dir DIR [--sink-handshake] [--jobs 16]
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41_mtp_campaign as C  # noqa: E402
from dsrom_sink_handshake import select  # noqa: E402

TB = ROOT / "rtl/test/tb_hdc_core_v41_mtp_slice.sv"
HARNESS = ROOT / "rtl/test/hdc_core_v41_mtp_slice_harness.cpp"
SLICE = re.compile(r"SLICE cycles=(\d+) heads=(\d+) head_mismatches=(\d+) acc_n=(\d+) exp_acc_n=(\d+) "
                   r"vm_mismatch=(\d+) kv_mismatch=(\d+) fault=(\d+) busy_me=(\d+) busy_su=(\d+) busy_qe=(\d+) "
                   r"busy_xu=(\d+) busy_he=(\d+)")
KEYS = ("cycles", "heads", "head_mismatches", "acc_n", "exp_acc_n", "vm_mismatch", "kv_mismatch", "fault",
        "busy_me", "busy_su", "busy_qe", "busy_xu", "busy_he")


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(obj, sources, defines):
    subprocess.run(["verilator", "--cc", "--exe", "--build", "-O1", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
                    "-Wno-BLKSEQ", "-Wno-IMPORTSTAR", "--top-module", "tb_hdc_core_v41_mtp_slice", "-Mdir", str(obj),
                    f"-I{C.SVH.parent}", f"+define+HDC_SW={C.I.SU_LANES}", "+define+HDC_MP=1", *defines,
                    *map(str, sources), str(TB), str(HARNESS), "-CFLAGS", "-O1", "-j", "8"],
                   check=True, capture_output=True)
    return obj / "Vtb_hdc_core_v41_mtp_slice"


def classify(name):
    if name.startswith("draft"):
        return "draft"
    if name in ("prologue",):
        return "prologue"
    if name.startswith("head"):
        return "head"
    if name.startswith("accept"):
        return "commit"
    if name.startswith("mtp"):
        return "dspark_seed"
    if re.fullmatch(r"L\d+", name):
        return "verify_layers"
    return "other"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slices", type=Path, required=True)
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--sink-handshake", action="store_true")
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    a.run_dir.mkdir(parents=True, exist_ok=True)
    man = json.loads((a.slices / "manifest.json").read_text())
    sel = select(C.RTL, enable=a.sink_handshake)
    exe = build(a.run_dir / "obj", sel["sources"], sel["defines"])
    rom = (a.slices / "rom").resolve()
    names = [s["name"] for s in man["slices"]] + (["null"] if (a.slices / "null").is_dir() else [])
    if a.only:
        names = [n for n in names if n in a.only]

    def run(name):
        d = (a.slices / name).resolve()
        log = a.run_dir / f"{name}.log"
        with log.open("w") as f:
            rc = subprocess.run([str(exe), f"+DIR={d}", f"+ROMDIR={rom}", *(d / "run.args").read_text().split()],
                                stdout=f, stderr=subprocess.STDOUT).returncode
        out = log.read_text(errors="replace")
        m = SLICE.search(out)
        r = {"name": name, "returncode": rc, "pass": rc == 0 and m is not None and "PASS" in out.split()}
        if m:
            r.update(zip(KEYS, map(int, m.groups())))
        else:
            r["tail"] = out.splitlines()[-10:]
        return r

    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        res = list(ex.map(run, names))
    by = {r["name"]: r for r in res}
    info = {s["name"]: s for s in man["slices"]}
    null = by.get("null", {}).get("cycles")
    groups = {}
    for s in man["slices"]:
        r = by.get(s["name"])
        if r is None or "cycles" not in r:
            continue
        g = classify(s["name"])
        groups.setdefault(g, {"slices": 0, "cycles": 0, "instructions": 0})
        groups[g]["slices"] += 1
        groups[g]["cycles"] += r["cycles"] - (null or 0)
        groups[g]["instructions"] += s["instructions"]
    total = sum(g["cycles"] for g in groups.values()) + (null or 0)
    rec = {"core": "ot_hdc_core_v41", "nslot": 8, "mp": 1, "gamma": man["gamma"], "prompt": man["prompt"],
           "pos": man["pos"], "sink_handshake": a.sink_handshake, "defines": sel["defines"],
           "isa_step": {k: man[k] for k in ("accepted", "emitted", "drafts", "targets", "golden_next",
                                            "emitted_equal_golden")},
           "null_slice_cycles": null, "slices": [dict(r, **{k: info[r["name"]][k] for k in ("pc", "instructions")})
                                                  if r["name"] in info else r for r in res],
           "all_slices_pass": all(r["pass"] for r in res),
           "composed": {"groups": groups, "step_cycles": total,
                        "draft_cycles": groups.get("draft", {}).get("cycles"),
                        "verify_cycles": sum(groups.get(g, {}).get("cycles", 0)
                                             for g in ("prologue", "verify_layers", "head")),
                        "dspark_seed_cycles": groups.get("dspark_seed", {}).get("cycles"),
                        "commit_cycles": groups.get("commit", {}).get("cycles"),
                        "emitted_tokens": len(man["emitted"]),
                        "cycles_per_emitted_token": round(total / len(man["emitted"]), 1)},
           "input_sha256": {str(p.relative_to(ROOT)): digest(p) for p in
                            (C.SVH, *sel["sources"], TB, HARNESS, *C.TOOLS, Path(__file__).resolve(),
                             ROOT / "tools/dsrom_sink_handshake.py", ROOT / "tools/dsrom_dspark_step_slices.py")},
           "slice_manifest_sha256": digest(a.slices / "manifest.json")}
    (a.run_dir / "result.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({"all_slices_pass": rec["all_slices_pass"], **rec["composed"]}, indent=1))
    return 0 if rec["all_slices_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
