"""bind_verify: independent proof that the bound die keeps the as-built connectivity (tools/die_plan/bind.py verify).

The generated RTL (DIR/bind.f: leaf interface files + bind_cells.sv + the partition modules + the bound top) is
elaborated again by Yosys, the partition modules dissolved, and every leaf input bit traced to its logical source with
the inserted cells as transport (ot_dp_st boundary flops / stations, ot_dp_dly kept stages), ot_dp_or as a reducer and
ot_reset_sync as the partition reset (the bind's own synchroniser; an as-built leaf ot_reset_sync the bind kept -- a
bind_names.json path -- stays a leaf, its outputs are compared as pins: DIE-S81-30 10-29).  Each as-built leaf input bit (DIR/bind_sinks.json) must see:
  * the same driver pin (as-built path.port[bit]) -- intra-partition with the same stage count, crossing with 2;
    with asbuilt kit_source_station_pricing on, a crossing's bound count is credited with the source-kit stations
    the bind priced but left to the source kit (KitSourceCredit; LATCHECK-1's station source);
  * a fault-OR with the same set of source pins;
  * the partition clock of the same domain / the partition's synchronised reset.
Sinks or sources inside a dissolved parent's glue are counted (not matched by name: Yosys renames glue cells).
Writes DIR/verify_report.json; exit 0 only with 0 mismatches, 0 unbound, 0 tied, 0 undriven, 0 multiply-driven.
Verilator lint of the bound top runs when a Verilator is found ($OT_BIND_VERILATOR or the opentallas 5.050 install).
"""
import json
import re
import os
import shutil
import subprocess
from pathlib import Path

import bind_elab as E
from bind import Binder, Graph, Rules, _tmap, load_plan, sv_id  # noqa: F401

VERIFY_RULES = {
    "transport": [
        {"module": "ot_dp_st", "map": {"q": "d", "eq": "ea"}, "drop_in": ["clk", "rst_n"], "stages": 1},
        {"module": "ot_dp_dly", "map": {"q": "d"}, "drop_in": ["clk"], "stages": 1, "stages_param": "D"},
        {"module": "ot_dp_dly_cnt", "map": {"q": "d"}, "drop_in": ["clk", "strap_cnt"],
         "stages": 0, "stages_port": "strap_cnt"},
        {"module": "ot_dp_rsync", "map": {"q": "a"}, "drop_in": ["clk"], "stages": 2, "stages_param": "S"},
        {"module": "ot_dp_rrelay", "map": {"q": "d"}, "drop_in": ["clk"], "stages": 1},
        # CLK form #7 lockup relay: posedge state + negedge re-launch = still ONE cycle
        {"module": "ot_dp_rrelay_nl", "map": {"q": "d"}, "drop_in": ["clk"], "stages": 1},
        # TYPE-SAFE-1 11-06 ft hop lockup latch (bind.ft_hop_lockup): transparent-low after a station flop = 0 cycles
        {"module": "ot_dp_lk", "map": {"q": "d"}, "drop_in": ["clk"], "stages": 0},
        # decision 13c consumer-tap relay: reset traced through d; the START (run) leg is checked by the lockstep tests
        {"module": "ot_dp_rgate", "map": {"q": "d"}, "drop_in": ["clk", "run"], "stages": 1},
    ],
    "reducers": [{"module": "ot_dp_or", "out": "y"}, {"module": "ot_dp_and", "out": "y", "op": "and"}],
    "sources": [{"module": "ot_reset_sync|ot_dp_rsync_s[23]", "kind": "reset", "outputs": {"sync_rst_n": "low"},
                 "drop_in": ["clk", "async_rst_n"]}],
}


def verilator():
    for c in (os.environ.get("OT_BIND_VERILATOR"), str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"),
              shutil.which("verilator")):
        if c and Path(c).exists():
            return c
    return None


def lint(out, top, files, defines=(), waive=(), incs=()):
    v = verilator()
    if not v:
        return dict(ran=False, reason="no verilator")
    cmd = [v, "--lint-only", "-Wno-fatal", "-Wno-DECLFILENAME", "-Wno-UNUSEDSIGNAL", "-Wno-PINCONNECTEMPTY",
           "--top-module", top] + [f"+define+{d}" for d in defines] + \
        sorted({f"-I{Path(f).parent}" for f in list(files) + list(incs)}) + [str(f) for f in files]
    (Path(out) / "verilator_lint.f").write_text("\n".join(cmd[1:]) + "\n")
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=out)
    errs = [ln for ln in r.stderr.splitlines() if ln.startswith("%Error") and not ln.startswith("%Error: Exiting")]
    waived = [ln for ln in errs if any(re.search(w["rx"], ln) for w in waive)]
    errs = [ln for ln in errs if ln not in waived]
    warns = [ln for ln in r.stderr.splitlines() if ln.startswith("%Warning")]
    (Path(out) / "verilator_lint.log").write_text(r.stderr)
    return dict(ran=True, rc=r.returncode, errors=len(errs), warnings=len(warns), first_errors=errs[:20],
                waived=waived, waivers=list(waive))


DEFINE_RE = re.compile(r"^[ \t]*`define\s+\w+(?:\([^)\n]*\))?((?:[^\n]*\\\n)*[^\n]*)", re.M)
MACRO_DEF = re.compile(r"^[ \t]*`define\s+([A-Za-z_]\w*)", re.M)
MACRO_USE = re.compile(r"`([A-Za-z_]\w*)")
DIRECTIVES = {"define", "undef", "undefineall", "ifdef", "ifndef", "elsif", "else", "endif", "include", "timescale",
              "default_nettype", "resetall", "celldefine", "endcelldefine", "line", "pragma", "begin_keywords",
              "end_keywords", "unconnected_drive", "nounconnected_drive", "__FILE__", "__LINE__", "protect",
              "endprotect", "verilator_config", "systemc_header", "systemc_interface", "systemc_imp_header",
              "systemc_implementation", "systemc_ctor", "systemc_dtor"}
BIND_CELLS = {"ot_dp_st", "ot_dp_dly", "ot_dp_or", "ot_dp_and", "ot_dp_rsync", "ot_reset_sync", "ot_dp_rrelay", "ot_dp_rrelay_nl", "ot_dp_rgate",
              "ot_dp_rsync_s2", "ot_dp_rsync_s3", "ot_dp_lockq"}


def declared_missing(ab0, base):
    """DIE-S81-32/BIND 10-29 (S81 verify256 lint FAIL: 1,769 MODMISSING in 156 of 363 split runs): the as-built
    manifest DECLARES the exact source of every macro view / out-of-tree leaf (netlist, files, prefer: e.g.
    physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v, the p192 r2c2 SRAM views,
    physical/rom_host_ingest/rtl/dsfd_host.sv).  E.module_index skips an unreadable declared file silently, so a
    verify run from a checkout without them (a sparse worktree: tools/ rtl/ physical/die_plan/<die>/ only) lost
    the declared view and the closure fell through to rtl/ (ambiguous p192/p192bs wrappers -> missing) or to
    nothing.  -> the declared paths that do not exist under base; a non-empty list stops the verify (no silent
    fallback to a different definition)."""
    out = []
    for k in ("netlist", "files", "prefer"):
        for f in ab0.get(k, []) or []:
            q = Path(f) if Path(f).is_absolute() else Path(base) / f
            if not q.exists() and f not in out:
                out.append(f)
    return out


def require_declared(ab0, base):
    miss = declared_missing(ab0, base)
    if miss:
        raise ValueError(f"bind verify: {len(miss)} as-built manifest source(s) absent under {base} (sparse checkout "
                         f"too narrow?): " + ", ".join(miss[:8]) + (" ..." if len(miss) > 8 else ""))


class LintSources:
    """DIE-S81-30 10-29 (COORD ruling S81 bind6 VERIFY FAIL (2): 5,071 lint MODMISSING): the module index the lint
    closure descends.  The as-built manifest index (rtl_roots + files) alone missed every child defined outside it
    (E.instantiated keeps only indexed names, so they vanished without a closure_missing entry): modules of multi-module
    files (ot_meso_ring in ot_meso_fifo.sv, ot_s81sl_ve_qmul/qadd/kand in eng/ot_s81sl_ve_fp.sv), the bind's own
    generated native glue (OUT/native_glue/*.sv), hard macros reached through a `define (ot_rom_4096x72_m8 in
    ot_s81sl_xs4.sv) and imported packages.  Index = every module DEFINITION scanned in (precedence, first wins):
      1. the manifest index (unchanged picks: a die whose old closure was complete gets the same files),
      2. the bind's extra library + its generated non-partition RTL (native glue),
      3. hard-macro views (bind.macro_views: black box, else model; never descended),
      4. the repo rtl/ tree (one non-sim definition, or a preferred one; several -> missing, never a silent pick).
    Instantiations are read from the needed module bodies AND from the file's `define bodies."""

    def __init__(self, ab0, base, rep, idx, prefer):
        import bind as B
        require_declared(ab0, base)
        self.base, self.prefer = Path(base), list(prefer)
        self.idx = {k: list(v) for k, v in idx.items()}
        own = [f for f in list(rep.get("extra_lib", [])) + list(rep.get("files", []))
               if Path(f).name != "bind_cells.sv" and not f.endswith("_bound_top.sv")]
        parts = {f for f in own if f in rep.get("files", []) and "native_glue" not in Path(f).parts}
        own_idx = E.module_index([], [f for f in own if f not in parts], base)
        self.added = {}
        for m, fs in own_idx.items():
            if m not in self.idx:
                self.idx[m], self.added[m] = list(fs), "bind"
        for m, d in B.macro_views(base).items():
            if m not in self.idx:
                bb, mdl = Path(d) / f"{m}_bb.v", Path(d) / f"{m}.v"
                f = bb if bb.is_file() else mdl if mdl.is_file() else None
                if f is not None:
                    self.idx[m], self.added[m] = [str(f)], "macro"
        rtl_all = self.base / "rtl"
        self.wide = E.module_index([str(rtl_all)], [], base) if rtl_all.is_dir() else {}
        self.roots = list(ab0.get("rtl_roots", ["rtl"])) or ["rtl"]
        self.defines = [str(d).split("=")[0] for d in ab0.get("defines", [])]
        self.ambiguous = {}
        self.picks, self.conflicts, self.moved, self._dparams = {}, {}, {}, {}
        # caches (one closure per partition module: ~360 on S81): stripped text, module bodies, prefer-file definitions
        self._txt, self._body, self._pdefs, self._uses, self._pdir = {}, {}, {}, {}, {}
        for q in self.prefer:
            if Path(q).is_file():
                self._pdefs[q] = {m.group(1) for m in E.MOD_RE.finditer(self.text(q))}

    def text(self, f):
        if f not in self._txt:
            self._txt[f] = E._strip(Path(f).read_text(errors="replace"))
        return self._txt[f]

    def body(self, f, n):
        """E.module_body on the cached stripped text"""
        k = (f, n)
        if k not in self._body:
            m = re.search(r"^\s*(?:\(\*[^\n]*?\*\)\s*)?module\s+" + re.escape(n) + r"\b(.*?)\bendmodule\b", self.text(f),
                          re.S | re.M)
            self._body[k] = m.group(1) if m else ""
        return self._body[k]

    def _prefer_for(self, n):
        """the prefer entries E.pick can use for n (same order): directories, and files that define n"""
        return [q for q in self.prefer if q not in self._pdefs and not Path(q).is_file() or n in self._pdefs.get(q, ())]

    def packages(self, files):
        """bind.kit_packages with cached reads: the packages the files reference (pkg::), transitively, users last;
        a package beside its users first, else the RTL roots."""
        import bind as B

        def uses(f):
            if f not in self._uses:
                self._uses[f] = sorted(set(B.PKG_USE.findall(self.text(f))))
            return self._uses[f]

        def pdir(d):
            if d not in self._pdir:
                self._pdir[d] = B._pkg_index([d], self.base, recurse=False)
            return self._pdir[d]
        pidx = {}
        for d in sorted({str(Path(f).resolve().parent) for f in files}, reverse=True):
            pidx.update(pdir(d))
        want = {u for f in files for u in uses(f) if "pkg" in u.lower()}
        if want - set(pidx):
            key = (tuple(self.roots), str(self.base))
            if key not in B._PKG_CACHE:
                B._PKG_CACHE[key] = B._pkg_index(self.roots, self.base)
            pidx = {**B._PKG_CACHE[key], **pidx}
        order, seen = [], set()

        def need(f):
            for u in uses(f):
                if u in pidx and u not in seen:
                    seen.add(u)
                    need(pidx[u])
                    order.append(str(Path(pidx[u])))
        for f in files:
            need(f)
        return order

    def _cands(self, n):
        if n in self.idx:
            return self.idx[n]
        c = [f for f in self.wide.get(n, []) if not re.search(r"_sim\.s?v$", f)] or self.wide.get(n, [])
        if len(c) > 1 and not any(Path(f).resolve() == Path(q).resolve() for f in c for q in self.prefer):
            self.ambiguous[n] = c
            return []
        if c:
            self.added.setdefault(n, "rtl")
        return c

    def _define_index(self):
        """{macro: [file, ...]} of every `define in the indexed + rtl/ sources (built once, on first need)"""
        if getattr(self, "_didx", None) is None:
            self._didx = {}
            for f in sorted({f for fs in list(self.idx.values()) + list(self.wide.values()) for f in fs}):
                try:
                    raw = Path(f).read_text(errors="replace")
                except OSError:
                    continue
                if "`define" in raw:
                    for d in MACRO_DEF.finditer(self.text(f)):
                        self._didx.setdefault(d.group(1), []).append(f)
        return self._didx

    def providers(self, files, have):
        """files that `define a macro the closure files use but none of them defines (e.g. `SELT_OB of
        ot_s81pa_ctl.sv lives in ot_s81ph_sel_tile.sv): exactly one defining file, else left unresolved"""
        used, defined = set(), set()
        for f in files:
            tx = self.text(f)
            used |= set(MACRO_USE.findall(tx))
            defined |= {d.group(1) for d in MACRO_DEF.finditer(tx)}
        need = used - defined - DIRECTIVES - set(self.defines)
        out = []
        for m in sorted(need):
            c = [f for f in self._define_index().get(m, []) if f not in have]
            if len(c) == 1 and c[0] not in out:
                out.append(c[0])
            elif len(c) > 1:
                self.ambiguous.setdefault("`" + m, c)
        return out

    def closure(self, names):
        """E.closure over this index: -> (files incl. their packages and macro providers first, missing).
        self.picks / self.conflicts / self.moved describe the last call (see _closure)."""
        files, missing, prov = self._closure(names, [])
        while True:
            new = self.providers(files, set(files) | set(prov))
            if not new:
                break
            prov += new
            # a provider file is read whole: its modules' children are needed too
            files, missing, _ = self._closure(names, prov)
        # a closure file that `defines a macro another closure file uses goes before them (ot_s81ph_sel_tile.sv
        # `SELT_* used by ot_s81ph_hq_tile.sv): Verilator sees a `define only after it is read
        body = [f for f in files if f not in prov]
        defs = {f: {d.group(1) for d in MACRO_DEF.finditer(self.text(f))} for f in body}
        uses = {f: set(MACRO_USE.findall(self.text(f))) for f in body}
        early = [f for f in body if any(defs[f] & uses[g] for g in body if g != f)]
        prov = prov + early
        pkgs = self.packages(prov + body)
        return [p for p in pkgs if p not in prov and p not in body] + prov + [f for f in body if f not in prov], missing

    def declared_params(self, f, n):
        k = (f, n)
        if k not in self._dparams:
            import bind as B
            self._dparams[k] = B._declared_params(f, n)
        return self._dparams[k]

    def _param_compatible(self, n, cands, prefer, need):
        """QC-VERIFY-GAPS (the bind kit closure's KITPARAM rule, bind.kit_closure, applied to the lint closure; QC s26
        verify lint: ot_qwen_rom_tile_nk sets .IRCK/.NKP/.LQR on ot_qwen_rom_tile_w12 but the lint read the rtl/hdc
        copy that declares none of them, 64 PINNOTFOUND): when several definitions of n exist (index + preferred
        files) and some do not declare every parameter the picked instantiating bodies set by name, only the
        compatible ones stay candidates and the incompatible preferred files lose their preference for n.  A pick that
        is compatible, or with no compatible alternative, is unchanged.  -> (cands, prefer)"""
        nc = list(dict.fromkeys(list(cands) + [q for q in prefer if n in self._pdefs.get(q, ())]))
        if len({str(Path(c).resolve()) for c in nc}) < 2:
            return cands, prefer
        ok = [c for c in nc if need <= self.declared_params(c, n)]
        if not ok or len(ok) == len(nc):
            return cands, prefer
        bad = {str(Path(c).resolve()) for c in nc if c not in ok}
        self.moved[n] = sorted(need)
        return ok, [q for q in prefer if str(Path(q).resolve()) not in bad]

    def _closure(self, names, extra_files):
        """closure passes until the picks are stable: a pass whose pick a later-scanned instantiator cannot serve is
        repeated with every PICKED instantiator's named parameters known up front (the result must not depend on scan
        order); at most 4 passes, the last one's conflicts stand"""
        files, missing, prov = self._closure_pass(names, extra_files, None)
        for _ in range(3):
            if not self.conflicts:
                break
            prev = dict(self.picks)
            files, missing, prov = self._closure_pass(names, extra_files, self._picked_need())
            if self.picks == prev:
                break
        return files, missing, prov

    def _picked_need(self):
        """{module: parameter names set by name in the PICKED definitions that instantiate it}: a sibling module of a
        picked file whose own pick is another file is not elaborated (the split run reads one definition per module)"""
        need = {}
        for c, by in self._need_src.items():
            for (f, owner), ps in by.items():
                if owner is None or self.picks.get(owner, f) == f:
                    need.setdefault(c, set()).update(ps)
        return need

    def _closure_pass(self, names, extra_files, seed):
        import bind as B
        known = set(self.idx) | set(self.wide)
        seen, files, missing = set(), [], set()
        self.picks, self.conflicts, self.moved = {}, {}, {}
        # module -> parameter names the picked instantiating bodies set by name (seeded: from the previous pass)
        need = {k: set(v) for k, v in (seed or {}).items()}
        self._need_src = src = {}         # module -> {(file, instantiating module): parameter names}

        def found(body, f, owner, picked):
            got = E.instantiated(body, known)
            for c, ps in B._named_param_overrides(body, got).items():
                src.setdefault(c, {}).setdefault((f, owner), set()).update(ps)
                if picked and seed is None:
                    need.setdefault(c, set()).update(ps)
            return sorted(got)
        todo = list(names)
        for f in extra_files:
            for m in E.MOD_RE.finditer(self.text(f)):
                todo += found(self.body(f, m.group(1)), f, None, True)
        while todo:
            n = todo.pop()
            if n in seen:
                continue
            seen.add(n)
            cands, pref = self._cands(n), self._prefer_for(n)
            if need.get(n):
                cands, pref = self._param_compatible(n, cands, pref, need[n])
            f, _ = E.pick({n: cands}, n, pref)
            if f is None:
                missing.add(n)
                continue
            self.picks[n] = f
            if self.added.get(n) == "macro":
                if f not in files:
                    files.append(f)
                continue
            if f not in files:
                files.append(f)
                txt = self.text(f)
                for m in E.MOD_RE.finditer(txt):
                    todo += found(self.body(f, m.group(1)), f, m.group(1), False)
                for d in DEFINE_RE.finditer(txt):          # a macro body names its module bare: `define ROM ot_rom_x
                    todo += sorted({w for w in re.findall(r"[A-Za-z_]\w*", d.group(1)) if w in known})
            todo += found(self.body(f, n), f, n, True)
        # a picked definition that does not declare a parameter a picked instantiator sets by name: one lint run
        # cannot hold both (two leaves needing two definitions of one name) -> lint_split splits the run
        for c, ps in self._picked_need().items():
            p = self.picks.get(c)
            if p is not None and self.added.get(c) != "macro" and not ps <= self.declared_params(p, c):
                self.conflicts[c] = ps - self.declared_params(p, c)
        return files, sorted(missing), list(extra_files)

    def leaf_groups(self, leafm):
        """Leaf masters of one partition split into groups whose closures agree on every module definition (greedy,
        sorted): one group when the partition closure has no definition conflict.  A leaf whose own closure conflicts
        stays a group of its own (its errors stay visible)."""
        picks = {}
        for m in leafm:
            self.closure([m])
            picks[m] = dict(self.picks)
        groups = []
        for m in sorted(leafm):
            g = next((g for g in groups if all(picks[x].get(k, f) == f for x in g for k, f in picks[m].items())), None)
            if g is None:
                groups.append([m])
            else:
                g.append(m)
        return groups


def declared_constant(want, got):
    """a bound constant that the bind declared: a strap (partition parameter) or a literal (proven-dead input /
    internal primitive literal), with the as-built value; any other constant on a leaf input is TIED"""
    return bool(want) and got[0] == "tied" and want[0] in ("strap", "literal") and want[1] == got[1]


def split_leaves(t, mods, idx):
    """the leaf masters a partition module file instantiates (u_<n>), plus the bind's own native glue cells (g_<n>)"""
    leafm = set(re.findall(r"^\s+(\w+)\s+(?:#\(.*?\)\s+)?u_\w+\s*\(", t, re.M))
    if isinstance(idx, LintSources):
        leafm |= {m for m in E.instantiated(E._strip(t), idx.idx) if idx.added.get(m) == "bind"}
    return sorted(leafm - set(mods) - BIND_CELLS)


def split_stub_text(text):
    """{module: its interface stub text} of an E.lib_stubs file (one `module ... endmodule` block each)"""
    return {m.group(1): m.group(0) + "\n" for m in
            re.finditer(r"^[ \t]*module\s+([A-Za-z_]\w*)\b.*?^[ \t]*endmodule\b", text, re.S | re.M)}


def dedup_by_pick(files, d, picks):
    """bind.kit_strip_dups for one split lint run (QC cbx_q10: the NK group's closure reads nk_vr7n
    ot_qwen_rom_tile_w12_land32.sv for ot_qwen_rom_tile_w12 AND rtl/hdc ot_qwen_rom_tile_w12.sv for a sibling module,
    so two files define ot_qwen_rom_tile_w12 and Verilator keeps the first): every module defined by several run files
    keeps the definition the closure picked (else the first); each other file is read as a copy with that module
    removed (original unchanged; copies named by list position, two picked files may share a basename).
    -> (files, the originals of the copies: their directories stay include dirs)"""
    defs = {}
    for f in files:
        for m in E.MOD_RE.finditer(E._strip(Path(f).read_text(errors="replace"))):
            defs.setdefault(m.group(1), [])
            if f not in defs[m.group(1)]:
                defs[m.group(1)].append(f)
    if all(len(v) < 2 for v in defs.values()):
        return list(files), []
    dd = Path(d) / "dedup"
    dd.mkdir(parents=True, exist_ok=True)
    out, orig = [], []
    for i, f in enumerate(files):
        keep = {m: next((x for x in fs if m in picks and Path(x).resolve() == Path(picks[m]).resolve()), fs[0])
                for m, fs in defs.items() if f in fs and len(fs) > 1}
        if all(k == f for k in keep.values()):
            out.append(f)
            continue
        new = Path(f).read_text(errors="replace")
        for m in sorted(k for k, v in keep.items() if v != f):     # the bind.kit_strip_dups module cut
            new, n = re.subn(r"^[ \t]*(?:\(\*[^\n]*?\*\)\s*)?module\s+" + re.escape(m) + r"\b.*?^[ \t]*endmodule\b[^\n]*\n?",
                             "", new, count=1, flags=re.S | re.M)
            if n != 1:
                raise RuntimeError(f"lint dedup: cannot strip duplicate module {m} from {f}")
        sub = dd / f"{i:03d}"
        sub.mkdir(exist_ok=True)
        c = sub / Path(f).name
        c.write_text(new)
        out.append(str(c))
        orig.append(str(f))
    return out, orig


def lint_split(out, top, F, G, gen_rtl, idx, prefer, rs, lib, ab0):
    """asbuilt.lint_split: a die too large for one Verilator run is linted in pieces that together cover it:
    the bound top + every partition module against leaf INTERFACE stubs, then each partition module with the real
    RTL closure of its own leaves (one run per partition module, jobs in parallel)."""
    from concurrent.futures import ThreadPoolExecutor
    defines, waive = ab0.get("defines", []), ab0.get("lint_waive", [])
    ldir = Path(out) / "lint"
    ldir.mkdir(exist_ok=True)
    stubs = E.lib_stubs(lib, ldir / "leaf_stubs.sv")
    runs = {"top": [stubs, str(rs)] + gen_rtl}
    cells = [f for f in gen_rtl if Path(f).name == "bind_cells.sv"]
    byfile, tops, stubbed, incs_of = {}, {}, set(), {}
    for f in gen_rtl:
        if f.endswith("_bound_top.sv") or f in cells:
            continue
        t = Path(f).read_text(errors="replace")
        mods = re.findall(r"^module\s+(\w+)", t, re.M)
        leafm = split_leaves(t, mods, idx)
        cl, _ = idx.closure(leafm) if isinstance(idx, LintSources) else E.closure(leafm, idx, prefer)
        groups = idx.leaf_groups(leafm) if isinstance(idx, LintSources) and idx.conflicts and len(leafm) > 1 else [leafm]
        for m in mods:
            byfile[m] = [f] + cells + [str(rs)] + cl
        if len(groups) > 1 and len(mods) == 1:
            # QC-VERIFY-GAPS (QC cbx_q10: NK + NL tiles need two different ot_qwen_rom_tile_w12 definitions, which one
            # Verilator run cannot hold): one run per leaf group, each with the real closure of its own leaves and
            # the interface stubs of the partition's other leaves; together the runs cover every leaf once
            other = split_stub_text(Path(stubs).read_text(errors="replace"))
            m = mods[0]
            # a leaf with no interface stub (a bind cell such as ot_dp_lk, read by every run via bind_cells.sv) is
            # linted in every group's run; only stubbed leaves outside the group become stubs
            shared = sorted(x for x in leafm if x not in other)
            groups = [g for g in ([x for x in g if x in other] for g in groups) if g]
            if len(groups) > 1:
                for k, g in enumerate(groups):
                    name = m if k == 0 else f"{m}__group{k}"
                    sd = ldir / name
                    sd.mkdir(exist_ok=True)
                    sf = sd / "other_leaf_stubs.sv"
                    sf.write_text("".join(other[x] for x in sorted(set(leafm) - set(g) - set(shared))))
                    gl, _ = idx.closure(sorted(set(g) | set(shared)))
                    gl, orig = dedup_by_pick(gl, sd, dict(idx.picks))
                    byfile[name] = [f] + cells + [str(rs), str(sf)] + gl
                    tops[name] = m
                    stubbed.add(name)
                    incs_of[name] = orig
    runs.update(byfile)

    def one(item):
        name, files = item
        d = ldir / name
        d.mkdir(exist_ok=True)
        # the top run reads leaf stubs, which keep the leaves' `include lines: their source directories are include dirs
        return name, lint(d, top if name == "top" else tops.get(name, name), files, defines, waive,
                          (list(lib) + incs_of.get(name, [])) if name == "top" or name in stubbed else ())
    res = dict(ThreadPoolExecutor(int(ab0.get("lint_jobs", 4))).map(one, sorted(runs.items())))
    errs = sum(r.get("errors", 0) for r in res.values() if r.get("ran"))
    first = [f"[{n}] {e}" for n, r in sorted(res.items()) for e in r.get("first_errors", [])][:20]
    return dict(ran=all(r.get("ran") for r in res.values()), split=True, runs=len(res), errors=errs,
                warnings=sum(r.get("warnings", 0) for r in res.values()), first_errors=first,
                failed_runs=sorted(n for n, r in res.items() if r.get("errors")),
                waived=[w for r in res.values() for w in r.get("waived", [])][:50], waivers=list(waive))


def landing_transport_rules():
    """Identity transport only; the independent landing verifier checks clock/reset/config."""
    return [
        dict(module='ot_dp_clk_landing',map={'q':'d'},
             drop_in=['clk','fclk','rst_n'],drop_out=['ready','fault'],stages=3),
        dict(module='ot_dp_clk_landing_ca',map={'q':'d'},
             drop_in=['clk','fclk','rst_n','t_rst_n'],drop_out=['ready','fault'],stages=0,stages_param='K'),
        dict(module='ot_dp_clk_landing_cas',map={'q':'d'},
             drop_in=['clk','fclk','rst_n','t_rst_n','strap_k'],drop_out=['ready','fault'],stages=0,stages_port='strap_k')]


def set_count_aligned_transport(graph,stages):
    """Use verified per-instance fixed CA latency, never unsigned modular strap K."""
    for ci,c in enumerate(graph.F.cells):
        if c.path not in stages:continue
        if c.module not in ('ot_dp_clk_landing_ca','ot_dp_clk_landing_cas'):
            raise ValueError('count-aligned latency names a non-CA cell '+c.path)
        spec=dict(graph.spec[ci],stages=int(stages[c.path]))
        spec.pop('stages_param',None);spec.pop('stages_port',None)
        graph.spec[ci]=spec


class KitSourceCredit:
    """VERIFY-PRICING-1 11-12: kit source stations a kit_source_station_pricing bind priced but did not emit.

    With asbuilt kit_source_station_pricing on, the bind takes a lane's source-kit stations out of the receiver pad
    (native_istations.annotate_kit: internal_kit_source_cycles) because the SOURCE kit inserts them (kit_istations
    u_ist_<o>_<j> before u_bout_<o>); bind_sinks.json still carries the full lane depth.  The bound RTL is therefore
    short by exactly that count on every sink whose path passes the lane's source face u_bout_<o>.  cuts:
    {(source partition, bus_out): (n, lane)} from lane_asbuilt_latency.source_cuts (LATCHECK-1's station source), so
    verify credits the same stations the as-built lane check counts.  credit(net) = the summed cuts of every cut
    u_bout_<o> on the transport chain that drives net (forwarded buses cross more than one); 0 when cuts is empty
    (switch off: the receiver pad holds them, nothing is credited)."""

    def __init__(self, G, cuts):
        self.G = G
        want = {f"{sv_id(p)}.u_bout_{sv_id(b)}": (n, lane) for (p, b), (n, lane) in cuts.items()}
        self.cells = {}                     # ci -> cut
        self.lane_of = {}                   # ci -> lane
        found = set()
        for ci, c in enumerate(G.F.cells):
            if G.kind[ci] != "transport":
                continue
            k = ".".join(c.path.split(".")[-2:])
            if k in want:
                self.cells[ci], self.lane_of[ci] = want[k]
                found.add(k)
        self.unmatched = sorted(set(want) - found)   # a priced source face the bound netlist does not have
        self._memo = {}

    def credit(self, net):
        """-> (stations, [lanes]) credited on the transport chain driving net"""
        if not self.cells:
            return 0, ()
        walk = []
        G = self.G
        base = (0, ())
        for _ in range(100000):
            if isinstance(net, str):
                break
            if net in self._memo:
                base = self._memo[net]
                break
            ds = G.drv.get(net, [])
            if len(ds) != 1 or net in G.F.const_drivers:
                break
            ci, pn, bit = ds[0]
            if G.kind[ci] != "transport":
                break
            sp = G.spec[ci]
            ip = _tmap(sp, pn)
            if ip is None:
                break
            ib = G.F.cells[ci].ports[ip]
            if sp.get("replicate") and ib:
                bit = bit % len(ib)
            walk.append((net, ci))
            net = ib[bit] if bit < len(ib) else "z"
        n, lanes = base
        for nt, ci in reversed(walk):
            if ci in self.cells:
                n, lanes = n + self.cells[ci], tuple(lanes) + (self.lane_of[ci],)
            self._memo[nt] = (n, lanes)
        return n, lanes

    def adjust(self, s, got, net):
        """a non-glue pin source's described stage count + the credited stations -> (got, credit, raw got, lanes)"""
        if not self.cells or s[0] != "pin" or got[3]:
            return got, 0, None, ()
        kc, lanes = self.credit(net)
        if not kc:
            return got, 0, None, ()
        return got[:2] + [got[2] + kc] + got[3:], kc, got, lanes


def kit_source_cuts(out, raw):
    """{(source partition, bus_out): (n, lane)} of a bind dir made with raw['asbuilt'] kit_source_station_pricing"""
    sel = raw["asbuilt"].get("kit_source_station_pricing")
    if not sel:
        return {}
    import lane_asbuilt_latency as LAL
    rows, module_of, ptype_of, types, _land, _pm = LAL.load_bind_dir(out, raw)
    return LAL.source_cuts(raw, rows, module_of, ptype_of, types, sel)


def native_lib_stubs(lib, vdir):
    """Interface-only leaf stubs for the NATIVE Yosys verify read.

    Verify always parses with read_verilog -sv, even when elaboration used slang
    (which accepts typed string parameters, e.g. the ROM macro VIAMAP/INSTANCE).
    Native Yosys rejects `parameter string`, so the stub file -- a black-box
    interface only, never a verification body -- is staged with untyped
    string-valued parameters (same literal defaults). Real sources unchanged."""
    if not lib:
        return []
    stub = E.lib_stubs(lib, vdir / "lib_stubs.sv")
    staged, _rec = E.string_parameter_compat([stub], vdir / "string_parameter_compat")
    return staged


PORT_RE = re.compile(r"\b(input|output|inout)\s+(?:wire\s+|logic\s+|reg\s+)?(?:signed\s+)?"
                     r"(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?([A-Za-z_]\w*)(?=\s*(?:,|\)|$))")


def stub_ifaces(text):
    """{module: {port: (dir, width)}} of the ANSI-header stubs in text with numeric ranges (the lib_stubs form)."""
    out = {}
    for m in re.finditer(r"^\s*module\s+([A-Za-z_]\w*)\b(.*?)\)\s*;", text, re.S | re.M):
        hdr = re.sub(r"^\s*#\s*\(.*?\)\s*\(", "(", m.group(2), flags=re.S)
        ports = {p.group(4): (p.group(1), abs(int(p.group(2)) - int(p.group(3))) + 1 if p.group(2) else 1)
                 for p in PORT_RE.finditer(hdr)}
        # a port this form cannot read (parametric range, packed type): no interface rather than a wrong one
        out[m.group(1)] = ports if len(ports) == len(re.findall(r"\b(?:input|output|inout)\b", hdr)) else None
    return out


def core_split_stubs(raw_ab, rep, stub_text, vdir):
    """Interface stubs for the leaves asbuilt.core_splits creates (e.g. qkd_kvs_pc -> qkd_kvs_pcc + qkd_kvs_pcf).

    The split leaves are hard leaves with no RTL source, so the lib stubs never define them and bound.ys stops on
    an undefined module.  Interfaces: bind_report core_split_ifaces (the final bind cells, exact), else derived from
    the source leaf's stub by the same port transform.  A split leaf that a lib file already defines keeps that."""
    specs = raw_ab.get("core_splits") or []
    if not specs:
        return []
    import bind_core_split
    have = stub_ifaces(stub_text)
    ifs = rep.get("core_split_ifaces") or bind_core_split.derived_ifaces(specs, have.get)
    body = []
    for mod, e in sorted(ifs.items()):
        if mod in have:
            continue
        ps = ", ".join(f"parameter {p} = 0" for p in e.get("params", []))
        pl = ",\n".join(f"    {d} wire [{w - 1}:0] {p}" for p, (d, w) in e["ports"].items())
        body.append(f"// core_splits leaf (no source): interface as bound\nmodule {mod}{f' #({ps})' if ps else ''} (\n"
                    f"{pl}\n);\nendmodule\n")
    if not body:
        return []
    f = vdir / "core_split_stubs.sv"
    f.write_text("\n".join(body))
    return [str(f)]


def cmd_verify(a):
    import bind as _b
    _b._AB_OVERRIDE["path"] = getattr(a, "asbuilt", None)
    raw = load_plan(a.plan)
    out = Path(a.out).resolve()
    rep = json.loads((out / "bind_report.json").read_text())
    require_declared(raw["asbuilt"], _b.plan_base(a.plan, raw))    # before the multi-hour read, not after it
    srcs = json.loads((out / "asbuilt_sources.json").read_text())
    gen = [f for f in rep["files"]]
    top = f"{sv_id(raw['die']['name'])}_bound_top"
    dissolve = sorted({t["module"] for t in rep["types"].values()})     # as bound (variants / renamed included)
    dissolve = sorted(set(dissolve) | {g["module"] for gs in rep.get("bound_groups", {}).values() for g in gs})
    ab = dict(netlist=[f for f in gen if f.endswith("_bound_top.sv")], top=top, dissolve=dissolve,
              defines=raw["asbuilt"].get("defines", []), substitute={})
    full = [f for f in gen if not f.endswith("_bound_top.sv")]
    rs = Path(E.REPO / "rtl/lib/ot_reset_sync.sv")
    # leaf interfaces: lib files, files of dissolved parents that also define leaves (not the die top / shims), variants
    pfull = [f for f in srcs.get("full", []) if f not in srcs.get("tops", []) and not Path(f).name.startswith("shim_")]
    lib = [f for f in srcs.get("lib", []) + pfull + rep.get("extra_lib", []) if f not in full] + \
        ([str(rs)] if str(rs) not in srcs.get("lib", []) else [])
    vdir = out / "verify"
    vdir.mkdir(exist_ok=True)
    sc = vdir / "bound.ys"
    js = vdir / "bound.json"
    ylib = native_lib_stubs(lib, vdir)
    ylib += core_split_stubs(raw["asbuilt"], rep, (vdir / "lib_stubs.sv").read_text() if lib else "", vdir)
    sc.write_text(E.yosys_script(ab, ab["netlist"], full, ylib, js, check=True, inc_files=lib))
    mounts = [out, E.REPO] + [Path(f).parent for f in lib]
    roots = sorted({str(Path(m).resolve()) for m in mounts}, key=len)
    mounts = [m for i, m in enumerate(roots) if not any(m.startswith(r + "/") for r in roots[:i])]
    E.run_yosys(sc, vdir / "bound.yosys.log", mounts, a.mem)
    F = E.flatten(json.loads(js.read_text()), top)
    errs = []
    vr = dict(VERIFY_RULES)
    landing_table=None;landing_verify=None
    if raw['asbuilt'].get('clock_landing_table'):
        landing_file=(Path(_b.plan_base(a.plan,raw))/raw['asbuilt']['clock_landing_table']).resolve()
        landing_table=json.loads(landing_file.read_text())
        vr['transport']=vr['transport']+landing_transport_rules()

    vr["clocks"], vr["resets"], vr["map"] = [], [], {}
    names = json.loads((out / "bind_names.json").read_text())
    R = Rules(vr)
    R.keep_source = set(names)          # as-built leaves the bind emitted are never reset/clock sources
    G = Graph(F, R, errs)
    sinks = json.loads((out / "bind_sinks.json").read_text())
    if landing_table:
        import clock_landing_verify as CLV
        live_widths={}
        for bus in json.loads((out/'bind_latency.json').read_text())['buses']:
            if bus.get('lane'):
                lane=bus['lane'];width=bus['width']
                if lane in live_widths and live_widths[lane]!=width:
                    raise ValueError('landing verify: inconsistent live lane width '+lane)
                live_widths[lane]=width
        landing_verify=CLV.Verification(F,G,raw,landing_table,names,live_widths=live_widths,plan_path=Path(a.plan))
        set_count_aligned_transport(G,landing_verify.transport_stages)
    clk_top = {}
    for pn, (d, bits) in F.top_ports.items():
        if pn.startswith("clk_"):
            clk_top[pn] = pn[4:]

    def gdesc(s):
        k = s[0]
        if k == "pin":
            c = F.cells[s[1]]
            p = names.get(c.path, c.path) if G.kind[s[1]] != "glue" else None
            return ["pin", f"{p}.{s[2]}[{s[3]}]" if p else None, s[4], G.kind[s[1]] == "glue"]
        if k == "top":
            if s[1] in clk_top:
                return ["clk", clk_top[s[1]]]
            if raw.get("reset", {}).get("release") == "wavefront" and s[1] == "rst_n":
                return ["rst", "low"]  # native hard-partition delivered reset; timing checked by offsets
            return ["top", s[1]]
        if k == "reset":
            return ["rst", s[1]]
        if k in ("or", "and"):
            return [k, sorted(gdesc(x)[1] for x in s[1] if x[0] == "pin")]
        if k == "const":
            return ["tied", s[1]]
        return [k]

    # QC-NK-HOLD A+P: declared core-input pipeline cycles (bind.core_input_pipe): the as-built stage count of those
    # sinks + D is the expected bound count (EQ with the cycle declared); every other sink is unchanged
    _pf = out / "bind_core_input_pipe.json"
    core_pipe = json.loads(_pf.read_text()) if _pf.is_file() else {}
    cnt_pipe = 0
    reg_parts = {sv_id(p) for p in rep.get("registered_pins", {})}
    cnt = dict(compared=0, matched=0, mismatched=0, glue_unmatched=0, unbound=0, tied=0, undriven=0, multiply_driven=0, plan_driven=0)
    mism, tied_ex = [], []
    seen = set()
    # VERIFY-PRICING-1: kit source stations priced in the lane but inserted later by the source kit (switch on only)
    kcuts = kit_source_cuts(out, raw)
    kit = KitSourceCredit(G, kcuts)
    kstat = dict(pricing=raw["asbuilt"].get("kit_source_station_pricing", False), lanes_priced=len(kcuts),
                 stations_priced=sum(n for n, _ in kcuts.values()), faces_unmatched=kit.unmatched[:50],
                 n_faces_unmatched=len(kit.unmatched), sinks=0, raw_mismatched_credited_match=0,
                 raw_matched_credited_mismatch=0, mismatched_both=0, matched_both=0, by_lane={},
                 cut_by_lane={lane: n for n, lane in kcuts.values()})
    for ci, c in enumerate(F.cells):
        if G.kind[ci] in ("transport", "reducer", "source", "glue"):
            continue
        ap = names.get(c.path)
        if ap is None:
            continue
        seen.add(ap)
        for pn, bits in c.ports.items():
            if G.dirs[ci].get(pn) != "input":
                continue
            for i, b in enumerate(bits):
                key = f"{ap}.{pn}[{i}]"
                want = sinks.get(key)
                if want and want[0] == "pin" and core_pipe.get(f"{ap}.{pn}"):
                    want = list(want[:2]) + [want[2] + int(core_pipe[f"{ap}.{pn}"])] + list(want[3:])
                    cnt_pipe += 1
                original=landing_verify.observer_input(c,pn,i) if landing_verify else None
                s = G.source(original if original is not None else b)
                got = gdesc(s)
                got, kc, raw_got, klanes = kit.adjust(s, got, original if original is not None else b)
                if kc:
                    kstat["sinks"] += 1
                    for ln in klanes:
                        kstat["by_lane"][ln] = kstat["by_lane"].get(ln, 0) + 1
                if got[0] in ("undriven", "dropped"):
                    cnt["undriven"] += 1
                    cnt["unbound"] += 1
                if want and want[0] == "plan":
                    # a plan-cell driven input: a live driver; a same-partition plan cell / leaf must be the one named
                    cnt["plan_driven"] += 1
                    if got[0] in ("pin", "clk", "rst", "or", "and") and (want[1] is None or got[0] == "pin" and got[1] == want[1]):
                        cnt["compared"] += 1
                        cnt["matched"] += 1
                        continue
                # a declared literal (bind.py: proven-dead input of asbuilt.dead_input_proofs / internal primitive
                # literal) is emitted as 1'b<v> by design: it matches only its own declared value (DIE-S81-30 10-29)
                declared = declared_constant(want, got)
                if got[0] == "tied" and not declared:
                    cnt["tied"] += 1
                    if len(tied_ex) < 50:
                        tied_ex.append((key, want, got))
                if got[0] == "tied" and declared:
                    got = want          # a declared strap (partition parameter) / literal carries the as-built value
                if got[0] == "multi":
                    cnt["multiply_driven"] += 1
                if want is None:
                    mism.append((key, "not in as-built", got))
                    cnt["mismatched"] += 1
                    continue
                cnt["compared"] += 1
                if want[0] == "pin" and (want[3] or got[0] == "pin" and got[3]):
                    cnt["glue_unmatched"] += 1
                    continue
                if want == ["rst", "low"] and got == ["top", "rst_n"] and c.path.split(".")[0] in reg_parts:
                    # registered-pin hard partition (bind.py reg_hard): no synchroniser of ours inside the bare
                    # macro, its leaf reset is the delivered die reset (arst_n) as in a wavefront hard partition
                    got = want
                if want == ["start"] and got == ["rst", "low"]:
                    # local START tap start_t<k> = ot_dp_rgate(raw reset, run): its reset leg traces to the die reset
                    # (run is dropped like on every gated tap); START timing is proven by the lockstep tests
                    got = want
                if landing_verify and want[0]=='clk':
                    part=c.path.split('.')[0]
                    regions={sv_id(p):r for p,r in landing_verify.region.items()}
                    if part in regions and got==['clk','region_'+sv_id(regions[part])]:
                        got=want  # exact region clock proved against this actual leaf partition
                ok = want[:3] == got[:3] if want[0] == "pin" else want == got
                if kc:
                    raw_ok = want[:3] == raw_got[:3] if want[0] == "pin" else want == raw_got
                    kstat["raw_mismatched_credited_match" if ok and not raw_ok else
                          "raw_matched_credited_mismatch" if raw_ok and not ok else
                          "matched_both" if ok else "mismatched_both"] += 1
                if ok:
                    cnt["matched"] += 1
                else:
                    cnt["mismatched"] += 1
                    if len(mism) < 200:
                        mism.append((key, want, got) + ((dict(kit_source_credit=kc, raw=raw_got),) if kc else ()))
    cnt["pipe_declared"] = cnt_pipe   # sinks compared with a declared +D core-input pipe (bind_core_input_pipe.json)
    missing = sorted(set(names.values()) - seen)
    # lint: the bound RTL plus the full RTL closure of every leaf master (unchanged as-built sources)
    from bind import plan_base
    ab0 = raw["asbuilt"]
    base = plan_base(a.plan, raw)
    idx = E.module_index(ab0.get("rtl_roots", ["rtl"]), ab0.get("files", []), base)
    prefer = [str(Path(base) / f) if not Path(f).is_absolute() else f for f in ab0.get("prefer", [])]
    leafm = sorted({c.module for ci, c in enumerate(F.cells) if G.kind[ci] == "leaf"})
    prefer += rep.get("extra_lib", [])
    LS = LintSources(ab0, base, rep, idx, prefer)
    cl, cl_missing = LS.closure(leafm)
    gen_rtl = [f for f in rep["files"]]
    if not ab0.get("lint_split"):
        lt = lint(out, top, cl + gen_rtl + [str(rs)], ab0.get("defines", []), ab0.get("lint_waive", []))
    else:
        lt = lint_split(out, top, F, G, gen_rtl, LS, prefer, rs, lib, ab0)
    lt["closure_files"], lt["closure_missing"] = len(cl), cl_missing
    lt["closure_added"] = dict(sorted(LS.added.items())[:200])
    lt["closure_ambiguous"] = {k: v[:4] for k, v in sorted(LS.ambiguous.items())[:50]}
    landing_result=landing_verify.report() if landing_verify else None
    if landing_result:errs.extend('CLOCK_LANDING '+e for e in landing_result['errors'])
    v = dict(clock_landing=landing_result,top=top, cells=len(F.cells), leaves_missing=len(missing), leaves_missing_examples=missing[:20],
             counts=cnt, kit_source_credit=kstat, mismatches=mism[:200], tied_examples=tied_ex, graph_errors=errs[:50], lint=lt,
             asbuilt_proof=rep["proof"], asbuilt_errors=rep["n_errors"])
    ok = (cnt["mismatched"] == 0 and cnt["unbound"] == 0 and cnt["tied"] == 0 and cnt["multiply_driven"] == 0 and
          not missing and not errs and rep["n_errors"] == 0 and (not lt.get("ran") or lt.get("errors") == 0))
    v["verdict"] = "PASS" if ok else "FAIL"
    (out / "verify_report.json").write_text(json.dumps(v, indent=1))
    print(json.dumps(dict(verdict=v["verdict"], **cnt, leaves_missing=len(missing), lint=lt.get("errors"),
                          asbuilt_errors=rep["n_errors"], kit_source_credited=kstat["sinks"],
                          kit_source_lanes=kstat["lanes_priced"])))
    for m in mism[:10]:
        print("  ", m)
    return 0 if ok else 1
