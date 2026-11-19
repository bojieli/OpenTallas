#!/usr/bin/env python3
"""start_stage_raw_resite.py PLAN.json BIND_RTL_DIR [--types REGEX] [--reach UM] [--out PLAN2.json] [--report R.json] [--check]

START-RAW-RESITE-1 (FABLE-FIX-KV-HG 11-18).  A landing START stage (clock.landing_writer_start / landing_reader_start
branches[bus].stages[i]) is an ot_dp_landing_relay held by rst_raw_n = the plan's raw_reset name.  The name is a reset-tree
relay output; when it is a PAD tap (the boot pad chain of the tree sits at the pad origin, not at the tap site) the relay
can be millimetres from the stage: kv3_hgi_v4 ft0_o stages 6 and 7 at (4.32, 20.06) read rst_n_t74 whose relay is at
(631.8, 1503.4), one 2.1 mm hop, post-CTS TT -571 ps (v5 -595, v6 -802, v7 -890; two ends per type).

Rule: a stage whose raw relay is farther than --reach (default 405 um, Manhattan) from the stage xy_um takes the NEAREST
relay of the same tree that (a) has the same wavefront depth (the release edge does not move), (b) is a tap output
(rst_n_t<k>) when the old one was, (c) does not drive an output port (face_guard 'shared'), (d) is within --reach.
Nothing qualifies: the stage is reported as unresolved and left unchanged.  The relay table is the tree the bind
emitted (BIND_RTL_DIR/<type>_part.reset_tree.json); run it on the base bind before the event bind, and with --check on
the new bind (exit 1 when a stage is still out of reach).  A plan with no such stage is written back byte-identical."""
import argparse, json, os, re, sys

KEYS = ("landing_writer_start", "landing_reader_start")


def relay_table(tree_json):
    """{q net: dict(xy, depth, tap, kind)} of one type's emitted reset tree"""
    out = {}
    for r in (tree_json.get("tree") or {}).get("relays") or []:
        out[r["q"]] = dict(xy=(float(r["xy"][0]), float(r["xy"][1])), depth=int(r["depth"]), tap=r.get("tap"), kind=r.get("kind"))
    return out


def ported_nets(bound_sv):
    return set(re.findall(r"\bassign\s+rst_o_\w+\s*=\s*(\w+)\s*;", bound_sv or ""))


def pick(raw, xy, relays, ported, reach):
    """-> (new raw, distance of the old one, why).  why: None = kept in reach / unknown name, 'resited', 'unresolved'."""
    if raw not in relays:
        return raw, None, None
    dist = lambda q: abs(relays[q]["xy"][0] - xy[0]) + abs(relays[q]["xy"][1] - xy[1])   # noqa: E731
    d0 = dist(raw)
    if d0 <= reach:
        return raw, d0, None
    tap = bool(re.fullmatch(r"rst_n_t\d+", raw))
    cand = sorted((dist(q), q) for q, r in relays.items()
                  if q != raw and r["depth"] == relays[raw]["depth"] and q not in ported
                  and bool(re.fullmatch(r"rst_n_t\d+", q)) == tap)
    if cand and cand[0][0] <= reach:
        return cand[0][1], d0, "resited"
    return raw, d0, "unresolved"


def resite_type(tn, t, relays, ported, reach):
    """edits t in place; -> list of records"""
    rec = []
    for key in KEYS:
        cfg = (t.get("clock") or {}).get(key) or {}
        for bus, br in sorted((cfg.get("branches") or {}).items()):
            for i, st in enumerate(br.get("stages", []) if isinstance(br, dict) else []):
                raw, xy = st.get("raw_reset"), st.get("xy_um")
                if not isinstance(raw, str) or not isinstance(xy, list) or len(xy) != 2:
                    continue
                new, d0, why = pick(raw, xy, relays, ported, reach)
                if why:
                    rec.append(dict(type=tn, key=key, bus=bus, stage=i, xy_um=xy, was=raw, was_um=round(d0, 1), raw=new, result=why,
                                    **({"now_um": round(abs(relays[new]["xy"][0] - xy[0]) + abs(relays[new]["xy"][1] - xy[1]), 1)}
                                       if why == "resited" else {})))
                    if why == "resited":
                        st["raw_reset"] = new
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("bind_rtl")
    ap.add_argument("--types", default=".*"); ap.add_argument("--reach", type=float, default=405.0)
    ap.add_argument("--out"); ap.add_argument("--report"); ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    text = open(a.plan).read(); plan = json.loads(text); rec = []; missing = []
    trees = {}          # plan type -> tree file (a class-split type is bound under its own module name)
    for f in sorted(os.listdir(a.bind_rtl)):
        if f.endswith(".reset_tree.json"):
            trees.setdefault(json.load(open(os.path.join(a.bind_rtl, f))).get("plan_type"), f)
    for tn, t in sorted(plan["partition_types"].items()):
        if not re.fullmatch(a.types, tn) or not any((t.get("clock") or {}).get(k) for k in KEYS):
            continue
        if tn not in trees:
            missing.append(tn); continue
        tj = os.path.join(a.bind_rtl, trees[tn])
        sv = tj[:-len(".reset_tree.json")] + ".sv"
        rec += resite_type(tn, t, relay_table(json.load(open(tj))), ported_nets(open(sv).read() if os.path.exists(sv) else ""), a.reach)
    res = [r for r in rec if r["result"] == "resited"]; unr = [r for r in rec if r["result"] == "unresolved"]
    if a.report:
        json.dump(dict(schema="opentallas.start_stage_raw_resite.v1", reach_um=a.reach, resited=res, unresolved=unr, no_tree=missing),
                  open(a.report, "w"), indent=1)
    if a.out and not a.check:
        open(a.out, "w").write(json.dumps(plan) if res else text)
    print(f"START_RAW_RESITE resited {len(res)} unresolved {len(unr)} no_tree {len(missing)} types {len(set(r['type'] for r in rec))}")
    return 1 if (a.check and (res or unr)) else 0


if __name__ == "__main__":
    sys.exit(main())
