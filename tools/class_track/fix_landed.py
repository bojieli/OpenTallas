#!/usr/bin/env python3
"""fix_landed.py -- FIX-LANDED audit (CLASS-TRACK, OWNER 11-25/26 class workflow).  REPORT ONLY.

For every scope adopted at a cut, check that its pieces reached the BUILT kit: seats, relay sites, stations, taps, tap groups and
the kit-original `source` lines of clock_taps.tcl (P-CLOCK-TAPS-COPY: a kit refresh from main silently dropped them).

    scope  = (scope_id, die, base_sha, plan, adopted_epoch, types)   one JSON list, or --plan alone = every type of the live plan,
             adopted when the plan file was written, base_sha = the plan's own sha256 prefix.
    kit    = a generated kit dir  <...>/gen/<type>/  (budget.json, clock_taps.tcl, istations.tcl, plan_pins.json ...); the newest
             kit per type wins.  Post-place DB evidence: a 3_place.odb under the kit's job dir (column `placed`).

Status per (scope, type, op class):
    LANDED         every expected item found in the kit
    NOT-LANDED     the kit was built after the scope was adopted and an expected item is missing / different
    NOT-YET-BUILT  no kit of the type, or the newest kit is older than the scope (it cannot contain it)
`stale_base` = 1 when the kit's recorded plan sha (budget.json io_hold.plan_sha256, kit_preflight plan sha) is not the scope base.

    fix_landed.py --plan PLAN [--scope-file S.json] --kit-root ROOT [--kit-root ROOT ...] [--out FIX-LANDED.tsv]

Fleet form (kits live on many hosts; the 100 MB plan stays on one):
    fix_landed.py extract --plan PLAN --die S81 --out expected.json         (small; ship to every kit host)
    fix_landed.py audit   --expected expected.json --kit-root ROOT ... --out host.tsv      (on each host, via ot-run)
    fix_landed.py merge   --out FIX-LANDED.tsv host1.tsv host2.tsv ...      (newest kit per type across hosts)
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys

COLS = ["scope_id", "die", "type", "op_class", "expected", "found", "status", "stale_base", "placed", "kit", "kit_mtime",
        "scope_epoch", "detail"]
LANDED, NOT_LANDED, NOT_YET = "LANDED", "NOT-LANDED", "NOT-YET-BUILT"
SRC_RE = re.compile(r"^\s*source\s+(/work/\S+\.tcl)", re.M)
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def sha12(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:12]


def find_kits(roots):
    """newest kit gen dir per type under the roots: a dir holding budget.json + clock_taps.tcl whose parent is 'gen'."""
    best = {}
    for root in roots:
        for dp, dns, fns in os.walk(root):
            if "clock_taps.tcl" in fns and "budget.json" in fns and os.path.basename(os.path.dirname(dp)) == "gen":
                t = os.path.basename(dp)
                m = os.path.getmtime(os.path.join(dp, "clock_taps.tcl"))
                if t not in best or m > best[t][0]:
                    best[t] = (m, dp)
                dns[:] = []  # a kit dir: never descend into it
                continue
            if dp.count(os.sep) - root.count(os.sep) > 9:
                dns[:] = []
            else:
                dns[:] = [d for d in dns if d not in ("results", "objects", "logs", "reports", "macros", "__pycache__")]
    return best


def placed(kit):
    job = os.path.dirname(os.path.dirname(kit))
    for dp, dns, fns in os.walk(job):
        if "3_place.odb" in fns:
            return 1
        if dp.count(os.sep) - job.count(os.sep) > 5:
            dns[:] = []
    return 0


def read(path):
    try:
        with open(path, errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def nums(text):
    return {float(x) for x in NUM_RE.findall(text)}


def kit_plan_sha(kit):
    try:
        b = json.load(open(os.path.join(kit, "budget.json")))
        s = (b.get("io_hold") or {}).get("plan_sha256")
        if s:
            return s[:12]
    except (OSError, ValueError):
        pass
    for fn in os.listdir(kit):
        if fn.startswith("kit_preflight") and fn.endswith(".json"):
            m = re.search(r'"plan_sha(?:256)?":\s*"([0-9a-f]{12,64})', read(os.path.join(kit, fn)))
            if m:
                return m.group(1)[:12]
    return ""


def expected_items(entry):
    """op class -> list of expected items from one plan partition_types entry."""
    clk = entry.get("clock") or {}
    ex = {}
    ex["taps"] = [(t.get("name"), tuple(t.get("xy") or ())) for t in clk.get("taps", [])]
    tg = entry.get("tap_group") or {}
    items = [("fixed", k, v) for k, v in (tg.get("fixed_taps") or {}).items()]
    items += [("re", k, "") for k in tg if k not in ("fixed_taps", "note")]
    ex["tap_groups"] = items
    ex["stations"] = [(s.get("conn"), tuple(map(tuple, s.get("regs_um") or []))) for s in entry.get("internal_stations", [])]
    rs = entry.get("relay_sites") or {}
    ex["relay_sites"] = [(k, tuple(v)) for k, v in rs.items() if isinstance(v, (list, tuple)) and len(v) == 2]
    seats = []
    for st in ("landing_reader_start", "landing_writer_start"):
        for br in ((clk.get(st) or {}).get("branches") or {}).values():
            for s in br.get("stages", []):
                if s.get("xy_um"):
                    seats.append((s.get("raw_reset") or "", tuple(s["xy_um"])))
    for e in entry.get("reset_start_raw_exports", []) or []:
        if e.get("xy_um"):
            seats.append((e.get("net") or e.get("instance") or "", tuple(e["xy_um"])))
    ex["seats"] = seats
    return ex


def freeze(ex):
    """JSON-safe form of expected_items() (tuples -> lists) and back."""
    return {k: [list(map(lambda v: list(map(list, v)) if v and isinstance(v[0], (list, tuple)) else (list(v) if isinstance(v, tuple) else v), i))
                for i in items] for k, items in ex.items()}


def thaw(ex):
    def t(v):
        return tuple(t(x) for x in v) if isinstance(v, list) else v
    return {k: [t(i) for i in items] for k, items in ex.items()}


def check_type(kit, ex):
    """-> list of (op_class, expected_n, found_n, detail).  Pure file reads of the kit dir."""
    out = []
    ct = read(os.path.join(kit, "clock_taps.tcl"))
    ist = read(os.path.join(kit, "istations.tcl"))
    # 1. kit-original source lines of clock_taps.tcl (the two known silent undos)
    want = ["/work/vpw_bank_clock.tcl"]
    for extra in ("landing_exports.tcl", "phy_clock_export_source.tcl"):
        if os.path.exists(os.path.join(kit, extra)) or os.path.exists(os.path.join(kit, "..", "..", extra)):
            want.append("/work/" + extra)
    have = set(SRC_RE.findall(ct)) | {w for w in want if w in ct}
    miss = [w for w in want if w not in have]
    out.append(("clock_taps_source", len(want), len(want) - len(miss), "missing " + ",".join(miss) if miss else ""))
    # 2. taps: plan clock.taps vs the kit's budget.json clock.taps (name + xy)
    try:
        kt = {(t["name"], tuple(t["xy"])) for t in json.load(open(os.path.join(kit, "budget.json")))["clock"]["taps"]}
    except (OSError, ValueError, KeyError):
        kt = set()
    pt = ex["taps"]
    f = sum(1 for t in pt if t in kt)
    out.append(("taps", len(pt), f, f"{len(pt) - f} plan taps not in kit budget.json" if f != len(pt) else ""))
    # 3. tap groups: the group regex / fixed tap name appears in the kit's clock_taps.tcl
    tgs = ex["tap_groups"]
    f = sum(1 for kind, k, v in tgs if (k in ct) and (kind == "re" or v in ct))
    out.append(("tap_groups", len(tgs), f, ""))
    # 4. stations: conn tag in istations.tcl and every register site coordinate present in the kit's istations / ft site tables
    stn = ex["stations"]
    pool = nums(ist) | nums(read(os.path.join(kit, "ft_bit_sites.tcl"))) | nums(read(os.path.join(kit, "ft_stations.txt")))
    f = 0
    for conn, regs in stn:
        tag = (conn or "").split(":", 1)[-1]
        if tag in ist and all(c in pool for r in regs for c in r):
            f += 1
    out.append(("stations", len(stn), f, "conn tag + register coordinates (loose number match)"))
    # 5. relay sites and 6. seats: coordinate pairs present in any kit text (loose number match, exact-instance match when named)
    allt = "".join(read(os.path.join(kit, n)) for n in ("relay_mid.tcl", "reset_tree.tcl", "ot_rst_copies.tcl", "istations.tcl",
                                                       "relay_polylines.txt", "ft_bit_sites.tcl"))
    pool2 = nums(allt)
    for oc, items in (("relay_sites", ex["relay_sites"]), ("seats", ex["seats"])):
        f = sum(1 for name, xy in items if all(c in pool2 for c in xy))
        out.append((oc, len(items), f, "coordinate pair present in the kit tcl (loose number match)"))
    return out


def audit(scopes, plan_types, kits, kit_filter=None):
    """plan_types: {type: partition_types entry}  or  {type: thawed expected dict} (from `extract`)."""
    rows = []
    for sc in scopes:
        for t in sc["types"]:
            entry = plan_types.get(t)
            if entry is None:
                continue
            k = kits.get(t)
            ex = entry if "taps" in entry and "relay_sites" in entry and "clock" not in entry else expected_items(entry)
            if k is None or k[0] < sc["adopted_epoch"]:
                for oc, items in ex.items():
                    rows.append(_row(sc, t, oc, len(items), 0, NOT_YET, 0, "", k, "no kit" if k is None else "kit older than scope"))
                rows.append(_row(sc, t, "clock_taps_source", 1, 0, NOT_YET, 0, "", k, "no kit" if k is None else "kit older than scope"))
                continue
            kp = kit_plan_sha(k[1])
            stale = int(bool(kp) and kp != sc["base_sha"][:12])
            for oc, n, f, detail in check_type(k[1], ex):
                if n == 0:
                    continue
                rows.append(_row(sc, t, oc, n, f, LANDED if f == n else NOT_LANDED, stale, kp, k, detail, placed(k[1])))
    return rows


def _row(sc, t, oc, n, f, status, stale, kp, k, detail, pl=0):
    return {"scope_id": sc["scope_id"], "die": sc["die"], "type": t, "op_class": oc, "expected": n, "found": f, "status": status,
            "stale_base": stale, "placed": pl, "kit": k[1] if k else "", "kit_mtime": int(k[0]) if k else "",
            "scope_epoch": int(sc["adopted_epoch"]), "detail": (detail + (f" kit_plan={kp}" if kp else "")).strip()}


def load_scopes(a, plan_types):
    if a.scope_file:
        sc = json.load(open(a.scope_file))
        for s in sc:
            s.setdefault("types", sorted(plan_types))
            s.setdefault("adopted_epoch", os.path.getmtime(a.plan))
        return sc
    return [{"scope_id": a.scope_id or ("plan-" + sha12(a.plan)), "die": a.die, "base_sha": sha12(a.plan), "plan": a.plan,
             "adopted_epoch": os.path.getmtime(a.plan), "types": sorted(plan_types)}]


def merge(paths):
    """one row set from several per-host TSVs: per (scope, type, op_class) the row with the newest kit; NOT-YET-BUILT wins only
    when no host has a kit newer than the scope."""
    best = {}
    for p in paths:
        with open(p, newline="") as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                k = (r["scope_id"], r["type"], r["op_class"])
                rank = (1 if r["kit"] else 0, int(r["kit_mtime"] or 0) if r["status"] != NOT_YET else -1)
                if k not in best or rank > best[k][0]:
                    best[k] = (rank, r)
    return [v[1] for _, v in sorted(best.items())]


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "extract":
        ap = argparse.ArgumentParser(prog="fix_landed extract", description="plan -> small expected.json shipped to kit hosts")
        ap.add_argument("--plan", required=True)
        ap.add_argument("--die", required=True)
        ap.add_argument("--out", required=True)
        a = ap.parse_args(argv[1:])
        pt = json.load(open(a.plan)).get("partition_types") or {}
        doc = {"die": a.die, "plan": a.plan, "base_sha": sha12(a.plan), "adopted_epoch": os.path.getmtime(a.plan),
               "types": {t: freeze(expected_items(e)) for t, e in pt.items()}}
        json.dump(doc, open(a.out, "w"))
        print(f"{a.die} {len(pt)} types base {doc['base_sha']}")
        return 0
    if argv and argv[0] == "merge":
        ap = argparse.ArgumentParser(prog="fix_landed merge")
        ap.add_argument("--out", required=True)
        ap.add_argument("tsv", nargs="+")
        a = ap.parse_args(argv[1:])
        rows = merge(a.tsv)
        with open(a.out, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS, delimiter="\t", lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        from collections import Counter
        print("FIX-LANDED merged " + ", ".join(f"{k}={v}" for k, v in sorted(Counter(r["status"] for r in rows).items())) +
              f"; stale_base={sum(int(r['stale_base']) for r in rows)}")
        return 0
    if argv and argv[0] == "audit":
        ap = argparse.ArgumentParser(prog="fix_landed audit")
        ap.add_argument("--expected", required=True)
        ap.add_argument("--kit-root", action="append", default=[])
        ap.add_argument("--out", required=True)
        a = ap.parse_args(argv[1:])
        doc = json.load(open(a.expected))
        sc = [{"scope_id": "plan-" + doc["base_sha"], "die": doc["die"], "base_sha": doc["base_sha"], "plan": doc["plan"],
               "adopted_epoch": doc["adopted_epoch"], "types": sorted(doc["types"])}]
        rows = audit(sc, {t: thaw(e) for t, e in doc["types"].items()}, find_kits(a.kit_root))
        with open(a.out, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS, delimiter="\t", lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        print(f"{doc['die']} rows {len(rows)} kits {len(find_kits(a.kit_root))}")
        return 0
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--die", default="")
    ap.add_argument("--scope-id", default="")
    ap.add_argument("--scope-file", default="")
    ap.add_argument("--kit-root", action="append", default=[])
    ap.add_argument("--types", default="", help="comma list: limit the scope to these types")
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    plan = json.load(open(a.plan))
    pt = plan.get("partition_types") or {}
    scopes = load_scopes(a, pt)
    if a.types:
        keep = set(a.types.split(","))
        for s in scopes:
            s["types"] = [t for t in s["types"] if t in keep]
    kits = find_kits(a.kit_root)
    rows = audit(scopes, pt, kits)
    fh = open(a.out, "w", newline="") if a.out else sys.stdout
    w = csv.DictWriter(fh, fieldnames=COLS, delimiter="\t", lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    if a.out:
        fh.close()
    from collections import Counter
    c = Counter((r["op_class"], r["status"]) for r in rows)
    print("FIX-LANDED " + ", ".join(f"{k[0]}:{k[1]}={v}" for k, v in sorted(c.items())) +
          f"; stale_base={sum(r['stale_base'] for r in rows)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
