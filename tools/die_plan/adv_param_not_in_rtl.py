"""ADV-PARAM-NOT-IN-RTL (P-PLAN-AHEAD-OF-RTL 11-27, PRECHECK, report only, never a gate): a parameter the plan sets on a leaf master must
exist in the as-built elaboration / the bound RTL.

Class (S81 11-26 CUT-2100): the WREG row d44304a8a2c5 (6 ops, partition_types[T].leaf_params {module, params {WREG: 1}}) set a parameter the
bound leaf RTL does not declare.  bind.regen_params refuses it ("PARAM_REGEN <leaf>.WREG: not a parameter of the leaf") on every
type of the row; forms v3 / v4 each lost a ~35 min whole 48-thread bind to it because scoped PRE never looked.

Statically (plan + tree, seconds): for every partition_types[T].leaf_params[].params key on module M, the key must be declared by M in one of
  RTL       a `module M` definition in the tree (rtl/, physical/die_plan/*): header `#(parameter ...)` or a `parameter` in the body
            (when several definitions of M exist, declared in ANY counts: the bind picks one, so only a name no definition has is reported)
  DECLARE   as-built manifest param_regen.declare[M] (parameters the netlist cannot show, bind.regen_params)
  NETLIST   an instance `M #(.P(..)) u (` in the as-built netlist text (the elaborated parameter list the bind starts from)
Same acceptance as bind.regen_params (c.params / param_defaults / declare), computed without the bind.  A master with no definition anywhere is
NOT-CHECKED (listed once, never counted clean).
findings(raw, plan_path, tree=None, **kw) -> ["WARN ADV-PARAM-NOT-IN-RTL ..."]; kw asbuilt=PATH (as-built manifest).
"""
import json
import os
import re
import time
from pathlib import Path

TAG = "ADV-PARAM-NOT-IN-RTL"
MAX_LINES = 20
SKIP_DIRS = frozenset(("results", "run", "runs", "logs", "objects", "kits", "reports", "tmp", "work", ".git"))
_CMT = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)
_PAR = re.compile(r"\b(?:parameter|localparam)\b(?:\s+(?:integer|int|logic|bit|signed|unsigned|real|string))*\s*(?:\[[^\]]*\]\s*)*([A-Za-z_]\w*)\s*=")
_PAR_LIST = re.compile(r"\bparameter\b([^;]*?)(?:;|$)", re.S)


def _w(*p):
    return " ".join(["WARN", TAG] + [str(x) for x in p])


def leaf_param_rules(raw):
    """-> [(type, index, module, [param names])] of partition_types[T].leaf_params"""
    out = []
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        rules = t.get("leaf_params") if isinstance(t, dict) else None
        for j, r in enumerate(rules if isinstance(rules, list) else []):
            if isinstance(r, dict) and r.get("module") and isinstance(r.get("params"), dict):
                out.append((tn, j, str(r["module"]), sorted(r["params"])))
    return out


def module_params(text, name):
    """-> set of parameter names of every `module <name>` in the source text (header list + body declarations), or None when undefined"""
    text = _CMT.sub(" ", text)
    res = None
    for m in re.finditer(r"\bmodule\s+" + re.escape(name) + r"\b", text):
        end = text.find("endmodule", m.end())
        body = text[m.end(): end if end >= 0 else len(text)]
        names = set()
        for seg in _PAR_LIST.finditer(body):               # `parameter a = 1, b = 2, ...` incl. the #( ) header list and comma chains
            names.update(_param_names(seg.group(0)))
        for hdr in re.finditer(r"#\s*\(", body[:20000]):   # header list may repeat `parameter` per item without `;`
            depth, i = 1, hdr.end()
            while i < len(body) and depth:
                depth += (body[i] == "(") - (body[i] == ")")
                i += 1
            names.update(_param_names(body[hdr.end(): i - 1]))
            break
        res = (res or set()) | names
    return res


def _param_names(seg):
    """names declared by `parameter [type] [range] N = v, M = v ...` (also bare `, M = v` continuation items)"""
    out, depth, cur = [], 0, ""
    for ch in seg:
        depth += ch in "([{"
        depth -= ch in ")]}"
        if ch == "," and depth <= 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    names = []
    for item in out:
        m = re.search(r"([A-Za-z_]\w*)\s*=", item)
        if m and not re.match(r"\s*\.", item):
            names.append(m.group(1))
    return names


def _rtl_files(tree):
    for sub in ("rtl", "physical"):
        root = Path(tree) / sub
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in SKIP_DIRS]
            for fn in fns:
                if fn.endswith((".sv", ".v")):
                    yield Path(dp) / fn


def scan_tree(tree, modules, budget_s=60.0):
    """-> {module: set(params) | None(no definition found)} from the RTL under tree"""
    t0 = time.time()
    pats = {m: re.compile(rb"\bmodule\s+" + re.escape(m.encode()) + rb"\b") for m in modules}
    got = {m: None for m in modules}
    for f in _rtl_files(tree):
        if time.time() - t0 > budget_s:
            break
        try:
            if f.stat().st_size > 12_000_000:
                continue
            b = f.read_bytes()
        except OSError:
            continue
        hit = [m for m, p in pats.items() if p.search(b)]
        if hit:
            txt = b.decode("utf-8", "replace")
            for m in hit:
                ps = module_params(txt, m)
                if ps is not None:
                    got[m] = (got[m] or set()) | ps
    return got


def asbuilt_params(asbuilt, modules):
    """-> ({module: params from param_regen.declare}, {module: params named on its netlist instances}); both {} without a manifest"""
    decl, net = {}, {}
    try:
        ab = json.loads(Path(asbuilt).read_text())
    except Exception:
        return decl, net
    for m, d in ((ab.get("param_regen") or {}).get("declare") or {}).items():
        if m in modules and isinstance(d, dict):
            decl[m] = set(d)
    base = Path(asbuilt).resolve().parent / (ab.get("base") or ".")
    for nl in ab.get("netlist") or []:
        f = Path(nl) if os.path.isabs(nl) else base / nl
        try:
            txt = f.read_text(errors="replace")
        except OSError:
            continue
        for m in modules:
            for inst in re.finditer(r"\b" + re.escape(m) + r"\s*#\s*\(((?:[^()]|\((?:[^()]|\([^()]*\))*\))*)\)\s*[\\\w]", txt):
                net.setdefault(m, set()).update(re.findall(r"\.\s*(\w+)\s*\(", inst.group(1)))
    return decl, net


def _find_tree(plan_path, tree):
    if tree:
        return Path(tree)
    p = Path(plan_path).resolve() if plan_path else None
    for a in (p.parents if p else []):
        if (a / "rtl").is_dir():
            return a
    return None


def findings(raw, plan_path, tree=None, **kw):
    rules = leaf_param_rules(raw)
    if not rules:
        return []
    tree = _find_tree(plan_path, tree)
    mods = sorted({m for _t, _j, m, _p in rules})
    rtl = scan_tree(tree, mods) if tree else {m: None for m in mods}
    ab = kw.get("asbuilt")
    decl, net = asbuilt_params(ab, set(mods)) if ab else ({}, {})
    declared = {m: (rtl.get(m) or set()) | decl.get(m, set()) | net.get(m, set()) for m in mods}
    known = {m for m in mods if rtl.get(m) is not None or m in decl or m in net}
    out, missing, unchecked, nparams = [], {}, set(), 0
    for tn, j, m, ps in rules:
        if m not in known:
            unchecked.add(m)
            continue
        for p in ps:
            nparams += 1
            if p not in declared[m]:
                missing.setdefault((m, p), []).append(f"{tn}[{j}]")
    for (m, p), tl in sorted(missing.items()):
        out.append(_w(f"{m}.{p}: PARAM-NOT-IN-RTL plan sets {p} on {len(tl)} type rule(s) ({', '.join(tl[:6])}{' ...' if len(tl) > 6 else ''}) "
                      f"but no `module {m}` in the tree and no as-built declare / netlist instance declares it; bind refuses each leaf "
                      f"(PARAM_REGEN ... not a parameter of the leaf).  Fix: land the RTL parameter and re-elaborate the as-built, or drop the row"))
    for m in sorted(unchecked):
        out.append(_w(f"{m}: NOT-CHECKED no `module {m}` definition under the tree and no as-built record of it"))
    out.append(_w(f"{len(rules)} leaf_params rule(s) on {len({r[0] for r in rules})} type(s), {nparams} param setting(s): "
                  f"{sum(len(v) for v in missing.values())} type rule(s) set a parameter the RTL does not declare, {len(unchecked)} master(s) not checked"))
    return out
