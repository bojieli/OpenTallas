"""Per-type diff of two strict S81 binds (FTLOCK-S81 go-live check; from die-s81-85/s81p7/binddiff.py).

usage: binddiff.py BIND_A BIND_B PLAN EVENT_TYPES_JSON OUT_JSON

Per-file equality, differing JSON files localized to plan type keys, and a per-type digest over
  * rtl/<prefix><type>.*                        (bound RTL is written as s81p_<type>.sv / .reset_tree.*),
  * native_internal_stations/<type>/**          (per-type kit_rtl.json + native .sv),
  * every JSON sub-tree keyed by the type name,
with each bind's own root path replaced by <BIND> so two binds written to different dirs compare by content.

Fix 11-11: the s81p7 version split rtl names at the first '.' and looked the stem up as a type, so the
s81p_-prefixed bound RTL never reached any digest (t27/t49 reported "digest equal" while 50/35 latches were added),
and absolute bind-dir paths inside kit_rtl.json counted as content changes.
"""
import hashlib
import json
import sys
from pathlib import Path

SKIP = {"asbuilt.json", "bind_sinks.json"}   # elab inputs (copied) / 2.7 GB: compared by file sha only
RTL_PREFIXES = ("s81p_", "")
NATIVE = "native_internal_stations"


def type_of(rel, types):
    """Plan type a bind file belongs to, or None."""
    parts = Path(rel).parts
    if len(parts) >= 3 and parts[0] == NATIVE and parts[1] in types:
        return parts[1]
    if len(parts) == 2 and parts[0] == "rtl":
        stem = parts[1].split(".")[0]
        for p in RTL_PREFIXES:
            if stem.startswith(p) and stem[len(p):] in types:
                return stem[len(p):]
    return None


def files(d):
    return sorted(str(p.relative_to(d)) for p in Path(d).rglob("*") if p.is_file())


def file_sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""):
            h.update(c)
    return h.hexdigest()


def norm_bytes(d, rel):
    """File content with the bind's own root path replaced by <BIND>."""
    root = str(Path(d).resolve()).encode()
    return (Path(d) / rel).read_bytes().replace(root, b"<BIND>")


def typed_keys(x, types, acc):
    if isinstance(x, dict):
        for k, v in x.items():
            if k in types:
                acc.setdefault(k, []).append(json.dumps(v, sort_keys=True))
            else:
                typed_keys(v, types, acc)
    elif isinstance(x, list):
        for v in x:
            typed_keys(v, types, acc)


def digests(d, types, json_limit=400_000_000):
    dg = {t: hashlib.sha256() for t in types}
    root = str(Path(d).resolve())
    for f in files(d):
        t = type_of(f, types)
        if t is not None:
            dg[t].update(f.encode())
            dg[t].update(norm_bytes(d, f))
        elif f.endswith(".json") and f not in SKIP and (Path(d) / f).stat().st_size < json_limit:
            acc = {}
            typed_keys(json.loads(norm_bytes(d, f)), types, acc)
            for t2, vs in acc.items():
                dg[t2].update(f.encode())
                for v in vs:
                    dg[t2].update(v.replace(root, "<BIND>").encode())
    return {t: h.hexdigest()[:16] for t, h in dg.items()}


def walk(x, y, path, out):
    if x == y:
        return
    if isinstance(x, dict) and isinstance(y, dict):
        for k in set(x) | set(y):
            walk(x.get(k), y.get(k), path + (k,), out)
    elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
        for i, (u, v) in enumerate(zip(x, y)):
            walk(u, v, path + (i,), out)
    else:
        out.append(path)


def compare(a, b, types, event):
    a, b = Path(a), Path(b)
    fa, fb = files(a), files(b)
    common = sorted(set(fa) & set(fb))
    diff = [f for f in common if file_sha(a / f) != file_sha(b / f) and norm_bytes(a, f) != norm_bytes(b, f)]
    touched = {}
    for f in diff:
        t = type_of(f, types)
        if t is not None or not f.endswith(".json") or f in SKIP:
            touched[f] = t or "non-type file differs"
            continue
        out = []
        walk(json.loads(norm_bytes(a, f)), json.loads(norm_bytes(b, f)), (), out)
        ts = sorted({p for path in out for p in path if isinstance(p, str) and p in types})
        nont = [path for path in out if not any(isinstance(p, str) and p in types for p in path)]
        touched[f] = dict(n_paths=len(out), types=ts, n_non_type=len(nont),
                          non_type_paths=[list(map(str, p))[:6] for p in nont[:8]])
    da, db = digests(a, types), digests(b, types)
    chg = sorted(t for t in types if da[t] != db[t])
    return dict(only_a=sorted(set(fa) - set(fb)), only_b=sorted(set(fb) - set(fa)), n_files=[len(fa), len(fb)],
                differing_files=len(diff), changed=chg, changed_not_in_event=sorted(set(chg) - set(event)),
                event_unchanged=sorted(set(event) - set(chg)), digests_a=da, digests_b=db, touched=touched)


def main(argv):
    a, b, plan, ev, out = argv[1:6]
    types = set(json.load(open(plan))["partition_types"])
    event = set(json.load(open(ev))["types"])
    r = compare(a, b, types, event)
    print("files", *r["n_files"], "only_a", r["only_a"][:10], "only_b", r["only_b"][:10])
    print("differing files (bind root normalized)", r["differing_files"])
    print("per-type digest changed:", len(r["changed"]), "unchanged:", len(types) - len(r["changed"]))
    print("changed but not in event:", len(r["changed_not_in_event"]), r["changed_not_in_event"])
    print("in event but digest equal:", r["event_unchanged"])
    nontype = sorted(f for f, v in r["touched"].items() if v == "non-type file differs"
                     or (isinstance(v, dict) and v["n_non_type"]))
    print("non-type differing files:", nontype)
    json.dump(r, open(out, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
