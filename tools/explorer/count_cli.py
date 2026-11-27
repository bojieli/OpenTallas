#!/usr/bin/env python3
"""count_cli.py -- c16 (COORD 11-27), REPORT ONLY: viewable against signed (any plan) and current, from the Explorer store, without the web login.

  python3 -I count_cli.py --pid <explorer service pid>    # reads the service environment (EXPLORER_STATE, OT_SIGNED_STORE, LV_STORE ...) and runs
                                                          # server.archive_summary() in-process; writes nothing.  Run it from the service's tools/explorer dir.
"""
import argparse
import importlib.util
import json
import os
import sys


def summarize(d):
    t = (d.get("any_plan") or {}).get("total") or {}
    nv = sorted(d.get("any_plan_not_viewable") or [])
    na = d.get("any_plan_not_archived") or []
    line = (f"EXPLORER viewable {t.get('viewable')}/{t.get('signed')} any-plan, {t.get('current_viewable')}/{t.get('current')} current; "
            f"archived {t.get('archived')}/{t.get('signed')}; not viewable {len(nv)}; not archived {len(na)}")
    return line, nv


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, required=True)
    a = ap.parse_args(argv)
    env = dict(l.split("=", 1) for l in open(f"/proc/{a.pid}/environ").read().split("\0") if "=" in l)
    os.environ.update({k: v for k, v in env.items() if k.startswith(("EXPLORER", "FLEET", "OT_", "LV_", "DESIGN", "TOKEN", "DATAFLOW"))})
    sys.argv = ["server.py"]
    sp = importlib.util.spec_from_file_location("expl_server", os.path.join(os.getcwd(), "server.py"))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    line, nv = summarize(m.archive_summary())
    print(line)
    for n in nv:
        print("  not viewable:", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
