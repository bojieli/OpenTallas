#!/usr/bin/env python3
"""QC-S28-B (DIE-QC-99 s28 event, lane B): re-appliable plan delta, independent of QC-S28-A.

  apply_s28b.py stage1 BASE.json SCP_R.json S25.json OUT.json REPORT.json
      B1 budgets.cland_strip_density 1.0 (plan-wide; per-type cland_strip_density_types and cland_strip_rows(_types)
         entries kept: rows stay floors, sle_ctl__cla4f6f12f 1.0 stays)
      B3 clock.landing_ring_fanout_max 32 (PLACEREP-1 / DSREP / RSTREP, 0 cycles; write_chunk + sdc opt-ins stay off)
      B4 die.layer_budget.type_m8_grant {enable true, ndr 4w} (LAYER-BUDGET-1 m8_grant.py, = OT_GEN_M8_GRANT=1)
      B5 sl_sc form: ft_slots + landing band rect_um of the 9 sl_sc types from plan_scp_r (= VL2QC-SC plan_sc_p
         ff3d2e192d + SC-REFLOOR-1 x_stm_fe_p1 re-site 39514a0c862c), three-way checked against s25 (their base)
  apply_s28b.py mkdelta BASE.json FINAL.json DELTA.json [--sidecar BASE_SC.json FINAL_SC.json]
      leaf-path diff (dicts recursed, lists whole) of every partition_types[T] / die-level key that changed
  apply_s28b.py apply BASE.json DELTA.json OUT.json [--sidecar IN_SC.json OUT_SC.json] [--report R.json]
      three-way: a path is applied only when BASE holds the delta's 'before' value (or already the 'after' value);
      otherwise it is a CONFLICT (reported, exit 3, nothing written) -- compose QC-S28-A first, then this delta.
"""
import copy
import hashlib
import json
import sys

MISSING = {"__missing__": True}
SC_TYPES = ["sle_sc_v1__cl115da35f", "sle_sc_v1__cl7479a5ec", "sle_sc_v2", "sle_sc_v3", "slw_sc_v1__cl63e5a7a2",
            "slw_sc_v1__cl64543eaf__cl4590432d", "slw_sc_v1__cl64543eaf__cl5e017c6f", "slw_sc_v2", "slw_sc_v3"]


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def get(d, path):
    for k in path:
        if isinstance(k, int):
            if not isinstance(d, list) or k >= len(d):
                return MISSING
        elif not isinstance(d, dict) or k not in d:
            return MISSING
        d = d[k]
    return d


def put(d, path, v):
    for k in path[:-1]:
        d = d[k] if isinstance(k, int) else d.setdefault(k, {})
    if v == MISSING:
        d.pop(path[-1], None)
    else:
        d[path[-1]] = copy.deepcopy(v)


def _ident(x):
    return x.get("inst", x.get("name")) if isinstance(x, dict) else None


def diff(a, b, path=()):
    """leaf paths where a and b differ: dicts recursed; a list of dicts with the same length and the same element
    identities (inst / name) is recursed by index (so two lanes editing different cores of one type compose); every
    other value is compared whole"""
    if isinstance(a, dict) and isinstance(b, dict) and a != MISSING and b != MISSING:
        out = []
        for k in sorted(set(a) | set(b)):
            out += diff(a.get(k, MISSING), b.get(k, MISSING), path + (k,))
        return out
    if (isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and a and
            all(isinstance(x, dict) for x in a + b) and [_ident(x) for x in a] == [_ident(x) for x in b]):
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, path + (i,))
        return out
    return [] if a == b else [path]


def ids(d, path):
    """identity (inst / name) of every list element on the path, so apply refuses a re-ordered list"""
    out = []
    for i, k in enumerate(path):
        if isinstance(k, int):
            out.append(_ident(get(d, path[:i + 1])))
    return out


def dump(obj, path):
    txt = json.dumps(obj, indent=1) + "\n"
    open(path, "w").write(txt)
    return hashlib.sha256(txt.encode()).hexdigest()


def stage1(base, scr, s25, out, rep):
    P = json.load(open(base))
    R = json.load(open(scr))["partition_types"]
    A = json.load(open(s25))["partition_types"]
    log = dict(base=base, base_sha256=sha(base), scp_r=scr, scp_r_sha256=sha(scr), s25=s25, s25_sha256=sha(s25), edits=[])
    b = P.setdefault("budgets", {})
    log["edits"].append(dict(item="B1", path="budgets.cland_strip_density", before=b.get("cland_strip_density"), after=1.0))
    b["cland_strip_density"] = 1.0
    c = P.setdefault("clock", {})
    log["edits"].append(dict(item="B3", path="clock.landing_ring_fanout_max", before=c.get("landing_ring_fanout_max"), after=32))
    c["landing_ring_fanout_max"] = 32
    lb = P["die"].setdefault("layer_budget", {})
    g = dict(enable=True, ndr="4w", note="QC s28 (DIE-QC-99 / QC-S28-B, LAYER-BUDGET-1 main 14f492184f, owner 11-11 "
             "'grant the leftover M8'): every placed QC type below M8 routes M8 on the tracks the die does not use "
             "(die PG + cut_avail reserve); no die route guide yet")
    log["edits"].append(dict(item="B4", path="die.layer_budget.type_m8_grant", before=lb.get("type_m8_grant"), after=g))
    lb["type_m8_grant"] = g
    T = P["partition_types"]
    for tn in SC_TYPES:
        t, a, r = T[tn], A[tn], R[tn]
        n = 0
        for path in diff(a, r):
            if not (path[0] == "ft_slots" or (path[:3] == ("clock", "landing_contract", "bands") and path[-1] in
                                               ("rect_um", "max_pin_to_band_hop_um"))):
                raise SystemExit(f"B5 {tn}: plan_scp_r changes {path} (not ft_slots / band rect): refuse")
            if get(t, path) != get(a, path):
                raise SystemExit(f"B5 {tn}: s28 differs from s25 at {path}: three-way conflict")
            put(t, path, get(r, path))
            n += 1
            log["edits"].append(dict(item="B5", type=tn, path="/".join(map(str, path))))
        print(f"B5 {tn}: {n} paths from plan_scp_r")
    log["out_sha256"] = dump(P, out)
    json.dump(log, open(rep, "w"), indent=1)
    print("stage1 ->", log["out_sha256"][:12])


def mkdelta(base, final, dpath, sc=None):
    B, F = json.load(open(base)), json.load(open(final))
    D = dict(schema="opentallas.qc_s28b_delta.v1", lane="QC-S28-B", base=base, base_sha256=sha(base),
             final_sha256=sha(final), ops=[])
    for path in diff(B, F):
        D["ops"].append(dict(path=list(path), before=get(B, path), after=get(F, path), ids=ids(B, path)))
    if sc:
        SB, SF = json.load(open(sc[0])), json.load(open(sc[1]))
        D["sidecar_base_sha256"], D["sidecar_final_sha256"] = sha(sc[0]), sha(sc[1])
        D["sidecar_ops"] = [dict(path=list(p), before=get(SB, p), after=get(SF, p), ids=ids(SB, p)) for p in diff(SB, SF)]
    types = sorted({o["path"][1] for o in D["ops"] if o["path"][0] == "partition_types"})
    D["types_touched"] = types
    D["die_keys_touched"] = sorted({"/".join(map(str, o["path"])) for o in D["ops"] if o["path"][0] != "partition_types"})
    json.dump(D, open(dpath, "w"), indent=1)
    print(f"delta: {len(D['ops'])} plan ops, {len(types)} types, die keys {D['die_keys_touched']}, "
          f"sidecar ops {len(D.get('sidecar_ops', []))}; sha256 {sha(dpath)[:12]}")


def apply(base, dpath, out, sc=None, rep=None):
    P, D = json.load(open(base)), json.load(open(dpath))
    conf, done, same = [], 0, 0

    def run(obj, ops, tag):
        nonlocal done, same
        for o in ops:
            p, cur = tuple(o["path"]), get(obj, tuple(o["path"]))
            if ids(obj, p) != o.get("ids", []):
                conf.append(dict(where=tag, path="/".join(map(str, p)), why="list element identity differs"))
            elif cur == o["after"]:
                same += 1
            elif cur == o["before"]:
                put(obj, p, o["after"])
                done += 1
            else:
                conf.append(dict(where=tag, path="/".join(map(str, p))))
    run(P, D["ops"], "plan")
    S = None
    if sc:
        S = json.load(open(sc[0]))
        run(S, D.get("sidecar_ops", []), "sidecar")
    r = dict(base_sha256=sha(base), delta_sha256=sha(dpath), applied=done, already=same, conflicts=conf)
    if conf:
        print(f"CONFLICT {len(conf)} paths (nothing written):", json.dumps(conf[:20]))
    else:
        r["out_sha256"] = dump(P, out)
        if sc:
            r["sidecar_out_sha256"] = dump(S, sc[1])
        print(f"applied {done}, already {same}, conflicts 0 -> {r['out_sha256'][:12]}")
    if rep:
        json.dump(r, open(rep, "w"), indent=1)
    return 3 if conf else 0


if __name__ == "__main__":
    a = sys.argv[1:]
    sc = None
    if "--sidecar" in a:
        i = a.index("--sidecar"); sc = a[i + 1:i + 3]; del a[i:i + 3]
    rep = None
    if "--report" in a:
        i = a.index("--report"); rep = a[i + 1]; del a[i:i + 2]
    if a[0] == "stage1":
        stage1(*a[1:6])
    elif a[0] == "mkdelta":
        mkdelta(a[1], a[2], a[3], sc)
    elif a[0] == "apply":
        sys.exit(apply(a[1], a[2], a[3], sc, rep))
    else:
        raise SystemExit(__doc__)
