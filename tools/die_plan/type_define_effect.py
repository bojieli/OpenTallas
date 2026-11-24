#!/usr/bin/env python3
"""type_define_effect: does each per-type `verilog_defines` entry of a plan take effect (TYPE-DEFINES-1123)?

A plan type may request Verilog macros (partition_types.<t>.verilog_defines).  The kit (synth, RTL lint, LEC gold)
reads them through gen_phys.type_verilog_defines.  The bind elab (bind_elab.yosys_script) reads only the die-wide
asbuilt `defines`, so a macro that a DISSOLVED / top body file reads (a parent that sets a leaf parameter, a
generate arm of a flat parent) is elaborated define-OFF and the bound partition RTL bakes that value in (S81 J7
t14: ot_s81sl_vpw #(.SPR(0), .XRB(0)) under a requested OT_S81SL_VP_SPR / _XRB).  This module classifies every
(type, define) pair from the elab source record (OUT/asbuilt_sources.json: tops / full / lib):

  DIE_WIDE      the macro is also in asbuilt.defines: the bind elab and the kit both see it
  KIT           read only by leaf (interface-only in the bind) files: the kit honours it, the bind is blind
                by design; PORTS when the macro guards a leaf port declaration (the bind stub cannot follow)
  BIND_IGNORED  read by a die top / dissolved body file: the bind elaborated it OFF -> the request had no effect
                unless bind_elab's per-type pass (variant elab + inertness proof) realized it
  NOT_SELECTED  only files the closure does not take read it (every module they define comes from another,
                preferred file, e.g. a portfix copy without the hunk): no effect anywhere
  DEAD          no file in the elab closure or under the RTL roots reads it: the request selects nothing

    python3 tools/die_plan/type_define_effect.py census --plan P.json --asbuilt AB.json --elab-out DIR [--json OUT]
"""
import argparse
import hashlib
from collections import Counter
import json
import os
import re
import sys
from pathlib import Path

USE_RE = re.compile(r"`(?:ifdef|ifndef|elsif|undef)\s+([A-Za-z_]\w*)|`([A-Za-z_]\w*)")
DIRECTIVES = {"ifdef", "ifndef", "elsif", "else", "endif", "undef", "define", "include", "timescale", "default_nettype",
              "resetall", "celldefine", "endcelldefine", "line", "pragma", "begin_keywords", "end_keywords",
              "unconnected_drive", "nounconnected_drive", "undefineall", "__FILE__", "__LINE__"}
SRC_SUFFIX = (".sv", ".v", ".svh", ".vh")


def strip(text):
    text = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def bare(d):
    """'-DNAME=1' / 'NAME=1' / 'NAME' -> 'NAME'"""
    return str(d).removeprefix("-D").split("=", 1)[0].strip()


def readers_of(text):
    """{macro read by this source text} (`ifdef/`ifndef/`elsif/`undef NAME and `NAME uses; `define NAME is not a read)"""
    t = strip(text)
    out = set()
    for a, b in USE_RE.findall(t):
        n = a or b
        if n and n not in DIRECTIVES:
            out.add(n)
    return out


def port_guards(text, names):
    """{macro of `names` whose `ifdef/`ifndef/`elsif arm inside a module header (between `module` and the first
    ');') declares a port (input / output / inout): such a macro may change the leaf's port list."""
    t = strip(text)
    hit = set()
    for m in re.finditer(r"\bmodule\s+[A-Za-z_]\w*", t):
        end = t.find(");", m.end())
        hdr = t[m.end(): end if end >= 0 else len(t)]
        for n in names:
            for g in re.finditer(r"`(?:ifdef|ifndef|elsif)\s+" + re.escape(n) + r"\b", hdr):
                stop = re.search(r"`(?:endif|else|elsif)\b", hdr[g.end():])
                arm = hdr[g.end(): g.end() + stop.start() if stop else len(hdr)]
                if re.search(r"\b(?:input|output|inout)\b", arm):
                    hit.add(n)
    return hit


def module_readers(text):
    """{module: {macro read inside that module's body}} (text outside any module, e.g. a file-level `ifdef around
    whole modules, is attributed to every module of the file)."""
    t = strip(text)
    spans = [(m.start(), m.group(1)) for m in re.finditer(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)", t)]
    out = {name: set() for _, name in spans}
    if not spans:
        return out
    ends = [m.end() for m in re.finditer(r"\bendmodule\b", t)]
    outside = []
    pos = 0
    for i, (st, name) in enumerate(spans):
        en = next((e for e in ends if e > st), len(t))
        outside.append(t[pos:st])
        out[name] |= readers_of(t[st:en])
        pos = en
    outside.append(t[pos:])
    glob = readers_of("".join(outside))
    for name in out:
        out[name] |= glob
    return out


MODDEF_RE = re.compile(r"^\s*(?:\(\*[^\n]*?\*\)\s*)?module\s+([A-Za-z_][A-Za-z0-9_$]*)", re.M)


class SourceScan:
    """macro -> files reading it, over a file set (cached per path)."""

    def __init__(self):
        self._cache = {}

    def reads(self, path):
        p = str(path)
        if p not in self._cache:
            try:
                txt = Path(p).read_text(errors="replace")
            except OSError:
                txt = ""
            self._cache[p] = (readers_of(txt), txt, set(MODDEF_RE.findall(strip(txt))), module_readers(txt))
        return self._cache[p]


def tree_sources(roots):
    out = []
    for r in roots:
        r = Path(r)
        if r.is_file():
            out.append(str(r))
            continue
        if not r.is_dir():
            continue
        for d, sub, names in os.walk(r):
            sub[:] = [s for s in sub if s not in ("build", "obj_dir", ".git", "__pycache__")]
            out += [str(Path(d) / n) for n in names if n.endswith(SRC_SUFFIX)]
    return out


def classify(plan, ab, sources, wide_roots=(), scan=None, types=None, prefer=()):
    """-> list of rows {type, define, verdict, die_wide, body_readers, leaf_readers, other_readers, ports}.
    sources = {"tops": [...], "full": [...], "lib": [...]} (bind_elab asbuilt_sources.json)."""
    scan = scan or SourceScan()
    die = {bare(d) for d in ab.get("defines", [])}
    body = list(dict.fromkeys(list(sources.get("tops", [])) + list(sources.get("full", []))))
    lib = list(dict.fromkeys(sources.get("lib", [])))
    in_elab = set(body) | set(lib)
    keep = ({ab.get("top"), ab.get("_elab_top")} | set(ab.get("dissolve", [])) | set(ab.get("substitute", {}))
            | {r["module"] for r in ab.get("substitute_parent", [])}) - {None}
    selected = {}                       # module -> the file the elab / kit closure takes it from (prefer first)
    for f in list(prefer) + body + lib:
        for m in scan.reads(f)[2]:
            selected.setdefault(m, f)
    wide = None
    rows = []
    for tn, t in sorted((plan.get("partition_types") or {}).items()):
        if types and tn not in types:
            continue
        for d in t.get("verilog_defines") or []:
            d = bare(d)
            # a body file may co-host leaf modules: only a read inside a KEPT module (top / dissolve / substitute) is
            # elaborated by the bind; a read inside a co-hosted leaf is the kit's
            br = [f for f in body if any(d in rd for m, rd in scan.reads(f)[3].items() if m in keep)]
            lr = [f for f in lib if d in scan.reads(f)[0]] + \
                [f for f in body if f not in br and d in scan.reads(f)[0]]
            other = []
            if not br and not lr:
                if wide is None:
                    wide = [f for f in tree_sources(wide_roots) if f not in in_elab]
                other = [f for f in wide if d in scan.reads(f)[0]]
            # a reader file whose every module the closure takes from ANOTHER file (a prefer / portfix copy) is never read
            shadowed = [f for f in other if scan.reads(f)[2] and
                        all(selected.get(m, f) != f for m in scan.reads(f)[2])]
            live_other = [f for f in other if f not in shadowed]
            ports = any(d in port_guards(scan.reads(f)[1], [d]) for f in lr)   # bind leaf stubs only
            if d in die:
                v = "DIE_WIDE"
            elif br:
                v = "BIND_IGNORED"
            elif lr or live_other:
                v = "KIT"
            elif shadowed:
                v = "NOT_SELECTED"
            else:
                v = "DEAD"
            rows.append(dict(type=tn, define=d, verdict=v, die_wide=d in die, ports=ports,
                             body_readers=br, leaf_readers=lr, other_readers=live_other[:20],
                             shadowed_readers=[dict(file=f, selected={m: selected[m] for m in sorted(scan.reads(f)[2])})
                                               for f in shadowed[:10]]))
    return rows


def summary(rows):
    s = {}
    for r in rows:
        s[r["verdict"]] = s.get(r["verdict"], 0) + 1
    return s


def failures(rows, realized=()):
    """rows whose request did not take effect: BIND_IGNORED (unless realized by the per-type elab pass), NOT_SELECTED
    and DEAD.  KIT rows with `ports` (the macro guards a bind leaf's port list) are advisory: the bind stub carries
    the define-off ports, so the strict bind's port checks see any width change."""
    real = set(realized)
    bad = []
    for r in rows:
        if r["verdict"] in ("DEAD", "NOT_SELECTED"):
            bad.append(r)
        elif r["verdict"] == "BIND_IGNORED" and (r["type"], r["define"]) not in real:
            bad.append(r)
    return bad


def describe(r):
    if r["verdict"] == "DEAD":
        return f"{r['type']}: {r['define']} DEAD (no RTL in the elab closure or the RTL roots reads it)"
    if r["verdict"] == "NOT_SELECTED":
        sh = r["shadowed_readers"][0]
        return (f"{r['type']}: {r['define']} NOT_SELECTED (only {Path(sh['file']).name} reads it, but the closure takes "
                f"{sorted(sh['selected'].items())[:2]} from another file)")
    if r["verdict"] == "BIND_IGNORED":
        return (f"{r['type']}: {r['define']} BIND_IGNORED (read by bind body file(s) "
                f"{[Path(f).name for f in r['body_readers']][:4]}; elaborated define-off)")
    return f"{r['type']}: {r['define']} KIT+PORTS (guards a leaf port list in {[Path(f).name for f in r['leaf_readers'] + r['other_readers']][:4]})"


def load_sources(elab_out):
    p = Path(elab_out) / "asbuilt_sources.json"
    return json.loads(p.read_text())


# ------------------------------------------------------------------------------------------------ bind: realize + assert
RECEIPT = "type_defines.json"
VARIANT_DIR = "type_define_variant"


def mode():
    """OT_BIND_TYPE_DEFINES: warn (default: report) | on (try realization and enforce) | off."""
    value = os.environ.get("OT_BIND_TYPE_DEFINES", "warn").strip().lower()
    return value if value in ("on", "warn", "off") else "warn"


def signatures(flat):
    """Compare connectivity using named terminals for every wire, including glue-only wires."""
    def cell_name(cell):
        # Yosys numbers the last component globally. Keep its source location
        # and distinguish peers at that location in their emitted order.
        return re.sub(r"\$[0-9]+$", "", cell.path) if cell.kind == "glue" else cell.path

    seen = Counter()
    cell_keys = []
    net_keys = {}

    def register(bits, path, pin):
        for i, bit in enumerate(bits):
            if not isinstance(bit, str):
                terminal = (path, pin, i)
                if bit not in net_keys or terminal < net_keys[bit]:
                    net_keys[bit] = terminal

    for name, (_, bits) in flat.top_ports.items():
        register(bits, ("", -1), name)
    for cell in flat.cells:
        path = cell_name(cell)
        key = (path, seen[path])
        seen[path] += 1
        cell_keys.append(key)
        for name, bits in cell.ports.items():
            register(bits, key, name)

    def nets(bits):
        return tuple(bit if isinstance(bit, str) else (
            net_keys[bit], flat.const_drivers.get(bit, (None,))[0]
        ) for bit in bits)

    out = {("@top", 0): (None, tuple(sorted((name, direction, nets(bits))
                        for name, (direction, bits) in flat.top_ports.items())))}
    for cell, key in zip(flat.cells, cell_keys):
        params = cell.yparams if cell.kind == "glue" else cell.params
        attrs = (cell.kind, cell.module, cell.keep,
                 tuple(sorted((name, str(value)) for name, value in (params or {}).items())))
        ports = tuple(sorted((name, nets(bits)) for name, bits in cell.ports.items()))
        path = cell.path.rsplit(".", 1)[0] if cell.kind == "glue" and "." in cell.path else (
            "" if cell.kind == "glue" else cell.path)
        out[key] = (path, attrs, ports)
    return out


def changed_paths(before, after):
    return {rec[0] for key in before.keys() | after.keys()
            if before.get(key) != after.get(key)
            for rec in (before.get(key), after.get(key)) if rec is not None}


def has_defines(plan):
    return any(t.get("verilog_defines") for t in (plan.get("partition_types") or {}).values())


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 22), b""):
            h.update(blk)
    return h.hexdigest()


def _types_of(plan, part_of, paths):
    p2t = {p["name"]: p["type"] for p in plan.get("partitions", []) if isinstance(p, dict) and "name" in p}
    out = {}
    for x in paths:
        part = part_of(x) if x else None
        out[x or "<die>"] = p2t.get(part, f"<unmapped:{part}>" if part else "<die>")
    return out


def request_scope(plan):
    types = (plan.get("partition_types") or {})
    scope = {
        "types": {name: target["verilog_defines"] for name, target in types.items() if target.get("verilog_defines")},
        "partitions": [(target.get("name"), target.get("type")) for target in plan.get("partitions") or ()],
    }
    return hashlib.sha256(json.dumps(scope, sort_keys=True).encode()).hexdigest()


def _requested(rows):
    requested = {}
    for r in rows:
        if r["verdict"] == "BIND_IGNORED":
            requested.setdefault(r["define"], set()).add(r["type"])
    return requested


def variant_specs(requested, variant):
    """[(defines, directory)] of every define-variant elab elab_pass runs, in its serial order: the combined variant,
    then one without_<define> per define (only when there is more than one)."""
    added = sorted(requested)
    specs = [(added, Path(variant))]
    for define in requested:
        other = [d for d in added if d != define]
        if other:
            specs.append((other, Path(variant) / ("without_" + define)))
    return specs


def unit_mem_gb(proc_cgroup="/proc/self/cgroup", root="/sys/fs/cgroup"):
    """the smallest memory.max (GB) on this process's cgroup path (the ot-run unit's cap), None when uncapped."""
    try:
        rel = next(ln.split(":", 2)[2].strip() for ln in Path(proc_cgroup).read_text().splitlines()
                   if ln.startswith("0::"))
    except (OSError, StopIteration, IndexError):
        return None
    caps, d = [], Path(root + rel)
    while d != Path(root) and d != d.parent:
        try:
            v = (d / "memory.max").read_text().strip()
            if v != "max":
                caps.append(int(v) / (1 << 30))
        except (OSError, ValueError):
            pass
        d = d.parent
    return min(caps) if caps else None


def elab_jobs(n, mem_gb):
    """BIND-ELAB-PAR: how many define-variant elabs run in the pool BESIDE the base elab (0 = the serial pass).
    $OT_BIND_ELAB_JOBS = N Yosys elabs at once, the base included (1 = serial); else min(n, max(4, idle cores),
    (min(MemAvailable, the unit's cgroup cap) - 64 GB) / per-job GB - 1).  The Yosys containers run outside the ot-run
    unit's cgroup, so the unit's own cap is applied here; the 64 GB is the bind process itself (S81 c7a: 52 GB peak), the
    -1 the base elab's own Yosys.  Each variant is one Yosys thread and the fleet admits on memory, never on load
    (OWNER 10-18), so a busy host still gets 4.  Per-job GB = $OT_BIND_ELAB_JOB_GB, else min(--mem, 14) (S81 c7a Yosys
    peak 11.4 GB).  One variant still runs beside the base (S81 c8: only ATTCUT left, 1 variant, was serial)."""
    env = os.environ.get("OT_BIND_ELAB_JOBS", "").strip()
    if env:
        try:
            return max(0, min(n, int(env) - 1))
        except ValueError:
            pass
    try:
        idle = int((os.cpu_count() or 1) - os.getloadavg()[0])
    except OSError:
        idle = 0
    avail = None
    try:
        for ln in Path("/proc/meminfo").read_text().splitlines():
            if ln.startswith("MemAvailable:"):
                avail = int(ln.split()[1]) / (1 << 20)
    except OSError:
        pass
    if avail is None:
        return 0
    cap = unit_mem_gb()
    per = min(float(mem_gb), 14.0)
    try:
        per = float(os.environ.get("OT_BIND_ELAB_JOB_GB") or per)
    except ValueError:
        pass
    return max(0, min(n, max(4, idle), int((min(avail, cap if cap is not None else avail) - 64) // max(per, 1.0)) - 1))


class Prestart:
    """BIND-ELAB-PAR 11-23: run elab_pass's define-variant elabs in a bounded process pool, started from the base
    elab's source lists (bind_elab.elab on_sources) so they run alongside the base Yosys run.  Each variant is the very
    elab_fn call elab_pass would make serially (same defines, same directory), so every emitted file is the same;
    elab_pass only waits for it instead of calling it.  Anything unexpected -> no prestart (serial, as before)."""

    def __init__(self, plan, ab, base, out, mem, elab_fn, roots=None):
        self.plan, self.ab, self.base, self.out, self.mem, self.elab_fn = plan, ab, base, Path(out), mem, elab_fn
        self.roots = roots
        self.futures = {}
        self.pool = None
        self.jobs = 0
        self.note = None

    def on_sources(self, tops, full, lib):
        try:
            pref = [str(Path(self.base) / f) if not Path(f).is_absolute() else f for f in self.ab.get("prefer", [])]
            rows = classify(self.plan, self.ab, dict(tops=tops, full=full, lib=lib),
                            self.roots or [str(Path(self.base) / "rtl")], prefer=pref)
            specs = variant_specs(_requested(rows), self.out / VARIANT_DIR)
            if not _requested(rows):
                return
            self.jobs = elab_jobs(len(specs), self.mem)
            if self.jobs < 1:
                self.note = "serial (OT_BIND_ELAB_JOBS=1 or no memory for a second Yosys)"
                print(f"   TYPE-DEFINES: {len(specs)} define-variant elab(s) run after the base elab: {self.note}",
                      flush=True)
                return
            # processes, not threads: each variant spends minutes in Python (module index, staging) before Yosys runs;
            # forked here, before the base elab loads anything big
            import multiprocessing as mp
            from concurrent.futures import ProcessPoolExecutor
            self.pool = ProcessPoolExecutor(self.jobs, mp_context=mp.get_context("fork"))
            for defines, directory in specs:
                extended = dict(self.ab, defines=list(self.ab.get("defines", [])) + list(defines))
                self.futures[str(directory)] = (list(defines), self.pool.submit(
                    self.elab_fn, extended, self.base, directory, self.mem))
            print(f"   TYPE-DEFINES: {len(specs)} define-variant elab(s) started alongside the base elab "
                  f"({self.jobs} parallel; OT_BIND_ELAB_JOBS)", flush=True)
        except Exception as exc:          # fall back to the serial pass
            self.note = f"prestart off: {type(exc).__name__}: {exc}"[:300]
            print(f"   TYPE-DEFINES: {self.note} (serial pass)", flush=True)
            self.close()

    def take(self, defines, directory):
        """True when the prestarted elab for exactly (defines, directory) is done (re-raises its error).  A prestarted
        elab for another define set in that directory is waited out first, so the serial run does not race it."""
        ent = self.futures.pop(str(directory), None)
        if ent is None:
            return False
        if ent[0] != list(defines):
            try:
                ent[1].result()
            except Exception:
                pass
            return False
        ent[1].result()
        return True

    def close(self):
        if self.pool is not None:
            for _, f in self.futures.values():
                f.cancel()
            self.pool.shutdown(wait=True)
            self.pool = None
        self.futures = {}


def elab_pass(plan, ab, base, out, mem, part_of, elab_fn, load_fn, flatten_fn, roots=None, prestart=None):
    """Report per-type requested defines and optionally adopt a checked define-on variant.
    prestart: a Prestart whose pool already runs (or ran) the variant elabs (BIND-ELAB-PAR)."""
    try:
        return _elab_pass(plan, ab, base, out, mem, part_of, elab_fn, load_fn, flatten_fn, roots, prestart)
    finally:
        if prestart is not None:
            prestart.close()


def _elab_pass(plan, ab, base, out, mem, part_of, elab_fn, load_fn, flatten_fn, roots, prestart):
    import shutil

    out = Path(out)
    current_mode = mode()
    rows = []
    if current_mode != "off" and has_defines(plan):
        srcs = load_sources(out)
        pref = [str(Path(base) / f) if not Path(f).is_absolute() else f for f in ab.get("prefer", [])]
        rows = classify(plan, ab, srcs, roots or [str(Path(base) / "rtl")], prefer=pref)
    ignored = [r for r in rows if r["verdict"] == "BIND_IGNORED"]
    rec = dict(schema="opentallas.type_define_effect.receipt.v1", mode=current_mode, summary=summary(rows), rows=rows,
               added=[], realized=[], verdict="NONE_NEEDED" if not ignored else "BIND_IGNORED")
    if ignored and current_mode == "on":
        requested = _requested(ignored)
        added = sorted(requested)
        variant = out / VARIANT_DIR
        top, parents = ab["top"], ab.get("substitute_parent", [])

        def elaborate(defines, directory):
            if prestart is None or not prestart.take(defines, directory):
                extended = dict(ab, defines=list(ab.get("defines", [])) + defines)
                elab_fn(extended, base, directory, mem)
            return signatures(flatten_fn(load_fn(directory), top, parents))

        try:
            original = signatures(flatten_fn(load_fn(out), top, parents))
            combined = elaborate(added, variant)
            all_changed = _types_of(plan, part_of, changed_paths(original, combined))
            outside = {}
            no_change = []
            realized = []
            for define, allowed in requested.items():
                other = [d for d in added if d != define]
                disabled = elaborate(other, variant / ("without_" + define)) if other else original
                affected = _types_of(plan, part_of, changed_paths(disabled, combined))
                for path, name in affected.items():
                    if name not in allowed:
                        outside.setdefault(name, []).append(path)
                for name in sorted(allowed):
                    if name in affected.values():
                        realized.append([name, define])
                    else:
                        no_change.append([name, define])
            # Also test the net change versus the untouched baseline.
            allowed_all = set().union(*requested.values())
            for path, name in all_changed.items():
                if name not in allowed_all:
                    outside.setdefault(name, []).append(path)
            rec.update(added=added, variant=str(variant), changed_cells=len(all_changed),
                       # sorted: set order follows the per-process string hash, so unsorted receipts of one
                       # elab differed run to run (BIND-ELAB-PAR c7a proof: same content, other key order)
                       changed_by_type=dict(sorted(Counter(all_changed.values()).items())),
                       outside={t: sorted(set(paths))[:5] for t, paths in sorted(outside.items())},
                       no_change=no_change)
            if outside or no_change:
                rec["verdict"] = "CONFLICT" if outside else "NO_EFFECT"
            else:
                off = out / "asbuilt.define_off.json"
                candidate = out / "asbuilt.define_on.tmp.json"
                shutil.copyfile(out / "asbuilt.json", off)
                shutil.copyfile(variant / "asbuilt.json", candidate)
                digest = _sha(candidate)
                os.replace(candidate, out / "asbuilt.json")
                rec.update(verdict="REALIZED", define_off_json=str(off), asbuilt_sha256=digest,
                           request_scope=request_scope(plan), realized=sorted(realized))
        except Exception as exc:                     # the receipt carries it for strict bind
            rec.update(verdict="ERROR", error=f"{type(exc).__name__}: {exc}"[:2000])
    (out / RECEIPT).write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def bind_check(plan, ab, out, base, roots=None):
    """bind-time assertion: every requested per-type define took effect.  -> (errors, warnings) as strings.
    A realized pair counts only when the receipt's adopted asbuilt.json is the one in OUT now."""
    out = Path(out)
    if mode() == "off" or not has_defines(plan) or not (out / "asbuilt_sources.json").is_file():
        return [], []
    rp = out / RECEIPT
    rec = json.loads(rp.read_text()) if rp.is_file() else {}
    realized = set()
    notes = []
    if rec.get("verdict") == "REALIZED":
        if ((out / "asbuilt.json").is_file() and rec.get("asbuilt_sha256") == _sha(out / "asbuilt.json")
                and rec.get("request_scope") == request_scope(plan)):
            realized = {tuple(x) for x in rec.get("realized", [])}
        else:
            notes.append("TYPE_DEFINE_RECEIPT_STALE: plan define scope or bound elaboration changed")
    pref = [str(Path(base) / f) if not Path(f).is_absolute() else f for f in ab.get("prefer", [])]
    rows = classify(plan, ab, load_sources(out), roots or [str(Path(base) / "rtl")], prefer=pref)
    msgs = [f"TYPE_DEFINE_NOEFFECT {describe(r)}" for r in failures(rows, realized)]
    if rec.get("verdict") == "CONFLICT":
        msgs.append(f"TYPE_DEFINE_CONFLICT added {rec.get('added')} changes types outside at least one requesting scope: "
                    f"{json.dumps(rec.get('outside'))[:600]} (make the RTL read the define only inside the requesting "
                    f"types, or request it on those types too)")
    if rec.get("verdict") == "ERROR":
        msgs.append(f"TYPE_DEFINE_ERROR variant elab: {rec.get('error')}")
    for name, define in rec.get("no_change", []) or []:
        msgs.append(f"TYPE_DEFINE_NOEFFECT {name}: enabling {define} changed no cell of this type")
    msgs = notes + msgs
    return (msgs, []) if mode() == "on" else ([], msgs)



def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("census")
    c.add_argument("--plan", required=True)
    c.add_argument("--asbuilt", help="asbuilt manifest (default: the plan's asbuilt section)")
    c.add_argument("--elab-out", required=True, help="bind elab OUT dir (asbuilt_sources.json)")
    c.add_argument("--roots", nargs="*", default=None, help="extra RTL roots for KIT/DEAD (default: <base>/rtl)")
    c.add_argument("--types", nargs="*")
    c.add_argument("--json")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text())
    ab = json.loads(Path(a.asbuilt).read_text()) if a.asbuilt else plan.get("asbuilt", {})
    src = load_sources(a.elab_out)
    b = ab.get("base")
    mp = Path(a.asbuilt or a.plan).parent
    base = (mp / b).resolve() if b and not Path(b).is_absolute() else Path(b or ".")
    roots = a.roots if a.roots is not None else [str(base / "rtl")]
    pref = [str(base / f) if not Path(f).is_absolute() else f for f in ab.get("prefer", [])]
    rows = classify(plan, ab, src, roots, types=set(a.types) if a.types else None, prefer=pref)
    bad = failures(rows)
    doc = dict(schema="opentallas.type_define_effect.v1", plan=str(Path(a.plan).resolve()), summary=summary(rows),
               not_effective=len(bad), rows=rows)
    if a.json:
        Path(a.json).write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps(doc["summary"]), f"not_effective={len(bad)}")
    for r in rows:
        print(f"{r['verdict']:13s} {r['type']} {r['define']}" + (" PORTS" if r["ports"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
