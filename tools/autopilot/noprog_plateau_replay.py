#!/usr/bin/env python3
"""noprog_plateau_replay.py [--hours 24] [--wd PATH]: STAGE-PLATEAU dry run.  Replays DRT-PLATEAU and HOLD-STALL against the kit logs this host's noprog scans
watched in the last HOURS h (state.json samples give line-count -> time anchors) and prints one JSON object per kit the rules WOULD have stopped.  Read-only."""
import argparse, glob, importlib.util, json, os, re, sys, time

ap = argparse.ArgumentParser()
ap.add_argument("--hours", type=float, default=24)
ap.add_argument("--wd", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "noprog_watchdog.py"))
ap.add_argument("--state", default=os.path.expanduser("~/.local/state/noprog/state.json"))
a = ap.parse_args()
spec = importlib.util.spec_from_file_location("npw", a.wd)
w = importlib.util.module_from_spec(spec)
sys.modules["npw"] = w
spec.loader.exec_module(w)
now = time.time()
horizon = now - a.hours * 3600
st = json.load(open(a.state))
host = os.environ.get("NOPROG_HOST") or os.uname().nodename
seen = set()


def real(log):
    for c in (log, log.replace(".tmp.log", ".log")):
        if os.path.isfile(c):
            return c
    return None


def birth(p):
    try:
        return os.stat(p).st_mtime if False else (w.birth(p) or os.stat(p).st_ctime)
    except OSError:
        return None


def anchors_at(lbirth, samples, upto_i, nlines, mt):
    an = [(lbirth, 0)]
    for s in samples[:upto_i + 1]:
        if s[0] > an[-1][0] and s[1] >= an[-1][1]:
            an.append((s[0], s[1]))
    return an


def first_sample_t(samples):
    return samples[0][0] if samples else None


for key, job in st["jobs"].items():
    cid, _, log = key.partition("|")
    samples = job.get("samples") or []
    if not samples or samples[-1][0] < horizon or log in seen:
        continue
    seen.add(log)
    p = real(log)
    if not p:
        continue
    name = os.path.basename(p)
    kind = w.stage_kind(p)
    ident_noname = os.path.dirname(p)
    try:
        text = w.read_text(p)
        mt = os.stat(p).st_mtime
    except OSError:
        continue
    lbirth = min(birth(p) or samples[0][0], samples[0][0])
    lines = text.splitlines()
    out = None
    if kind == "drt":
        vals = w.drt_totals(text)
        idxs = [i for i, ln in enumerate(lines) if w.DRT_ITER.search(ln)]
        an_full = anchors_at(lbirth, samples, len(samples), len(lines), mt) + [(max(mt, samples[-1][0] + 1), len(lines))]
        an_full = sorted(set(an_full))
        for n in range(1, len(vals) + 1):
            ev = w.drt_plateau_evidence(vals[:n])
            if ev:
                ft = w.interp_time(idxs[n - 1], an_full)
                after = vals[n - 1:]
                out = {"rule": "DRT-PLATEAU", "fire_iter": n - 1, "fire_t": ft, "stage_age_h": round((ft - lbirth) / 3600, 1), "evidence": ev,
                       "at_fire": vals[n - 1], "final": vals[-1], "min_after": min(after), "iters_total": len(vals), "series_tail": vals[-8:]}
                res_dir = os.path.dirname(p).replace("/logs/", "/results/")
                out["route_done"] = bool(glob.glob(res_dir + "/5_2_route.odb") or glob.glob(res_dir + "/5_route.odb"))
                out["drc"] = w.latest_drc_summary(p)[:300]
                break
    elif name.startswith("pregrt_ff_hold"):
        ser_final = w.extract("other", text)
        for i, s in enumerate(samples):
            nl = min(int(s[1]), len(lines))
            sub = "\n".join(lines[:nl])
            res = w.extract("other", sub)
            if res.get("name") != "repair_TNS":
                continue
            an = anchors_at(lbirth, samples, i, nl, mt)
            an.append((max(s[0], an[-1][0] + 1), nl)) if an[-1][1] != nl else None
            ex = s[0] - samples[0][0] >= 2 * 3600
            v, why, detail = w.judge(res, an, s[0], window=2 * 3600, exact=ex, zero_needs_growth=True)
            ev = w.hold_stall_evidence(name, res, v, why, detail, an, s[0], 2 * 3600 if ex else 2.5 * 3600)
            if ev:
                fin = ser_final["series"]
                tail = [x[1] for x in fin][-6:]
                out = {"rule": "HOLD-STALL", "fire_t": s[0], "stage_age_h": round((s[0] - lbirth) / 3600, 1), "evidence": ev,
                       "at_fire": res["series"][-1][1], "final": fin[-1][1] if fin else None, "min_after": min([x[1] for x in fin] or [None]) if fin else None,
                       "tail": tail, "route_done": False, "converged_final": bool(fin and fin[-1][1] <= 0)}
                break
    if out:
        ex = w.unsignable_exempt(ident_noname, "", kind) or ("re-sign" if re.search(r"(?i)re-?sign", ident_noname) else "")
        out.update(host=host, log=p, exempt=ex, fire_in_24h=out["fire_t"] >= horizon, still_writing=now - mt < 3600, log_age_h=round((now - mt) / 3600, 1),
                   over_3h=out["stage_age_h"] > 3.0)
        print(json.dumps(out, sort_keys=True))
