#!/usr/bin/env python3
"""build_protected_live (FLEET-OPS-R, COORD FABLE-FLOW-0700 (1)): the delete guard's protected list from LIVE structured references only.
Sources: kit_wave.json dies (CURRENT keys: every key whose name does not mark history -- prev / retired / superseded / history / old / note), the tree-switch markers
(same key rule), PROTECTED-DBS files.  NOT handoff prose or COORD-REVIEW-QUEUE.md (97 % of the old list; a refusal post renewed its own protection).
Running jobs, waiter command lines and units are NOT in the list: ot_delete_guard.refuse() checks the live process table at delete time.
usage: build_protected_live.py COORD_DIR OUT [MARKER_DIR ...]"""
import glob, importlib.util, json, os, re, sys, time

HIST = re.compile(r"(^|_)(prev|previous|retired|superseded|history|old|note|notes|rollback_hist)(_|$)", re.I)
RX = re.compile(r"/srv/opentallas-scratch[0-9]*/claude/[A-Za-z0-9._+/@=~-]+")


def paths_in(obj, out, canon):
    """add every scratch path in obj to out, skipping history keys"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if HIST.search(str(k)):
                continue
            paths_in(v, out, canon)
    elif isinstance(obj, list):
        for v in obj:
            paths_in(v, out, canon)
    elif isinstance(obj, str):
        for m in RX.finditer(obj):
            t = m.group().rstrip("/.-")
            if t.count("/") >= 5:
                out.add(canon(t))


def build(coord, markers=(), canon=os.path.normpath):
    out = set()
    try:
        cfg = json.load(open(os.path.join(coord, "autopilot/kit_wave.json")))
        paths_in(cfg.get("dies") or {}, out, canon)
    except (OSError, ValueError):
        raise SystemExit("kit_wave.json unreadable: refusing to build an empty list")
    for d in markers:
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if f.startswith("tree_switch_") and f.endswith(".json"):
                try:
                    mk = json.load(open(os.path.join(d, f)))
                    if isinstance(mk, dict) and str(mk.get("status") or "").upper().startswith("SUPERSEDED"):
                        continue                       # a marker its owner / COORD marked SUPERSEDED no longer protects anything (kept for history)
                    paths_in(mk, out, canon)
                except (OSError, ValueError):
                    pass
    for f in ("PROTECTED-DBS.txt", "lanes/PROTECTED-DBS.txt"):
        try:
            for l in open(os.path.join(coord, f)):
                l = l.split("#")[0].strip()
                if l.startswith("/srv/"):
                    out.add(canon(l))
        except OSError:
            pass
    return out


def prose_paths(files, out, canon, now=None, max_age_h=24.0, skip=("COORD-REVIEW-QUEUE.md",)):
    """(d) scratch paths quoted in the given handoff files changed in the last max_age_h, never COORD-REVIEW-QUEUE (it renews its own protection)"""
    now = now or time.time()
    for f in files:
        if os.path.basename(f) in skip or os.path.basename(f).startswith(("COORD", "CODEX")):
            continue
        try:
            if now - os.stat(f).st_mtime > max_age_h * 3600:
                continue
            for m in RX.finditer(open(f, errors="replace").read()):
                t = m.group().rstrip("/.-")
                if t.count("/") >= 5:
                    out.add(canon(t))
        except OSError:
            pass


def event_paths(coord, out, canon, now=None, max_age_h=72.0):
    """(b) bind / LATCHECK / G0 inputs of in-flight plan events: structured json that names them (tree checks, handoff json: plan events, candidates, receipts), recent only"""
    now = now or time.time()
    for pat in ("autopilot/tree_checks/*", "lanes/handoff/*.json", "autopilot/*candidate*.json", "autopilot/events/*.json"):
        for f in glob.glob(os.path.join(coord, pat)):
            try:
                if now - os.stat(f).st_mtime > max_age_h * 3600:
                    continue
                paths_in(json.load(open(f)), out, canon)
            except (OSError, ValueError):
                pass


def live_cmd_paths(out, canon, proc="/proc", unit_dirs=("~/.config/systemd/user",)):
    """(c) scratch paths named by running process command lines on this host (ot-run queue clients and waiters, jobs) and by user systemd unit files"""
    for c in glob.glob(os.path.join(proc, "[0-9]*", "cmdline")):
        try:
            t = open(c, "rb").read().replace(b"\0", b" ").decode("latin1")
        except OSError:
            continue
        for m in RX.finditer(t):
            x = m.group().rstrip("/.-")
            if x.count("/") >= 5:
                out.add(canon(x))
    for d in unit_dirs:
        for f in glob.glob(os.path.join(os.path.expanduser(d), "**", "*.service"), recursive=True) + glob.glob(os.path.join(os.path.expanduser(d), "*.timer")):
            try:
                for m in RX.finditer(open(f, errors="replace").read()):
                    x = m.group().rstrip("/.-")
                    if x.count("/") >= 5:
                        out.add(canon(x))
            except OSError:
                pass


def main(argv):
    coord, outp, markers = argv[1], argv[2], argv[3:] or [os.path.join(argv[1], "lanes/handoff"), os.path.join(argv[1], "state")]
    here = os.path.dirname(os.path.realpath(__file__))
    sp = importlib.util.spec_from_file_location("ot_delete_guard", os.path.join(here, "ot_delete_guard.py"))
    g = importlib.util.module_from_spec(sp); sp.loader.exec_module(g)
    s = build(coord, markers, g.canon)
    event_paths(coord, s, g.canon)
    prose_paths(glob.glob(os.path.join(coord, "lanes/handoff/*.md")), s, g.canon)
    live_cmd_paths(s, g.canon)
    g.write_list(s, outp)
    print(len(s), "live protected roots ->", outp)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
