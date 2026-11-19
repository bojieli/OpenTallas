#!/usr/bin/env python3
"""publish_apply.py -- LATENCY-R 11-18 (COORD ruling 11-18, OWNER "remove plan validations, build all types directly from the latest plan").

Measured 11-17 (lanes/LATENCY-1117.md): a plan event spent 1.5-3 h between "bind done" and "first kit": serial PRE/G0/R8/cohort/CB16 checks, a 13-92 min
publish gate (static then dry gen), a separate apply step that waited on a person, gate-label misses, then a tick.  This tool is the one step a lane runs
the moment its tree is PUBLISHED:

  apply     optimistic atomic apply (apply_reviewed_tree_marker optimistic=True: publish gate, source guard and smoke are ADVISORY, no pilot hold, the
            event joins gate_events_extra in the same write), commit through coord-commit.sh, then the publish gate is started in the background as a
            REPORT (its record lists advisory findings; it never blocks), and one post names the warnings.  The next wave pass launches every type.
  bind-fail strict bind / LATCHECK (still running in parallel, the only blocking plan checks) failed: hold ONLY the types it names (explicit --types,
            or the plan item names found in --log), released by result:<owner>:<id>.  Running rows of held types are cancelled by the wave (kit_wave
            hold_records with cancel_running, WAVE-FLOW-R2).

    publish_apply.py apply --candidate JSON --expect-source OLD_TREE --expect-event OLD_EVENT --lane LANE [--coord ~/coord] [--no-gate]
    publish_apply.py bind-fail --die DIE --lane LANE --id ID (--types t1,t2 | --log FILE) [--reason TEXT] [--coord ~/coord] [--dry]
    publish_apply.py derive-asbuilt --bind BIND_DIR --asbuilt KIT_ASBUILT --tree TREE --out NEW_ASBUILT
  apply first runs kit_topology.bind_matches on the candidate on a candidate host (FABLE-FLOW-1400): a bind that does not match refuses (rc 4).
  bind-fail writes dies.<die>.bind_fail {id, bind, items} first: the wave books those rows FAIL class BIND-FAIL until the bind changes.
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import apply_reviewed_tree_marker as A  # noqa: E402
import flow_guard as FG  # noqa: E402
import hold_records as HR  # noqa: E402


def post(C, lane, text, run=subprocess.run):
    return run(["bash", str(Path(C) / "bin/post.sh"), lane, text], capture_output=True, text=True, timeout=600)


def gate_argv(C, cand_path, tree, event):
    """the advisory publish gate after the apply: the projection re-applies the SAME tree onto the live config, so it expects the new source/event"""
    return [sys.executable, "-I", str(HERE / "publish_gate.py"), "run", "--candidate", str(cand_path), "--expect-source", tree,
            "--expect-event", str(event), "--coord", str(C), "--commit"]

# FABLE-FLOW-1400 (1): QC sat 3.2 h on 56 BIND-STALE rows because the candidate's kit_rtl.asbuilt named the N2BBR clock table while its bind was made
# on N4DBQ.  apply now runs kit_topology.bind_matches (the wave's own bind preflight) on the candidate, on a host that holds the tree, BEFORE the switch.
PROBE_CAND = r"""
import json, os, sys
from pathlib import Path
a = json.loads(sys.argv[1])
try:
    if a.get("scope"):
        os.environ["OT_NATIVE_RESET_SCOPE"] = a["scope"]
    sys.path.insert(0, str(Path(a["src"]) / "tools" / "die_plan"))
    import kit_topology as kt
    raw = json.loads(Path(a["plan"]).read_text())
    ab = a.get("asbuilt") or None
    types = [t for t in (raw.get("partition_types") or {}) if kt.has_topology(raw, t, ab)]
    stale = [t for t in types if not kt.bind_matches(raw, t, a["bind_out"], ab, a["plan"])]
    diff = {}
    if stale:
        old = json.loads((Path(a["bind_out"]) / "native_topology.json").read_text())
        new = kt.native_contract(raw, ab, a["plan"])
        diff = {k: [str(old.get(k))[:16], str(new.get(k))[:16]] for k in ("clock_table_sha256", "reset", "transport", "ownership") if old.get(k) != new.get(k)}
    out = {"checked": len(types), "stale": stale, "diff": diff}
except Exception as e:
    out = {"error": (type(e).__name__ + ": " + str(e))[:300]}
print("AP_JSON " + json.dumps(out))
"""


def candidate_bind_args(obj):
    """-> (probe args, hosts) of a bind-mode candidate, (None, []) when the candidate builds no bind"""
    m = obj.get("marker", obj)
    mc = m.get("config") or {}
    kr = mc.get("kit_rtl") or {}
    if kr.get("mode") != "bind" or not kr.get("bind_out"):
        return None, []
    env = dict(m.get("die_gen_env") or {})
    return (dict(src=m["tree"], plan=m["plan"], bind_out=kr["bind_out"], asbuilt=kr.get("asbuilt") or "", scope=env.get("OT_NATIVE_RESET_SCOPE") or ""),
            list(mc.get("gen_hosts") or m.get("hosts") or []))


def bind_check(obj, run=subprocess.run):
    """-> (ok, text).  ok None = not a bind candidate; the probe runs on the first candidate host that answers"""
    args, hosts = candidate_bind_args(obj)
    if not args:
        return None, "no bind"
    err = []
    for h in hosts:
        p = run(["ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=15", h,
                 "python3 -I -c " + shlex.quote(PROBE_CAND) + " " + shlex.quote(json.dumps(args))], capture_output=True, text=True, timeout=900)
        line = [x for x in (p.stdout or "").splitlines() if x.startswith("AP_JSON ")]
        if not line:
            err.append(f"{h}: rc {p.returncode} {(p.stderr or '')[-160:]}")
            continue
        r = json.loads(line[-1][8:])
        if r.get("error"):
            return False, f"bind check on {h} could not run: {r['error']}"
        if r["stale"]:
            return False, (f"bind {args['bind_out']} does not match the candidate on {len(r['stale'])}/{r['checked']} types ({h}): differs {r['diff']}; "
                           f"e.g. {', '.join(r['stale'][:6])}.  A clock_table_sha256-only difference = the asbuilt names other tables than the bind used: "
                           f"derive it from the bind (publish_apply.py derive-asbuilt --bind {args['bind_out']} --asbuilt {args['asbuilt']} --tree {args['src']} --out NEW)")
        return True, f"bind matches the candidate on {r['checked']}/{r['checked']} types ({h})"
    return False, "bind check: no candidate host answered: " + "; ".join(err)[:400]


def tree_rel(path, tree_roots):
    """an absolute file path inside one of the tree roots (or any tree: from physical/ / tools/ / rtl/ on) -> tree-relative"""
    for t in tree_roots:
        t = t.rstrip("/") + "/"
        if path.startswith(t):
            return path[len(t):]
    for marker in ("/physical/", "/tools/", "/rtl/"):
        if marker in path:
            return path[path.index(marker) + 1:]
    raise ValueError(f"{path}: not inside a source tree")


def derive_asbuilt(bind, asbuilt, tree, out):
    """FABLE-FLOW-1400 (1): the kit asbuilt the bind was ACTUALLY made with: asbuilt's clock_landing_table / land_r8 / land_r8_extra replaced by the
    sidecar / r8 / extra tables bind/INPUTS_ISOLATED.json records (tree-relative, each sha-checked in tree).  Never hand-edited.  -> the written dict"""
    import hashlib
    iso = json.loads((Path(bind) / "INPUTS_ISOLATED.json").read_text())
    a = json.loads(Path(asbuilt).read_text())

    def rel_checked(pth, sha):
        r = tree_rel(pth, [tree])
        got = hashlib.sha256((Path(tree) / r).read_bytes()).hexdigest()
        if sha and got != sha:
            raise SystemExit(f"DERIVE refuse: {r} in {tree} is {got[:12]}, the bind used {str(sha)[:12]}")
        return r
    if iso.get("sidecar"):
        a["clock_landing_table"] = rel_checked(iso["sidecar"], iso.get("sidecar_sha256"))
    if iso.get("r8"):
        a["land_r8"] = rel_checked(iso["r8"], iso.get("r8_sha256"))
    if iso.get("extra_tables"):
        a["land_r8_extra"] = [rel_checked(x["copy"], x.get("sha256")) for x in iso["extra_tables"]]
    a["derived_from_bind"] = {"bind": str(bind), "tool": "publish_apply.py derive-asbuilt (FABLE-FLOW-1400)"}
    tmp = Path(out).with_suffix(".tmp")
    tmp.write_text(json.dumps(a, indent=1) + "\n")
    os.replace(tmp, out)
    return a


def cmd_derive(a):
    d = derive_asbuilt(a.bind, a.asbuilt, a.tree, a.out)
    print(json.dumps({k: d.get(k) for k in ("clock_landing_table", "land_r8", "land_r8_extra")}, indent=1))
    print(f"DERIVED {a.out}: add it to the tree (live-tree pack), point kit_rtl.asbuilt at it; the bind receipt's asbuilt_sha256 names the asbuilt the bind was run with")
    return 0


def cmd_apply(a, run=subprocess.run, apply_fn=None, commit_fn=None):
    C = Path(a.coord)
    obj = json.loads(Path(a.candidate).read_text())
    obj["optimistic"] = True
    obj["_path"] = a.candidate
    if not getattr(a, "skip_bind_check", False):
        ok, txt = (getattr(a, "bind_check_fn", None) or bind_check)(obj, run=run)
        print(f"BIND-CHECK {txt}", flush=True)
        if ok is False:
            print("APPLY REFUSED: the candidate's bind does not match it (the wave would hold every type BIND-STALE); fix the candidate or pass --skip-bind-check")
            return 4
    t0 = time.time()
    res = (apply_fn or A.apply_marker)(C, obj, a.expect_source, a.expect_event, pilot_item=a.pilot_item, optimistic=True)
    res["commit"] = (commit_fn or A.commit_apply)(C, res)
    res["apply_s"] = round(time.time() - t0, 1)
    gate = "off"
    if not a.no_gate:
        # the gate's projection must see the candidate as optimistic too (guard/smoke advisory); written next to the receipt
        gc = Path(res["receipt"]).with_suffix(".gate_candidate.json")
        gc.write_text(json.dumps(dict({k: v for k, v in obj.items() if k != "_path"}, optimistic=True), indent=1))
        unit = "pubgate-%s-%d" % (res["applied"], int(time.time()))
        r = run(["systemd-run", "--user", "--unit", unit, "--collect", "--quiet", "--nice=10", *gate_argv(C, gc, (obj.get("marker") or obj)["tree"], res.get("event"))],
                capture_output=True, text=True, timeout=120)
        gate = unit if r.returncode == 0 else "not started (rc %d: %s)" % (r.returncode, (r.stderr or r.stdout)[-160:])
    res["advisory_gate"] = gate
    w = res.get("warnings") or []
    post(C, a.lane, f"APPLIED-OPTIMISTIC [{a.lane} -> COORD; cc WAVE-FLOW-R2] {res['applied']} event {res.get('event')} tree {res.get('source')}: every type launches on the "
                    f"next wave pass (no pilot); apply {res['apply_s']} s; advisory gate {gate}; gen_hosts {','.join(res.get('gen_hosts') or [])}; "
                    f"{len(w)} advisory warning(s){': ' + ' | '.join(w)[:900] if w else ''}. Strict bind + LATCHECK stay blocking: on a failure run "
                    f"publish_apply.py bind-fail (holds only the named types).", run=run)
    print(json.dumps(res))
    return 0


def item_names(d):
    """every item name the die's current plan lists (hold_event_items of its plan sha, else the union of all lists)"""
    hei = d.get("hold_event_items") or {}
    items = hei.get(d.get("plan_sha256")) or [i for v in hei.values() for i in v]
    return sorted(set(items))


def types_from_log(text, items):
    """plan item names that appear as whole words in a bind/LATCHECK failure log, longest first (a__b before a)"""
    found = []
    for it in sorted(items, key=len, reverse=True):
        if re.search(r"(?<![A-Za-z0-9_])" + re.escape(it) + r"(?![A-Za-z0-9_])", text):
            if not any(it in f for f in found):
                found.append(it)
    return sorted(found)


def bind_fail_record(d, types, lane, ident, reason):
    return {"id": f"bindfail-{ident}", "plan_sha": d.get("plan_sha256"), "items": list(types), "owner": lane, "carry": True, "cancel_running": True,
            "reason": f"LATENCY-R optimistic launch: strict bind/LATCHECK failed on these types only ({reason})"[:900],
            "release": [f"result:{lane}:{ident}"]}


def bind_fail_records(cfg, die, types, lane, ident, now=None):
    """one bind_fail record per bind the named types build on now (item kit_rtl over die kit_rtl): {id, bind, items, at, lane}"""
    import kit_wave as KW
    by = {}
    for t in types:
        b = KW.item_bind_out(cfg, die, t)
        if b:
            by.setdefault(b, []).append(t)
    at = time.time() if now is None else now
    return [{"id": f"bindfail-{ident}", "bind": b, "items": sorted(ts), "at": at, "lane": lane} for b, ts in sorted(by.items())]


def owner_lane_of(d, fallback):
    if d.get("die_owner"):
        return str(d["die_owner"])
    m = re.search(r"\(([A-Z][A-Z0-9-]+)\)", str(d.get("owner_lane") or ""))
    return m.group(1) if m else fallback


SSH = ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=10"]


def running_rows(state, die, types):
    """the wave rows of DIE whose type is named and whose kit is running (RUNNING / LAUNCHING unit, or an ENQUEUED job that is running / queued)"""
    out = []
    for r in (state.get("items") or {}).values():
        if r.get("die") != die or r.get("item") not in types:
            continue
        if r.get("status") in ("RUNNING", "LAUNCHING") or (r.get("status") == "ENQUEUED" and r.get("q_status") in ("RUNNING", "QUEUED", "STARTING", "WAIT-GEOM")):
            out.append(r)
    return out


def cancel_running_kits(rows, run=subprocess.run):
    """OWNER r705 (1): cancel the running kits of the named types by EXACT unit: the ot-heavy scope(s) of the attempt on its host (resolved with a dry run of ot-heavy-stop
    --match <attempt dir>, then stopped one by one with --unit) and the wave's own hub unit.  -> [(item, where, unit)]"""
    done = []
    for r in rows:
        host, _, kit = str(r.get("kit") or "").partition(":")
        adir = kit.rsplit("/gen/", 1)[0] if kit else ""
        if host and adir:
            q = run([*SSH, host, f"ot-heavy-stop --match {adir} --dry-run 2>&1 | grep -o 'oth-[A-Za-z0-9-]*' | sort -u"], capture_output=True, text=True, timeout=120)
            for u in [x for x in (q.stdout or "").split() if x.startswith("oth-")]:
                run([*SSH, host, f"ot-heavy-stop --unit {u}"], capture_output=True, text=True, timeout=120)
                done.append((r.get("item"), host, u))
        if r.get("unit") and r.get("status") in ("RUNNING", "LAUNCHING"):
            run(["systemctl", "--user", "stop", str(r["unit"])], capture_output=True, text=True, timeout=120)
            done.append((r.get("item"), "hub", str(r["unit"])))
    return done


def cmd_bind_fail(a, run=subprocess.run):
    C = Path(a.coord)
    cfg = json.loads((C / "autopilot/kit_wave.json").read_text())
    d = cfg["dies"][a.die]
    items = item_names(d)
    types = [t for t in (a.types or "").split(",") if t] or types_from_log(Path(a.log).read_text(errors="replace") if a.log else "", items)
    if not types:
        print("BIND-FAIL: no plan type named in the failure; nothing held (hold the die by hand if the failure is die-wide)")
        return 2
    if FG.stops_off_die(cfg, a.die):
        # OWNER r705 (1): under stops_off a bind / LATCHECK failure holds NOTHING: the running kits of the named types are cancelled by exact unit and ONE line names the owner lane
        owner = owner_lane_of(d, a.lane)
        st = {}
        try:
            st = json.loads((C / "autopilot/kit_wave_state.json").read_text())
        except (OSError, ValueError):
            pass
        rows = running_rows(st, a.die, set(types))
        # FABLE-FLOW-1400 (3): the cancelled rows were read as OOM and resubmitted at x1.5 memory on the failed bind (QC cbx_q10).  A bind_fail
        # record (bind id + the bind each type builds on) is written FIRST: the wave books those rows FAIL class BIND-FAIL and launches the
        # types again only when their bind_out changes (kit_wave.bind_fail_active).
        recs = bind_fail_records(cfg, a.die, types, a.lane, a.id)
        if a.dry:
            print(json.dumps({"cancel": [(r.get("item"), r.get("unit"), r.get("kit")) for r in rows], "owner": owner, "bind_fail": recs}, indent=1))
            return 0
        if recs:
            patch = [{"op": "add", "path": f"/dies/{a.die}/bind_fail", "value": list(d.get("bind_fail") or []) + recs}] if not d.get("bind_fail") else \
                [{"op": "add", "path": f"/dies/{a.die}/bind_fail/-", "value": x} for x in recs]
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
                json.dump(patch, f)
            r = run([sys.executable, "-I", str(HERE / "kit_wave_edit.py"), "--coord", str(C), "--message",
                     f"{a.lane}: bind-fail {a.id} ({len(types)} types, class BIND-FAIL)", "--patch-file", f.name], capture_output=True, text=True, timeout=600)
            os.unlink(f.name)
            if r.returncode:
                print("BIND-FAIL: the bind_fail record was not written; nothing cancelled: " + (r.stdout + r.stderr)[-400:])
                return 1
        done = cancel_running_kits(rows, run=run)
        post(C, a.lane, f"BIND-FAIL-CANCEL [{a.lane} -> {owner}] {a.die}: strict bind/LATCHECK failed for {len(types)} type(s): {', '.join(types)[:600]}; cancelled {len(rows)} running "
                        f"kit(s) by exact unit ({len(done)} unit(s)); nothing is held (stops_off), the types relaunch on the next change", run=run)
        print(json.dumps({"cancelled": done, "owner": owner}))
        return 0
    rec = bind_fail_record(d, types, a.lane, a.id, a.reason or (a.log or "explicit types"))
    probe = json.loads(json.dumps(cfg))
    HR.add_record(probe, a.die, dict(rec))          # validation only: unknown item / lane / term -> ValueError, nothing written
    patch = [{"op": "add", "path": f"/dies/{a.die}/hold_records/-" if d.get("hold_records") else f"/dies/{a.die}/hold_records",
              "value": rec if d.get("hold_records") else [rec]}]
    if a.dry:
        print(json.dumps(patch, indent=1))
        return 0
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(patch, f)
    r = run([sys.executable, "-I", str(HERE / "kit_wave_edit.py"), "--message", f"{a.lane}: bind-fail hold {rec['id']} ({len(types)} types)", "--patch-file", f.name],
            capture_output=True, text=True, timeout=600)
    os.unlink(f.name)
    if r.returncode:
        print((r.stdout + r.stderr)[-600:])
        return 1
    post(C, a.lane, f"BIND-FAIL-HOLD [{a.lane} -> COORD; cc WAVE-FLOW-R2] {a.die}: held {len(types)} type(s) named by the strict bind/LATCHECK failure, every other "
                    f"type keeps building: {', '.join(types)[:900]}; release result:{a.lane}:{a.id}", run=run)
    print(json.dumps(rec))
    return 0


def main(argv=None):
    P = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = P.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("apply")
    p.add_argument("--candidate", required=True)
    p.add_argument("--expect-source", required=True)
    p.add_argument("--expect-event", required=True)
    p.add_argument("--lane", required=True)
    p.add_argument("--pilot-item")
    p.add_argument("--coord", default=os.path.expanduser("~/coord"))
    p.add_argument("--no-gate", action="store_true", help="do not start the advisory publish gate")
    p.add_argument("--skip-bind-check", action="store_true", help="apply although kit_topology.bind_matches says the bind does not match the candidate")
    dv = sp.add_parser("derive-asbuilt", help="write the kit asbuilt the bind was made with (tables from bind/INPUTS_ISOLATED.json)")
    dv.add_argument("--bind", required=True)
    dv.add_argument("--asbuilt", required=True)
    dv.add_argument("--tree", required=True)
    dv.add_argument("--out", required=True)
    b = sp.add_parser("bind-fail")
    b.add_argument("--die", required=True)
    b.add_argument("--lane", required=True)
    b.add_argument("--id", required=True)
    b.add_argument("--types", default="")
    b.add_argument("--log")
    b.add_argument("--reason", default="")
    b.add_argument("--coord", default=os.path.expanduser("~/coord"))
    b.add_argument("--dry", action="store_true")
    a = P.parse_args(argv)
    return cmd_apply(a) if a.cmd == "apply" else cmd_derive(a) if a.cmd == "derive-asbuilt" else cmd_bind_fail(a)


if __name__ == "__main__":
    sys.exit(main())
