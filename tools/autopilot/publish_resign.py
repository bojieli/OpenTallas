#!/usr/bin/env python3
"""PUBLISH-RESIGN (KITPACK-CLOSE-1115, COORD r221 / FABLE-FLOWCLASS-KITPACK-2030 F4): lane-built cores are PUBLISHED at sign-off,
not left as host:dir rows.  Each lanes/AUTO-RESIGN.tsv row (die, name, host, dir with signoff/signoff.json, ...) is exported
with export_view.py on its host into a CLOSED view (signoff copy + landing_evidence, no pointers into the build dir) and merged
into the hub sidecar prov_view_sources_auto.json through counted_child_views.publish_manifest, the path the wave already
overlays at read time.  Rows whose host is terminated (epyc4/5/6) are dropped, never published.

    publish_resign.py --registry ~/coord/lanes/AUTO-RESIGN.tsv --row 56 --publish ~/coord/autopilot/prov_view_sources_auto.json
    publish_resign.py --registry ... --name s81p_slice_station__t51_ot_s81_station_t51_native_w --dry
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import counted_child_views as CV  # noqa: E402

RETIRED_HOSTS = ("epyc4", "epyc5", "epyc6")


def parse_registry(text):
    """[(line number, die, name, host, dir)] of every data row"""
    rows = []
    for n, ln in enumerate(text.splitlines(), 1):
        if not ln.strip() or ln.startswith("#"):
            continue
        f = ln.split("\t")
        if len(f) >= 4:
            rows.append((n, f[0], f[1], f[2], f[3]))
    return rows


def select(rows, lines=(), names=()):
    """-> (publishable rows, dropped [(row, why)]): candidates that name a terminated host or an unresolved glob are dropped"""
    keep, drop = [], []
    for r in rows:
        if (lines or names) and r[0] not in lines and r[1:3][1] not in names:
            continue
        if r[3] in RETIRED_HOSTS:
            drop.append((r, f"host {r[3]} is terminated"))
        elif any(c in r[4] for c in "*?["):
            drop.append((r, "dir is a glob: name the exact directory"))
        else:
            keep.append(r)
    return keep, drop


def record(row):
    _n, _die, _name, host, d = row
    d = d.rstrip("/")
    return dict(host=host, signoff=f"{d}/signoff/signoff.json", kit=d, base=None, db=None, flow_tag=None)


def build_manifest(rows, export=CV.export_one, log=print):
    """{die: manifest} in the shape counted_child_views.publish_manifest takes"""
    mans = {}
    for row in rows:
        die, name = row[1], row[2]
        c = export(die, name, record(row), log)
        if not c:
            log(f"PUBLISH-RESIGN FAIL {die} {name} {row[3]}:{row[4]}")
            continue
        man = mans.setdefault(die, dict(schema="opentallas.kw32.counted_child_views.v1", die=die,
                                        generated=time.strftime("%Y-%m-%d %H:%M %Z"), plan_sha=None, modules={}, missing={}))
        man["modules"].setdefault(c["module"], dict(types=[], plan_pin_hashes=[], candidates=[]))["candidates"].append(c)
    return mans


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--registry", default=os.path.expanduser("~/coord/lanes/AUTO-RESIGN.tsv"))
    ap.add_argument("--row", type=int, nargs="*", default=[], help="registry line numbers")
    ap.add_argument("--name", nargs="*", default=[])
    ap.add_argument("--publish", help="hub sidecar prov_view_sources_auto.json")
    ap.add_argument("--dry", action="store_true", help="list what would be exported")
    a = ap.parse_args(argv)
    if not (a.row or a.name):
        ap.error("name --row or --name (publishing every row at once is not allowed)")
    keep, drop = select(parse_registry(Path(a.registry).read_text()), set(a.row), set(a.name))
    for r, why in drop:
        print(f"PUBLISH-RESIGN DROP row {r[0]} {r[2]} {r[3]}:{r[4]}: {why}")
    if a.dry:
        for r in keep:
            print(f"PUBLISH-RESIGN WOULD EXPORT row {r[0]} {r[1]} {r[2]} {r[3]}:{r[4]}")
        return 0
    mans = build_manifest(keep, log=lambda s: print(s, file=sys.stderr))
    if not mans:
        return 1
    for die, man in sorted(mans.items()):
        done = CV.publish_manifest(a.publish, man) if a.publish else []
        print(f"PUBLISH-RESIGN {die}: exported {sorted(man['modules'])}; published {done}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
