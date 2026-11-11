#!/usr/bin/env python3
"""S81 event SERDES-KITWIN-1111 (DIE-S81-85 sub-lane for DIE-S81-87, COORD ruling 11-11): the serdes kits charge each
kit clock port its own measured window, window = measured + MARGIN ps (default 20), instead of the plan's flat per_type_ps.

Mechanism (nothing new in the generator): plan clock.tap_window.per_port_ps {type: {port: ps}} (KW-FIX-4-SDC,
gen_phys.tap_window_port_table).  This event only FILLS that table for the serdes types from a measured table, so the
kit SDC / hold gate / sdc_lint / die_sta_related all read it through the existing gen_phys functions.

  measured table : any JSON with top key per_port_ps {type: {port: ps}} (die_sta_related --kit-window-out form, e.g.
                   DIE-RECHECK-1 kitwin_auto_<plan>.json).  READ ONLY, passed as --table (the path is an argument
                   because the ready5 plan re-measures it).
  rule           : window(port) = min(measured(port) + MARGIN, CAP), CAP = 208 ps (T/4 of the 833 ps clock, the limit
                   gen_phys.tap_window_port_table enforces).  Nothing is clipped to 116.  Ports above FLAG_PS (116) are
                   only FLAGGED in the report (a die clock item), never changed.
  types          : plan partition types whose name starts with --prefix (default serdes__).  A type with no measured
                   port in the table gets NO entry: it keeps its flat per_type_ps / window_ps (byte-identical SDC) and
                   is listed UNMEASURED in the report.
  refused        : a serdes type that already has a different per_port_ps entry; a table port that is not a window
                   port of the type (checked through gen_phys on the result; skip with --no-verify).
  fallback ports : a window port of a written type that the table lacks (the forwarded-clock edge ports fclk_in_*)
                   keeps the type's flat W_t, exactly as gen_phys does (named in the SDC comment); they are listed in the
                   report as ports_unmeasured_flat_fallback.  --strict-fallback refuses them instead.

Plan text is edited in place (the per_port_ps block and the tap_window note only); every other byte is unchanged and the
parsed plan is asserted equal apart from those two places.

usage: delta_serdes_kitwin_1111.py PLAN_JSON --table KITWIN_JSON [--out PLAN_OUT] [--report REPORT_JSON]
                                   [--margin 20] [--cap 208] [--flag 116] [--prefix serdes__] [--check] [--no-verify]
  default writes PLAN_JSON in place unless --out; --check writes nothing.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def num(v):
    v = float(v)
    return int(v) if v.is_integer() else v


def build(plan_text, table, args):
    """-> (new_plan_text, report, new); raises SystemExit on a refused input."""
    d = json.loads(plan_text)
    tw = d["clock"]["tap_window"]
    have = tw.get("per_port_ps") or {}
    meas = table["per_port_ps"]
    types = sorted(t for t in d["partition_types"] if t.startswith(args.prefix))
    if not types:
        raise SystemExit(f"no plan type starts with {args.prefix!r}")
    new, rep_types, unmeasured, clamped, flagged = {}, {}, [], {}, {}
    for t in types:
        m = meas.get(t) or {}
        if not m:
            unmeasured.append(t)
            continue
        win = {}
        for p, v in sorted(m.items()):
            v = float(v)
            if v < 0:
                raise SystemExit(f"{t}.{p}: negative measured window {v:g}")
            w = v + args.margin
            if w > args.cap:
                clamped.setdefault(t, {})[p] = [v, w]
                w = float(args.cap)
            if v > args.flag:
                flagged.setdefault(t, {})[p] = [v, w]
            win[p] = num(w)
        if t in have:
            if {k: num(x) for k, x in have[t].items()} != win:
                raise SystemExit(f"{t}: plan already has a different clock.tap_window.per_port_ps entry")
            continue
        new[t] = win
        rep_types[t] = dict(ports=len(win), measured_max=max(float(x) for x in m.values()),
                            window_min=min(win.values()), window_max=max(win.values()),
                            flat_before=num(tw.get("per_type_ps", {}).get(t, tw["window_ps"])))
    s = plan_text
    if new:
        i = s.index('  "tap_window": {')
        end = s.index("\n  }", i)               # end of the tap_window object (1-space plan indent)
        ents = ",\n".join(
            f'    "{t}": {{\n' + ",\n".join(f'     "{p}": {v}' for p, v in win.items()) + "\n    }"
            for t, win in new.items())
        if '"per_port_ps": {' in s[i:end]:
            j = s.index('"per_port_ps": {', i)
            k = s.index("\n   }", j)           # end of the per_port_ps object
            s = s[:k] + ",\n" + ents + s[k:]
        else:
            s = s[:end] + ',\n   "per_port_ps": {\n' + ents + "\n   }" + s[end:]
        note = (f" SERDES-KITWIN-1111 (COORD 11-11, DIE-S81-87): per_port_ps for {len(new)} serdes types = measured +"
                f" {args.margin:g} ps (cap {args.cap:g}, not clipped to {args.flag:g}), measured table"
                f" {table.get('_name', '?')} sha256 {table.get('_sha256', '?')[:12]} plan {str(table.get('plan_sha256', '?'))[:12]}"
                f" corners {table.get('corners', '?')}; types without a measured port keep the flat per_type_ps.")
        m_ = re.search(r'(  "tap_window": \{\n   "window_ps": [^\n]*\n   "note": "(?:[^"\\]|\\.)*)(")', s)
        s = s[:m_.end(1)] + note + s[m_.end(1):]
    d2 = json.loads(s)                      # only per_port_ps and note may change
    t2 = d2["clock"]["tap_window"]
    assert {t: t2["per_port_ps"][t] for t in new} == new
    for t in new:
        t2["per_port_ps"].pop(t)
    if "per_port_ps" in t2 and not t2["per_port_ps"] and "per_port_ps" not in tw:
        del t2["per_port_ps"]
    t2["note"] = tw["note"]
    assert d2 == d, "only the serdes per_port_ps entries and the tap_window note may change"
    rep = dict(event="SERDES-KITWIN-1111", margin_ps=args.margin, cap_ps=args.cap, flag_ps=args.flag,
               table=table.get("_name"), table_sha256=table.get("_sha256"), table_plan_sha256=table.get("plan_sha256"),
               plan_in_sha256=sha256(plan_text.encode()), plan_out_sha256=sha256(s.encode()),
               types_written=rep_types,
               types_unmeasured_keep_flat={t: num(tw.get("per_type_ps", {}).get(t, tw["window_ps"])) for t in unmeasured},
               ports_clamped_to_cap=clamped, ports_measured_over_flag=flagged,
               ports_written=sum(len(v) for v in new.values()))
    return s, rep, new


def verify(plan_text, new):
    """the result loads through gen_phys: every written port is a window port of its type and no window port falls back."""
    here = Path(__file__).resolve()
    for up in here.parents:
        if (up / "tools" / "die_plan" / "gen_phys.py").exists():
            sys.path.insert(0, str(up / "tools" / "die_plan"))
            break
    import gen_phys
    import schema
    P = schema.Plan(json.loads(plan_text))
    bad, fallback = {}, {}
    for t, win in new.items():
        names = set(gen_phys.window_port_names(P, t))
        extra, fb = sorted(set(win) - names), gen_phys.tap_window_fallback_ports(P, t)
        if extra:
            bad[t] = extra
        assert gen_phys.tap_window_port_table(P, t) == {k: float(v) for k, v in win.items()}
        if fb:
            fallback[t] = dict(ports=fb, flat_ps=gen_phys.tap_window_ps(P, t))
    if bad:
        raise SystemExit(f"REFUSED, table ports that are not window ports of the type: {json.dumps(bad)}")
    return fallback


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--table", required=True)
    ap.add_argument("--out")
    ap.add_argument("--report")
    ap.add_argument("--margin", type=float, default=20.0)
    ap.add_argument("--cap", type=float, default=208.0)
    ap.add_argument("--flag", type=float, default=116.0)
    ap.add_argument("--prefix", default="serdes__")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--no-verify", action="store_true")
    ap.add_argument("--strict-fallback", action="store_true")
    ap.add_argument("--emit-table", help="also write the per-port, per-type window table (measured, window) as JSON")
    args = ap.parse_args(argv)
    tp = Path(args.table)
    raw = tp.read_bytes()
    table = json.loads(raw)
    table["_name"], table["_sha256"] = tp.name, sha256(raw)
    s, rep, new = build(Path(args.plan).read_text(), table, args)
    if new and not args.no_verify:
        rep["ports_unmeasured_flat_fallback"] = verify(s, new)
        if rep["ports_unmeasured_flat_fallback"] and args.strict_fallback:
            raise SystemExit(f"REFUSED (--strict-fallback): {json.dumps(rep['ports_unmeasured_flat_fallback'])}")
    print(f"SERDES-KITWIN-1111: {len(rep['types_written'])} types, {rep['ports_written']} ports written; "
          f"UNMEASURED (flat kept) {sorted(rep['types_unmeasured_keep_flat'])}; "
          f"clamped {sum(len(v) for v in rep['ports_clamped_to_cap'].values())}; "
          f"flat-fallback ports {rep.get('ports_unmeasured_flat_fallback', {})}; "
          f"measured over {args.flag:g}: " + ", ".join(f"{t}.{p}={v[0]:g}->{v[1]:g}"
                                                       for t, ps in rep["ports_measured_over_flag"].items()
                                                       for p, v in ps.items()))
    if not args.check:
        if args.report:
            Path(args.report).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
        Path(args.out or args.plan).write_text(s)
        if args.emit_table:
            tab = dict(schema="opentallas.serdes_kitwin.v1", rule=f"window = min(measured + {args.margin:g}, {args.cap:g})",
                       source=dict(table=table["_name"], sha256=table["_sha256"], plan_sha256=table.get("plan_sha256"),
                                   proof=table.get("proof"), corners=table.get("corners")),
                       margin_ps=args.margin, cap_ps=args.cap, flag_ps=args.flag,
                       measured_ps={t: table["per_port_ps"][t] for t in sorted(rep["types_written"])},
                       window_ps={t: new[t] for t in sorted(new)} or {t: json.loads(s)["clock"]["tap_window"]["per_port_ps"][t]
                                                                       for t in sorted(rep["types_written"])},
                       unmeasured_keep_flat=rep["types_unmeasured_keep_flat"])
            Path(args.emit_table).write_text(json.dumps(tab, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
