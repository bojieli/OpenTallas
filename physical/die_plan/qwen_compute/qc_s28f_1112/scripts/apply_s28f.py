#!/usr/bin/env python3
"""QC-S28-F (DIE-QC-99 s28 event, lane F): re-appliable plan + sidecar delta, independent of QC-S28-A/B/E.

  The delta was composed by (epyc9, cwd = src28b copy, base plan_qc99_s28 2f0c17d5f1a3 / sidecar 38a30992accc):
    1. monband_s28f.py  MONITOR-BAND-SITE: 6 su collector monitor bands re-sited next to their own status pins
       (rect_um, max_pin_to_band_hop_um, placement) -- positions only
    2. taptarget_s28f.py TAP-CAP: clock.tap_target_sinks 900 -> 800 on sle_fw_v2__cl69f5e854 + sle_fw_v3, taps
       re-derived, landing pins re-pointed to the nearest new tap, collector tree republished (make_s28 compose rule)
    3. tools/die_plan/collector_reattach.py (main tool)
  apply_s28f.py mkdelta BASE.json FINAL.json DELTA.json [--sidecar BASE_SC.json FINAL_SC.json]
  apply_s28f.py apply BASE.json DELTA.json OUT.json [--sidecar IN_SC.json OUT_SC.json] [--report R.json]
      three-way: a path is applied only when BASE holds the delta's 'before' value (or already the 'after' value);
      otherwise CONFLICT (reported, exit 3, nothing written).  Compose order with A/B/E is free: F touches only
      the 8 types listed in the delta's types_touched and no die-level key.
"""
import copy
import hashlib
import json
import sys

MISSING = {"__missing__": True}


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


def dump(obj, path, like=None):
    """write in the style of the input file `like` (plan: indent 1; runtime sidecar: one line)"""
    one = like is not None and not open(like).read(2).startswith("{\n")
    txt = json.dumps(obj, indent=None if one else 1) + "\n"
    open(path, "w").write(txt)
    return hashlib.sha256(txt.encode()).hexdigest()


def mkdelta(base, final, dpath, sc=None):
    B, F = json.load(open(base)), json.load(open(final))
    D = dict(schema="opentallas.qc_s28f_delta.v1", lane="QC-S28-F", base=base, base_sha256=sha(base),
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
        r["out_sha256"] = dump(P, out, base)
        if sc:
            r["sidecar_out_sha256"] = dump(S, sc[1], sc[0])
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
    if a[0] == "mkdelta":
        mkdelta(a[1], a[2], a[3], sc)
    elif a[0] == "apply":
        sys.exit(apply(a[1], a[2], a[3], sc, rep))
    else:
        raise SystemExit(__doc__)
