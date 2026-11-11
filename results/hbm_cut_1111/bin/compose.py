#!/usr/bin/env python3
"""HBM-COMPOSE hbm-cut-1111: path-level plan-dir deltas, conflict check, ordered apply with per-step assert.

Delta JSON: {"name", "source", "base", "files": {rel: {"kind": "json", "ops": [[path, "set"|"del", value]]}
                                                  | {"kind": "raw", "op": "set"|"del", "from": abs, "sha256": hex}}}
Path elements: str (dict key), int (list index, only when both lists have equal length and no identity key),
{"k": idkey, "v": idval} (list of dicts keyed by a unique identity, same key order on both sides).
A list whose identity order or length changes is one leaf (whole-list set), so any finer write by another
delta under it is a prefix overlap = conflict.

usage:
  compose.py diff BASE_DIR NEW_DIR NAME OUT [--file-base rel=ALT_FILE ...] [--only rel,rel] [--skip rel,rel]
  compose.py adopt BASE_DIR ADOPT_JSON NAME OUT          # {type: {inst: [x, y, orient]}}
  compose.py conflicts D1 D2 ...
  compose.py apply BASE_DIR OUT_DIR LOG D1 D2 ...        # sequential, asserts only declared paths change
  compose.py classify BASE_DIR OUT_DIR OUT_JSON          # eq_gate classes of every changed die_plan path
"""
import gzip, hashlib, json, os, shutil, sys

BOOK = {"SHA256SUMS", "README_EVENT.txt", "eq_gate.json", "g0_report.json", "g0_base_report.json", "DO_NOT_COUNT"}
IDKEYS = ("inst", "name", "id", "slot", "bus")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dump_like(obj, raw_ref):
    """Serialize the way the plan tools do (checked: die_plan/core_conns indent 1 + NL; clock_entries compact + NL)."""
    for ind, nl in ((1, True), (1, False), (None, True), (None, False), (2, True)):
        if (json.dumps(json.loads(raw_ref), indent=ind) + ("\n" if nl else "")).encode() == raw_ref:
            return (json.dumps(obj, indent=ind) + ("\n" if nl else "")).encode()
    raise SystemExit("no matching serialization for reference file")


def idkey(lst):
    if not lst or not all(isinstance(e, dict) for e in lst):
        return None
    for k in IDKEYS:
        vals = [e.get(k) for e in lst]
        if all(isinstance(v, str) for v in vals) and len(set(vals)) == len(vals):
            return k
    return None


def jdiff(a, b, p, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if k not in b:
                out.append([p + [k], "del", None])
            else:
                jdiff(a[k], b[k], p + [k], out)
        for k in b:
            if k not in a:
                out.append([p + [k], "set", b[k]])
        if list(b) != [k for k in a if k in b] + [k for k in b if k not in a]:
            out.append([p, "order", list(b)])   # cosmetic key order (not a write; skipped by the conflict check)
        return
    if isinstance(a, list) and isinstance(b, list):
        ka, kb = idkey(a), idkey(b)
        if ka and ka == kb and [e[ka] for e in a] == [e[kb] for e in b]:
            for u, v in zip(a, b):
                jdiff(u, v, p + [{"k": ka, "v": u[ka]}], out)
            return
        if ka is None and kb is None and len(a) == len(b):
            for i, (u, v) in enumerate(zip(a, b)):
                jdiff(u, v, p + [i], out)
            return
    if a != b or type(a) != type(b):
        out.append([p, "set", b])


def step(node, e):
    if isinstance(e, dict):
        for x in node:
            if isinstance(x, dict) and x.get(e["k"]) == e["v"]:
                return x
        raise KeyError(f"no element {e}")
    return node[e]


def japply(obj, ops):
    for path, op, val in ops:
        if op == "order":
            n = obj
            for e in path:
                n = step(n, e)
            items = dict(n); n.clear()
            for k in val:
                if k in items: n[k] = items.pop(k)
            n.update(items)
            continue
        n = obj
        for e in path[:-1]:
            n = step(n, e)
        last = path[-1] if path else None
        if not path:
            raise SystemExit("root replace not allowed")
        if isinstance(last, dict):
            idx = next(i for i, x in enumerate(n) if isinstance(x, dict) and x.get(last["k"]) == last["v"])
            if op == "del":
                del n[idx]
            else:
                n[idx] = val
        elif op == "del":
            del n[last]
        else:
            n[last] = val
    return obj


def pkey(p):
    return tuple(json.dumps(e, sort_keys=True) for e in p)


def walkfiles(d):
    for r, _, fs in os.walk(d):
        for f in fs:
            full = os.path.join(r, f)
            if os.path.islink(full):
                raise SystemExit(f"symlink in plan dir: {full}")
            yield os.path.relpath(full, d)


def is_json(rel):
    return rel.endswith(".json")


def cmd_diff(base, new, name, out, extra):
    alt, only, skip = {}, None, set()
    i = 0
    while i < len(extra):
        if extra[i] == "--file-base":
            r, f = extra[i + 1].split("=", 1); alt[r] = f; i += 2
        elif extra[i] == "--only":
            only = set(extra[i + 1].split(",")); i += 2
        elif extra[i] == "--skip":
            skip |= set(extra[i + 1].split(",")); i += 2
        else:
            raise SystemExit(extra[i])
    fb, fn = set(walkfiles(base)), set(walkfiles(new))
    files, book = {}, []
    for rel in sorted(fb | fn):
        if only is not None and rel not in only:
            continue
        bfile = alt.get(rel, os.path.join(base, rel))
        nfile = os.path.join(new, rel)
        inb, inn = os.path.exists(bfile), rel in fn
        if inb and inn and sha(bfile) == sha(nfile):
            continue
        if os.path.basename(rel) in BOOK or (rel.endswith(".gz") and rel[:-3] in (fb | fn)) or rel in skip:
            book.append(rel); continue
        if inn and inb and is_json(rel):
            ops = []
            jdiff(json.load(open(bfile)), json.load(open(nfile)), [], ops)
            files[rel] = {"kind": "json", "ops": ops, "base_sha256": sha(bfile), "new_sha256": sha(nfile)}
        elif inn:
            files[rel] = {"kind": "raw", "op": "set", "from": os.path.abspath(nfile), "sha256": sha(nfile)}
        else:
            files[rel] = {"kind": "raw", "op": "del"}
    d = {"name": name, "source": os.path.abspath(new), "base": os.path.abspath(base), "files": files,
         "bookkeeping_not_applied": book, "file_base_override": alt}
    json.dump(d, open(out, "w"), indent=1)
    for rel, f in files.items():
        print(name, rel, f["kind"], len(f["ops"]) if f["kind"] == "json" else f["op"])
    print("bookkeeping skipped:", book)


def cmd_adopt(base, adopt, name, out):
    P = json.load(open(os.path.join(base, "die_plan.json")))
    A = json.load(open(adopt))
    ops = []
    for t, insts in sorted(A.items()):
        hcs = {h["inst"]: h for h in P["partition_types"][t]["hard_cores"]}
        for inst, v in sorted(insts.items()):
            if inst not in hcs:
                raise SystemExit(f"{t}: no hard core {inst}")
            x, y, o = v
            pre = ["partition_types", t, "hard_cores", {"k": "inst", "v": inst}]
            if [x, y] != hcs[inst]["origin_um"]:
                ops.append([pre + ["origin_um"], "set", [x, y]])
            if o != hcs[inst].get("orient", "R0"):
                ops.append([pre + ["orient"], "set", o])
    d = {"name": name, "source": os.path.abspath(adopt), "base": os.path.abspath(base),
         "files": {"die_plan.json": {"kind": "json", "ops": ops}}, "bookkeeping_not_applied": []}
    json.dump(d, open(out, "w"), indent=1)
    print(name, len(ops), "ops")


def keys_of(d):
    for rel, f in d["files"].items():
        if f["kind"] == "json":
            for p, op, v in f["ops"]:
                if op != "order":
                    yield rel, p, op, v
        else:
            yield rel, None, f["op"], f.get("sha256")


def cmd_conflicts(paths):
    D = [json.load(open(p)) for p in paths]
    bad = []
    for i in range(len(D)):
        for j in range(i + 1, len(D)):
            idx = {}
            for rel, p, op, v in keys_of(D[i]):
                idx.setdefault(rel, []).append((p, op, v))
            for rel, q, op2, v2 in keys_of(D[j]):
                for p, op, v in idx.get(rel, []):
                    if p is None or q is None:
                        hit = True; same = (op, v) == (op2, v2)
                    else:
                        kp, kq = pkey(p), pkey(q)
                        n = min(len(kp), len(kq))
                        hit = kp[:n] == kq[:n]
                        same = hit and kp == kq and (op, v) == (op2, v2)
                    if hit:
                        bad.append({"a": D[i]["name"], "b": D[j]["name"], "file": rel, "path_a": p, "path_b": q,
                                    "identical": same})
    settled = []
    if os.environ.get("SETTLED"):
        settled = json.load(open(os.environ["SETTLED"]))   # [{"a":..,"b":..,"types":[..],"ruling":..}]
    for b in bad:
        t = b["path_a"][1] if b["path_a"] and len(b["path_a"]) > 1 else None
        b["settled"] = next((s["ruling"] for s in settled if s["a"] == b["a"] and s["b"] == b["b"] and t in s["types"]), None)
    open_ = [b for b in bad if not b["identical"] and not b["settled"]]
    print(json.dumps({"n_overlap": len(bad), "n_identical": sum(b["identical"] for b in bad),
                      "n_settled": sum(bool(b["settled"]) for b in bad), "n_open": len(open_),
                      "overlaps": bad[:200]}, indent=1, default=str))
    return 1 if open_ else 0


def cmd_apply(base, out, log, paths):
    if os.path.exists(out):
        raise SystemExit(f"{out} exists")
    shutil.copytree(base, out, symlinks=False, copy_function=shutil.copy2)
    steps = []
    for dp in paths:
        d = json.load(open(dp))
        rec = {"delta": d["name"], "delta_file": os.path.abspath(dp), "delta_sha256": sha(dp), "files": {}}
        for rel, f in d["files"].items():
            tgt = os.path.join(out, rel)
            if f["kind"] == "raw":
                if f["op"] == "del":
                    os.unlink(tgt)
                else:
                    assert sha(f["from"]) == f["sha256"], (rel, "source changed since diff")
                    os.makedirs(os.path.dirname(tgt), exist_ok=True)
                    if os.path.exists(tgt):
                        os.unlink(tgt)
                    shutil.copy2(f["from"], tgt)
                rec["files"][rel] = {"raw": f["op"]}
                continue
            raw = open(tgt, "rb").read()
            before = json.loads(raw)
            after = japply(json.loads(raw), f["ops"])
            body = dump_like(after, raw)
            open(tgt + ".tmp", "wb").write(body); os.replace(tgt + ".tmp", tgt)
            # assert: only declared paths changed (re-diff before vs after; every change must sit under a declared path)
            got = []
            jdiff(before, json.loads(body), [], got)
            got = [g for g in got if g[1] != "order"]
            decl = {pkey(p) for p, op, _ in f["ops"] if op != "order"}
            gotk = [pkey(g[0]) for g in got]
            gotpre = {k[:i] for k in gotk for i in range(len(k) + 1)}
            gotset = set(gotk)
            stray = [g[0] for g, k in zip(got, gotk) if not any(k[:i] in decl for i in range(len(k) + 1))]
            missing = [p for p, op, v in f["ops"] if op != "order" and pkey(p) not in gotpre and
                       not any(pkey(p)[:i] in gotset for i in range(len(p) + 1))]
            assert not stray, (d["name"], rel, "undeclared change", stray[:5])
            rec["files"][rel] = {"ops": len(f["ops"]), "changed_leaf_paths": len(got), "noop_ops": len(missing),
                                 "sha256": hashlib.sha256(body).hexdigest()}
            gz = tgt + ".gz"
            if os.path.exists(gz):
                open(gz, "wb").write(gzip.compress(body, mtime=0))
        steps.append(rec)
        print("applied", d["name"], json.dumps(rec["files"])[:400])
    json.dump(steps, open(log, "w"), indent=1)


CLASSES = [("positions_orients", ("origin_um", "orient")), ("ft_bands_windows", ("die_ft_bands", "ft_slots", "windows",
           "buses", "face_layers", "internal_stations", "stations")), ("notes", ("note", "notes")),
           ("outline", ("outline_um",)), ("clock", ("clock",)), ("reset", ("reset",))]


def cmd_classify(base, new, outp):
    a = json.load(open(os.path.join(base, "die_plan.json"))); b = json.load(open(os.path.join(new, "die_plan.json")))
    ops = []
    jdiff(a, b, [], ops)
    res = {}
    ta, tb = set(a["partition_types"]), set(b["partition_types"])
    for p, op, v in ops:
        s = [e if isinstance(e, (str, int)) else f"{e['k']}={e['v']}" for e in p]
        c = "other"
        if len(p) == 2 and p[0] == "partition_types" and (p[1] not in ta or p[1] not in tb):
            c = "type_split"
        elif p and p[-1] in ("note", "notes"):
            c = "notes"
        else:
            for name, keys in CLASSES:
                if any(isinstance(e, str) and e in keys for e in p):
                    c = name; break
        if c == "other" and p and p[0] == "partitions":
            c = "type_split"
        res.setdefault(c, []).append("/".join(map(str, s)))
    types = sorted({p[1] for p, _, _ in ops if p[0] == "partition_types"})
    out = {"base_sha256": sha(os.path.join(base, "die_plan.json")), "new_sha256": sha(os.path.join(new, "die_plan.json")),
           "changed_paths": len(ops), "by_class": {k: {"n": len(v), "paths": v} for k, v in sorted(res.items())},
           "types_changed": types, "types_removed": sorted(ta - tb), "types_added": sorted(tb - ta)}
    json.dump(out, open(outp, "w"), indent=1)
    print({k: len(v) for k, v in res.items()}, "types", len(types), "removed", out["types_removed"], "added", out["types_added"])


if __name__ == "__main__":
    c, *r = sys.argv[1:]
    if c == "diff":
        cmd_diff(r[0], r[1], r[2], r[3], r[4:])
    elif c == "adopt":
        cmd_adopt(*r)
    elif c == "conflicts":
        sys.exit(cmd_conflicts(r))
    elif c == "apply":
        cmd_apply(r[0], r[1], r[2], r[3:])
    elif c == "classify":
        cmd_classify(*r)
    else:
        raise SystemExit(__doc__)
