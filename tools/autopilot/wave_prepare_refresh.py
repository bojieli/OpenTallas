#!/usr/bin/env python3
"""wave_prepare_refresh.py PREP_DIR: make wave_prepare.json match the prepared plan and sidecar actually on disk.

head_wave_kit_rtl.py export() refuses a kit when sha256(source_plan.json) != wave_prepare.json prepared_plan_sha256 ('prepared
plan changed'), so any edit of the plan after prepare (NF10/NF12 style) needs the receipt republished.  The wave switch step
runs this whenever the plan sha it adopts differs from the receipt (KIT-OPS-5 11-15).  Exit 0 = receipt current or refreshed,
1 = receipt missing/unreadable.  Prints one line.
"""
import hashlib, json, os, stat, sys, time


def digest(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def status(prep):
    """(ok, msg) without writing: a prep dir with no wave_prepare.json is not a prepared HEAD tree (ok); a receipt whose plan or
    sidecar sha differs from the files on disk is stale (not ok: head_wave_kit_rtl would raise 'prepared plan changed')"""
    rp = os.path.join(prep, "wave_prepare.json")
    if not os.path.exists(rp):
        return True, "no wave_prepare.json (not a prepared tree)"
    try:
        rec = json.load(open(rp))
        plan, side = digest(os.path.join(prep, "source_plan.json")), digest(os.path.join(prep, "source_sidecar.json"))
    except (OSError, ValueError) as e:
        return False, f"wave_prepare unreadable: {e}"
    if (rec.get("prepared_plan_sha256"), rec.get("sidecar_sha256")) == (plan, side):
        return True, f"wave_prepare current (plan {plan[:12]})"
    return False, f"wave_prepare STALE: receipt plan {str(rec.get('prepared_plan_sha256'))[:12]} != file {plan[:12]}"


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
    # P-RAIL-BYPASS (FLEET-OPS-R4 11-26, HEAD-INT-R2 hand-edited the shas past the guard): the supported path now also works in a read-only or overlaid fork
    # (the prep dir is made writable for the rename and restored) and keeps an audit trail of every refresh, so nobody needs to edit the receipt by hand
    rec.setdefault("refresh_history", []).append({"t": int(time.time()), "lane": os.environ.get("OT_LANE", ""), "host": os.uname().nodename,
                                                  "old_plan": old[0], "old_sidecar": old[1], "new_plan": plan, "new_sidecar": side})
    pst = os.lstat(prep)
    tmp = rp + ".new"
    try:
        os.chmod(prep, pst.st_mode | stat.S_IWUSR)
        json.dump(rec, open(tmp, "w"), indent=1)
        os.replace(tmp, rp)
    except OSError as e:
        return 1, f"cannot write {rp}: {e} (is {prep} a sealed tree? fork it with ot-tree-fork first)"
    finally:
        try:
            os.chmod(prep, pst.st_mode)
        except OSError:
            pass
    return 0, f"wave_prepare refreshed: plan {str(old[0])[:12]} -> {plan[:12]}, sidecar {str(old[1])[:12]} -> {side[:12]}"


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "--status":
        ok, msg = status(sys.argv[1]); print(msg); sys.exit(0 if ok else 1)
    rc, msg = refresh(sys.argv[1])
    print(msg)
    sys.exit(rc)
