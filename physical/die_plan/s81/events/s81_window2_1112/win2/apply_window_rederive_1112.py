#!/usr/bin/env python3
"""S81 stage WINDOW-REDERIVE-1112 (WINDOW-S81-1 for DIE-S81-87, COORD ruling 11-12): re-derive the per-port kit clock
windows of the S81 plan from a MEASURED-NEED table (die_sta_related --kit-window-out form, DIE-PROTO kitwin_auto_<plan>.json).

composer stage contract:  apply_window_rederive_1112.py IN OUT REPORT [--table T] [--signed F] ...   (cwd = repo root)
  declared keys (stage spec): top_keys ["clock.tap_window"], type_keys [].  The only plan content that may change is
  clock.tap_window.per_port_ps (entries of types listed in the table) and the clock.tap_window.note (one sentence appended
  when something changed).  Anything else fails closed (parsed plan compared before/after).  Without --table OUT is a
  byte-identical copy of IN.  Output keeps the plan's json form (compact+newline or indent=1+newline), else refused.

Rule per table port (type t, port p, measured need n):
  effective(t,p) = clock.tap_window.per_port_ps[t][p] if present, else per_type_ps[t], else window_ps
  n <= effective            -> unchanged (the window already covers the need; never lowered)
  n >  effective            -> window = min(n + MARGIN, CAP)   (MARGIN 20, CAP 208 = T/4)       [a conflicting existing entry
                               is only ever RAISED: it is overwritten only when smaller than the need]
  n + MARGIN > CAP, n<=CAP  -> written at CAP, listed REGION-TREE BALANCE (soft: margin < MARGIN)
  n >  CAP                  -> NOT written (not clipped), listed REGION-TREE BALANCE (hard: needs a region-tree balance)
  type in --signed          -> never changed; reported in signed_would_change when it would have changed
  table port that is not a window port of the type (gen_phys) -> REFUSED unless --allow-stale (then skipped + reported)
  negative need, a table type not in the plan, malformed existing entry -> REFUSED / reported.
--name-only FILE (types whose signed record matches by NAME only) is informational: reported, not excluded.
--base-plan PLAN: types whose partition_types entry differs from that older plan are reported as need_measured_on_older
  _definition (the need was measured before the type changed).
Idempotent: a second run on its own output changes nothing.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

EVENT = "WINDOW-REDERIVE-1112"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def num(v):
    v = float(v)
    return int(v) if v.is_integer() else v


def read_list(p):
    out = set()
    for ln in Path(p).read_text().splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#"):
            out.add(ln.split("\t")[0])
    return out


def form_of(plan, raw):
    for name, f in (("compact_nl", lambda d: json.dumps(d) + "\n"), ("indent1_nl", lambda d: json.dumps(d, indent=1) + "\n")):
        if f(plan).encode() == raw:
            return f
    raise SystemExit("REFUSED: plan is not in a json.dumps form (compact / indent=1, + newline)")


def derive(plan, table, signed, name_only, args, older=None):
    tw = plan["clock"]["tap_window"]
    flat_default = tw["window_ps"]
    flat = tw.get("per_type_ps") or {}
    have = tw.get("per_port_ps") or {}
    meas = table["per_port_ps"]
    types = plan["partition_types"]
    cap, margin = float(args.cap), float(args.margin)
    new = {}                    # t -> {port: window}
    changes, balance, signed_would, not_in_plan, stale = {}, {}, {}, [], {}
    for t in sorted(meas):
        if t not in types:
            not_in_plan.append(t)
            continue
        eff_flat = float(flat.get(t, flat_default))
        cur = have.get(t) or {}
        for p, v in cur.items():
            if not isinstance(v, (int, float)) or v < 0 or v > cap:
                raise SystemExit(f"REFUSED: malformed existing per_port_ps[{t}][{p}] = {v!r}")
        for p, n in sorted(meas[t].items()):
            n = float(n)
            if n < 0:
                raise SystemExit(f"REFUSED: {t}.{p}: negative measured need {n:g}")
            eff = float(cur[p]) if p in cur else eff_flat
            if n <= eff:
                continue
            w = min(n + margin, cap)
            row = dict(need=num(n), effective=num(eff), existing_entry=p in cur)
            if n > cap:
                balance.setdefault(t, {})[p] = dict(row, kind="HARD need>cap, not written", window_written=None)
                continue
            if n + margin > cap:
                balance.setdefault(t, {})[p] = dict(row, kind="SOFT written at cap, margin<%g" % margin, window_written=num(w))
            row["window"] = num(w)
            if t in signed:
                signed_would.setdefault(t, {})[p] = row
                continue
            changes.setdefault(t, {})[p] = row
            new.setdefault(t, {})[p] = num(w)
    return new, changes, balance, signed_would, not_in_plan


def apply(plan, new):
    tw = plan["clock"]["tap_window"]
    pp = tw.setdefault("per_port_ps", {})
    for t, win in new.items():
        ent = pp.setdefault(t, {})
        for p, w in win.items():
            ent[p] = w


def verify(plan, new):
    here = Path(__file__).resolve()
    for up in [*here.parents, Path.cwd().resolve()]:     # script copy outside the repo: the composer runs with cwd = repo root
        if (up / "tools" / "die_plan" / "gen_phys.py").exists():
            sys.path.insert(0, str(up / "tools" / "die_plan"))
            break
    import gen_phys
    import schema
    P = schema.Plan(plan)
    stale, fallback = {}, {}
    for t, win in new.items():
        names = set(gen_phys.window_port_names(P, t))
        bad = sorted(set(win) - names)
        if bad:
            stale[t] = bad
        tab = gen_phys.tap_window_port_table(P, t)
        for p, w in win.items():
            assert tab[p] == float(w), (t, p)
        fb = gen_phys.tap_window_fallback_ports(P, t)
        if fb:
            fallback[t] = dict(ports=fb, flat_ps=gen_phys.tap_window_ps(P, t))
    return stale, fallback


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("report")
    ap.add_argument("--table")
    ap.add_argument("--signed", help="file: one type per line, never changed")
    ap.add_argument("--name-only", help="file: types with a name-only signed record (informational)")
    ap.add_argument("--base-plan", help="older plan the table was measured on")
    ap.add_argument("--margin", type=float, default=20.0)
    ap.add_argument("--cap", type=float, default=208.0)
    ap.add_argument("--allow-stale", action="store_true")
    ap.add_argument("--no-verify", action="store_true")
    a = ap.parse_args(argv)
    raw = Path(a.inp).read_bytes()
    if not a.table:
        Path(a.out).write_bytes(raw)
        Path(a.report).write_text(json.dumps(dict(event=EVENT, applied=False, plan_in_sha256=sha(raw),
                                                  plan_out_sha256=sha(raw)), indent=1) + "\n")
        print(f"{EVENT}: no --table, byte-identical copy")
        return
    plan = json.loads(raw)
    dump = form_of(plan, raw)
    tp = Path(a.table)
    traw = tp.read_bytes()
    table = json.loads(traw)
    signed = read_list(a.signed) if a.signed else set()
    name_only = read_list(a.name_only) if a.name_only else set()
    new, changes, balance, signed_would, not_in_plan = derive(plan, table, signed, name_only, a)
    stale, fallback = ({}, {})
    if new:
        trial = json.loads(raw)
        apply(trial, new)
        if not a.no_verify:
            stale, fallback = verify(trial, new)
        if stale and not a.allow_stale:
            raise SystemExit("REFUSED, table ports that are not window ports of the type: " + json.dumps(stale)[:1500])
        if stale:
            for t, ps in stale.items():
                for p in ps:
                    new[t].pop(p)
                    changes[t].pop(p)
                if not new[t]:
                    new.pop(t)
                    changes.pop(t)
        new_plan = json.loads(raw)
        apply(new_plan, new)
        if new:
            tw = new_plan["clock"]["tap_window"]
            tw["note"] += (f" {EVENT} (COORD 11-12, DIE-S81-87): per_port_ps of {len(new)} types, {sum(len(v) for v in new.values())}"
                           f" ports raised to min(measured need + {a.margin:g}, {a.cap:g}) from {tp.name} sha256 {sha(traw)[:12]}"
                           f" (plan {str(table.get('plan_sha256', '?'))[:12]}, corners {table.get('corners', '?')}); ports whose need already fits"
                           f" keep their window; ports with need above the cap are not written (region-tree balance).")
        # declared keys only
        chk = json.loads(json.dumps(new_plan))
        c, o = chk["clock"]["tap_window"], plan["clock"]["tap_window"]
        c["note"] = o["note"]
        if "per_port_ps" in c:
            for t in new:
                if t in o.get("per_port_ps", {}):
                    c["per_port_ps"][t] = o["per_port_ps"][t]
                else:
                    c["per_port_ps"].pop(t)
            if not c["per_port_ps"] and "per_port_ps" not in o:
                del c["per_port_ps"]
        assert chk == plan, "only clock.tap_window.per_port_ps and the note may change"
        out_bytes = dump(new_plan).encode()
    else:
        out_bytes = raw
    older = None
    changed_since = []
    if a.base_plan:
        older = json.loads(Path(a.base_plan).read_bytes())["partition_types"]
        for t in sorted(set(changes) | set(balance) | set(signed_would)):
            if t in older and older[t] != plan["partition_types"][t]:
                changed_since.append(t)
            elif t not in older:
                changed_since.append(t)
    Path(a.out).write_bytes(out_bytes)
    rep = dict(event=EVENT, applied=bool(new), margin_ps=a.margin, cap_ps=a.cap, table=tp.name, table_sha256=sha(traw),
               table_plan_sha256=table.get("plan_sha256"), plan_in_sha256=sha(raw), plan_out_sha256=sha(out_bytes),
               types_written={t: dict(ports=len(w), widest=max(r["window"] for r in changes[t].values()),
                                      need_max=max(r["need"] for r in changes[t].values())) for t, w in sorted(new.items())},
               ports_written=sum(len(v) for v in new.values()),
               changes=changes,
               REGION_TREE_BALANCE=balance,
               region_tree_balance_ports=sum(len(v) for v in balance.values()),
               signed_would_change=signed_would, signed_excluded_input=sorted(signed),
               name_only_signed_written=sorted(t for t in new if t in name_only),
               name_only_signed_not_excluded_note="name-only signed matches are not proven to be the plan type definition",
               table_types_not_in_plan=not_in_plan, stale_ports_skipped=stale,
               fallback_ports_flat=fallback,
               need_measured_on_older_definition=changed_since,
               table_types_unlisted_in_plan=sorted(set(plan["partition_types"]) - set(table["per_port_ps"])))
    Path(a.report).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(f"{EVENT}: {len(new)} types, {rep['ports_written']} ports written; REGION-TREE BALANCE {len(balance)} types "
          f"{rep['region_tree_balance_ports']} ports; signed would change {sorted(signed_would)}; "
          f"older-definition types {len(changed_since)}")


if __name__ == "__main__":
    main()
