"""ADV-GHOST-MACRO (PRECHECK-R2, estimator, never a gate): placed plan rows with no instance in the bound RTL.

Every placed macro / hard core a type's plan names (hard_cores[], contents[] with a lef, phy_pg_macros[], pads[].macro_pin,
soft_clones[]) must exist in the kit RTL: the bound type module the bind emitted (BIND_OUT/rtl/<module>.sv) wrapped by the
kit as `u_bound`.  A row with no RTL instance is a ghost: it reserves area + keep-outs, steers pins and confuses place, and
the kit fails late (KIT_PREFLIGHT macro_instances / PLAN-SRC-MACRO at place).  Known positive (FAM-S81-SVC-OWN 11-22): the
S81 J7 svc rs/pvso types place u_bound.g_u_rsv_NN_u_u_att_{pmem,land,pvq}_capture.* SRAM rows that only the kit memory
closure (s81_svc_memory_closure.py) creates, but the bound carries the narrow pvq helper 133b963e instead of 9c28130c, so the
closure is NOT_APPLICABLE and none of those instances ever exist.

Resolution per row mirrors the kit: physical_inst (else the plan inst) -> rows without a physical identity are projected
through tools/die_plan/bound_macro_paths.resolve (+ s81_svc_pvso_paths) on the bound text -> the path (minus `u_bound.`)
is walked through the bound module (instances by line regex) and, below it, through module bodies indexed from the bind's
bind.f / rtl dir / the plan's type sources (generate labels transparent; a module with no definition = leaf, accepted).
A missing first-level `<X>_capture` whose base `<X>` is a native helper is a kit memory-closure product: accepted only when
the tree's closure applies() would hold (its NATIVE helper set all instantiated in the bound).

Static source: bound text only (no asbuilt.json / elab); per-file parse is memoised in-process and (with cache_dir or
$OT_ADV_CACHE_DIR) on disk keyed by path+size+mtime.  Missing bind = one "not checked" line.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

CHECK = "ADV-GHOST-MACRO"
MAX_LINES = 20
TREE_BIND_REL = ("physical/die_plan/{die}/plan_of_record/native_bind/out", "physical/die_plan/{die}/plan_of_record/bind_of_record")
_KW = frozenset("""module endmodule if else for while case casez casex endcase begin end assign always always_ff always_comb
always_latch initial function endfunction task endtask generate endgenerate wire reg logic input output inout parameter
localparam genvar integer return default typedef struct union enum package import interface modport bit int byte signed
unsigned real time event assert assume cover property sequence final foreach repeat forever do posedge negedge or and not
supply0 supply1 tri wand wor specify defparam""".split())
_LINE_INST = re.compile(r"(?m)^[ \t]*([A-Za-z_][\w$]*)[ \t]+(?:#[ \t]*\(.*?\)[ \t]*)?(\\\S+|[A-Za-z_][\w$]*)[ \t]*(?:\[[^\]\n]*\][ \t]*)?\(")
_ML_INST = re.compile(r"(?ms)^[ \t]*([A-Za-z_][\w$]*)\s*#\s*\((.*?)\)\s*(\\\S+|[A-Za-z_][\w$]*)\s*(?:\[[^\]]*\]\s*)?\(")
_MODULE = re.compile(r"(?m)^[ \t]*(?:module|macromodule)\s+(?:automatic\s+)?([A-Za-z_][\w$]*)")
_ENDMOD = re.compile(r"(?m)^[ \t]*endmodule\b")
_LABEL = re.compile(r"\bbegin\s*:\s*([A-Za-z_][\w$]*)")
_BLOCK_C = re.compile(r"/\*.*?\*/", re.S)
_LINE_C = re.compile(r"//[^\n]*")
_IDX = re.compile(r"\[[^\]]*\]")
_MEMO = {}


def _w(msg):
    return "WARN %s %s" % (CHECK, msg)


# ------------------------------------------------------------------------------------------------ parsing (memoised)
def _strip(text):
    return _LINE_C.sub("", _BLOCK_C.sub(lambda m: "\n" * m.group(0).count("\n"), text))


def _insts(body):
    out = {}
    for rx in (_LINE_INST, _ML_INST):
        for m in rx.finditer(body):
            mod, name = m.group(1), m.group(m.lastindex)
            if mod in _KW or name in _KW:
                continue
            out.setdefault(name.lstrip("\\"), mod)
    return out


def _parse_file(path, disk):
    """{module: {"i": {inst: module}, "l": [gen labels]}} of one source file (comments stripped)."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    key = "%s|%d|%d" % (path, st.st_size, int(st.st_mtime))
    if key in _MEMO:
        return _MEMO[key]
    if disk is not None and key in disk:
        _MEMO[key] = disk[key]
        return disk[key]
    try:
        text = _strip(Path(path).read_text(errors="replace"))
    except OSError:
        return None
    mods = {}
    starts = [(m.start(), m.group(1)) for m in _MODULE.finditer(text)]
    for i, (s, name) in enumerate(starts):
        e = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        em = _ENDMOD.search(text, s, e)
        body = text[s:em.start() if em else e]
        mods.setdefault(name, {"i": _insts(body), "l": sorted(set(_LABEL.findall(body))),
                               "t": None})
        mods[name]["_body"] = body
    pp = "``" in text                  # token-pasted instance names (`define ... u_eA``Q): not resolvable by regex
    res = {k: {"i": v["i"], "l": v["l"], "pp": pp and "`" in v["_body"]} for k, v in mods.items()}
    # identifier set (cheap fallback for parser misses below the top level)
    for k, v in mods.items():
        res[k]["w"] = sorted(set(re.findall(r"\b[A-Za-z_][\w$]*\b", v["_body"])) - _KW) if len(v["_body"]) < 400000 else None
    _MEMO[key] = res
    if disk is not None:
        disk[key] = res
        disk["__dirty__"] = True
    return res


def _bound_parse(text, module, disk):
    """bound module only: {inst: module} (bound files are generated one instance per line), keyed by the text digest
    (the kit-side text transforms below change it)."""
    import hashlib
    key = "B|%s|%s" % (module, hashlib.sha1(text.encode("utf-8", "replace")).hexdigest())
    if key in _MEMO:
        return _MEMO[key]
    if disk is not None and key in disk:
        _MEMO[key] = disk[key]
        return disk[key]
    m = re.search(r"(?m)^[ \t]*module\s+" + re.escape(module) + r"\b", text)
    body = text[m.start():] if m else text
    em = _ENDMOD.search(body)
    body = body[:em.start()] if em else body
    sb = _strip(body)
    ins = _insts(sb)
    res = {"i": ins, "l": sorted(set(_LABEL.findall(sb))), "mods": sorted(set(ins.values()))}
    _MEMO[key] = res
    if disk is not None:
        disk[key] = res
        disk["__dirty__"] = True
    return res


def _kit_text(text, t, kcc):
    """the kit-rtl renames that change instance names (bind.py kit-rtl): QC A0 cores u_t<r><c> replace their native
    leaves u_u_t_<r>_<c> (kit_core_clocks.swap_native_cores).  A transform that refuses is the kit's own error: no swap."""
    if kcc is None:
        return text, None
    try:
        return kcc.swap_native_cores(text, t.get("hard_cores"))[0], None
    except Exception as e:
        return text, "kit core swap refuses: %s" % str(e)[:120]


# ------------------------------------------------------------------------------------------------ inputs
def _die_names(raw, plan_path, tree):
    names = []
    d = raw.get("die") or {}
    for k in ("name", "label"):
        if isinstance(d.get(k), str):
            names.append(d[k])
    pp = str(plan_path or "")
    m = re.search(r"/physical/die_plan/([^/]+)/", pp)
    if m:
        names.append(m.group(1))
    if tree and os.path.isdir(os.path.join(tree, "physical", "die_plan")):
        names += sorted(os.listdir(os.path.join(tree, "physical", "die_plan")))
    return list(dict.fromkeys(names))


def _report_modules(bdir):
    """{type: bound module} from BIND_OUT/bind_report.json (bind.py kit-rtl reads the same map: a type whose plan module
    is shared binds as <module>__<type>); {} without a report."""
    k = "R|" + bdir
    if k not in _MEMO:
        try:
            r = json.loads(Path(bdir, "bind_report.json").read_text())
            _MEMO[k] = {tn: v.get("module") for tn, v in (r.get("types") or {}).items() if isinstance(v, dict)}
        except (OSError, ValueError, AttributeError):
            _MEMO[k] = {}
    return _MEMO[k]


def _bound_path(bdir, module, tn=None):
    """(path, module) of the bound type module in a bind dir, else (None, None)."""
    mods = [m for m in (_report_modules(bdir).get(tn) if tn else None, module) if m]
    for m in dict.fromkeys(mods):
        for p in (os.path.join(bdir, "rtl", m + ".sv"), os.path.join(bdir, m + ".sv")):
            if os.path.isfile(p):
                return p, m
    return None, None


def _bind_dirs(raw, plan_path, tree, kw):
    """candidate bind out dirs, best first: explicit > plan-of-record in the tree > plan-adjacent > sibling <tree>_bind*."""
    exp = kw.get("bind_out") or os.environ.get("OT_ADV_BIND_OUT")
    if exp:
        return [str(exp)]
    c = []
    if tree:
        for die in _die_names(raw, plan_path, tree):
            for rel in TREE_BIND_REL:
                c.append(os.path.join(tree, rel.format(die=die)))
    if plan_path:
        pd = os.path.dirname(os.path.abspath(str(plan_path)))
        for rel in ("bind_of_record", "native_bind/out", "published", "bind", "out", "../published", "../bind_of_record"):
            c.append(os.path.normpath(os.path.join(pd, rel)))
    if tree:
        t = str(tree).rstrip("/")
        par = os.path.dirname(t)
        try:
            c += [os.path.join(par, n) for n in sorted(os.listdir(par)) if n.startswith(os.path.basename(t) + "_bind")]
        except OSError:
            pass
    return [d for d in dict.fromkeys(c) if os.path.isdir(d)]


def _choose_bind(raw, plan_path, tree, kw, types):
    best, best_n = None, 0
    for d in _bind_dirs(raw, plan_path, tree, kw):
        n = sum(1 for tn, t in types.items() if isinstance(t, dict) and t.get("module") and _bound_path(d, t["module"], tn)[0])
        if n > best_n:
            best, best_n = d, n
    return best, best_n


def _relocate(p, tree, bdir):
    if os.path.isabs(p) and os.path.isfile(p):
        return p
    if not os.path.isabs(p):
        for base in (tree, bdir):
            if base and os.path.isfile(os.path.join(base, p)):
                return os.path.join(base, p)
    for anchor in ("/rtl/", "/physical/", "/results/", "/tools/"):
        i = p.find(anchor)
        if i >= 0 and tree and os.path.isfile(os.path.join(tree, p[i + 1:])):
            return os.path.join(tree, p[i + 1:])
    return None


class _Index:
    """module name -> parsed def, built lazily from bind.f + bind rtl dirs + plan sources (first definition wins)."""

    def __init__(self, bdir, tree, raw, disk):
        self.bdir, self.tree, self.raw, self.disk = bdir, tree, raw, disk
        self.files, self.mod_file, self.built = None, {}, False

    def _file_list(self):
        fl = []
        bf = os.path.join(self.bdir, "bind.f")
        if os.path.isfile(bf):
            for tok in Path(bf).read_text(errors="replace").split():
                if tok.startswith(("+", "-")):
                    continue
                r = _relocate(tok, self.tree, self.bdir)
                if r:
                    fl.append(r)
        for sub in ("rtl", "structural_full", "structural_tops", "rtl/native_glue", ""):
            d = os.path.join(self.bdir, sub)
            if os.path.isdir(d):
                fl += sorted(os.path.join(d, n) for n in os.listdir(d) if n.endswith((".sv", ".v")))
        for t in (self.raw.get("partition_types") or {}).values():
            for s in t.get("sources") or []:
                if isinstance(s, str):
                    r = _relocate(s, self.tree, self.bdir)
                    if r:
                        fl.append(r)
        return list(dict.fromkeys(fl))

    def build(self):
        if self.built:
            return
        self.built = True
        self.files = self._file_list()
        rx = re.compile(rb"(?m)^[ \t]*(?:module|macromodule)\s+([A-Za-z_][\w$]*)")
        for f in self.files:
            key = "M|%s" % f
            try:
                st = os.stat(f)
            except OSError:
                continue
            k2 = "%s|%d|%d" % (key, st.st_size, int(st.st_mtime))
            names = _MEMO.get(k2) or (self.disk or {}).get(k2)
            if names is None:
                try:
                    names = [m.group(1).decode() for m in rx.finditer(Path(f).read_bytes())]
                except OSError:
                    continue
                _MEMO[k2] = names
                if self.disk is not None:
                    self.disk[k2] = names
                    self.disk["__dirty__"] = True
            for n in names:
                self.mod_file.setdefault(n, []).append(f)

    def get(self, module):
        """first definition with a body (instances or generate labels); a bind blackbox / structural port stub (S81
        structural_full/*_ot_s81sl_vn.sv: vn_b with no u_h1) is no evidence, so only stubs = None (leaf, accepted)."""
        self.build()
        for f in self.mod_file.get(module) or ():
            d = (_parse_file(f, self.disk) or {}).get(module)
            if d and (d["i"] or d["l"]):
                return d
        return None


# ------------------------------------------------------------------------------------------------ resolution
def _segs(path):
    return [s for s in (_IDX.sub("", x) for x in path.split(".")) if s]


def _walk(segs, top, index):
    """-> (ok, depth_failed, reason).  top = bound parse; below: module defs from the index."""
    cur = top
    for i, s in enumerate(segs):
        if cur is None:
            return True, None, "leaf"                      # no definition (macro / blackbox / generated leaf): accept
        if s in cur["i"]:
            mod = cur["i"][s]
            cur = index.get(mod) if i + 1 < len(segs) else None
            continue
        if s in cur.get("l", ()):
            continue                                       # generate block label
        w = cur.get("w")
        if i > 0 and (w is None or s in w or cur.get("pp")):
            return True, None, "text"       # named in the body / built by a token-pasting macro (parser miss): accept
        return False, i, None
    return True, None, "full"


def _closure_native(tree, dirs):
    for d in dirs:
        f = os.path.join(d, "s81_svc_memory_closure.py")
        if os.path.isfile(f):
            m = re.search(r"(?ms)^NATIVE\s*=\s*\((.*?)\)", Path(f).read_text(errors="replace"))
            if m:
                return re.findall(r"'([^']+)'|\"([^\"]+)\"", m.group(1)), f
    return None, None


def _tool_dirs(tree):
    ds = []
    if tree:
        ds.append(os.path.join(tree, "tools", "die_plan"))
    ds.append(os.path.dirname(os.path.abspath(__file__)))
    return [d for d in dict.fromkeys(ds) if os.path.isdir(d)]


def _import(name, dirs):
    for d in dirs:
        if os.path.isfile(os.path.join(d, name + ".py")):
            if d not in sys.path:
                sys.path.insert(0, d)
            try:
                mod = __import__(name)
                return mod
            except Exception:
                return None
    return None


def _rows(t):
    """(kind, plan inst, path the kit places, module, area um2) for every placed row of a type."""
    out = []
    hc_names = set()
    for c in t.get("hard_cores") or []:
        if isinstance(c, dict) and c.get("inst"):
            hc_names.add(c["inst"])
            out.append(("hard_core", c, c["inst"]))
    for c in t.get("contents") or []:
        if isinstance(c, dict) and c.get("inst") and c.get("lef") and c["inst"] not in hc_names:
            out.append(("macro", c, c["inst"]))
    for p in t.get("phy_pg_macros") or []:
        if isinstance(p, str):
            out.append(("phy_pg_macro", {"inst": p, "physical_inst": p}, p))
    for p in t.get("pads") or []:
        mp = p.get("macro_pin") if isinstance(p, dict) else None
        if isinstance(mp, dict) and mp.get("inst"):
            out.append(("pad_macro_pin", {"inst": mp["inst"], "physical_inst": mp["inst"]}, mp["inst"]))
    for s in t.get("soft_clones") or []:
        if isinstance(s, dict) and s.get("physical_inst"):
            out.append(("soft_clone", {"inst": s["physical_inst"], "physical_inst": s["physical_inst"],
                                       "module": s.get("master")}, s["physical_inst"]))
    seen, res = set(), []
    for kind, c, inst in out:
        key = (kind, inst)
        if key in seen:
            continue
        seen.add(key)
        ol = c.get("outline_um") or [0, 0]
        try:
            area = float(ol[0]) * float(ol[1])
        except (TypeError, ValueError, IndexError):
            area = 0.0
        res.append((kind, c, inst, c.get("module"), area))
    return res


def _group(paths):
    g = {}
    for p in paths:
        k = re.sub(r"\[\d+\]", "[*]", p)
        k = re.sub(r"(?<=[._])\d+(?=[._]|$)", "*", k)
        g.setdefault(k, []).append(p)
    return sorted(g.items(), key=lambda kv: -len(kv[1]))


def type_ghosts(tn, t, bpath, index, mods, native, disk, bmod=None):
    """-> (ghost rows [(kind, inst, path, reason, area)], checked row count)."""
    rows = _rows(t)
    if not rows:
        return [], 0
    try:
        raw_text = Path(bpath).read_text(errors="replace")
    except OSError:
        return None, 0
    bmp, pvso, kcc = mods
    raw_text, swap_err = _kit_text(raw_text, t, kcc)
    bmod = bmod or t["module"]
    top = _bound_parse(raw_text, bmod, disk)
    need_raw = any("physical_inst" not in c and "physical_master" not in c for _, c, _, _, _ in rows)
    proj = {}
    if need_raw:
        try:
            if bmp is not None:
                for r in bmp.resolve(t, raw_text):
                    proj.setdefault(r["inst"], r["physical_inst"])
        except Exception:
            pass
        try:
            if pvso is not None:
                for r in pvso.resolve(tn, t, raw_text):
                    proj.setdefault(r["inst"], r["physical_inst"])
        except Exception:
            pass
    bound_mods = set(top.get("mods") or top["i"].values())
    closure_ok = None
    if native:
        closure_ok = all(any(re.match(re.escape(n) + r"\b", m) for m in bound_mods) for n in native)
    ghosts = []
    for kind, c, inst, module, area in rows:
        path = c.get("physical_inst") or proj.get(inst) or inst
        p = path[len("u_bound."):] if path.startswith("u_bound.") else path
        segs = _segs(p)
        if not segs:
            continue
        if segs[0] not in top["i"] and not path.startswith("u_bound."):
            # bound_macro_paths._resolve_flat / gen_phys leaf ids: a flat plan core <inst> is bound leaf u_<inst>
            # (also for hard cores without a lef, which _resolve_flat skips)
            for alt in ("u_" + segs[0], "u_" + re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9_]", "_", segs[0])).strip("_")):
                if alt in top["i"]:
                    segs = [alt] + segs[1:]
                    break
        ok, at, why = _walk(segs, top, index)
        if ok:
            continue
        if at == 0:
            f = segs[0]
            m = re.match(r"(.+?)_(capture|capture_v2|fit|staging_fit)$", f)
            base = m.group(1) if m else None
            if base and base in top["i"]:
                bmod = top["i"][base]
                if closure_ok:
                    continue                               # kit memory closure creates it
                miss = [n for n in (native or []) if not any(x.startswith(n) for x in bound_mods)]
                reason = ("kit-closure product of %s (%s); closure NOT_APPLICABLE: bound lacks native helper %s"
                          % (base, bmod[:28], ",".join(x[:28] for x in miss) or "?") if native else
                          "kit-generated name of %s (%s) with no closure tool to create it" % (base, bmod[:28]))
            elif c.get("physical_inst") and not path.startswith("u_bound."):
                reason = ("physical_inst is a plan path, not u_bound.<bound inst> (rows with a physical identity are never "
                          "projected through the as-built map)")
            elif inst not in proj and not path.startswith("u_bound."):
                reason = "plan path %s maps to no bound instance (no as-built root, no u_bound leaf)" % segs[0]
            else:
                reason = "no instance %s in bound %s" % (f, bmod) + ("; " + swap_err if swap_err else "")
        else:
            reason = "no %s under %s" % (segs[at], ".".join(segs[:at]))
        ghosts.append((kind, inst, path, reason, area))
    return ghosts, len(rows)


def findings(raw, plan_path, tree=None, **kw):
    t0 = time.time()
    try:
        return _findings(raw, plan_path, tree, kw, t0)
    except Exception as e:  # estimator: never raise
        return [_w("not checked: %s: %s" % (type(e).__name__, str(e)[:160]))]


def _findings(raw, plan_path, tree, kw, t0):
    types = (raw or {}).get("partition_types") or {}
    if not types:
        return [_w("not checked: plan has no partition_types")]
    tree = str(tree) if tree else None
    bdir, ncov = _choose_bind(raw, plan_path, tree, kw, types)
    if not bdir:
        return [_w("not checked: no bound RTL (no BIND_OUT/rtl/<module>.sv for any type; pass bind_out=)")]
    cache_dir = kw.get("cache_dir") or os.environ.get("OT_ADV_CACHE_DIR")
    disk, cfile = None, None
    if cache_dir:
        cfile = os.path.join(cache_dir, "adv_ghost_macro_cache.v2.json")
        try:
            disk = json.loads(Path(cfile).read_text())
        except (OSError, ValueError):
            disk = {}
    tdirs = _tool_dirs(tree)
    mods = (_import("bound_macro_paths", tdirs), _import("s81_svc_pvso_paths", tdirs), _import("kit_core_clocks", tdirs))
    native, _ = _closure_native(tree, tdirs)
    native = [a or b for a, b in native] if native else None
    index = _Index(bdir, tree, raw, disk)
    max_lines = int(kw.get("max_lines", MAX_LINES))
    lines, n_ghost, n_types, n_rows, area, unchecked, n_hard = [], 0, 0, 0, 0.0, [], 0
    per = []
    for tn in sorted(types):
        t = types[tn]
        if not isinstance(t, dict) or not t.get("module") or not _rows(t):
            continue
        if t.get("hard") is True:
            n_hard += 1                  # a hard type is placed as its own signed view (QC phy_*: bare PHY macro), no kit
            continue
        bp, bmod = _bound_path(bdir, t["module"], tn)
        if not bp:
            unchecked.append(tn)
            continue
        g, n = type_ghosts(tn, t, bp, index, mods, native, disk, bmod)
        if g is None:
            unchecked.append(tn)
            continue
        n_rows += n
        if g:
            n_types += 1
            n_ghost += len(g)
            a = sum(x[4] for x in g)
            area += a
            per.append((tn, bmod, g, n, a))
    per.sort(key=lambda x: (-len(x[2]), x[0]))
    for tn, module, g, n, a in per[:max_lines]:
        parts = []
        for k, members in _group([x[2] for x in g])[:3]:
            why = next(x[3] for x in g if x[2] == members[0])
            parts.append("%s x%d (%s)" % (k, len(members), why))
        more = len(_group([x[2] for x in g])) - 3
        lines.append(_w("%s: %d/%d placed rows have no instance in bound %s (threshold 0), %.0f um2 reserved: %s%s; fix: drop/rename "
                        "the rows to bound paths, or make the bind/kit emit the instances" % (
                            tn, len(g), n, module, a, "; ".join(parts), "; +%d more groups" % more if more > 0 else "")))
    prov = ""
    try:
        pb = json.loads(Path(bdir, "provenance_bind.json").read_text()).get("provenance", {}).get("plan")
        if pb and not os.path.isabs(pb) and tree:
            pb = os.path.join(tree, pb)
        if pb and plan_path and os.path.abspath(pb) != os.path.abspath(str(plan_path)):
            same = (os.path.isfile(pb) and os.path.getsize(pb) == os.path.getsize(str(plan_path))
                    and Path(pb).read_bytes() == Path(str(plan_path)).read_bytes())
            if not same:
                prov = "; CAVEAT bind was made from another plan (%s): a ghost may be bind staleness, re-check on this plan's bind" % pb
    except (OSError, ValueError, AttributeError):
        pass
    summ = ("summary: %d ghost rows in %d types (%.0f um2) over %d placed rows; bind %s covers %d/%d types (%d hard types skipped)%s; %.1f s" % (
        n_ghost, n_types, area, n_rows, bdir, ncov, len(types), n_hard,
        ("; not checked (no bound module): %d types e.g. %s" % (len(unchecked), ",".join(unchecked[:3]))) if unchecked else "",
        time.time() - t0)) + prov
    lines.append(_w(summ))
    if disk is not None and disk.pop("__dirty__", None):
        try:
            os.makedirs(cache_dir, exist_ok=True)
            tmp = cfile + ".%d.tmp" % os.getpid()
            Path(tmp).write_text(json.dumps(disk))
            os.replace(tmp, cfile)
        except OSError:
            pass
    return lines


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--tree")
    ap.add_argument("--bind-out")
    ap.add_argument("--cache-dir")
    ap.add_argument("--max-lines", type=int, default=MAX_LINES)
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    t0 = time.time()
    out = findings(raw, a.plan, a.tree, bind_out=a.bind_out, cache_dir=a.cache_dir, max_lines=a.max_lines)
    print("\n".join(out))
    print("# findings() %.1f s (plan load excluded)" % (time.time() - t0))


if __name__ == "__main__":
    main()
