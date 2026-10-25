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
        m = re.match(r"^\s*(?:override\s+)?(?:export\s+)?([A-Z0-9_]+)\s*[:?+]?=\s*(.*)$", line)
        if m:
            env[m[1]] = m[2].strip()
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


def read_rtl_cmds(env, kit, frontend, lib_bbs, chparam=True, slang_extra=()):
    """yosys commands reading the kit RTL with `frontend` ('verilog' | 'slang'); lib_bbs: macro liberty files whose
    cells have no Verilog body in the sources (read as blackbox cells); slang_extra: extra read_slang options."""
    files = [kpath(kit, f) for f in env["VERILOG_FILES"].split()]
    incs = [kpath(kit, d) for d in env.get("VERILOG_INCLUDE_DIRS", "").split()]
    defs = env.get("VERILOG_DEFINES", "").split()
    if "-DSYNTHESIS" not in defs:
        defs.append("-DSYNTHESIS")
    cmds = [f"read_liberty -lib -ignore_miss_func {l}" for l in lib_bbs]
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
          "setattr -mod -unset keep_hierarchy", "setattr -unset keep_hierarchy", "proc",
          # constant folding / width reduction that keeps don't-care semantics (-keepdc), per module before
          # flatten, and peepopt (shiftmul / shiftadd: a dynamic part-select full[276 * f + b] becomes a mux of the
          # constant-stride slices instead of a 32-stage x-filled barrel shifter): without them eng_rr_e's 552
          # strided selects expand to 31M cells (77 GB) in techmap; with them 263k cells, 1.2 GB
          "opt_expr -keepdc", "opt_clean", "wreduce -keepdc", "peepopt", "opt_clean", "wreduce -keepdc", "opt_clean",
          "flatten -noscopeinfo", "opt_clean",
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
    return n.replace("\\", "").replace(" ", ""), inv


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

    def add_input(self, name):
        if self.ands:
            raise LecError("inputs after ands")
        self.ni += 1
        self.inames.append(name)
        return 2 * self.ni

    def AND(self, a, b):
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

    def XOR(self, a, b):
        return self.AND(self.AND(a, b ^ 1) ^ 1, self.AND(a ^ 1, b) ^ 1) ^ 1

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

    def simulate(self, words, seed=1):
        """bit-parallel random simulation (python ints of `words` x 64 bits) -> value list per variable."""
        import random
        rnd = random.Random(seed)
        W = 64 * words
        mask = (1 << W) - 1
        val = [0] * (self.ni + len(self.ands) // 2 + 1)
        for v in range(1, self.ni + 1):
            val[v] = rnd.getrandbits(W)
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
        self.galias = galias
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

    def build(self, with_compare=True, with_hyp=True, extra=None, free_const=None):
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
                elif h and h[0] == "eq":
                    later.append((side, k, h))
                elif free_const is not None and k.startswith("ff:"):
                    bind(lmap, p[k], free_const)  # cofactor: unpaired registers held at a constant
                else:
                    v = m.add_input(f"{side}:{k}")
                    kind[v >> 1] = (side + "_only", k)
                    bind(lmap, p[k], v)
        # hypotheses 'eq': bind to the partner's (already bound) value; chains resolve in passes, cycles are dropped
        while later:
            nxt = []
            for side, k, h in later:
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
            r = subprocess.run([abc, "-c", "; ".join(script)], capture_output=True, text=True)
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


def alias_arrays(L, log, words=4):
    """an RTL array whose gate flops synthesis named after an ALIAS array (`assign SX[i] = X[i]`: rename -wire picked
    the alias wire, so the gate holds SX[i][b] while the gold, read with the other frontend, holds X[h][flat]): the
    gold flops' own Q-net alias names carry the gate base, which is the evidence that pairs the two bases.  The index
    tuples are flattened mixed-radix (outer index reversed or not, either side) and the gate keys re-keyed to the gold
    names when the flattened gate set is a subset of the gold set (synthesis may have merged some elements into other
    registers: those gold flops stay gold-only and are paired by function in correspond); among the variants the one
    with the fewest disagreeing matched compare points in simulation is kept.  Sound: the re-key is a bijection of
    key points and every next-state function is still proved (a wrong layout can only produce a difference)."""
    def split(keys):
        d = {}
        for k in keys:
            m = IDX.match(k)
            if k.startswith("ff:") and m:
                d.setdefault(m.group(1), {})[k] = tuple(int(x) for x in re.findall(r"\d+", m.group(2)))
        return d

    def flats(d, rev):
        n = len(next(iter(d.values())))
        if len({len(v) for v in d.values()}) != 1:
            return None
        hi = [max(v[j] for v in d.values()) + 1 for j in range(n)]
        r = {}
        for k, v in d.items():
            f = 0
            for j in range(n):
                x = (hi[j] - 1 - v[j]) if (rev and j == 0 and n > 1) else v[j]
                f = f * hi[j] + x
            r[f] = k
        return r if len(r) == len(d) else None

    def mismatches():
        m, kind = L.build(with_compare=False, with_hyp=False)
        val, mask = m.simulate(words, seed=4343)
        return sum(1 for k in L.matched if k.startswith("ff:") and
                   lit_val(val, mask, L.dlit[("gold", k)]) != lit_val(val, mask, L.dlit[("gate", k)]))

    def apply(mp):                                   # gate key -> gold key
        for tk, gk in mp.items():
            L.tp[gk] = L.tp.pop(tk)
            if tk in L.tc:
                L.tc[gk] = L.tc.pop(tk)
        L.matched = sorted(set(L.gp) & set(L.tp))
        L.gonly = sorted(set(L.gp) - set(L.tp))
        L.tonly = sorted(set(L.tp) - set(L.gp))

    galias = getattr(L, "galias", {})
    G, T = split(L.gonly), split(L.tonly)
    for gb, g in sorted(G.items()):
        votes = collections.Counter()
        for k in g:
            for a in galias.get(k, ()):
                m = IDX.match(a)
                if m and m.group(1) in T and m.group(1) != gb:
                    votes[m.group(1)] += 1
        for tb, n in votes.most_common(1):
            t = T[tb]
            if 2 * n < len(g) or 2 * len(t) < len(g) or len(t) > len(g):
                continue
            cands = []
            for gr in (False, True):
                for tr in (False, True):
                    fg, ft = flats(g, gr), flats(t, tr)
                    if fg and ft and set(ft) <= set(fg):
                        mp = {ft[f]: fg[f] for f in ft}
                        if mp not in cands:
                            cands.append(mp)
            if not cands:
                continue
            base = mismatches()
            best = None
            for mp in cands:
                apply(mp)
                n_ = mismatches()
                apply({v: k for k, v in mp.items()})
                if best is None or n_ < best[0]:
                    best = (n_, mp)
            if best[0] < base:
                apply(best[1])
                del T[tb]
                log.append(f"alias array: gate {tb.split('.')[-1]} ({len(t)} b) -> gold {gb.split('.')[-1]} "
                           f"({len(g)} b, Q-net alias evidence {n}); mismatching compare points {base} -> {best[0]}")


def correspond(L, work, conflicts, log, rounds=10, sim_iters=12, words=16):
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
    Unpaired flops stay free inputs."""
    alias_arrays(L, log)
    relayout(L, log)
    renamed(L, log)
    replica_proposals(L, log)
    tried = collections.Counter()      # failed attempts per candidate (a pair may fail while a neighbour is wrong)
    for rnd in range(rounds + 40):
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
                for k in L.gonly:
                    if not k.startswith("ff:") or ("gold", k) in L.hyp or k in partnered:
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
                            if tried[("gold", k, c, inv)] < 2:
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
            # a structural constant under the hypotheses now in place)
            for side, keys in (("gold", L.gonly), ("gate", L.tonly)):    # gate-only flops: constant candidates too
                for k in keys:
                    if k.startswith("ff:") and (side, k) not in L.hyp and k not in partners and \
                            (tried[(side, k, "c")] < 2 or L.dlit.get((side, k), 2) in (0, 1)):
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
        if not L.hyp:
            return
        m, kind = L.build(with_compare=False, with_hyp=True)
        st = prove(m, work, conflicts, log, tag=f"hyp{rnd}")
        bad = [n for n, s in st.items() if s != "proved"]
        (Path(work) / f"hyp{rnd}_failed.txt").write_text("".join(n + "\n" for n in bad))
        log.append(f"correspondence round {rnd}: {len(st)} hypotheses, {len(bad)} failed "
                   f"({sum(st[n] == 'undecided' for n in bad)} undecided) {bad[:6]}")
        if not bad:
            if L.hyp == before or not adding:
                return
            continue
        for n in bad:
            _, side, k = n.split(":", 2)
            side = "both" if side == "bothg" else side
            h = L.hyp.pop((side, k), None)
            if h is None:
                continue
            tried[(side, k, "c") if h[0] == "const" else (side, k, h[2], h[3])] += 1
    L.hyp.clear()                             # refinement did not converge: no assumptions at all
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
        np_ = sum(1 for v in status.values() if v == "proved")
        rec["counts"] = dict(compare_points=len(status), proved=np_,
                             differs=sum(1 for v in status.values() if v == "differs"),
                             undecided=sum(1 for v in status.values() if v == "undecided"))
        rec["failing"] = hard[:500]
        rec["unproven_points"] = soft[:500]
        if hard:
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
           "-v", f"{out}:/lecout", "-v", f"{me}:/lec.py:ro", "-e", f"HUID={os.getuid()}", "-e", f"HGID={os.getgid()}",
           image, "bash", "-lc"]
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
    return {"EQUIVALENT": 0, "NOT EQUIVALENT": 1, "LINT FAIL": 1, "UNPROVEN": 2}.get(r["verdict"], 3)


if __name__ == "__main__":
    sys.exit(main())
