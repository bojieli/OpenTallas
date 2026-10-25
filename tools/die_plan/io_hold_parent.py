#!/usr/bin/env python3
"""IO-HOLD option A parent check: related-pair FF hold with CPPR on every partition crossing whose receiver kit took
its sender's guaranteed output-min as min input delay (COORD ruling 2026-10-25 10:23; gen_phys.input_hold_min).

    python3 tools/die_plan/io_hold_parent.py PLAN.json DIE_STA.json [--out R.json] [--standin-types t1,t2]
    python3 tools/die_plan/io_hold_parent.py - DIE_STA.json --all-seams      # every seam group, no plan

Under option A the kits no longer pad their inputs for the related tap pair skew between sender and receiver (nor
for the receiver's 12.5-ps hold-uncertainty half, which the sender guarantee already used); that seam is checked ONCE
here, on the assembled parent (die or cluster) with the real views.  DIE_STA.json is the result of the existing die
STA flow on that parent:

    python3 tools/die_plan/die_sta.py run --top <parent top> --parts <real views> --out DIR --mode flat|ilm \
        --corner TT --corner FF [--spine-tree DIR | --die-spef ...]

die_sta times every seam bit with each partition's own routed clock tree propagated, hold uncertainty 25 ps, CPPR on,
and the related launch x capture register pairs of each seam with their CPPR credit (pairskew).  For every plan port
into an A input this script requires, at FF: a timed hold path, worst seam hold slack >= 0, and the CPPR-credited
related pair skew <= die_sta.SKEW_PS (80 ps) at TT and FF.  Ports whose sender or receiver is a budget stand-in
(--standin-types) are not evidence: NOT_TIMED.  A kit signed off under option A counts only once every one of its A
input ports is PASS here (COORD 10:23).

Verdict: PASS (all A ports PASS) / FAIL (any A port FAIL) / INCOMPLETE (no FAIL, some A port not timed); exit 0 / 1 / 2.
ilm and flat are hold verdicts; etm is refused (its clock->output arcs are MAX-only, die_sta docstring).
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_sta  # noqa: E402
import gen_phys  # noqa: E402
import gen_rtl  # noqa: E402
import schema as S  # noqa: E402
from schema import DIE_PART  # noqa: E402

HOLD_CORNER = "FF"            # owner sign-off: hold at FF (setup TT); never SS
PAIR_CORNERS = ("TT", "FF")


def _groups(corner):
    """{(src inst, dst inst, dst bus): (seam dict, pairskew dict)} of one die_sta corner (keys 'src->dst/bus')."""
    out = {}
    for g, s in (corner.get("seams") or {}).items():
        src, _, rest = g.partition("->")
        dst, _, bus = rest.partition("/")
        out[(src, dst, bus)] = (s, (corner.get("pairskew") or {}).get(g))
    return out


def _all_seam_ports(sta):
    """--all-seams: one pseudo port per die_sta seam group (no plan; every crossing treated as an A crossing)."""
    keys = set()
    for c in (sta.get("corners") or {}).values():
        keys |= set(_groups(c))
    return [(f"{s}->{d}/{b}", dict(src=dict(part=s, bus=b), dst=dict(part=d, bus=b))) for s, d, b in sorted(keys)]


def check(P, sta, standin_types=(), all_seams=False):
    """-> dict(verdict, counts, ports=[...]) for every partition->partition plan port into an option-A input
    (all_seams: every die_sta seam group, P may be None)."""
    if sta.get("mode") == "etm":
        raise ValueError("etm die STA is not a hold verdict (MAX-only clock->output arcs); run flat or ilm")
    corners = sta.get("corners") or {}
    miss = [c for c in (HOLD_CORNER,) + PAIR_CORNERS if c not in corners or corners[c].get("exit", 0) != 0]
    grp = {c: _groups(corners[c]) for c in corners}
    a_cache, rows = {}, []
    for pid, pr in (_all_seam_ports(sta) if all_seams else sorted(P.ports.items())):
        s, d = pr["src"]["part"], pr["dst"]["part"]
        if all_seams:
            dt, st, bus = d, s, pr["dst"]["bus"]
            a = dict(in_min_ps=None, basis="--all-seams")
            key = (s, d, bus)
        else:
            if DIE_PART in (s, d) or s not in P.parts or d not in P.parts:
                continue
            dt, st = P.parts[d]["type"], P.parts[s]["type"]
            if dt not in a_cache:
                a_cache[dt] = gen_phys.input_hold_min(P, dt)
            bus = gen_rtl.sv_id(pr["dst"]["bus"])
            a = a_cache[dt].get(bus)
            if a is None:
                continue
            key = (gen_rtl.sv_id(s), gen_rtl.sv_id(d), bus)
        row = dict(port=pid, src=s, dst=d, dst_type=dt, src_type=st, bus=pr["dst"]["bus"], in_min_ps=a["in_min_ps"],
                   basis=a["basis"])
        why = []
        if st in standin_types or dt in standin_types:
            why.append("budget stand-in view")
        if miss:
            why.append(f"corner(s) {','.join(miss)} not run")
        seam = grp.get(HOLD_CORNER, {}).get(key)
        if seam is None or not seam[0].get("min"):
            why.append("no FF hold path in die_sta")
        else:
            h = seam[0]["min"]
            row.update(hold_ff_ps=h["worst"], neg=h["neg"], tns_ps=h["tns"], worst_from=h["start"], worst_to=h["end"])
        for c in PAIR_CORNERS:
            ps = grp.get(c, {}).get(key, (None, None))[1]
            if ps and ps.get("max_cppr") is not None:
                row[f"pair_hold_skew_cppr_{c}"] = ps.get("max_cppr")
                row[f"pair_setup_skew_cppr_{c}"] = ps.get("min_cppr")
            elif not miss:
                why.append(f"no related-pair skew (CPPR) at {c} in die_sta (rerun with the current die_sta.py)")
        if why:
            row.update(status="NOT_TIMED", why="; ".join(why))
        else:
            bad = []
            if row["hold_ff_ps"] < 0:
                bad.append(f"FF seam hold {row['hold_ff_ps']:g} ps / {row['neg']} ep")
            for c in PAIR_CORNERS:
                sk = [abs(v) for v in (row.get(f"pair_hold_skew_cppr_{c}"), row.get(f"pair_setup_skew_cppr_{c}"))
                      if v is not None]
                if sk and max(sk) > die_sta.SKEW_PS:
                    bad.append(f"{c} related pair skew (CPPR) {max(sk):g} > {die_sta.SKEW_PS:g} ps")
            row.update(status="FAIL" if bad else "PASS", why="; ".join(bad))
        rows.append(row)
    cnt = dict(a_ports=len(rows), pass_=sum(r["status"] == "PASS" for r in rows),
               fail=sum(r["status"] == "FAIL" for r in rows), not_timed=sum(r["status"] == "NOT_TIMED" for r in rows))
    cnt["pass"] = cnt.pop("pass_")
    verdict = "FAIL" if cnt["fail"] else ("INCOMPLETE" if cnt["not_timed"] or not rows else "PASS")
    worst = min((r for r in rows if "hold_ff_ps" in r), key=lambda r: r["hold_ff_ps"], default=None)
    return dict(schema="opentallas.io_hold_parent.v1", plan=P.name if P is not None else None, mode=sta.get("mode"), verdict=verdict,
                counts=cnt, worst=worst, kit_types=sorted(a_cache),
                gate=(f"every plan port into an IO-HOLD A input: FF seam hold >= 0 (25 ps unc, CPPR, real propagated "
                      f"trees) and related pair skew with CPPR <= {die_sta.SKEW_PS:g} ps at TT and FF"),
                ports=rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan", help="die / parent plan JSON ('-' with --all-seams)")
    ap.add_argument("die_sta_json")
    ap.add_argument("--out")
    ap.add_argument("--standin-types", default="", help="comma list of partition types that are budget stand-ins")
    ap.add_argument("--all-seams", action="store_true", help="check every die_sta seam group (no plan selection)")
    a = ap.parse_args(argv)
    P = None if a.all_seams and a.plan == "-" else S.Plan(json.loads(Path(a.plan).read_text()))
    r = check(P, json.loads(Path(a.die_sta_json).read_text()),
              standin_types={x for x in a.standin_types.split(",") if x}, all_seams=a.all_seams)
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1) + "\n")
    c = r["counts"]
    w = r["worst"]
    print(f"IO_HOLD_PARENT {r['verdict']} plan {r['plan']} mode {r['mode']} A-ports {c['a_ports']} pass {c['pass']} fail {c['fail']} "
          f"not_timed {c['not_timed']}" + (f" worst {w['port']} {w['hold_ff_ps']:g} ps" if w else ""))
    for x in r["ports"]:
        if x["status"] != "PASS":
            print(f"  {x['status']} {x['port']} {x['src']}->{x['dst']}.{x['bus']}: {x['why']}")
    return {"PASS": 0, "FAIL": 1}.get(r["verdict"], 2)


if __name__ == "__main__":
    sys.exit(main())
