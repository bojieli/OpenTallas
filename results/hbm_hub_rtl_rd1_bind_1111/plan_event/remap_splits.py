"""HBM-HUB-RTL-1 11-11: remap yosys-numbered primitive names (inst.$procdff$N, inst.$ternary$f.sv:L$N, ...) in any
bind input JSON (compose spec, map_file, land_r8 table: values and keys) from one as-built elaboration to another.
A cell maps to the cell of the same instance path whose (type, src, parameters, port widths) key has the same rank by
yosys number in the new elaboration; any count mismatch is reported as a miss and left unchanged.
usage: remap_splits.py OLD_asbuilt.json NEW_asbuilt.json IN.json OUT.json TOP"""
import json, sys, re, collections
old, new, spec_in, spec_out, top = sys.argv[1:6]
O = json.load(open(old))["modules"]; N = json.load(open(new))["modules"]
def mod_of(M, path):
    """instance path -> module; a yosys cell name may itself contain dots (generate scopes: ge[0].gc[1].leaf)"""
    m, segs = top, path.split(".")
    while segs:
        for k in range(len(segs), 0, -1):
            c = M[m]["cells"].get(".".join(segs[:k]))
            if c is not None and c["type"] in M:
                m, segs = c["type"], segs[k:]
                break
        else:
            return None
    return m
def key(c):
    return (c["type"], re.sub(r"[^|:]*/", "", c.get("attributes", {}).get("src") or ""), json.dumps(c.get("parameters", {}), sort_keys=True),
            json.dumps({k: len(v) for k, v in c.get("connections", {}).items()}, sort_keys=True))
cache, ren, miss, normd = {}, {}, [], {}
def norm(n):
    return "$".join(p.rsplit("/", 1)[1] if "/" in p else p for p in n.split("$"))
def remap(full):
    if full in ren:
        return ren[full]
    if ".$" not in full:
        ren[full] = full; return full
    inst, name = full.split(".$", 1); name = "$" + name
    if "$" not in name:
        ren[full] = full; return full
    mo, mn = mod_of(O, inst), mod_of(N, inst)
    if mo is not None and mo not in normd:
        normd[mo] = {norm(n): n for n in O[mo]["cells"] if "$" in n}
    if mo is not None:
        name = normd[mo].get(name, name)
    if mo is None or mn is None or name not in O[mo]["cells"]:
        miss.append((full, "path")); ren[full] = full; return full
    num = lambda n: int(re.search(r"(\d+)$", n).group(1)) if re.search(r"\$(\d+)$", n) else -1
    for M, mm, tag in ((O, mo, "o"), (N, mn, "n")):
        if (tag, mm) not in cache:
            idx = {}
            for n, c in M[mm]["cells"].items():
                if "$" in n:
                    idx.setdefault(key(c), []).append(n)
            cache[(tag, mm)] = {k: sorted(v, key=num) for k, v in idx.items()}
    k = key(O[mo]["cells"][name])
    co, cn = cache[("o", mo)].get(k, []), cache[("n", mn)].get(k, [])
    if len(co) != len(cn) or name not in co:
        miss.append((full, f"{len(co)} old vs {len(cn)} new")); ren[full] = full; return full
    ren[full] = f"{inst}.{norm(cn[co.index(name)])}"; return ren[full]
s = json.load(open(spec_in))
def walk(x):
    if isinstance(x, dict):
        return {walk(k): walk(v) for k, v in x.items()}
    if isinstance(x, list):
        return [walk(v) for v in x]
    if isinstance(x, str) and ".$" in x:
        return NAME.sub(lambda m: remap(m.group(0)), x)
    return x
NAME = re.compile(r"(?:[\w\[\]]+\.)*?[\w\[\]]+\.\$.*?\$\d+(?!\d)")
s = walk(s)
# Second pass: names the old elaboration does not have (a map written against an older elaboration still lists them):
# match them straight against the new elaboration by (instance, name without the yosys number), same count, by rank.
stem = lambda n: re.sub(r"\$\d+$", "", n)
groups = collections.defaultdict(list)
for full, v in list(ren.items()):
    if v == full and ".$" in full:
        inst, name = full.split(".$", 1)
        groups[(inst, stem("$" + name))].append(full)
fixed = {}
for (inst, st), olds in groups.items():
    mn = mod_of(N, inst)
    if mn is None:
        continue
    news = sorted((norm(n) for n in N[mn]["cells"] if "$" in n and stem(norm(n)) == st),
                  key=lambda n: int(re.search(r"(\d+)$", n).group(1)))
    olds = sorted(olds, key=lambda n: int(re.search(r"(\d+)$", n).group(1)))
    if news and len(news) == len(olds):
        for o, n in zip(olds, news):
            fixed[o] = f"{inst}.{n}"
if fixed:
    ren.update(fixed)
    miss = [m for m in miss if m[0] not in fixed]
    def walk2(x):
        if isinstance(x, dict):
            return {walk2(k): walk2(v) for k, v in x.items()}
        if isinstance(x, list):
            return [walk2(v) for v in x]
        if isinstance(x, str) and ".$" in x:
            return NAME.sub(lambda m: fixed.get(m.group(0), m.group(0)), x)
        return x
    s = walk2(s)
print("second pass (by stem, rank, against the new elaboration):", len(fixed), file=sys.stderr)
newnames = {v for k, v in ren.items() if k != v}
txt = json.dumps(s)
changed = sum(1 for k, v in ren.items() if k != v)
# any other occurrence of an old primitive name elsewhere in the spec
rest = [k for k, v in ren.items() if k != v and ('"' + k + '"') in txt and k not in newnames]
json.dump(s, open(spec_out, "w"), indent=1)
print(json.dumps({"splits": len(s.get("primitive_splits", [])) if isinstance(s, dict) else 0, "renamed": changed, "unchanged": len(ren) - changed,
                  "miss": len(miss), "miss_first": miss[:5], "miss_by": collections.Counter((m[0].split(".$")[0].split(".")[0], m[0].split(".$")[1].split("$")[0], m[1] if m[1]=="path" else "cnt") for m in miss).most_common(12), "old_names_left_in_spec": rest[:5]}))
