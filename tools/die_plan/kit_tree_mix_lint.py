#!/usr/bin/env python3
"""HBM-HUB-RTL-1 11-11 (class of tag hbm-hub-gather-phase): lint kit file-lists for rtl/ <-> r18h5_bundle tree mixes.

    kit_tree_mix_lint.py KIT_RTL.f [...] [--json OUT] [--quiet]

Why: an HBM kit closure may take a parent module from main rtl/ and its child from the bind-of-record bundle
(physical/die_plan/hbm/bind/r18h5_bundle/rtl), or the reverse.  The two trees hold different versions of ~30 modules
whose parameter interfaces differ.  When the parent does not set a parameter by name, the child elaborates with ITS
tree's default, which can differ from the default the parent's own tree assumes (q_hub: rtl/ ot_hbm_hc_q_static passes
RESP_PHASE only; the bundle reader's PERIOD defaulted to 24 -> GATHER_PHASE 174 hit the $fatal guard).

Finding MIX_PARAM: an instance edge parent P (file in tree A) -> child C (picked file in tree B != A) where C's copy in
tree A exists and the parameter interfaces differ in a way the parent does not pin: a parameter the parent does not set
by name that is missing in one copy or has a different default text.  Edges whose child copies are identical in every
unset parameter are SAFE_MIX (reported as counts only).  A MIX_PARAM edge is PROVEN (not a finding) only when the
registry (default physical/die_plan/hbm/kit_tree_mix_proofs.json, written by kit_tree_mix_prove.py) holds an entry for
the child whose every pick/twin source file has the same sha256 at this kit's roots and whose proven parameter domain
names every parameter the parent sets.  Exit 1 when any MIX_PARAM remains.
"""
import argparse, hashlib, json, re, sys
from pathlib import Path

BUNDLE = "/physical/die_plan/hbm/bind/r18h5_bundle/rtl/"
KW = set("""module endmodule input output inout wire reg logic integer genvar assign always always_ff always_comb
if else for begin end case endcase generate endgenerate function endfunction task endtask initial localparam parameter
default posedge negedge or and not buf return typedef struct enum""".split())


def strip(t):
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    return re.sub(r"//[^\n]*", "", t)


def tree(p):
    p = str(p)
    if BUNDLE in p:
        return "bundle", p.split(BUNDLE, 1)[0], p.split(BUNDLE, 1)[1]
    # main rtl/: the first <root>/rtl/ whose <root> is a repo checkout holding the bundle (a kit's own rtl/ dir, e.g.
    # items/<t>/rtl/source_alias, is not a tree)
    for m in re.finditer(r"/rtl/", p):
        root = p[:m.start()]
        if Path(root + BUNDLE).is_dir():
            return "rtl", root, p[m.end():]
    return "other", None, None


def counterpart(p):
    t, root, rel = tree(p)
    if t == "bundle":
        return Path(root) / "rtl" / rel
    if t == "rtl":
        return Path(root + BUNDLE) / rel
    return None


def balanced(t, i):
    """t[i] == '(' -> index after the matching ')'"""
    d = 0
    for j in range(i, len(t)):
        d += {"(": 1, ")": -1}.get(t[j], 0)
        if d == 0:
            return j + 1
    return len(t)


def split_top(s):
    out, d, cur = [], 0, ""
    for ch in s:
        if ch in "([{":
            d += 1
        elif ch in ")]}":
            d -= 1
        if ch == "," and d == 0:
            out.append(cur); cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out


_cache = {}


def modules(path):
    """{module: (params {name: default_text}, body_text)} of one file (header #( ) params + body parameters)"""
    path = str(path)
    if path in _cache:
        return _cache[path]
    try:
        t = strip(Path(path).read_text(errors="replace"))
    except OSError:
        _cache[path] = {}
        return {}
    out = {}
    for m in re.finditer(r"\bmodule\s+(\w+)", t):
        name, i = m.group(1), m.end()
        e = t.find("endmodule", i)
        e = len(t) if e < 0 else e
        params = {}
        j = i
        while j < len(t) and t[j].isspace():
            j += 1
        if t.startswith("#", j):
            k = t.index("(", j)
            k2 = balanced(t, k)
            for item in split_top(t[k + 1:k2 - 1]):
                mm = re.search(r"(\w+)\s*=\s*(.*)$", item.strip(), re.S)
                if mm and not re.match(r"\s*localparam\b", item):
                    params[mm.group(1)] = " ".join(mm.group(2).split())
        body = t[i:e]
        for mm in re.finditer(r"\bparameter\b([^;]*);", body):
            for item in split_top(mm.group(1)):
                m2 = re.search(r"(\w+)\s*=\s*(.*)$", item.strip(), re.S)
                if m2:
                    params.setdefault(m2.group(1), " ".join(m2.group(2).split()))
        out[name] = (params, body)
    _cache[path] = out
    return out


def instances(body, known):
    """[(child, set of params set by name, positional?)]"""
    res = []
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*(#\s*\()?", body):
        c = m.group(1)
        if c not in known or c in KW:
            continue
        i = m.end()
        named, pos = set(), False
        if m.group(2):
            k = i - 1
            k2 = balanced(body, k)
            args = body[k + 1:k2 - 1]
            named = set(re.findall(r"\.(\w+)\s*\(", args))
            pos = bool(args.strip()) and not named
            i = k2
        mm = re.match(r"\s*([A-Za-z_]\w*)\s*(\[[^\]]*\]\s*)?\(", body[i:])
        if not mm:
            continue
        res.append((c, named, pos))
    for m in re.finditer(r"\bdefparam\s+[\w.]*?(\w+)\.(\w+)\s*=", body):
        res.append((None, {m.group(2)}, False))
    return res


def read_list(f):
    files = []
    for ln in Path(f).read_text(errors="replace").split():
        if ln.startswith(("+", "-")):
            continue
        if ln.endswith((".v", ".sv", ".svh", ".vh")):
            files.append(ln)
    return files


def _resolve(key, root):
    t, rel = key.split(":", 1)
    return Path(root) / "rtl" / rel if t == "rtl" else Path(root + BUNDLE) / rel


def proven(reg, child, cf, named):
    root = tree(cf)[1]
    for e in reg:
        if e.get("module") != child or not all(x.get("proven") for x in e.get("results", [])):
            continue
        if not set(named) <= set(e.get("domain", {})):
            continue
        ok = True
        for k, h in list(e["pick_files"].items()) + list(e["twin_files"].items()):
            f = _resolve(k, root) if ":" in k and k.split(":", 1)[0] in ("rtl", "bundle") else Path(k)
            if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != h:
                ok = False
                break
        if ok:
            return e
    return None


def lint(flist, reg=()):
    files = read_list(flist)
    pick = {}
    for f in files:
        for m in modules(f):
            pick.setdefault(m, f)        # first definition in list order (kit_strip_dups keeps the closure pick)
    known = set(pick)
    finds, safe, mixed_edges, prov = [], 0, 0, []
    for p, pf in sorted(pick.items()):
        tp = tree(pf)[0]
        if tp == "other":
            continue
        for c, named, pos in instances(modules(pf)[p][1], known):
            if c is None or c == p:
                continue
            cf = pick[c]
            tc = tree(cf)[0]
            if tc == "other" or tc == tp:
                continue
            mixed_edges += 1
            cp = counterpart(cf)
            twin = modules(cp).get(c) if cp and cp.is_file() else None
            if twin is None:
                safe += 1        # the parent's tree has no copy of the child: nothing to disagree with
                continue
            a, b = modules(cf)[c][0], twin[0]
            diff = sorted(k for k in set(a) | set(b) if k not in named and a.get(k) != b.get(k))
            if pos:
                diff = sorted(set(a) ^ set(b))
            if diff and proven(reg, c, cf, named):
                prov.append(f"{p}->{c}")
            elif diff:
                finds.append(dict(parent=p, parent_file=pf, parent_tree=tp, child=c, child_file=cf, child_tree=tc,
                                  twin_file=str(cp), unset_param_diff={k: [a.get(k), b.get(k)] for k in diff}))
            else:
                safe += 1
    return dict(kit=str(flist), files=len(files), mixed_edges=mixed_edges, safe_mix=safe, proven=sorted(set(prov)),
                mix_param=finds)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lists", nargs="+")
    ap.add_argument("--json")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--registry", default=str(Path(__file__).resolve().parents[2] / "physical/die_plan/hbm/kit_tree_mix_proofs.json"))
    a = ap.parse_args(argv)
    rp = Path(a.registry)
    reg = json.loads(rp.read_text()).get("proofs", []) if rp.is_file() else []
    res = [lint(f, reg) for f in a.lists]
    bad = 0
    for r in res:
        bad += len(r["mix_param"])
        if not a.quiet or r["mix_param"]:
            print(f"{'FAIL' if r['mix_param'] else 'PASS'} {r['kit']} files={r['files']} mixed_edges={r['mixed_edges']} "
                  f"safe_mix={r['safe_mix']} proven={len(r['proven'])} mix_param={len(r['mix_param'])}")
        for x in r["mix_param"]:
            print(f"  MIX_PARAM {x['parent']}[{x['parent_tree']}] -> {x['child']}[{x['child_tree']}] "
                  f"unset params differ: {x['unset_param_diff']}")
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1))
    print(f"KIT_TREE_MIX_LINT {'FAIL' if bad else 'PASS'} kits={len(res)} mix_param={bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
