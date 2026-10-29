#!/usr/bin/env python3
"""DIE-HBM-19 (COORD ruling DIE-HBM-18-PARK (3), 'plan follows source'): opt-in plan delta that removes a PATH-HBM-R9
service-quadrant duplicate (__q0 / __q1 full-outline copy) of a hub hard-core family for which the as-built source has
ONE instance per hub.  A plan not passed through it is unchanged.

  drop_dup_copies.py PLAN_DIR OUT_DIR --family u_sucore_Q [--family ...] [--keep auto|q0|q1] [--hubs q_hub_ne,q_hub_nw]

Per hub type and family:
  keep     auto = the copy that minimises the summed Manhattan length of every station end retargeted onto it
           (locality first, 12.13); the other copy is dropped.
  stations every internal station end on the dropped copy (launch/capture == family or family.<port>, segment index
           of that end == dropped copy) is moved to the same pin on the kept copy (pin frame mapped through both
           orients; both copies share module + outline + pins_file); r9_segments end index -> kept index; the
           station is re-routed with hub_repack.route_station (reach 360, registers on free lattice) with at least
           its old register count; a station that becomes an exact duplicate (same launch/capture/ends) is removed.
  clock    the dropped copy's clock tap is removed.
Writes OUT_DIR/die_plan.json + drop_dup_report.json (everything else hard-linked).  Plan arithmetic: UNCHECKED until
NUMBER-CHECK (12.9f) except counts.
"""
import argparse, collections, hashlib, json, os, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve()


def _orient_pt(o, w, h, x, y):
    return {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o]


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def r3(v):
    return round(v, 3)


def run(plan_dir, out_dir, families, keep="auto", hubs=("q_hub_ne", "q_hub_nw"), tools=None, route=True):
    sys.path.insert(0, str(tools))
    import hub_repack as HR
    import check as CK
    plan_dir, out_dir = Path(plan_dir), Path(out_dir)
    raw = (plan_dir / "die_plan.json").read_bytes()
    P = json.loads(raw)
    rep = dict(schema="opentallas.hbm.drop_dup_copies.v1", source_plan_sha256=hashlib.sha256(raw).hexdigest(),
               families=families, keep=keep, hubs={})
    for tn in hubs:
        t = P["partition_types"][tn]
        W, H = t["outline_um"]
        hrep = rep["hubs"][tn] = {}
        for fam in families:
            cp = {k: next((h for h in t["hard_cores"] if h["inst"] == f"{fam}__q{k}"), None) for k in (0, 1)}
            if not all(cp.values()):
                hrep[fam] = dict(skipped="no __q0/__q1 pair")
                continue
            assert cp[0]["module"] == cp[1]["module"], fam
            assert all(abs(a - b) < 0.01 for a, b in zip(cp[0]["outline_um"], cp[1]["outline_um"])), fam
            w, h = cp[0]["outline_um"]
            same_pins = cp[0].get("pins_file") == cp[1].get("pins_file") and cp[0].get("pins") == cp[1].get("pins")
            ptab = {}
            if not same_pins:
                for k in (0, 1):
                    acc = collections.defaultdict(list)
                    for nm, _ly, x, y in CK.core_pins(cp[k], plan_dir):
                        acc[nm.split("[")[0]].append((x, y))
                    ptab[k] = {n: (sum(a for a, _ in v) / len(v), sum(b for _, b in v) / len(v)) for n, v in acc.items()}

            def ends(s):
                out = []
                seg = s.get("r9_segments") or []
                for i, key, pt in ((0, "launch", "from_um"), (1, "capture", "to_um")):
                    n = s.get(key, "")
                    if (n == fam or n.startswith(fam + ".")) and len(seg) == 2:
                        out.append((i, key, pt, seg[i]))
                return out

            def moved(p, src, dst, port=None):
                lx, ly = _orient_pt(src.get("orient", "R0"), w, h, p[0] - src["origin_um"][0], p[1] - src["origin_um"][1])
                if not same_pins and port is not None:   # port-less end (core-level conn): orient mapping only
                    ks, kd = (0 if src is cp[0] else 1), (0 if dst is cp[0] else 1)
                    if port not in ptab[ks] or port not in ptab[kd]:
                        raise SystemExit(f"{fam}: per-copy pins differ and port {port!r} not in both pin tables")
                    lx += ptab[kd][port][0] - ptab[ks][port][0]
                    ly += ptab[kd][port][1] - ptab[ks][port][1]
                x, y = _orient_pt(dst.get("orient", "R0"), w, h, lx, ly)
                return (r3(dst["origin_um"][0] + x), r3(dst["origin_um"][1] + y))

            def port_of(n):
                return n[len(fam) + 1:] if n.startswith(fam + ".") else None

            cost = {}
            for kk in (0, 1):
                d = 1 - kk
                c = 0.0
                for s in t["internal_stations"]:
                    for i, key, pt, k in ends(s):
                        if k == d:
                            other = s["to_um" if i == 0 else "from_um"]
                            c += man(moved(s[pt], cp[d], cp[kk], port_of(s[key])), other)
                cost[kk] = r3(c)
            kk = (min(cost, key=cost.get) if keep == "auto" else int(keep[1]))
            d = 1 - kk
            kept, drop = cp[kk], cp[d]
            R = None
            if route:
                cores = [x for x in t["hard_cores"] if x is not drop]
                R = HR.Raster(W, H, [HR._core_rect(x) for x in cores])
            st = dict(kept=kept["inst"], dropped=drop["inst"], cost_um=cost, stations_moved=0, duplicates_removed=0,
                      regs_old=0, regs_new=0, latency_up=0, latency_up_hist=collections.Counter(), failed=0,
                      length_old_um=0.0, length_new_um=0.0)
            new_st, seen = [], set()
            for s in t["internal_stations"]:
                e = [x for x in ends(s) if x[3] == d]
                if e:
                    s = dict(s)
                    seg = list(s["r9_segments"])
                    for i, key, pt, k in e:
                        s[pt] = list(moved(s[pt], drop, kept, port_of(s[key])))
                        seg[i] = kk
                    s["r9_segments"] = seg
                    st["stations_moved"] += 1
                    n_old = len(s.get("regs_um", []))
                    st["regs_old"] += n_old
                    st["length_old_um"] += man(s["from_um"], s["to_um"])  # straight-line lower bound after the move
                    if route:
                        res = HR.route_station(R, tuple(s["from_um"]), tuple(s["to_um"]), n_old, 360.0)
                        if res is None:
                            st["failed"] += 1
                            st["regs_new"] += n_old
                        else:
                            s["regs_um"] = [list(r) for r in res["regs"]]
                            st["regs_new"] += len(res["regs"])
                            st["length_new_um"] += res["length_um"]
                            dd = len(res["regs"]) - n_old
                            if dd > 0:
                                st["latency_up"] += 1
                                st["latency_up_hist"][dd] += 1
                            s["note"] = (s.get("note", "") + f" | DIE-HBM-19 drop_dup: {drop['inst']} -> {kept['inst']} "
                                         f"({res['kind']}, {res['length_um']} um, {len(res['regs'])} st)")
                sig = json.dumps([s.get("launch"), s.get("capture"), s["from_um"], s["to_um"], s.get("bits")])
                if e and sig in seen:
                    st["duplicates_removed"] += 1
                    continue
                seen.add(sig)
                new_st.append(s)
            t["internal_stations"] = new_st
            t["hard_cores"] = [x for x in t["hard_cores"] if x is not drop]
            ck = t.get("clock", {})
            nt = len(ck.get("taps", []))
            ck["taps"] = [x for x in ck.get("taps", []) if x.get("name") != drop["inst"]]
            st["taps_removed"] = nt - len(ck.get("taps", []))
            st["latency_up_hist"] = dict(sorted(st["latency_up_hist"].items()))
            st["length_old_um"] = r3(st["length_old_um"]); st["length_new_um"] = r3(st["length_new_um"])
            hrep[fam] = st
        t["note"] = t.get("note", "") + f" | DIE-HBM-19 plan follows source: dropped duplicate copies {families}"
    P["note"] = P.get("note", "") + f" | DIE-HBM-19 drop_dup_copies {families} (plan follows source, HBM-034)"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    for f in os.listdir(plan_dir):
        if f in ("die_plan.json", "drop_dup_report.json"):
            continue
        s = plan_dir / f
        if s.is_dir():
            shutil.copytree(s, out_dir / f, copy_function=os.link)
        else:
            os.link(s, out_dir / f)
    txt = json.dumps(P, indent=1)
    (out_dir / "die_plan.json").write_text(txt)
    rep["plan_sha256"] = hashlib.sha256(txt.encode()).hexdigest()
    (out_dir / "drop_dup_report.json").write_text(json.dumps(rep, indent=1))
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan_dir"); ap.add_argument("out_dir")
    ap.add_argument("--family", action="append", required=True)
    ap.add_argument("--keep", default="auto", choices=("auto", "q0", "q1"))
    ap.add_argument("--hubs", default="q_hub_ne,q_hub_nw")
    ap.add_argument("--tools", default=str(HERE.parents[3] / "tools" / "die_plan"))
    a = ap.parse_args(argv)
    rep = run(a.plan_dir, a.out_dir, a.family, a.keep, tuple(a.hubs.split(",")), a.tools)
    for tn, fs in rep["hubs"].items():
        for fam, st in fs.items():
            print(tn, fam, json.dumps(st))
    print("plan sha256", rep["plan_sha256"][:12])


if __name__ == "__main__":
    main()
