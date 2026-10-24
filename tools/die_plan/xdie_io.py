"""Cross-die die-IO pairing check (lane S81-HEAD 2026-10-24; extends PLAN-TOOL5 die_io_plan (a) across dies).

die_io.py checks ONE die: every PHY has a shoreline window and one window carries the host link.  A rack circuit joins
two dies, so its two endpoint windows must also agree.  For every circuit of a rack connection table
(results/arch/release_rack_1021/connections_<system>.csv) whose ends are dies with a die plan:

  missing   each endpoint macro (a_macros / b_macros, '+'-joined lk_<name>) has a die.io window on part lk_<name>
            in the die_io of that end's die role (ERROR);
  iface     both ends' windows have the same iface (serdes / ucie) (ERROR);
  lanes     the circuit's lanes_per_dir <= the end's macros x lanes a macro (window signals = 4 x lanes + 2) (ERROR);
  pitch     both ends use the same bump pitch (ERROR: the package / board breakout differs);
  host      a die role's die_io marks a host window (host: true / iface host) only if the rack gives that role a
            host circuit, and every role with a host circuit marks its host macros host: true (ERROR); a role
            without a host circuit may mark in-band host windows (host: "in_band", die_io.py --in-band-host), which
            must be macros the rack actually wires for that role (ERROR otherwise);
  unused    a die-IO window no circuit of that role uses (WARN: a reserve or an unplanned PHY).

    python3 tools/die_plan/xdie_io.py --conn results/arch/release_rack_1021/connections_s81.csv \
        --role H=physical/die_plan/s81_head/die_io.json --role S=physical/die_plan/s81/die_io.json \
        --role B=physical/die_plan/s81/die_io.json [--out REPORT.json]

A role is the first letter of the rack's unit name (S81: H = head die, S = stage / layer die, B = copy-B die, which
is a layer-die master).  Ends without a role (host NIC, mgmt) are skipped; a 'mgmt' row is not a SerDes circuit.
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path


def lanes_of(w):
    return (int(w["signals"]) - 2) // 4 if w.get("iface") == "serdes" else None


def check(conn_rows, roles):
    errs, warns = [], []
    used = defaultdict(set)
    host_roles = set()
    by_cls = defaultdict(int)
    for r in conn_rows:
        if r.get("cls") == "mgmt":
            continue
        ends = []
        for s in ("a", "b"):
            unit = r[f"{s}_unit"]
            role = unit[:1] if unit and unit[:1] in roles else None
            ends.append((s, role, [m for m in r[f"{s}_macros"].split("+") if m.startswith("lk_")]))
        if r.get("cls") == "host":
            for s, role, _ in ends:
                if role:
                    host_roles.add(role)
        wins = []
        for s, role, macros in ends:
            if not role:
                wins.append(None)
                continue
            io = roles[role]
            ws = []
            for m in macros:
                used[role].add(m)
                w = io.get(m)
                if w is None:
                    errs.append(dict(rule="missing", circuit=r["id"], cls=r["cls"], role=role, macro=m,
                                     msg=f"{r['cls']} {r['id']}: role {role} has no die.io window on {m}"))
                else:
                    ws.append(w)
            if ws:
                lanes = sum(lanes_of(w) or 0 for w in ws)
                if lanes and int(r["lanes_per_dir"]) > lanes:
                    errs.append(dict(rule="lanes", circuit=r["id"], role=role,
                                     msg=f"{r['id']}: {r['lanes_per_dir']} lanes > {lanes} on {role} {macros}"))
            wins.append(ws)
        if all(wins) and len(wins) == 2:
            a, b = wins
            ia, ib = {w["iface"] for w in a}, {w["iface"] for w in b}
            if ia != ib:
                errs.append(dict(rule="iface", circuit=r["id"], msg=f"{r['id']}: iface {ia} vs {ib}"))
            pa, pb = {w["pitch_um"] for w in a}, {w["pitch_um"] for w in b}
            if pa != pb:
                errs.append(dict(rule="pitch", circuit=r["id"], msg=f"{r['id']}: bump pitch {pa} vs {pb}"))
            by_cls[(r["cls"], ends[0][1], ends[1][1])] += 1
    summ = dict(circuits_checked=sum(by_cls.values()),
                by_class={f"{c} {a}-{b}": n for (c, a, b), n in sorted(by_cls.items())}, roles={})
    for role, io in roles.items():
        hw = sorted(m for m, w in io.items() if w.get("host") is True or w.get("iface") == "host")
        ib = sorted(m for m, w in io.items() if w.get("host") == "in_band")
        unused = sorted(set(io) - used[role] - {m for m, w in io.items() if w.get("iface") == "hbm_phy"})
        summ["roles"][role] = dict(windows=len(io), used=sorted(used[role] & set(io)), host_windows=hw, unused=unused,
                                   host_circuit=role in host_roles, in_band_host_windows=ib)
        if ib and not set(ib) <= used[role]:
            errs.append(dict(rule="host", role=role, msg=f"role {role}: in-band host windows {sorted(set(ib) - used[role])}"
                                                         " are wired by no rack circuit of this role"))
        if hw and role not in host_roles:
            errs.append(dict(rule="host", role=role, msg=f"role {role}: die_io marks {hw} host: true but the rack gives "
                                                         "this role no host circuit (host traffic is in-band)"))
        if role in host_roles:
            need = sorted(m for m in used[role] if m.startswith("lk_HOST"))
            if not set(need) <= set(hw):
                errs.append(dict(rule="host", role=role, msg=f"role {role}: host circuit macros {need} not all "
                                                             f"host: true (marked {hw})"))
        for m in unused:
            warns.append(dict(rule="unused", role=role, macro=m, msg=f"role {role}: window {m} used by no circuit"))
    return errs, warns, summ


def load_io(path):
    io = json.loads(Path(path).read_text())
    io = io.get("io", io) if isinstance(io, dict) else io
    return {w["part"]: w for w in io if w.get("part")}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--conn", required=True)
    ap.add_argument("--role", action="append", required=True, help="LETTER=die_io.json")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    roles = {k: load_io(v) for k, v in (x.split("=", 1) for x in a.role)}
    rows = list(csv.DictReader(open(a.conn)))
    errs, warns, summ = check(rows, roles)
    # collapse repeated messages per (rule, role, macro)
    agg = defaultdict(lambda: dict(n=0))
    for e in errs:
        k = (e["rule"], e.get("role"), e.get("macro"), e.get("cls"))
        agg[k]["n"] += 1
        agg[k].setdefault("example", e["msg"])
    rep = dict(schema="opentallas.die_plan.xdie_io.v1", conn=a.conn, roles=dict(x.split("=", 1) for x in a.role),
               verdict="PASS" if not errs else "FAIL", errors=len(errs),
               error_groups=[dict(rule=k[0], role=k[1], macro=k[2], cls=k[3], **v) for k, v in agg.items()],
               warnings=[w["msg"] for w in warns], summary=summ)
    txt = json.dumps(rep, indent=1)
    if a.out:
        Path(a.out).write_text(txt + "\n")
    for g in rep["error_groups"]:
        print(f"ERROR [{g['rule']}] x{g['n']}: {g['example']}")
    for w in rep["warnings"]:
        print(f"WARN  {w}")
    print(f"xdie_io {rep['verdict']}: {summ['circuits_checked']} circuits with both ends planned, {len(errs)} errors, "
          f"{len(warns)} warnings; {summ['by_class']}")
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
