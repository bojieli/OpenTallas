#!/usr/bin/env python3
"""QC-PLAN-R9-LEAFLEG (FABLE-PD-QC-0440 section 2, fix 4): reset LEAF legs of a bound die plan.  ADVISORY ESTIMATOR, never a gate.

The bind proves relay-to-relay hops only (bind_reset.json long_hops / max_die_hop_um).  The leg it does not see is the last
one: a leaf relay driving sinks far away (QC cbf_q00__cl1b5a6458 fp3: leaf u_rrl_482 (tap 45, centre cross) drives the
type's rst_n, which reached the four fabric stations u_u_fab_u_x_*, one 1,850 um away; -394 ps).  This tool reads a bind
output directory and the plan it bound, and for every reset consumer of every generated reset tree finds the relay whose
q net drives it (through `wire a = b;` / `assign a = b;` aliases of the bound RTL) and measures the Manhattan leg.

  python3 -I tools/precheck/reset_leaf_legs.py BIND_DIR PLAN.json [--out-json OUT.json] [--out-tsv OUT.tsv]
          [--cap-um 300] [--types T[,T...]] [--positions POS.json]

Consumers and their positions (type frame, um):
  core     tree.core_resets: tap relay rst_n_t<tap> -> core reset pin (pin_um, else xy).  The core-input lockup cell (ot_dp_lk)
           on the same tap net is covered by that row.
  out      `assign rst_o_<k> / start_o_<k> = <net>;` -> bind_reset.json types[T].outs (name, x, y), else tree.outs[k].
  inst     any emitted non-tree instance port on a tree net (banks u_bin/u_bout/u_ft/u_ist, fabric stations, landing relays ...):
           --positions {type: {inst: [x, y] | [[x, y], ...]}} first (e.g. from a placed kit), then plan relay_sites points
           of that instance (`inst/...`, `inst.`), then the plan bank estimate (bank_reset_delta.bank_xy: bus face-window centre,
           ft_slots / internal_stations regs_um).  With several points the worst leg counts.
  tap      clock tap site as the proxy for the tap's own sinks: relay with q rst_n_t<i> -> site i of reset.consumer_sites_um
           (+ reset.local_taps_um as reset_local_<j>), else the plan's clock tap table (reset_tree._taps).
  logic    a tree net used in a bound `assign` expression (flattened logic): no position -> UNMEASURED.
Kit re-point: a boundary bank flop (ot_dp_st / ot_dp_ste eq, FIRM-placed) is re-pointed by the kit's reset_taps.tcl (pre-GPL) to
the NEAREST consumer tap net, whatever the bound RTL says (fp3 cbf_q00__cl1b5a6458: u_bout_bc_o01.eq D on rst_n = t45 in the
RTL, on rst_n_t97 placed), so its leg is measured to that nearest tap relay (leg_rtl_um / bound_relay keep the bound one;
--no-kit-repoint measures the bound net).  Leaf (non-FIRM) logic such as fabric stations keeps its RTL net: inst_taps is the fix.
A consumer with no position is UNMEASURED (never PASS).  Rows over --cap-um are OVER.  Each plan reset.inst_taps row is also
checked against the bound RTL (the sink port must sit on rst_n_t<tap>): inst_taps_not_applied lists the misses, and
inst_taps_off_consumer the rows whose tap index is an out / core relay of the bound tree (>= n_reset_consumers): legal (same
depth K), but numbered after the consumer taps, so it shifts when taps are added -- read its leg (b14 cbn_q11__cl5cc92dfe
x_2_3 on tap 89 = core_rst1, 2,579 um).  inst points from plan relay_sites are every planned flop site of the instance, so the leg
is an upper bound when only some of those flops take the reset.

Exit 0 always (it is an estimator), 2 only on malformed inputs (missing bind dir / plan / unreadable JSON).
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIE_PLAN = HERE.parent / "die_plan"
sys.path.insert(0, str(DIE_PLAN))
import bank_reset_delta as BRD  # noqa: E402
import reset_consumers as RC  # noqa: E402
sys.path.pop(0)

SCHEMA = "opentallas.reset_leaf_legs.v1"
CAP_UM = 300.0
TREE_MODS = ("ot_dp_rrelay", "ot_dp_rgate", "ot_dp_rsync")
LOCKUP_MODS = ("ot_dp_lk",)
BANK_MODS = ("ot_dp_st", "ot_dp_ste")
ALIAS = re.compile(r"(?m)^[ \t]*(?:wire|assign)[ \t]+(?:\[[^\]]*\][ \t]*)?([A-Za-z_]\w*)[ \t]*=[ \t]*([A-Za-z_]\w*)[ \t]*;")
ASSIGN = re.compile(r"(?m)^[ \t]*assign[ \t]+([^=;]+?)[ \t]*=[ \t]*([^;]+);")
# generated relay line with its site comment:  ot_dp_rrelay u_srl_7 (.clk(clk), .d(x), .q(y));  // run wire ... @ (82.1, 1437.8)
RELAY_LINE = re.compile(r"(?m)^[ \t]*(ot_dp_r\w+)[ \t]+(u_\w+)[ \t]*\(.*?\.q\(([A-Za-z_]\w*)\)\);[^\n]*?//[ \t]*(\w+)[^\n]*@ \(([-\d.]+), ([-\d.]+)\)")
IDENT = re.compile(r"[A-Za-z_][\w$]*")
OUT_PORT = re.compile(r"^(?:rst_o|start_o)_\d+$")


class InputError(ValueError):
    pass


def man(a, b):
    return abs(float(a[0]) - float(b[0])) + abs(float(a[1]) - float(b[1]))


def load_json(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError) as e:
        raise InputError(f"cannot read JSON {p}: {e}")


def resolve(net, aliases):
    seen = set()
    while net in aliases and net not in seen:
        seen.add(net)
        net = aliases[net]
    return net


def drivers(tree, sv):
    """{net: relay row} of every generated relay output: tree.relays (exact sites), plus the relays the tree json does
    not list (START run chain u_srl_*, ...) from their RTL site comments (0.1 um)."""
    out = {}
    for r in tree.get("relays") or []:
        if isinstance(r.get("q"), str) and r.get("xy"):
            out[r["q"]] = dict(name=r.get("name"), xy=[float(r["xy"][0]), float(r["xy"][1])], kind=r.get("kind"),
                               depth=r.get("depth"), tap=r.get("tap"), src="tree")
    for m in RELAY_LINE.finditer(sv):
        mod, inst, q, word, x, y = m.groups()
        if q not in out:
            out[q] = dict(name=inst, xy=[float(x), float(y)], kind=word, depth=None, tap=None, src="rtl_comment")
    return out


def tap_sites(tn, t, tree, plan_raw, cache):
    """{tap index: (x, y, source)} for the tree's tap list (index = position in tree.taps)."""
    names = tree.get("taps") or []
    r = t.get("reset") or {}
    sites = {}
    frozen = r.get("consumer_sites_um")
    by_name = {}
    if frozen:
        by_name = {str(n): (float(x), float(y)) for n, x, y in frozen}
    for j, xy in enumerate(r.get("local_taps_um") or []):
        by_name[f"reset_local_{j}"] = (float(xy[0]), float(xy[1]))
    if not frozen:
        try:                                      # the plan's own clock tap table (heavy: one schema.Plan per run)
            if "P" not in cache:
                sys.path.insert(0, str(DIE_PLAN))
                import reset_tree as RT
                import schema as S
                sys.path.pop(0)
                cache["P"], cache["RT"] = S.Plan(plan_raw), RT
            for n, x, y in cache["RT"]._taps(cache["P"], tn):
                by_name.setdefault(str(n), (float(x), float(y)))
            src = "plan_clock_taps"
        except Exception as e:                    # noqa: BLE001 -- estimator: no site -> UNMEASURED
            cache.setdefault("tap_errors", {})[tn] = f"{type(e).__name__}: {e}"[:300]
            src = None
    else:
        src = "consumer_sites_um"
    for i, n in enumerate(names):
        if n in by_name:
            sites[i] = (*by_name[n], "local_taps_um" if n.startswith("reset_local_") else src)
    return sites


def inst_points(tn, t, inst, positions, module=""):
    """[(x, y)], source -- or ([], None).  A boundary bank (ot_dp_st / ot_dp_ste) resets ONE flop (eq, beside its q bits):
    its relay_sites points collapse to their centroid; any other instance keeps every point (worst leg counts)."""
    p = (positions.get(tn) or {}).get(inst)
    if p:
        pts = [p] if isinstance(p[0], (int, float)) else p
        return [(float(a[0]), float(a[1])) for a in pts], "positions"
    rs = t.get("relay_sites") or {}
    pts = [v for k, v in rs.items() if k.startswith(inst + "/") or k.startswith(inst + ".")]
    if pts and module in BANK_MODS:
        return [(sum(float(v[0]) for v in pts) / len(pts), sum(float(v[1]) for v in pts) / len(pts))], "plan_relay_sites_centroid"
    if pts:
        return [(float(v[0]), float(v[1])) for v in pts], "plan_relay_sites"
    try:
        xy = BRD.bank_xy(t, inst)
    except Exception:                             # noqa: BLE001 -- a malformed plan row: UNMEASURED, not a crash
        xy = None
    if xy:
        return [(float(xy[0]), float(xy[1]))], "plan_bank_estimate"
    return [], None


def type_legs(tn, t, tree, sv, bind_type, positions, cap, plan_raw, cache, kit_repoint=True):
    drv = drivers(tree, sv)
    names = tree.get("taps") or []
    n_cons = int(tree.get("n_reset_consumers") or tree.get("n_clock_taps") or len(names))
    cons_taps = [(f"rst_n_t{i}", drv[f"rst_n_t{i}"]) for i in range(n_cons) if f"rst_n_t{i}" in drv]
    aliases = dict(ALIAS.findall(sv))
    calls = RC._calls(sv)
    tree_insts = {r["name"] for r in tree.get("relays") or []} | {d["name"] for d in drv.values()}
    legs, unmeasured = [], []

    def leg(cls, consumer, net, pts, src, extra=None, repoint=False):
        d = drv[net]
        if not pts:
            unmeasured.append(dict(cls=cls, consumer=consumer, relay=d["name"], net=net, **(extra or {})))
            return
        far = max(pts, key=lambda p: man(d["xy"], p))
        row = dict(cls=cls, consumer=consumer, relay=d["name"], relay_kind=d["kind"], net=net,
                   relay_xy=[round(v, 3) for v in d["xy"]], consumer_xy=[round(v, 3) for v in far],
                   n_points=len(pts), leg_um=round(man(d["xy"], far), 1), pos_src=src, **(extra or {}))
        row["leg_rtl_um"] = row["leg_um"]
        if repoint and cons_taps and net.startswith("rst_n"):
            # the kit's reset_taps.tcl (pre-GPL) re-points every FIRM-placed flop on a tap net to its NEAREST tap
            # (seen on fp3: u_bout_bc_o01.eq D rst_n (t45) -> rst_n_t97): the placed leg is the nearest-tap one
            kn, kd = min(cons_taps, key=lambda c: max(man(c[1]["xy"], p) for p in pts))
            kfar = max(pts, key=lambda p: man(kd["xy"], p))
            row.update(relay=kd["name"], relay_kind=kd["kind"], net=kn, relay_xy=[round(v, 3) for v in kd["xy"]],
                       consumer_xy=[round(v, 3) for v in kfar], leg_um=round(man(kd["xy"], kfar), 1),
                       bound_net=net, bound_relay=d["name"], kit_repoint=True)
        legs.append(row)

    # core reset pins
    core_taps = set()
    for c in tree.get("core_resets") or []:
        net = f"rst_n_t{c.get('tap')}"
        core_taps.add(net)
        if net not in drv:
            unmeasured.append(dict(cls="core", consumer=f"{c.get('inst')}.{c.get('pin')}", relay=None, net=net,
                                   why="tap relay not in tree"))
            continue
        xy = c.get("pin_um") or c.get("xy")
        leg("core", f"{c.get('inst')}.{c.get('pin')}", net, [tuple(xy)] if xy else [], "tree_core_resets")

    # outs
    outs_xy = {}
    for k, o in enumerate((bind_type or {}).get("outs") or []):
        outs_xy[str(o[0])] = (float(o[1]), float(o[2]))
    tree_outs = tree.get("outs") or []
    for m in ASSIGN.finditer(sv):
        lhs, rhs = m.group(1).strip(), m.group(2).strip()
        ids = [resolve(i, aliases) for i in IDENT.findall(rhs)]
        hit = [i for i in ids if i in drv]
        if not hit:
            continue
        if OUT_PORT.match(lhs):
            k = int(lhs.rsplit("_", 1)[1])
            xy = outs_xy.get(f"rst_o_{k}") or (tuple(tree_outs[k][:2]) if k < len(tree_outs) else None)
            leg("out", lhs, hit[0], [xy] if xy else [], "bind_reset_outs" if f"rst_o_{k}" in outs_xy else "tree_outs")
        elif re.fullmatch(r"[A-Za-z_]\w*", rhs) and lhs in aliases:   # a plain alias: its users are counted at the use
            continue
        else:
            for net in sorted(set(hit)):
                unmeasured.append(dict(cls="logic", consumer=lhs[:80], relay=drv[net]["name"], net=net))

    # instance ports
    for inst, c in calls.items():
        if inst in tree_insts:
            continue
        mod = c["module"]
        for port, (expr, _lo, _hi) in c["ports"].items():
            ids = {resolve(i, aliases) for i in IDENT.findall(expr)}
            for net in sorted(i for i in ids if i in drv):
                if mod.startswith(LOCKUP_MODS) and net in core_taps:
                    continue                           # core-input lockup: measured by its core row
                pts, src = inst_points(tn, t, inst, positions, mod)
                leg("inst", f"{inst}.{port}", net, pts, src, dict(module=mod), repoint=kit_repoint and mod in BANK_MODS)

    # clock tap sites (proxy for the tap's own sinks)
    sites = tap_sites(tn, t, tree, plan_raw, cache)
    for i, name in enumerate(names[:n_cons]):          # taps after the consumers are the out / core relays (rows above)
        net = f"rst_n_t{i}"
        if net not in drv:
            continue
        s = sites.get(i)
        leg("tap", f"tap{i}:{name}", net, [s[:2]] if s else [], s[2] if s else None)

    # plan inst_taps rows applied in the bound RTL?
    not_applied, off_consumer = [], []
    for row in (t.get("reset") or {}).get("inst_taps") or []:
        port = row.get("port", "rst_n")
        tap = row.get("tap")
        if isinstance(tap, int) and not 0 <= tap < n_cons:
            # an out / core relay index, not a consumer tap: legal, but its number moves whenever consumer taps are added
            off_consumer.append(dict(tap=tap, tap_name=names[tap] if 0 <= tap < len(names) else None,
                                     n_reset_consumers=n_cons, sinks=list(row.get("sinks") or [])))
        for s in row.get("sinks") or []:
            got = (calls.get(s) or {}).get("ports", {}).get(port, (None,))[0]
            if got != f"rst_n_t{row.get('tap')}":
                not_applied.append(dict(sink=s, port=port, want=f"rst_n_t{row.get('tap')}", bound=got))

    over = sorted((x for x in legs if x["leg_um"] > cap), key=lambda x: -x["leg_um"])
    n_over_rtl = sum(1 for x in legs if x["leg_rtl_um"] > cap)
    by_cls = {}
    for x in unmeasured:
        by_cls[x["cls"]] = by_cls.get(x["cls"], 0) + 1
    return dict(n_consumers=len(legs) + len(unmeasured), n_measured=len(legs), n_unmeasured=len(unmeasured),
                unmeasured_by_class=by_cls, max_leg_um=max((x["leg_um"] for x in legs), default=None),
                n_over=len(over), n_over_as_bound=n_over_rtl, over=over, unmeasured=unmeasured, legs=legs,
                inst_taps_rows=len((t.get("reset") or {}).get("inst_taps") or []), inst_taps_not_applied=not_applied,
                inst_taps_off_consumer=off_consumer,
                verdict="OVER" if over else ("UNMEASURED" if unmeasured else "UNDER"))


def run(bind_dir, plan_path, cap=CAP_UM, types=None, positions=None, kit_repoint=True):
    bind_dir = Path(bind_dir)
    rtl = bind_dir / "rtl"
    if not rtl.is_dir():
        raise InputError(f"{rtl}: no bind rtl/ dir")
    plan = load_json(plan_path)
    if not isinstance(plan, dict) or not isinstance(plan.get("partition_types"), dict):
        raise InputError(f"{plan_path}: no partition_types")
    br = load_json(bind_dir / "bind_reset.json") if (bind_dir / "bind_reset.json").is_file() else {}
    btypes = br.get("types") or {}
    pt = plan["partition_types"]
    trees = sorted(p for p in rtl.glob("*.reset_tree.json"))
    out, cache, no_tree = {}, {}, []
    seen = set()
    for p in trees:
        doc = load_json(p)
        tn = doc.get("plan_type") or p.name[: -len(".reset_tree.json")]
        if types and tn not in types:
            continue
        seen.add(tn)
        if tn not in pt:
            out[tn] = dict(verdict="UNMEASURED", error="type not in plan")
            continue
        try:
            sv = BRD.bound_rtl(rtl, tn, pt[tn]).read_text()
        except (BRD.DeltaError, OSError) as e:
            out[tn] = dict(verdict="UNMEASURED", error=str(e))
            continue
        tree = doc.get("tree")
        if not isinstance(tree, dict):
            raise InputError(f"{p}: no tree")
        try:
            out[tn] = type_legs(tn, pt[tn], tree, sv, btypes.get(tn), positions or {}, cap, plan, cache, kit_repoint)
        except RC.ResetConsumerError as e:
            out[tn] = dict(verdict="UNMEASURED", error=f"bound RTL parse: {e}")
    for tn in sorted(pt):
        if tn not in seen and (not types or tn in types):
            no_tree.append(tn)
    worst = sorted((dict(type=tn, **{k: x[k] for k in ("cls", "consumer", "relay", "leg_um")})
                    for tn, r in out.items() for x in r.get("over") or []), key=lambda x: -x["leg_um"])
    summ = dict(types=len(out), types_over=sum(1 for r in out.values() if r.get("n_over")),
                legs_over=sum(r.get("n_over", 0) for r in out.values()),
                legs_over_as_bound=sum(r.get("n_over_as_bound", 0) for r in out.values()),
                legs_over_by_class={},
                measured=sum(r.get("n_measured", 0) for r in out.values()),
                unmeasured=sum(r.get("n_unmeasured", 0) for r in out.values()),
                unmeasured_by_class={}, types_error=sorted(tn for tn, r in out.items() if r.get("error")),
                types_without_tree=no_tree, inst_taps_not_applied=sum(len(r.get("inst_taps_not_applied") or []) for r in out.values()),
                inst_taps_off_consumer=sorted(f"{tn}:tap{x['tap']}({x['tap_name']})" for tn, r in out.items()
                                              for x in r.get("inst_taps_off_consumer") or []),
                worst=worst[:10])
    for r in out.values():
        for x in r.get("over") or []:
            k = x["cls"] if x["cls"] != "inst" else f"inst:{x.get('module')}.{x['consumer'].rsplit('.', 1)[-1]}"
            summ["legs_over_by_class"][k] = summ["legs_over_by_class"].get(k, 0) + 1
        for k, v in (r.get("unmeasured_by_class") or {}).items():
            summ["unmeasured_by_class"][k] = summ["unmeasured_by_class"].get(k, 0) + v
    return dict(schema=SCHEMA, advisory=True, bind_dir=str(bind_dir), plan=str(plan_path), cap_um=cap, kit_repoint=kit_repoint,
                summary=summ,
                tap_site_errors=cache.get("tap_errors", {}), types=out)


TSV_COLS = ("status", "type", "class", "consumer", "leaf_relay", "relay_kind", "net", "leg_um", "relay_xy", "consumer_xy", "pos_src")


def write_tsv(rep, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(TSV_COLS)
        for tn, r in sorted(rep["types"].items()):
            for x in r.get("over") or []:
                w.writerow(("OVER", tn, x["cls"], x["consumer"], x["relay"], x["relay_kind"], x["net"], x["leg_um"],
                            "%.1f,%.1f" % tuple(x["relay_xy"]), "%.1f,%.1f" % tuple(x["consumer_xy"]), x["pos_src"]))
            for x in r.get("unmeasured") or []:
                w.writerow(("UNMEASURED", tn, x["cls"], x["consumer"], x.get("relay") or "", "", x.get("net") or "", "", "", "", ""))
            if r.get("error"):
                w.writerow(("UNMEASURED", tn, "type", "", "", "", "", "", "", "", r["error"][:200]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bind_dir")
    ap.add_argument("plan")
    ap.add_argument("--out-json")
    ap.add_argument("--out-tsv")
    ap.add_argument("--cap-um", type=float, default=CAP_UM)
    ap.add_argument("--types")
    ap.add_argument("--positions", help="JSON {type: {inst: [x, y] | [[x, y], ...]}} (placed points override the plan)")
    ap.add_argument("--no-kit-repoint", action="store_true",
                    help="measure bank (ot_dp_st/ste) legs on the bound net, not the nearest tap reset_taps.tcl re-points them to")
    a = ap.parse_args(argv)
    try:
        pos = load_json(a.positions) if a.positions else {}
        rep = run(a.bind_dir, a.plan, a.cap_um, set(a.types.split(",")) if a.types else None, pos, not a.no_kit_repoint)
    except InputError as e:
        print(f"reset_leaf_legs: malformed input: {e}", file=sys.stderr)
        return 2
    if a.out_json:
        Path(a.out_json).write_text(json.dumps(rep, indent=1) + "\n")
    if a.out_tsv:
        write_tsv(rep, a.out_tsv)
    s = rep["summary"]
    print(f"reset_leaf_legs (ADVISORY): {s['types']} types, {s['types_over']} with leaf legs > {a.cap_um:g} um "
          f"({s['legs_over']} legs; {s['legs_over_as_bound']} on the bound nets before kit re-point), measured {s['measured']}, UNMEASURED {s['unmeasured']} {s['unmeasured_by_class']}, "
          f"no tree {len(s['types_without_tree'])}, inst_taps not applied {s['inst_taps_not_applied']}, "
          f"inst_taps on a non-consumer tap {s['inst_taps_off_consumer']}")
    for x in s["worst"][:5]:
        print(f"  {x['leg_um']:8.1f} um  {x['type']}  {x['cls']}  {x['consumer']}  <- {x['relay']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
