#!/usr/bin/env python3
"""station_move.py -- ONE station-move API for plan rows (STATION-MOVE-HELPER 11-24, COORD from a FABLE-RC-KV class note).

A row that moves, removes or re-seats a station must update every record derived from that station in the same op, or the bind
/ G0 finds the stale record an hour later (KV-INCORE-R2 C2T bank_taps, S81-T2-REFLOOR D2 landing edges, KV-HG-CAP export taps;
the static check is station_xref.py = PRE class STNXREF).  This module is that op.  For one ft slot (or internal-station bus) of
one type it rewrites, together:
  regs_um / stations        the station sites (type frame) and count;
  bit_sites_um              pattern j follows station j by the station's own delta (new stations take the nearest old
                            station's pattern, re-centred on the new site);
  reset.bank_taps           the slot's sinks re-derived: a station whose site did not move keeps its tap; a moved / new station
                            goes to the NEAREST plan reset-tree tap with room (bank_reset_delta rule: <= LEAF_MAX, <= REACH_UM);
                            removed stations leave; u_ft_<slot>_o_<k> renumbered with the new order;
  landing in-pins           station 0 moved -> fclk_in_<slot>_i / cland_fstart_in_<slot>_i landing_contract pins and the
                            matching clock.edge_clocks tap_um follow by the same delta (follow_pins=True, default);
  latency.lanes             every lane whose priced stations change gets cycles / stations / natural / pad / word_cycles by the
                            same delta (schema.Plan.lane_latency before vs after, the NOSEAM / stn_reprice form);
  receipt                   landing_network edges that touch a moved pin and now hop over their max_hop_um are LISTED
                            (relays are re-derived by the landing relay step, reach_relay_plan), never silently kept.

Ops (all idempotent: applying the same op to its own output changes nothing):
  move(raw, type, slot, frm, to)       the station at site frm goes to site to (no station at frm and one at to: no-op)
  remove(raw, type, slot, at)          the station at site at leaves (none there: no-op); the last station never leaves
  reseat(raw, type, slot, sites)       the slot's stations become exactly sites (count may change; same sites: no-op)
  Library: apply(raw, ops, taps_fn=None, price_fn=None) -> receipt; raw is changed in place.

CLI:  python3 -I tools/die_plan/station_move.py PLAN_IN PLAN_OUT --ops OPS.json [--receipt R.json] [--no-check]
          [--taps-from-rtl TYPE=BOUND_PART.sv ...] [--plan-path P] [--no-follow-pins]
  OPS.json = [{"op": "move", "type": T, "slot": S, "from": [x, y], "to": [x, y]},
              {"op": "remove", "type": T, "slot": S, "at": [x, y]},
              {"op": "reseat", "type": T, "slot": S, "sites": [[x, y], ...]}]   ("slot": "bus:<name>" = internal stations)
          [--no-regen] [--regen-lat DIR ...] [--regen-schedule RECEIPT.json[=SIDECAR.json] ...] [--tree TREE]
  DERIVED FILES (regen_derived, after PLAN_OUT is written): the records that live OUTSIDE the plan are regenerated from PLAN_OUT
  in the same call, so no copy-forward stays behind (HEAD w3 prep a74be4f5 package 85 values behind, S81 c8 s81_latency.json 787
  of 873 values behind, HEAD head_nf15b_schedule_1116 receipt predating the 11-19 stations):
    latency packages        every <die>_latency.json / <die>_lat_pkg.sv that latpkg_check finds under PLAN_OUT's own directory
                            (depth <= 3: its lat/ and prep dirs) with a digest != the new plan (default on, --no-regen), plus
                            every --regen-lat DIR, are rewritten by gen.write_latency (tmp + os.replace);
    schedule receipts       every --regen-schedule RECEIPT (s81_head regen_schedule_constants form) is regenerated on PLAN_OUT
                            with its recorded CA table; a landed receipt needs its sidecar (RECEIPT=SIDECAR); the sibling
                            <stem>_pkg.sv (nf15b_schedule.json -> nf15b_pkg.sv) is rewritten when present.
  Then latpkg_check (PRE LATPKG) runs on PLAN_OUT; a regeneration that fails or a package it wrote that still reads stale is
  exit 3 (PLAN_OUT itself is kept: its in-plan records are already consistent).
  After the ops it runs station_xref (STNXREF) on PLAN_OUT against PLAN_IN and prints the counts; exit 3 if a form that this
  helper owns (BANKSINK, BANKFOLLOW, BITCOUNT, BITFOLLOW, STAGECNT, LANDFOLLOW) is non-zero on the touched types (the op did
  not close its own records), else 0.  PLAN_OUT is written only on exit 0 (else PLAN_OUT.refused).
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # -I drops the script dir
TOL_UM = 1e-3
LAT_KEYS = ("cycles", "stations", "natural", "pad", "word_cycles")
OWN_FORMS = ("BANKSINK", "BANKFOLLOW", "BITCOUNT", "BITFOLLOW", "STAGECNT", "LANDFOLLOW")


class MoveError(ValueError):
    pass


def man(a, b):
    return abs(float(a[0]) - float(b[0])) + abs(float(a[1]) - float(b[1]))


def _xy(p):
    return [round(float(p[0]), 4), round(float(p[1]), 4)]


def _same(a, b, tol=TOL_UM):
    return man(a, b) <= tol


def _slot(t, slot):
    """-> (entry, kind, inst prefix): ft slot by name, or internal_stations row for 'bus:<name>'"""
    if slot.startswith("bus:"):
        rows = [e for e in t.get("internal_stations") or [] if e.get("conn") == slot]
        if len(rows) != 1:
            raise MoveError(f"{slot}: {len(rows)} internal_stations rows (need exactly 1)")
        return rows[0], "ist", f"u_ist_{slot[4:]}_"
    s = next((x for x in t.get("ft_slots") or [] if x.get("name") == slot), None)
    if s is None:
        raise MoveError(f"no ft slot {slot}")
    regs = s.get("regs_um") or []
    if len(regs) != int(s.get("stations", 1) or 1):
        raise MoveError(f"{slot}: {len(regs)} regs_um for {s.get('stations')} stations (needs one site per station)")
    return s, "ft", f"u_ft_{slot}_o_"


def _default_taps(raw, tn):
    sys.path.insert(0, str(HERE))
    import bank_reset_delta as BD
    return BD.plan_tree_taps(raw, tn)


def _limits():
    try:
        sys.path.insert(0, str(HERE))
        import bank_reset_delta as BD
        return BD.LEAF_MAX, BD.REACH_UM
    except Exception:  # noqa: BLE001 - pure tests without the reset stack
        return 32, 405.0


def _match(old, new):
    """new index -> old index of the same site (exact), else None"""
    out, used = {}, set()
    for j, q in enumerate(new):
        i = next((i for i, r in enumerate(old) if i not in used and _same(r, q)), None)
        if i is not None:
            used.add(i)
        out[j] = i
    return out


def _nearest(old, q):
    return min(range(len(old)), key=lambda i: (man(old[i], q), i))


def _reseat_entry(t, tn, slot, new_sites, taps_fn, raw, rec, follow_pins=True):
    s, kind, pre = _slot(t, slot)
    old = [tuple(map(float, r)) for r in s.get("regs_um") or []]
    new = [tuple(map(float, q)) for q in new_sites]
    if not new:
        raise MoveError(f"{tn} {slot}: a slot keeps at least one station")
    if len(new) == len(old) and all(_same(a, b) for a, b in zip(old, new)):
        return False
    if kind == "ist" and len(new) != len(old):
        raise MoveError(f"{tn} {slot}: internal-station count changes go through the ISTCYC reprice (plan_gate_pre.py reprice); "
                        f"this helper moves them only")
    m = _match(old, new)
    src = {j: (m[j] if m[j] is not None else _nearest(old, q)) for j, q in enumerate(new)}
    # bit sites: pattern j (station j >= 1) follows its station
    bits = s.get("bit_sites_um")
    if kind == "ft" and bits is not None and len(bits) == len(old) - 1:
        nb = []
        for j in range(1, len(new)):
            i = src[j] if src[j] >= 1 else min(range(1, len(old)), key=lambda k: (man(old[k], new[j]), k)) if len(old) > 1 else None
            if i is None:
                nb.append([])
                continue
            dx, dy = new[j][0] - old[i][0], new[j][1] - old[i][1]
            nb.append([[round(b[0] + dx, 4), round(b[1] + dy, 4)] for b in bits[i - 1]])
        s["bit_sites_um"] = nb
    s["regs_um"] = [_xy(q) for q in new]
    if kind == "ft":
        s["stations"] = len(new)
    rec["slots"].append(dict(type=tn, slot=slot, stations=[len(old), len(new)],
                             moved=sum(1 for j in range(len(new)) if m[j] is None)))
    # reset bank taps
    rs = t.get("reset") or {}
    bt = rs.get("bank_taps")
    if bt:
        pat = re.compile(re.escape(pre) + r"(\d+)$")
        old_tap = {}
        for r in bt:
            for x in r.get("sinks") or []:
                mm = pat.fullmatch(x)
                if mm:
                    old_tap[int(mm.group(1))] = r["tap"]
            r["sinks"] = [x for x in r.get("sinks") or [] if not pat.fullmatch(x)]
        load = {r["tap"]: len(r["sinks"]) for r in bt}
        leaf_max, reach = _limits()
        taps = None
        for j, q in enumerate(new):
            inst = f"{pre}{j}"
            keep = old_tap.get(m[j]) if m[j] is not None else None
            if keep is not None:
                tap = keep
            elif not old_tap:
                continue                                  # the slot had no bank rows: nothing derived to update
            else:
                if taps is None:
                    taps = taps_fn(raw, tn)
                order = sorted(taps, key=lambda i: (man(taps[i], q), i))
                tap = next((i for i in order if load.get(i, 0) < leaf_max), None)
                if tap is None or man(taps[tap], q) > reach + 1e-6:
                    raise MoveError(f"{tn} {inst} at {_xy(q)}: no reset-tree tap with room within {reach} um")
                rec["bank"].append(dict(type=tn, inst=inst, tap=tap, hop_um=round(man(taps[tap], q), 1)))
            row = next((r for r in bt if r["tap"] == tap), None)
            if row is None:
                row = {"tap": tap, "sinks": []}
                bt.append(row)
            row["sinks"].append(inst)
            load[tap] = load.get(tap, 0) + 1
        rs["bank_taps"] = sorted([r for r in bt if r["sinks"]], key=lambda r: r["tap"])
    # landing in-pins follow station 0
    if kind == "ft" and follow_pins and not _same(old[0], new[0]):
        dx, dy = new[0][0] - old[0][0], new[0][1] - old[0][1]
        ck = t.get("clock") or {}
        names = {f"fclk_in_{slot}_i", f"cland_fstart_in_{slot}_i"}
        for p in (ck.get("landing_contract") or {}).get("pins") or []:
            if p.get("name") in names and p.get("xy_um"):
                p["xy_um"] = _xy((p["xy_um"][0] + dx, p["xy_um"][1] + dy))
                rec["pins"].append(dict(type=tn, pin=p["name"], xy_um=p["xy_um"]))
        for e in ck.get("edge_clocks") or []:
            if e.get("port") in names and e.get("tap_um"):
                e["tap_um"] = _xy((e["tap_um"][0] + dx, e["tap_um"][1] + dy))
    return True


def _norm_ops(ops):
    out = []
    for o in ops:
        if o.get("op") not in ("move", "remove", "reseat"):
            raise MoveError(f"unknown op {o.get('op')!r}")
        for k in ("type", "slot"):
            if not o.get(k):
                raise MoveError(f"op {o['op']} needs {k}")
        out.append(o)
    return out


def _target(t, o):
    s, _, _ = _slot(t, o["slot"])
    regs = [tuple(map(float, r)) for r in s.get("regs_um") or []]
    if o["op"] == "reseat":
        return o["sites"]
    if o["op"] == "move":
        i = next((i for i, r in enumerate(regs) if _same(r, o["from"])), None)
        if i is None:
            if any(_same(r, o["to"]) for r in regs):
                return regs                               # already moved: idempotent no-op
            raise MoveError(f"{o['type']} {o['slot']}: no station at {o['from']}")
        return regs[:i] + [tuple(o["to"])] + regs[i + 1:]
    i = next((i for i, r in enumerate(regs) if _same(r, o["at"])), None)
    if i is None:
        return regs                                       # already removed: idempotent no-op
    return regs[:i] + regs[i + 1:]


def default_price(raw, plan_path=None):
    """{lane: schema.Plan.lane_latency}; plan_path = where the plan lives (relative inputs: sink bins, tap files)"""
    sys.path.insert(0, str(HERE))
    import schema as S
    P = S.Plan(raw, plan_path) if plan_path else S.Plan(raw)
    return {lid: P.lane_latency(lid) for lid in P.lanes}


def apply(raw, ops, taps_fn=None, price_fn=None, follow_pins=True, plan_path=None):
    """apply ops to raw IN PLACE -> receipt dict(slots, bank, pins, lanes, edges_over)."""
    ops = _norm_ops(ops)
    taps_fn = taps_fn or _default_taps
    rec = dict(slots=[], bank=[], pins=[], lanes={}, edges_over=[], types=sorted({o["type"] for o in ops}))
    lanes = (raw.get("latency") or {}).get("lanes")
    need_price = False
    for o in ops:
        t = (raw.get("partition_types") or {}).get(o["type"])
        if t is None:
            raise MoveError(f"no type {o['type']}")
        s, _, _ = _slot(t, o["slot"])
        n0 = len(s.get("regs_um") or [])
        if n0 != len(_target(t, o)):
            need_price = True
    price = price_fn or (lambda r: default_price(r, plan_path))
    before = price(raw) if (lanes and need_price) else None
    changed = False
    for o in ops:
        t = raw["partition_types"][o["type"]]
        changed |= _reseat_entry(t, o["type"], o["slot"], _target(t, o), taps_fn, raw, rec, follow_pins)
    if before is not None and changed:
        after = price(raw)
        for lid, b in before.items():
            a = after.get(lid)
            if not a or lid not in lanes or a.get("stations") == b.get("stations"):
                continue
            row = dict(lanes[lid])
            for k in LAT_KEYS:
                if k in row and k in a and k in b:
                    row[k] = row[k] + a[k] - b[k]
            rec["lanes"][lid] = [lanes[lid].get("cycles"), row.get("cycles")]
            lanes[lid] = row
    try:
        sys.path.insert(0, str(HERE))
        import station_xref as SX
        F = SX._Frame(raw)
        moved = {(p["type"], p["pin"]) for p in rec["pins"]}
        if moved:
            ptype = {p["name"]: p.get("type") for p in raw.get("partitions") or []}
            for e in ((raw.get("clock") or {}).get("landing_network") or {}).get("edges") or []:
                ends = {(ptype.get(e["src"]["part"]), e["src"]["bus"]), (ptype.get(e["dst"]["part"]), e["dst"]["bus"])}
                if ends & moved:
                    hs = SX._edge_hops(F, e)
                    if hs and max(hs) > float(e.get("max_hop_um") or 405) + 1e-3:
                        rec["edges_over"].append(dict(id=e.get("id"), hop_um=round(max(hs), 1)))
    except Exception as e:  # noqa: BLE001
        rec["edges_note"] = f"edge scan skipped: {type(e).__name__}: {e}"
    return rec


def _replace_from(tmp_file, dst):
    """copy+mv: the new content lands next to dst, then one os.replace (readers never see a half file)"""
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, part = tempfile.mkstemp(prefix=f".{dst.name}.", dir=dst.parent)
    with os.fdopen(fd, "wb") as w:
        w.write(Path(tmp_file).read_bytes())
    os.replace(part, dst)


def regen_latency(raw, dirs):
    """gen.write_latency of raw into every dir (atomic per file) -> [dict(kind, path, digest)]"""
    import gen
    out = []
    for d in sorted({Path(x) for x in dirs}):
        with tempfile.TemporaryDirectory(prefix="stnmove_lat_") as td:
            try:
                _, sv, js = gen.write_latency(raw, td)
            except SystemExit as e:
                raise MoveError(f"latency package regeneration refused: {e}") from None
            for f in (sv, js):
                _replace_from(f, d / f.name)
                out.append(dict(kind="latency", path=str(d / f.name), digest=gen.plan_digest(raw)))
    return out


def regen_schedule(raw, plan_out, receipt, sidecar=None):
    """regenerate one regen_schedule_constants receipt on plan_out (its recorded CA table) -> dict(kind, path, lanes_changed)"""
    sys.path.insert(0, str(HERE.parent / "s81_head"))
    import regen_schedule_constants as RS
    receipt = Path(receipt)
    old = json.loads(receipt.read_text())
    inp = old.get("inputs") or {}
    ca = json.loads(Path(inp["ca"]).read_text()) if inp.get("ca") else None
    landed = json.loads(Path(sidecar).read_text()) if sidecar else None
    if inp.get("landed_sidecar_sha256") and landed is None:
        raise MoveError(f"{receipt}: a landed-sidecar receipt; pass --regen-schedule {receipt}=SIDECAR.json")
    try:
        new = RS.generate(raw, ca, landed)
    except ValueError as e:
        raise MoveError(f"{receipt}: {e}") from None
    new["inputs"] = dict(plan=str(plan_out), plan_sha256=hashlib.sha256(Path(plan_out).read_bytes()).hexdigest(),
                         ca=inp.get("ca"))
    if landed is not None:
        new["inputs"]["landed_sidecar_sha256"] = hashlib.sha256(Path(sidecar).read_bytes()).hexdigest()
        new["plan_delta"] = RS.delta(RS.generate(raw), new)
    new["regenerated_by"] = dict(tool="tools/die_plan/station_move.py", previous_plan_sha256=inp.get("plan_sha256"))
    changed = sorted(l for l in set(new["lanes"]) | set(old.get("lanes") or {})
                     if (old.get("lanes") or {}).get(l, {}).get("cycles") != new["lanes"].get(l, {}).get("cycles"))
    with tempfile.TemporaryDirectory(prefix="stnmove_sched_") as td:
        tj = Path(td) / receipt.name
        tj.write_text(json.dumps(new, indent=2) + "\n")
        _replace_from(tj, receipt)
        pkg = receipt.with_name(receipt.name[:-len("_schedule.json")] + "_pkg.sv") if receipt.name.endswith("_schedule.json") else None
        if pkg is not None and pkg.is_file():
            ts = Path(td) / pkg.name
            ts.write_text(RS.sv(new))
            _replace_from(ts, pkg)
    return dict(kind="schedule", path=str(receipt), lanes_changed=len(changed), changed=changed[:20])


def regen_derived(raw, plan_out, near=True, lat_dirs=(), schedules=(), tree=None):
    """regenerate every out-of-plan record derived from plan_out (written already) -> dict(files, latpkg)

    schedules = [(receipt, sidecar or None)].  Library form of the CLI's DERIVED FILES step."""
    import gen
    import latpkg_check as LP
    dirs = {Path(d) for d in lat_dirs}
    if near:
        own, dig, die = Path(plan_out).resolve().parent, gen.plan_digest(raw), LP.die_name(raw)
        for f in LP.find_packages(plan_out, tree):
            pk = LP.read_package(f)
            if pk and own in f.resolve().parents and pk.get("digest") != dig and (not die or pk.get("die") in (None, die)):
                dirs.add(f.parent)
    files = regen_latency(raw, dirs) if dirs else []
    files += [regen_schedule(raw, plan_out, r, sc) for r, sc in schedules]
    lines = LP.findings(raw, plan_out, tree, [str(d) for d in dirs], want_readers=False)
    dig = gen.plan_digest(raw)
    still = [f["path"] for f in files if f["kind"] == "latency" and (LP.read_package(Path(f["path"])) or {}).get("digest") != dig]
    return dict(files=files, latpkg=lines, stale_after=still)


def _dump_like(raw, text):
    """keep the input's indent style (compact plans stay compact)"""
    ind = 1 if text.startswith("{\n ") and not text.startswith("{\n  ") else (2 if text.startswith("{\n  ") else None)
    return json.dumps(raw, indent=ind, ensure_ascii=False) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan_in")
    ap.add_argument("plan_out")
    ap.add_argument("--ops", required=True)
    ap.add_argument("--receipt")
    ap.add_argument("--no-check", action="store_true")
    ap.add_argument("--no-follow-pins", action="store_true")
    ap.add_argument("--taps-from-rtl", action="append", default=[], metavar="TYPE=PART.sv",
                    help="reset-tree tap sites of TYPE from a bound RTL of the same tree (bank_reset_delta.tree_taps) instead of a "
                         "reset_tree solve with this tree's tools (use when the plan was built with another rt)")
    ap.add_argument("--plan-path", help="path schema.Plan resolves relative plan inputs against (default PLAN_IN)")
    ap.add_argument("--no-regen", action="store_true", help="do not regenerate the stale latency packages under PLAN_OUT's dir")
    ap.add_argument("--regen-lat", action="append", default=[], metavar="DIR", help="also (re)write the latency package here")
    ap.add_argument("--regen-schedule", action="append", default=[], metavar="RECEIPT[=SIDECAR]",
                    help="regenerate this schedule receipt (regen_schedule_constants form) on PLAN_OUT")
    ap.add_argument("--tree", help="tree root for latpkg_check (default: found from PLAN_OUT)")
    a = ap.parse_args(argv)
    text = Path(a.plan_in).read_text()
    raw = json.loads(text)
    try:
        rtl = dict(x.split("=", 1) for x in a.taps_from_rtl)
        taps_fn = None
        if rtl:
            import bank_reset_delta as BD

            def taps_fn(r, tn):
                return BD.tree_taps(Path(rtl[tn]).read_text()) if tn in rtl else _default_taps(r, tn)
        rec = apply(raw, json.loads(Path(a.ops).read_text()), taps_fn=taps_fn, follow_pins=not a.no_follow_pins,
                    plan_path=a.plan_path or a.plan_in)
    except MoveError as e:
        print(f"STATION-MOVE REFUSED: {e}", file=sys.stderr)
        return 3
    rc = 0
    if not a.no_check:
        import station_xref as SX
        base = json.loads(text)
        lines = SX.findings(raw, base, a.plan_path or a.plan_in, forms=SX.FORMS)
        own = [x for x in lines if any(x.startswith(f"WARN STNXREF-{f} ") for f in OWN_FORMS)
               and any(f" {tn}" in x for tn in rec["types"])
               and not any(x.startswith(f"WARN STNXREF-BANKFOLLOW {b['type']}: {b['inst']} ") for b in rec["bank"])]   # re-derived here: its nearest tap may be the old one
        rec["stnxref"] = lines
        print("\n".join(x for x in lines if x.startswith("LIST ")))
        if own:
            print("STATION-MOVE REFUSED: the op left its own derived records stale:\n  " + "\n  ".join(own[:12]), file=sys.stderr)
            rc = 3
    out = Path(a.plan_out) if rc == 0 else Path(a.plan_out + ".refused")
    out.write_text(_dump_like(raw, text))
    if rc == 0 and (not a.no_regen or a.regen_lat or a.regen_schedule):
        try:
            sch = [tuple(x.split("=", 1)) if "=" in x else (x, None) for x in a.regen_schedule]
            rg = regen_derived(raw, out, near=not a.no_regen, lat_dirs=a.regen_lat, schedules=sch, tree=a.tree)
        except MoveError as e:
            print(f"STATION-MOVE REFUSED: derived-file regeneration: {e}", file=sys.stderr)
            rg, rc = dict(files=[], latpkg=[], stale_after=[], error=str(e)), 3
        rec["derived"] = rg
        for f in rg["files"]:
            print(f"REGEN {f['kind']} {f['path']}" + (f" lanes changed {f['lanes_changed']}" if "lanes_changed" in f else ""))
        print("\n".join(x for x in rg["latpkg"] if x.startswith("LIST ")))
        if rg["stale_after"]:
            print("STATION-MOVE REFUSED: regenerated packages still stale:\n  " + "\n  ".join(rg["stale_after"]), file=sys.stderr)
            rc = 3
    if a.receipt:
        Path(a.receipt).write_text(json.dumps(rec, indent=1) + "\n")
    print(f"STATION-MOVE {'OK' if rc == 0 else 'REFUSED'} slots {len(rec['slots'])} bank re-derived {len(rec['bank'])} pins {len(rec['pins'])} "
          f"lanes repriced {len(rec['lanes'])} edges over hop {len(rec['edges_over'])} derived files {len((rec.get('derived') or {}).get('files', []))} -> {out}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
