#!/usr/bin/env python3
"""LAND_R8 IS DERIVED, NEVER CARRIED (QC-S28-A 11-12, COORD class fix for the s27 R8_STALE).

The as-built manifest's `land_r8` table (r8.py pads output, e.g. runtime/r8_sw2.json) is a FUNCTION of the bind:
r8.py pads on the bus_groups.json of a bind of (plan, manifest).  Any change to either one that moves a bound depth
(a plan qreg / station, a manifest substitute_inst that adds a stage) makes a carried table stale, and the strict bind
then fails R8_STALE.  s25 regenerated the table for its slw_fw_v3 x_ctl_i qreg (W5 ctl->fw 10 -> 11) but shipped it only
as a package (r8_sw2_s25.json.gz) staged by hand into kit trees; the branch trees (s25..s28) kept the old table
76cabd11016e, so a bind of the s27 tree's own manifest (ad39098247af, + DIE-QC-97 st_b substitute_inst) failed 30
R8_STALE on dvs_W5 (bound 11, table 10).  This tool makes the table a compose step:

    python3 tools/die_plan/land_r8_derive.py derive PLAN BUS_GROUPS --like TABLE --out TABLE [--json REPORT]
        re-derive the table with r8.py pads on BUS_GROUPS (a bind of the event's plan + manifest; a strict bind that
        failed R8_STALE still writes bus_groups.json, and the members' bound depths do not depend on the table), using
        the r8 options recorded in the current table (replica, bus, exempt, landed bundles).  Output is byte-identical to
        `r8.py pads` with those options; it is written atomically (temp file + rename, never in place, so hard-linked
        trees are not touched).  REPORT lists every member whose bound / pad / landed depth changed vs --like.
    python3 tools/die_plan/land_r8_derive.py check PLAN BUS_GROUPS --table TABLE [--json REPORT]
        exit 0 when TABLE is exactly the derivation (members equal), else exit 1 with the changed members: the compose
        gate that keeps a carried table out of an event.

COMPOSE RECIPE (every plan event / manifest change of a die that sets asbuilt.land_align = r8):
    1. strict bind of (plan, manifest) with the tree's current table  -> bind1/bus_groups.json (rc 0 or R8_STALE)
    2. land_r8_derive.py derive plan bind1/bus_groups.json --like <land_r8> --out <land_r8>
    3. if the table changed: strict bind again (rc 0 required); land_r8_derive.py check on its bus_groups (exit 0)
    4. commit the derived table in the event's tree (runtime file), not as a side package.
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r8 as R8  # noqa: E402

FIELDS = ("sink", "sink_part", "src_part", "sink_port", "sink_bits", "source", "asbuilt", "bound", "pad", "landed", "lane")


def options(table):
    """r8 options recorded in a table (r8.write_pads writes them), defaults = r8.py CLI defaults"""
    ld = table.get("landed") or {}
    return dict(replica=table.get("replica", "all"), bus=table.get("bus", "part"), exempt=list(table.get("exempt") or []),
                landed=list(ld.get("rx") or []), window=int(ld.get("window", 4)),
                stage_cycles=float(ld.get("stage_cycles", 0.5)), over=ld.get("over_margin", "keep"))


def derive(raw, bg, opts):
    """(table text, summary) = exactly what `r8.py pads` writes for these options"""
    R8.configure(opts["exempt"], opts["landed"], opts["window"], opts["stage_cycles"], opts["over"])
    with tempfile.TemporaryDirectory() as td:
        p, sm = R8.write_pads(raw, bg, td, opts["replica"], opts["bus"])
        return p.read_text(), sm


def pinned(text, pre, extra):
    """DIE-QC-102 deliberate R8 pin (pin_r8_v2.py) applied on a derivation: returns the pinned table text"""
    import pin_r8_v2 as P
    t = P.apply_pin(json.loads(text), P.load(pre), extra, log=lambda *a: None)
    return json.dumps(t, indent=1) + "\n"


def diff(old, new, limit=60):
    """member-level comparison of two tables: {added, removed, changed, lanes, equal}"""
    om = {m["id"]: m for m in old.get("members", [])}
    nm = {m["id"]: m for m in new.get("members", [])}
    changed, lanes = [], {}
    for i in sorted(set(om) & set(nm)):
        a, b = om[i], nm[i]
        d = {k: [a.get(k), b.get(k)] for k in FIELDS if a.get(k) != b.get(k)}
        if d:
            changed.append(dict(id=i, **d))
            for ln in {a.get("lane"), b.get("lane")}:
                lanes[str(ln)] = lanes.get(str(ln), 0) + 1
    added, removed = sorted(set(nm) - set(om)), sorted(set(om) - set(nm))
    # members equal as a multiset of their content (ids may swap between twin lanes, e.g. _p1 halves)
    key = lambda m: json.dumps({k: m.get(k) for k in ("id",) + FIELDS}, sort_keys=True)
    equal = sorted(map(key, old.get("members", []))) == sorted(map(key, new.get("members", [])))
    return dict(equal=equal, members_old=len(om), members_new=len(nm), added=len(added), removed=len(removed),
                changed=len(changed), lanes=lanes, added_ids=added[:limit], removed_ids=removed[:limit],
                changed_members=changed[:limit])


def write_atomic(path, text):
    path = Path(path)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.chmod(tmp, 0o664)
        os.replace(tmp, path)     # new inode: a hard-linked copy of the old table elsewhere keeps its bytes
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("derive")
    a.add_argument("plan")
    a.add_argument("bus_groups")
    a.add_argument("--like", required=True, help="current table: its r8 options are reused, its members diffed")
    a.add_argument("--out", required=True)
    a.add_argument("--json")
    a.add_argument("--pin-pre", help="pre-derive table (.json/.json.gz): apply pin_r8_v2.py to the derivation (the deliberate QC s29 R8 pin)")
    a.add_argument("--pin-extra", type=int, default=0)
    c = sub.add_parser("check")
    c.add_argument("plan")
    c.add_argument("bus_groups")
    c.add_argument("--table", required=True)
    c.add_argument("--json")
    c.add_argument("--pin-pre", help="pre-derive table (.json/.json.gz): apply pin_r8_v2.py to the derivation (the deliberate QC s29 R8 pin)")
    c.add_argument("--pin-extra", type=int, default=0)
    a = ap.parse_args(argv)
    import schema as S
    raw = S.load(a.plan)
    bg = json.loads(Path(a.bus_groups).read_text())
    ref = json.loads(Path(a.like if a.cmd == "derive" else a.table).read_text())
    text, sm = derive(raw, bg, options(ref))
    import pin_r8_v2 as P
    if a.pin_pre:
        text = pinned(text, a.pin_pre, a.pin_extra)
    elif a.cmd == "check" and P.PIN_MARK in str(ref.get("note", "")):
        print(f"LAND_R8 PIN MISSING {a.table}: the table is a deliberate pin ({P.PIN_MARK}) but check got no --pin-pre; "
              "a plain derivation would silently drop it")
        return 2
    d = diff(ref, json.loads(text))
    rep = dict(cmd=a.cmd, plan=str(a.plan), bus_groups=str(a.bus_groups), bus_groups_digest=R8.bg_digest(bg),
               options=options(ref), summary=sm, diff=d)
    if a.cmd == "derive":
        write_atomic(a.out, text)
        import hashlib
        rep["out"] = str(a.out)
        rep["out_sha256"] = hashlib.sha256(text.encode()).hexdigest()
        print(f"LAND_R8 DERIVED {a.out} sha256 {rep['out_sha256'][:12]}: members {d['members_new']}, changed "
              f"{d['changed']} (+{d['added']} -{d['removed']}) vs {a.like}; lanes {json.dumps(d['lanes'])}")
        rc = 0
    else:
        rc = 0 if d["equal"] else 1
        print(f"LAND_R8 {'DERIVED' if rc == 0 else 'STALE'} {a.table}: changed {d['changed']} (+{d['added']} "
              f"-{d['removed']}) vs a derivation from {a.bus_groups}; lanes {json.dumps(d['lanes'])}")
        for m in d["changed_members"][:10]:
            print(f"  STALE {m['id']}: " + ", ".join(f"{k} {v[0]}->{v[1]}" for k, v in m.items() if k != "id"))
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1) + "\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
