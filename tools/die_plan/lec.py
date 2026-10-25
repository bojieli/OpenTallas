#!/usr/bin/env python3
"""Logic equivalence check (LEC) of a partition kit: kit RTL vs its synthesised gate netlist (LEC lane, 2026-10-24).

    python3 tools/die_plan/lec.py KITDIR [--netlist NET.v] [--out DIR]         # exit 0 EQUIVALENT, 1 NOT EQUIVALENT,
                                                                                #      2 UNPROVEN, 3 tool error
Why: on 2026-10-24 the Yosys slang frontend silently dropped csa31[30:24] (out-of-range a[31:24] of a 31-bit operand,
ot_s81eng_rr_n32.sv), so every synthesised S81 eng netlist tied 11 request-address bits to 0 while every Verilator
bench passed.  Simulation of the RTL cannot see a synthesis-frontend bug; an RTL-vs-netlist equivalence check can.

Method = the commercial LEC flow (Conformal / Formality): sequential equivalence by key-point mapping (combinational
equivalence of every next-state / output function) plus register correspondence.
  gold  the kit RTL (config.mk VERILOG_FILES / DEFINES / INCLUDE_DIRS / TOP_PARAMS) read with a DIFFERENT HDL frontend
        than synthesis used (synthesis read_slang -> gold read_verilog -sv; synthesis read_verilog -> gold read_slang),
        then only proc / opt_expr -keepdc / wreduce -keepdc / peepopt / flatten / memory_map / generic techmap (no
        fsm / share / opt_dff / abc on the reference).
  gate  the gate netlist (default: 1_2_yosys.v; --netlist for the ODB export) with the ASAP7 TT liberty functions
        (RVT / LVT / SLVT, read_liberty functional models), flattened.
  key points  primary inputs and outputs by name; every flop by its register bit (both sides name the flop cell after
        the register wire it drives, `rename -wire`, as ORFS synth.tcl does; liberty QN state polarity normalised;
        unnamed generate scopes dropped); black boxes (SRAM / ROM macros, *_bb.v, SYNTH_BLACKBOXES, hard cores) are
        replaced on BOTH sides by the same stub: each input pin bit is a compare point, each output pin bit a shared
        free input (matched pins).
  register correspondence  registers that do not match by name (synthesis removed a constant flop, merged equal
        flops, named a flop after an alias wire, or the two frontends lay out an unpacked array differently) are
        paired / merged / set constant by random-simulation signatures, then the whole hypothesis set is proved
        inductively by ABC together (van Eijk): failing hypotheses are dropped until the set is inductive.  Registers
        are compared from equal (reset / don't-care) states, as commercial LEC does.
  compare points  every primary output, every flop next-state function (enable / sync reset folded by dffunmap, async
        set / reset by async2sync) and every black-box input pin, each one output of one AIG miter; proved by ABC
        (&fraig sweeping + &sat per output, per-cone &cec for leftovers; every compare point is its own cone, so the
        check is partitioned by construction and scales to 400k-cell kits).
Kept registers (fail-closed): every register bit the RTL declares kept ((* keep *) or a flop in a keep_hierarchy
        cell: pin flops, placement replicas) must be a flop of its own name in the netlist; one merged into its twin
        (opt_merge) passes correspondence, so it is counted here: KEEP FAIL (exit 1, the kit stops like NOT EQUIVALENT).
Verdict (DIR/lec.json; DIR defaults to KITDIR/lec):
  EQUIVALENT      every compare point proved (unmatched registers, if any, were free inputs: unobservable);
  NOT EQUIVALENT  >= 1 compare point differs and its cone sees only matched / proved key points and RTL registers the
                  synthesis dropped although they are not constant: a real function difference (failing points listed;
                  run_kit.sh stops the kit);
  UNPROVEN        the check could not finish (gold frontend cannot parse, latches / clock gates, solver limit) or a
                  difference depends on a gate register with no RTL counterpart / an X (don't-care) source, i.e. a
                  sequential optimisation (FSM recoding, retiming) this check cannot certify: reason recorded;
                  run_kit.sh warns and continues.
Kit flows never retime registers (retiming = UNPROVEN by construction: register keys would not match).
Run inside the ORFS image (run_kit.sh does), or from a host with docker: lec.py re-invokes itself in --image.
"""
import argparse
import collections
import gzip
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from array import array
from pathlib import Path

SCHEMA = "opentallas.lec.v1"
PROVE_JOBS = 1
IMAGE = os.environ.get("OT_ORFS_IMAGE", "openroad/orfs:asap7lock")
ORFS = "/OpenROAD-flow-scripts"
NLDM = ORFS + "/flow/platforms/asap7/lib/NLDM"
STD_LIBS = [f"asap7sc7p5t_{g}_{vt}_TT_nldm_{d}" for vt in ("RVT", "LVT", "SLVT")
            for g, d in (("AO", "211120.lib.gz"), ("INVBUF", "220122.lib.gz"), ("OA", "211120.lib.gz"),
                         ("SEQ", "220123.lib"), ("SIMPLE", "211120.lib.gz"))]
WRAP = "lec_top"            # wrapper: the kit top as u_dut, every output port bit captured by a keep flop lec_po_*
BB = "lec_bb"               # stub register prefix: lec_bbi_<pin> (compare point) / lec_bbo_<pin> (free input)
UNSUPPORTED_CELLS = re.compile(r"^(ICG|DHL|DLL|SDF|SDFH|SDFL)")   # clock gates, latches, scan flops (not modelled)
TYPE_SFX = re.compile(r"\$_[A-Z]+(?:_[A-Z0-9]+)?_$")
IDX = re.compile(r"^(.*?)((?:\[\d+\])+)$")
GENBLK = re.compile(r"(?<![^.])genblk\d+\.")
VAR_SFX = re.compile(r"\.(IQNN|IQN|IQ)$")

# flop naming map: every remaining $_DFF_[PN]_ gets a keep wire '<cell>.lecq' (AIGER map name of the latch)
LECFF_V = r"""(* techmap_celltype = "$_DFF_P_ $_DFF_N_" *)
module _lec_ff (C, D, Q);
  parameter _TECHMAP_CELLTYPE_ = "";
  input C, D;
  output Q;
  (* keep *) wire \_TECHMAP_REPLACE_.lecq ;
  $dff #(.WIDTH(1), .CLK_POLARITY(_TECHMAP_CELLTYPE_ == "$_DFF_P_")) _TECHMAP_REPLACE_ (.CLK(C), .D(D), .Q(\_TECHMAP_REPLACE_.lecq ));
  assign Q = \_TECHMAP_REPLACE_.lecq ;
endmodule
"""


class LecError(Exception):
    pass


class LintFail(Exception):
    """RTL lint failure (implicit nets): fails the kit like NOT EQUIVALENT (exit 1)."""


class Unproven(Exception):
    pass


# ---------------------------------------------------------------------------------------------- kit configuration
def parse_config(kit):
    """config.mk -> {VAR: value} (the make subset the kit generators write)."""
    env = {}
    for line in (Path(kit) / "config.mk").read_text().splitlines():
        line = line.split("#", 1)[0].rstrip()
        m = re.match(r"^\s*(?:override\s+)?(?:export\s+)?([A-Z0-9_]+)\s*([:?+]?)=\s*(.*)$", line)
        if not m:
            continue
        var, op, val = m[1], m[2], m[3].strip()
        if op == "+" and env.get(var):        # make += appends (HEAD0719 kits: VERILOG_FILES += ot_s81hd_rom_addr_copy.sv)
            env[var] = f"{env[var]} {val}" if val else env[var]
        elif op == "?" and var in env:        # make ?= sets only an undefined variable
            pass
        else:
            env[var] = val
    if "DESIGN_NAME" not in env or "VERILOG_FILES" not in env:
        raise LecError(f"{kit}/config.mk: no DESIGN_NAME / VERILOG_FILES")
    return env


def kpath(kit, p):
    """/work/... (the kit's docker mount) -> path under `kit`."""
    return str(Path(kit) / p[len("/work/"):]) if p.startswith("/work/") else p


def find_netlist(kit):
    """the Yosys netlist of the kit (1_2_yosys.v; 1_synth.v of older ORFS)."""
    for n in ("1_2_yosys.v", "1_synth.v"):
        c = sorted(Path(kit).glob(f"run/results/asap7/*/base/{n}"))
        if c:
            return str(c[-1])
    raise LecError(f"no synthesised netlist under {kit}/run/results/asap7/*/base")


def macro_libs(env, kit):
    out = []
    for k in ("ADDITIONAL_LIBS", "TC_LIB_FILES"):
        for p in env.get(k, "").split():
            if p.endswith((".lib", ".lib.gz")) and "$(" not in p:
                q = kpath(kit, p)
                if q not in out:
                    out.append(q)
    return out


def lib_cells(path):
    op = gzip.open if str(path).endswith(".gz") else open
    with op(path, "rt", errors="replace") as f:
        return re.findall(r"^\s*cell\s*\(\s*\"?([A-Za-z_][\w$]*)\"?\s*\)", f.read(), flags=re.M)


def src_modules(path):
    try:
        t = Path(path).read_text(errors="replace")
    except OSError:
        return []
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    t = re.sub(r"//[^\n]*", " ", t)
    return re.findall(r"^\s*(?:\(\*.*?\*\)\s*)?(?:module|macromodule)\s+(?:automatic\s+|static\s+)?([A-Za-z_][\w$]*)",
                      t, flags=re.M)


def netlist_cell_types(path):
    """instance master names of a structural Verilog netlist (Yosys / OpenROAD write_verilog)."""
    t = Path(path).read_text(errors="replace")
    t = re.sub(r"\(\*.*?\*\)", " ", t, flags=re.S)
    return set(re.findall(r"^\s*([A-Za-z_][\w$]*)\s+(?:\\\S+|[A-Za-z_][\w$\[\]\.]*)\s*\(", t, flags=re.M)) - {
        "module", "input", "output", "wire", "assign", "inout", "reg"}


# ---------------------------------------------------------------------------------------------- yosys scripts
def top_params(env):
    t = env.get("VERILOG_TOP_PARAMS", "").split()
    return list(zip(t[0::2], t[1::2]))


def rtl_standard_libs(env, kit):
    """Resolve explicit ASAP7 cell instances in RTL to the real functional
    Liberty models, as on the gate side (e.g. ot_hdly's HB4xp67 buffer)."""
    referenced, defined = set(), set()
    for f in env["VERILOG_FILES"].split():
        p = kpath(kit, f)
        try:
            text = Path(p).read_text(errors="replace")
        except OSError:
            continue
        referenced.update(re.findall(r"\b[A-Za-z_]\w*_ASAP7_75t_[RLS]\b", text))
        defined.update(src_modules(p))
    needed = referenced - defined
    return [f"{NLDM}/{l}" for l in STD_LIBS if needed and needed.intersection(lib_cells(f"{NLDM}/{l}"))]


def read_rtl_cmds(env, kit, frontend, lib_bbs, chparam=True, slang_extra=()):
    """yosys commands reading the kit RTL with `frontend` ('verilog' | 'slang'); lib_bbs: macro liberty files whose
    cells have no Verilog body in the sources (read as blackbox cells); slang_extra: extra read_slang options."""
    files = [kpath(kit, f) for f in env["VERILOG_FILES"].split()]
    incs = [kpath(kit, d) for d in env.get("VERILOG_INCLUDE_DIRS", "").split()]
    defs = env.get("VERILOG_DEFINES", "").split()
    if "-DSYNTHESIS" not in defs:
        defs.append("-DSYNTHESIS")
    # Functional cells must never be replaced by free black-box outputs.
    cmds = [f"read_liberty -ignore_miss_func {l}" for l in rtl_standard_libs(env, kit)]
    cmds += [f"read_liberty -lib -ignore_miss_func {l}" for l in lib_bbs]
    if frontend == "slang":
        a = ["--keep-hierarchy", "--compat=vcs", "--ignore-assertions", "--top", env["DESIGN_NAME"]] + list(slang_extra)
        a += [f"-I{i}" for i in incs] + defs + files
        for k, v in top_params(env):
            a += ["-G", f"{k}={v}"]
        for m in env.get("SYNTH_BLACKBOXES", "").split():
            a += ["--blackboxed-module", m]
        for l in lib_bbs:
            for c in lib_cells(l):
                a += ["--blackboxed-module", c]
        cmds += ["read_slang " + " ".join(shlex.quote(x) for x in a), "setattr -unset init"]
    else:
        cmds += ["verilog_defaults -push", "verilog_defaults -add " + " ".join(defs)]
        cmds += ["read_verilog -defer -sv " + " ".join(f"-I{i}" for i in incs) + " " + f for f in files]
        cmds += ["verilog_defaults -pop"]
        if chparam:
            cmds += [f"chparam -set {k} {v} {env['DESIGN_NAME']}" for k, v in top_params(env)]
    return cmds


SEQ_TAIL = [
    # every flop: named after the register bit it drives (ORFS synth.tcl does the same before dfflibmap)
    "rename -wire t:$_*DFF*_ t:$_*FF*_",
    "async2sync", "dffunmap",
    "select -assert-none t:$_DLATCH* t:$_SR_* t:$_ALDFF* t:$_DFFSRE*",
    "techmap -map {lecff} t:$_DFF_P_ t:$_DFF_N_", "simplemap t:$dff",
    "opt_clean", "splitnets -ports",
    "setundef -undriven -anyseq", "setundef -anyseq", "setundef -zero -init",
    "aigmap", "opt_clean", "stat",
    "write_aiger -zinit -map {out}.map {out}.aig",
]


def gold_script(env, kit, frontend, lib_bbs, stubs, wrap, lecff, out):
    s = read_rtl_cmds(env, kit, frontend, lib_bbs, chparam=False)
    s += [f"read_verilog -overwrite {stubs}", f"read_verilog {wrap}", f"hierarchy -check -top {WRAP}",
          # declared kept registers (the kept-register check): (* keep *) wires and every wire of a keep_hierarchy
          # module (pin / replica flop cells), marked before the hierarchy attributes are dropped
          "setattr -set lec_keep 1 w:* a:keep %i", "setattr -set lec_keep 1 A:keep_hierarchy",
          "setattr -mod -unset keep_hierarchy", "setattr -unset keep_hierarchy", "proc",
          # constant folding / width reduction that keeps don't-care semantics (-keepdc), per module before
          # flatten, and peepopt (shiftmul / shiftadd: a dynamic part-select full[276 * f + b] becomes a mux of the
          # constant-stride slices instead of a 32-stage x-filled barrel shifter): without them eng_rr_e's 552
          # strided selects expand to 31M cells (77 GB) in techmap; with them 263k cells, 1.2 GB
          "opt_expr -keepdc", "opt_clean", "wreduce -keepdc", "peepopt", "opt_clean", "wreduce -keepdc", "opt_clean",
          "flatten -noscopeinfo", "opt_clean", f"select -write {out}.keep w:* a:lec_keep %i",
          # -nordff: memory_dff would merge an address / data register into a synchronous read port, and memory_map
          # then re-creates it as an anonymous '$...$rdreg' flop that no key point names (kv3_astk zn sd[k]: the
          # zq[5:2] address register became 4 unnamed gold latches, so every oa bit was UNPROVEN); the reference keeps
          # the RTL registers as written and an asynchronous read port
          "memory -nomap -nordff", "memory_map", "opt_expr -keepdc", "opt_clean",
          "techmap", "opt_clean"]
    return "\n".join(s + [c.format(lecff=lecff, out=out) for c in SEQ_TAIL]) + "\n"


def gate_script(env, netlist, stubs, wrap, lecff, out):
    s = [f"read_liberty -ignore_miss_func {NLDM}/{l}" for l in STD_LIBS]
    s += [f"read_verilog {stubs}", f"read_verilog {netlist}", f"read_verilog {wrap}", f"hierarchy -check -top {WRAP}",
          "setattr -mod -unset keep_hierarchy", "setattr -unset keep_hierarchy", "proc", "flatten -noscopeinfo", "opt_clean", "techmap", "opt_clean"]
    return "\n".join(s + [c.format(lecff=lecff, out=out) for c in SEQ_TAIL]) + "\n"


IMPLICIT_NET = re.compile(r"^(\S+?):(\d+):\d+: warning: implicit net '([^']+)' created \[-Wimplicit-net\]")


def implicit_net_lint(env, kit, lib_bbs, out, log):
    """lint gate (LEC 10-25): an identifier used before its declaration (or never declared) in a port connection
    becomes an implicit 1-bit net.  yosys-slang (--compat=vcs, the synthesis frontend) leaves that net undriven
    while read_verilog binds the later declaration: ot_s81eng_aq_n32 g_ec .ep_next(ep_next) tied 8 exponent
    registers to 0 in every synthesised eng netlist.  Industry practice (`default_nettype none`, lint
    UndrivenNet / implicit-net rules): any implicit net fails the kit.  Returns [(file, line, net)]."""
    s = read_rtl_cmds(env, kit, "slang", lib_bbs, slang_extra=["-Wimplicit-net"])
    run_yosys("\n".join(s) + "\n", out / "lint.ys", log)
    hits = []
    for l in Path(str(out / "lint.ys") + ".log").read_text(errors="replace").splitlines():
        m = IMPLICIT_NET.match(l.strip())
        if m and (m[1], m[2], m[3]) not in hits:
            hits.append((m[1], m[2], m[3]))
    return hits


def bb_script(env, kit, frontend, lib_bbs, out):
    """pre-pass: elaborate the gold RTL and write every black-box module (ports only) as JSON."""
    s = read_rtl_cmds(env, kit, frontend, lib_bbs)
    s += [f"hierarchy -check -top {env['DESIGN_NAME']}"]
    s += [f"blackbox {m}" for m in env.get("SYNTH_BLACKBOXES", "").split()]
    s += ["select =A:blackbox", f"write_verilog -blackboxes -noattr -selected {out}.v", "select -clear",
          f"blackbox {env['DESIGN_NAME']}", f"select ={env['DESIGN_NAME']}",
          f"write_verilog -blackboxes -noattr -selected {out}_top.v"]
    return "\n".join(x for x in s if x) + "\n"


def parse_bb_verilog(path):
    """yosys write_verilog of blackbox modules -> {module: [(port, dir, width)]}"""
    t = Path(path).read_text() if Path(path).is_file() else ""
    t = re.sub(r"\(\*.*?\*\)", " ", t, flags=re.S)
    mods = {}
    for m in re.finditer(r"module\s+(\\\S+|[\w$]+)\s*\((.*?)\);(.*?)endmodule", t, flags=re.S):
        name = m[1].lstrip("\\")
        order = [p.strip().lstrip("\\") for p in m[2].replace("\n", " ").split(",") if p.strip()]
        decl = {}
        for d in re.finditer(r"^\s*(input|output|inout)\s+(?:wire\s+|reg\s+)?(?:\[(\d+):(\d+)\]\s*)?(\\\S+|[\w$]+)\s*;",
                             m[3], flags=re.M):
            w = abs(int(d[2]) - int(d[3])) + 1 if d[2] is not None else 1
            lo = min(int(d[2]), int(d[3])) if d[2] is not None else 0
            decl[d[4].lstrip("\\")] = (d[1], w, lo)
        mods[name] = [(p,) + decl[p] for p in order if p in decl]
    return mods


def stub_verilog(bbports):
    """{module: [(port, dir, width, lsb)]} -> stubs identical for gold and gate: input bits land on keep flops
    '<inst>.lec_bbi_<pin>[i]' (compare points), output bits come from free self-loop flops '<inst>.lec_bbo_<pin>[i]'
    (shared inputs)."""
    out = ["// GENERATED by tools/die_plan/lec.py: black-box stubs (input pins = compare points, outputs = free)"]
    for mod, ports in sorted(bbports.items()):
        out.append(f"module \\{mod} ({', '.join(esc(p) for p, *_ in ports)});")
        out.append("  wire lec_clk;")
        for p, d, w, lo in ports:
            rng = f"[{lo + w - 1}:{lo}] " if w > 1 or lo else ""
            if d == "input":
                out += [f"  input {rng}{esc(p)};", f"  (* keep *) reg {rng}{esc(BB + 'i_' + p)};",
                        f"  always @(posedge lec_clk) {esc(BB + 'i_' + p)} <= {esc(p)};"]
            elif d == "output":
                out += [f"  output {rng}{esc(p)};", f"  (* keep *) reg {rng}{esc(BB + 'o_' + p)};",
                        f"  always @(posedge lec_clk) {esc(BB + 'o_' + p)} <= {esc(BB + 'o_' + p)};",
                        f"  assign {esc(p)} = {esc(BB + 'o_' + p)};"]
            else:
                raise Unproven(f"black box {mod}: inout pin {p} (not modelled)")
        out.append("endmodule")
    return "\n".join(out) + "\n"


def wrapper_verilog(top, ports, params=()):
    """lec_top: inputs fed through, every output port bit captured by a keep flop 'lec_po_<port>[i]' (D = the output
    function: a constant output keeps its name, which write_aiger's port map would drop)."""
    ins = [(p, w, lo) for p, d, w, lo in ports if d == "input"]
    outs = [(p, w, lo) for p, d, w, lo in ports if d == "output"]
    if any(d not in ("input", "output") for p, d, w, lo in ports):
        raise Unproven(f"top {top}: inout ports are not modelled")
    rng = lambda w, lo: f"[{lo + w - 1}:{lo}] " if w > 1 or lo else ""
    o = [f"// GENERATED by tools/die_plan/lec.py: LEC wrapper of {top}",
         f"module {WRAP}({', '.join(esc(p) for p, w, lo in ins)});", "  wire lec_clk;"]
    o += [f"  input {rng(w, lo)}{esc(p)};" for p, w, lo in ins]
    o += [f"  wire {rng(w, lo)}{esc('lec_o_' + p)};" for p, w, lo in outs]
    par = (" #(" + ", ".join(f".{k}({v})" for k, v in params) + ")") if params else ""
    con = [f".{esc(p)}({esc(p)})" for p, w, lo in ins] + [f".{esc(p)}({esc('lec_o_' + p)})" for p, w, lo in outs]
    o.append(f"  \\{top} {par} u_dut ({', '.join(con)});")
    for p, w, lo in outs:
        o += [f"  (* keep *) reg {rng(w, lo)}{esc('lec_po_' + p)};",
              f"  always @(posedge lec_clk) {esc('lec_po_' + p)} <= {esc('lec_o_' + p)};"]
    o.append("endmodule")
    return "\n".join(o) + "\n"


def esc(n):
    return n if re.fullmatch(r"[A-Za-z_][\w$]*", n) else f"\\{n} "


# ---------------------------------------------------------------------------------------------- AIGER
def read_aig(path):
    """binary AIGER 'aig M I L O A' -> dict(I, L, O, A, latches [next], outputs [lit], ands array [r0, r1, ...])"""
    buf = Path(path).read_bytes()
    nl = buf.index(b"\n")
    hdr = buf[:nl].split()
    if hdr[0] != b"aig":
        raise LecError(f"{path}: not binary AIGER")
    M, I, L, O, A = (int(x) for x in hdr[1:6])
    if any(int(x) for x in hdr[6:]):
        raise LecError(f"{path}: AIGER with B/C/J/F sections")
    pos = nl + 1
    latches, outputs = [], []
    for lst, n in ((latches, L), (outputs, O)):
        for _ in range(n):
            e = buf.index(b"\n", pos)
            lst.append(int(buf[pos:e].split()[0]))
            pos = e + 1
    ands = array("q", bytes(16 * A))
    lhs = 2 * (I + L)
    for k in range(A):
        lhs += 2
        x = i = 0
        while True:
            b = buf[pos]; pos += 1
            x |= (b & 0x7F) << (7 * i); i += 1
            if not b & 0x80:
                break
        r0 = lhs - x
        x = i = 0
        while True:
            b = buf[pos]; pos += 1
            x |= (b & 0x7F) << (7 * i); i += 1
            if not b & 0x80:
                break
        ands[2 * k] = r0
        ands[2 * k + 1] = r0 - x
    return dict(I=I, L=L, O=O, A=A, latches=latches, outputs=outputs, ands=ands)


def read_map(path):
    """yosys write_aiger -map -> {'input'|'output'|'latch': {index: [(name, bit), ...]}}"""
    m = {"input": {}, "output": {}, "latch": {}}
    for line in Path(path).read_text().splitlines():
        f = line.split(" ", 3)
        if len(f) == 4 and f[0] in m:
            m[f[0]].setdefault(int(f[1]), []).append((f[3], int(f[2])))
    return m


def flop_key(name):
    """'<reg>[b]$_T_.lecq' (gold, or gate stub) / '<reg>[b]$_T_.IQN$_T2_.lecq' (gate liberty flop) ->
    (key, inverted).  ASAP7 IQN state = !D (next_state "!D"); IQ / IQNN hold D."""
    if not name.endswith(".lecq"):
        return None, False
    n = TYPE_SFX.sub("", name[:-5])
    inv = False
    v = VAR_SFX.search(n)
    if v:
        inv = v[1] == "IQN"
        n = TYPE_SFX.sub("", n[:v.start()])
    # OpenROAD-exported netlists (3_place / 6_final) keep the hierarchy separator '/' in flop names
    return n.replace("\\", "").replace(" ", "").replace("/", "."), inv


def port_key(n, b):
    """map port entry -> 'name[bit]' (splitnets -ports already wrote 'name[bit]' wires)."""
    return n if re.search(r"\[\d+\]$", n) else f"{n}[{b}]"


def key_points(aig, amap):
    """-> pis {key: lit of the logical value}, cps {key: lit}, free (unnamed) input lits, anonymous latch lits."""
    I = aig["I"]
    pis, cps, xs, anon, alias = {}, {}, [], [], {}
    for idx, names in amap["input"].items():
        pis["pi:" + port_key(*names[0])] = 2 * (idx + 1)
    for idx in range(I):
        if idx not in amap["input"]:
            xs.append(2 * (idx + 1))            # $anyseq (X / undriven) inputs: free, don't-care
    for idx in range(aig["L"]):
        lit, nxt = 2 * (I + idx + 1), aig["latches"][idx]
        key, inv = None, False
        for n, b in amap["latch"].get(idx, ()):
            key, inv = flop_key(n)
            if key:
                break
        if not key:
            anon.append((lit, nxt))
            continue
        if key.startswith("lec_po_"):          # wrapper output capture: compare point only
            cps["po:" + key[7:]] = nxt
            continue
        nk = GENBLK.sub("", key)          # unnamed generate scopes: read_verilog 'genblk1.', slang none
        if "ff:" + nk not in pis:
            key = nk
        if "ff:" + key in pis:
            raise LecError(f"duplicate flop key {key}")
        if f".{BB}i_" in key:                   # black-box input pin: compare point only
            cps["bb:" + key] = nxt
            continue
        if f".{BB}o_" in key:                   # black-box output pin: shared free input only
            pis["bb:" + key] = lit
            continue
        pis["ff:" + key] = lit ^ inv
        cps["ff:" + key] = nxt ^ inv
        if not inv:            # other public wires on the same (logical) Q net: alias names of this register
            al = set()
            for n, b in amap["latch"].get(idx, ()):
                if "$" in n or n.endswith(".lecq") or "." + BB in n:
                    continue
                n = GENBLK.sub("", n.replace("\\", "").replace(" ", ""))
                al.add("ff:" + (n if re.search(r"\[\d+\]$", n) else f"{n}[{b}]"))
                if b == 0:
                    al.add("ff:" + n)
            alias["ff:" + key] = al
    return pis, cps, xs, anon, alias


class Aig:
    """AIG builder (inputs first, then structurally hashed ands; literal 0 = false)."""

    def __init__(self):
        self.ni = 0
        self.inames = []
        self.ands = array("q")
        self.outs, self.onames = [], []
        self.strash = {}
        self.parity_expr, self.parity_cache = {}, {}

    def add_input(self, name):
        if self.ands:
            raise LecError("inputs after ands")
        self.ni += 1
        self.inames.append(name)
        return 2 * self.ni

    def AND(self, a, b):
        # ~(x & y) & ~(~x & ~y) == x ^ y. Recognise the AIG XOR
        # encoding while importing both frontends so differently factored CRC
        # matrices share one GF(2) expression before SAT (no assumptions).
        if a & 1 and b & 1 and a > 1 and b > 1:
            ia, ib = (a >> 1) - self.ni - 1, (b >> 1) - self.ni - 1
            if ia >= 0 and ib >= 0:
                x = self.ands[2 * ia:2 * ia + 2]
                y = self.ands[2 * ib:2 * ib + 2]
                if set(x) == {v ^ 1 for v in y}:
                    return self.XOR(*x)
        return self._and(a, b)

    def _and(self, a, b):
        if a < b:
            a, b = b, a
        if b == 0 or a == (b ^ 1):
            return 0
        if b == 1 or a == b:
            return a
        r = self.strash.get((a, b))
        if r is None:
            self.ands.append(a)
            self.ands.append(b)
            r = 2 * (self.ni + len(self.ands) // 2)
            self.strash[(a, b)] = r
        return r

    def _parity(self, a):
        if a <= 1:
            return frozenset(), a
        if a in self.parity_expr:
            return self.parity_expr[a]
        if a ^ 1 in self.parity_expr:
            terms, const = self.parity_expr[a ^ 1]
            return terms, const ^ 1
        return frozenset([a & ~1]), a & 1

    def XOR(self, a, b):
        aa, ac = self._parity(a)
        bb, bc = self._parity(b)
        terms, const = aa ^ bb, ac ^ bc
        if not terms:
            return const
        if terms in self.parity_cache:
            return self.parity_cache[terms] ^ const

        def build(ts):
            if len(ts) == 1:
                return ts[0]
            mid = len(ts) // 2
            x, y = build(ts[:mid]), build(ts[mid:])
            r = self._and(self._and(x, y ^ 1) ^ 1, self._and(x ^ 1, y) ^ 1) ^ 1
            self.parity_expr[r] = (frozenset(ts), 0)
            return r

        r = build(sorted(terms))
        self.parity_expr[r] = (terms, 0)
        self.parity_cache[terms] = r
        return r ^ const

    def write(self, path, outs=None):
        outs = self.outs if outs is None else outs
        A, I = len(self.ands) // 2, self.ni
        out = bytearray(f"aig {I + A} {I} 0 {len(outs)} {A}\n".encode())
        out += "".join(f"{o}\n" for o in outs).encode()
        lhs = 2 * I
        ands = self.ands
        for k in range(A):
            lhs += 2
            r0, r1 = ands[2 * k], ands[2 * k + 1]
            for d in (lhs - r0, r0 - r1):
                while d > 0x7F:
                    out.append((d & 0x7F) | 0x80)
                    d >>= 7
                out.append(d)
        Path(path).write_bytes(bytes(out))

    def cone_inputs(self, lit):
        seen, stack, ins = set(), [lit >> 1], set()
        while stack:
            v = stack.pop()
            if v == 0 or v in seen:
                continue
            seen.add(v)
            if v <= self.ni:
                ins.add(v)
            else:
                k = v - self.ni - 1
                stack += (self.ands[2 * k] >> 1, self.ands[2 * k + 1] >> 1)
        return ins

    def near_inputs(self, lit, depth):
        """the inputs / registers within `depth` AND levels of `lit` (a hold mux puts its own Q at depth <= 3)."""
        seen, front, ins = set(), [lit >> 1], set()
        for _ in range(depth + 1):
            nxt = []
            for v in front:
                if v == 0 or v in seen:
                    continue
                seen.add(v)
                if v <= self.ni:
                    ins.add(v)
                else:
                    k = v - self.ni - 1
                    nxt += (self.ands[2 * k] >> 1, self.ands[2 * k + 1] >> 1)
            front = nxt
        return ins

    def simulate(self, words, seed=1, flip=()):
        """bit-parallel random simulation (python ints of `words` x 64 bits) -> value list per variable.
        `flip`: input variables whose random values are complemented (the same patterns otherwise)."""
        import random
        rnd = random.Random(seed)
        W = 64 * words
        mask = (1 << W) - 1
        val = [0] * (self.ni + len(self.ands) // 2 + 1)
        for v in range(1, self.ni + 1):
            val[v] = rnd.getrandbits(W) ^ (mask if v in flip else 0)
        a = self.ands
        base = self.ni + 1
        for k in range(len(a) // 2):
            r0, r1 = a[2 * k], a[2 * k + 1]
            x = val[r0 >> 1] ^ (mask if r0 & 1 else 0)
            y = val[r1 >> 1] ^ (mask if r1 & 1 else 0)
            val[base + k] = x & y
        return val, mask


def lit_val(val, mask, lit):
    return val[lit >> 1] ^ (mask if lit & 1 else 0)


class Lec:
    """gold / gate key points + register correspondence hypotheses -> miter AIGs."""

    def __init__(self, gold, gmap, gate, tmap, port_map=None):
        self.gold, self.gate = gold, gate
        self.gp, self.gc, self.gx, self.ganon, galias = key_points(gold, gmap)
        self.tp, self.tc, self.tx, self.tanon, _ = key_points(gate, tmap)
        # a gold register whose Q net also carries the name the gate flop was given (synthesis named the flop after
        # an alias, e.g. the output port it drives): re-key it to that name
        tfree = set(self.tp) - set(self.gp)
        self.aliased = []
        for k in sorted(set(self.gp) - set(self.tp)):
            hit = sorted(galias.get(k, set()) & tfree)
            if len(hit) == 1 and hit[0] not in self.gp:
                self.gp[hit[0]] = self.gp.pop(k)
                self.gc[hit[0]] = self.gc.pop(k)
                tfree.discard(hit[0])
                self.aliased.append(f"{k}->{hit[0]}")
        if port_map:
            ren = lambda d: {(k[:3] + port_map.get(k[3:], k[3:])) if k[:3] in ("pi:", "po:") else k: v
                             for k, v in d.items()}
            self.tp, self.tc = ren(self.tp), ren(self.tc)
        # arrays the two frontends lay out differently (read_verilog mem[i][bit] vs slang mem[h][flat]) match some
        # names by accident: when a gate base name carries an index tuple the gold side does not have, none of its
        # names are trusted; the gate keys are re-keyed (base#t) and paired by function (array_maps / signatures)
        gidx, tidx = {}, {}
        for d, src in ((gidx, self.gp), (tidx, self.tp)):
            for k in src:
                m = IDX.match(k)
                if k.startswith("ff:") and m:
                    d.setdefault(m.group(1), set()).add(m.group(2))
        self.relaid = sorted(b for b in tidx if b in gidx and not tidx[b] <= gidx[b])
        for b in self.relaid:
            for ix in tidx[b]:
                self.tp[f"{b}#t{ix}"] = self.tp.pop(b + ix)
                self.tc[f"{b}#t{ix}"] = self.tc.pop(b + ix)
        self.matched = sorted(set(self.gp) & set(self.tp))
        self.gonly = sorted(k for k in set(self.gp) - set(self.tp))
        self.tonly = sorted(k for k in set(self.tp) - set(self.gp))
        # hypotheses on unmatched flops: key -> ('const', c) | ('eq', side, other_key, inv)
        self.hyp = {}
        # state-encoding constraints (FSM recoding): (side, keys, allowed value tuples) assumed on the current state
        # and proved on the next state together with the hypotheses (an inductive invariant like the others)
        self.cons = []

    def build(self, with_compare=True, with_hyp=True, extra=None, free_const=None, hold_matched=()):
        """one AIG with every matched key point a shared input; a hypothesised gold-only flop becomes its constant /
        its partner's input; other unmatched key points and X sources are free inputs.  Outputs: XOR per matched
        compare point (with_compare) and per hypothesis (D(flop) vs constant / partner's D).
        The RTL's X is a don't care (the Conformal / Formality default): the gold side also carries an X rail
        (ternary: an X source is X, an AND is X unless an input is a definite 0); a compare output is
        (gold != gate) & gold-not-X, and a hypothesis on an RTL register whose next state is X holds (the register
        may take the value synthesis chose)."""
        m = Aig()
        kind = {}
        lg, lt = {0: 0}, {0: 0}
        lgx = {}                                  # gold node -> literal "this node is X" (absent = 0)

        def bind(lmap, lit, v):
            lmap[lit & ~1] = v ^ (lit & 1)

        shared = {}
        merged = []
        for k in self.matched:
            h = self.hyp.get(("both", k))
            if h and h[0] == "const":             # matched flop proved constant (both sides)
                shared[k] = h[1]
                bind(lg, self.gp[k], h[1])
                bind(lt, self.tp[k], h[1])
                continue
            if h:                                 # register correspondence among matched flops: k == representative
                merged.append(k)
                continue
            if free_const is not None and k in hold_matched:
                shared[k] = free_const            # cofactor: these matched registers held at the constant too
                bind(lg, self.gp[k], free_const)
                bind(lt, self.tp[k], free_const)
                continue
            v = m.add_input(k)
            kind[v >> 1] = ("matched", k)
            shared[k] = v
            bind(lg, self.gp[k], v)
            bind(lt, self.tp[k], v)
        while merged:                             # chains (rep itself merged later) resolve in passes
            nxt = []
            for k in merged:
                _, _, rep, inv = self.hyp[("both", k)]
                if rep not in shared:
                    nxt.append(k)
                    continue
                shared[k] = shared[rep] ^ inv
                bind(lg, self.gp[k], shared[k])
                bind(lt, self.tp[k], shared[k])
            if len(nxt) == len(merged):
                for k in nxt:
                    self.hyp.pop(("both", k), None)
                raise LecError("cyclic flop hypotheses (rebuild)")
            merged = nxt
        later = []
        for side, keys, p, lmap in (("gold", self.gonly, self.gp, lg), ("gate", self.tonly, self.tp, lt)):
            for k in keys:
                h = self.hyp.get((side, k))
                if h and h[0] == "const":
                    bind(lmap, p[k], h[1])
                elif h and h[0] in ("eq", "cube"):
                    later.append((side, k, h))
                elif free_const is not None and k.startswith("ff:"):
                    bind(lmap, p[k], free_const)  # cofactor: unpaired registers held at a constant
                else:
                    v = m.add_input(f"{side}:{k}")
                    kind[v >> 1] = (side + "_only", k)
                    bind(lmap, p[k], v)
        # hypotheses 'eq': bind to the partner's (already bound) value; chains resolve in passes, cycles are dropped
        cubes = []
        while later:
            nxt = []
            for side, k, h in later:
                if h[0] == "cube":                 # bound after the X inputs (ANDs come after every input)
                    cubes.append((side, k, h))
                    continue
                _, oside, ok, inv = h
                olmap, op = (lg, self.gp) if oside == "gold" else (lt, self.tp)
                if ok in shared:
                    v = shared[ok]
                elif (op[ok] & ~1) in olmap:
                    v = olmap[op[ok] & ~1] ^ (op[ok] & 1)
                    # a cross-side pair (gate register == gold register) is one register; a gold-only replica
                    # cohort bound to a gold-only representative that is itself still free stays gold_only
                    if v > 1 and oside != side and kind.get(v >> 1, ("",))[0].endswith("_only"):
                        kind[v >> 1] = ("paired", ok)
                else:
                    nxt.append((side, k, h))
                    continue
                lmap, p = (lg, self.gp) if side == "gold" else (lt, self.tp)
                bind(lmap, p[k], v ^ inv)
            if len(nxt) == len(later):
                for side, k, h in nxt:          # cyclic partners: drop the hypothesis, free input
                    self.hyp.pop((side, k), None)
                raise LecError("cyclic flop hypotheses (rebuild)")
            later = nxt
        for side, xs, anon, lmap in (("gold", self.gx, self.ganon, lg), ("gate", self.tx, self.tanon, lt)):
            for lit in xs:
                v = m.add_input(f"{side}:x{lit >> 1}")
                kind[v >> 1] = (side + "_x", f"x{lit >> 1}")
                bind(lmap, lit, v)
                if side == "gold":
                    lgx[lit & ~1] = 1
            for lit, _ in anon:
                v = m.add_input(f"{side}:anon{lit >> 1}")
                kind[v >> 1] = (side + "_anon", f"anon{lit >> 1}")
                bind(lmap, lit, v)
        for side, k, h in cubes:                  # gate one-hot state bit == (gold state vector == code)
            _, oside, oks, ovals = h
            olmap, op = (lg, self.gp) if oside == "gold" else (lt, self.tp)
            v = 1
            for ok, ov in zip(oks, ovals):
                v = m.AND(v, olmap[op[ok] & ~1] ^ (op[ok] & 1) ^ (ov ^ 1))
            lmap, p = (lg, self.gp) if side == "gold" else (lt, self.tp)
            bind(lmap, p[k], v)
        for d, lmap in ((self.gold, lg), (self.gate, lt)):
            base = 2 * (d["I"] + d["L"])
            a = d["ands"]
            ternary = d is self.gold
            for k in range(d["A"]):
                r0, r1 = a[2 * k], a[2 * k + 1]
                va, vb = lmap[r0 & ~1] ^ (r0 & 1), lmap[r1 & ~1] ^ (r1 & 1)
                lmap[base + 2 * (k + 1)] = m.AND(va, vb)
                if ternary:
                    xa, xb = lgx.get(r0 & ~1, 0), lgx.get(r1 & ~1, 0)
                    if xa or xb:
                        zero = m.AND(m.AND(va ^ 1, xa ^ 1) ^ 1, m.AND(vb ^ 1, xb ^ 1) ^ 1)   # no definite 0
                        lgx[base + 2 * (k + 1)] = m.AND(zero, m.AND(xa ^ 1, xb ^ 1) ^ 1)
        G = lambda lit: lg[lit & ~1] ^ (lit & 1)
        T = lambda lit: lt[lit & ~1] ^ (lit & 1)
        self.dlit = {}
        for k in self.gc:
            self.dlit[("gold", k)] = G(self.gc[k])
        for k in self.tc:
            self.dlit[("gate", k)] = T(self.tc[k])
        nx = lambda k: lgx.get(self.gc[k] & ~1, 0) ^ 1          # gold next state of k is not X
        self.xpoints = sorted(k for k in self.gc if lgx.get(self.gc[k] & ~1, 0))
        if with_compare:
            for k in sorted(set(self.gc) & set(self.tc)):
                m.outs.append(m.AND(m.XOR(G(self.gc[k]), T(self.tc[k])), nx(k)))
                m.onames.append(k)
        if with_hyp:
            for (side, k), h in sorted(self.hyp.items()):
                if side == "both" and h[0] == "const":
                    m.outs.append(m.AND(self.dlit[("gold", k)] ^ h[1], nx(k)))
                    m.onames.append(f"hyp:both:{k}")
                    m.outs.append(self.dlit[("gate", k)] ^ h[1])
                    m.onames.append(f"hyp:bothg:{k}")
                    continue
                if side == "both":
                    _, _, rep, inv = h
                    m.outs.append(m.AND(m.XOR(self.dlit[("gold", k)], self.dlit[("gold", rep)] ^ inv), nx(k)))
                    m.onames.append(f"hyp:both:{k}")
                    m.outs.append(m.XOR(self.dlit[("gate", k)], self.dlit[("gate", rep)] ^ inv))
                    m.onames.append(f"hyp:bothg:{k}")
                    continue
                d = self.dlit[(side, k)]
                if h[0] == "cube":
                    _, oside, oks, ovals = h
                    c = 1
                    for ok, ov in zip(oks, ovals):
                        c = m.AND(c, self.dlit[(oside, ok)] ^ (ov ^ 1))
                    m.outs.append(m.XOR(d, c))
                    m.onames.append(f"hyp:{side}:{k}")
                    continue
                if h[0] == "const":
                    m.outs.append(m.AND(d ^ h[1], nx(k)) if side == "gold" else d ^ h[1])
                else:
                    _, oside, ok, inv = h
                    od = self.dlit[(oside, ok)] if (oside, ok) in self.dlit else self.dlit[("gold", ok)]
                    # an RTL register (k, or the gate register's gold partner ok) loaded with X may hold either;
                    # a gate register paired with another gate register (gate-side replica cohort, possibly a
                    # re-keyed base#t[i] name with no gold next state) has no RTL X to honour
                    xm = nx(k) if side == "gold" else (nx(ok) if oside == "gold" and ok in self.gc else 1)
                    m.outs.append(m.AND(m.XOR(d, od ^ inv), xm))
                m.onames.append(f"hyp:{side}:{k}")
        if self.cons:
            def member(lits, allowed):
                v = 0
                for vals in allowed:
                    c = 1
                    for l, b in zip(lits, vals):
                        c = m.AND(c, l ^ (b ^ 1))
                    v = m.AND(v ^ 1, c ^ 1) ^ 1
                return v
            cur = lambda sd, k: G(self.gp[k]) if sd == "gold" else T(self.tp[k])
            assume = 1
            for sd, keys, allowed in self.cons:
                assume = m.AND(assume, member([cur(sd, k) for k in keys], allowed))
            m.outs = [m.AND(o, assume) for o in m.outs]
            for sd, keys, allowed in self.cons:
                m.outs.append(m.AND(assume, member([self.dlit[(sd, k)] for k in keys], allowed) ^ 1))
                m.onames.append(f"cons:{sd}:{keys[0]}")
        return m, kind


def abc_bin():
    for c in (ORFS + "/tools/install/yosys/bin/yosys-abc", shutil.which("yosys-abc") or ""):
        if c and os.access(c, os.X_OK):
            return c
    raise LecError("yosys-abc not found")


def aig_outputs(path):
    """output literals of a binary AIGER (header + output section only)."""
    with open(path, "rb") as f:
        hdr = f.readline().split()
        I, L, O = int(hdr[2]), int(hdr[3]), int(hdr[4])
        for _ in range(L):
            f.readline()
        return [int(f.readline().split()[0]) for _ in range(O)]


def xor_sat(m, ids, log):
    """Optional XOR-aware SAT for CRC/status cones ABC leaves undecided.

    Keep the complete original AIG CNF for every cone. Native XOR equations
    are redundant exact identities from the Boolean normaliser, never design
    assumptions. If pycryptosat is absent the caller retains UNDECIDED.
    """
    if os.environ.get("LEC_SOLVER_PATH") and os.environ["LEC_SOLVER_PATH"] not in sys.path:
        sys.path.append(os.environ["LEC_SOLVER_PATH"])       # pycryptosat (cp310 wheel extracted), see via_docker
    try:
        import pycryptosat
    except ImportError:
        return {}
    need = set()
    stack = [m.outs[i] >> 1 for i in ids]
    while stack:
        v = stack.pop()
        if not v or v in need:
            continue
        need.add(v)
        if v > m.ni:
            k = v - m.ni - 1
            stack.extend(t >> 1 for t in m.ands[2 * k:2 * k + 2])
    solver = pycryptosat.Solver(threads=1)
    if need:
        # Also declare a cone consisting solely of an unconstrained input.
        solver.add_clause([max(need), -max(need)])

    def clause(lits):
        if 1 not in lits:
            solver.add_clause([-(x >> 1) if x & 1 else x >> 1 for x in lits if x > 1])

    for k in range(len(m.ands) // 2):
        n = 2 * (m.ni + k + 1)
        if n >> 1 not in need:
            continue
        x, y = m.ands[2 * k:2 * k + 2]
        clause([n ^ 1, x])
        clause([n ^ 1, y])
        clause([n, x ^ 1, y ^ 1])
    nx = 0
    for lit, (terms, const) in m.parity_expr.items():
        if lit >> 1 not in need or any(t >> 1 not in need for t in terms):
            continue
        vs = collections.Counter([lit >> 1] + [t >> 1 for t in terms])
        vs = [v for v, n in vs.items() if n & 1]
        rhs = bool(const ^ (lit & 1))
        if not vs:
            if rhs:
                raise LecError("inconsistent Boolean XOR identity")
            continue
        solver.add_xor_clause(vs, rhs)
        nx += 1
    statuses = {}
    for i in ids:
        lit = m.outs[i]
        if lit <= 1:
            statuses[m.onames[i]] = "differs" if lit else "proved"
            continue
        start = time.time()
        sat, _ = solver.solve(assumptions=[-(lit >> 1) if lit & 1 else lit >> 1])
        statuses[m.onames[i]] = "proved" if sat is False else "differs" if sat is True else "undecided"
        log.append(f"XOR SAT {getattr(pycryptosat, '__version__', 'unknown')}: {m.onames[i]} "
                   f"{statuses[m.onames[i]]}, {len(need)} cone variables, {nx} redundant XORs, "
                   f"{time.time() - start:.3f}s")
    return statuses


def prove(m, work, conflicts, log, tag="miter", single_cap=2000):
    """per-output status {name: 'proved' | 'differs' | 'undecided'} of the miter outputs of builder m.
    ABC: &fraig (simulation + SAT sweeping of the shared gold / gate structure; proved outputs collapse to 0), then
    &sat -a -z on what is left (each output: UNSAT -> const 0, SAT -> counterexample kept).  When &sat leaves undefined
    outputs, random simulation marks the SAT ones and the rest are re-checked one cone at a time (&cone -O i;
    &cec -n -m) with 10x the conflicts on the cone query (no recursive per-node proof expansion)."""
    if not m.outs:
        return {}
    work = Path(work)
    miter, swept = work / f"{tag}.aig", work / f"{tag}_swept.aig"
    m.write(miter)
    abc = abc_bin()
    r = subprocess.run([abc, "-c", f"&r {miter}; &ps; &fraig -C {conflicts}; &ps; "
                                   f"&sat -a -z -v -C {conflicts * 10}; &ps; &w {swept}"],
                       capture_output=True, text=True)
    txt = r.stdout + r.stderr
    log.append(f"==== {tag}\n{txt}")
    if not swept.is_file():
        raise Unproven(f"ABC failed on {tag}: {txt[-300:]}")
    outs = aig_outputs(swept)
    if len(outs) != len(m.onames):
        raise LecError(f"ABC changed the output count of {tag}")
    st = {n: ("proved" if o == 0 else "left") for n, o in zip(m.onames, outs)}
    u = re.search(r"Undef calls\s+(\d+)", txt)
    undef = int(u[1]) if u else -1
    left = [i for i, o in enumerate(outs) if o != 0]
    if undef == 0:
        for i in left:
            st[m.onames[i]] = "differs" if outs[i] != 0 else "proved"
        # a constant-1 output is a difference too; non-constant ones were SAT in &sat -a
        return st
    # outputs &sat left undefined vs SAT ones are told apart by random simulation of the miter (a pattern that
    # sets the output is a counterexample); only the rest go to one cone at a time
    val, mask = m.simulate(8, seed=99)
    for i in left:
        st[m.onames[i]] = "differs" if lit_val(val, mask, m.outs[i]) else "undecided"
    left = [i for i in left if st[m.onames[i]] == "undecided"]
    pending = left[:single_cap]
    if pending:
        from concurrent.futures import ThreadPoolExecutor
        jobs = max(1, PROVE_JOBS)
        size = len(pending) if jobs == 1 else max(1, (len(pending) + jobs * 4 - 1) // (jobs * 4))
        batches = [pending[i:i+size] for i in range(0, len(pending), size)]
        def one_batch(ids):
            script = [f"&r {swept}; &cone -O {i}; &cec -n -m -C {conflicts * 10}" for i in ids]
            # one command per line in a script file (abc -f): a long batch passed as one -c argument exceeds the
            # kernel per-argument limit (MAX_ARG_STRLEN 128 KiB; OSError E2BIG on the 48k-output kvs_pc miters)
            sf = work / f"{tag}_cones_{ids[0]}_{ids[-1]}.abc"
            sf.write_text("\n".join(script) + "\n")
            r = subprocess.run([abc, "-f", str(sf)], capture_output=True, text=True)
            return ids, r.stdout + r.stderr
        with ThreadPoolExecutor(max_workers=jobs) as ex:
            for ids, t in ex.map(one_batch, batches):
                log.append(f"==== {tag} single cones {ids[0]}..{ids[-1]}\n{t}")
                # Naive SAT reports one aggregate line for a nontrivial cone; trivial
                # cones use the CEC sentence. Keep UNDECIDED in sequence: dropping it
                # would shift a later proof onto the wrong output.
                pat = (r"Networks are (NOT EQUIVALENT|equivalent|UNDECIDED)|"
                       r"UNSAT\s*=\s*(\d+)\.\s*SAT\s*=\s*(\d+)\.\s*UNDEC\s*=\s*(\d+)\.")
                res = []
                for hit in re.finditer(pat, t):
                    if hit[1]:
                        res.append({"NOT EQUIVALENT": "differs", "equivalent": "proved"}.get(hit[1], "undecided"))
                    else:
                        u, sat, undec = map(int, hit.group(2, 3, 4))
                        res.append("proved" if (u, sat, undec) == (1, 0, 0) else
                                   "differs" if (u, sat, undec) == (0, 1, 0) else "undecided")
                for i, status in zip(ids, res):
                    st[m.onames[i]] = status
    unknown = [i for i, n in enumerate(m.onames) if st[n] == "undecided"]
    if unknown:
        st.update(xor_sat(m, unknown, log))
    return st




def array_maps(gkeys, tkeys):
    """candidate name maps for arrays the two frontends lay out differently (read_verilog: mem[i][bit]; slang:
    mem[h][flat bit] ...): for a base name present on both sides with the same total bit count, the index tuples are
    flattened mixed-radix; variants with the outer index reversed on either side.  -> {base: [ {gold: gate} ...]}"""
    def split(keys):
        d = {}
        for k in keys:
            m = IDX.match(k)
            if m:
                d.setdefault(m.group(1), {})[k] = tuple(int(x) for x in re.findall(r"\d+", m.group(2)))
        return d
    G, T = split(gkeys), split(k.replace("#t[", "[") for k in tkeys)
    tname = {k.replace("#t[", "["): k for k in tkeys}
    out = {}
    for base in set(G) & set(T):
        g, t = G[base], T[base]
        if len(g) != len(t) or len({len(v) for v in g.values()}) != 1 or len({len(v) for v in t.values()}) != 1:
            continue

        def flats(d, rev):
            n = len(next(iter(d.values())))
            hi = [max(v[j] for v in d.values()) + 1 for j in range(n)]
            r = {}
            for k, v in d.items():
                f = 0
                for j in range(n):
                    x = (hi[j] - 1 - v[j]) if (rev and j == 0 and n > 1) else v[j]
                    f = f * hi[j] + x
                r[f] = k
            return r if len(r) == len(d) else None
        maps = []
        for gr in (False, True):
            for tr in (False, True):
                fg, ft = flats(g, gr), flats(t, tr)
                if fg and ft and set(fg) == set(ft):
                    maps.append({fg[f]: tname[ft[f]] for f in fg})
        if maps:
            out[base] = maps
    return out


def relayout(L, log, words=4, trials=64):
    """unpacked arrays: the two frontends may number the elements of `reg x [0:N-1]` in opposite order under the
    same names (read_verilog: element i = x[i]; slang: the flattened vector, element 0 at the MSB).  Greedy: for every
    array base whose matched compare points disagree in simulation, reverse the outer index on the gate side and keep
    it when clearly fewer matched compare points disagree (by 8, twice the array's bits and 1 % of the total) or the
    array's own compare points all agree after it.  A wrong choice can only produce a difference, never hide one (the
    mapping is a bijection of key points; everything is still proved)."""
    def mismatches():
        m, kind = L.build(with_compare=False, with_hyp=False)
        val, mask = m.simulate(words, seed=4242)
        bad = collections.Counter()
        for k in L.matched:
            mm = IDX.match(k)
            if k.startswith("ff:") and \
                    lit_val(val, mask, L.dlit[("gold", k)]) != lit_val(val, mask, L.dlit[("gate", k)]):
                bad[mm.group(1) if mm else k] += 1
        return bad

    def flip(base):
        keys = [k for k in L.matched if IDX.match(k) and IDX.match(k).group(1) == base]
        if not keys:
            return False
        idx = {k: tuple(int(x) for x in re.findall(r"\d+", IDX.match(k).group(2))) for k in keys}
        hi0 = max(v[0] for v in idx.values())
        rev = {k: base + "".join(f"[{x}]" for x in (hi0 - v[0],) + v[1:]) for k, v in idx.items()}
        if set(rev.values()) != set(keys) or all(rev[k] == k for k in keys):
            return False
        old_p = {k: L.tp[k] for k in keys}
        old_c = {k: L.tc[k] for k in keys if k in L.tc}
        for k in keys:                             # gold k <-> gate rev[k]
            L.tp[k] = old_p[rev[k]]
            if rev[k] in old_c:
                L.tc[k] = old_c[rev[k]]
        return True
    bad = mismatches()
    tried = set()
    for _ in range(trials):
        cand = [b for b, n in bad.most_common() if b not in tried and IDX.match(b + "[0]")]
        if not cand:
            return
        base = cand[0]
        tried.add(base)
        if not flip(base):
            continue
        new = mismatches()
        # a true reversal repairs a whole downstream cone (LLd cal_v: 4 bits, 368 -> 327 mismatches; wa_v 327 ->
        # 260); a few compare points either way is simulation noise (l5f: a 32-b output register 2475 -> 2471)
        size = sum(1 for k in L.matched if IDX.match(k) and IDX.match(k).group(1) == base)
        gain = sum(bad.values()) - sum(new.values())
        log.append(f"relayout trial: {base} ({size} b) mismatching compare points {sum(bad.values())} -> "
                   f"{sum(new.values())}, own {bad[base]} -> {new[base]}")
        if gain >= max(8, 2 * size, sum(bad.values()) // 100) or (gain > 0 and new[base] == 0 < bad[base]):
            log.append(f"relayout: {base} (outer index reversed on the gate side)")
            bad = new
            tried = {b for b in tried if b == base}
        else:
            flip(base)                             # undo (the reversal is an involution)


IDXK = re.compile(r"^(.*)\[(\d+)\]$")


def renamed(L, log, words=4):
    """a register vector synthesis narrowed (constant low bits dropped: r256 = {res_q, 8'd0}) keeps names that start
    at bit 0, so the gate's r[1][10] is the RTL's r[1][18]: when the matched bits of a vector disagree in simulation
    and most of the disagreeing gold bits simulate like a different gate bit of the same vector, the vector's gate
    names are not trusted (re-keyed base#t, paired by function like a re-laid array)."""
    m, kind = L.build(with_compare=False, with_hyp=False)
    val, mask = m.simulate(words, seed=5151)
    sv = lambda side, k: lit_val(val, mask, L.dlit[(side, k)])
    bases = collections.defaultdict(list)
    for k in L.matched:
        mm = IDX.match(k)
        if k.startswith("ff:") and mm:
            bases[mm.group(1)].append(k)
    hit = []
    for b, ks in bases.items():
        bad = [k for k in ks if sv("gold", k) != sv("gate", k) and sv("gold", k) not in (0, mask)]
        if len(bad) < 2:
            continue
        tsig = {}
        for k in ks:
            tsig.setdefault(sv("gate", k), set()).add(k)
        moved = sum(1 for k in bad if (tsig.get(sv("gold", k), set()) | tsig.get(sv("gold", k) ^ mask, set())) - {k})
        if 2 * moved >= len(bad):
            hit.append(b)
            log.append(f"renamed: {b} ({moved} of {len(bad)} disagreeing bits simulate like another gate bit)")
    for b in hit:
        for k in bases[b]:
            nk = f"{b}#t{k[len(b):]}"
            L.tp[nk] = L.tp.pop(k)
            if k in L.tc:
                L.tc[nk] = L.tc.pop(k)
    if hit:
        L.relaid = sorted(set(L.relaid) | set(hit))
        L.matched = sorted(set(L.gp) & set(L.tp))
        L.gonly = sorted(set(L.gp) - set(L.tp))
        L.tonly = sorted(set(L.tp) - set(L.gp))


def name_dist(a, b):
    """how far apart two key names are (differing tokens; digits compared as tokens): a gold copy of a merged register
    pairs with the copy of its own name shape (g_c[10].f[0] -> g_c[0].f[0], not g_ctl[1].u_c.g_c[0].f[0])"""
    ta, tb = re.split(r"(\d+)", a), re.split(r"(\d+)", b)
    if len(ta) != len(tb):
        return 1000 + abs(len(a) - len(b))
    return sum(x != y for x, y in zip(ta, tb))


def closest(k, cands, cap=512):
    return sorted(cands, key=lambda c: name_dist(k, c)) if len(cands) <= cap else cands


GENCOPY = re.compile(r"(?<![A-Za-z0-9_])g_[A-Za-z0-9_]+\[\d+\]")


def replica_proposals(L, log):
    """Propose interchangeable generated-register cohorts on both designs.

    The input-support fingerprint keeps primary/black-box inputs distinct;
    current-state dependencies may be interchangeable generated feedback copies.
    This is only candidate discovery: both designs' next-state relations still
    pass through the normal simultaneous inductive SAT proof/refinement.
    """
    norm = lambda k: GENCOPY.sub(lambda m: m[0].split("[")[0] + "[]", k)
    symbols = {}
    def sym(k):
        if k not in symbols:
            symbols[k] = 1 << len(symbols)
        return symbols[k]
    def groups(d, points, compare, side):
        support = [0] * (d["I"] + d["L"] + d["A"] + 1)
        for v in range(1, d["I"] + d["L"] + 1):
            support[v] = sym(("anonymous", side, v))
        for k, lit in sorted(points.items()):
            # State copies are induction candidates; external data bits stay distinct.
            support[lit >> 1] = 0 if k.startswith("ff:") else sym(("point", k))
        base = d["I"] + d["L"] + 1
        for i in range(d["A"]):
            support[base+i] = support[d["ands"][2*i] >> 1] | support[d["ands"][2*i+1] >> 1]
        out = {}
        for k, lit in compare.items():
            if k.startswith("ff:") and GENCOPY.search(k):
                out.setdefault((norm(k), support[lit >> 1]), []).append(k)
        return out
    n = 0
    for side, d, points, compare in (("gold", L.gold, L.gp, L.gc), ("gate", L.gate, L.tp, L.tc)):
        for keys in groups(d, points, compare, side).values():
            if len(keys) < 2:
                continue
            common = sorted(set(keys) & set(L.matched))
            rep = common[0] if common else sorted(keys)[0]
            rsd = "both" if rep in L.matched else side
            h = L.hyp.get((rsd, rep))
            if h and h[0] == "eq" and h[2] in keys:
                L.hyp.pop((rsd, rep))          # anchor a cohort without a cyclic old representative
            for k in sorted(keys):
                if k == rep or (side == "gate" and k in L.matched):
                    continue                 # matched relations come from the gold cohort
                sd = "both" if k in L.matched else side
                h = ("eq", side, rep, 0)
                if L.hyp.get((sd, k)) != h:
                    L.hyp[sd, k] = h
                    n += 1
    log.append(f"replica proposal: {n} generated-register relations (gold input support modulo copy indices)")


def anchored(L):
    """flops that already have a partner of their own: targets of gate-side / matched-side 'eq' hypotheses.  A gold-only
    representative of a gold-only replica cohort (g_add[1..3].u_ca.v == g_add[0].u_ca.v, all four merged by synthesis
    into a matched u_tag.line[9]) is NOT anchored: it must still be paired with a matched / gate flop or proved
    constant, else the whole cohort stays a free input and every cone it feeds 'differs' (kv3_astk / kv3_pv_pair
    adders, 2026-10-25)."""
    ms = set(L.matched)
    return {h[2] for (sd, k), h in L.hyp.items() if h[0] == "eq" and (sd != "gold" or h[2] in ms)}
def register_alias_proposals(L, log):
    """Propose register aliases across frontends, including a cut's output q
    versus its internal g_r.r register. Every relation is proved/refined."""
    n = 0
    def strip(k):
        k = re.sub(r"_r(?=(?:\[\d+\])*$)", "", k)
        return re.sub(r"\.(?:g_r|g_rv|g_reg)\.r((?:\[\d+\])*)$", r".q\1", k)
    by_name = collections.defaultdict(list)
    for k in L.gonly:
        by_name[strip(k)].append(k)
    for k in L.tonly:
        cand = by_name.get(strip(k), [])
        if len(cand) == 1 and ("gate", k) not in L.hyp:
            L.hyp[("gate", k)] = ("eq", "gold", cand[0], 0)
            n += 1
    log.append(f"register aliases: {n} same-name / register-output relations proposed")


def cone_sim(m, lits, fixed, words, seed):
    """bit-parallel simulation of only the cone of `lits` (inputs: `fixed` {var: int}, others random)."""
    import random
    rnd = random.Random(seed)
    W = 64 * words
    mask = (1 << W) - 1
    need, stack = set(), [l >> 1 for l in lits]
    while stack:
        v = stack.pop()
        if v == 0 or v in need:
            continue
        need.add(v)
        if v > m.ni:
            k = v - m.ni - 1
            stack += (m.ands[2 * k] >> 1, m.ands[2 * k + 1] >> 1)
    val = {0: 0}
    for v in sorted(need):
        if v <= m.ni:
            val[v] = fixed[v] if v in fixed else rnd.getrandbits(W)
        else:
            k = v - m.ni - 1
            r0, r1 = m.ands[2 * k], m.ands[2 * k + 1]
            val[v] = (val[r0 >> 1] ^ (mask if r0 & 1 else 0)) & (val[r1 >> 1] ^ (mask if r1 & 1 else 0))
    return [val[l >> 1] ^ (mask if l & 1 else 0) for l in lits], mask


def fsm_proposals(L, log, words=2, max_bits=4):
    """FSM state recoding (yosys fsm: a binary RTL state vector B[n-1:0] becomes one-hot gate flops B#t[i]).
    For each such vector the code -> one-hot-bit map is found by simulating both next-state functions from every
    (code, one-hot bit) pair; a map consistent with every observed transition is proposed as
      gate B#t[pi(c)] == (gold B == c)    (a 'cube' hypothesis: the gate flop is bound to the gold state compare)
      gold B in dom(pi)                   (a state constraint: the codes the recoded FSM implements)
    Both are proved inductively with every other hypothesis (assumed on the current state, proved on the next); a
    wrong map can only fail and be dropped, never hide a difference."""
    m, kind = L.build(with_compare=False, with_hyp=False)
    var = {}
    for v, (kd, k) in kind.items():
        if kd in ("gold_only", "gate_only"):
            var[(kd[:4], k)] = v
    bound = {k for (sd, k) in L.hyp} | {h[2] for h in L.hyp.values() if h[0] == "eq"}
    gb, tb = collections.defaultdict(dict), collections.defaultdict(dict)
    for k in L.gonly:
        a = IDXK.match(k)
        if k.startswith("ff:") and a and k not in bound and ("gold", k) in var:
            gb[a.group(1)][int(a.group(2))] = k
    for k in L.tonly:
        a = IDXK.match(k)
        if k.startswith("ff:") and a and a.group(1).endswith("#t") and k not in bound and ("gate", k) in var:
            tb[a.group(1)[:-2]][int(a.group(2))] = k
    n_new = 0
    for base in sorted(set(gb) & set(tb)):
        gk = [gb[base][i] for i in sorted(gb[base])]
        tk = [tb[base][i] for i in sorted(tb[base])]
        n, nt = len(gk), len(tk)
        if not (1 < n <= max_bits and 2 < nt <= (1 << n)) or sorted(gb[base]) != list(range(n)):
            continue
        import math
        if math.comb(1 << n, nt) * math.factorial(nt) > 200000:
            log.append(f"fsm: {base} ({n} gold / {nt} gate bits): encoding search too large, none proposed")
            continue
        dl = [L.dlit[("gold", k)] for k in gk] + [L.dlit[("gate", k)] for k in tk]
        R = {}
        for c in range(1 << n):
            for j in range(nt):
                ones = (1 << (64 * words)) - 1
                fixed = {var[("gold", k)]: (ones if (c >> b) & 1 else 0) for b, k in enumerate(gk)}
                fixed.update({var[("gate", k)]: (ones if i == j else 0) for i, k in enumerate(tk)})
                vals, mask = cone_sim(m, dl, fixed, words, seed=c * 64 + j)
                obs = collections.Counter()
                for lane in range(64 * words):
                    gn = sum(((vals[b] >> lane) & 1) << b for b in range(n))
                    tn = [(vals[n + i] >> lane) & 1 for i in range(nt)]
                    obs[(gn, tn.index(1) if sum(tn) == 1 else -1)] += 1
                R[(c, j)] = obs
        # the next states also depend on registers not yet paired (a renamed alias of a state flag is a free input
        # on each side), so a transition agrees only where those agree: pick the map with the most agreeing
        # transitions (unique best, a majority of all lanes); the induction proof decides
        import itertools
        lanes = 64 * words
        best, second, pi = -1, -1, None
        for codes in itertools.combinations(range(1 << n), nt):
            for perm in itertools.permutations(range(nt)):
                cand = dict(zip(codes, perm))
                sc = sum(cnt for c, j in cand.items() for (gn, ti), cnt in R[(c, j)].items()
                         if ti >= 0 and cand.get(gn) == ti)
                if sc > best:
                    best, second, pi = sc, best, cand
                elif sc > second:
                    second = sc
        if pi is None or best == second or 2 * best <= nt * lanes:
            log.append(f"fsm: {base} ({n} gold / {nt} gate bits): no unique encoding (best {best}, next {second} of "
                       f"{nt * lanes} transitions), none proposed")
            continue
        for c, j in sorted(pi.items()):
            L.hyp[("gate", tk[j])] = ("cube", "gold", list(gk), [(c >> b) & 1 for b in range(n)])
            n_new += 1
        L.cons.append(("gold", list(gk), [[(c >> b) & 1 for b in range(n)] for c in sorted(pi)]))
        log.append(f"fsm: {base} recoded one-hot: " + ", ".join(f"{c}->{tk[j]}" for c, j in sorted(pi.items())))
    return n_new


def drop_failed(L, bad):
    """drop failing hypotheses / constraints (a failing constraint takes its FSM's cube hypotheses with it)."""
    for n in bad:
        if n.startswith("cons:"):
            _, sd, k = n.split(":", 2)
            for c in [c for c in L.cons if c[0] == sd and c[1][0] == k]:
                L.cons.remove(c)
                for key, h in list(L.hyp.items()):
                    if h[0] == "cube" and list(h[2]) == list(c[1]):
                        L.hyp.pop(key)
            continue
        _, sd, k = n.split(":", 2)
        L.hyp.pop(("both" if sd == "bothg" else sd, k), None)


def kept_registers(L, keep_file):
    """Kept-register check (fail-closed, PATH-KV-PC3 10-25): every RTL register bit the design declares kept --
    a (* keep *) register or a flop inside a keep_hierarchy cell (pin flops, placement replicas) -- must be a flop of
    its own in the netlist.  A kept copy that synthesis merged into its twin (opt_merge) is proved equivalent by
    register correspondence, so LEC alone would pass it: here it fails.  Run after correspond(): a gold register
    paired 1:1 with a gate-only flop (a rename) is present; one proved constant (a dead pin bit, a constant ID strap
    through its landing flops) is reported, not failed (no flop to keep); one merged into another register or left
    unpaired is missing.  -> (declared keys, missing keys, constant keys)."""
    keepw = set()
    for line in Path(keep_file).read_text().splitlines():
        n = line.strip().split("/", 1)[-1].replace("\\", "").replace(" ", "")
        if n.startswith("u_dut."):
            keepw.add(GENBLK.sub("", n))
    alias = dict(a.split("->", 1) for a in L.aliased)
    inv_alias = {v: k for k, v in alias.items()}
    declared = []
    for k in L.gp:
        if not k.startswith("ff:"):
            continue
        o = inv_alias.get(k, k)[3:]
        m = IDX.match(o)
        if o in keepw or (m and m.group(1) in keepw):
            declared.append(k)
    gate, relaid = set(L.tp), collections.Counter()
    for k in L.tp:
        if "#t" in k:
            relaid[k.split("#t", 1)[0]] += 1
    gold_rel = collections.Counter()
    for k in declared:
        m = IDX.match(k)
        if m and m.group(1) in relaid:
            gold_rel[m.group(1)] += 1
    renamed = {h[2] for (sd, c), h in L.hyp.items() if sd == "gate" and h[0] == "eq" and h[2] in L.gp}
    missing, const = [], []
    for k in sorted(declared):
        if k in gate or k in renamed:
            continue
        m = IDX.match(k)
        if m and m.group(1) in relaid and relaid[m.group(1)] >= gold_rel[m.group(1)]:
            continue                 # an array the two frontends lay out differently: counted per array
        h = L.hyp.get(("gold", k))
        if h and h[0] == "const":
            const.append(k)
            continue
        missing.append(k)
    return sorted(declared), missing, const


def care_pairs(L, words, seed, tried, keys, cap=256):
    """Self-holding RTL registers that synthesis merged into an equal register (`kv_d <= r_d; c1 <= r_d` under one
    enable, `wes[287:286] <= {sv, sv}`): D(k) depends on k itself, which no partner shares, so neither the plain nor
    the equal-size-group cofactor signatures ever pair k.  Pair on the care set instead: the patterns where D(k) is
    the same when every unpaired RTL-only register value is complemented (the hold term drops out) must equal the
    partner's D
    there (either polarity), with >= 24 cared patterns (of 2048+) and both values present.  Partners: matched registers
    (a merge: k == partner) and unpaired gate-only registers (a rename).  Candidate discovery only: every pair is
    proved by the same simultaneous induction as the others (a wrong one fails and is dropped)."""
    pop = lambda x: bin(x).count("1")
    m, kind = L.build(with_compare=False, with_hyp=False)
    flip = {v for v, kd in kind.items() if kd[0] == "gold_only"}
    words = max(words, 32)                  # rare enables (a 5-bit address tap: 1/32) still leave >= 24 cared
    v0, mask = m.simulate(words, seed=seed)
    v1, _ = m.simulate(words, seed=seed, flip=flip)
    cof = [lambda side, k, vv=vv: lit_val(vv, mask, L.dlit[(side, k)]) for vv in (v0, v1)]
    groups = {}
    for k in keys:
        a, b = cof[0]("gold", k), cof[1]("gold", k)
        care = mask & ~(a ^ b)
        v = a & care
        if pop(care) < 24 or v in (0, care):
            continue
        groups.setdefault(care, []).append((k, v))
    if not groups:
        return 0
    pv = []
    for side, keys_ in (("gold", L.matched), ("gate", L.tonly)):
        for c in keys_:
            if c.startswith("ff:") and (side == "gold" or ("gate", c) not in L.hyp):
                a, b = cof[0](side, c), cof[1](side, c)
                pv.append((side, c, mask & ~(a ^ b), a))
    new, taken = 0, set()
    for care, ks in sorted(groups.items(), key=lambda g: (-len(g[1]), g[1][0][0]))[:cap]:
        idx = {}
        for side, c, pc, a in pv:
            if pc & care == care:
                idx.setdefault(a & care, []).append((side, c))
        for k, v in ks:
            hit = None
            for inv, t in ((0, v), (1, v ^ care)):
                cs = {c: side for side, c in idx.get(t, []) if (side, c) not in taken}
                for c in closest(k, list(cs)):
                    key = ("gold", k, c, inv) if cs[c] == "gold" else ("gate", c, k, inv)
                    if tried[key] < 2:
                        hit = (cs[c], c, inv)
                        break
                if hit:
                    break
            if not hit:
                continue
            side, c, inv = hit
            if side == "gold":
                L.hyp[("gold", k)] = ("eq", "gold", c, inv)
            else:
                L.hyp[("gate", c)] = ("eq", "gold", k, inv)
                taken.add(("gate", c))
            new += 1
    return new


def structural_constant_closure(L, log):
    """Propose exact next-state constants through both sides' padding pipes.

    Called after the existing hypotheses have proved. Every added relation is
    included in the next simultaneous induction proof before acceptance.
    """
    total = 0
    while True:
        L.build(with_compare=False, with_hyp=False)
        new = []
        for side, keys in (("gold", L.gonly), ("gate", L.tonly)):
            for k in keys:
                d = L.dlit.get((side, k), 2)
                if k.startswith("ff:") and (side, k) not in L.hyp and d in (0, 1):
                    new.append(((side, k), ("const", d)))
        for k in L.matched:
            g, t = L.dlit.get(("gold", k), 2), L.dlit.get(("gate", k), 3)
            if k.startswith("ff:") and ("both", k) not in L.hyp and g == t and g in (0, 1):
                new.append((("both", k), ("const", g)))
        if not new:
            break
        L.hyp.update(new)
        total += len(new)
    if total:
        log.append(f"structural constant closure: {total} relations proposed")
    return total


def correspond(L, work, conflicts, log, rounds=24, sim_iters=12, words=16):
    """register correspondence for flops that do not match by name (synthesis removed a constant flop, merged
    duplicates, or the two frontends named a register differently, e.g. a register that drives an output port):
      1. pairing by simulation: gold-only and gate-only flops (and matched flops, for merges) are paired when their
         next-state functions have the same random-simulation signature (either polarity); every pair binds the two
         flops together, so the next round sees more structure (iterated to a fixpoint);
      2. constants: a gold-only flop still unpaired is assumed constant 0 / 1 when its next state simulates to that
         constant with every assumption applied (opt_dff constant flops, self-holding reset values);
      3. proof: every hypothesis (D(flop) == partner's D / == constant) is an output of one miter, proved by ABC with
         all hypotheses assumed: an inductive invariant.  Failing hypotheses are dropped and the loop repeats (new
         candidates for `rounds` rounds, then refinement only, which shrinks monotonically to an inductive set).
    Unpaired flops stay free inputs.
    rounds=24 (was 10): in deep lane trees (dsdv_gunit_l4 g_lv[3..4], kv3_astk zn u_tag) a merged valid line
    (u_tv.line[4] == u_k5.g_r.v == valid_out) is dropped while its upstream index-line constants are still being
    refined and needs adding rounds after them; 10 left it free -> false NOT EQUIVALENT (gunit_l4 895 points,
    EQUIVALENT at 24 rounds, 738 s)."""
    relayout(L, log)
    renamed(L, log)
    replica_proposals(L, log)
    register_alias_proposals(L, log)
    fsm_proposals(L, log)
    tried = collections.Counter()      # failed attempts per candidate (a pair may fail while a neighbour is wrong)
    # refine-only rounds drop at least one hypothesis each, so they always end; past rounds + 40 they go on
    # while the time budget lasts (s81 hd_tile: false copies along 60-stage skew delay lines peel one stage
    # per round -- stopping at 64 rounds freed every unmatched flop and left 83 points differing)
    t_ref, budget = time.time(), float(os.environ.get("OT_LEC_REFINE_S", "3600"))
    for rnd in range(rounds + 1000):
        if rnd >= rounds + 40 and time.time() - t_ref > budget:
            break
        adding = rnd < rounds           # then refine only: drop what fails until the set is inductive
        before = dict(L.hyp)
        if adding:
            for it in range(sim_iters):
                m, kind = L.build(with_compare=False, with_hyp=False)
                val, mask = m.simulate(words, seed=7 * rnd + it + 1)
                sv = lambda side, k: lit_val(val, mask, L.dlit[(side, k)])
                bound = {k for (sd, k), h in L.hyp.items()} | {h[2] for h in L.hyp.values() if h[0] == "eq"}
                gbound = {k for (sd, k), h in L.hyp.items()} | anchored(L)
                tsig = {}
                for k in L.tonly:
                    if k.startswith("ff:") and ("gate", k) not in L.hyp and k not in bound and \
                            sv("gate", k) not in (0, mask):
                        tsig.setdefault(sv("gate", k), []).append(k)
                msig = {}
                for k in L.matched:
                    if k.startswith("ff:"):
                        msig.setdefault(sv("gold", k), []).append(k)
                # gold-only registers that already have a gate partner act as matched for pairing: synthesis may
                # merge a second gold register into the same gate flop (eng lookup: roff[j] <= r8[j][4:3] is
                # baddr[j][4:3] since r256 is 0 mod 256; gate keeps only baddr#t[j][4:3], whose gold partner is
                # the gold-only baddr[j][4:3]; with matched-only candidates roff stayed free -> q_off differed)
                for (sd, c), h in L.hyp.items():
                    ok = h[2] if h[0] == "eq" else None
                    if sd == "gate" and h[1] == "gold" and ok in L.gp and ok not in L.tp and ok.startswith("ff:") \
                            and ("gold", ok) not in L.hyp:
                        msig.setdefault(sv("gold", ok), []).append(ok)
                new = 0
                free_g = [k for k in L.gonly if k.startswith("ff:") and ("gold", k) not in L.hyp and k not in gbound]
                # (a bit that simulates constant pairs here only once its constant hypothesis has failed: the
                # MSB of a remainder that is set only on a divide by zero)
                free_t = [k for k in L.tonly if k.startswith("ff:") and ("gate", k) not in L.hyp and k not in bound]
                for base, maps in array_maps(free_g, free_t).items():
                    best = max(maps, key=lambda mp: sum(sv("gold", a) == sv("gate", b) for a, b in mp.items()))
                    for a, b in best.items():
                        s = sv("gold", a)
                        if s == sv("gate", b) and (s not in (0, mask) or tried[("gold", a, "c")] >= 1) and \
                                tried[("gate", b, a, 0)] < 2:
                            L.hyp[("gate", b)] = ("eq", "gold", a, 0)
                            tsig[s] = [c for c in tsig.get(s, []) if c != b]
                            new += 1
                partnered = anchored(L)
                # the index strides of the gold-only bits already paired inside their own vector (a merged operand
                # copy: b_n[i] == a_n[i + 24]); a bit the signatures cannot place (it simulates constant: an
                # implicit leading one) tries its vector's strides
                strides, mset = collections.defaultdict(collections.Counter), set(L.matched)
                for (sd, k), h in L.hyp.items():
                    a, b = IDXK.match(k), h[0] == "eq" and IDXK.match(h[2])
                    if sd == "gold" and a and b and a.group(1) == b.group(1):
                        strides[a.group(1)][int(b.group(2)) - int(a.group(2))] += 1
                # a cohort representative (partnered: other gold flops' "eq" partner) pairs too: synthesis may
                # have merged the whole cohort into a third, name-matched register (kv3_pv_pair: every lane's
                # u_prod.v3 == the slice's fc[2]; the rep left free made all 32 lane fault registers differ)
                for k in L.gonly:
                    if not k.startswith("ff:") or ("gold", k) in L.hyp:
                        continue
                    s = sv("gold", k)
                    if s in (0, mask) and tried[("gold", k, "c")] < 1:
                        continue                      # constant-looking: step 2 first
                    hit = None
                    a = IDXK.match(k)
                    for d, _ in (strides[a.group(1)].most_common(4) if a and a.group(1) in strides else []):
                        c = f"{a.group(1)}[{int(a.group(2)) + d}]"
                        if c != k and c in mset and sv("gold", c) in (s, s ^ mask):
                            inv = int(sv("gold", c) != s)
                            if tried[("gold", k, c, inv)] < 2:
                                hit = ("gold", k, ("eq", "gold", c, inv))
                                break
                    for inv, t in (() if hit or s in (0, mask) else ((0, s), (1, s ^ mask))):
                        for c in closest(k, tsig.get(t, [])):
                            if ("gate", c) not in L.hyp and tried[("gate", c, k, inv)] < 2:
                                hit = ("gate", c, ("eq", "gold", k, inv))
                                break
                        if hit:
                            break
                        for c in closest(k, msig.get(t, [])):
                            # (an anchored gold-only candidate may itself have been paired this pass: never
                            # bind to a register already bound, or two anchored registers bind to each other)
                            if c != k and ("gold", c) not in L.hyp and tried[("gold", k, c, inv)] < 2:
                                hit = ("gold", k, ("eq", "gold", c, inv))
                                break
                        if hit:
                            break
                    if hit:
                        L.hyp[(hit[0], hit[1])] = hit[2]
                        tsig = {t: [c for c in v if c != hit[1]] for t, v in tsig.items()}
                        new += 1
                for k in L.tonly:
                    if not k.startswith("ff:") or ("gate", k) in L.hyp or k in bound:
                        continue
                    s = sv("gate", k)
                    if s in (0, mask):
                        continue                      # constant-looking: a constant hypothesis, not a pair
                    for inv, t in ((0, s), (1, s ^ mask)):
                        c = next((c for c in closest(k, msig.get(t, [])) if tried[("gate", k, c, inv)] < 2), None)
                        if c:
                            L.hyp[("gate", k)] = ("eq", "gold", c, inv)
                            new += 1
                            break
                # self-holding registers (load-enable) depend on their own state, which differs by side: pair the
                # unpaired ones by the signature of D with every unpaired register held at 0, and at 1
                if not new:
                    cof = []
                    for c in (0, 1):
                        mc, _ = L.build(with_compare=False, with_hyp=False, free_const=c)
                        vc, _ = mc.simulate(words, seed=31 * rnd + it + 5)
                        cof.append(lambda side, k, vc=vc, dl=dict(L.dlit): lit_val(vc, mask, dl[(side, k)]))
                    partnered = anchored(L)
                    ug = [k for k in L.gonly if k.startswith("ff:") and ("gold", k) not in L.hyp and k not in partnered]
                    ut = {}
                    for k in L.tonly:
                        if k.startswith("ff:") and ("gate", k) not in L.hyp:
                            ut.setdefault((cof[0]("gate", k), cof[1]("gate", k)), []).append(k)
                    m, kind = L.build(with_compare=False, with_hyp=False)   # restore dlit of the normal build
                    ga = {}
                    for k in ug:
                        ga.setdefault((cof[0]("gold", k), cof[1]("gold", k)), []).append(k)
                    nat = lambda k: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", k)]
                    for a, ks in ga.items():
                        # equal-size groups only (cofactor signatures collide easily), paired in name order (the
                        # bits of one vector look alike here); the induction proof decides
                        cs = ut.get(a, [])
                        if len(ks) != len(cs) or len(ks) > 64 or (a[0] in (0, mask) and a[0] == a[1]):
                            continue
                        for k, c in zip(sorted(ks, key=nat), sorted(cs, key=nat)):
                            if tried[("gate", c, k, 0)] < 2:
                                L.hyp[("gate", c)] = ("eq", "gold", k, 0)
                                new += 1
                    # load-enable registers merged by synthesis into a MATCHED sibling bit (no reset, one enable,
                    # equal data: QC su8 fa[313]/fa[314] -> fa[315]): with the unpaired registers and the matched
                    # bits of their own vectors held at 0 / at 1 (self-hold removed, other state random), a gold-only
                    # register pairs with the one matched sibling of its (non-constant) cofactor signature, several
                    # gold registers may share it; induction decides
                    ug = [k for k in ug if ("gold", k) not in L.hyp]
                    vb = {IDX.match(k).group(1) for k in ug if IDX.match(k)}
                    hold = {k for k in L.matched if k.startswith("ff:") and IDX.match(k) and IDX.match(k).group(1) in vb}
                    if ug and hold:
                        hof = []
                        for c in (0, 1):
                            mc, _ = L.build(with_compare=False, with_hyp=False, free_const=c, hold_matched=hold)
                            vc, _ = mc.simulate(words, seed=37 * rnd + it + 3)
                            hof.append(lambda side, k, vc=vc, dl=dict(L.dlit): lit_val(vc, mask, dl[(side, k)]))
                        hm = {}
                        for k in hold:
                            if ("both", k) not in L.hyp:
                                hm.setdefault((hof[0]("gold", k), hof[1]("gold", k)), []).append(k)
                        hg = {k: (hof[0]("gold", k), hof[1]("gold", k)) for k in ug}
                        m, kind = L.build(with_compare=False, with_hyp=False)
                        v2, _ = m.simulate(words, seed=41 * rnd + it + 7)
                        looks_const = {k for k in ug if lit_val(v2, mask, L.dlit[("gold", k)]) in (0, mask)}
                        for k, a in hg.items():
                            if a[0] in (0, mask) and a[1] in (0, mask):
                                continue
                            # several siblings may look alike (sign-extension / borrow bits): nearest name first,
                            # a failed pair moves on to the next one
                            # (a constant-looking register tries its constant first; at most 3 siblings per register)
                            if tried[("gold", k, "sib")] >= 3 or (tried[("gold", k, "c")] < 1 and
                                                                   k in looks_const):
                                continue
                            c = next((c for c in closest(k, hm.get(a, [])) if tried[("gold", k, c, 0)] < 1), None)
                            if c:
                                tried[("gold", k, "sib")] += 1
                                L.hyp[("gold", k)] = ("eq", "gold", c, 0)
                                new += 1
                    # merged into a matched register of ANOTHER vector (HBM tkm tile: self-holding X[0..3][j] ->
                    # up_out[86 i + j], gt[64..67][j] -> q_bg[8][86 j + 85]): the same cofactor test with every
                    # SELF-HOLDING matched register (own Q within 8 AND levels of its next state: the hold mux) held at
                    # 0 / at 1 -- holding every matched register would make enables / data constant too; a pair
                    # proposed here is proved by induction like any other
                    ug2 = [k for k in ug if ("gold", k) not in L.hyp and tried[("gold", k, "sib")] < 3]
                    if ug2:
                        m, kind = L.build(with_compare=False, with_hyp=False)
                        var_of = {kk: v for v, (t, kk) in kind.items() if t == "matched"}
                        hall = {k for k in L.matched if k.startswith("ff:") and k in var_of and
                                var_of[k] in m.near_inputs(L.dlit[("gold", k)], 8)}
                        hof = []
                        for c in (0, 1):
                            mc, _ = L.build(with_compare=False, with_hyp=False, free_const=c, hold_matched=hall)
                            vc, _ = mc.simulate(words, seed=43 * rnd + it + 11)
                            hof.append(lambda side, k, vc=vc, dl=dict(L.dlit): lit_val(vc, mask, dl[(side, k)]))
                        hm = {}
                        for k in hall:
                            if ("both", k) not in L.hyp:
                                a = (hof[0]("gold", k), hof[1]("gold", k))
                                if a[0] not in (0, mask) or a[1] not in (0, mask):
                                    hm.setdefault(a, []).append(k)
                        m, kind = L.build(with_compare=False, with_hyp=False)
                        v2, _ = m.simulate(words, seed=47 * rnd + it + 13)
                        for k in ug2:
                            a = (hof[0]("gold", k), hof[1]("gold", k))
                            if (a[0] in (0, mask) and a[1] in (0, mask)) or len(hm.get(a, [])) > 8 or \
                                    (tried[("gold", k, "c")] < 1 and lit_val(v2, mask, L.dlit[("gold", k)]) in (0, mask)):
                                continue
                            c = next((c for c in closest(k, hm.get(a, [])) if tried[("gold", k, c, 0)] < 1), None)
                            if c:
                                tried[("gold", k, "sib")] += 1
                                tried[("gold", k, c, 0)] += 1
                                L.hyp[("gold", k)] = ("eq", "gold", c, 0)
                                new += 1
                    new += care_pairs(L, words, 77 * rnd + it + 3, tried, [k for k in ug if ("gold", k) not in L.hyp])
                # Duplicate feedback copies can choose different representatives in each frontend.
                # Group on gold signatures even before individual gold/gate D functions agree;
                # the hypothesis miter below proves the equality on BOTH sides simultaneously.
                groups = {}
                for k in L.matched:
                    if k.startswith("ff:") and ("both", k) not in L.hyp:
                        s = sv("gold", k)
                        if s in (0, mask):
                            continue
                        inv = s >> (mask.bit_length() - 1)
                        groups.setdefault(s ^ (mask if inv else 0), []).append((k, inv))
                for g in groups.values():
                    if len(g) < 2:
                        continue
                    g.sort()
                    rep, rinv = g[0]
                    for k, inv in g[1:]:
                        if tried[("both", k, rep, inv ^ rinv)] < 2:
                            L.hyp[("both", k)] = ("eq", "gold", rep, inv ^ rinv)
                            new += 1
                if not new:
                    break
            # constants for the gold-only flops left: fixpoint in simulation, starting from 0
            partners = anchored(L)
            # (a constant that failed while its neighbours were wrong is retried once its next state has become
            # a structural constant under the hypotheses now in place -- for a self-holding register, with the
            # unpaired registers (itself) held at 0: eng u_e.hq_atom[30] <= iss ? baddr[][35] : hq_atom[30] is
            # dropped in early rounds and becomes constant only once the cb_q -> r8 -> baddr chain is proved)
            m, kind = L.build(with_compare=False, with_hyp=False, free_const=0)
            zdl = dict(L.dlit)
            m, kind = L.build(with_compare=False, with_hyp=False)
            for side, keys in (("gold", L.gonly), ("gate", L.tonly)):    # gate-only flops: constant candidates too
                for k in keys:
                    if k.startswith("ff:") and (side, k) not in L.hyp and k not in partners and \
                            (tried[(side, k, "c")] < 2 or L.dlit.get((side, k), 2) in (0, 1) or
                             (zdl.get((side, k)) == 0 and tried[(side, k, "c")] < 6)):
                        L.hyp[(side, k)] = ("const", L.dlit.get((side, k)) if L.dlit.get((side, k)) in (0, 1) else 0)
            # matched flops whose next state simulates constant on both sides (synthesis may have merged such a
            # flop into another constant one, so the gate's copy is a different, free register)
            m, kind = L.build(with_compare=False, with_hyp=False)
            val, mask = m.simulate(words, seed=999)
            reps = {h[2] for (sd, k), h in L.hyp.items() if sd == "both" and h[0] == "eq"}
            for k in L.matched:
                if not k.startswith("ff:") or ("both", k) in L.hyp or k in reps or tried[("both", k, "c")] >= 2:
                    continue
                a, b = lit_val(val, mask, L.dlit[("gold", k)]), lit_val(val, mask, L.dlit[("gate", k)])
                if a == b and a in (0, mask):
                    L.hyp[("both", k)] = ("const", 1 if a else 0)
            # self-holding constants: a matched register that only ever reloads a constant or holds itself
            # (eng u_e.hq_atom[30] <= iss ? baddr[][35] (constant 0) : hq_atom[30]) simulates non-constant from a
            # random state; with the free matched registers held at c its next state is c on both sides, and its
            # own Q is in its next-state cone.  Candidate only; induction decides.
            var_of = {kk: v for v, (t, kk) in kind.items() if t == "matched"}
            gdl = dict(L.dlit)
            cands = {k for k in L.matched if k.startswith("ff:") and ("both", k) not in L.hyp and k not in reps
                     and tried[("both", k, "c")] < 2}
            selfc = []
            for c in (0, 1):
                mc, _ = L.build(with_compare=False, with_hyp=False, free_const=c, hold_matched=cands)
                vc, _ = mc.simulate(words, seed=997 + c)
                want = mask if c else 0
                for k in sorted(cands):
                    if lit_val(vc, mask, L.dlit[("gold", k)]) == want and lit_val(vc, mask, L.dlit[("gate", k)]) == want \
                            and k in var_of and len(selfc) < 4096 and (var_of[k] in m.cone_inputs(gdl[("gold", k)])):
                        selfc.append((k, c))
            m, kind = L.build(with_compare=False, with_hyp=False)
            for k, c in selfc:
                if ("both", k) not in L.hyp:
                    L.hyp[("both", k)] = ("const", c)
            for it in range(sim_iters):
                m, kind = L.build(with_compare=False, with_hyp=False)
                val, mask = m.simulate(words, seed=1000 + it)
                changed = 0
                for (sd, k), h in list(L.hyp.items()):
                    if h[0] != "const":
                        continue
                    s = lit_val(val, mask, L.dlit[("gold" if sd == "both" else sd, k)])
                    if sd == "both" and s != lit_val(val, mask, L.dlit[("gate", k)]):
                        s = -1                              # sides disagree: not a constant
                    want = mask if h[1] else 0
                    if s != want:
                        del L.hyp[(sd, k)]
                        if s in (0, mask):
                            L.hyp[(sd, k)] = ("const", 1 if s else 0)
                        else:
                            tried[(sd, k, "c")] += 2
                        changed += 1
                if not changed:
                    break
        if adding:
            # State relations rejected before aliases/copies settled can become
            # inductive later; retry while candidates are still being added.
            fsm_proposals(L, log)
        if not L.hyp:
            return
        m, kind = L.build(with_compare=False, with_hyp=True)
        st = prove(m, work, conflicts, log, tag=f"hyp{rnd}")
        bad = [n for n, s in st.items() if s != "proved"]
        (Path(work) / f"hyp{rnd}_failed.txt").write_text("".join(n + "\n" for n in bad))
        log.append(f"correspondence round {rnd}: {len(st)} hypotheses, {len(bad)} failed "
                   f"({sum(st[n] == 'undecided' for n in bad)} undecided) {bad[:6]}")
        if not bad:
            if structural_constant_closure(L, log):
                continue     # prove the new constants before returning
            if L.hyp == before or not adding:
                return
            continue
        drop_failed(L, [n for n in bad if n.startswith("cons:")])
        for n in bad:
            if n.startswith("cons:"):
                continue
            _, side, k = n.split(":", 2)
            side = "both" if side == "bothg" else side
            h = L.hyp.pop((side, k), None)
            if h is None:
                continue
            tried[(side, k, "c") if h[0] == "const" else (side, k, str(h[2]), str(h[3]))] += 1
    L.hyp.clear()                             # refinement did not converge: no assumptions at all
    L.cons.clear()
    log.append("correspondence: refinement did not converge; all unmatched flops free")


# ---------------------------------------------------------------------------------------------- driver
def run_yosys(script, path, log):
    Path(path).write_text(script)
    y = ORFS + "/tools/install/yosys/bin/yosys"
    y = y if os.access(y, os.X_OK) else (shutil.which("yosys") or "yosys")
    r = subprocess.run([y, "-q", "-l", str(path) + ".log", "-s", str(path)], capture_output=True, text=True)
    if r.returncode:
        err = [l for l in (Path(str(path) + ".log").read_text(errors="replace").splitlines()
                           if Path(str(path) + ".log").is_file() else []) if "ERROR" in l]
        raise Unproven(f"yosys {Path(path).name} failed: " + ("; ".join(err[-3:]) or r.stderr[-400:]))
    return r


def check(kit, netlist=None, out=None, gold_frontend=None, conflicts=1000, port_map=None, reuse=False):
    kit = str(Path(kit).resolve())
    out = Path(out or Path(kit) / "lec")
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rec = dict(schema=SCHEMA, kit=kit, generated=time.strftime("%Y-%m-%dT%H:%M:%S%z"), verdict="UNPROVEN")
    log = []
    try:
        env = parse_config(kit)
        top = env["DESIGN_NAME"]
        netlist = netlist or find_netlist(kit)
        gate_fe = env.get("SYNTH_HDL_FRONTEND", "") or "verilog"
        gold_fe = gold_frontend or ("verilog" if gate_fe == "slang" else "slang")
        rec.update(top=top, netlist=netlist, synth_frontend=gate_fe, gold_frontend=gold_fe)
        if gold_fe == gate_fe:
            rec["warning"] = "gold frontend == synthesis frontend (frontend bugs are not independent)"
        bad = sorted(c for c in netlist_cell_types(netlist) if UNSUPPORTED_CELLS.match(c))
        if bad:
            raise Unproven(f"netlist holds cells LEC does not model: {bad[:8]}")
        srcmods = set()
        for f in env["VERILOG_FILES"].split():
            srcmods |= set(src_modules(kpath(kit, f)))
        lib_bbs = [l for l in macro_libs(env, kit) if not set(lib_cells(l)) <= srcmods]
        # 0. lint: implicit nets fail the kit before any proof (see implicit_net_lint)
        hits = implicit_net_lint(env, kit, lib_bbs, out, log)
        rec["implicit_nets"] = [dict(file=f.replace("/work/", "", 1), line=int(n), net=w) for f, n, w in hits[:200]]
        if hits:
            rec["verdict"] = "LINT FAIL"
            rec["reason"] = (f"{len(hits)} implicit net(s) created (identifier used before its declaration or "
                             f"undeclared; undriven in the yosys-slang synthesis): " +
                             ", ".join(f"{Path(f).name}:{n} {w}" for f, n, w in hits[:8]))
            raise LintFail(rec["reason"])
        # 1. black boxes of the gold elaboration (ports) -> one stub file for both sides
        run_yosys(bb_script(env, kit, gold_fe, lib_bbs, out / "bb"), out / "bb.ys", log)
        bbports = parse_bb_verilog(out / "bb.v")
        bbports = {k: v for k, v in bbports.items() if not k.startswith("$abstract")}
        rec["black_boxes"] = {k: len(v) for k, v in sorted(bbports.items())}
        (out / "stubs.v").write_text(stub_verilog(bbports))
        tops = parse_bb_verilog(out / "bb_top.v")
        if top not in tops:
            raise LecError(f"pre-pass did not write the ports of {top}")
        rec["ports"] = dict(inputs=sum(w for p, d, w, lo in tops[top] if d == "input"),
                            outputs=sum(w for p, d, w, lo in tops[top] if d == "output"))
        (out / "wrap_gold.v").write_text(wrapper_verilog(top, tops[top], top_params(env) if gold_fe == "verilog"
                                                         else ()))
        (out / "wrap_gate.v").write_text(wrapper_verilog(top, tops[top]))
        (out / "lecff.v").write_text(LECFF_V)
        # 2. gold and gate AIGs (two yosys processes in parallel)
        t1 = time.time()
        if reuse and all((out / f).is_file() for f in ("gold.aig", "gold.map", "gate.aig", "gate.map")):
            log.append("reusing gold / gate AIGs")
        else:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(2) as ex:
                fg = ex.submit(run_yosys, gold_script(env, kit, gold_fe, lib_bbs, out / "stubs.v", out / "wrap_gold.v",
                                                      out / "lecff.v", out / "gold"), out / "gold.ys", log)
                ft = ex.submit(run_yosys, gate_script(env, netlist, out / "stubs.v", out / "wrap_gate.v",
                                                      out / "lecff.v", out / "gate"), out / "gate.ys", log)
                fg.result()
                ft.result()
        rec["t_aig_s"] = round(time.time() - t1, 1)
        # 3. key points, register correspondence, miter
        t1 = time.time()
        L = Lec(read_aig(out / "gold.aig"), read_map(out / "gold.map"),
                read_aig(out / "gate.aig"), read_map(out / "gate.map"), port_map)
        correspond(L, out, conflicts, log)
        (out / "hyp.json").write_text(json.dumps([[sd, k, list(h)] for (sd, k), h in sorted(L.hyp.items())]) + "\n")
        m, kind = L.build(with_compare=True, with_hyp=True)
        rec["t_corr_s"] = round(time.time() - t1, 1)
        hyp = L.hyp
        consts = sorted(k for (sd, k), h in hyp.items() if h[0] == "const")
        pairs = sorted(f"{sd}:{k}={'~' if h[3] else ''}{h[2]}" for (sd, k), h in hyp.items() if h[0] == "eq")
        partners = anchored(L)
        live_g = [k for k in L.gonly if ("gold", k) not in hyp and k not in partners]
        live_t = [k for k in L.tonly if ("gate", k) not in hyp]
        cpg = sorted(set(L.gc) - set(L.tc))
        cpt = sorted(set(L.tc) - set(L.gc))
        lst = lambda v: dict(n=len(v), first=v[:40])
        rec["keypoints"] = dict(
            gold=dict(inputs=L.gold["I"], flops=L.gold["L"], outputs=L.gold["O"], ands=L.gold["A"]),
            gate=dict(inputs=L.gate["I"], flops=L.gate["L"], outputs=L.gate["O"], ands=L.gate["A"]),
            matched=len(L.matched), gold_constant_flops=lst(consts), paired_flops=lst(pairs),
            gold_unmatched_live=lst(live_g), gate_unmatched=lst(live_t),
            gold_x_sources=len(L.gx), gate_x_sources=len(L.tx),
            gold_only_compare=lst(cpg), gate_only_compare=lst(cpt))
        if not m.outs:
            raise Unproven("no matched compare points")
        # 4. prove every compare point (and the correspondence hypotheses once more, together)
        t1 = time.time()
        status = prove(m, out, conflicts, log, tag="miter")
        rec["t_prove_s"] = round(time.time() - t1, 1)
        idx = {n: i for i, n in enumerate(m.onames)}
        hard, soft = [], []
        for n, st in sorted(status.items()):
            if st == "proved":
                continue
            ins = m.cone_inputs(m.outs[idx[n]])
            kinds = sorted({kind[v][0] for v in ins if kind[v][0] not in ("matched", "paired")})
            keys = sorted(kind[v][1] for v in ins if kind[v][0] not in ("matched", "paired"))[:8]
            e = dict(point=n, status=st, cone_unmatched=kinds, cone_unmatched_keys=keys)
            # a difference whose cone sees only matched key points, constants, partners and RTL registers that
            # synthesis removed although their next state is not constant is a real function difference
            if st == "differs" and set(kinds) <= {"gold_only", "gold_x"}:
                hard.append(e)
            else:
                soft.append(e)
        rec["x_dont_care_points"] = lst([k for k in L.xpoints if k in status])
        kf = Path(str(out / "gold") + ".keep")
        if kf.is_file():
            kdecl, kmiss, kconst = kept_registers(L, kf)
            rec["kept_registers"] = dict(declared=len(kdecl), in_netlist=len(kdecl) - len(kmiss) - len(kconst),
                                         constant_proved=lst(kconst), missing=lst(kmiss))
        else:
            kmiss = None
            rec["kept_registers"] = "not checked (no gold.keep: AIGs reused from an older lec.py)"
        np_ = sum(1 for v in status.values() if v == "proved")
        rec["counts"] = dict(compare_points=len(status), proved=np_,
                             differs=sum(1 for v in status.values() if v == "differs"),
                             undecided=sum(1 for v in status.values() if v == "undecided"))
        rec["failing"] = hard[:500]
        rec["unproven_points"] = soft[:500]
        if kmiss:
            rec["verdict"] = "KEEP FAIL"
            rec["reason"] = (f"{len(kmiss)} of {len(kdecl)} declared kept register bits are not flops of their own "
                             f"name in the netlist (merged / folded / renamed by synthesis; first: "
                             + ", ".join(kmiss[:6]) + ")")
            if hard:
                rec["reason"] += f"; also {len(hard)} compare points differ"
        elif hard:
            rec["verdict"] = "NOT EQUIVALENT"
            rec["reason"] = f"{len(hard)} compare points differ (first: " + \
                ", ".join(e["point"] for e in hard[:8]) + ")"
            rm = sorted({k for e in hard for k in e["cone_unmatched_keys"] if k.startswith("ff:")})
            if rm:
                rec["reason"] += "; RTL registers removed by synthesis although not constant: " + ", ".join(rm[:8])
        elif soft:
            rec["verdict"] = "UNPROVEN"
            rec["reason"] = (f"{len(soft)} compare points not proved; each depends on X (don't-care) sources, "
                             f"synthesis-only registers or hit the solver limit (first: "
                             + ", ".join(e["point"] for e in soft[:6]) + ")")
        else:
            # every compare point proved with the unmatched registers as free inputs: they cannot matter
            rec["verdict"] = "EQUIVALENT"
            rec["note"] = (f"{len(status)} compare points proved; {len(L.matched)} key points matched by name, "
                           f"{len(pairs)} register pairs / merges and {len(consts)} constant registers proved "
                           f"inductively; {len(live_g)} RTL and {len(live_t)} gate registers unmatched and "
                           f"unobservable (proved as free inputs)")
            if rec["x_dont_care_points"]["n"]:
                rec["note"] += (f"; {rec['x_dont_care_points']['n']} of them reach an RTL X (don't care: equal "
                                f"wherever the RTL is not X)")
    except LintFail:
        pass
    except Unproven as e:
        rec["verdict"], rec["reason"] = "UNPROVEN", str(e)
    except (LecError, OSError, subprocess.SubprocessError, ValueError, KeyError) as e:
        rec["verdict"], rec["reason"] = "ERROR", f"{type(e).__name__}: {e}"
        import traceback
        log.append(traceback.format_exc())
    rec["t_total_s"] = round(time.time() - t0, 1)
    (out / "lec.json").write_text(json.dumps(rec, indent=1) + "\n")
    (out / "lec.log").write_text("\n".join(log))
    return rec


def in_image():
    return os.path.isdir(ORFS + "/tools/install/yosys")


def via_docker(args, image, mem):
    """re-run this script inside the ORFS image: kit at /work, output dir at /lecout."""
    kit = str(Path(args.kit).resolve())
    out = str(Path(args.out or Path(kit) / "lec").resolve())
    Path(out).mkdir(parents=True, exist_ok=True)
    me = str(Path(__file__).resolve())
    cmd = ["docker", "run", "--rm", f"--memory={mem}g", f"--memory-swap={mem}g", "-v", f"{kit}:/work:ro",
           "-v", f"{out}:/lecout", "-v", f"{me}:/lec.py:ro", "-e", f"HUID={os.getuid()}", "-e", f"HGID={os.getgid()}"]
    # optional XOR-aware SAT backend: OT_LEC_SOLVER = a host dir holding pycryptosat for the image's python (cp310)
    sol = os.environ.get("OT_LEC_SOLVER", "")
    if sol and os.path.isdir(sol):
        cmd += ["-v", f"{os.path.abspath(sol)}:/lecsolver:ro", "-e", "LEC_SOLVER_PATH=/lecsolver"]
    cmd += [image, "bash", "-lc"]
    inner = ["python3", "-I", "/lec.py", "/work", "--out", "/lecout", "--conflicts", str(args.conflicts), "--jobs", str(args.jobs)]
    if args.netlist:
        n = str(Path(args.netlist).resolve())
        if not n.startswith(kit + "/"):
            raise SystemExit(f"--netlist must be inside the kit ({kit}) for --image runs")
        inner += ["--netlist", "/work/" + n[len(kit) + 1:]]
    if args.reuse:
        inner += ["--reuse"]
    if args.gold_frontend:
        inner += ["--gold-frontend", args.gold_frontend]
    if args.port_map:
        shutil.copyfile(args.port_map, Path(out) / "port_map.json")
        inner += ["--port-map", "/lecout/port_map.json"]
    sh = " ".join(shlex.quote(x) for x in inner) + "; rc=$?; chown -R $HUID:$HGID /lecout; exit $rc"
    return subprocess.run(cmd + [sh]).returncode


def main(argv=None):
    global PROVE_JOBS
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kit")
    ap.add_argument("--netlist", help="gate netlist (default: KIT/run/results/asap7/*/base/1_2_yosys.v)")
    ap.add_argument("--out", help="output dir (default KIT/lec)")
    ap.add_argument("--jobs", type=int, default=1, help="parallel independent SAT-cone batches (admit matching threads/memory)")
    ap.add_argument("--gold-frontend", choices=("verilog", "slang"),
                    help="default: the frontend synthesis did NOT use")
    ap.add_argument("--port-map", help="JSON {gate port bit: gold port bit} (renamed packed buses)")
    ap.add_argument("--conflicts", type=int, default=1000)
    ap.add_argument("--reuse", action="store_true", help="reuse OUT/gold|gate.aig from an earlier run (debug)")
    ap.add_argument("--image", default=None, help="run inside this docker image (default when not in the ORFS image)")
    ap.add_argument("--mem", type=int, default=32, help="docker --memory GB for --image runs")
    a = ap.parse_args(argv)
    PROVE_JOBS = max(1, a.jobs)
    if not in_image():
        rc = via_docker(a, a.image or IMAGE, a.mem)
        p = Path(a.out or Path(a.kit) / "lec") / "lec.json"
        if p.is_file():
            r = json.loads(p.read_text())
            print(f"LEC {r['verdict']}: {r.get('top')} {r.get('reason', r.get('note', ''))} "
                  f"({r.get('t_total_s')} s)")
        return rc
    pm = json.loads(Path(a.port_map).read_text()) if a.port_map else None
    r = check(a.kit, a.netlist, a.out, a.gold_frontend, a.conflicts, pm, a.reuse)
    c = r.get("counts", {})
    print(f"LEC {r['verdict']}: {r.get('top')} cp={c.get('compare_points')} proved={c.get('proved')} "
          f"differs={c.get('differs')} undecided={c.get('undecided')} {r.get('reason', r.get('note', ''))} "
          f"({r['t_total_s']} s)")
    return {"EQUIVALENT": 0, "NOT EQUIVALENT": 1, "LINT FAIL": 1, "KEEP FAIL": 1, "UNPROVEN": 2}.get(r["verdict"], 3)


if __name__ == "__main__":
    sys.exit(main())
