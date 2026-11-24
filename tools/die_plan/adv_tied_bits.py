"""adv_tied_bits.py -- PRECHECK ADV-TIED-BITS (COORD flow review 11-24 08:55; report only, r703).

Strict bind reports UNBOUND-tied bits (bind.py: a leaf-core input driven by a constant in the elaborated die netlist, no
declared tie / strap / proven-dead) only after a 5-h run: S81 c8 and lk_ES0 had 486,184 such bits on 16 svc types
(attn_hcore.ib 294400, rt2_load.ld_w 65472, v41x_dly.d 64768 ...).  S81-SVC-TIED's cause: slang's empty-blackbox import
reuses the FIRST instance's port ABI, so a parameterized leaf instantiated with different width parameters and not listed in
asbuilt slang_parameterized_blackboxes gets one width for every instance; the cut bits come back as constants (TIED).

Two parts, per plan type:
  OBSERVED   a bind_tied.json next to the bind of record (kw bind_out, or the newest under the tree's
             plan_of_record/native_bind/) -- bits per type and its top module.port classes
  PREDICTED  static, from the bind-tree RTL closure (ADV-TREE-DRIFT): every module instantiated in the closure that is not
             dissolved by the as-built (a blackbox leaf), not listed in slang_parameterized_blackboxes, whose port widths use
             a parameter that the instances override with more than one value.  Bits = sum over instances of the width
             difference to the first instance where the values evaluate, else '?'.
kw asbuilt (asbuilt_run.json; default the newest asbuilt_run*.json under plan_of_record/native_bind), bind_out, tree.
findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.
"""
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

CHECK = "ADV-TIED-BITS"
MAX_LINES = 30
_CMT = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)
_INSTP = re.compile(r"(?m)^\s*([A-Za-z_]\w*)\s*#\s*\(")
_PDEF = re.compile(r"\bparameter\s+(?:integer\s+|int\s+|logic\s+|bit\s+|\[[^\]]*\]\s*)?([A-Za-z_]\w*)\s*=\s*([^,;)]+)")
_PORT = re.compile(r"\b(input|output|inout)\s+(?:wire\s+|reg\s+|logic\s+)?(?:signed\s+)?\[([^\]]+)\]\s*([A-Za-z_]\w*)")


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def _balanced(s, i):
    """s[i] == '(' -> index after the matching ')' (or -1)"""
    d = 0
    for j in range(i, min(len(s), i + 20000)):
        c = s[j]
        if c == "(":
            d += 1
        elif c == ")":
            d -= 1
            if d == 0:
                return j + 1
    return -1


def _split_top(s):
    out, d, cur = [], 0, []
    for c in s:
        if c in "([{":
            d += 1
        elif c in ")]}":
            d -= 1
        if c == "," and d == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(c)
    out.append("".join(cur))
    return [x.strip() for x in out if x.strip()]


def module_header(text, name):
    """(param defaults {P: expr}, width ports {port: range expr using a parameter}) of module NAME in text"""
    m = re.search(r"(?m)^\s*module\s+" + re.escape(name) + r"\b", text)
    if not m:
        return None
    e = text.find(");", m.end())
    hdr = text[m.end(): e if e > 0 else m.end() + 20000]
    body = text[m.end(): m.end() + 60000]
    pdef = dict(_PDEF.findall(hdr))
    for k, v in _PDEF.findall(body):
        pdef.setdefault(k, v)
    ports = {}
    for _dir, rng, pn in _PORT.findall(hdr):
        if any(tok in pdef for tok in re.findall(r"[A-Za-z_]\w*", rng)):
            ports[pn] = rng
    return pdef, ports


def instances(text, known):
    """[(module, {param: expr})] parameterised instantiations of known modules in text"""
    out = []
    for m in _INSTP.finditer(text):
        mod = m.group(1)
        if mod not in known:
            continue
        j = text.find("(", m.end() - 1)
        k = _balanced(text, j)
        if k < 0:
            continue
        ov = {}
        for a in _split_top(text[j + 1:k - 1]):
            mm = re.match(r"\.\s*([A-Za-z_]\w*)\s*\((.*)\)\s*$", a, re.S)
            if mm:
                ov[mm.group(1)] = " ".join(mm.group(2).split())
        out.append((mod, ov))
    return out


def _width(rng, env):
    hi, _, lo = rng.partition(":")
    lo = lo or hi
    f = lambda s: eval(re.sub(r"\$clog2", "clog2", s), {"clog2": lambda x: max(0, (int(x) - 1).bit_length()), "__builtins__": {}}, dict(env))  # noqa: E731
    return abs(int(f(hi)) - int(f(lo))) + 1


def _env(pdef, ov, base=None):
    env = dict(base or {})
    for k, v in list(pdef.items()) + list(ov.items()):
        try:
            env[k] = int(eval(re.sub(r"(\d+)'[sS]?[dD](\d+)", r"\2", v), {"__builtins__": {}}, dict(env)))
        except Exception:  # noqa: BLE001
            pass
    return env


def _newest(d, pat):
    try:
        fs = sorted(Path(d).glob(pat), key=lambda p: p.stat().st_mtime)
    except OSError:
        return None
    return str(fs[-1]) if fs else None


def _findings(raw, plan_path, tree=None, **kw):
    import adv_tree_drift as T
    tree = tree or kw.get("tree") or T._find_tree(plan_path)
    if not tree or not (Path(tree) / "rtl").is_dir():
        return [_w("NOT-RUN: no bind tree with rtl/ (kw tree)")]
    die = raw.get("die") if isinstance(raw.get("die"), str) else (raw.get("die") or {}).get("name", "")
    nb = Path(tree) / "physical" / "die_plan" / str(die or "") / "plan_of_record" / "native_bind"
    abp = kw.get("asbuilt") or (_newest(nb, "asbuilt_run*.json") or _newest(nb.parent, "asbuilt*.json") if die else None)
    ab = {}
    if abp and os.path.isfile(abp):
        try:
            ab = json.load(open(abp))
        except (OSError, ValueError):
            ab = {}
    listed = set(ab.get("slang_parameterized_blackboxes") or [])
    dissolve = set(ab.get("dissolve") or []) | {r["module"] for r in ab.get("substitute_parent", []) if isinstance(r, dict) and "module" in r}
    out = []
    # OBSERVED: a bind_tied.json of the bind of record
    bo = kw.get("bind_out")
    tj = (os.path.join(bo, "bind_tied.json") if bo else None) or None
    if not (tj and os.path.isfile(tj)) and nb.is_dir():
        tj = _newest(nb, "**/bind_tied.json")
    obs_types = {}
    if tj and os.path.isfile(tj):
        try:
            rows = json.load(open(tj))
        except (OSError, ValueError):
            rows = []
        inst2type = {}
        for k in ("partitions", "instances"):
            for it in raw.get(k) or []:
                if isinstance(it, dict) and it.get("name") and it.get("type"):
                    inst2type[it["name"]] = it["type"]
        per = defaultdict(lambda: defaultdict(int))
        for r in rows if isinstance(rows, list) else []:
            first = str(r.get("path", "")).split(".")[0]
            t = inst2type.get(first, first)
            per[t][f"{r.get('module')}.{r.get('port')}"] += len(r.get("bits") or [])
        for t, ports in sorted(per.items(), key=lambda kv: -sum(kv[1].values())):
            n = sum(ports.values())
            obs_types[t] = n
            if len(out) < MAX_LINES // 2:
                top = ", ".join(f"{p} {b}" for p, b in sorted(ports.items(), key=lambda kv: -kv[1])[:4])
                out.append(_w(f"OBSERVED {t}: {n} UNBOUND-tied bit(s) in {tj}; top {top}"))
    # PREDICTED: unlisted parameterized blackbox leaves with more than one width-parameter value in the closure.
    # Only the slang frontend shares one blackbox ABI per module (bind_elab: read_slang --empty-blackboxes); native / yosys
    # elaboration reads each instance's own parameters.
    fe = ab.get("frontend", "native") if ab else None
    if fe != "slang":
        out.append(_w("summary", f"OBSERVED {sum(obs_types.values())} tied bit(s) on {len(obs_types)} type(s) ({tj or 'no bind_tied.json found'}); "
                      f"PREDICTED not applicable: as-built {abp or 'none found (kw asbuilt)'} frontend {fe or '?'} "
                      f"(the shared-ABI truncation is a slang-frontend class)"))
        return out
    idx = T.rtl_index(tree)
    closure = T.rtl_closure(raw, tree, index=idx)
    heads, texts = {}, {}

    def text(f):
        if f not in texts:
            try:
                with open(os.path.join(tree, f), errors="replace") as fh:
                    texts[f] = _CMT.sub("", fh.read())
            except OSError:
                texts[f] = ""
        return texts[f]

    known = set(idx[0])
    use = defaultdict(list)                                    # module -> [(file, overrides)]
    # the as-built elaborates the die tops + every DISSOLVE module in full; each module those bodies instantiate and that
    # is not dissolved itself is a slang blackbox leaf (bind_elab.plan_sources).  Without an as-built: every closure file.
    if dissolve:
        bodies = []
        for dm in sorted(dissolve):
            for f in (idx[0].get(dm) or [])[:1]:
                m = re.search(r"(?ms)^\s*module\s+" + re.escape(dm) + r"\b.*?^\s*endmodule\b", text(f))
                if m:
                    bodies.append((f, m.group(), dm))
    else:
        bodies = [(f, text(f), None) for f in closure]
    penv = {}
    for f, body, dm in bodies:
        if dm and dm not in penv:
            h = module_header(body, dm)
            penv[dm] = _env(h[0], {}) if h else {}
        for mod, ov in instances(body, known):
            if mod in dissolve or mod in listed:
                continue
            use[mod].append((f, ov, penv.get(dm) or {}))
    pred = []
    for mod, us in use.items():
        fs = idx[0].get(mod) or []
        if len(fs) != 1:
            continue
        if mod not in heads:
            heads[mod] = module_header(text(fs[0]), mod)
        h = heads[mod]
        if not h or not h[1]:
            continue
        pdef, ports = h
        wp = {tok for rng in ports.values() for tok in re.findall(r"[A-Za-z_]\w*", rng) if tok in pdef}
        sets = {}
        for f, ov, _pe in us:
            key = tuple(sorted((p, ov.get(p, pdef.get(p, "").strip())) for p in wp))
            sets.setdefault(key, []).append(f)
        if len(sets) < 2:
            continue
        bits, unk = 0, 0
        first = None
        for f, ov, pe in us:
            env = _env(pdef, {k: v for k, v in ov.items()}, None)
            for k, v in ov.items():                       # an override naming the parent's parameters: parent defaults
                if k not in env or k in pdef and env.get(k) == _env(pdef, {}).get(k):
                    try:
                        env[k] = int(eval(v, {"__builtins__": {}}, dict(pe)))
                    except Exception:  # noqa: BLE001
                        pass
            try:
                ws = {p: _width(r, env) for p, r in ports.items()}
            except Exception:  # noqa: BLE001
                unk += 1
                continue
            if first is None:
                first = ws
                continue
            bits += sum(abs(ws[p] - first.get(p, ws[p])) for p in ws)
        types = T.closure_types(raw, idx, sorted({u[0] for u in us}))
        tset = sorted({t for v in types.values() for t in v})
        pred.append((mod, len(us), len(sets), sorted(wp), sorted(ports)[:4], bits, unk, tset))
    pred.sort(key=lambda r: (-r[5], -r[1], r[0]))
    pt = defaultdict(int)
    for mod, n, ns, wp, ps, bits, unk, tset in pred:
        for t in tset:
            pt[t] += bits
        if len(out) >= MAX_LINES:
            continue
        out.append(_w(f"PREDICTED {mod}: UNLISTED parameterized blackbox leaf, {n} instance(s) with {ns} distinct width-parameter "
                      f"set(s) ({','.join(wp[:4])}) on port(s) {','.join(ps)}; est >= {bits} bit(s){f' (+{unk} unevaluated)' if unk else ''} "
                      f"cut to the first instance ABI; types {len(tset)} ({','.join(tset[:4])}{' ...' if len(tset) > 4 else ''}); "
                      f"fix = list it in asbuilt slang_parameterized_blackboxes or give each width its own module (S81-SVC-TIED)"))
    top_t = ", ".join(f"{t} {b}" for t, b in sorted(pt.items(), key=lambda kv: -kv[1])[:8])
    out.append(_w("summary", f"OBSERVED {sum(obs_types.values())} tied bit(s) on {len(obs_types)} type(s) "
                  f"({tj or 'no bind_tied.json found'}); PREDICTED {len(pred)} unlisted parameterized leaf module(s), "
                  f"est {sum(r[5] for r in pred)} bit(s) on {sum(1 for v in pt.values() if v)} type(s) ({top_t or 'none'}); "
                  + ("" if dissolve else "NO as-built dissolve list: every closure instance counted (over-estimate); ") + "frontend slang; " + f"as-built {abp or 'none'} lists {len(listed)} parameterized blackbox(es), dissolves {len(dissolve)}; closure {len(closure)} file(s)"))
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--tree")
    ap.add_argument("--asbuilt")
    ap.add_argument("--bind-out")
    a = ap.parse_args()
    for ln in findings(json.load(open(a.plan)), a.plan, a.tree, asbuilt=a.asbuilt, bind_out=a.bind_out):
        print(ln)
