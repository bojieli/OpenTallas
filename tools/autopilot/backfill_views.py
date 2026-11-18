#!/usr/bin/env python3
"""BACKFILL-VIEWS (KITPACK-CLOSE-1115, COORD r221 follow-up): close every view the CURRENT plans of record reference.

For each die of kit_wave.json, read its plan (dies.<die>.plan), take every child *.lef under partition_types, resolve the view dir
on THIS host and make it closed in place: signoff.json copied from provenance.export.signoff (sha256 must equal
export.signoff_sha256) and, for a hard landing child whose build dir (provenance.src) still holds face_guard.json + land_slots.json,
landing_evidence/ via hard_landing.close_view.  Nothing else in the view is touched (provenance.json stays byte-identical).

  closed      became closed now   would   closable (dry run)          already   was closed          open   cannot be closed here (build dir gone, receipt
  absent      the view dir is not on this host                          sha mismatch, stub provenance): re-export or restage

    backfill_views.py --config kit_wave.json [--die D ...] [--apply] [--json]       (no --apply: count only, change nothing)
Run it on every gen host (backfill_views.py --fleet drives that over ssh); flip hard_landing.VIEW_CLOSED_MODE to 'strict' when open = 0.
"""
import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "die_plan"))
SSH = ["ssh", "-n", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", "-o", "ControlPath=none"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def plan_views(plan, src):
    """[(lef string, resolved view dir or None)] for every child lef the plan names"""
    import kit_input_preflight as KP
    out = []
    for lef in KP.plan_lefs(plan):
        cands = [lef] if os.path.isabs(lef) else [os.path.join(r, lef) for r in (src, os.path.dirname(plan)) if r]
        hit = next((c for c in cands if os.path.isfile(c)), None)
        out.append((lef, os.path.dirname(hit) if hit else None))
    return out


def closed_state(vd):
    """-> (is_closed, needs_landing)"""
    import kit_input_preflight as KP
    vd = Path(vd)
    landing = bool(KP.LANDING_RE.search(vd.name)) or (vd / "landing_evidence").is_dir()
    ok = (vd / "signoff.json").is_file() and (not landing or (vd / "landing_evidence" / "manifest.json").is_file())
    return ok, landing


def close_one(vd, apply):
    """-> (status, why): plain | already | closed | would | open | nonlanding
    plain = no provenance.json (a library / third-party macro LEF: nothing to close); open = a hard landing child that stays unclosed
    (blocks strict mode); nonlanding = a non-landing core view whose receipt copy cannot be made (informational, gen never reads it)"""
    import hard_landing as HL
    vd = Path(vd)
    if not (vd / "provenance.json").is_file():
        return "plain", ""
    ok, landing = closed_state(vd)
    if ok:
        return "already", ""
    try:
        prov = json.loads((vd / "provenance.json").read_text())
    except (OSError, ValueError) as e:
        return "open", f"provenance.json unreadable: {e}"
    exp = prov.get("export") or {}
    so, kit = exp.get("signoff"), prov.get("src")
    mod = (prov.get("kit") or {}).get("module") or next((p.stem for p in vd.glob("*.lef")), None)
    land = os.path.isfile(os.path.join(kit or "/", "land_slots.json")) and os.path.isfile(os.path.join(kit or "/", "face_guard.json"))
    landing = landing or land
    bad = "open" if landing else "nonlanding"
    if not so:
        return bad, "stub provenance (no export.signoff): needs a signed export"
    if not os.path.isfile(vd / "signoff.json") and not os.path.isfile(so):
        return bad, f"receipt {so} is gone: re-export"
    src_so = str(vd / "signoff.json") if os.path.isfile(vd / "signoff.json") else so
    if sha(src_so) != exp.get("signoff_sha256"):
        return bad, "signoff.json differs from the exported receipt sha: re-export"
    if landing and not land:
        return "open", f"landing child but build dir {kit} no longer holds face_guard.json/land_slots.json: re-export"
    if not apply:
        return "would", "can be closed in place (dry run)"
    _c, problems = HL.close_view(vd, kit or "/nonexistent", mod, src_so)
    if problems:
        return bad, problems[0][:300]
    return ("closed", "") if closed_state(vd)[0] else (bad, "close_view left it unclosed")


def run(cfg, dies, apply):
    res = dict(host=socket.gethostname(), closed=0, would=0, already=0, open=0, absent=0, plain=0, nonlanding=0, no_plan=[], items=[])
    seen = set()
    for die in dies:
        d = cfg["dies"][die]
        plan, src = str(d.get("plan") or ""), str(d.get("src") or "")
        if not plan or not os.path.isfile(plan):
            res["no_plan"].append(die)
            continue
        for lef, vd in plan_views(plan, src):
            if vd in seen and vd:
                continue
            seen.add(vd or lef)
            if vd is None:
                res["absent"] += 1
                res["items"].append(dict(die=die, view=lef, status="absent", why="view dir not on this host"))
                continue
            st, why = close_one(vd, apply)
            res[st] += 1
            if st not in ("already", "plain"):
                res["items"].append(dict(die=die, view=vd, status=st, why=why))
    return res


def propagate(tot, log=print):
    """a view closed on one host is closed on every host that holds the same view dir but lost its build dir: copy signoff.json and
    landing_evidence/ from a host where it is closed (tar over ssh, existing files kept).  -> number of (host, view) copies"""
    import shlex
    closed_on = {}
    for h, j in tot["hosts"].items():
        for it in j.get("items", []):
            if it["status"] == "closed":
                closed_on.setdefault(it["view"], h)
    n = 0
    for h, j in tot["hosts"].items():
        for it in j.get("items", []):
            vd, donor = it["view"], closed_on.get(it["view"])
            if it["status"] != "open" or not donor or donor == h:
                continue
            q = shlex.quote(vd)
            pipe = (f"{' '.join(SSH)} {donor} 'cd {q} && tar -cf - signoff.json $(test -d landing_evidence && echo landing_evidence)' | "
                    f"{' '.join(SSH).replace('-n ', '')} {h} 'cd {q} && tar -xf - --skip-old-files'")
            r = subprocess.run(["bash", "-c", "set -o pipefail; " + pipe], capture_output=True, text=True, timeout=900)
            log(f"BACKFILL copy {donor}:{vd} -> {h} rc={r.returncode}")
            n += r.returncode == 0
    return n


def fleet(cfg_path, dies, apply, hosts):
    """copy the three tools + config to each host, run there, merge counts"""
    here, dp = HERE, HERE.parent / "die_plan"
    tot = dict(closed=0, would=0, already=0, open=0, absent=0, plain=0, nonlanding=0, hosts={})
    for h in hosts:
        stage = "/tmp/kp_backfill"
        subprocess.run(SSH + [h, f"mkdir -p {stage}/autopilot {stage}/die_plan"], capture_output=True, timeout=60)
        for f, d in (("backfill_views.py", "autopilot"), ("kit_input_preflight.py", "autopilot")):
            subprocess.run(["scp", "-q", "-o", "ControlPath=none", str(here / f), f"{h}:{stage}/{d}/{f}"], capture_output=True, timeout=60)
        subprocess.run(["scp", "-q", "-o", "ControlPath=none", str(dp / "hard_landing.py"), f"{h}:{stage}/die_plan/hard_landing.py"], capture_output=True, timeout=60)
        subprocess.run(["scp", "-q", "-o", "ControlPath=none", cfg_path, f"{h}:{stage}/kit_wave.json"], capture_output=True, timeout=60)
        cmd = f"python3 -I {stage}/autopilot/backfill_views.py --config {stage}/kit_wave.json --json " + " ".join(f"--die {x}" for x in dies) + (" --apply" if apply else "")
        r = subprocess.run(SSH + [h, cmd], capture_output=True, text=True, timeout=1800)
        try:
            j = json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            tot["hosts"][h] = dict(error=(r.stderr or r.stdout)[-300:])
            continue
        tot["hosts"][h] = j
        for k in ("closed", "would", "already", "open", "absent", "plain", "nonlanding"):
            tot[k] += j[k]
    if apply:
        tot["propagated"] = propagate(tot, lambda m: print(m, file=sys.stderr))
    return tot


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=os.path.expanduser("~/coord/autopilot/kit_wave.json"))
    ap.add_argument("--die", action="append", default=[])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fleet", nargs="*", help="drive the run over ssh on these hosts (default: every gen host in the config)")
    a = ap.parse_args(argv)
    cfg = json.load(open(a.config))
    dies = a.die or sorted(cfg["dies"])
    if a.fleet is not None:
        hosts = a.fleet or sorted({h for d in cfg["dies"].values() for h in (d.get("gen_hosts") or cfg.get("gen_hosts") or [])})
        tot = fleet(a.config, dies, a.apply, hosts)
        print(json.dumps(tot) if a.json else "BACKFILL " + " ".join(f"{k}={tot[k]}" for k in ("closed", "would", "already", "open", "absent", "plain", "nonlanding")))
        return 0 if tot["open"] == 0 and not any("error" in v for v in tot["hosts"].values()) else 1
    res = run(cfg, dies, a.apply)
    if a.json:
        print(json.dumps(res))
    else:
        print(f"BACKFILL {res['host']}: closed={res['closed']} would={res['would']} already={res['already']} open={res['open']} nonlanding={res['nonlanding']} plain={res['plain']} absent={res['absent']} no_plan={res['no_plan']}")
        for it in res["items"]:
            print(f"  {it['status']:7} {it['die']} {it['view']}: {it['why']}")
    return 0 if res["open"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
