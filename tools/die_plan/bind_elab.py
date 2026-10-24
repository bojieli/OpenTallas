"""bind_elab: the as-built die, elaborated and flattened to its leaves (front end of tools/die_plan/bind.py).

The as-built die top (a GEN die.v or a hand-written die top) and the RTL below it are elaborated by Yosys:

  * the die top and every DISSOLVE module (`asbuilt.dissolve`: structural parents the plan splits across partitions,
    e.g. a CB16 cluster or a slice flat parent) are read in full;
  * every other module is a LEAF: read with `read_verilog -lib` (interface only) and black-boxed after `hierarchy`,
    so its RTL is instantiated unchanged by the generated partitions, with the parameters Yosys derived for it;
  * a master with no RTL at all (a die relay / landing / reset repeater of the GEN) stays an unknown cell; it must be
    removed by an `asbuilt.transport` rule (which also gives its port directions).

`flatten()` walks the Yosys JSON from the top through the dissolved modules and returns one `Flat` netlist: every
leaf / glue / unknown cell with its full instance path, module (original name), parameters and per-bit pin nets
(global net ids; constants as '0' '1' 'x' 'z').

    python3 tools/die_plan/bind.py elab PLAN.json --out DIR      (writes DIR/asbuilt.json, the Yosys netlist)
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SKIP_DIR = re.compile(r"/(test|tests|tb|bench)/|/tb_[^/]*$|_tb\.s?v$")
MOD_RE = re.compile(r"^\s*(?:\(\*[^\n]*?\*\)\s*)?module\s+([A-Za-z_][A-Za-z0-9_$]*)", re.M)
INST_RE = re.compile(r"(?<![.\w$`])([A-Za-z_][A-Za-z0-9_$]*)(?![A-Za-z0-9_$])(?=\s*(?:#\s*\(|[A-Za-z_\\`]))")  # filtered by the index
YOSYS_IMAGE = os.environ.get("OT_BIND_YOSYS_IMAGE", "openroad/orfs:asap7lock")
YOSYS_IN_IMAGE = "/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys"


class ElabError(Exception):
    pass


def _strip(text):
    text = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def module_index(roots, files, base):
    """{module: [file, ...]} over the RTL roots (recursively, test benches skipped) and the extra files."""
    idx = {}
    paths = []
    for r in roots:
        rp = Path(r) if Path(r).is_absolute() else Path(base) / r
        if rp.is_file():
            paths.append(rp)
            continue
        for p in sorted(list(rp.rglob("*.sv")) + list(rp.rglob("*.v"))):
            if not SKIP_DIR.search(str(p)):
                paths.append(p)
    paths += [Path(f) if Path(f).is_absolute() else Path(base) / f for f in files]
    for p in paths:
        try:
            t = p.read_text(errors="replace")
        except OSError:
            continue
        if "module" not in t:
            continue
        for m in MOD_RE.finditer(_strip(t)):
            idx.setdefault(m.group(1), [])
            if str(p) not in idx[m.group(1)]:
                idx[m.group(1)].append(str(p))
    return idx


def module_body(path, name):
    t = _strip(Path(path).read_text(errors="replace"))
    m = re.search(r"^\s*(?:\(\*[^\n]*?\*\)\s*)?module\s+" + re.escape(name) + r"\b(.*?)\bendmodule\b", t, re.S | re.M)
    return m.group(1) if m else ""


def instantiated(body, idx):
    return {m.group(1) for m in INST_RE.finditer(body) if m.group(1) in idx}


def closure(names, idx, prefer):
    """every file needed to elaborate `names` fully (their own definitions and everything below them)."""
    seen, files, missing = set(), [], set()
    todo = list(names)
    while todo:
        n = todo.pop()
        if n in seen:
            continue
        seen.add(n)
        f, _ = pick(idx, n, prefer)
        if f is None:
            missing.add(n)
            continue
        if f not in files:
            files.append(f)
            # a tool reads the whole file: every module defined in it needs its children too
            for m in MOD_RE.finditer(_strip(Path(f).read_text(errors="replace"))):
                todo += sorted(instantiated(module_body(f, m.group(1)), idx))
        todo += sorted(instantiated(module_body(f, n), idx))
    return files, sorted(missing)


def pick(idx, name, prefer):
    """the one file whose definition of `name` is used: a `prefer` file wins (the later entry), else the only one;
    several candidates with no preference -> the first path that is not a black box (_bb.v), recorded as ambiguous."""
    c = idx.get(name, [])
    if not c:
        return None, False
    pr = [f for f in c if any(Path(f).resolve() == Path(p).resolve() for p in prefer)]
    if pr:
        return max(pr, key=lambda f: max(i for i, p in enumerate(prefer) if Path(p).resolve() == Path(f).resolve())), False
    # preferred directories (e.g. the hard-macro libraries, in die_port_bind MACRO_DIRS order): behavioural model first
    dirs = [str(Path(p).resolve()) + "/" for p in prefer if Path(p).is_dir()]
    for d in dirs:
        ind = [f for f in c if str(Path(f).resolve()).startswith(d)]
        if ind:
            nb = [f for f in ind if not f.endswith("_bb.v")] or ind
            return nb[0], False
    nb = [f for f in c if not f.endswith("_bb.v")] or c
    return nb[0], len(set(nb)) > 1


def make_shim(orig_file, orig, rule, repl_file):
    """a generated module named `orig` (its own header, parameters accepted) that instantiates the substitute module:
    asbuilt.substitute {orig: {"module": M, "ports": {orig_port: [M ports...]}, "params": {...}, "reason": ...}}.
    Ports not named map to the same name; substitute inputs left unconnected are reported UNDRIVEN by bind."""
    sys_path = str(Path(__file__).resolve().parents[1])
    import sys as _s
    if sys_path not in _s.path:
        _s.path.insert(0, sys_path)
    import die_port_bind as D
    rule = {"module": rule} if isinstance(rule, str) else rule
    om = next(m for m in D.parse_modules(Path(orig_file).read_text(errors="replace"), orig_file) if m.name == orig)
    rm = next(m for m in D.parse_modules(Path(repl_file).read_text(errors="replace"), repl_file) if m.name == rule["module"])
    pdecl = ", ".join(f"parameter {k} = {v}" for k, v in om.params.items()
                      if re.search(r"\bparameter\b[^;]*\b" + re.escape(k) + r"\b", Path(orig_file).read_text(errors="replace")))
    ports = []
    for pn in om.order:
        d, rng = om.ports[pn]
        r = "".join(f"[{a}:{b}]" for a, b in rng)
        ports.append(f"    {d} wire {r} {pn}")
    pm = rule.get("ports", {})
    conns, assigns = {}, []
    for pn in om.order:
        d = om.ports[pn][0]
        for q in pm.get(pn, [pn]):
            if q not in rm.ports:
                continue
            if d == "input":
                conns[q] = pn
            elif q not in conns:
                conns[q] = f"s_{q}"
                assigns.append((pn, q))
            else:
                assigns.append((pn, q))
            if d != "input":
                break
    missing_in = [q for q in rm.order if q not in conns and rm.ports[q][0] == "input"]
    missing_out = [q for q in rm.order if q not in conns and rm.ports[q][0] == "output"]
    unmapped = [pn for pn in om.order if not any(q in rm.ports for q in pm.get(pn, [pn]))]
    rp = ", ".join(f".{k}({v})" for k, v in rule.get("params", {}).items())
    wdecl = "".join(f"    wire {''.join(f'[{a}:{b}]' for a, b in rm.ports[q][1])} s_{q};\n" for _, q in assigns
                    if conns.get(q) == f"s_{q}" and not any(x == q for x in [y for _, y in assigns][:0]))
    wdecl = "".join(sorted(set(wdecl.splitlines(True))))
    cs = ",\n".join(f"        .{q}({conns[q]})" if q in conns else f"        .{q}()" for q in rm.order)
    asg = "".join(f"    assign {pn} = s_{q};\n" for pn, q in assigns)
    txt = (f"// GENERATED by tools/die_plan/bind_elab.py: as-built substitution {orig} -> {rule['module']} "
           f"({rule.get('reason', 'no reason given')}).  Do not edit.\n"
           f"module {orig} " + (f"#({pdecl}) " if pdecl else "") + "(\n" + ",\n".join(ports) + "\n);\n" + wdecl +
           f"    {rule['module']}" + (f" #({rp})" if rp else "") + f" u_sub (\n{cs}\n    );\n" + asg + "endmodule\n")
    return txt, dict(orig=orig, module=rule["module"], unconnected_inputs=missing_in, open_outputs=missing_out,
                     orig_ports_unmapped=unmapped, reason=rule.get("reason"))


def plan_sources(ab, base, idx=None, shim_dir=None):
    """resolve the as-built source set: (top files, full files, lib files, record).  Full = the die top(s) and every
    dissolve module's file; lib = one file per leaf module referenced by them (interface only)."""
    roots = ab.get("rtl_roots", ["rtl"])
    files = list(ab.get("files", []))
    tops = [str(Path(base) / f) if not Path(f).is_absolute() else f for f in ab["netlist"]]
    if idx is None:
        idx = module_index(roots, files, base)
    prefer = [str(Path(base) / f) if not Path(f).is_absolute() else f for f in ab.get("prefer", [])]
    subst = ab.get("substitute", {})
    pvar = [r["module"] for r in ab.get("substitute_parent", [])]
    dissolve = set(ab.get("dissolve", [])) | set(pvar)
    full, lib, amb, missing = [], [], {}, set()
    seen = set()
    todo = list(pvar)               # per-instance variants of dissolved parents are elaborated too
    for t in tops:
        body = _strip(Path(t).read_text(errors="replace"))
        todo += sorted(instantiated(body, idx))
        # die masters that are not defined anywhere (relays of a GEN die.v) stay unknown cells
        for m in re.finditer(r"^\s+([A-Za-z_][A-Za-z0-9_$]*)\s+(?:#\s*\(.*?\)\s*)?[A-Za-z_\\]\S*\s*\(", body, re.M):
            if m.group(1) not in idx and m.group(1) not in ("module", "input", "output", "wire", "assign"):
                missing.add(m.group(1))
    shims = []
    while todo:
        n = todo.pop()
        if n in seen:
            continue
        seen.add(n)
        if n in subst and shim_dir is not None:
            r = subst[n]
            rn = r if isinstance(r, str) else r["module"]
            of, _ = pick(idx, n, prefer)
            rf, _ = pick(idx, rn, prefer)
            if of is None or rf is None:
                raise ElabError(f"substitute {n} -> {rn}: definition missing")
            txt, rec = make_shim(of, n, r, rf)
            sf = Path(shim_dir) / f"shim_{n}.sv"
            sf.write_text(txt)
            full.append(str(sf))
            shims.append(rec)
            todo.append(rn)
            continue
        f, a = pick(idx, n, prefer)
        if f is None:
            missing.add(n)
            continue
        if a:
            amb[n] = idx[n]
        if n in dissolve:
            if f not in full:
                full.append(f)
            body = module_body(f, n)
            ch = instantiated(body, idx)
            todo += sorted(ch)
        else:
            if f not in lib:
                lib.append(f)
    lib = [f for f in lib if f not in full]
    rec = dict(modules=len(seen), full_files=len(full), lib_files=len(lib), ambiguous={k: v for k, v in sorted(amb.items())},
               undefined=sorted(missing), substituted=shims)
    return tops, full, lib, rec


def lib_stubs(lib, out_path):
    """interface-only copies of the leaf (lib) files: each module's header (parameters + port list) and, for a
    non-ANSI header, its parameter / port declarations, then endmodule.  Yosys then never parses leaf bodies (some
    leaf RTL elaborates only under the tool of record, e.g. hierarchical references into generate blocks); the
    leaves stay black boxes either way, and the Verilator lint reads the real files."""
    out = []
    for f in lib:
        t = _strip(Path(f).read_text(errors="replace"))
        out.append(f"// ---- interface of {f}")
        out += [ln for ln in re.findall(r"^[ \t]*`(?:define|undef|include)\b(?:[^\n]*\\\n)*[^\n]*", t, re.M)]
        for m in MOD_RE.finditer(t):
            i = m.end()
            # skip a parameter block #( ... )
            j = i
            while j < len(t) and t[j].isspace():
                j += 1
            if j < len(t) and t[j] == "#":
                k = t.index("(", j)
                j = _match(t, k) + 1
            k = t.find("(", j)
            semi = t.find(";", j)
            if k < 0 or (0 <= semi < k):
                hdr_end = semi
            else:
                hdr_end = t.find(";", _match(t, k))
            hdr = t[m.start():hdr_end + 1]
            body_end = t.find("endmodule", hdr_end)
            body = t[hdr_end + 1:body_end]
            ansi = re.search(r"\b(input|output|inout)\b", hdr) is not None
            decl, lp = [], []
            for st in re.finditer(r"(?:^|(?<=;))\s*((?:parameter|localparam|input|output|inout)\b[^;]*;)", body):
                txt = st.group(1)
                if txt.startswith("localparam"):
                    lp.append(txt)
                elif not ansi or txt.startswith("parameter"):
                    decl.append(txt)
            # localparams / constant functions only when the interface needs them (a body localparam may sit in a
            # generate block and name a genvar)
            fall = {m2.group(1): m2.group(0) for m2 in
                    re.finditer(r"\bfunction\b(?:\s+automatic)?(?:\s+\w+)?(?:\s*\[[^\]]*\])?\s+(\w+).*?\bendfunction\b",
                                body, re.S)}
            need_txt = hdr + " ".join(decl)
            keep_lp, keep_fn = [], []
            changed = True
            while changed:
                changed = False
                for x in lp:
                    nm = re.match(r"localparam\b[^=]*?(\w+)\s*=", x)
                    if x not in keep_lp and nm and re.search(rf"\b{nm.group(1)}\b", need_txt):
                        keep_lp.append(x)
                        need_txt += " " + x
                        changed = True
                for nm, x in fall.items():
                    if x not in keep_fn and re.search(rf"\b{nm}\s*\(", need_txt):
                        keep_fn.append(x)
                        need_txt += " " + x
                        changed = True
            keep_lp.sort(key=lp.index)
            decl = ["    " + x for x in keep_lp + decl]
            fns = keep_fn
            out.append(hdr + "\n" + "\n".join(fns + decl) + "\nendmodule")
    Path(out_path).write_text("\n".join(out) + "\n")
    return str(out_path)


def _match(t, k):
    d = 0
    for i in range(k, len(t)):
        if t[i] == "(":
            d += 1
        elif t[i] == ")":
            d -= 1
            if d == 0:
                return i
    raise ElabError("unbalanced parentheses")


def yosys_script(ab, tops, full, lib, out_json, check=False, inc_files=()):
    dflags = " ".join(f"-D{d}" for d in ab.get("defines", []))
    incs = sorted({str(Path(f).parent) for f in list(tops) + list(full) + list(lib) + list(inc_files)})
    iflags = " ".join(f"-I{d}" for d in incs)
    lines = []
    for f in lib:
        lines.append(f"read_verilog -sv -lib -overwrite {dflags} {iflags} {f}")
    for f in full + tops:
        lines.append(f"read_verilog -sv -overwrite {dflags} {iflags} {f}")
    subst = ab.get("substitute", {})
    pvar = sorted({r["module"] for r in ab.get("substitute_parent", [])})
    top = ab.get("_elab_top", ab["top"])
    keep = sorted({ab["top"], top} | set(ab.get("dissolve", [])) | set(subst) | set(pvar))
    sel = " ".join(f"={m} =A:hdlname={m}" for m in keep)
    lines += [f"hierarchy {'-check ' if check else ''}-top {top}",
              f"select -set keep {sel}",
              "blackbox =* @keep %d",
              "proc",
              f"write_json {out_json}"]
    return "\n".join(x for x in lines if x) + "\n"


def run_yosys(script_path, log_path, mounts, mem_gb=32):
    """Yosys >= 0.40: $OT_BIND_YOSYS, else the ORFS image in docker (memory capped, no swap)."""
    exe = os.environ.get("OT_BIND_YOSYS")
    if exe:
        cmd = [exe, "-q", "-l", str(log_path), "-s", str(script_path)]
    else:
        if not shutil.which("docker"):
            raise ElabError("no yosys: set OT_BIND_YOSYS or install docker with the ORFS image")
        vs = []
        for m in sorted({str(Path(x).resolve()) for x in mounts}):
            vs += ["-v", f"{m}:{m}"]
        cmd = ["docker", "run", "--rm", f"--memory={mem_gb}g", f"--memory-swap={mem_gb}g", "-u",
               f"{os.getuid()}:{os.getgid()}"] + vs + ["-w", str(Path(script_path).parent), YOSYS_IMAGE,
                                                        YOSYS_IN_IMAGE, "-q", "-l", str(log_path), "-s", str(script_path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        tail = (r.stderr or "")[-3000:] + (Path(log_path).read_text()[-3000:] if Path(log_path).exists() else "")
        raise ElabError(f"yosys failed (rc {r.returncode}):\n{tail}")


def elab(ab, base, out_dir, mem_gb=32, idx=None):
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    ab = dict(ab)
    nl = []
    for f in ab["netlist"]:
        fp = Path(f) if Path(f).is_absolute() else Path(base) / f
        if fp.name.endswith(".gz"):
            import gzip
            dst = out / fp.name[:-3]
            dst.write_bytes(gzip.open(fp).read())
            fp = dst
        nl.append(str(fp))
    alias = ab.get("alias", {})
    if alias:
        # GEN die masters that are aliases of an RTL module (same ports, no parameters): renamed in a copy of the die top
        rx = re.compile(r"^(\s*)(" + "|".join(re.escape(a) for a in sorted(alias, key=len, reverse=True)) + r")(?=\s)", re.M)
        for i, f in enumerate(nl):
            t = Path(f).read_text(errors="replace")
            t2 = rx.sub(lambda m: m.group(1) + alias[m.group(2)], t)
            if t2 != t:
                dst = out / ("aliased_" + Path(f).name)
                dst.write_text(t2)
                nl[i] = str(dst)
    ab["netlist"] = nl
    tops, full, lib, rec = plan_sources(ab, base, idx, shim_dir=out)
    rec["aliased"] = alias
    pvar = sorted({r["module"] for r in ab.get("substitute_parent", [])})
    if pvar:
        # keep the per-instance parent variants through `hierarchy -top`: a wrapper top instantiates the die and each
        wt = out / "bind_elab_keep.sv"
        wt.write_text("// GENERATED by bind_elab.py: keeps asbuilt.substitute_parent variants elaborated\n"
                      "module bind_elab_keep ();\n" + f"    {ab['top']} u_die ();\n" +
                      "".join(f"    {m} u_v{i} ();\n" for i, m in enumerate(pvar)) + "endmodule\n")
        tops = tops + [str(wt)]
        ab["_elab_top"] = "bind_elab_keep"
    js = out / "asbuilt.json"
    sc = out / "asbuilt.ys"
    ylib = lib
    if ab.get("lib_stubs", True):
        ylib = [lib_stubs(lib, out / "asbuilt_lib_stubs.sv")] if lib else []
    sc.write_text(yosys_script(ab, tops, full, ylib, js, inc_files=lib))
    mounts = [out, Path(base).resolve(), REPO] + [Path(f).parent for f in tops + full + lib]
    roots = sorted({str(Path(m).resolve()) for m in mounts}, key=len)
    mounts = [m for i, m in enumerate(roots) if not any(m.startswith(r + "/") for r in roots[:i])]
    run_yosys(sc, out / "asbuilt.yosys.log", mounts, mem_gb)
    rec.update(json=str(js), script=str(sc), top=ab["top"])
    (out / "asbuilt_sources.json").write_text(json.dumps(dict(rec, tops=tops, full=full, lib=lib), indent=1))
    return rec


# ------------------------------------------------------------------------------------------------ flatten
def _pval(v):
    """Yosys JSON parameter value -> (verilog literal, python value)."""
    if isinstance(v, int):
        return str(v), v
    if isinstance(v, str) and re.fullmatch(r"[01xz]+", v) and v:
        w = len(v)
        if "x" in v or "z" in v:
            return f"{w}'b{v}", v
        n = int(v, 2)
        if w == 32:
            s = n - (1 << 32) if n >> 31 else n
            return str(s), s
        return f"{w}'b{v}", n
    if isinstance(v, str):
        s = v[:-1] if v.endswith(" ") else v       # Yosys marks a string that looks like bits with a trailing space
        return '"' + s.replace('"', '\\"') + '"', s
    return str(v), v


class Cell:
    __slots__ = ("path", "module", "params", "ports", "dirs", "kind", "ytype", "yparams", "src")

    def __init__(self, path, module, params, ports, dirs, kind, ytype=None, yparams=None, src=None):
        self.path, self.module, self.params, self.ports, self.dirs, self.kind = path, module, params, ports, dirs, kind
        self.ytype, self.yparams, self.src = ytype, yparams, src


class Flat:
    """flattened netlist: cells (leaf | glue | unknown) with global per-bit nets; top ports."""

    def __init__(self):
        self.parent = []
        self.cells = []
        self.top_ports = {}          # name -> (dir, [net])
        self.const_drivers = {}      # net -> (const, where): a constant assigned inside a dissolved module
        self.dissolved = {}          # path -> module

    def new(self, n):
        b = len(self.parent)
        self.parent.extend(range(b, b + n))
        return b

    def find(self, x):
        p = self.parent
        r = x
        while p[r] != r:
            r = p[r]
        while p[x] != r:
            p[x], x = r, p[x]
        return r

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.parent[max(a, b)] = min(a, b)

    def canon(self):
        for c in self.cells:
            for pn, bits in c.ports.items():
                c.ports[pn] = [b if isinstance(b, str) else self.find(b) for b in bits]
        for k, (d, bits) in list(self.top_ports.items()):
            self.top_ports[k] = (d, [b if isinstance(b, str) else self.find(b) for b in bits])
        self.const_drivers = {self.find(k): v for k, v in self.const_drivers.items()}


def flatten(yjs, top, parent_variants=()):
    """parent_variants: [{"inst": regex on the hierarchical path, "module": M}] -- a dissolved parent instance is
    elaborated as variant M (its ports a subset): connections to ports M lacks are dropped (recorded: literal or net),
    ports M adds stay unconnected (recorded)."""
    mods = yjs["modules"]
    F = Flat()
    F.parent_variants = []
    pv = [(re.compile(r["inst"]), r["module"]) for r in parent_variants]
    byname = {}
    for k, m in mods.items():
        byname.setdefault(m.get("attributes", {}).get("hdlname", k), k)
    if top not in mods:
        raise ElabError(f"top {top} not in the Yosys netlist")

    def orig(mname):
        m = mods.get(mname)
        if m is None:
            return mname
        return m.get("attributes", {}).get("hdlname", mname)

    def walk(mname, path, portmap):
        """portmap: {local bit: global net or const} for the module's port bits"""
        m = mods[mname]
        local = {}
        nb = 0
        for nn in m.get("netnames", {}).values():
            for b in nn["bits"]:
                if isinstance(b, int):
                    nb = max(nb, b + 1)
        base = F.new(nb)

        def g(b):
            if isinstance(b, str):
                return b
            if b in portmap:
                return portmap[b]
            return base + b
        for c_name, c in m.get("cells", {}).items():
            # Yosys names glue cells $type$<absolute src path>:<line>$<n>: keep the file name only (stable names)
            c_name = re.sub(r"\$(/[^$:]*/)([^/$:]+:)", r"$\2", c_name)
            cpath = f"{path}.{c_name}" if path else c_name
            ct = c["type"]
            conns = {pn: [g(b) for b in bits] for pn, bits in c["connections"].items()}
            if ct in mods and "blackbox" not in mods[ct].get("attributes", {}):
                vm = next((mm for rx, mm in pv if rx.fullmatch(cpath)), None)
                if vm is not None:
                    vk = byname.get(vm)
                    if vk is None or "blackbox" in mods[vk].get("attributes", {}):
                        raise ElabError(f"substitute_parent {cpath} -> {vm}: variant not elaborated")
                    vp = mods[vk].get("ports", {})
                    rec = dict(inst=cpath, master=orig(ct), variant=vm, dropped_literal_bits=0, dropped_net_ports=[],
                               new_unconnected_ports=sorted(p for p in vp if p not in conns))
                    for pn in [p for p in conns if p not in vp]:
                        bits = conns.pop(pn)
                        if all(isinstance(b, str) for b in bits):
                            rec["dropped_literal_bits"] += len(bits)
                        else:
                            rec["dropped_net_ports"].append(pn)
                    F.parent_variants.append(rec)
                    ct = vk
                sub = mods[ct]
                pm = {}
                for pn, p in sub.get("ports", {}).items():
                    pb = p["bits"]
                    cb = conns.get(pn, ["z"] * len(pb))
                    for i, b in enumerate(pb):
                        x = cb[i] if i < len(cb) else "z"
                        if isinstance(b, str):
                            # a constant on the child side of a port: the parent net is driven by a constant
                            if not isinstance(x, str):
                                F.const_drivers[x] = (b, f"{cpath}.{pn}[{i}]")
                            continue
                        if b in pm:
                            y = pm[b]
                            if x == "z" and not isinstance(y, str):
                                # an output the parent leaves open ('z') that the child aliases to another port's net
                                # (e.g. assign ck_rt = {8{clk}}): open, not a constant driver of that net (BINDER4)
                                continue
                            if isinstance(x, str) or isinstance(y, str):
                                if not isinstance(x, str):
                                    F.const_drivers[x] = (y, f"{cpath}.{pn}[{i}]")
                                elif not isinstance(y, str):
                                    F.const_drivers[y] = (x, f"{cpath}.{pn}[{i}]")
                            else:
                                F.union(x, y)
                        else:
                            pm[b] = x
                F.dissolved[cpath] = orig(ct)
                walk(ct, cpath, pm)
                continue
            if ct.startswith("$") and ct not in mods:
                F.cells.append(Cell(cpath, ct, {}, conns, dict(c.get("port_directions", {})), "glue", ct,
                                    dict(c.get("parameters", {})), c.get("attributes", {}).get("src")))
                continue
            if ct in mods:
                sub = mods[ct]
                params = {k: _pval(v)[0] for k, v in sub.get("parameter_default_values", {}).items()} \
                    if ct.startswith("$paramod") else {k: _pval(v)[0] for k, v in c.get("parameters", {}).items()}
                F.cells.append(Cell(cpath, orig(ct), params, conns, dict(c.get("port_directions", {})), "leaf", ct))
            else:
                params = {k: _pval(v)[0] for k, v in c.get("parameters", {}).items()}
                F.cells.append(Cell(cpath, ct, params, conns, {}, "unknown", ct))
        # constant drivers assigned to internal nets of this module: netnames whose bits are constants are folded by
        # Yosys into the connections (cells then see '0'/'1' directly), so nothing else to record here.
        return base

    m = mods[top]
    pm = {}
    for pn, p in m.get("ports", {}).items():
        bits = []
        for b in p["bits"]:
            if isinstance(b, str):
                bits.append(b)
                continue
            if b not in pm:
                pm[b] = F.new(1)
            bits.append(pm[b])
        F.top_ports[pn] = (p["direction"], bits)
    walk(top, "", pm)
    F.canon()
    return F
