#!/usr/bin/env python3
"""wave_prepare_refresh.py PREP_DIR: make wave_prepare.json match the prepared plan and sidecar actually on disk.

head_wave_kit_rtl.py export() refuses a kit when sha256(source_plan.json) != wave_prepare.json prepared_plan_sha256 ('prepared
plan changed'), so any edit of the plan after prepare (NF10/NF12 style) needs the receipt republished.  The wave switch step
runs this whenever the plan sha it adopts differs from the receipt (KIT-OPS-5 11-15).  Exit 0 = receipt current or refreshed,
1 = receipt missing/unreadable.  Prints one line.
"""
import hashlib, json, os, sys


def digest(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def refresh(prep):
    rp = os.path.join(prep, "wave_prepare.json")
    try:
        rec = json.load(open(rp))
    except (OSError, ValueError):
        return 1, f"no readable {rp}"
    plan, side = digest(os.path.join(prep, "source_plan.json")), digest(os.path.join(prep, "source_sidecar.json"))
    old = (rec.get("prepared_plan_sha256"), rec.get("sidecar_sha256"))
    if old == (plan, side):
        return 0, f"wave_prepare current (plan {plan[:12]})"
    rec["prepared_plan_sha256"], rec["sidecar_sha256"] = plan, side
    rec["republished_by"] = "wave_prepare_refresh (plan/sidecar edited after prepare)"
    tmp = rp + ".new"
    json.dump(rec, open(tmp, "w"), indent=1)
    os.replace(tmp, rp)
    return 0, f"wave_prepare refreshed: plan {str(old[0])[:12]} -> {plan[:12]}, sidecar {str(old[1])[:12]} -> {side[:12]}"


if __name__ == "__main__":
    rc, msg = refresh(sys.argv[1])
    print(msg)
    sys.exit(rc)
