#!/usr/bin/env python3
"""Run the as-built V4.1 core's MTP bench (tb_hdc_core_v41_mtp, ot_hdc_core_v41, NSLOT 8, MP 1) on existing
images, without any model inference: the rom_m1_* parts of tools/rtl_hdc_v41_mtp_campaign.py and its --plain
baseline, from images that campaign (or tools/dsrom_dspark_make_images.py) already wrote.

--sink-handshake builds with the default-off XU/Sinkhorn acceptance successor (tools/dsrom_sink_handshake.py).
Each simulation streams to its own log under --run-dir; part.json is rewritten as runs finish.

    python3 tools/dsrom_dspark_cached_rtl_v41.py --part rom_m1_g5_gold4 --sink-handshake --mutate \
        --image IMG [--image IMG ...] --run-dir DIR
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41_mtp_campaign as C  # noqa: E402
from dsrom_sink_handshake import select  # noqa: E402


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse(out, rc, plain):
    r = {"returncode": rc}
    if plain:
        m = C.PLAIN.search(out)
        r["pass"] = rc == 0 and "PASS" in out.split() and m is not None
        if m:
            r.update(zip(("prompt", "generated", "token_mismatches", "heads", "head_mismatches", "prefill_cycles",
                          "decode_cycles", "decode_steps", "vm_mismatches", "kv_mismatches"), map(int, m.groups())))
            r["cycles_per_token"] = round(r["decode_cycles"] / r["decode_steps"], 1)
    else:
        m = C.SUMMARY.search(out)
        r["pass"] = rc == 0 and "PASS" in out.split() and m is not None
        if m:
            r.update(zip(("prompt", "generated", "iters", "token_mismatches", "accept_mismatches", "heads",
                          "head_mismatches", "prefill_cycles", "iter_cycles", "draft_cycles", "vm_mismatches",
                          "kv_mismatches"), map(int, m.groups())))
            it = [dict(zip(("it", "pos", "input", "accepted", "emitted", "cycles", "draft_cycles", "fault"),
                           map(int, x.groups()))) for x in C.ITER.finditer(out)]
            r["per_iter"] = it
            r["pass"] = r["pass"] and len(it) == r["iters"] > 0 and all(x["fault"] == 0 for x in it)
            if it:
                n, em = len(it), sum(x["emitted"] for x in it)
                r["draft_cycles_per_step"] = round(sum(x["draft_cycles"] for x in it) / n, 1)
                r["verify_accept_cycles_per_step"] = round(sum(x["cycles"] - x["draft_cycles"] for x in it) / n, 1)
                r["cycles_per_step"] = round(sum(x["cycles"] for x in it) / n, 1)
                r["emitted"] = em
                r["cycles_per_emitted_token"] = round(sum(x["cycles"] for x in it) / em, 1) if em else None
                r["accepted_hist"] = {a: sum(x["accepted"] == a for x in it) for a in sorted({x["accepted"] for x in it})}
        u = C.UTIL.search(out)
        if u:
            r["iter_unit_busy_cycles"] = dict(zip(("me", "su", "qe", "xu", "he"), map(int, u.groups())))
    r["tail"] = out.strip().splitlines()[-12:]
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--part", required=True)
    ap.add_argument("--image", type=Path, action="append", required=True)
    ap.add_argument("--sink-handshake", action="store_true")
    ap.add_argument("--mutate", action="store_true", help="also run the HDC_MUTATE_RESTORE build on the first "
                                                          "+FORCE image (it must be detected)")
    ap.add_argument("--run-dir", type=Path, required=True)
    a = ap.parse_args()
    a.run_dir.mkdir(parents=True, exist_ok=True)
    sel = select(C.RTL, enable=a.sink_handshake)
    C.RTL = sel["sources"]
    defines = tuple(d.removeprefix("+define+") for d in sel["defines"])
    imgs = [p.resolve() for p in a.image]
    args = {p: (p / "run.args").read_text().split() for p in imgs}
    plain = {p: "+PLAIN" in args[p] for p in imgs}
    srcs = [C.SVH, *C.RTL, C.TB, C.HARNESS, *C.TOOLS, Path(__file__).resolve(), ROOT / "tools/dsrom_sink_handshake.py"]
    rec = {"part": a.part, "core": "ot_hdc_core_v41", "nslot": 8, "mp": 1, "sink_handshake": a.sink_handshake,
           "defines": list(defines), "status": "building",
           "input_sha256": {str(p.relative_to(ROOT)): digest(p) for p in srcs},
           "image_sha256": {str(p): {f.name: digest(f) for f in sorted(p.iterdir()) if f.is_file()} for p in imgs},
           "runs": []}
    out = a.run_dir / "part.json"

    def save():
        out.write_text(json.dumps(rec, indent=1) + "\n")
    save()
    t0 = time.time()
    exe = C.build(a.run_dir, 1, False, defines)
    mexe = None
    forced = [p for p in imgs if "+FORCE" in args[p]]
    if a.mutate and forced:
        mexe = C.build(a.run_dir, 1, False, defines + ("HDC_MUTATE_RESTORE",))
    rec["build_seconds"] = round(time.time() - t0, 1)
    rec["status"] = "running"
    save()
    jobs = [(p.name, exe, p) for p in imgs] + ([("MUTANT_" + forced[0].name, mexe, forced[0])] if mexe else [])

    def sim(job):
        name, x, img = job
        log = a.run_dir / f"{name}.log"
        t = time.time()
        with log.open("w") as f:
            rc = subprocess.run([str(x), f"+DIR={img}", *args[img]], stdout=f, stderr=subprocess.STDOUT).returncode
        r = parse(log.read_text(errors="replace"), rc, plain[img])
        r["seconds"] = round(time.time() - t, 1)
        return name, img, r

    with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
        for name, img, r in ex.map(sim, jobs):
            if name.startswith("MUTANT_"):
                rec["mutation_rtl_restore_slot_plus_1"] = {"image": str(img), "detected": not r["pass"],
                                                           **{k: v for k, v in r.items() if k != "per_iter"}}
            else:
                rec["runs"].append({"image": str(img), "args": args[img], "rtl": r, "pass": r["pass"]})
            save()
    rec["pass"] = all(r["pass"] for r in rec["runs"]) and \
        rec.get("mutation_rtl_restore_slot_plus_1", {"detected": True})["detected"]
    rec["status"] = "done"
    save()
    return 0 if rec["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
