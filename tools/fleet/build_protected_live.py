#!/usr/bin/env python3
"""build_protected_live (FLEET-OPS-R, COORD FABLE-FLOW-0700 (1)): the delete guard's protected list from LIVE structured references only.
Sources: kit_wave.json dies (CURRENT keys: every key whose name does not mark history -- prev / retired / superseded / history / old / note), the tree-switch markers
(same key rule), PROTECTED-DBS files.  NOT handoff prose or COORD-REVIEW-QUEUE.md (97 % of the old list; a refusal post renewed its own protection).
Running jobs, waiter command lines and units are NOT in the list: ot_delete_guard.refuse() checks the live process table at delete time.
usage: build_protected_live.py COORD_DIR OUT [MARKER_DIR ...]"""
import importlib.util, json, os, re, sys

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
                    paths_in(json.load(open(os.path.join(d, f))), out, canon)
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


def main(argv):
    coord, outp, markers = argv[1], argv[2], argv[3:] or [os.path.join(argv[1], "lanes/handoff"), os.path.join(argv[1], "state")]
    here = os.path.dirname(os.path.realpath(__file__))
    sp = importlib.util.spec_from_file_location("ot_delete_guard", os.path.join(here, "ot_delete_guard.py"))
    g = importlib.util.module_from_spec(sp); sp.loader.exec_module(g)
    s = build(coord, markers, g.canon)
    g.write_list(s, outp)
    print(len(s), "live protected roots ->", outp)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
