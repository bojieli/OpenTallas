#!/usr/bin/env python3
"""Run the actual v41x MTP RTL on existing images, without any model inference.

Successor to the handover campaign: keep build objects and stream each simulation
to its own log, including mutants. Never regenerate missing expectations on a CPU
host. An existing image is historical stimulus, not new checkpoint qualification.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
MISMATCHES = ("token_mismatches", "accept_mismatches", "head_mismatches",
              "vm_mismatches", "kv_mismatches")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parse_terminal(out, returncode, campaign):
    m = campaign.C.SUMMARY.search(out)
    r = {"returncode": returncode, "pass": False}
    if not m:
        r["tail"] = out.splitlines()[-20:]
        return r
    keys = ("prompt", "generated", "iters", "token_mismatches", "accept_mismatches",
            "heads", "head_mismatches", "prefill_cycles", "iter_cycles", "draft_cycles",
            "vm_mismatches", "kv_mismatches")
    r.update(zip(keys, map(int, m.groups())))
    r["per_iter"] = [dict(zip(("it", "pos", "input", "accepted", "emitted", "cycles",
                              "draft_cycles", "fault"), map(int, x.groups())))
                     for x in campaign.C.ITER.finditer(out)]
    cnt = {x.group(1): {"ops": int(x.group(2)), "elements": int(x.group(3))}
           for x in campaign.XCNT.finditer(out)}
    r["activation"] = campaign.X.activation(cnt)
    r["pass"] = (returncode == 0 and "PASS" in out.splitlines()
                 and all(r[k] == 0 for k in MISMATCHES)
                 and r["activation"]["pass"] and len(r["per_iter"]) == r["iters"]
                 and r["iters"] > 0 and all(x["fault"] == 0 for x in r["per_iter"]))
    r["tail"] = out.splitlines()[-20:]
    return r


def check_image(img, gamma):
    args = (img / "run.args").read_text().split()
    if f"+GAMMA={gamma}" not in args or "+PLAIN" in args:
        raise ValueError(f"image is not a gamma-{gamma} MTP image: {img}")
    isa = json.loads((img / "isa.json").read_text())
    if not isa.get("equal_golden_tokens") or not isa.get("committed_logits_bit_exact_with_golden"):
        raise ValueError(f"image did not pass its original ISA/golden comparison: {img}")
    files = sorted(img.glob("*.hex")) + [img / "run.args", img / "isa.json"]
    return args, isa, {p.name: digest(p) for p in files}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--part", required=True)
    ap.add_argument("--image", type=Path, action="append", required=True)
    ap.add_argument("--units", default="he,me,att,sel,eg,su")
    ap.add_argument("--fp", choices=("rtl", "dpi"), default="rtl")
    ap.add_argument("--acc-guard", action="store_true")
    ap.add_argument("--sink-handshake", action="store_true", help="opt-in actual Sinkhorn acceptance successor; cached images only")
    ap.add_argument("--gamma", type=int, choices=(1, 3, 5), default=5)
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--run-dir", type=Path, required=True)
    a = ap.parse_args()
    # Reject missing inputs before importing or building anything. No Model(),
    # golden_run(), make_images(), ISA execution or inference is called here.
    images = [(p.resolve(), *check_image(p, a.gamma)) for p in a.image]
    a.run_dir.mkdir(parents=True, exist_ok=False)
    import rtl_hdc_dspark_v41x_campaign as campaign
    campaign.X.UNITS = campaign.UNITS = tuple(a.units.split(","))
    if set(campaign.UNITS) - set(campaign.X.X_UNITS) or "idx" in campaign.UNITS:
        raise ValueError("unsupported units")
    campaign.X.PARAMS["fp"] = a.fp
    campaign.ACC_GUARD = a.acc_guard
    campaign.SINK_HANDSHAKE = a.sink_handshake
    sources = [campaign.X.SVH, campaign.X.VLT, *campaign.sources(True), campaign.TB,
               campaign.HARNESS, *campaign.TOOLS, Path(__file__).resolve()]
    pins = {str(p.relative_to(ROOT)): digest(p) for p in sources}
    rec = {"schema": "opentallas.hdc-dspark-v41x-rtl-part.v1", "part": a.part,
           "status": "building", "core": "ot_hdc_core_v41x", "gamma": a.gamma,
           "verify_positions": a.gamma + 1, "nslot": 8, "lane_multiplier_mp": 1,
           "sink_handshake": a.sink_handshake,
           "respecified_units": list(campaign.UNITS), "fp": a.fp,
           "accept_unit": "ot_hdc_mtp_accept_guarded" if a.acc_guard else "ot_hdc_accept",
           "input_sha256": pins, "image_sha256": {str(p): h for p, _, _, h in images},
           "claim_boundary": "cached reduced images, actual RTL; no new golden or inference, no SS/FF claim",
           "runs": []}

    def save():
        p = a.run_dir / "part.json.tmp"
        p.write_text(json.dumps(rec, indent=1) + "\n")
        p.replace(a.run_dir / "part.json")

    save()
    try:
        exe = campaign.build(a.run_dir.resolve(), jobs=a.jobs)
        rec["executable_sha256"] = digest(exe)
        rec["status"] = "running"
        save()
        for n, (img, args, isa, _) in enumerate(images):
            log = a.run_dir / f"run{n}.log"
            started = time.monotonic()
            with log.open("x") as f:
                process = subprocess.Popen(["stdbuf", "-oL", str(exe), f"+DIR={img}", *args],
                                           stdout=f, stderr=subprocess.STDOUT)
                rec["active"] = {"pid": process.pid, "image": str(img), "log": str(log)}
                save()
                rc = process.wait()
            rtl = parse_terminal(log.read_text(), rc, campaign)
            rtl["seconds"] = round(time.monotonic() - started, 1)
            rtl["log_sha256"] = digest(log)
            rec["runs"].append({"prompt": f"cached_p{rtl.get('prompt', 'unknown')}",
                                "drafter": "forced" if "+FORCE" in args else "dspark",
                                "isa": isa, "rtl": rtl, "pass": rtl["pass"]})
            rec.pop("active", None)
            save()
        rec["sources_unchanged"] = all(digest(ROOT / p) == h for p, h in pins.items())
        rec["pass"] = bool(rec["runs"]) and all(r["pass"] for r in rec["runs"]) and rec["sources_unchanged"]
        rec["status"] = "pass" if rec["pass"] else "fail"
        save()
        return 0 if rec["pass"] else 1
    except BaseException as e:
        rec["status"] = "fail"
        rec["pass"] = False
        rec["error"] = str(e)
        save()
        raise


if __name__ == "__main__":
    raise SystemExit(main())
