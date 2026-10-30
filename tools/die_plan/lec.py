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
Hints (KIT/lec_hints.json or --hints; PATH-KV-PC4 10-25): untrusted register correspondences ('user match') for twins
        the signature search cannot find (rare-event bits, frontend array layouts); every hint is proved by the same
        induction and dropped if it fails, never a waiver (apply_hints).
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
import hashlib
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
# latch-based integrated clock gates modelled by the clock-gate -> enable abstraction (icg_to_enable); every ASAP7
# ICG drive strength has the same statetable: IQ = ENA | SE while CLK is low, held while high; GCLK = CLK & IQ
ICG_CELLS = re.compile(r"^ICGx(1|2|2p67DC|3|4|4DC|5|5p33DC|6p67DC|8DC)_ASAP7_75t_(R|L|SL)$")
# transparent-low latches (lockup latches, latch : enable "!CLK"): modelled by latch_to_wire (OT_LEC_LATCH=0 refuses)
LOCKUP_CELLS = re.compile(r"^DLLx(1|2|3)_ASAP7_75t_(R|L|SL)$")
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


def blackbox_local_constant_cleanup(env, kit):
    """Slang exports module-scope genvars and localparams as parameters even on blackboxed hard macros.

    Genvars and localparams cannot be overridden as module parameters. Remove only names
    literally declared as a genvar or localparam in that exact hard macro's source before replacing it by a pin-only stub.
    Formal parameters and unknown names remain untouched, so bad overrides still fail hierarchy checks.
    """
    commands = []
    files = [Path(kpath(kit, f)) for f in env["VERILOG_FILES"].split()]
    for master in env.get("SYNTH_BLACKBOXES", "").split():
        declarations = []
        for path in files:
            text = re.sub(r'"(?:\\.|[^"\\])*"|/\*.*?\*/|//[^\n]*', " ", path.read_text(), flags=re.S)
            match = re.search(r"\bmodule\s+" + re.escape(master) + r"\b(.*?)\bendmodule\b", text, re.S)
            if match:
                names = set()
                for declaration in re.findall(r"\bgenvar\s+([^;]+);", match.group(1)):
                    for name in declaration.split(","):
                        name = name.strip()
                        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", name):
                            names.add(name)
                for declaration in re.findall(r"\blocalparam\s+([^;]+);", match.group(1)):
                    names.update(re.findall(r"([A-Za-z_][A-Za-z0-9_$]*)\s*=", declaration))
                declarations.append(names)
        if declarations and all(names == declarations[0] for names in declarations):
            for name in sorted(declarations[0]):
                commands.append(f"setparam -unset {name} t:{master}")
    return commands


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
    if env.get("_LEC_ICG_GOLD_V"):        # ICG cells instantiated by the RTL: read_liberty skips them (statetable)
        cmds.append(f"read_verilog -sv {env['_LEC_ICG_GOLD_V']}")
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
        cmds += blackbox_local_constant_cleanup(env, kit)
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


def split_seq(env):
    """phase A / JSON rewrite / phase B is needed for clock gates and for lockup latches."""
    return bool(env.get("_LEC_ICG_V") or env.get("_LEC_LATCH"))


def seq_tail(out, lecff, icg):
    """SEQ_TAIL; with clock gates (icg) it is split at the clock-gate -> enable abstraction: phase A writes the
    flattened fine-grained design as JSON, icg_to_enable rewrites it, phase B (seq_tail_b) reads it back."""
    if not icg:
        return [c.format(lecff=lecff, out=out) for c in SEQ_TAIL]
    return [SEQ_TAIL[0], f"write_json {out}.preicg.json"]


def seq_tail_b(out, lecff):
    return "\n".join([f"read_json {out}.icg.json", f"hierarchy -top {WRAP}"] +
                     [c.format(lecff=lecff, out=out) for c in SEQ_TAIL[1:]]) + "\n"


def gold_script(env, kit, frontend, lib_bbs, stubs, wrap, lecff, out, slang_extra=()):
    s = read_rtl_cmds(env, kit, frontend, lib_bbs, chparam=False, slang_extra=slang_extra)
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
          "select -clear", f"write_json {out}.aliases.json",
          # -nordff: memory_dff would merge an address / data register into a synchronous read port, and memory_map
          # then re-creates it as an anonymous '$...$rdreg' flop that no key point names (kv3_astk zn sd[k]: the
          # zq[5:2] address register became 4 unnamed gold latches, so every oa bit was UNPROVEN); the reference keeps
          # the RTL registers as written and an asynchronous read port
          "memory -nomap -nordff", "memory_map", "opt_expr -keepdc", "opt_clean",
          "techmap", "opt_clean"]
    return "\n".join(s + seq_tail(out, lecff, split_seq(env))) + "\n"


# Formal preparation must retain every FF already present in the physical netlist.
# Flatten discards wrapper keep attributes; opt_clean otherwise deletes unloaded
# but physically required copies and produces a false KEEP failure. This does not
# create a register or forgive a synthesis merge: a missing physical FF stays absent.
GATE_PHYSICAL_FF_KEEP = "setattr -set keep 1 t:$*ff* t:$_*FF*_"


def gate_script(env, netlist, stubs, wrap, lecff, out):
    s = [f"read_liberty -ignore_miss_func {NLDM}/{l}" for l in STD_LIBS]
    s += [f"read_verilog {env['_LEC_ICG_V']}"] if env.get("_LEC_ICG_V") else []
    s += [f"read_verilog {stubs}", f"read_verilog {netlist}", f"read_verilog {wrap}", f"hierarchy -check -top {WRAP}",
          "setattr -mod -unset keep_hierarchy", "setattr -unset keep_hierarchy", "proc",
          GATE_PHYSICAL_FF_KEEP, "flatten -noscopeinfo", "opt_clean", "techmap", "opt_clean"]
    return "\n".join(s + seq_tail(out, lecff, split_seq(env))) + "\n"


# ---------------------------------------------------------------------------------------------- clock gates
def icg_verilog(cells):
    """black-box definitions of the ICG cells (read_liberty skips statetable cells); never a stub: icg_to_enable
    removes every instance before the AIG is written."""
    return "".join(f"(* blackbox *) module {c} (input CLK, input ENA, input SE, output GCLK); endmodule\n"
                   for c in sorted(cells))


FF_TYPE = re.compile(r"^\$_(DFF|DFFE|SDFF|SDFFE|SDFFCE|DFFSR|DFFSRE|ALDFF|ALDFFE)_([NP])([NP01]*)_$")
LATCH_TYPE = re.compile(r"^\$_(DLATCH|DLATCHSR|SR)_")


def icg_to_enable(src, dst, side):
    """Clock-gate -> enable abstraction (the standard commercial-LEC model of a latch-based ICG), applied
    identically to gold and gate on the flattened fine-grained design (JSON src -> dst); returns statistics.

    A latch-based ICG (statetable: IQ = ENA | SE transparent while CLK is low; GCLK = CLK & IQ) gives a rising
    GCLK edge at a rising CLK edge iff ENA | SE held during the preceding low phase.  When ENA / SE are functions
    of primary inputs and of state that changes only at rising edges of the same root clock, that value is the
    value an enable flop on the root clock samples at the same edge, so: a rising-edge flop clocked by GCLK ==
    the same flop on CLK whose clocked update (data, enable, sync reset) is additionally enabled by ENA | SE
    (async set / reset untouched).  A black-box clock pin on GCLK becomes the compare point ENA | SE (edge iff
    enabled; every other pin is compared every cycle).  Refused (Unproven), never approximated: a GCLK load that is
    not a rising-edge flop clock or a black-box clock pin (logic, port, falling-edge flop, latch, memory, another
    ICG = cascaded gates), a CLK that is not a primary input (derived / gated clock), and an ENA / SE cone that
    reads a clock net, a latch, a falling-edge flop, an unknown cell or a flop of another clock.  Asynchronous set /
    reset / load (in a gated flop or in the enable cone) keep the synchronous async2sync model of the rest of LEC."""
    d = json.loads(Path(src).read_text())
    tops = [k for k, v in d["modules"].items() if str(v.get("attributes", {}).get("top", "0")).strip("0") != ""]
    if len(tops) != 1:
        raise LecError(f"icg {side}: {len(tops)} top modules in {src}")
    m = d["modules"][tops[0]]
    cells = m["cells"]
    nxt = [1 + max([b for n in m["netnames"].values() for b in n["bits"] if isinstance(b, int)] +
                   [b for p in m["ports"].values() for b in p["bits"] if isinstance(b, int)] + [1])]
    name_of = {}
    for n, w in m["netnames"].items():
        for b in w["bits"]:
            if isinstance(b, int):
                name_of.setdefault(b, n)
    pis = {b for p in m["ports"].values() if p["direction"] == "input" for b in p["bits"] if isinstance(b, int)}
    pos = {b for p in m["ports"].values() if p["direction"] != "input" for b in p["bits"] if isinstance(b, int)}
    drv, loads = {}, collections.defaultdict(list)
    for cn, c in cells.items():
        for p, bits in c["connections"].items():
            out = c.get("port_directions", {}).get(p) == "output"
            for i, b in enumerate(bits):
                if isinstance(b, int):
                    if out:
                        drv[b] = (cn, p)
                    else:
                        loads[b].append((cn, p, i))
    icgs = {cn: c for cn, c in cells.items() if ICG_CELLS.match(c["type"])}
    st = dict(gates=len(icgs), gated_flops=0, gated_bb_clock_pins=0, per_gate={}, flop_types={})
    if not icgs:
        Path(dst).write_text(json.dumps(d))
        return st

    def bit(cn, p):
        b = cells[cn]["connections"].get(p, ["x"])
        if len(b) != 1:
            raise Unproven(f"icg {side}: {cn}.{p} is not a single bit")
        return b[0]

    def through_bufs(b):
        while isinstance(b, int) and b in drv and cells[drv[b][0]]["type"] == "$_BUF_":
            b = cells[drv[b][0]]["connections"]["A"][0]
        return b

    gclk_of = {}                          # GCLK bit (and $_BUF_ copies) -> ICG cell
    for cn in icgs:
        g, todo = bit(cn, "GCLK"), []
        if isinstance(g, int):
            todo.append(g)
        while todo:
            b = todo.pop()
            gclk_of[b] = cn
            todo += [cells[l]["connections"]["Y"][0] for l, p, i in loads.get(b, ()) if cells[l]["type"] == "$_BUF_"]
    root = {}
    for cn in icgs:
        r = through_bufs(bit(cn, "CLK"))
        if r in gclk_of:
            raise Unproven(f"icg {side}: cascaded clock gates ({gclk_of[r]} GCLK drives {cn}.CLK): not modelled")
        if r not in pis:
            raise Unproven(f"icg {side}: {cn}.CLK is not driven by a primary input ({name_of.get(r, r)}): not modelled")
        root[cn] = r

    def ff_root(cn):
        """root clock bit of a flop / None for the LEC's own stub and wrapper flops (lec_clk, undriven)."""
        r = through_bufs(cells[cn]["connections"]["C"][0])
        if r in gclk_of:
            return root[gclk_of[r]]
        if r in pis:
            return r
        q = cells[cn]["connections"].get("Q", [None])[0]
        if r not in drv and re.search(r"(^|\.)lec_(bbo|bbi|po)_", str(name_of.get(q, ""))):
            return None
        raise Unproven(f"icg {side}: flop {cn} has a clock that is neither a primary input nor a modelled gate")

    clock_bits = set(pis & {root[c] for c in icgs}) | set(gclk_of)
    for cn, c in cells.items():
        if FF_TYPE.match(c["type"]):
            clock_bits.add(c["connections"]["C"][0])

    def check_cone(cn, b0, r):
        seen, todo = set(), [b0]
        while todo:
            b = todo.pop()
            if not isinstance(b, int) or b in seen:
                continue
            seen.add(b)
            if b in clock_bits:
                raise Unproven(f"icg {side}: {cn} enable reads a clock net ({name_of.get(b, b)}): not modelled")
            if b in pis or b not in drv:
                continue
            dn, dp = drv[b]
            t = cells[dn]["type"]
            f = FF_TYPE.match(t)
            if f:
                if f[2] != "P":
                    raise Unproven(f"icg {side}: {cn} enable reads {t} {dn} (not a rising-edge flop)")
                fr = ff_root(dn)
                if fr is not None and fr != r:
                    raise Unproven(f"icg {side}: {cn} enable reads flop {dn} of another clock")
                continue
            if LATCH_TYPE.match(t) or not t.startswith("$_") or ICG_CELLS.match(t):
                raise Unproven(f"icg {side}: {cn} enable reads {t} {dn}: not modelled")
            todo += [x for p, bits in cells[dn]["connections"].items()
                     if cells[dn].get("port_directions", {}).get(p) != "output" for x in bits]
        return len(seen)

    def newcell(t, conns, outp="Y"):
        y = nxt[0]
        nxt[0] += 1
        cells[f"$lec_icg${y}"] = {"hide_name": 1, "type": t, "parameters": {}, "attributes": {},
                                  "port_directions": {p: ("output" if p == outp else "input") for p in conns},
                                  "connections": {p: ([y] if p == outp else [v]) for p, v in conns.items()}}
        return y

    def and_(a, b):
        if a == "0" or b == "0":
            return "0"
        if a == "1":
            return b
        if b == "1":
            return a
        return newcell("$_AND_", {"A": a, "B": b, "Y": None})

    def or_(a, b):
        if a == "1" or b == "1":
            return "1"
        if a == "0":
            return b
        if b == "0":
            return a
        return newcell("$_OR_", {"A": a, "B": b, "Y": None})

    def act(sig, pol):                    # active-high form of a control of polarity pol
        if pol == "P":
            return sig
        if sig in ("0", "1"):
            return "1" if sig == "0" else "0"
        return newcell("$_NOT_", {"A": sig, "Y": None})

    mem_wclk = {}                         # $mem_v2 -> original write-port clock identities

    def gate_mem_port(cn, ln, lp, li, en):
        """LEC-FPREG-7 10-27 (S81 dsfd_cfifo_crs4: slot ICG GCLK -> bank $mem_v2 WR_CLK): a rising-edge clocked
        memory port on GCLK == the same port on the root clock with its enables ANDed with ENA | SE (the flop rule
        applied to the port's write / read-enable bits).  Refused: falling-edge or unclocked write port, a clocked
        read port with a sync / async reset, and another write port on a different clock unless both are
        gated from the same root and write constant, distinct addresses."""
        c = cells[ln]
        P, pc = c["parameters"], c["connections"]
        ival = lambda v: int(v, 2) if isinstance(v, str) else int(v)

        def pbit(name, i):
            v = P.get(name, "0")
            b = v if isinstance(v, str) else format(int(v), "b")
            return b.rjust(i + 1, "0")[-1 - i] == "1"
        kind = lp[:2]
        if kind == "WR":
            if not (pbit("WR_CLK_ENABLE", li) and pbit("WR_CLK_POLARITY", li)):
                raise Unproven(f"icg {side}: {cn} GCLK clocks {ln} write port {li} that is not rising-edge clocked")
            wclk = mem_wclk.setdefault(ln, [gclk_of.get(b, through_bufs(b)) for b in pc["WR_CLK"]])  # before rewrites
            ab = ival(P["ABITS"])
            addr = lambda j: pc["WR_ADDR"][j * ab:(j + 1) * ab]
            for j, cb in enumerate(wclk):
                if j == li or not pbit("WR_CLK_ENABLE", j) or cb == wclk[li]:
                    continue
                # another write port on a different (gated) clock: kept only when it is gated from the SAME root and
                # both ports write constant, different addresses (crs4 ot_s81_land GSLOT ring: slot s writes bank[s]
                # through its own ICG), so no write-write collision order is ever needed after the move to the root
                rj = root[cb] if cb in icgs else cb
                ca, cj = addr(li), addr(j)
                if rj != root[cn] or not all(str(x) in "01" for x in ca + cj) or [str(x) for x in ca] == \
                        [str(x) for x in cj]:
                    raise Unproven(f"icg {side}: {ln} write ports {li}/{j} on different clocks (not one root with "
                                   f"constant distinct addresses): not modelled")
            w = ival(P["WIDTH"])
            pc["WR_EN"][li * w:(li + 1) * w] = [and_(en, b) for b in pc["WR_EN"][li * w:(li + 1) * w]]
        elif pbit("RD_CLK_ENABLE", li):
            if not pbit("RD_CLK_POLARITY", li):
                raise Unproven(f"icg {side}: {cn} GCLK clocks {ln} read port {li} on its falling edge: not modelled")
            if any(str(pc.get(x, ["0"] * (li + 1))[li]) != "0" for x in ("RD_SRST", "RD_ARST")):
                raise Unproven(f"icg {side}: {cn} GCLK clocks {ln} read port {li} with a reset: not modelled")
            pc["RD_EN"][li] = and_(en, pc["RD_EN"][li])
        pc[lp][li] = root[cn]
        st["gated_mem_ports"] = st.get("gated_mem_ports", 0) + 1
        st["per_gate"][cn]["mem_ports"] = st["per_gate"][cn].get("mem_ports", 0) + 1

    eff = {}
    for cn in sorted(icgs):
        r = root[cn]
        n = check_cone(cn, bit(cn, "ENA"), r) + check_cone(cn, bit(cn, "SE"), r)
        eff[cn] = or_(bit(cn, "ENA"), bit(cn, "SE"))
        st["per_gate"][cn] = dict(type=icgs[cn]["type"], clk=name_of.get(r, str(r)), enable_cone_nets=n, flops=0,
                                  bb_clock_pins=0)
    for g, cn in sorted(gclk_of.items(), key=lambda x: str(x)):
        en = eff[cn]
        for ln, lp, li in list(loads.get(g, ())):
            c = cells[ln]
            t = c["type"]
            if t == "$_BUF_":
                continue
            f = FF_TYPE.match(t)
            pc = c["connections"]
            q = pc.get("Q", [None])[0] if f else None
            if f and lp == "D" and re.search(r"(^|\.)lec_bbi_", str(name_of.get(q, ""))):
                pc["D"] = [en]               # black-box clock pin: compare 'an edge reaches the macro'
                st["gated_bb_clock_pins"] += 1
                st["per_gate"][cn]["bb_clock_pins"] += 1
                continue
            if t == "$mem_v2" and lp in ("WR_CLK", "RD_CLK"):
                gate_mem_port(cn, ln, lp, li, en)
                continue
            if not f or lp != "C" or f[2] != "P":
                raise Unproven(f"icg {side}: {cn} GCLK reaches {t} {ln}.{lp}[{li}] (only rising-edge flop clocks, "
                               f"$mem_v2 clocked ports and black-box clock pins are modelled)")
            kind, ctl = f[1], f[3]
            if kind == "DFF" and ctl == "":
                c["type"] = "$_DFFE_PP_"
                pc["E"] = [en]
            elif kind == "DFF":                                            # async reset: untouched by the clock
                c["type"] = f"$_DFFE_P{ctl}P_"
                pc["E"] = [en]
            elif kind == "DFFE":
                c["type"] = f"$_DFFE_P{ctl[:-1]}P_"
                pc["E"] = [and_(en, act(pc["E"][0], ctl[-1]))]
            elif kind == "SDFF":                                           # sync reset is clocked: gated too
                c["type"] = f"$_SDFFCE_P{ctl}P_"
                pc["E"] = [en]
            elif kind == "SDFFCE":
                c["type"] = f"$_SDFFCE_P{ctl[:-1]}P_"
                pc["E"] = [and_(en, act(pc["E"][0], ctl[-1]))]
            elif kind == "SDFFE":                                          # reset over enable: CE = en & (R | E)
                c["type"] = f"$_SDFFCE_P{ctl[:-1]}P_"
                pc["E"] = [and_(en, or_(act(pc["R"][0], ctl[0]), act(pc["E"][0], ctl[-1])))]
            elif kind == "DFFSR":
                c["type"] = f"$_DFFSRE_P{ctl}P_"
                pc["E"] = [en]
            elif kind == "ALDFF":                                          # async load: untouched by the clock
                c["type"] = f"$_ALDFFE_P{ctl}P_"
                pc["E"] = [en]
            elif kind == "ALDFFE":
                c["type"] = f"$_ALDFFE_P{ctl[:-1]}P_"
                pc["E"] = [and_(en, act(pc["E"][0], ctl[-1]))]
            elif kind == "DFFSRE":
                c["type"] = f"$_DFFSRE_P{ctl[:-1]}P_"
                pc["E"] = [and_(en, act(pc["E"][0], ctl[-1]))]
            else:
                raise Unproven(f"icg {side}: {cn} GCLK clocks {t} {ln}: not modelled")
            pc["C"] = [root[cn]]
            c.setdefault("port_directions", {})["E"] = "input"
            st["gated_flops"] += 1
            st["per_gate"][cn]["flops"] += 1
            st["flop_types"][t] = st["flop_types"].get(t, 0) + 1
        if g in pos:
            raise Unproven(f"icg {side}: {cn} GCLK is a module output: not modelled")
    for cn in icgs:
        del cells[cn]
    for k in [k for k, v in d["modules"].items() if ICG_CELLS.match(k)]:
        del d["modules"][k]
    Path(dst).write_text(json.dumps(d))
    return st


def latch_to_wire(src, dst, side):
    """Lockup-latch abstraction (JSON src -> dst, both sides): a transparent-low latch ($_DLATCH_N_ with E = a
    primary-input clock, or $_DLATCH_P_ with E = NOT(that clock): the ASAP7 DLL liberty model) whose data cone
    holds only primary inputs, constants and rising-edge flops on primary-input clocks, and whose Q reaches (through
    combinational logic only) nothing but synchronous pins (D / E / sync R) of rising-edge flops on primary-input
    clocks, is a wire in the cycle model: its sources change only at rising edges, it is transparent for the low
    phase before the next rising edge, and its readers sample only at that edge -> they see D of the same cycle.
    The high-phase hold value is never sampled (hold / phase timing is STA's).  Refused (Unproven), never
    approximated: transparent-high latches, an enable that is not a (buffered / inverted) primary input, a data
    source that is a latch / falling-edge flop / clock net / unknown cell / LEC stub, a Q load that is a clock or
    async pin, a falling-edge flop, a latch, a module output, a black-box compare pin, memory or unknown cell."""
    d = json.loads(Path(src).read_text())
    tops = [k for k, v in d["modules"].items() if str(v.get("attributes", {}).get("top", "0")).strip("0") != ""]
    if len(tops) != 1:
        raise LecError(f"latch {side}: {len(tops)} top modules in {src}")
    m = d["modules"][tops[0]]
    cells = m["cells"]
    name_of = {}
    for n, w in m["netnames"].items():
        for b in w["bits"]:
            if isinstance(b, int):
                name_of.setdefault(b, n)
    pis = {b for p in m["ports"].values() if p["direction"] == "input" for b in p["bits"] if isinstance(b, int)}
    pos = {b for p in m["ports"].values() if p["direction"] != "input" for b in p["bits"] if isinstance(b, int)}
    drv, loads = {}, collections.defaultdict(list)
    for cn, c in cells.items():
        for p, bits in c["connections"].items():
            out = c.get("port_directions", {}).get(p) == "output"
            for i, b in enumerate(bits):
                if isinstance(b, int):
                    if out:
                        drv[b] = (cn, p)
                    else:
                        loads[b].append((cn, p, i))
    lats = {cn: c for cn, c in cells.items() if LATCH_TYPE.match(c["type"])}
    st = dict(latches=len(lats), to_wire=0, per_latch={})
    if not lats:
        Path(dst).write_text(json.dumps(d))
        return st

    def one(cn, p):
        b = cells[cn]["connections"].get(p, ["x"])
        if len(b) != 1:
            raise Unproven(f"latch {side}: {cn}.{p} is not a single bit")
        return b[0]

    def const_mux(cn):                    # $_MUX_ / $_NMUX_ with constant data pins = a BUF / NOT of S, else None
        c = cells[cn]
        if c["type"] not in ("$_MUX_", "$_NMUX_"):
            return None
        a, b = c["connections"].get("A", [None])[0], c["connections"].get("B", [None])[0]
        if (a, b) not in (("0", "1"), ("1", "0")):
            return None
        return (a == "1") ^ (c["type"] == "$_NMUX_")      # Y = S ? B : A: inverted when A = 1 (MUX) / A = 0 (NMUX)

    def through(b, inv=False):            # through $_BUF_ (and $_NOT_ when inv): -> (bit, inverted)
        # also through a constant-data $_MUX_ / $_NMUX_: the RTL frontend's unoptimised "!clk" (S ? 1'b0 : 1'b1) on
        # an always_latch enable (S81 R21b u_view c_lk, LEC-FPREG-4 10-27)
        neg = False
        while isinstance(b, int) and b in drv:
            cn = drv[b][0]
            t = cells[cn]["type"]
            if t in (("$_BUF_", "$_NOT_") if inv else ("$_BUF_",)):
                neg ^= t == "$_NOT_"
                b = cells[cn]["connections"]["A"][0]
                continue
            cm = const_mux(cn)
            if cm is None or (cm and not inv):
                break
            neg ^= cm
            b = cells[cn]["connections"]["S"][0]
        return b, neg

    stub = re.compile(r"(^|\.)lec_(bbo|bbi|po)_")

    def rise_ff(cn):
        """a rising-edge flop on a primary-input clock (no LEC stub / wrapper flop) -> its FF_TYPE match, else None."""
        f = FF_TYPE.match(cells[cn]["type"])
        if not f or f[2] != "P":
            return None
        if through(cells[cn]["connections"]["C"][0])[0] not in pis:
            return None
        if stub.search(str(name_of.get(cells[cn]["connections"].get("Q", [None])[0], ""))):
            return None
        return f

    clock_bits = set()
    for cn, c in cells.items():
        if FF_TYPE.match(c["type"]):
            clock_bits.add(through(c["connections"]["C"][0])[0])
    ff_clocks = set(clock_bits)          # a latch enable must be a clock of some flop, not any input
    for cn in lats:
        clock_bits.add(through(one(cn, "E"), True)[0])

    # The RTL frontend writes always_latch if (!clk) q = d as D = $_MUX_(S = clk, A = d, B = x / q): a latch only
    # reads D while transparent, so the branch S selects in the transparent phase IS the latch data (S81 R21b
    # u_view c_lk, LEC-FPREG-4 10-27).  Only a $_MUX_ driving D directly whose select is this latch's own enable
    # clock (through BUF / NOT) is resolved; any other select stays in the data cone (a clock read -> Unproven).
    dsel = {}                            # latch -> its transparent-phase data bit (phase mux resolved)
    for cn in lats:
        d_in = one(cn, "D")
        if isinstance(d_in, int) and d_in in drv and cells[drv[d_in][0]]["type"] == "$_MUX_":
            mc = cells[drv[d_in][0]]["connections"]
            sb, sneg = through(mc["S"][0], True)
            if sb == through(one(cn, "E"), True)[0]:   # transparent while E's clock = 0: S = sneg -> B (1) / A (0)
                dsel[cn] = mc["B" if sneg else "A"][0]
    # Latch chains (S81 R21b: io_clk go lockup latch -> core logic -> ck seam lockup latch, LEC-FPREG-4 10-27): every
    # latch here is transparent-low on a primary-input clock (each is checked in its own iteration, and any failure
    # refuses the whole netlist), so in the low phase of one cycle the data of a rising-edge flop passes the whole
    # chain and the rising-edge readers sample it: the chain is a wire like one latch.  The data cone therefore
    # passes through another latch to its (phase-resolved) D, the Q fan-out through another latch's D to its Q; a
    # chain that returns to the latch itself is a combinational loop after the abstraction -> Unproven.
    for cn in sorted(lats):
        c = cells[cn]
        t = c["type"]
        e, neg = through(one(cn, "E"), True)
        if t not in ("$_DLATCH_N_", "$_DLATCH_P_") or e not in pis or e not in ff_clocks or (t == "$_DLATCH_P_") != neg:
            raise Unproven(f"latch {side}: {t} {cn} is not a transparent-low latch on a primary-input clock")
        d_in = dsel.get(cn, one(cn, "D"))
        seen, todo, srcs = set(), [d_in], 0
        while todo:                        # data cone
            b = todo.pop()
            if not isinstance(b, int) or b in seen:
                continue
            seen.add(b)
            if b in clock_bits:
                raise Unproven(f"latch {side}: {cn} data reads a clock net ({name_of.get(b, b)})")
            if b in pis or b not in drv:
                srcs += 1
                continue
            dn, dp = drv[b]
            if dn in lats:                 # chained latch: its own transparent-phase data
                if dn == cn:
                    raise Unproven(f"latch {side}: {cn} data reaches its own Q (latch loop)")
                todo.append(dsel.get(dn, one(dn, "D")))
                continue
            if FF_TYPE.match(cells[dn]["type"]):
                if not rise_ff(dn):
                    raise Unproven(f"latch {side}: {cn} data reads {cells[dn]['type']} {dn} (not a rising-edge flop "
                                   f"on a primary-input clock)")
                srcs += 1
                continue
            if not re.match(r"^\$_(BUF|NOT|AND|NAND|OR|NOR|XOR|XNOR|ANDNOT|ORNOT|MUX|NMUX|AOI3|OAI3|AOI4|OAI4)_$",
                            cells[dn]["type"]):
                raise Unproven(f"latch {side}: {cn} data reads {cells[dn]['type']} {dn}: not modelled")
            todo += [x for p, bits in cells[dn]["connections"].items()
                     if cells[dn].get("port_directions", {}).get(p) != "output" for x in bits]
        q = one(cn, "Q")
        seen2, todo, sinks = set(), [q], 0
        while todo:                        # Q fan-out
            b = todo.pop()
            if not isinstance(b, int) or b in seen2:
                continue
            seen2.add(b)
            if b in pos:
                raise Unproven(f"latch {side}: {cn} Q reaches module output {name_of.get(b, b)}")
            for ln, lp, li in loads.get(b, ()):
                lt = cells[ln]["type"]
                if ln in lats and lp == "D":   # chained latch: continue from its Q
                    if ln == cn:
                        raise Unproven(f"latch {side}: {cn} Q reaches its own D (latch loop)")
                    todo.append(one(ln, "Q"))
                    continue
                f = FF_TYPE.match(lt)
                if f:
                    ok = rise_ff(ln) and (lp in ("D", "E") or (lp == "R" and f[1].startswith("SDFF")))
                    if not ok:
                        raise Unproven(f"latch {side}: {cn} Q reaches {lt} {ln}.{lp} (only D / E / sync R of "
                                       f"rising-edge flops on primary-input clocks are modelled)")
                    sinks += 1
                    continue
                if not re.match(r"^\$_(BUF|NOT|AND|NAND|OR|NOR|XOR|XNOR|ANDNOT|ORNOT|MUX|NMUX|AOI3|OAI3|AOI4|OAI4)_$",
                                lt):
                    raise Unproven(f"latch {side}: {cn} Q reaches {lt} {ln}.{lp}: not modelled")
                todo += [x for p, bits in cells[ln]["connections"].items()
                         if cells[ln].get("port_directions", {}).get(p) == "output" for x in bits]
        if q in clock_bits:
            raise Unproven(f"latch {side}: {cn} Q is a clock net")
        st["per_latch"][cn] = dict(type=t, clk=name_of.get(e, str(e)), data_sources=srcs, sinks=sinks,
                                   phase_mux=cn in dsel)
    st["phase_mux"] = len(dsel)
    for cn in sorted(lats):               # all checked first: then each latch -> $_BUF_ D -> Q
        c = cells[cn]
        cells[cn] = {"hide_name": c.get("hide_name", 1), "type": "$_BUF_", "parameters": {}, "attributes": {},
                     "port_directions": {"A": "input", "Y": "output"},
                     "connections": {"A": [dsel.get(cn, one(cn, "D"))], "Y": [one(cn, "Q")]}}
        st["to_wire"] += 1
    Path(dst).write_text(json.dumps(d))
    return st


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
        # Generated ROM metadata must remain legal when the pin-model stub
        # replaces the native BB. Unknown parameter names still fail hierarchy.
        if re.fullmatch(r"ot_rom_[0-9]+x[0-9]+_m[0-9]+", mod):
            out.append('  parameter VIAMAP = "", INSTANCE = "";')
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
        # Expanding every prefix of a wide CRC makes normalization quadratic.
        # Above this support size keep the exact ordinary AIG XOR; SAT still
        # proves the same Boolean function without an expanded parity cache.
        self.parity_terms = max(2, int(os.environ.get("OT_LEC_PARITY_TERMS", "256")))

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
        if len(aa) + len(bb) > self.parity_terms:
            return self._and(self._and(a, b ^ 1) ^ 1, self._and(a ^ 1, b) ^ 1) ^ 1
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
        self.galias = galias
        self.tp, self.tc, self.tx, self.tanon, _ = key_points(gate, tmap)
        # a gold register whose Q net also carries the name the gate flop was given (synthesis named the flop after
        # an alias, e.g. the output port it drives): re-key it to that name
        tfree = set(self.tp) - set(self.gp)
        self.aliased = []
        for k in sorted(set(self.gp) - set(self.tp)):
            hit = sorted(galias.get(k, set()) & tfree)
            # A scalar register can drive an unpacked array element. Slang flattens that
            # Q-wire array in reverse element order, while read_verilog names the gate
            # flop with the actual element index (cf_o -> cf[1] in the HBM indexer).
            # Its flat alias bit is not an element identity. Leave scalar-to-indexed
            # aliases for function-based correspondence and its inductive proof.
            if not IDX.match(k):
                hit = [a for a in hit if not IDX.match(a)]
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
        # OT_LEC_SUPERSET_VEC=1 (opt-in, default off): a 1-D vector whose gate bits are a strict superset of the gold
        # bits (the gold frontend dropped dead bits the gate kept, e.g. inside a keep_hierarchy cell) is laid out
        # identically on both sides; keep the common bit names and re-key only the gate-only extra bits.  Every
        # name match is still a correspondence obligation, so a wrong pairing can only fail, never hide a difference.
        superset_vec = os.environ.get("OT_LEC_SUPERSET_VEC") == "1"
        one_dim = lambda s: all(ix.count("[") == 1 for ix in s)
        self.superset_extra = []                  # [(gate bit, re-keyed gate key)]: the per-run list (lec.json)
        for b in self.relaid:
            sub = superset_vec and gidx[b] < tidx[b] and one_dim(tidx[b])
            for ix in tidx[b]:
                if sub and ix in gidx[b]:
                    continue
                if sub:
                    self.superset_extra.append((b + ix, f"{b}#t{ix}"))
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
        self.cycle_dropped = []                   # (node, hypothesis) dropped by build() to break a binding cycle

    def _drop_cycle_hyp(self, pend):
        """pend: unresolved hypothesis node -> the node it is bound to.  No pass made progress, so every walk along
        the bindings either closes a cycle or ends at a node that is never bound in this pass (e.g. a 'cube' state
        bit).  Drop exactly one hypothesis: on a cycle its largest key (the cycle's other equalities still relate all
        its members; a wrong one is refuted by the induction like any other), on a dead end the node bound to it.
        Dropping a hypothesis only removes an assumption: the flop becomes a free input, never a waiver.
        -> [dropped node]"""
        node, seen = min(pend), []
        while node in pend and node not in seen:
            seen.append(node)
            node = pend[node]
        drop = max(seen[seen.index(node):]) if node in seen else seen[-1]
        self.cycle_dropped.append((drop, self.hyp.pop(drop)))
        return [drop]

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
            if len(nxt) == len(merged):           # a cycle: drop ONE hypothesis on it (a free matched input)
                pend = {("both", k): ("both", self.hyp[("both", k)][2]) for k in nxt}
                (_, k), = self._drop_cycle_hyp(pend)
                nxt.remove(k)
                v = m.add_input(k)
                kind[v >> 1] = ("matched", k)
                shared[k] = v
                bind(lg, self.gp[k], v)
                bind(lt, self.tp[k], v)
            merged = nxt
        later = []
        loaded = []                               # 'loaded' hypotheses: bound after every input (guard ANDs)
        # A gold-only register whose next state is its own Q is never written (no reset, no load): slang pads a
        # non-power-of-two unpacked array (rg_d[0:4] -> 8 words) with such words, where read_verilog reads X.
        # An ASAP7 flop has no power-up value, so the register holds X: a gold X source, never the constant 0
        # that write_aiger -zinit gives it (LEC-ICG-2 10-26: 27 qxpq cfg_d bits differed only at rg_s >= 5,
        # unreachable since rk <= 17; RTL-vs-netlist co-simulation 0 mismatches)
        self.unwritten = sorted(k for k in self.gonly if k.startswith("ff:") and self.gc.get(k) == self.gp[k])
        unwritten = set(self.unwritten)
        self.fill_live = fill_live(self.hyp)      # pipeline-fill hints whose ghost chain reaches its constant root
        self.fill_in = {}                         # gold key -> ghost 'filled' input literal
        fillq = []
        for side, keys, p, lmap in (("gold", self.gonly, self.gp, lg), ("gate", self.tonly, self.tp, lt)):
            for k in keys:
                h = self.hyp.get((side, k))
                if side == "gold" and k in unwritten:
                    v = m.add_input(f"gold:{k}")
                    kind[v >> 1] = ("gold_x", k)
                    bind(lmap, p[k], v)
                    lgx[p[k] & ~1] = 1
                elif h and h[0] == "fill" and side == "gold" and k in self.fill_live:
                    # Q = filled ? c : X.  'filled' is a tool-owned ghost bit (not RTL state): filled' = filled(pred),
                    # the root's filled' = 1, so every ghost is 1 a chain-length of edges after the reset state and
                    # X is never held as a constant: an unfilled register is X (its RTL power-up value) and a compare
                    # point reading it is a don't care only while the register really is X in the RTL.
                    f = m.add_input(f"fill:{k}")
                    kind[f >> 1] = ("fill", k)
                    v = m.add_input(f"gold:{k}")
                    kind[v >> 1] = ("gold_x", k)
                    self.fill_in[k] = f
                    fillq.append((k, h, f, v))      # bound after every input (the mux is ANDs)
                elif h and h[0] == "const":
                    bind(lmap, p[k], h[1])
                elif h and h[0] in ("eq", "cube"):
                    later.append((side, k, h))
                elif h and h[0] == "loaded" and side == "gold":
                    v = m.add_input(f"gold:{k}")        # its power-up value: free wherever the guard is false
                    kind[v >> 1] = ("gold_only", k)
                    bind(lmap, p[k], v)
                    loaded.append((k, h, v))
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
            if len(nxt) == len(later):            # a cycle: drop ONE hypothesis on it (that flop a free input)
                pend = {(side, k): (h[1], h[2]) for side, k, h in nxt}
                (side, k), = self._drop_cycle_hyp(pend)
                nxt = [e for e in nxt if (e[0], e[1]) != (side, k)]
                lmap, p = (lg, self.gp) if side == "gold" else (lt, self.tp)
                v = m.add_input(f"{side}:{k}")
                kind[v >> 1] = (side + "_only", k)
                bind(lmap, p[k], v)
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
        for k, h, f, v in fillq:                  # Q = filled ? c : X (gold X rail = not filled)
            bind(lg, self.gp[k], m.AND(m.AND(f, h[1]) ^ 1, m.AND(f ^ 1, v) ^ 1) ^ 1)
            lgx[self.gp[k] & ~1] = f ^ 1
        lkeys = {k for k, _, _ in loaded}
        for k, h, v in loaded:                    # Q = guard ? c : power-up value (loaded-valid qualification)
            if any(key in lkeys for cube in h[2] for key, _ in cube):
                raise LecError(f"loaded guard of {k} reads another loaded register")
            g = guard_lit(m, h[2], lambda key: lg[self.gp[key] & ~1] ^ (self.gp[key] & 1))
            bind(lg, self.gp[k], (m.AND(g ^ 1, v ^ 1) ^ 1) if h[1] else m.AND(g ^ 1, v))
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
        self.dxlit = {k: lgx.get(self.gc[k] & ~1, 0) for k in self.gc}   # gold next state of k is X (sim_refine)
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
                    # A recoded FSM bit represents a predicate over the gold state.
                    # Preserve the same X semantics used for eq/const hypotheses.
                    # An AND is known if all atoms are known OR one known atom is false.
                    known, false_known = 1, 0
                    if oside == "gold":
                        for ok, ov in zip(oks, ovals):
                            atom = self.dlit[(oside, ok)] ^ (ov ^ 1)
                            known = m.AND(known, nx(ok))
                            false_known = m.AND(false_known ^ 1, m.AND(atom ^ 1, nx(ok)) ^ 1) ^ 1
                    known = m.AND(known ^ 1, false_known ^ 1) ^ 1
                    m.outs.append(m.AND(m.XOR(d, c), known))
                    m.onames.append(f"hyp:{side}:{k}")
                    continue
                if h[0] == "loaded":
                    # next state: guard' (or a guard register's next state X) -> D(k) == c and not X
                    gn = guard_lit(m, h[2], lambda key: self.dlit[("gold", key)])
                    anyx = 0
                    for cube in h[2]:
                        for key, _ in cube:
                            anyx = m.AND(anyx ^ 1, self.dxlit.get(key, 0) ^ 1) ^ 1
                    gx = m.AND(gn ^ 1, anyx ^ 1) ^ 1
                    bad = m.AND((d ^ h[1]) ^ 1, self.dxlit.get(k, 0) ^ 1) ^ 1
                    m.outs.append(m.AND(gx, bad))
                    m.onames.append(f"hyp:{side}:{k}")
                    continue
                if h[0] == "fill":
                    # filled' (the root: always; else the predecessor's ghost) -> D(k) == c and not X, and
                    # not filled' -> D(k) is X (tight: the ghost is 0 only while the RTL register really is X, so no
                    # read of a known RTL value becomes a don't care).  A hint whose ghost chain is broken (a
                    # predecessor dropped) is not bound (free) and fails here, so it drops.
                    if k not in self.fill_live:
                        m.outs.append(1)
                    else:
                        fn = 1 if h[2] is None else self.fill_in[h[2]]
                        dx = self.dxlit.get(k, 0)
                        bad = m.AND((d ^ h[1]) ^ 1, dx ^ 1) ^ 1
                        m.outs.append(m.AND(m.AND(fn, bad) ^ 1, m.AND(fn ^ 1, dx ^ 1) ^ 1) ^ 1)
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
        # Proof statuses are keyed by output name. A collision can overwrite a
        # failed obligation with a later pass, so reject it before any solver.
        duplicates = sorted(n for n, count in collections.Counter(m.onames).items() if count > 1)
        if duplicates:
            raise LecError("duplicate miter output names: " + ", ".join(duplicates[:8]))
        return m, kind


def guard_lit(m, guard, lit):
    """guard = [[[key, value], ...], ...]: an OR of cubes over gold registers -> AIG literal (lit(key) = its value)."""
    g = 0
    for cube in guard:
        c = 1
        for key, val in cube:
            c = m.AND(c, lit(key) ^ (val ^ 1))
        g = m.AND(g ^ 1, c ^ 1) ^ 1
    return g


def fill_live(hyp):
    """gold keys of 'fill' hypotheses whose predecessor chain ends at a root (pred None) through fill hypotheses only,
    with no cycle: only those ghosts are guaranteed to become 1 (a broken chain would keep its register X forever)."""
    fills = {k: h[2] for (sd, k), h in hyp.items() if sd == "gold" and h and h[0] == "fill"}
    live = {}
    for k in fills:
        path, x = [], k
        while x in fills and x not in live and x not in path:
            path.append(x)
            x = fills[x]
        ok = live.get(x, False) if x in live else (x is None)
        for y in path:
            live[y] = ok
    return {k for k, ok in live.items() if ok}


def loaded_base(L, guard):
    """loaded-valid base case: every guard cube is DEFINITELY false in the gold reset state (reset_state: every reset
    port asserted OT_LEC_RESET_CYCLES edges from an all-unknown power-up; pure constant propagation).  -> None when
    it holds, else the first cube that is not refuted there (the hint is refused: the register could be assumed
    loaded while it still holds its power-up X)."""
    if not hasattr(L, "rst_val"):
        noreset_classify(L)
    for cube in guard:
        if not any(L.rst_val.get(("gold", key), (None, None))[0] == 1 - val for key, val in cube):
            return cube
    return None


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
    # one cone at a time: naive SAT (x10 the sweep's conflicts), then what it leaves UNDECIDED (a solver limit, not a
    # difference) by SAT sweeping inside the cone (&cec -m without -n, x100 / x1000): wide XOR trees (ECC encoders)
    # that naive SAT cannot finish collapse there (PATH-KV-PC4 10-25: 77 kvs_pc ECC / write-queue cones undecided at
    # 1M naive conflicts, each proved by &cec -m in ~1 s).  Only what no pass answers stays undecided.
    for opt, factor in (("-n -m", 10), ("-m", 100), ("-m", 1000)):
        if not pending:
            break
        from concurrent.futures import ThreadPoolExecutor
        jobs = max(1, PROVE_JOBS)
        size = len(pending) if jobs == 1 else max(1, (len(pending) + jobs * 4 - 1) // (jobs * 4))
        batches = [pending[i:i+size] for i in range(0, len(pending), size)]
        def one_batch(ids, factor=factor, opt=opt):
            script = [f"&r {swept}; &cone -O {i}; &cec {opt} -C {conflicts * factor}" for i in ids]
            # one command per line in a script file (abc -f): a long batch passed as one -c argument exceeds the
            # kernel per-argument limit (MAX_ARG_STRLEN 128 KiB; OSError E2BIG on the 48k-output kvs_pc miters)
            sf = work / f"{tag}_cones_{ids[0]}_{ids[-1]}_x{factor}{opt.replace(' ', '')}.abc"
            sf.write_text("\n".join(script) + "\n")
            r = subprocess.run([abc, "-f", str(sf)], capture_output=True, text=True)
            return ids, r.stdout + r.stderr
        with ThreadPoolExecutor(max_workers=jobs) as ex:
            for ids, t in ex.map(one_batch, batches):
                log.append(f"==== {tag} single cones {ids[0]}..{ids[-1]} (&cec {opt} conflicts x{factor})\n{t}")
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
        pending = [i for i in pending if st[m.onames[i]] == "undecided"]
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


def relayout(L, log, words=4, trials=64, packed=frozenset()):
    """unpacked arrays: the two frontends may number the elements of `reg x [0:N-1]` in opposite order under the
    same names (read_verilog: element i = x[i]; slang: the flattened vector, element 0 at the MSB).  Greedy: for every
    array base whose matched compare points disagree in simulation, reverse the outer index on the gate side and keep
    it when clearly fewer matched compare points disagree (by 8, twice the array's bits and 1 % of the total) or the
    array's own compare points all agree after it.  A wrong choice can only produce a difference, never hide one (the
    mapping is a bijection of key points; everything is still proved).
    packed: gold bases the RTL declares as PACKED vectors (slang_packed_vectors); every frontend numbers a packed
    vector's bits alike, so they are never reversed (DIE-KV-32-LEC 10-29: q0 u_b `reg [1:0] lmax_any_i` was reversed
    on a 529 -> 508 simulation gain from its lmax_i cone before sc_addr[11] was proved constant; own 1 -> 1, then 4
    false NOT EQUIVALENT points lmax_any[0..1] / lmax_any_i[0..1])."""
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
        cand = [b for b, n in bad.most_common() if b not in tried and b not in packed and IDX.match(b + "[0]")]
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


def replica_groups(d, points, compare):
    """Group generated ff: compare keys by (norm(k), input-support set); exact."""
    norm = lambda k: GENCOPY.sub(lambda m: m[0].split("[")[0] + "[]", k)
    # Exact support-set grouping, computed one norm(k) bucket at a time over
    # that bucket's cone only, with bucket-local leaf numbering and freeing of
    # dead supports.  A design-wide bitset per AND node is O(nodes x symbols)
    # and exhausted 320 GB on the 841k-input Q2n2 gate (LEC-TOOL-3).
    pv = {}
    for k, lit in sorted(points.items()):
        pv[lit >> 1] = None if k.startswith("ff:") else ("point", k)
    base = d["I"] + d["L"] + 1
    ands = d["ands"]
    buckets = {}
    for k, lit in compare.items():
        if k.startswith("ff:") and GENCOPY.search(k):
            buckets.setdefault(norm(k), []).append(k)
    out = {}
    for nk, keys in sorted(buckets.items()):
        if len(keys) < 2:
            out[(nk, None)] = keys
            continue
        roots = [compare[k] >> 1 for k in keys]
        cone, todo = set(), list(roots)
        while todo:
            v = todo.pop()
            if v in cone:
                continue
            cone.add(v)
            if v >= base:
                i = v - base
                todo.append(ands[2*i] >> 1); todo.append(ands[2*i+1] >> 1)
        uses = {}
        for v in cone:
            if v >= base:
                i = v - base
                for c in (ands[2*i] >> 1, ands[2*i+1] >> 1):
                    uses[c] = uses.get(c, 0) + 1
        for v in roots:
            uses[v] = uses.get(v, 0) + (1 << 30)     # roots are never freed
        local, sup = {}, {}
        def leaf(t):
            if t not in local:
                local[t] = 1 << len(local)
            return local[t]
        for v in sorted(cone):
            if v >= base:
                i = v - base
                a, b = ands[2*i] >> 1, ands[2*i+1] >> 1
                sup[v] = sup[a] | sup[b]
                for c in (a, b):
                    uses[c] -= 1
                    if not uses[c]:
                        del sup[c]
            elif v in pv:
                sup[v] = 0 if pv[v] is None else leaf(pv[v])
            elif v == 0:
                sup[v] = 0
            else:
                sup[v] = leaf(("anonymous", v))
        for k, v in zip(keys, roots):
            out.setdefault((nk, sup[v]), []).append(k)
    return out


def replica_proposals(L, log):
    """Propose interchangeable generated-register cohorts on both designs.

    The input-support fingerprint keeps primary/black-box inputs distinct;
    current-state dependencies may be interchangeable generated feedback copies.
    This is only candidate discovery: both designs' next-state relations still
    pass through the normal simultaneous inductive SAT proof/refinement.
    """
    norm = lambda k: GENCOPY.sub(lambda m: m[0].split("[")[0] + "[]", k)
    n = 0
    for side, d, points, compare in (("gold", L.gold, L.gp, L.gc), ("gate", L.gate, L.tp, L.tc)):
        for keys in replica_groups(d, points, compare).values():
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
    return {h[2] for (sd, k), h in L.hyp.items() if h[0] == "eq" and h[1] != "gate" and (sd != "gold" or h[2] in ms)}


def bound_keys(L):
    """registers that are not free for new pairing: those with a hypothesis, and the partners of cross-side / matched
    relations.  A gate-only REPRESENTATIVE of a gate-side replica cohort (g_ft[1..3].u_rsd.q#t[135] == g_ft[0]'s) is
    still free: it needs a gold partner or a constant of its own, else the whole cohort stays a free input (KV head
    e0/e2/e6: the constant-0 relay bit qb_send[5] that gold drops, kept by gate keep -> 4..39 points UNPROVEN)."""
    return {k for (sd, k) in L.hyp} | {h[2] for h in L.hyp.values() if h[0] == "eq" and h[1] != "gate"}
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


ZH = -2                                  # fsm_proposals: the zero-hot (all gate bits 0) state


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
        zh = nt + 1 <= (1 << n)            # room for a zero-hot state (all gate bits 0, LEC-FPREG-4 L3 u_rw.st)
        for c in range(1 << n):
            for j in list(range(nt)) + ([ZH] if zh else []):
                ones = (1 << (64 * words)) - 1
                fixed = {var[("gold", k)]: (ones if (c >> b) & 1 else 0) for b, k in enumerate(gk)}
                fixed.update({var[("gate", k)]: (ones if i == j else 0) for i, k in enumerate(tk)})
                vals, mask = cone_sim(m, dl, fixed, words, seed=c * 64 + (j if j >= 0 else 63))
                obs = collections.Counter()
                for lane in range(64 * words):
                    gn = sum(((vals[b] >> lane) & 1) << b for b in range(n))
                    tn = [(vals[n + i] >> lane) & 1 for i in range(nt)]
                    obs[(gn, tn.index(1) if sum(tn) == 1 else (ZH if sum(tn) == 0 else -1))] += 1
                R[(c, j)] = obs
        # the next states also depend on registers not yet paired (a renamed alias of a state flag is a free input
        # on each side), so a transition agrees only where those agree: pick the map with the most agreeing
        # transitions (unique best, a majority of all lanes); the induction proof decides
        import itertools
        lanes = 64 * words
        def search(zero_hot):
            # zero_hot: one more code is the all-zero gate state (yosys fsm one-hot recoding of a reset/idle state
            # as no bit set); its transitions are scored like the one-hot ones
            best, second, pi = -1, -1, None
            for codes in itertools.combinations(range(1 << n), nt):
                for perm in itertools.permutations(range(nt)):
                    base_ = dict(zip(codes, perm))
                    for z in ([c for c in range(1 << n) if c not in base_] if zero_hot else [None]):
                        cand = dict(base_)
                        if z is not None:
                            cand[z] = ZH
                        sc = sum(cnt for c, j in cand.items() for (gn, ti), cnt in R[(c, j)].items()
                                 if ti != -1 and cand.get(gn) == ti)
                        if sc > best:
                            best, second, pi = sc, best, cand
                        elif sc > second:
                            second = sc
            ok = pi is not None and best != second and 2 * best > len(pi) * lanes
            return ok, best, second, pi
        ok, best, second, pi = search(False)
        if not ok and zh:                  # only when no one-hot map is unique: earlier verdicts are unchanged
            if math.comb(1 << n, nt) * math.factorial(nt) * ((1 << n) - nt) > 200000:
                log.append(f"fsm: {base} ({n} gold / {nt} gate bits): zero-hot encoding search too large")
            else:
                okz, bz, sz, pz = search(True)
                if okz:
                    ok, best, second, pi = okz, bz, sz, pz
        if not ok:
            log.append(f"fsm: {base} ({n} gold / {nt} gate bits): no unique encoding (best {best}, next {second} of "
                       f"{nt * lanes} transitions), none proposed")
            continue
        for c, j in sorted(pi.items()):
            if j == ZH:                    # zero-hot: implied by the other cubes (every gate bit 0), no flop of its own
                continue
            L.hyp[("gate", tk[j])] = ("cube", "gold", list(gk), [(c >> b) & 1 for b in range(n)])
            n_new += 1
        # a later round can re-propose the same state vector (its cube hypotheses were dropped and its gate bits are
        # unbound again): the new encoding replaces the earlier constraint over the same gold bits instead of adding
        # a second one with the same proof-output name (cons:gold:<first key>, rejected by build() as a duplicate)
        L.cons = [c for c in L.cons if not (c[0] == "gold" and list(c[1]) == list(gk))]
        L.cons.append(("gold", list(gk), [[(c >> b) & 1 for b in range(n)] for c in sorted(pi)]))
        log.append(f"fsm: {base} recoded one-hot: " + ", ".join(f"{c}->{tk[j] if j != ZH else 'zero-hot'}"
                                                                for c, j in sorted(pi.items())))
    return n_new


def seq_traces(L, log, words=4, warm=2, cycles=48, seed=2718):
    """sequential random simulation of gold and gate from the all-zero register state (every keyed register at
    logical 0 on both sides, as LEC compares from equal states) with the SAME random values on every matched primary
    input / black-box output each cycle -> per register key (side, key): (trace hash, complemented-trace hash) or
    None when constant.  Register correspondence candidates independent of names and of the current hypotheses:
    a re-laid / cross-instance-named gate flop (hcore g_ske skew lines: yosys kept ANOTHER instance's name on a
    merged delay-line flop; HBM tkm leaf: slang X[w][flat] vs read_verilog SX[p][b]) has the trace of its RTL
    register.  Candidates only: every pair is proved by the inductive correspondence like any other."""
    import random
    W = 64 * words
    mask = (1 << W) - 1
    rnd = random.Random(seed)
    shared = sorted(k for k in L.matched if not k.startswith("ff:"))
    out = {}
    sides = (("gold", L.gold, L.gp), ("gate", L.gate, L.tp))
    states = []
    for side, d, P in sides:
        st = [0] * d["L"]
        I = d["I"]
        for k, lit in P.items():
            if k.startswith("ff:") and lit >> 1 > I:
                st[(lit >> 1) - I - 1] = mask if lit & 1 else 0
        states.append(st)
    acc = {}
    for cyc in range(warm + cycles):
        sv = {k: rnd.getrandbits(W) for k in shared}
        for si, (side, d, P) in enumerate(sides):
            I, NL, a = d["I"], d["L"], d["ands"]
            r2 = random.Random(seed * 7919 + cyc * 2 + si)
            val = [0] * (1 + I + NL + d["A"])
            for v in range(1, I + 1):
                val[v] = r2.getrandbits(W)
            st = states[si]
            for i in range(NL):
                val[I + 1 + i] = st[i]
            for k in shared:
                lit = P.get(k)
                if lit is not None:
                    val[lit >> 1] = sv[k] ^ (mask if lit & 1 else 0)
            base = I + NL + 1
            for j in range(d["A"]):
                r0, r1 = a[2 * j], a[2 * j + 1]
                val[base + j] = (val[r0 >> 1] ^ (mask if r0 & 1 else 0)) & (val[r1 >> 1] ^ (mask if r1 & 1 else 0))
            if cyc >= warm:
                for k, lit in P.items():
                    if k.startswith("ff:"):
                        v = val[lit >> 1] ^ (mask if lit & 1 else 0)
                        h = acc.get((side, k))
                        acc[(side, k)] = (hash((h[0], v)), hash((h[1], v ^ mask)), h[2] and v == 0,
                                          h[3] and v == mask) if h else (hash(v), hash(v ^ mask), v == 0, v == mask)
            states[si] = [val[l >> 1] ^ (mask if l & 1 else 0) for l in d["latches"]]
    const = {}
    for key, (hp, hn, c0, c1) in acc.items():
        out[key] = None if (c0 or c1) else (hp, hn)
        if c0 or c1:
            const[key] = 1 if c1 else 0
    L.trace_const = const            # (side, key) -> the constant value of a constant trace (trace_constant_closure)
    log.append(f"sequential traces: {len(out)} registers, {sum(v is None for v in out.values())} constant, "
               f"{warm}+{cycles} cycles x {W} lanes")
    return out


def trace_proposals(L, T, tried, log):
    """pair still-unpaired registers whose sequential traces (seq_traces) are equal, either polarity: gold-only with
    gate-only, gold-only with a matched register, gold-only with an earlier gold-only of the same trace (synthesis
    merged both into one gate flop), gate-only with a matched / gold-only register.  At most 2 tries per pair,
    nearest name first; the inductive proof decides.  -> number of hypotheses added."""
    partnered = anchored(L)
    bound = bound_keys(L)
    canon = lambda t: (min(t), int(t[0] > t[1]))          # (canonical hash, polarity of this register)
    pool_t, pool_m = collections.defaultdict(list), collections.defaultdict(list)
    for k in L.tonly:
        t = T.get(("gate", k))
        if t and k.startswith("ff:") and ("gate", k) not in L.hyp and k not in bound:
            c, p = canon(t)
            pool_t[c].append((k, p))
    for k in L.matched:
        t = T.get(("gold", k))
        if t and k.startswith("ff:") and T.get(("gate", k)) == t:
            c, p = canon(t)
            pool_m[c].append((k, p))
    rep = {}                       # canonical trace -> (gold key whose value carries it, its polarity)
    n = 0
    for k in L.gonly:
        t = T.get(("gold", k))
        if not t or not k.startswith("ff:") or ("gold", k) in L.hyp or k in partnered:
            continue
        c, p = canon(t)
        hit = None
        for g, q in sorted(pool_t.get(c, []), key=lambda e: name_dist(k, e[0])):
            if tried[("tr", "gate", g, k)] < 2:
                hit = ("gate", g, ("eq", "gold", k, p ^ q))
                pool_t[c].remove((g, q))
                rep.setdefault(c, (k, p))
                break
        if not hit:
            for g, q in sorted(pool_m.get(c, []), key=lambda e: name_dist(k, e[0])):
                if tried[("tr", "gold", k, g)] < 2:
                    hit = ("gold", k, ("eq", "gold", g, p ^ q))
                    rep.setdefault(c, (g, q))
                    break
        if not hit and c in rep and rep[c][0] != k and tried[("tr", "gold", k, rep[c][0])] < 2:
            hit = ("gold", k, ("eq", "gold", rep[c][0], p ^ rep[c][1]))
        if not hit:
            rep.setdefault(c, (k, p))
            continue
        tried[("tr",) + hit[:2] + (hit[2][2],)] += 1
        L.hyp[hit[:2]] = hit[2]
        n += 1
    for c, ks in pool_t.items():
        for g, q in ks:
            tgt = rep.get(c) or next(iter(pool_m.get(c, [])), None)
            if tgt and tried[("tr", "gate", g, tgt[0])] < 2:
                tried[("tr", "gate", g, tgt[0])] += 1
                L.hyp[("gate", g)] = ("eq", "gold", tgt[0], q ^ tgt[1])
                n += 1
    if n:
        log.append(f"trace proposals: {n} register relations from equal sequential traces")
    return n


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




def _sim_given(m, ivals, mask):
    """bit-parallel simulation of builder m with the given input values (var -> int)."""
    val = [0] * (m.ni + len(m.ands) // 2 + 1)
    for v, x in ivals.items():
        val[v] = x
    a, base = m.ands, m.ni + 1
    for k in range(len(a) // 2):
        r0, r1 = a[2 * k], a[2 * k + 1]
        val[base + k] = (val[r0 >> 1] ^ (mask if r0 & 1 else 0)) & (val[r1 >> 1] ^ (mask if r1 & 1 else 0))
    return val


def sim_refine(L, log, tried, words=8, quiet=3, seed=4242):
    """Witness-based refinement by simulation (LEC-TOOL-1 10-27), run before every ABC hypothesis round.

    van Eijk refinement drops, per round, the hypotheses that fail from a state satisfying all current hypotheses.
    On a long delay line of wrong duplicate / constant hypotheses only the head stage fails per round (its
    successor stage becomes refutable only once the head is free), so the ABC loop peels one stage per round:
    HBM hcp_sys1 R5 peeled dld[] one 47-bit stage per ~80 s round, hit OT_LEC_REFINE_S after 64 rounds and then
    cleared EVERY hypothesis (1075 points 'differ', 0 constants / pairs kept).

    Here the free miter (no hypotheses bound) is built once; each iteration draws random states, forces them onto
    the current hypotheses (every bound register takes its partner's / constant value, lanes left inconsistent are
    masked out), simulates one step and drops every hypothesis whose next-state relation is violated in a valid
    lane.  Such a lane is a concrete state satisfying every current hypothesis (and FSM constraint) whose successor
    violates the dropped one: exactly the counterexample the ABC round would find, so a dropped hypothesis can
    never be part of the inductive fixpoint.  Nothing is ever accepted here: the surviving set still goes to the
    ABC induction proof, so this can only save rounds, never prove a point.  -> number of hypotheses dropped."""
    if not L.hyp:
        return 0
    hyp, cons = L.hyp, L.cons
    L.hyp, L.cons = {}, []
    try:
        m, kind = L.build(with_compare=False, with_hyp=False)
        dl, xl = dict(L.dlit), dict(L.dxlit)
    finally:
        L.hyp, L.cons = hyp, cons
    import random
    rnd = random.Random(seed)
    W = 64 * words
    mask = (1 << W) - 1
    mvar, svar = {}, {"gold": {}, "gate": {}}
    for v, (t, k) in kind.items():
        if t == "matched":
            mvar[k] = v
        elif t in ("gold_only", "gate_only"):
            svar[t[:4]][k] = v

    def var(side, k):
        return mvar.get(k) if k in mvar else svar.get(side, {}).get(k)

    dropped, still, it = 0, 0, 0
    while still < quiet:
        it += 1
        ivals = {v: (rnd.getrandbits(W) & ~3) | 2 for v in range(1, m.ni + 1)}
        # Keep two concrete lanes with free inputs all-zero/all-one. Random
        # states almost never carry through a wide counter's low bits, so a
        # false constant otherwise peels one bit per expensive SAT round.
        # Give these lanes a legal FSM seed; the existing validity mask below
        # still checks every hypothesis and constraint before anything drops.
        for sd, keys, allowed in L.cons:
            if allowed:
                for k, bit in zip(keys, allowed[0]):
                    v = var(sd, k)
                    if v is not None:
                        ivals[v] = (ivals[v] & ~3) | (3 if bit else 0)
        items = sorted(L.hyp.items())

        def src(h):
            if h[0] == "const":
                return mask if h[1] else 0
            if h[0] == "eq":
                v = var(h[1], h[2])
                return None if v is None else ivals[v] ^ (mask if h[3] else 0)
            if h[0] == "cube":
                c = mask
                for ok, ov in zip(h[2], h[3]):
                    v = var(h[1], ok)
                    if v is None:
                        return None
                    c &= ivals[v] ^ (0 if ov else mask)
                return c
            return None

        tgt = {key: var("gold" if key[0] == "both" else key[0], key[1]) for key, _ in items}
        for _ in range(64):                         # chains resolve in passes (cycles stay inconsistent: masked)
            changed = False
            for key, h in items:
                tv, s = tgt[key], src(h)
                if tv is not None and s is not None and ivals[tv] != s:
                    ivals[tv], changed = s, True
            if not changed:
                break
        valid = mask
        for key, h in items:
            tv, s = tgt[key], src(h)
            if tv is not None and s is not None:
                valid &= ~(ivals[tv] ^ s)
        cur = lambda sd, k: ivals.get(var(sd, k), 0)

        def member(vals, allowed):
            acc = 0
            for t in allowed:
                c = mask
                for x, b in zip(vals, t):
                    c &= x if b else ~x & mask
                acc |= c
            return acc
        for sd, keys, allowed in L.cons:
            if all(var(sd, k) is not None for k in keys):
                valid &= member([cur(sd, k) for k in keys], allowed)
        if not valid:
            still += 1
            continue
        val = _sim_given(m, ivals, mask)
        D = lambda sd, k: lit_val(val, mask, dl[(sd, k)])
        NX = lambda k: ~lit_val(val, mask, xl[k]) & mask if k in xl else mask
        bad = []
        for key, h in items:
            side, k = key
            if tgt[key] is None:
                continue
            try:
                if side == "both":
                    if h[0] == "const":
                        c = mask if h[1] else 0
                        v = ((D("gold", k) ^ c) & NX(k)) | (D("gate", k) ^ c)
                    elif h[0] == "eq":
                        inv = mask if h[3] else 0
                        v = ((D("gold", k) ^ D("gold", h[2]) ^ inv) & NX(k)) | (D("gate", k) ^ D("gate", h[2]) ^ inv)
                    else:
                        continue
                elif h[0] == "const":
                    v = (D(side, k) ^ (mask if h[1] else 0)) & (NX(k) if side == "gold" else mask)
                elif h[0] == "eq":
                    od = D(h[1], h[2]) if (h[1], h[2]) in dl else D("gold", h[2])
                    xm = NX(k) if side == "gold" else (NX(h[2]) if h[1] == "gold" and h[2] in L.gc else mask)
                    v = (D(side, k) ^ od ^ (mask if h[3] else 0)) & xm
                elif h[0] == "cube":
                    c = mask
                    for ok, ov in zip(h[2], h[3]):
                        c &= D(h[1], ok) ^ (0 if ov else mask)
                    known, false_known = mask, 0
                    if h[1] == "gold":
                        for ok, ov in zip(h[2], h[3]):
                            atom = D(h[1], ok) ^ (0 if ov else mask)
                            known &= NX(ok)
                            false_known |= (~atom & NX(ok))
                    v = (D(side, k) ^ c) & (known | false_known)
                else:
                    continue
            except KeyError:
                continue
            if v & valid:
                bad.append((key, h))
        badc = [f"cons:{sd}:{keys[0]}" for sd, keys, allowed in L.cons
                if all((sd, k) in dl for k in keys) and
                ~member([D(sd, k) for k in keys], allowed) & mask & valid]
        if not bad and not badc:
            still += 1
            continue
        still = 0
        for key, h in bad:
            if L.hyp.pop(key, None) is None:
                continue
            side, k = key
            tried[(side, k, "c") if h[0] == "const" else (side, k, h[2], h[3]) if h[0] == "eq" else
                  (side, k, str(h[2]), str(h[3]))] += 1
            dropped += 1
        if badc:
            drop_failed(L, badc)
            dropped += len(badc)
    if dropped:
        log.append(f"simulation refinement: {dropped} hypotheses refuted by concrete witnesses in {it} iterations")
    return dropped


def proved_state_constant(L, side, key, seen=None):
    """Resolve only accepted induction equalities ending in a constant."""
    seen = set() if seen is None else seen
    node = (side,key)
    if node in seen:
        return None
    seen.add(node)
    h=L.hyp.get(node)
    both=h is None
    if both:
        h=L.hyp.get(("both",key))
    if not h:
        return None
    if h[0]=="const":
        return int(h[1])
    if h[0]=="eq":
        c=proved_state_constant(L,side if both else h[1],h[2],seen)
        return None if c is None else c ^ int(h[3])
    return None


def unobservable_keys(L):
    """{'ff:<key>'} gold registers no compare point observes: outside the bit-level backward cone (through register
    next states, to a fixpoint) of every wrapper output capture (po:) and black-box input (bb:) in the gold AIG.  Such
    a register drives nothing, so dead-logic removal (ORFS eliminate_dead_logic) may delete it; that is not a merge
    (QC-A0-KITS-4 10-28, romleaf: 32 of 1206 kept bits xa_m[8k+7] only reach a shift that drops them; FLOW-GEN-1)."""
    g = L.gold
    I, NL, ands, latches = g["I"], g["L"], g["ands"], g["latches"]
    seen, stack = set(), [lit >> 1 for k, lit in L.gc.items() if k[:3] in ("po:", "bb:")]
    if not stack:                                       # no compare point: nothing can be judged dead (fail closed)
        return set()
    while stack:
        v = stack.pop()
        if v == 0 or v in seen:
            continue
        seen.add(v)
        if v <= I:
            continue
        if v <= I + NL:
            stack.append(latches[v - I - 1] >> 1)
        else:
            k = v - I - NL - 1
            stack += (ands[2 * k] >> 1, ands[2 * k + 1] >> 1)
    return {k for k, lit in L.gp.items() if k.startswith("ff:") and (lit >> 1) not in seen}


def kept_wire_alias_copies(L, declared, aliases_file):
    """Recognize RTL Q-wire aliases while requiring one distinct gate FF per kept bit.

    The JSON is captured before register mapping from the same golden assembly.
    An alias is wiring identity, not merely an equal-value replica hypothesis.
    """
    p = Path(aliases_file)
    if not p.is_file():
        return set()
    nets = json.loads(p.read_text())["modules"][WRAP]["netnames"]
    bit_names, wire_bits = collections.defaultdict(set), {}
    for name, net in nets.items():
        name = GENBLK.sub("", name.replace("\\", "").replace(" ", ""))
        bits, offset = net["bits"], int(net.get("offset", 0))
        for i, bit in enumerate(bits):
            if not isinstance(bit, int):
                continue
            ix = offset + (len(bits)-1-i if net.get("upto", 0) else i)
            names = {"ff:" + name + "[" + str(ix) + "]"}
            if len(bits) == 1 and offset == 0:
                names.add("ff:" + name)
            for n in names:
                wire_bits[n] = bit
            bit_names[bit].update(names)
    old_names = {v:k for k,v in (a.split("->",1) for a in L.aliased)}
    gate, renamed = set(L.tp), collections.defaultdict(set)
    for (side,c),h in L.hyp.items():
        if side == "gate" and h[0] == "eq" and h[1] == "gold":
            renamed[h[2]].add(c)
    candidates = {}
    for k in declared:
        if proved_state_constant(L,"gold",k) is not None:
            continue
        old = old_names.get(k,k)
        # HEAD-KITS-2 10-28: a gate array whose bits were re-keyed as base#t[i] (Lec relaid: the gate holds bits the
        # gold array lacks, e.g. ot_s81hd_spo o/ow/oe[512..514] = the kept g_c[c].ctl_q copies) is still that alias
        # wire's flop; the one-distinct-gate-FF-per-kept-bit matching below stays the proof.
        names = set(bit_names.get(wire_bits.get(old), ()))
        names |= {m.group(1) + "#t" + m.group(2) for m in map(IDX.match, list(names)) if m}
        choices = names & gate
        if k in gate:
            choices.add(k)
        choices.update(renamed[k])
        candidates[k] = choices
    assigned = {}
    def assign(k, seen):
        for c in sorted(candidates[k]):
            if c in seen:
                continue
            seen.add(c)
            if c not in assigned or assign(assigned[c], seen):
                assigned[c] = k
                return True
        return False
    # All kept demands participate, including the already name-matched ones.
    # This prevents an alias from reusing a gate flop already counted elsewhere.
    if all(assign(k,set()) for k in sorted(candidates, key=lambda k:len(candidates[k]))):
        return set(candidates)
    return set()


RRS_COPY = re.compile(r"^(ff:.*?)ot_rrs__([A-Za-z0-9_]+)__c(\d+)$")


def kept_reset_copies(L, declared):
    """Kept reset-relay copy bits that physical/common_flow/ot_rst_copies.py re-pointed (QC-LEC-3 10-26, N59: 664 of
    680 'missing' kept bits were these).  The pass proves the N bits of a family wire WN identical, adds one alias wire
    \\ot_rrs__<tag>__c<k> per copy bit k (tag = WN with non [A-Za-z0-9_] -> '_', last 60 characters) and moves loads
    onto it; synthesis then names copy k's flop after that alias.  The copy is still a flop of its own, under a
    deterministic new name.  A declared gold bit WN[k] counts as present only when exactly one gate family
    <prefix>ot_rrs__<tag>__c* matches WN's sanitised name under the same hierarchy prefix, that family is claimed by
    no other gold register, and its copy indices equal the declared bit indices of WN one for one (fail-closed:
    a folded copy leaves a hole, a truncated-tag collision matches twice)."""
    fams = collections.defaultdict(dict)
    for k in L.tp:
        m = RRS_COPY.match(k)
        if m:
            fams[(m.group(1), m.group(2))][int(m.group(3))] = k
    if not fams:
        return set()
    bits = collections.defaultdict(dict)
    for k in declared:
        m = IDXK.match(k)
        if m:
            bits[m.group(1)][int(m.group(2))] = k
    claim = collections.defaultdict(list)
    for base in bits:
        for pre, tag in fams:
            if base.startswith(pre) and re.sub(r"[^A-Za-z0-9_]", "_", base[len(pre):])[-60:] == tag:
                claim[(pre, tag)].append(base)
    by_base = collections.defaultdict(list)
    for fam, bases in claim.items():
        if len(bases) == 1:
            by_base[bases[0]].append(fam)
    present = set()
    for base, fl in by_base.items():
        if len(fl) == 1 and set(fams[fl[0]]) == set(bits[base]):
            present.update(bits[base].values())
    return present


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
    alias_copies = kept_wire_alias_copies(L, declared, Path(keep_file).with_suffix(".aliases.json"))
    reset_copies = kept_reset_copies(L, declared)
    missing, const = [], []
    for k in sorted(declared):
        if k in gate or k in renamed:
            continue
        m = IDX.match(k)
        if m and m.group(1) in relaid and relaid[m.group(1)] >= gold_rel[m.group(1)]:
            continue                 # an array the two frontends lay out differently: counted per array
        if proved_state_constant(L,"gold",k) is not None:
            const.append(k)
            continue
        if k not in alias_copies and k not in reset_copies:
            missing.append(k)
    # FLOW-GEN-1 10-28: a kept bit no observable point reads drives nothing; removing it is not a merge.  Reported
    # (L.kept_unobservable), not failed.  A kept bit that is read stays fail-closed.
    dead = unobservable_keys(L) if missing else set()
    L.kept_unobservable = sorted(k for k in missing if k in dead or inv_alias.get(k, k) in dead)
    missing = [k for k in missing if k not in L.kept_unobservable]
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



def structural_twin_closure(L, log):
    """Propose same-side duplicate FFs by exact next-state literal identity.

    Unlike random signatures this finds rare carry bits and arbitrarily deep
    merged valid pipes. All proposals enter the next induction miter.
    """
    total = 0
    while True:
        L.build(with_compare=False, with_hyp=False)
        new = []
        for side, keys in (("gold", L.gonly), ("gate", L.tonly)):
            paired_roots = {h[2] for (sd,k),h in L.hyp.items()
                            if h[0] == "eq" and h[1] == side and sd != side}
            twins = {}
            for c in sorted(set(L.matched) | paired_roots):
                d = L.dlit.get((side, c), 0)
                if c.startswith("ff:") and d > 1 and (side, c) not in L.hyp:
                    twins.setdefault(d >> 1, []).append((c, d))
            for k in keys:
                d = L.dlit.get((side, k), 0)
                if not k.startswith("ff:") or (side, k) in L.hyp or k in paired_roots or d <= 1:
                    continue
                choices = twins.get(d >> 1, [])
                if choices:
                    c, dc = min(choices)
                    new.append(((side, k), ("eq", side, c, (d ^ dc) & 1)))
        # The frontends also expose different wire aliases for one flop.
        # Compare exact functions across sides, including rare enable bits
        # whose random signatures look constant (XS3 wce_n / wce3).
        gold = {}
        for k in L.gonly:
            d = L.dlit.get(("gold", k), 0)
            if k.startswith("ff:") and d > 1 and ("gold", k) not in L.hyp:
                gold.setdefault(d >> 1, []).append((k, d))
        for k in L.tonly:
            d = L.dlit.get(("gate", k), 0)
            if not k.startswith("ff:") or ("gate", k) in L.hyp or d <= 1:
                continue
            choices = gold.get(d >> 1, [])
            if choices:
                c = closest(k, [q for q, _ in choices])[0]
                dc = dict(choices)[c]
                new.append((("gate", k), ("eq", "gold", c, (d ^ dc) & 1)))
        if not new:
            break
        L.hyp.update(new)
        total += len(new)
    if total:
        log.append(f"structural twin closure: {total} relations proposed")
    return total



def matched_copy_closure(L, log, T, tried, words=8, seed=5151, rounds=8):
    """Propose MATCHED registers equal to a matched copy of the same function (LEC-TOOL-2 10-27).

    Both frontends may keep several copies of one value, each a matched register of its own name, while the
    downstream logic reads a DIFFERENT copy on each side (HBM ot_hgi_coll_gq_land r4: the eight landing lanes'
    sector high bits ln_s[*][15:13] all load base_q[*][15:13] == g_dst[15:13], holding while rn is low; synthesis
    kept four copies per bit and each side's record mux reads its own choice, so the miter left ln_s[0][29] and
    ln_s[0][45] free of each other and 24 record bits 277..279 'differed' with every cone input matched).  The
    name-based pairing never relates two matched registers, and merged_proposals only relates same-support
    siblings (here the lanes read different le_k entries, whose selection drops out only for the high bits).

    Candidates: matched, not yet merged, non-constant registers whose sequential traces from the zero state (seq_traces)
    are equal on both sides and to each other (either polarity).  Each is bound to the first copy of its class and
    kept only if, with that binding (the copies hold themselves), its next state simulates equal to the copy's on
    BOTH sides (gold X lanes are don't care); then it enters the simultaneous induction proof with every other
    hypothesis: a register that is not a copy (other load condition, other data) is refuted there and dropped,
    never assumed.  Each pair is proposed at most once.  -> number of relations proposed."""
    if T is None:
        return 0
    nat = lambda k: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", k)]
    groups = collections.defaultdict(list)
    for k in sorted(L.matched, key=nat):
        if not k.startswith("ff:") or ("both", k) in L.hyp or k not in L.gc or k not in L.tc:
            continue
        tg, tt = T.get(("gold", k)), T.get(("gate", k))
        if not tg or tg != tt:
            continue
        groups[min(tg)].append((k, int(tg[0] > tg[1])))
    pending = {}
    for ks in groups.values():
        if len(ks) < 2:
            continue
        rk, rp = ks[0]       # a copy that already is some register's partner may be bound too (build() follows chains)
        for k, p in ks:
            if k != rk and not tried[("both", k, rk, p ^ rp)] and not tried[("cc", k, rk)]:
                pending[k] = ("eq", "gold", rk, p ^ rp)
    for it in range(rounds):
        if not pending:
            break
        for k, h in pending.items():
            L.hyp[("both", k)] = h
        m, _ = L.build(with_compare=False, with_hyp=False)
        val, mask = m.simulate(words, seed=seed + it)
        bad = []
        for k, (_, _, rk, inv) in pending.items():
            im = mask if inv else 0
            care = mask ^ (lit_val(val, mask, L.dxlit[k]) | lit_val(val, mask, L.dxlit[rk]))
            g = (lit_val(val, mask, L.dlit[("gold", k)]) ^ lit_val(val, mask, L.dlit[("gold", rk)]) ^ im) & care
            t = lit_val(val, mask, L.dlit[("gate", k)]) ^ lit_val(val, mask, L.dlit[("gate", rk)]) ^ im
            if g or t:
                bad.append(k)
        for k in bad:
            L.hyp.pop(("both", k), None)
            tried[("cc", k, pending.pop(k)[2])] += 1
        if not bad:
            break
    else:
        for k in pending:                          # undecided after `rounds`: not proposed
            L.hyp.pop(("both", k), None)
        pending = {}
    for k, h in pending.items():
        tried[("cc", k, h[2])] += 1
    if pending:
        log.append(f"matched copy closure: {len(pending)} matched registers proposed equal to a matched copy of equal "
                   f"trace and next state")
    return len(pending)


def trace_constant_closure(L, log, tried):
    """Constant-from-reset candidates (LEC-TOOL-2 10-27): a register whose sequential trace (seq_traces: from the
    zero state, random inputs including the reset each cycle) is one constant on every side that has it is proposed
    that constant -- matched registers on both sides, gold-only / gate-only on their side -- and enters the
    simultaneous induction proof with every other hypothesis.  HBM hcp_sys1 R5: nout_r[1] resets to 0 and reloads
    the tied cmd_nout[1] = 0 (async reset, kept by synthesis as a matched DFFASRHQN), so gold d0[F_NV] =
    last_r ? nlast_r : 256 is 256 (nlast_r[7:0] == nout_r[1] == 0, proved) while the gate folded sd_nv[7:0] to 0; with
    nout_r[1] a free matched input the 9 sd_nv face bits 'differed'.  The random-state signature search never
    proposes it (its next state depends on its own state) unless the self-hold cofactor also happens to fire, so only
    self-holding registers are proposed here.
    A register that is constant only from reset but not inductively (it needs another invariant that is not
    proposed) is refuted and dropped, never assumed.  Each register is proposed at most once.  -> number proposed."""
    tc = getattr(L, "trace_const", None)
    if not tc:
        return 0
    m, kind = L.build(with_compare=False, with_hyp=False)
    var_of = {(t.split("_")[0] if t != "matched" else "both", kk): v for v, (t, kk) in kind.items()
              if t in ("matched", "gold_only", "gate_only")}
    # only self-holding registers (own Q within 8 AND levels of the next state: hold mux + async2sync reset mux);
    # a constant register whose next state does not read itself is found by the random-state signature search
    holds = lambda sd, k: (sd, k) in var_of and var_of[(sd, k)] in m.near_inputs(
        L.dlit[("gold" if sd == "both" else sd, k)], 8)
    n = 0
    for k in L.matched:
        if not k.startswith("ff:") or ("both", k) in L.hyp or tried[("tc", "both", k)]:
            continue
        g, t = tc.get(("gold", k)), tc.get(("gate", k))
        if g is not None and g == t and holds("both", k):
            tried[("tc", "both", k)] += 1
            L.hyp[("both", k)] = ("const", g)
            n += 1
    partners = anchored(L)
    for side, keys in (("gold", L.gonly), ("gate", L.tonly)):
        for k in keys:
            c = tc.get((side, k))
            if c is None or not k.startswith("ff:") or (side, k) in L.hyp or k in partners or tried[("tc", side, k)] \
                    or not holds(side, k):
                continue
            tried[("tc", side, k)] += 1
            L.hyp[(side, k)] = ("const", c)
            n += 1
    if n:
        log.append(f"trace constant closure: {n} registers of constant sequential trace proposed constant")
    return n


# ------------------------------------------------------------------------------------------------ no-reset constants
# KV-KITS-9 10-28: the KV HBM-domain reset hrst_n / hrst (h prefix, no underscore) is a reset port too; unnamed, the
# kvs_pc HBM-domain reset constants (u_front.sc, bs, u_calendar.active_row behind hr <= hrst) had no reset base case.
RESET_PORT = re.compile(r"^(?:\w+_)?h?(?:rst|reset|rn|rstn|nrst|arst|srst)(?:_?n|_ni|_b|_l)?(?:_pin)?$", re.I)


def kit_reset_ports(kit):
    """reset port names the kit declares (FLOW-GEN-1 10-28): core.json boundary_role {port: 'reset'} (the typed
    boundary map every core-kit generator writes) and the constraint.sdc '# reset <ports>: ...' line.  None when the
    kit declares nothing (the name pattern alone then decides, as before)."""
    kit, out = Path(kit), set()
    try:
        roles = json.loads((kit / "core.json").read_text()).get("boundary_role") or {}
        out |= {str(k) for k, v in roles.items() if v == "reset"}
    except (OSError, ValueError, AttributeError):
        pass
    try:
        for m in re.finditer(r"^# reset ([^:\n]+):", (kit / "constraint.sdc").read_text(), re.M):
            out |= set(m.group(1).split())
    except OSError:
        pass
    return sorted(out) or None


def reset_vars(d, pis, asserted=None, levels=None, declared=None):
    """{var: asserted value} of the reset ports of one side (pi keys; OT_LEC_RESET_PORTS=a,b overrides the name
    pattern).  Active low when the name ends in n / _ni / _b / _l (rst_n, rn, core_rst_n) -- unless the structure
    says otherwise (LEC-FPREG-7 10-27, S81 dsdv_bksel_c: port 'rst' is the ACTIVE-LOW async reset of every register,
    'always @(posedge ck or negedge rst[0])'; the name rule asserted rst = 1 = released, so the 'reset state' reset
    nothing and 6,382 points differed).  The asserted level of a reset is by definition the level that forces the
    registers: from an all-unknown state, one edge with the port at each level (the other reset ports at their
    level); when the opposite level of the name rule forces more than twice as many registers that the name level does
    not force, it is the asserted level (registers constant at both levels do not count: S81 RXsf gold has ~2,070).  OT_LEC_RESET_POLARITY=name keeps the name rule only.  asserted: {pi key: logical asserted value} decided
    on the gold side, applied unchanged to the gate (one port, one polarity); levels: dict filled with {pi key: asserted
    value} -> R = {var: asserted literal value}.  declared: the kit's declared reset ports (kit_reset_ports), reset
    ports in addition to the name pattern, so a declared reset needs no name rule (KV hrst_n)."""
    names = [n for n in os.environ.get("OT_LEC_RESET_PORTS", "").split(",") if n]
    declared = set(declared or ())
    R, key_of, lv = {}, {}, {}
    for k, lit in pis.items():
        if not k.startswith("pi:"):
            continue
        base = re.sub(r"\[\d+\]$", "", k[3:]).split(".")[-1]
        if not (base in names if names else (base in declared or RESET_PORT.match(base))):
            continue
        stem = re.sub(r"_pin$", "", base, flags=re.I)
        low = bool(re.search(r"(n|_ni|_b|_l)$", stem, re.I))
        lv[k] = asserted[k] if asserted and k in asserted else (0 if low else 1)
        R[lit >> 1] = lv[k] ^ (lit & 1)
        key_of[lit >> 1] = k
    if asserted is None and R and "I" in d and os.environ.get("OT_LEC_RESET_POLARITY", "struct") != "name":
        for v in sorted(R):
            S = {b: set(reset_state(d, {**R, v: b}, 1)[0]) for b in (0, 1)}
            n = {b: len(S[b] - S[1 - b]) for b in (0, 1)}      # forced ONLY at that level: constant registers excluded
            if n[1 - R[v]] > 2 * max(1, n[R[v]]):
                R[v] = 1 - R[v]
                lv[key_of[v]] ^= 1
    if levels is not None:
        levels.update(lv)
    return R


def reset_state(d, R, cycles):
    """Ternary constant propagation of one side's AIG with every reset port asserted for `cycles` clock edges from
    an all-unknown power-up state -> {latch var: 0 / 1} for the registers whose value is then a proved constant (a
    register with a reset, a reset synchroniser, a register reloaded every cycle from those), plus {latch var: the
    edge it first became constant}.  Pure constant propagation (AND with a definite 0 is 0): no assumption on any
    unknown value, so a register that only holds itself until a load stays unknown."""
    I, Lc, a = d["I"], d["L"], d["ands"]
    base = I + Lc + 1
    st, first = {}, {}
    for cyc in range(1, cycles + 1):
        val = [None] * (base + d["A"])
        val[0] = 0
        for v, b in R.items():
            val[v] = b
        for v, b in st.items():
            val[v] = b
        for k in range(d["A"]):
            r0, r1 = a[2 * k], a[2 * k + 1]
            x, y = val[r0 >> 1], val[r1 >> 1]
            x = None if x is None else x ^ (r0 & 1)
            y = None if y is None else y ^ (r1 & 1)
            val[base + k] = 0 if (x == 0 or y == 0) else 1 if (x == 1 and y == 1) else None
        nst = {}
        for i, nxt in enumerate(d["latches"]):
            x = val[nxt >> 1]
            if x is not None:
                nst[I + 1 + i] = x ^ (nxt & 1)
        for v, b in nst.items():
            if st.get(v) != b:
                first[v] = cyc
        st = nst
    return st, first


def noreset_classify(L):
    """per side: the reset-state value of every register (reset_state, OT_LEC_RESET_CYCLES edges, default 4) ->
    L.rst_val[(side, key)] = (value or None, first edge)."""
    cycles = int(os.environ.get("OT_LEC_RESET_CYCLES", "4"))
    L.rst_val, L.rst_ports = {}, {}
    pol = None
    for side, d, p in (("gold", L.gold, L.gp), ("gate", L.gate, L.tp)):
        lv = {}
        R = reset_vars(d, p, pol, lv, getattr(L, "kit_reset_ports", None))
        pol = lv if pol is None else pol
        L.__dict__.setdefault("rst_asserted", {})[side] = lv
        L.rst_ports[side] = sorted(k for k, lit in p.items() if (lit >> 1) in R and k.startswith("pi:"))
        st, first = reset_state(d, R, cycles)
        L.__dict__.setdefault("_rst_state", {})[side] = st
        for k, lit in p.items():
            if k.startswith("ff:"):
                v = lit >> 1
                L.rst_val[(side, k)] = (None if v not in st else st[v] ^ (lit & 1), first.get(v))


def release_states(d, st, n):
    """Ternary constant propagation for n further edges after the reset window, from the reset state st, with EVERY
    input unknown (the reset ports too: after the window the port may release or stay asserted) -> [state after edge
    window+1, ..., window+n] ({latch var: 0 / 1}).  An over-approximation of every reachable state at those edges: a
    register is known only when its value is forced, e.g. a region reset held by the core's own synchronous-release
    reset relay (ot_rst_relay: SYNC_STAGES + TREE_STAGES edges after the port releases)."""
    I, Lc, a = d["I"], d["L"], d["ands"]
    base = I + Lc + 1
    out = []
    for _ in range(n):
        val = [None] * (base + d["A"])
        val[0] = 0
        for v, b in st.items():
            val[v] = b
        for k in range(d["A"]):
            r0, r1 = a[2 * k], a[2 * k + 1]
            x, y = val[r0 >> 1], val[r1 >> 1]
            x = None if x is None else x ^ (r0 & 1)
            y = None if y is None else y ^ (r1 & 1)
            val[base + k] = 0 if (x == 0 or y == 0) else 1 if (x == 1 and y == 1) else None
        st = {}
        for i, nxt in enumerate(d["latches"]):
            x = val[nxt >> 1]
            if x is not None:
                st[I + 1 + i] = x ^ (nxt & 1)
        out.append(st)
    return out


def release_unmasked(L, side, delayed, cycles, dropped=()):
    """delayed: {key: edge e > cycles} constant hypotheses on unmatched registers of one side whose base case is
    only established e edges after power-up, i.e. after the reset window (a reload chain longer than the window,
    rooted at a combinational constant or a reset register).  Before edge e such a register Q may still hold its X
    power-up value.  That is harmless exactly when nothing observes it: at every edge t in (cycles, e] the next
    state of every other register R must not depend on Q's value (taint: a path from Q to D(R) that no FORCED 0
    blocks, the forced values from release_states with every input free, e.g. a write enable or a reset held by
    the core's own reset relay), and no primary output may read Q.  Then every compare point and every hypothesis
    is the one the trace with Q == c gives, so the induction base moves to edge e without any reset-duration
    assumption.  Exempt readers: unmatched registers with no hypothesis (free inputs of every miter already).
    dropped: (side, key) hypotheses the caller already drops (free registers, like any unhypothesised one).
    -> {key} of delayed hypotheses that are observable before their edge (dropped by the caller)."""
    d, p = (L.gold, L.gp) if side == "gold" else (L.gate, L.tp)
    I, Lc, a = d["I"], d["L"], d["ands"]
    base = I + Lc + 1
    qe = {p[k] >> 1: e for k, e in delayed.items()}
    key_of = {p[k] >> 1: k for k in delayed}
    vkey = {lit >> 1: k for k, lit in p.items() if k.startswith("ff:")}
    matched = set(getattr(L, "matched", ()))
    hyp = getattr(L, "hyp", {})
    free = lambda k: k is not None and k not in matched and (
        (side, k) in dropped or ((side, k) not in hyp and ("both", k) not in hyp))
    watch = [(I + 1 + i, nxt) for i, nxt in enumerate(d["latches"])
             if (I + 1 + i) not in qe and not free(vkey.get(I + 1 + i))]
    bad_nodes = []
    last = max(qe.values())
    cache = L.__dict__.setdefault("_release_states", {})
    if len(cache.get(side, ())) < last - cycles:
        cache[side] = release_states(d, L._rst_state[side], last - cycles)
    states = [L._rst_state[side]] + cache[side]
    for s_ in range(cycles, last):                   # state after edge s_ -> next state (edge s_ + 1)
        src = {v for v, e in qe.items() if e > s_}   # Q not yet established at s_
        st = states[s_ - cycles]
        val = [None] * (base + d["A"])
        val[0] = 0
        for v, b in st.items():
            val[v] = b
        taint = bytearray(base + d["A"])
        for v in src:
            taint[v] = 1
        for k in range(d["A"]):
            r0, r1 = a[2 * k], a[2 * k + 1]
            x, y = val[r0 >> 1], val[r1 >> 1]
            x = None if x is None else x ^ (r0 & 1)
            y = None if y is None else y ^ (r1 & 1)
            val[base + k] = 0 if (x == 0 or y == 0) else 1 if (x == 1 and y == 1) else None
            if x == 0 or y == 0:
                continue                             # a forced 0 blocks: the AND does not see Q
            if taint[r0 >> 1] or taint[r1 >> 1]:
                taint[base + k] = 1
        for v, nxt in watch:
            if taint[nxt >> 1]:
                bad_nodes.append(nxt >> 1)
        bad_nodes += [o >> 1 for o in d["outputs"] if taint[o >> 1]]
        if bad_nodes:
            break
    bad = set()
    for root in bad_nodes:                           # blame the delayed registers in the observer's cone
        seen, stack = set(), [root]
        while stack:
            v = stack.pop()
            if v in seen or v == 0:
                continue
            seen.add(v)
            if v in qe:
                bad.add(key_of[v])
            elif v >= base:
                q = v - base
                stack += (a[2 * q] >> 1, a[2 * q + 1] >> 1)
    return bad


def latch_cone(L, side, k, cap=200000):
    """The registers in D(k)'s own-side cone. Unknown/X sources, anonymous
    state or a cone over cap return None: none can establish a base case.
    Cached because the AIGs never change."""
    cache = L.__dict__.setdefault("_latch_cone", {})
    if (side, k) in cache:
        return cache[(side, k)]
    d, c = (L.gold, L.gc) if side == "gold" else (L.gate, L.tc)
    if "_qkey" not in L.__dict__:
        L._qkey = {sd: {lit >> 1: kk for kk, lit in p.items() if kk.startswith("ff:")}
                   for sd, p in (("gold", L.gp), ("gate", L.tp))}
    I, Lc, a = d["I"], d["L"], d["ands"]
    if "_noreset_xvars" not in L.__dict__:
        L._noreset_xvars = {"gold": {v >> 1 for v in L.gx}, "gate": {v >> 1 for v in L.tx}}
    xvars = L._noreset_xvars[side]
    seen, stack, regs, n = set(), [c[k] >> 1], set(), 0
    while stack:
        v = stack.pop()
        if v == 0 or v in seen:
            continue
        seen.add(v)
        if v <= I + Lc:
            if v in xvars:
                cache[(side, k)] = None   # X-masked induction is not a constant's base case
                return None
            if v > I:
                if v not in L._qkey[side]:
                    cache[(side, k)] = None   # anonymous state: no untracked base-case assumptions
                    return None
                regs.add(L._qkey[side][v])
            continue
        n += 1
        if n > cap:
            cache[(side, k)] = None
            return None
        q = v - I - Lc - 1
        stack += (a[2 * q] >> 1, a[2 * q + 1] >> 1)
    cache[(side, k)] = frozenset(regs)
    return cache[(side, k)]


def noreset_sound(L):
    """{(side, key): first edge} of the constant hypotheses that hold in the reset state (base case), by a fixpoint
    over OT_LEC_RESET_CYCLES edges: a hypothesis holds from edge e when the reset state gives the constant
    (reset_state), or when D(k) does not read k and every constant-hypothesised register in its cone holds from
    edge e - 1 (D(k) == c is proved by the induction for every value of the other, free, registers).
    Unestablished equality/FSM hypotheses cannot supply that base case.
    Release edges (LEC-FPREG 10-27): an unmatched register's reload chain may continue for OT_LEC_RELEASE_EDGES
    (default 8) edges past the window (a pipelined fp unit's constant err / exponent bits: decode constant ->
    5 unreset cut registers -> constant from edge 5); such a base case at edge e > window is kept only when
    release_unmasked shows no register or output observes the register before edge e (its readers are held by
    the core's own reset relay).  Matched registers (compare points) never take a release-edge base case."""
    if not hasattr(L, "rst_val"):
        noreset_classify(L)
    cycles = int(os.environ.get("OT_LEC_RESET_CYCLES", "4"))
    extra = max(0, int(os.environ.get("OT_LEC_RELEASE_EDGES", "8")))
    consts = {(sd, k): h[1] for (sd, k), h in L.hyp.items() if h[0] == "const"}
    sides = lambda sd: ("gold", "gate") if sd == "both" else (sd,)
    banned = set()
    while True:
        held = _noreset_held(L, consts, sides, cycles, extra, banned)
        late = [(s, k) for (s, k), e in held.items() if e > cycles]
        if not late:
            break
        bad = set()
        for side in ("gold", "gate"):
            dl = {k: held[(s, k)] for s, k in late if s == side}
            if dl:
                bad |= {(side, k) for k in release_unmasked(L, side, dl, cycles, banned)}
        if not bad:
            break
        banned |= bad
    L.noreset_release = {sk: e for sk, e in held.items() if e > cycles}
    out = {}
    for (sd, k) in consts:
        es = [held.get((s, k)) for s in sides(sd)]
        if all(x is not None for x in es):
            out[(sd, k)] = max(es)
    return out


def _noreset_held(L, consts, sides, cycles, extra, banned):
    """noreset_sound's fixpoint -> {(side, key): first edge the constant holds}; edges past `cycles` only for
    unmatched registers not in `banned`."""
    held = {}                                 # (side, key) -> edge, per side
    matched = set(L.matched)
    for (sd, k), c in consts.items():
        for s in sides(sd):
            v, e = L.rst_val.get((s, k), (None, None))
            edges = [e or 1] if v == c else []
            if getattr(L, "raw_constant_status", {}).get((s, k, c)) == "proved":
                edges.append(1)           # D == c for ALL inputs/state, including every RTL X
            prefix = getattr(L, "raw_prefix_edges", {}).get((s, k, c))
            if prefix is not None and (prefix <= cycles or
                    (sd != "both" and k not in matched and (s, k) not in banned)):
                edges.append(prefix)
            if edges:
                held[(s, k)] = min(edges)
    hyp_side = lambda s, j: (("both", j) in consts) or ((s, j) in consts)
    for e in range(1, cycles + extra + 1):
        new = {}
        for (sd, k), c in consts.items():
            for s in sides(sd):
                if (s, k) in held:
                    continue
                if e > cycles and (sd == "both" or k in matched or (s, k) in banned):
                    continue
                cone = latch_cone(L, s, k)
                if cone is None or k in cone:
                    continue
                dc, qp = (L.gc, L.gp) if s == "gold" else (L.tc, L.tp)
                if any(dc.get(j) == qp[j] for j in cone):
                    continue     # an unwritten register's X rail cannot seed another constant
                # Equality/FSM hypotheses can be inductive without being true in
                # the power-up state. They are not a base case for a constant.
                if any(h is not None and h[0] != "const" for j in cone
                       for h in (L.hyp.get(("both", j)), L.hyp.get((s, j)))):
                    continue
                if any(cs in (s, "both") and set(ks) & cone for cs, ks, _ in L.cons):
                    continue
                if all((s, j) in held and held[(s, j)] < e for j in cone if hyp_side(s, j)):
                    new[(s, k)] = e
        if not new and e > max(held.values(), default=0):
            break                             # (reset-state edges are seeded up front: no gap before them)
        held.update(new)
    return held


def raw_constant_bases(L, work, conflicts, log):
    """Try an unconditional base case where structural cone analysis refused one.

    This uses the ORIGINAL side AIG, with every latch and input an independent
    free input. In particular RTL X inputs are ordinary Boolean variables:
    there are no X rails, reset constraints, correspondence hypotheses or FSM
    assumptions. UNSAT(D xor c) establishes Q == c after the first clock edge.
    SAT/undecided establishes nothing. Cache by side/key/value; the source AIGs
    are immutable throughout correspondence. The normal induction still proves
    every surviving hypothesis again in the final miter.
    """
    cache = L.__dict__.setdefault("raw_constant_status", {})
    batch = L.__dict__.get("_raw_constant_batch", 0)
    if not hasattr(L, "rst_val"):
        noreset_classify(L)
    # LEC-FPREG-3 10-27 (KV core 112 differ): also every constant the reset state does not give.  An adder MSB that
    # is 0 for every operand (qwen nearhbm_prod s1_e[9] = ea + ek + 5 < 512) is X in the ternary reset state when its
    # operand registers have no reset, and the reload rule refuses it when an operand register carries an equality
    # hypothesis; the universal proof (everything free) needs neither.
    for side, d, points in (("gold", L.gold, L.gc), ("gate", L.gate, L.tc)):
        candidates = sorted({(k, h[1]) for (sd, k), h in L.hyp.items()
                             if h[0] == "const" and sd in (side, "both")
                             and (side, k, h[1]) not in cache
                             and (latch_cone(L, side, k) is None
                                  or L.rst_val.get((side, k), (None, None))[0] != h[1])})
        if not candidates:
            continue
        m = Aig()
        m.ni = d["I"] + d["L"]
        m.ands = d["ands"]
        m.outs = [points[k] ^ c for k, c in candidates]
        m.onames = [f"raw-base:{side}:{k}:{c}" for k, c in candidates]
        status = prove(m, work, conflicts, log, tag=f"rawbase{batch}_{side}")
        for (k, c), name in zip(candidates, m.onames):
            cache[(side, k, c)] = status.get(name, "undecided")
        log.append(f"universal raw-D bases {side}: {sum(status.get(n) == 'proved' for n in m.onames)}"
                   f" / {len(candidates)} proved with all RTL X and state free")
        batch += 1
    L._raw_constant_batch = batch


def raw_prefix_miter(d, roots, steps):
    """Unroll raw source literals after `steps` clocks from entirely free state.

    Each source PI (including RTL X) is fresh at EACH edge. Latches at time
    zero are independent inputs. Only the requested time-expanded cones are
    copied; shared state aliases and within-edge PI correlations are preserved.
    No reset, hypothesis, X mask or state constraint enters this AIG.
    Roots are logical next-state literals, so frame steps-1 is state at steps.
    """
    if not isinstance(steps, int) or steps < 1:
        raise ValueError("raw prefix steps must be a positive integer")
    roots = list(roots)
    I, N, a = d["I"], d["L"], d["ands"]
    base = I + N + 1
    order, seen, leaves = [], set(), set()
    stack = [(steps - 1, lit >> 1, False) for lit in roots]
    while stack:
        t, v, done = stack.pop()
        key = (t, v)
        if v == 0 or key in seen:
            continue
        if v <= I or (v < base and t == 0):
            seen.add(key)
            leaves.add(key)
        elif done:
            seen.add(key)
            order.append(key)
        else:
            stack.append((t, v, True))
            if v < base:
                stack.append((t - 1, d["latches"][v - I - 1] >> 1, False))
            else:
                j = 2 * (v - base)
                stack.extend(((t, a[j] >> 1, False), (t, a[j + 1] >> 1, False)))
    m = Aig()
    vals = {key: m.add_input(f"raw_t{key[0]}_v{key[1]}") for key in sorted(leaves)}

    def value(t, lit):
        return (vals[(t, lit >> 1)] if lit >> 1 else 0) ^ (lit & 1)

    for t, v in order:
        if v < base:
            vals[(t, v)] = value(t - 1, d["latches"][v - I - 1])
        else:
            j = 2 * (v - base)
            vals[(t, v)] = m.AND(value(t, a[j]), value(t, a[j + 1]))
    m.outs = [value(steps - 1, lit) for lit in roots]
    return m


def raw_prefix_bases(L, candidates, steps, work, conflicts, log):
    """Prove requested constant bases after an exact finite prefix, unconditionally.

    This is opt-in proof work, not a duration contract: all initial state and
    every time-step input remain free. Late bases still pass release_unmasked
    before use; final induction proves preservation. SAT/undecided prove no base.
    """
    cache = L.__dict__.setdefault("raw_prefix_status", {})
    edges = L.__dict__.setdefault("raw_prefix_edges", {})
    for side, d, points in (("gold", L.gold, L.gc), ("gate", L.gate, L.tc)):
        todo = sorted({(k, c) for s, k, c in candidates if s == side
                       and (s, k, c, steps) not in cache})
        if not todo:
            continue
        if any(k not in points or c not in (0, 1) for k, c in todo):
            raise LecError("invalid raw prefix base candidate")
        m = raw_prefix_miter(d, [points[k] for k, c in todo], steps)
        m.outs = [lit ^ c for lit, (k, c) in zip(m.outs, todo)]
        m.onames = [f"raw-prefix:{side}:{k}:{c}:{steps}" for k, c in todo]
        batch = L.__dict__.get("_raw_prefix_batch", 0)
        status = prove(m, work, conflicts, log, tag=f"rawprefix{batch}_{side}_{steps}")
        L._raw_prefix_batch = batch + 1
        for (k, c), name in zip(todo, m.onames):
            result = status.get(name, "undecided")
            cache[(side, k, c, steps)] = result
            if result == "proved":
                edges[(side, k, c)] = min(steps, edges.get((side, k, c), steps))
        log.append(f"universal raw prefix {side} at edge {steps}: "
                   f"{sum(status.get(n) == 'proved' for n in m.onames)} / {len(todo)} bases")


def eq_const_resolve(L, log=None):
    """An equality hypothesis whose representative carries a constant hypothesis is that constant (HBM-CORES-REBAL-6
    10-28, side_rest u_egs: gold-only rem_stage[0][34..] = eq gold g_dig[2].src_rem[0], itself const 0, while the
    identical u_sq copy got const 0).  Left as 'eq', the register blocks every reload base case through its cone
    (noreset_sound refuses cones with equality hypotheses), so 466 structural shift-in zeros of one fsqrt copy were
    dropped.  Rewritten to ('const', c ^ inv) it must pass the same reset-state base case as any constant (stricter
    than the equality), and the final induction still proves it.  Chains resolve transitively; cycles and free
    representatives stay as they are. -> number rewritten."""
    def const_of(sd, k, seen):
        for key in (("both", k), (sd, k)):
            h = L.hyp.get(key)
            if h is None:
                continue
            if h[0] == "const":
                return h[1]
            if h[0] == "eq" and key not in seen:
                c = const_of(h[1], h[2], seen | {key})
                return None if c is None else c ^ h[3]
        return None
    n, first = 0, []
    for key, h in list(L.hyp.items()):
        if h[0] != "eq":
            continue
        c = const_of(h[1], h[2], {key})
        if c is not None:
            L.hyp[key] = ("const", c ^ h[3])
            n += 1
            if len(first) < 6:
                first.append(f"{key[0]}:{key[1]}={c ^ h[3]}")
    if n and log is not None:
        log.append(f"eq-to-const hypotheses resolved: {n} {first}")
    return n


def noreset_filter(L, log, tried, work=None, conflicts=1000):
    """Constant hypotheses on registers that are not that constant in the reset state (LEC-TOOL-4 10-27, COORD
    ruling on no-reset constants).  The correspondence induction proves Q == c -> D(Q) == c; its base case is the
    reset state.  A register with no reset (an X power-up, e.g. hcp_sys1 db <= nf_r on rs_take, argmax ti) that only
    holds itself until its first load is X there, and binding it to c would assume X == c for every output that can
    observe it before that load.  A constant hypothesis is kept only when noreset_sound shows it holds within
    OT_LEC_RESET_CYCLES edges of reset (the register resets to c, or is reloaded every cycle from registers that
    do); the others are dropped and never re-proposed (the register stays a free input, so an observable difference
    is reported, never assumed away). There is no switch to assume an unknown
    power-up value equals a constant. -> number dropped."""
    eq_const_resolve(L, log)
    if work is not None:
        raw_constant_bases(L, work, conflicts, log)
        steps = int(os.environ.get("OT_LEC_RAW_BASE_STEPS", "0"))
        if steps > 1:
            ok = noreset_sound(L)
            candidates = [(s, k, h[1]) for (sd, k), h in L.hyp.items() if h[0] == "const" and (sd, k) not in ok
                          for s in (("gold", "gate") if sd == "both" else (sd,))]
            raw_prefix_bases(L, candidates, steps, work, conflicts, log)
    total = 0
    while True:                     # dropping one can unseat a register reloaded from it
        ok = noreset_sound(L)
        bad = [(sd, k, h[1]) for (sd, k), h in L.hyp.items() if h[0] == "const" and (sd, k) not in ok]
        if not bad:
            break
        L.noreset_dropped = getattr(L, "noreset_dropped", {})
        for sd, k, c in bad:
            del L.hyp[(sd, k)]
            tried[(sd, k, "c")] += 6
            tried[("tc", sd, k)] += 1
            L.noreset_dropped[(sd, k)] = c
        total += len(bad)
        log.append(f"no-reset constants: {len(bad)} constant hypotheses dropped (not that constant in the reset "
                   f"state: X power-up until a load) {[f'{s}:{k}={c}' for s, k, c in bad[:6]]}")
    return total


def noreset_report(L):
    """lec.json 'noreset_constants': every constant hypothesis kept, with the reset-state basis, and every one
    dropped by noreset_filter."""
    if not hasattr(L, "rst_val"):
        noreset_classify(L)
    kept = []
    ok = noreset_sound(L)
    for (sd, k), h in sorted(L.hyp.items()):
        if h[0] != "const":
            continue
        edge = ok.get((sd, k), -1)
        cyc = int(os.environ.get("OT_LEC_RESET_CYCLES", "4"))
        sides = ("gold", "gate") if sd == "both" else (sd,)
        raw = all(getattr(L, "raw_constant_status", {}).get((s, k, h[1])) == "proved" for s in sides)
        prefix = all(getattr(L, "raw_prefix_edges", {}).get((s, k, h[1])) == edge for s in sides)
        kept.append(dict(register=k, side=sd, value=h[1], edge=edge,
                         basis="universal_raw_D" if raw else
                               "universal_raw_prefix" if prefix else
                               "reset" if edge <= 1 else "reloaded" if edge <= cyc else "release"))
    dropped = [dict(register=k, side=sd, value=c) for (sd, k), c in sorted(getattr(L, "noreset_dropped", {}).items())
               if (sd, k) not in L.hyp]
    L.noreset_kept_all, L.noreset_dropped_all = kept, dropped      # uncapped: noreset_listing
    return dict(enabled=True, reset_ports=L.rst_ports, reset_asserted=getattr(L, "rst_asserted", {}), reset_cycles=int(os.environ.get("OT_LEC_RESET_CYCLES", "4")),
                release_edges=int(os.environ.get("OT_LEC_RELEASE_EDGES", "8")),
                n_release=sum(1 for e in kept if e["basis"] == "release"),
                release=[e for e in kept if e["basis"] == "release"][:500],
                n_universal_raw_D=sum(1 for e in kept if e["basis"] == "universal_raw_D"),
                universal_raw_D=[e for e in kept if e["basis"] == "universal_raw_D"][:500],
                raw_base_steps=int(os.environ.get("OT_LEC_RAW_BASE_STEPS", "0")),
                n_universal_raw_prefix=sum(1 for e in kept if e["basis"] == "universal_raw_prefix"),
                universal_raw_prefix=[e for e in kept if e["basis"] == "universal_raw_prefix"][:500],
                n_kept=len(kept), n_reloaded=sum(1 for e in kept if e["basis"] == "reloaded"),
                n_dropped=len(dropped), reloaded=[e for e in kept if e["basis"] == "reloaded"][:500],
                dropped=dropped[:500],
                basis=("a constant hypothesis is kept only when the reset state (every reset port asserted for "
                       "reset_cycles edges from an all-unknown power-up) gives that constant, or an acyclic "
                       "reload is inductively constant from already established constants; equality/FSM "
                       "assumptions never establish a constant's base case"))


def noreset_listing(L, path):
    """COORD 10-29 (hd_ctl): lec.py lists EVERY register it treats as a constant, not only the first 500 that
    lec.json carries.  Writes PATH (TSV: status kept|dropped, side, register, value, edge, basis) from the last
    noreset_report and -> dict(file, sha256, n_kept, n_dropped) for lec.json.  The constant rule itself is
    unchanged: a register is a constant only when its reset state or a structurally constant reload chain gives
    that constant (noreset_sound); a no-reset register on a hold / enable path (D = en ? c : Q) is never one."""
    kept = getattr(L, "noreset_kept_all", None)
    if kept is None:
        noreset_report(L)
        kept = L.noreset_kept_all
    rows = ["status\tside\tregister\tvalue\tedge\tbasis"]
    rows += [f"kept\t{e['side']}\t{e['register']}\t{e['value']}\t{e['edge']}\t{e['basis']}" for e in kept]
    rows += [f"dropped\t{e['side']}\t{e['register']}\t{e['value']}\t\tnot constant in the reset state"
             for e in L.noreset_dropped_all]
    data = ("\n".join(rows) + "\n").encode()
    Path(path).write_bytes(data)
    return dict(file=str(path), sha256=hashlib.sha256(data).hexdigest(), n_kept=len(kept),
                n_dropped=len(L.noreset_dropped_all))


def slang_elements(aliases_file):
    """slang lays an unpacked array out as one flat vector (`reg [3:0] x [0:N-1]`: element 0 at the MSB) and drives
    each element from its own cell `$driver$x[i]` (the aldff / dff of that element).  -> {gold key 'ff:<scope>x[f]':
    '[i]...[b]'}: the element index tuple and the bit within the element of every flat bit such a cell drives, read
    from the gold design written before techmap (gold.aliases.json).  Empty when the file or the cells are absent."""
    try:
        d = json.loads(Path(aliases_file).read_text())
    except (OSError, ValueError):
        return {}
    out = {}
    for mod in d.get("modules", {}).values():
        drv = {}                                    # (array name, bit id) -> '[i]..[b]'
        for cn, c in mod.get("cells", {}).items():
            mm = re.search(r"\$driver\$([^$\[\]]+)((?:\[\d+\])+)$", cn)
            if not mm:
                continue
            for b, bit in enumerate(c.get("connections", {}).get("Q", ())):
                if isinstance(bit, int):
                    scope = cn[:mm.start()].removeprefix("$flatten\\").replace("\\", "")
                    name = scope + mm[1]
                    qwidth = len(c.get("connections", {}).get("Q", ()))
                    drv[(name, bit)] = mm[2] + (f"[{b}]" if qwidth > 1 else "")
        if not drv:
            continue
        by_bit = collections.defaultdict(list)
        for (name, bit), suffix in drv.items():
            by_bit[bit].append((name, suffix))
        for nn, w in mod.get("netnames", {}).items():
            if w.get("hide_name"):
                continue
            for f, bit in enumerate(w.get("bits", ())):
                e = drv.get((nn.replace("\\", ""), bit)) if isinstance(bit, int) else None
                if e is None and isinstance(bit, int):
                    matches = {v for name, v in by_bit.get(bit, ())
                               if nn == name or nn.endswith("." + name)}
                    if len(matches) == 1:
                        e = matches.pop()
                if e:
                    out[f"ff:{nn}[{f}]"] = e
    return out


def slang_packed_vectors(aliases_file):
    """-> {gold base 'ff:<scope>x'} of the registers the RTL declares as PACKED vectors (`reg [N-1:0] x`), read from
    the slang gold design written before techmap (gold.aliases.json): one `$driver$x` cell (no element index; an
    unpacked array has one `$driver$x[i]` per element, see slang_elements) whose Q is exactly the public net x, wider
    than one bit.  Empty when the file or such cells are absent (read_verilog gold: no change)."""
    try:
        d = json.loads(Path(aliases_file).read_text())
    except (OSError, ValueError):
        return frozenset()
    out = set()
    for mod in d.get("modules", {}).values():
        drv = {}                                    # Q bit tuple -> driven register name (unindexed $driver$x)
        for cn, c in mod.get("cells", {}).items():
            mm = re.search(r"\$driver\$([^$\[\]:]+)$", cn)
            q = c.get("connections", {}).get("Q", ())
            if mm and len(q) > 1 and all(isinstance(b, int) for b in q):
                drv[tuple(q)] = mm[1]
        if not drv:
            continue
        for nn, w in mod.get("netnames", {}).items():
            name = drv.get(tuple(w.get("bits", ())))
            if name and not w.get("hide_name") and (nn == name or nn.endswith("." + name)):
                out.add("ff:" + nn.replace("\\", ""))
    return frozenset(out)


def normalize_gold_elements(L, elements, log):
    """Restore scalar unpacked element names before matching state.

    A partial synthesized array may keep indices that happen to be flat gold
    indices too (gold rv[0..18] versus real rv[1..19], with gate rv[2..4]).
    Such accidental matches cannot be corrected by unmatched-only pairing.
    Driver Q-net metadata supplies the names; all next-state checks still run.
    """
    ren = {}
    for k, suffix in elements.items():
        ix = IDX.match(k)
        if k in L.gp and ix and suffix.count("[") == 1:
            ren[k] = ix[1] + suffix
    # Reject ambiguous metadata instead of silently collapsing registers.
    names = [ren.get(k, k) for k in L.gp]
    if len(names) != len(set(names)):
        raise LecError("slang element names collide with another gold key point")
    changed = sum(k != v for k, v in ren.items())
    L.element_names = {v: v[len(IDX.match(v)[1]):] for v in ren.values()}
    if not changed:
        return 0
    L.gp = {ren.get(k, k): v for k, v in L.gp.items()}
    L.gc = {ren.get(k, k): v for k, v in L.gc.items()}
    L.galias = {ren.get(k, k): {ren.get(a, a) for a in aliases}
                for k, aliases in L.galias.items()}
    L.matched = sorted(set(L.gp) & set(L.tp))
    L.gonly = sorted(set(L.gp) - set(L.tp))
    L.tonly = sorted(set(L.tp) - set(L.gp))
    log.append(f"slang element names: {changed} gold register keys normalized from driver Q nets")
    return changed


def json_alias_keys(L, log, work=None):
    """Recover public Q-wire aliases omitted by write_aiger's latch map.

    gold.aliases.json is written from the same elaborated gold before techmap.
    A gold-only and gate-only name at the same position of IDENTICAL public
    net bit vectors may be paired when the relation is one-to-one. Requiring
    the whole vector avoids confusing slang-flattened scalar unpacked arrays
    with gate element names (cf[0:4] versus cf[1]/cf[3]). This only renames gate key
    points: every D function and every downstream comparison stays in the
    miter, so an incorrect implementation still fails induction. No simulated
    signatures or inferred name similarity establish this correspondence.
    """
    if work is None:
        return 0
    try:
        data = json.loads((Path(work) / "gold.aliases.json").read_text())
    except (OSError, ValueError):
        return 0
    wanted = set(L.gonly) | set(L.tonly)
    held = {k for (_side, k) in L.hyp}
    bits = {}
    ambiguous = set()
    bit_of, bit_amb, scalar = {}, set(), set()     # key -> one net bit (mn, bit) for the scalar-alias pass below
    for mn, mod in data.get("modules", {}).items():
        for nn, net in mod.get("netnames", {}).items():
            if net.get("hide_name") or net.get("upto"):
                continue
            name = GENBLK.sub("", nn.replace("\\", "").replace(" ", "").replace("/", "."))
            offset = int(net.get("offset", 0))
            vector = tuple(net.get("bits", ()))
            for i, bit in enumerate(vector):
                if not isinstance(bit, int):
                    continue
                keys = [f"ff:{name}[{i + offset}]"]
                if len(net.get("bits", ())) == 1 and offset == 0:
                    keys.append(f"ff:{name}")
                for key in keys:
                    if key not in wanted or key in held:
                        continue
                    if bit_of.setdefault(key, (mn, bit)) != (mn, bit):
                        bit_amb.add(key)
                    if len(vector) == 1 and offset == 0 and key == f"ff:{name}":
                        scalar.add(key)
                    value = (mn, vector, i)
                    if key in bits and bits[key] != value:
                        ambiguous.add(key)
                    bits[key] = value
    gold, gate = collections.defaultdict(list), collections.defaultdict(list)
    for key in L.gonly:
        if key in bits and key not in ambiguous:
            gold[bits[key]].append(key)
    for key in L.tonly:
        if key in bits and key not in ambiguous:
            gate[bits[key]].append(key)
    pairs = [(gate[b][0], gs[0]) for b, gs in gold.items()
             if len(gs) == 1 and len(gate.get(b, ())) == 1]
    # Scalar Q-wire alias of one vector bit (QC stream 10-30: 'wire cm_x = p2l[234]'; slang keeps the flop as p2l[234],
    # read_verilog names it after the scalar cm_x).  The GATE key must be a plain 1-bit public net, so no gate-side
    # index convention is involved (unlike the cf[1] vs h2.cf_o slices kept out above); the gold key is gold's own
    # element name and both are the SAME gold net bit.  One-to-one per bit only; again only gate keys are renamed.
    paired = {k for pr in pairs for k in pr}
    gbit, tbit = collections.defaultdict(list), collections.defaultdict(list)
    for key in L.gonly:
        if key in bit_of and key not in bit_amb and key not in paired:
            gbit[bit_of[key]].append(key)
    for key in L.tonly:
        if key in bit_of and key not in bit_amb and key not in paired:
            tbit[bit_of[key]].append(key)
    pairs += [(ts[0], gbit[b][0]) for b, ts in tbit.items()
              if len(ts) == 1 and ts[0] in scalar and len(gbit.get(b, ())) == 1]
    for tk, gk in pairs:
        L.tp[gk] = L.tp.pop(tk)
        if tk in L.tc:
            L.tc[gk] = L.tc.pop(tk)
    if pairs:
        L.matched = sorted(set(L.gp) & set(L.tp))
        L.gonly = sorted(set(L.gp) - set(L.tp))
        L.tonly = sorted(set(L.tp) - set(L.gp))
        log.append(f"gold JSON Q aliases: {len(pairs)} gate flops re-keyed to exact gold wire bits")
    return len(pairs)


def slang_flat_word_keys(members, gate_families):
    """Exact multi-dimensional logical driver indices -> read_verilog flat words.

    Only a complete zero-based Cartesian driver grid with uniform packed width
    qualifies. Gate words must cover that grid's product, with the same bit
    extent (individual bits may have merged away). There is one row-major
    logical flattening; no reversal or simulation score chooses a layout.
    Return gate key -> gold key only when exactly one named family qualifies.
    These are correspondence proposals, never assumptions or waived compares.
    """
    logical = {}
    for gold, (_outer, suffix) in members.items():
        ix = tuple(map(int, re.findall(r"\d+", suffix)))
        if len(ix) < 3 or ix in logical:
            return {}, ()
        logical[ix] = gold
    if not logical or len({len(ix) for ix in logical}) != 1:
        return {}, ()
    rank = len(next(iter(logical)))
    shape = tuple(max(ix[j] for ix in logical) + 1 for j in range(rank))
    total = 1
    for j, n in enumerate(shape):
        if min(ix[j] for ix in logical) != 0:
            return {}, ()
        total *= n
    if total != len(logical):                         # holes / partial drivers: no shape inference
        return {}, ()
    width = shape[-1]
    words = total // width
    candidates = []
    for family in gate_families:
        indexed = {}
        for suffix, gate in family.items():
            ix = tuple(map(int, re.findall(r"\d+", suffix)))
            if len(ix) != 2 or ix in indexed:
                break
            indexed[ix] = gate
        else:
            if not indexed or {ix[0] for ix in indexed} != set(range(words)) \
                    or min(ix[1] for ix in indexed) != 0 or max(ix[1] for ix in indexed) + 1 != width:
                continue
            mapping = {}
            for (word, bit), gate in indexed.items():
                dims, rest = [], word
                for n in reversed(shape[:-1]):
                    rest, i = divmod(rest, n)
                    dims.append(i)
                mapping[gate] = logical[tuple(reversed(dims)) + (bit,)]
            if len(mapping) != len(indexed):
                continue
            candidates.append(mapping)
    return (candidates[0], shape) if len(candidates) == 1 else ({}, ())


def slang_element_keys(L, log, work=None):
    """gold-only flops of a slang-flattened array, paired by NAME with the gate flops of the same element, from slang's
    per-element driver cells (slang_elements): gold 'ff:S.X[f]' is element '[i]..[b]'.
      * the gate kept the element name: 'ff:S.X[i]..[b]' or its relaid form 'ff:S.X#t[i]..[b]' (gate-only) -> re-key;
      * the LAST element of the array (i = its largest outer index) whose gate flops synthesis named after the wire
        they drive (`assign q = r[D-1]`; rename -wire picks the output: ot_qkh_relay D=2 -> gate 'S.q[b]'): when the
        scope S has exactly one gate-only base 'ff:S.W' whose bit indices are exactly the element's bit indices and
        none of them is a gold name -> re-key gate 'ff:S.W[b]' to the gold key of element [i][b].
    Sound: a bijection of key points; every next-state function is still proved (a wrong pairing can only produce a
    difference).  PATH-KV 10-26: kv3_head_eighth_e1 KEEP FAIL 36 = u_ric.r[16..31] / u_rkv.r[2..3] (gold) vs
    u_ric.q[0..15] / u_rkv.q[0..1] (gate), their relaid first stages paired to the wrong element by function."""
    elem = slang_elements(Path(work) / "gold.aliases.json") if work is not None else {}
    # Current main already normalized scalar unpacked names; keep those canonical indices.
    elem.update(getattr(L, "element_names", {}))
    if not elem:
        return 0
    held = {k for (_sd, k) in L.hyp}
    tonly = set(L.tonly)
    gonly = {k for k in L.gonly if k in elem and k not in held}
    if not gonly:
        return 0
    arr = collections.defaultdict(dict)              # gold array base -> {gold key: (outer index, element suffix)}
    for k, e in elem.items():
        m = IDX.match(k)
        if m:
            arr[m.group(1)][k] = (int(re.match(r"\[(\d+)\]", e).group(1)), e)
    tbase = collections.defaultdict(dict)            # (scope) -> {gate base: {bit suffix: gate key}}
    for k in tonly:
        m = IDX.match(k)
        if m and k.startswith("ff:") and k not in held:
            b = m.group(1)
            tbase[b.rsplit(".", 1)[0]].setdefault(b, {})[m.group(2)] = k
    mp = {}                                          # gate key -> gold key
    for gb, members in arr.items():
        scope = gb.rsplit(".", 1)[0]
        families = [tbase.get(scope, {}).get(b, {}) for b in (gb, gb + "#t")]
        flat, shape = slang_flat_word_keys(members, families)
        flat = {tk: gk for tk, gk in flat.items() if gk in gonly and tk not in mp}
        if flat:
            mp.update(flat)
            log.append(f"slang mixed-radix keys: {gb} logical driver grid {shape} -> "
                       f"flat gate words ({len(flat)} bits)")
        proposed = set(mp.values())
        top = max(i for i, _ in members.values())
        last = {}
        for gk, (i, e) in members.items():
            if gk not in gonly or gk in proposed:
                continue
            for tk in (gb + e, gb + "#t" + e):
                if tk in tonly and tk not in mp:
                    mp[tk] = gk
                    proposed.add(gk)
                    break
            else:
                if i == top:
                    last[e[len(f"[{i}]"):]] = gk     # bit suffix '[b]' -> gold key
        if not last:
            continue
        cands = [b for b, bits in tbase.get(scope, {}).items()
                 if b != gb and not b.endswith("#t") and set(bits) == set(last) and not any(k in L.gp for k in bits.values())]
        if len(cands) == 1:
            for sfx, gk in last.items():
                mp[tbase[scope][cands[0]][sfx]] = gk
            log.append(f"slang last element: gate {cands[0].split('.')[-1]} ({len(last)} b) -> gold "
                       f"{gb.split('.')[-1]}[{top}] ({scope.split('.')[-1]})")
    if not mp:
        return 0
    for tk, gk in mp.items():
        L.tp[gk] = L.tp.pop(tk)
        if tk in L.tc:
            L.tc[gk] = L.tc.pop(tk)
    L.matched = sorted(set(L.gp) & set(L.tp))
    L.gonly = sorted(set(L.gp) - set(L.tp))
    L.tonly = sorted(set(L.tp) - set(L.gp))
    log.append(f"slang element keys: {len(mp)} gate flops re-keyed to their gold element names")
    return len(mp)


def memory_geometry(aliases_file):
    """{gold array base 'ff:<scope>.<name>': (element width, size, start offset)} of every RTL memory of the gold
    design written before techmap (gold.aliases.json 'memories'): the source's own element geometry.  Empty when
    the file is absent or unreadable."""
    try:
        d = json.loads(Path(aliases_file).read_text())
    except (OSError, ValueError):
        return {}
    out = {}
    for mod in d.get("modules", {}).values():
        for name, mem in mod.get("memories", {}).items():
            try:
                g = (int(mem["width"]), int(mem["size"]), int(mem.get("start_offset", 0)))
            except (KeyError, TypeError, ValueError):
                continue
            base = "ff:" + GENBLK.sub("", name.replace("\\", "").replace(" ", "").replace("/", "."))
            out[base] = None if base in out and out[base] != g else g      # ambiguous name: no geometry
    return {k: v for k, v in out.items() if v}


def memory_layout(g, t, geom):
    """exact gate -> gold re-key of one RTL memory from its source geometry (word width W, size S, offset O of the
    pre-techmap gold memory).  Gold (memory_map after an optional opt_mem_widen by F = S / words): key [w][j] =
    address w*F + j//W, bit j%W (wide sub-word k holds address w*F + k at bits k*W: yosys' wide-port convention).
    Gate (synthesised netlist, one flop vector per element): [a][b] = address a, bit b.  When the gate has K = W/w
    times more elements than the gold memory has words (slang folds the inner unpacked dimension of
    `reg [w-1:0] x [0:N-1][0:K-1]` into one W-bit word, element 0 at the MSB, like its flat vectors), gate element
    a is word a//K, sub-element K-1-a%K (K = the one divisor of W that places every gate bit on a distinct gold bit;
    trailing elements may be absent).  -> {gate key: gold key} when every gate bit lands on a distinct gold bit,
    else None (never a guess)."""
    if not geom or not g or not t:
        return None
    W, S, O = geom
    if W <= 0 or S <= 0 or any(len(v) != 2 for v in g.values()):
        return None
    # one-bit elements: the gate names them x[a] (one index); bit 0 of element a (HBM argmax tvl[0:3][0:7])
    one = all(len(v) == 1 for v in t.values())
    if one:
        t = {k: (v[0], 0) for k, v in t.items()}
    elif any(len(v) != 2 for v in t.values()):
        return None
    words = {v[0] for v in g.values()}
    # widening factor F: wide word w holds addresses w*F .. w*F+F-1.  When the present words do not divide S, F is
    # read off the widest bit present: the LAST wide word may be partial (hcp_sys1 u_div r_rem [0:26] x 25 b ->
    # r_rem[0][0..399] = addresses 0..15, r_rem[1][0..274] = 16..26), or trailing words may be absent altogether
    # (HBM argmax tk / tvl [0:3]: the last tree level is unused, F = 1).  Every bit must land at an address < S.
    if S % len(words) == 0:
        F = S // len(words)
    else:
        F = max(j for _, j in g.values()) // W + 1
        if max(words) >= -(-S // F):
            return None
    gold = {}
    for k, (w, j) in g.items():
        if j >= F * W or w * F + j // W >= S:
            return None
        gold[(w * F + j // W, j % W)] = k
    if len(gold) != len(g):
        return None

    def place(elem):
        mp = {}
        for k, e in elem.items():
            if e not in gold:
                return None
            mp[k] = gold[e]
        return mp if len(set(mp.values())) == len(mp) else None

    amax = max(a for a, _ in t.values())
    bmax = max(b for _, b in t.values())
    elem = False
    if all(O <= a < O + S and 0 <= b < W for a, b in t.values()) and (W == 1 or not one):
        elem = None
    elif F == 1 and O == 0 and min(min(v) for v in t.values()) >= 0:
        # inner elements per gold word K (element width w = W / K): read off the gate's highest element and bit.
        # Trailing elements may be absent (a reduction tree `x [0:LL][0:LP-1]` uses LP >> lv elements at level lv:
        # HBM argmax ti / tvl last level keeps element 0 only, gate ti#t[24] = level 3 element 0 = gold
        # ti[3][126..143]); K must be the ONLY divisor of W that places every gate bit on a distinct gold bit
        # (tk: 264 b words, gate element 17 bit 32 fits K = 6 and K = 8; only K = 8 lands on gold bits), else no guess.
        fits = []
        for K in range(2, W + 1):
            w = W // K
            if W % K or amax >= K * S or bmax >= w or (one and w != 1):
                continue
            mp = place({k: (a // K, (K - 1 - a % K) * w + b) for k, (a, b) in t.items()})
            if mp:
                fits.append(mp)
        return fits[0] if len(fits) == 1 else None
    return place(t) if elem is None else None


def alias_arrays(L, log, words=4, work=None):
    """an RTL array whose gate flops synthesis named after an ALIAS array (`assign SX[i] = X[i]`: rename -wire picked
    the alias wire, so the gate holds SX[i][b] while the gold, read with the other frontend, holds X[h][flat]): the
    gold flops' own Q-net alias names carry the gate base, which is the evidence that pairs the two bases.  The index
    tuples are flattened mixed-radix (outer index reversed or not, either side) and the gate keys re-keyed to the gold
    names when the flattened gate set is a subset of the gold set (synthesis may have merged some elements into other
    registers: those gold flops stay gold-only and are paired by function in correspond); among the variants the one
    with the fewest disagreeing matched compare points in simulation is kept.  Sound: the re-key is a bijection of
    key points and every next-state function is still proved (a wrong layout can only produce a difference).
    The layout is read from slang's per-element driver cells when the gold has them (slang_elements); simulation
    alone cannot tell (PATH-KV-LEC 10-25: calendar wait_q / left_q / burst_q [0:N-1], slang element 0 at the MSB vs
    read_verilog x[0]: random patterns never reach wait_q == 0, both layouts mismatched equally, the first, element-
    reversed one was kept -> 528 false differences on kvs_pc and its head kit)."""
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

    # never re-key a point an existing hypothesis names (e.g. trace/relaid-line proposals made before this pass):
    # the re-key would orphan the hypothesis' key or representative
    held = set()
    for (_sd, k), h in L.hyp.items():
        held.add(k)
        for x in h[1:]:
            if isinstance(x, str):
                held.add(x)
            elif isinstance(x, (list, tuple)):
                held.update(y for y in x if isinstance(y, str))
    galias = getattr(L, "galias", {})
    elem = slang_elements(Path(work) / "gold.aliases.json") if work is not None else {}
    elem.update(getattr(L, "element_names", {}))
    geom = memory_geometry(Path(work) / "gold.aliases.json") if work is not None else {}
    G, T = split(k for k in L.gonly if k not in held), split(k for k in L.tonly if k not in held)
    for gb, g in sorted(G.items(), key=lambda x: -len(x[1])):
        votes = collections.Counter()
        for k in g:
            for a in galias.get(k, ()):
                m = IDX.match(a)
                if m and m.group(1) in T and m.group(1) != gb:
                    votes[m.group(1)] += 1
        if gb + "#t" in T:                          # the same array, re-keyed (relaid) because the frontends
            votes[gb + "#t"] = len(g)                # index it differently (slang gt[row][4 words] vs gt[q][j])
        for tb, n in votes.most_common(1):
            t = T[tb]
            if 2 * n < len(g):
                continue
            # The source memory's own geometry places every gate bit exactly, so the size guards below (made for
            # guessed layouts) do not apply: synthesis may keep far fewer bits than the gold memory has (hcp_sys1
            # u_div r_rem: gate 313 of 675, a triangular remainder pipeline whose constant low bits were dropped)
            gmp = memory_layout(g, t, geom.get(gb))
            if gmp:
                apply(gmp)
                del T[tb]
                log.append(f"alias array: gate {tb.split('.')[-1]} ({len(t)} b) -> gold {gb.split('.')[-1]} "
                           f"({len(g)} b, Q-net alias evidence {n}); source memory layout {geom[gb]} "
                           f"(width, size, offset) (simulation scoring unnecessary; proof pending)")
                continue
            if 2 * len(t) < len(g) or len(t) > len(g):
                continue
            cands = []
            for gr in (False, True):
                for tr in (False, True):
                    fg, ft = flats(g, gr), flats(t, tr)
                    if fg and ft and set(ft) <= set(fg):
                        mp = {ft[f]: fg[f] for f in ft}
                        if mp not in cands:
                            cands.append(mp)
            # The source memory's own geometry (pre-techmap gold: element width / size / offset) fixes the layout
            # exactly: yosys may widen a memory before mapping it (opt_mem_widen: a_pr [0:15] x 24 b -> 2 words x
            # 192 b, gold a_pr[w][j] = element 8w + j/24, bit j%24), and the gate may have dropped constant high
            # bits (a_pr#t[r][3..16]), so radices read off either side's maximal indices give none of the four
            # flat variants above the right stride (QC slw_hc0 10-26: 223 a_pr + 268 b_emin false differences).
            if not cands:
                continue
            if len(cands) == 1:
                # one candidate: no score can change the choice (N59: 512 one-bit u_pd2_emb_code_q_<i>.r arrays,
                # two whole-design simulations each, ~100 min before the first SAT round)
                apply(cands[0])
                del T[tb]
                log.append(f"alias array: gate {tb.split('.')[-1]} ({len(t)} b) -> gold {gb.split('.')[-1]} "
                           f"({len(g)} b, Q-net alias evidence {n}); single layout (proof pending)")
                continue
            # A unique element-driver winner selects exactly the mapping the
            # scored path below would select, independently of every simulation
            # score. Avoid rebuilding/simulating the whole design for each
            # small alias array (N59: thousands of arrays before the first SAT
            # round). This changes candidate discovery only: simultaneous
            # inductive proof/refinement still checks every selected relation.
            structural = [sum(1 for tk, gk in mp.items() if elem.get(gk) == tk[len(tb):]) for mp in cands]
            top = max(structural, default=0)
            if top > 0 and structural.count(top) == 1:
                mp = cands[structural.index(top)]
                apply(mp)
                del T[tb]
                log.append(f"alias array: gate {tb.split('.')[-1]} ({len(t)} b) -> gold {gb.split('.')[-1]} "
                           f"({len(g)} b, Q-net alias evidence {n}); unique slang element-driver layout "
                           f"{top}/{len(mp)} bits (simulation scoring unnecessary; proof pending)")
                continue
            base = mismatches()
            scored = []
            for mp in cands:
                apply(mp)
                scored.append((mismatches(), mp))
                apply({v: k for k, v in mp.items()})
            best = min(scored, key=lambda x: x[0])
            # slang's per-element driver cells name the element each flat gold bit belongs to: when they exist they
            # decide the layout (structural evidence); simulation only orders variants without such evidence
            agree = [sum(1 for tk, gk in mp.items() if elem.get(gk) == tk[len(tb):]) for _, mp in scored]
            structural = False
            if max(agree, default=0) > 0:
                j = max(range(len(scored)), key=lambda i: agree[i])
                if scored[j] is not best:
                    log.append(f"alias array: {gb.split('.')[-1]} layout from slang element drivers "
                               f"({agree[j]} of {len(scored[j][1])} bits agree; simulation preferred another, "
                               f"{best[0]} vs {scored[j][0]} mismatches)")
                best = scored[j]
                structural = True
            # Without structural layout evidence a re-key that RAISES the disagreeing compare points is no
            # evidence for any of the guessed layouts (QC slw_hc0 10-26: a_pr 2535 -> 2762, b_emin 2762 -> 3098,
            # every variant a wrong stride): leave the array unpaired for function-based correspondence, which
            # still proves whatever it pairs.  A refused re-key never hides a difference (nothing is assumed).
            if best[0] > base and not structural:
                log.append(f"alias array: gate {tb.split('.')[-1]} ({len(t)} b) -> gold {gb.split('.')[-1]} "
                           f"REFUSED: best of {len(scored)} layouts raises mismatching compare points "
                           f"{base} -> {best[0]} (left to correspondence)")
                continue
            apply(best[1])
            del T[tb]
            log.append(f"alias array: gate {tb.split('.')[-1]} ({len(t)} b) -> gold {gb.split('.')[-1]} "
                       f"({len(g)} b, Q-net alias evidence {n}); mismatching compare points {base} -> {best[0]}")


def merged_proposals(L, log, cap=4096):
    """a gold-only register synthesis MERGED into another register of the same function (opt_merge: the TKM tile's
    X[0..3] and up_out load the same value on every op, so the gate keeps only up_out): neither the names nor a raw
    simulation pair them (each one's hold path reads its own, still unbound, state).  Candidate = a matched gold flop
    whose next-state support equals the gold-only flop's, with each flop's OWN state read as SELF; proposed as an
    'eq' hypothesis and proved inductively with all the others (a wrong proposal is dropped, never assumed)."""
    d, gp = L.gold, L.gp
    I, Lc = d["I"], d["L"]
    base = I + Lc + 1
    ands = d["ands"]
    sym = {}
    for k, lit in gp.items():
        sym[lit >> 1] = k
    memo = {}

    def support(lit):
        v0 = lit >> 1
        if v0 in memo:
            return memo[v0]
        out, seen, st = set(), set(), [v0]
        while st:
            v = st.pop()
            if v in seen or v == 0:
                continue
            seen.add(v)
            if v in sym:
                out.add(sym[v])
            elif v < base:
                out.add(("x", v))
            else:
                i = v - base
                st.append(ands[2 * i] >> 1)
                st.append(ands[2 * i + 1] >> 1)
        memo[v0] = frozenset(out)
        return memo[v0]
    gonly = [k for k in L.gonly if k.startswith("ff:") and ("gold", k) not in L.hyp and k in L.gc][:cap]
    if not gonly:
        return
    fp = {}
    for k in gonly:
        s_ = support(L.gc[k])
        fp.setdefault(frozenset("SELF" if x == k else x for x in s_), []).append(k)
    n = 0
    cands = collections.defaultdict(list)            # gold-only k -> matched registers with its support (in order)
    for c in L.matched:
        if not c.startswith("ff:") or c not in L.gc:
            continue
        s_ = support(L.gc[c])
        ks = fp.get(frozenset("SELF" if x == c else x for x in s_))
        if ks:
            for k in ks:
                if ("gold", k) not in L.hyp:
                    cands[k].append(c)
    # Several matched registers may share one support set: the per-epoch copies e_poolc0 / e_poolc1 both read
    # (b_vk[0], b_epk[0], b_poolm, SELF), and the gold-only e_pool[1] synthesis merged into e_poolc1 was proposed
    # against the first, e_poolc0[0] (QC slw_hc0 10-26: refuted every round, e_pool[1] left free -> 9 POOLc points
    # differ).  Pick, per gold-only register, the first candidate whose next state simulates equal to it with the
    # pair's state bound together (a hold path then reads one value, so only the load condition / data decide);
    # the chosen relation is still proved inductively with all the others, a wrong one is dropped, never assumed.
    choice = {k: cs[0] for k, cs in cands.items()}
    pending = {k: list(cs) for k, cs in cands.items() if len(cs) > 1}
    rounds = 0
    while pending and rounds < 8:
        rounds += 1
        for k, cs in pending.items():
            L.hyp[("gold", k)] = ("eq", "gold", cs[0], 0)
        try:
            m, _ = L.build(with_compare=False, with_hyp=True)
            val, mask = m.simulate(4, seed=4545 + rounds)
            ok = {k for k, cs in pending.items()
                  if lit_val(val, mask, L.dlit[("gold", k)]) == lit_val(val, mask, L.dlit[("gold", cs[0])])}
        finally:
            for k in pending:
                L.hyp.pop(("gold", k), None)
        for k in list(pending):
            if k in ok:
                choice[k] = pending.pop(k)[0]
            else:
                pending[k].pop(0)
                if not pending[k]:
                    del pending[k]                   # none agrees: keep the first (refinement drops it)
    n_dis = sum(1 for k, c in choice.items() if len(cands[k]) > 1 and c != cands[k][0])
    for k, c in choice.items():
        L.hyp[("gold", k)] = ("eq", "gold", c, 0)
        n += 1
    # The chosen copy need not be the one synthesis kept the merged register's loads on: QC slw_hc0 10-26 (QC-LEC-3,
    # CHECKED on the AIGs) paired e_pool[1] with e_poolc1[0], but the gate POOLc next state reads e_poolc1[3]; the
    # four copies are matched registers with their own (self-holding, never reset) state, so the miter left
    # e_poolc1[0] != e_poolc1[3] free and 9 POOLc points differed.  The same-support siblings of the chosen copy are
    # copies of one register (same load condition and data, each holding itself), so propose them equal to it on
    # both sides; like every other hypothesis each is proved by the simultaneous induction and dropped if refuted.
    # Only siblings whose next state simulates equal to the chosen copy's with the pair's state bound are proposed
    # (the other epoch's copy e_poolc0 shares the support but not the load condition).
    chosen = set(choice.values())
    sib = collections.defaultdict(list)          # sibling copy -> chosen copies it may equal (in order)
    for k, c in choice.items():
        for c2 in cands[k]:
            if c2 not in chosen and c2 in L.matched and ("both", c2) not in L.hyp and ("both", c) not in L.hyp \
                    and c not in sib[c2]:
                sib[c2].append(c)
    pending = {c2: list(cs) for c2, cs in sib.items() if cs}
    rounds = 0
    while pending and rounds < 8:
        rounds += 1
        for c2, cs in pending.items():
            L.hyp[("both", c2)] = ("eq", "gold", cs[0], 0)
        m, _ = L.build(with_compare=False, with_hyp=True)
        val, mask = m.simulate(4, seed=4646 + rounds)
        for c2 in list(pending):
            if lit_val(val, mask, L.dlit[("gold", c2)]) == lit_val(val, mask, L.dlit[("gold", pending[c2][0])]):
                del pending[c2]                      # agrees: keep the proposal
            else:
                L.hyp.pop(("both", c2), None)
                pending[c2].pop(0)
                if not pending[c2]:
                    del pending[c2]
    for c2 in pending:                               # undecided after 8 rounds: not proposed
        L.hyp.pop(("both", c2), None)
    n_sib = sum(1 for c2 in sib if ("both", c2) in L.hyp)
    log.append(f"merged proposal: {n} of {len(gonly)} gold-only registers share a matched register's next-state support"
               + (f" ({n_dis} re-chosen among same-support candidates by bound-state simulation)" if n_dis else "")
               + (f"; {n_sib} same-support sibling copies proposed equal to the chosen copy" if n_sib else ""))

def early_whole_compare(L, work, conflicts, log, rnd):
    """Opt-in proof ordering only: a fully proved whole miter can stop alias discovery.

    Every comparison and surviving invariant remains an obligation. The caller
    has just proved the invariant set; check() still runs its ordinary final
    hint/reset/KEEP/comparison path. This is never a cached PASS receipt.
    """
    if os.environ.get("OT_LEC_EARLY_COMPARE") != "1":
        return False
    m, _ = L.build(with_compare=True, with_hyp=True)
    status = prove(m, work, conflicts, log, tag=f"early_compare{rnd}")
    complete = (bool(m.onames) and len(status) == len(m.onames)
                and set(status) == set(m.onames))
    passed = complete and all(status[n] == "proved" for n in m.onames)
    L.early_compare = dict(round=rnd, complete=complete, passed=passed,
                           counts=dict(collections.Counter(status.values())))
    log.append(f"early whole comparison round {rnd}: complete={complete}, proved={passed}; "
               "ordinary final checks remain required")
    return passed


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
    normalize_gold_elements(L, slang_elements(Path(work) / "gold.aliases.json"), log)




    json_alias_keys(L, log, work=work)
    slang_element_keys(L, log, work=work)
    alias_arrays(L, log, work=work)
    relayout(L, log, packed=slang_packed_vectors(Path(work) / "gold.aliases.json"))
    renamed(L, log)
    replica_proposals(L, log)
    merged_proposals(L, log)
    register_alias_proposals(L, log)
    if getattr(L, "preseed_hints", None):
        seed = apply_hints(L, L.preseed_hints, work, conflicts, log, propose_only=True)
        log.append(f"explicit untrusted hints preseeded before discovery: {seed['applied']} applied")
    if getattr(L, "fsm_hints", None):
        seed = apply_hints(L, L.fsm_hints, work, conflicts, log, propose_only=True)
        log.append(f"fsm: explicit untrusted hints seeded before discovery: {seed['applied']} applied")
    fsm_proposals(L, log)
    traces = None                      # sequential traces (seq_traces), computed on first need
    tried = collections.Counter()      # failed attempts per candidate (a pair may fail while a neighbour is wrong)
    # refine-only rounds drop at least one hypothesis each, so they always end; past rounds + 40 they go on
    # while the time budget lasts (s81 hd_tile: false copies along 60-stage skew delay lines peel one stage
    # per round -- stopping at 64 rounds freed every unmatched flop and left 83 points differing)
    t_ref, budget = time.time(), float(os.environ.get("OT_LEC_REFINE_S", "3600"))
    # LEC-FPREG-3 10-27 (SYS_C 4,561 differ): when the budget expires, refinement used to clear EVERY hypothesis
    # (6 false counter constants peeling one bit per SAT round wiped ~5,490 valid relations).  It now finishes
    # monotonically instead: each failing hypothesis is dropped together with every hypothesis whose raw next state
    # (no assumption applied) reads a dropped register, transitively, and the smaller set is proved again.  Dropping
    # only removes assumptions, the loop still returns only on a fully proved (inductive) set, so this is sound;
    # OT_LEC_REFINE_MONOTONE=0 restores the old clear-all.
    expired, sup = False, {}
    seen_proved = collections.Counter()   # proved-set signature -> rounds proved
    early_compare_tried = False
    for rnd in range(rounds + 1000):
        if rnd >= rounds + 40 and time.time() - t_ref > budget:
            if os.environ.get("OT_LEC_REFINE_MONOTONE", "1") == "0":
                break
            if not expired:
                log.append(f"correspondence: refine budget {budget:.0f} s spent at round {rnd}; monotone finish "
                           f"(failures + raw-next-state fanout dropped) with {len(L.hyp)} hypotheses")
            expired = True
        adding = rnd < rounds           # then refine only: drop what fails until the set is inductive
        before = dict(L.hyp)
        if adding:
            for it in range(sim_iters):
                m, kind = L.build(with_compare=False, with_hyp=False)
                val, mask = m.simulate(words, seed=7 * rnd + it + 1)
                sv = lambda side, k: lit_val(val, mask, L.dlit[(side, k)])
                bound = bound_keys(L)
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
                # registers no next-state signature places (re-laid / cross-instance-named delay-line flops, slang
                # vs read_verilog array layouts): pair them by their sequential traces from the zero state
                if not new:
                    if traces is None:
                        traces = seq_traces(L, log)
                    new += trace_proposals(L, traces, tried, log)
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
            # constant 1 from hold / reset (LEC-TOOL-1 10-27): a register that only ever holds or (re)loads 1 --
            # reset value 1 and every load 1, or no reset (X power-up) and every load 1 (synthesis folds it to 1:
            # HBM argmax ti[lv][e] low index bits, hcp_sys1 d0 = last ? nlast : 256) -- has next state 1 once the
            # unpaired registers (itself) are held at 1.  Trying only 0 first made it fail twice and stay free.
            # Candidate only: the induction below proves D == 1 with the reset input free, so a register that
            # resets to 0 or ever loads a non-1 value is refuted.
            m, kind = L.build(with_compare=False, with_hyp=False, free_const=1)
            odl = dict(L.dlit)
            m, kind = L.build(with_compare=False, with_hyp=False)
            for side, keys in (("gold", L.gonly), ("gate", L.tonly)):    # gate-only flops: constant candidates too
                for k in keys:
                    one = odl.get((side, k)) == 1 and zdl.get((side, k)) != 0
                    if k.startswith("ff:") and (side, k) not in L.hyp and k not in partners and \
                            (tried[(side, k, "c")] < 2 or L.dlit.get((side, k), 2) in (0, 1) or
                             ((zdl.get((side, k)) == 0 or one) and tried[(side, k, "c")] < 6)):
                        d = L.dlit.get((side, k))
                        L.hyp[(side, k)] = ("const", d if d in (0, 1) else 1 if one else 0)
            # matched flops whose next state simulates constant on both sides (synthesis may have merged such a
            # flop into another constant one, so the gate's copy is a different, free register)
            m, kind = L.build(with_compare=False, with_hyp=False)
            val, mask = m.simulate(words, seed=999)
            reps = {h[2] for (sd, k), h in L.hyp.items() if sd == "both" and h[0] == "eq"}
            for k in L.matched:
                if not k.startswith("ff:") or ("both", k) in L.hyp or tried[("both", k, "c")] >= 2:
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
            cands = {k for k in L.matched if k.startswith("ff:") and ("both", k) not in L.hyp
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
        if os.environ.get("OT_LEC_SIM_REFINE", "1") != "0":
            sim_refine(L, log, tried, seed=4242 + rnd)
        if not L.hyp:
            if traces is None:
                traces = seq_traces(L, log)
            if os.environ.get("OT_LEC_COPY_CLOSURE", "1") != "0":
                matched_copy_closure(L, log, traces, tried)     # (each pair / register at most once: no loop)
            if os.environ.get("OT_LEC_TRACE_CONST", "1") != "0":
                trace_constant_closure(L, log, tried)
        noreset_filter(L, log, tried, work, conflicts)
        if not L.hyp:
            return
        m, kind = L.build(with_compare=False, with_hyp=True)
        st = prove(m, work, conflicts, log, tag=f"hyp{rnd}")
        bad = [n for n, s in st.items() if s != "proved"]
        (Path(work) / f"hyp{rnd}_failed.txt").write_text("".join(n + "\n" for n in bad))
        log.append(f"correspondence round {rnd}: {len(st)} hypotheses, {len(bad)} failed "
                   f"({sum(st[n] == 'undecided' for n in bad)} undecided) {bad[:6]}")
        if not bad:
            if not early_compare_tried:
                early_compare_tried = True
                if early_whole_compare(L, work, conflicts, log, rnd):
                    return
            # A closure can re-propose a constant rejected by the reset-state check.
            # Only surviving changes need another proof round; otherwise empty
            # rounds repeat until the time budget discards valid correspondence.
            snap = dict(L.hyp)
            # LEC-FPREG-7 10-27 (RXsf: hyp50..hyp1190 byte-identical miters, 0 failed, ~12 s each): a closure's
            # proposal survives the reset-state filter here but is removed again before the next proof (sim_refine /
            # top-of-round filter), so the SAME proved set returns every round until rounds + 1000, where the
            # non-convergence exit cleared every hypothesis.  The set was just proved inductive in full: seeing it
            # proved a third time is a fixpoint, return it as is (sound: only proved sets are ever returned).
            sig = hashlib.sha1(repr(sorted((repr(hk), repr(h)) for hk, h in L.hyp.items())).encode()).hexdigest()
            seen_proved[sig] += 1
            if seen_proved[sig] >= 3:
                log.append(f"correspondence round {rnd}: the same proved set ({len(L.hyp)} hypotheses) recurred "
                           f"{seen_proved[sig]}x with no surviving closure change; fixpoint, returned")
                return

            def surviving_change():
                noreset_filter(L, log, tried, work, conflicts)
                return L.hyp != snap

            if structural_constant_closure(L, log) and surviving_change():
                continue     # prove the new surviving relations before returning
            if structural_twin_closure(L, log) and surviving_change():
                continue     # rejected constants must not starve the twin closure
            if traces is None:
                traces = seq_traces(L, log)
            if os.environ.get("OT_LEC_COPY_CLOSURE", "1") != "0":
                if matched_copy_closure(L, log, traces, tried) and surviving_change():
                    continue
            if os.environ.get("OT_LEC_TRACE_CONST", "1") != "0" and trace_constant_closure(L, log, tried) \
                    and surviving_change():
                continue
            if L.hyp == before or not adding:
                return
            continue
        drop_failed(L, [n for n in bad if n.startswith("cons:")])
        if expired and any(hk not in sup for hk in L.hyp):
            sup.update(raw_support(L, [hk for hk in L.hyp if hk not in sup]))
        gone = set()
        for n in bad:
            if n.startswith("cons:"):
                continue
            _, side, k = n.split(":", 2)
            side = "both" if side == "bothg" else side
            h = L.hyp.pop((side, k), None)
            if h is None:
                continue
            gone.add(k)
            # Equality candidates are looked up with an integer polarity. Keep
            # that key unchanged when recording rejection, or they are retried
            # in every adding round. FSM cube tuples keep their textual key.
            tried[(side, k, "c") if h[0] == "const" else
                  (side, k, h[2], h[3]) if h[0] == "eq" else
                  (side, k, str(h[2]), str(h[3]))] += 1
        if expired and gone:
            n0 = len(L.hyp)
            cascade_drop(L, sup, gone)
            log.append(f"correspondence round {rnd}: monotone finish dropped {n0 - len(L.hyp)} dependent "
                       f"hypotheses, {len(L.hyp)} left")
    L.hyp.clear()                             # refinement did not converge: no assumptions at all
    L.cons.clear()
    log.append("correspondence: refinement did not converge; all unmatched flops free")


def raw_support(L, keys):
    """{(side, key): register keys read by the RAW next state of each hypothesis (and of its 'eq' partner)}, built
    with no hypothesis applied, so a constant's dependence on another hypothesised register stays visible."""
    saved = L.hyp
    L.hyp = {}
    try:
        m, kind = L.build(with_compare=False, with_hyp=False)
        out = {}
        for hk in keys:
            side, k = hk
            h = saved.get(hk)
            lits = [L.dlit.get((sd, k)) for sd in (("gold", "gate") if side == "both" else (side,))]
            if h and h[0] == "eq":
                lits += [L.dlit.get((h[1], h[2])), L.dlit.get(("gold", h[2]))]
            reads = set()
            for lit in lits:
                if lit is not None:
                    reads |= {kind[v][1] for v in m.cone_inputs(lit) if v in kind}
            out[hk] = reads
        return out
    finally:
        L.hyp = saved


def cascade_drop(L, sup, gone):
    """drop, transitively, every hypothesis whose raw next state reads a register in `gone` (its own hypothesis
    was dropped, so that register is free).  Removes assumptions only.  -> keys dropped."""
    gone, out, changed = set(gone), [], True
    while changed:
        changed = False
        for hk in list(L.hyp):
            if sup.get(hk, set()) & gone:
                L.hyp.pop(hk)
                gone.add(hk[1])
                out.append(hk)
                changed = True
    return out


def apply_hints(L, hints, work, conflicts, log, rounds=40, propose_only=False):
    """Untrusted correspondence hints (the commercial 'user match' / 'add mapped points'; PATH-KV-PC4 10-25):
    [[side, key, ['eq', oside, okey, inv] | ['const', c]], ...] for registers the signature search cannot pair
    (rare-event twins such as an opcode bit that only a refresh sets, which random simulation never excites;
    unpacked arrays whose layout differs between the two frontends).  A hint is never a waiver: hints override the
    discovered hypothesis of the same register, then the whole set is proved by the same simultaneous induction as
    every other hypothesis and every failing one is dropped until the set is inductive (a wrong hint only leaves its
    register free; the compare points then fail or stay unproved).  Unnamed latches (no public wire on the Q net)
    become side-only keys ff:__<side>_anon_<var> paired by a unique simulation signature, proved the same way.
    -> dict(given, applied, skipped, anon, dropped, kept)."""
    rec = dict(given=len(hints), applied=0, skipped=[], anon=0, dropped=[], kept=0)
    keys = lambda sd: L.gp if sd in ("gold", "both") else L.tp
    # Loaded-valid qualification (LEC-FPREG-5 10-27): ['gold', key, ['loaded', c, guard]] for an RTL register with
    # no reset that synthesis folded to the constant c it is always loaded with (ot_s81_su_rw k <= k_i == K on the
    # first operand row).  guard = [[[gold key, 0|1], ...], ...] (an OR of cubes over gold registers: the RTL valid /
    # job state under which the register has been loaded).  The register is bound to (guard ? c : its free power-up
    # value), never to c unconditionally (X is not a constant); proved with every other hypothesis: guard on the next
    # state -> D == c and not X; base case: every cube definitely false in the reset state (loaded_base), else the
    # hint is refused.  A read of the register outside the guard sees the free value, so it differs (observed).
    # FSM recoding hints: ['gate', key, ['cube', 'gold', [gold keys], [code bits]]] and the state constraint
    # ['cons', 'gold', [gold keys], [[allowed bits], ...]] (fsm_proposals' forms), proved the same way.
    gk = lambda key: isinstance(key, str) and key.startswith("ff:") and "__" not in key and key in L.gp
    loaded = {e[1] for e in hints if isinstance(e, (list, tuple)) and len(e) == 3 and e[0] == "gold"
              and isinstance(e[2], (list, tuple)) and e[2] and e[2][0] == "loaded"}
    rec["loaded"], rec["loaded_refused"] = [], []
    # Pipeline fill (LEC-FPREG-6 10-27): ['gold', key, ['fill', c, pred]] for an RTL register with no reset on an
    # every-cycle pipeline whose source is the constant c (exp_s x = {1'b1, x[30:0]}: xc5/6/7[31]); synthesis folded
    # it.  It holds X until the constant has ridden down to it.  Bound to (filled ? c : X) with a tool-owned ghost
    # 'filled' bit (filled' = filled(pred); pred None = the chain root, filled' = 1), never to c unconditionally.
    # Proved with the other hypotheses (filled' -> D == c and not X).  Base: the register is not the other constant
    # in the reset state (ghost = 1 where it already is c, else 0 = X, which is its RTL value there).  A read while
    # unfilled is an RTL X (don't care, the tool's X rule); a read after filling is compared against c.
    fills = {}
    for e in hints:
        if isinstance(e, (list, tuple)) and len(e) == 3 and isinstance(e[2], (list, tuple)) and e[2] \
                and e[2][0] == "fill":
            fills[e[1] if isinstance(e[1], str) else repr(e[1])] = e
    rec["fill"], rec["fill_refused"] = [], []
    for e in hints:
        if isinstance(e, (list, tuple)) and len(e) == 3 and isinstance(e[2], (list, tuple)) and e[2] \
                and e[2][0] == "fill":
            try:
                sd, k, (_, c, pred) = e
                ok = (sd == "gold" and k in L.gonly and gk(k) and c in (0, 1) and k not in getattr(L, "unwritten", ())
                      and (pred is None or (pred in fills and pred != k)))
            except (TypeError, ValueError):
                ok = False
            if not ok:
                rec["skipped"].append(e)
                continue
            if not hasattr(L, "rst_val"):
                noreset_classify(L)
            rv = L.rst_val.get(("gold", k), (None, None))[0]
            if rv == 1 - c:
                rec["fill_refused"].append(dict(register=k, why=f"reset-state value {rv} is the other constant"))
                continue
            L.hyp[(sd, k)] = ("fill", c, pred)
            rec["applied"] += 1
            continue
    for e in hints:
        if isinstance(e, (list, tuple)) and len(e) == 3 and isinstance(e[2], (list, tuple)) and e[2] \
                and e[2][0] == "fill":
            continue
        refs = []                                  # other hint forms must not read a fill register (X while unfilled)
        try:
            if e[0] == "cons":
                refs = list(e[2])
            elif e[2][0] == "loaded":
                refs = [x for cube in e[2][2] for x, _ in cube]
            elif e[2][0] == "cube":
                refs = list(e[2][2])
            elif e[2][0] == "eq":
                refs = [e[2][2]]
        except (IndexError, TypeError, KeyError):
            refs = []
        if any(isinstance(x, str) and x in fills for x in refs):
            rec["skipped"].append(e)
            continue
        if isinstance(e, (list, tuple)) and e and e[0] == "cons":
            try:
                _, csd, ck, allowed = e
                ok = (csd == "gold" and ck and all(gk(x) for x in ck) and allowed and
                      all(len(a) == len(ck) and all(b in (0, 1) for b in a) for a in allowed))
            except (ValueError, TypeError):
                ok = False
            if not ok:
                rec["skipped"].append(e)
                continue
            L.cons = [c for c in L.cons if not (c[0] == "gold" and list(c[1]) == list(ck))]
            L.cons.append(("gold", list(ck), [list(a) for a in allowed]))
            rec["applied"] += 1
            continue
        if isinstance(e, (list, tuple)) and len(e) == 3 and isinstance(e[2], (list, tuple)) and e[2] \
                and e[2][0] in ("loaded", "cube"):
            try:
                sd, k, h = e[0], e[1], e[2]
                if h[0] == "loaded":
                    guard = [[(x, int(v)) for x, v in cube] for cube in h[2]]
                    ok = (sd == "gold" and k in L.gonly and gk(k) and h[1] in (0, 1) and guard and
                          all(cube and all(gk(x) and v in (0, 1) and x not in loaded for x, v in cube)
                              for cube in guard))
                    hh = ("loaded", h[1], guard)
                else:
                    ok = (sd == "gate" and k in L.tonly and h[1] == "gold" and h[2] and
                          all(gk(x) for x in h[2]) and len(h[3]) == len(h[2]) and all(b in (0, 1) for b in h[3]))
                    hh = ("cube", "gold", list(h[2]), list(h[3]))
            except (IndexError, TypeError, ValueError):
                ok = False
            if not ok:
                rec["skipped"].append(e)
                continue
            if hh[0] == "loaded":
                cube = loaded_base(L, hh[2])
                if cube is not None:
                    rec["loaded_refused"].append(dict(register=k, cube=[list(x) for x in cube],
                                                      why="guard cube not refuted in the reset state"))
                    continue
            L.hyp[(sd, k)] = hh
            rec["applied"] += 1
            continue
        try:
            sd, k, h = e[0], e[1], tuple(e[2])
            ok = (sd in ("gold", "gate", "both") and k.startswith("ff:") and "__" not in k and k in keys(sd)
                  and (sd != "both" or k in L.matched) and
                  ((h[0] == "const" and h[1] in (0, 1)) or
                   (h[0] == "eq" and h[1] in ("gold", "gate") and h[3] in (0, 1) and "__" not in h[2]
                    and h[2] in keys(h[1]))))
        except (IndexError, TypeError, AttributeError):
            ok = False
        if not ok:
            rec["skipped"].append(e)
            continue
        if h[0] == "eq" and k in L.matched and h[1] == "gold" and h[2] in L.gonly:
            sd, k, h = "gold", h[2], ("eq", "gold", k, h[3])     # a gold-only twin points at the matched register
        L.hyp[(sd, k)] = h
        rec["applied"] += 1
    if propose_only:
        # Seed explicit state metadata before discovery, exactly like fsm_proposals.
        # correspond() still proves/drops every cube and state constraint below.
        return rec
    anon = []
    for side in ("gold", "gate"):
        points, compare, only = (L.gp, L.gc, L.gonly) if side == "gold" else (L.tp, L.tc, L.tonly)
        for lit, nxt in (L.ganon if side == "gold" else L.tanon):
            k = f"ff:__{side}_anon_{lit >> 1}"
            points[k], compare[k] = lit, nxt
            only.append(k)
            anon.append((side, k))
    L.ganon, L.tanon = [], []
    if anon:
        m, _ = L.build(with_compare=False, with_hyp=False)
        val, mask = m.simulate(32, seed=20261025)
        sv = lambda sd, k: lit_val(val, mask, L.dlit[(sd, k)])
        sigs = collections.defaultdict(set)
        for sd, ks in (("gold", L.gp), ("gate", L.tp)):
            for c in ks:
                if c.startswith("ff:") and (sd, c) not in L.hyp and "__" not in c:
                    s = sv(sd, c)
                    sigs[s].add((sd if c not in L.matched else "gold", c, 0))
                    sigs[s ^ mask].add((sd if c not in L.matched else "gold", c, 1))
        for side, k in anon:
            s = sv(side, k)
            hits = sigs.get(s, set())
            if s not in (0, mask) and len(hits) == 1:
                osd, c, inv = next(iter(hits))
                L.hyp[(side, k)] = ("eq", osd, c, inv)
                rec["anon"] += 1
    for rnd in range(rounds):
        noreset_filter(L, log, collections.Counter(), work, conflicts)
        m, _ = L.build(with_compare=False, with_hyp=True)
        st = prove(m, work, conflicts, log, tag=f"hint{rnd}")
        bad = [n for n, s in st.items() if s != "proved"]
        log.append(f"hint refinement round {rnd}: {len(st)} hypotheses, {len(bad)} failed {bad[:6]}")
        if not bad:
            rec["kept"] = len(L.hyp)
            rec["loaded"] = [dict(register=k, value=h[1], guard=[[list(x) for x in c] for c in h[2]], base="reset")
                             for (sd, k), h in sorted(L.hyp.items()) if h[0] == "loaded"]
            rec["fill"] = [dict(register=k, value=h[1], pred=h[2],
                                base_filled=L.rst_val.get(("gold", k), (None, None))[0] == h[1])
                           for (sd, k), h in sorted(L.hyp.items()) if h[0] == "fill"]
            return rec
        drop_failed(L, [n for n in bad if n.startswith("cons:")])
        rec["dropped"] += [n for n in bad if n.startswith("cons:")]
        for n in bad:
            if n.startswith("cons:"):
                continue
            _, side, k = n.split(":", 2)
            if L.hyp.pop(("both" if side == "bothg" else side, k), None) is not None:
                rec["dropped"].append(k)
    L.hyp.clear()
    L.cons.clear()
    rec["kept"] = 0
    log.append("hint refinement did not converge; all unmatched flops free")
    return rec


SIBLING_IDX = re.compile(r"\[(\d+)\]")


def replica_siblings(key, keys):
    """same-bit copies of a generated register: names equal to `key` except one index that is not the trailing (bit)
    index -- the copy / group index (g_off[0].r_part[150] vs g_off[3].r_part[150], c_p[1][11] vs c_p[2][11]).
    Name-only candidate discovery; every pairing it feeds is still proved.  -> sorted keys (key excluded)."""
    ix = list(SIBLING_IDX.finditer(key))
    if ix and ix[-1].end() == len(key):
        ix = ix[:-1]                              # the bit index of a vector register stays fixed
    out = set()
    for m in ix:
        pat = re.compile(re.escape(key[:m.start()]) + r"\[\d+\]" + re.escape(key[m.end():]) + r"$")
        out |= {k for k in keys if k != key and pat.match(k)}
    return sorted(out)


def transfer_profile(L, profile, log):
    """Re-derive a correspondence profile (hyp.json [[side, key, hint], ...]) saved by an EARLIER gate on THIS
    gate's matched / gold-only / gate-only roles (QC NL fresh gate 10-29).  Synthesis keeps an arbitrary copy of a
    duplicated register; a fresh netlist may keep a different one (gate kept c_p[2][11], the old one c_p[1][11]).
    The names all still exist, so a name-only restore keeps the old gold-side hint ('gold', c_p[2][11]) == c_p[1][11]
    on a register that is now MATCHED and leaves the old representative c_p[1][11] gold-only with no hint: a free
    input, so its relation fails and every hint / compare point reading it fails with it (57 + 105 differences).
    Here each hint is re-sided on the fresh roles:
      * key or partner absent                         -> dropped (reported)
      * gold hint on a now-matched key, eq a now-gold-only partner P
                                                      -> swapped: P == key (same polarity), P re-anchored
      * gold const on a now-matched key               -> both-side const
      * both-side hint on a now gold-/gate-only key   -> that side
      * any other hint on a key of the wrong role     -> dropped (reported)
    then every gold eq hint whose partner is gold-only with no hint of its own (an orphan representative) gets that
    partner re-anchored to a MATCHED same-bit sibling of its replica group (replica_siblings).  Nothing here is
    assumed: the caller proves the whole set jointly (prove_profile); a failing hint is dropped and reported, so a
    wrong sibling or polarity only leaves a register free, never a waiver.  Replaces L.hyp.
    -> dict(given, kept, swapped, resided, reanchored, ambiguous, dropped)."""
    ms = set(L.matched)
    side_keys = {"gold": L.gp, "gate": L.tp}
    role = lambda k: "both" if k in ms else "gold" if k in L.gp else "gate" if k in L.tp else None
    rec = dict(given=len(profile), kept=0, swapped=[], resided=[], reanchored=[], ambiguous=[], dropped=[])
    L.hyp.clear()
    late = []
    for e in profile:
        sd, k, h = e[0], e[1], tuple(e[2])
        r = role(k)
        partner_ok = h[0] != "eq" or h[2] in side_keys.get(h[1], ())
        if r is None or not partner_ok:
            rec["dropped"].append(dict(hint=[sd, k, list(h)], why="key or partner absent in this gate"))
            continue
        if sd == r:
            L.hyp[sd, k] = h
            continue
        if sd == "gold" and r == "both" and h[0] == "eq" and h[1] == "gold" and role(h[2]) == "gold":
            late.append(("swap", e, ("gold", h[2]), ("eq", "gold", k, h[3])))
        elif sd in ("gold", "gate") and r == "both" and h[0] == "const":
            late.append(("reside", e, ("both", k), h))
        elif sd == "both" and r in ("gold", "gate") and h[0] in ("const", "eq") \
                and (h[0] == "const" or h[1] == "gold" or r == "gate"):
            late.append(("reside", e, (r, k), h))
        else:
            rec["dropped"].append(dict(hint=[sd, k, list(h)], why=f"stale side {sd}: key is {r} in this gate"))
    for how, e, hk, h in late:                    # a hint native to this gate's roles wins over a re-sided one
        if hk in L.hyp:
            rec["dropped"].append(dict(hint=list(e), why=f"{how}: {hk[0]}:{hk[1]} already has a hint"))
            continue
        L.hyp[hk] = h
        rec["swapped" if how == "swap" else "resided"].append(dict(old=list(e), new=[hk[0], hk[1], list(h)]))
    orphans = sorted({h[2] for (sd, k), h in L.hyp.items() if sd == "gold" and h[0] == "eq" and h[1] == "gold"
                      and role(h[2]) == "gold" and ("gold", h[2]) not in L.hyp})
    for p in orphans:
        cands = replica_siblings(p, ms)
        if not cands:
            continue
        if len(cands) > 1:
            rec["ambiguous"].append(dict(register=p, candidates=cands))
        L.hyp["gold", p] = ("eq", "gold", cands[0], 0)
        rec["reanchored"].append(dict(register=p, to=cands[0]))
    rec["kept"] = len(L.hyp)
    log.append(f"profile transfer: {rec['kept']} of {rec['given']} hints; {len(rec['swapped'])} swapped to the "
               f"surviving replica, {len(rec['resided'])} re-sided, {len(rec['reanchored'])} orphan representatives "
               f"re-anchored ({len(rec['ambiguous'])} ambiguous), {len(rec['dropped'])} dropped")
    return rec


def prove_profile(L, work, conflicts, log, rounds=32, single_cap=100):
    """prove every hypothesis jointly (one simultaneous induction); drop each failing one and repeat until the set
    is inductive.  -> dict(rounds, dropped=[output names], status={output: verdict} of the final round)."""
    dropped = []
    for it in range(rounds):
        m, _ = L.build(with_compare=False, with_hyp=True)
        st = prove(m, work, conflicts, log, tag=f"profile{it}", single_cap=single_cap)
        bad = [n for n, s in st.items() if s != "proved"]
        log.append(f"profile joint round {it}: {len(st)} hypotheses, {len(bad)} failed {bad[:6]}")
        if not bad:
            return dict(rounds=it + 1, dropped=dropped, status=st)
        dropped += bad
        drop_failed(L, bad)
    raise LecError("profile joint proof did not converge")


# ---------------------------------------------------------------------------------------------- driver
def run_gold(env, kit, gold_fe, lib_bbs, out, log, rec):
    """gold AIG.  An unpacked array that memory_map cannot convert (write ports on several clocks, e.g. a
    per-tap clocked delay line r[p] <= r[p+1] on clk[(p-1)/48], ot_hbm_su_static_ins) stays a $mem_v2 cell and the
    AIGER backend rejects it; synthesis (read_verilog) turned the same array into named registers (mem2reg), so the
    gold is re-read with read_slang --no-implicit-memories: every array becomes its registers, as written."""
    args = (env, kit, gold_fe, lib_bbs, out / "stubs.v", out / "wrap_gold.v", out / "lecff.v", out / "gold")
    # Opt-in for register arrays whose implicit-memory lowering hides element
    # driver metadata at gold.aliases.json (N59 qe_rep, QC HC e_W). The same
    # frontend option already serves the unmappable-memory fallback below.
    # This preserves individual logical register elements before memory_map;
    # every next-state and output compare still passes normal induction.
    no_mem = gold_fe == "slang" and str(env.get("OT_LEC_GOLD_NO_IMPLICIT_MEMORIES", "0")) == "1"
    if no_mem:
        rec["gold_no_implicit_memories"] = True
    try:
        return run_side(env, gold_script(*args, slang_extra=["--no-implicit-memories"] if no_mem else ()), out,
                        "gold", log, rec)
    except Unproven as e:
        if no_mem or gold_fe != "slang" or "Unsupported cell type: $mem_v2" not in str(e):
            raise
        log.append(f"gold: unmappable memory ({str(e)[-160:]}); re-reading with read_slang --no-implicit-memories")
        rec["gold_no_implicit_memories"] = True
        return run_side(env, gold_script(*args, slang_extra=["--no-implicit-memories"]), out, "gold", log, rec)


def run_side(env, script, out, side, log, rec):
    """one side's AIG: one yosys run, or with clock gates phase A -> icg_to_enable -> phase B."""
    try:
        r = run_yosys(script, out / f"{side}.ys", log)
    except Unproven as e:
        if RENAME_ASSERT not in str(e):
            raise
        raise Unproven(rename_collision_reason(script, out, side, log, rec, str(e))) from None
    if not split_seq(env):
        return r
    pre = out / f"{side}"
    rec.setdefault("clock_gates", {})[side] = icg_to_enable(f"{pre}.preicg.json", f"{pre}.icg.json", side)
    if env.get("_LEC_LATCH"):
        rec.setdefault("lockup_latches", {})[side] = latch_to_wire(f"{pre}.icg.json", f"{pre}.icg.json", side)
    r = run_yosys(seq_tail_b(pre, out / "lecff.v"), out / f"{side}_b.ys", log)
    for f in (f"{pre}.preicg.json", f"{pre}.icg.json"):
        Path(f).unlink(missing_ok=True)
    return r


# `rename -wire` names each private flop after the register bit it drives; two flops driving ONE wire bit get the
# same name and yosys aborts (rtlil.cc rename assert) instead of reporting it. HEAD-KITS-9 10-29, hd_ctl gold: a
# static (non-automatic) function `isnan` called from a clocked and a combinational process; read_slang lowers its
# argument to one module variable `isnan.x` that a register of each call site drives (multi-driven gold).
RENAME_ASSERT = "count_id(cell->name) == 0"
MULTI_DRV = re.compile(r"^Warning: multiple conflicting drivers for (\S+?)\.\\?(\S+?)(?: \[(\d+)\])?:\s*$")
MULTI_DRV_PORT = re.compile(r"^\s+port (\S+) of cell (\S+) \((\S+)\)\s*$")


def multi_driven_bits(text):
    """yosys `check` log -> {wire bit: [(cell, type), ...]} for every bit with several drivers."""
    out, cur = {}, None
    for line in text.splitlines():
        m = MULTI_DRV.match(line)
        if m:
            cur = m.group(2) + (f"[{m.group(3)}]" if m.group(3) is not None else "")
            out[cur] = []
            continue
        m = MULTI_DRV_PORT.match(line) if cur is not None else None
        if m:
            out[cur].append((m.group(2), m.group(3)))
        else:
            cur = None
    return out


def rename_collision_reason(script, out, side, log, rec, err):
    """re-run the side's script up to the flop rename with `check` (log only) and name the multi-driven register
    bits that made `rename -wire` collide; the verdict stays UNPROVEN (a multi-driven RTL register has no single
    reference value: write_aiger would keep an arbitrary driver)."""
    lines = script.splitlines()
    cut = next((i for i, l in enumerate(lines) if l.startswith("rename -wire")), None)
    if cut is None:
        return err
    try:
        run_yosys("\n".join(lines[:cut] + ["check"]) + "\n", out / f"{side}_mdrv.ys", log)
        bits = multi_driven_bits(Path(str(out / f"{side}_mdrv.ys") + ".log").read_text(errors="replace"))
    except Unproven as e:
        return f"{err} (multi-driver diagnosis failed: {str(e)[-200:]})"
    ff = {b: d for b, d in bits.items() if sum(1 for _, t in d if FF_TYPE.match(t)) >= 2}
    rec.setdefault("multi_driven_registers", {})[side] = {"n": len(ff), "first": sorted(ff)[:20]}
    if not ff:
        return f"{err} (no multi-driven register bit found by check; {len(bits)} multi-driven bits)"
    scopes = sorted({b.rsplit(".", 1)[0] for b in ff if "." in b})
    return (f"{side}: {len(ff)} register bits are driven by two or more flops, so `rename -wire` gives them one "
            f"name (yosys assert {RENAME_ASSERT!r}): {', '.join(sorted(ff)[:6])}; a static function/task variable "
            f"written from several processes lowers this way (scopes: {', '.join(scopes[:6])}) -> declare the "
            f"function `automatic` in the RTL")


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


def superset_report(L, m, kind, verdict):
    """COORD RULING HBM-CORE-LAT-R4 (3) / R5 collar: the per-run list of the gate-only extra bits that
    OT_LEC_SUPERSET_VEC=1 re-keyed, each with the reason it cannot change a compare point.

    binding  free   the bit is a free input of the miter (no hypothesis): an EQUIVALENT miter proves no compare
                    point (outputs, matched next states, black-box pins) depends on it, i.e. it is unobservable;
             const / eq / cube   the bit is bound by a register-correspondence hypothesis that the same induction
                    proved (the bit equals a constant / a matched register): it carries no independent value;
             rekeyed / not built   a later pass renamed the key or no miter exists: NOT shown (fail closed).
    observers  compare / hypothesis outputs whose AIG cone structurally contains the free bit (0 = no fan-out to
               any compare point at all; > 0 = fan-out that the proof showed is functionally masked).
    -> dict(enabled, n_extra, all_shown, extra_bits=[...], basis)"""
    ex = list(getattr(L, "superset_extra", []) or [])
    free = {k: v for v, (kd, k) in kind.items() if kd == "gate_only"}
    bit_of = {}
    for i, (b, k) in enumerate(ex):
        if k in free:
            bit_of[free[k]] = i
    # one forward pass: bitmask of the free extra bits each AIG node depends on (only nodes that depend on one)
    dep = {v: 1 << i for v, i in bit_of.items()}
    if dep:
        ands, base = m.ands, m.ni + 1
        for k in range(len(ands) // 2):
            a, b = dep.get(ands[2 * k] >> 1, 0), dep.get(ands[2 * k + 1] >> 1, 0)
            if a or b:
                dep[base + k] = a | b
    obs = collections.defaultdict(list)
    for o, n in zip(m.outs, m.onames):
        d = dep.get(o >> 1, 0)
        while d:
            low = d & -d
            obs[low.bit_length() - 1].append(n)
            d ^= low
    rows, eq = [], verdict == "EQUIVALENT"
    for i, (b, k) in enumerate(ex):
        if k in free:
            binding = "free"
        elif k in L.tp and ("gate", k) in L.hyp:
            binding = L.hyp[("gate", k)][0]
        elif k in L.tp:
            binding = "bound"
        else:
            binding = "rekeyed"
        ok = eq and binding in ("free", "const", "eq", "cube")
        rows.append(dict(bit=b, key=k, binding=binding, observers=len(obs.get(i, ())),
                         first_observers=obs.get(i, [])[:4], shown=ok))
    return dict(enabled=True, n_extra=len(rows), all_shown=all(r["shown"] for r in rows), extra_bits=rows,
                basis=("free bits: free inputs of the proved miter (unobservable); const/eq/cube bits: bound by "
                       "inductively proved correspondence hypotheses; shown only when the verdict is EQUIVALENT"))


def ft_parallel_normalise(kit, top, netlist, out, rec):
    """KV-CORES-PV2 10-27 (12.2a1 island ft arcs, kit island_ft.json): an arc with n > 1 parallel drivers (island
    mesh_driver) is one logical driver in RTL -- driver j >= 1 drives its own net <sink>__p<j> -- and a physical short in
    the placed/routed ODB (ot_ft_short).  Parallel identical buffers on one input are one driver functionally, so the gate
    netlist's short is mapped back to the RTL form (Y of driver j -> <sink>__p<j>) before the AIG build; fail-closed: every
    declared driver must be found with Y on <sink> or <sink>__p<j>.  No island_ft.json or no parallel arc -> unchanged."""
    fj = Path(kit) / "island_ft.json"
    if not fj.is_file():
        return netlist
    par = [(a["sink"], j, c["name"]) for a in json.loads(fj.read_text())["arcs"]
           for j, c in enumerate(a["cells"]) if j]
    if not par:
        return netlist
    op = gzip.open if str(netlist).endswith(".gz") else open
    with op(netlist, "rt", errors="replace") as f:
        t = f.read()
    m = re.search(r"^module\s+\\?" + re.escape(top) + r"\s*\(.*?\);", t, re.M | re.S)
    if not m:
        raise Unproven(f"ft_parallel: module {top} not found in {netlist}")
    wires, done = [], []
    for sink, j, name in par:
        cm = re.compile(r"(^\s*\S+\s+\\?" + re.escape(name) + r"\s*\((?:[^;])*?\.Y\s*\(\s*)\\?([^\s()]+)(\s*\))", re.M | re.S)
        hits = cm.findall(t)
        if len(hits) != 1:
            raise Unproven(f"ft_parallel: driver {name} found {len(hits)} times")
        net = hits[0][1]
        pn = f"{sink}__p{j}"
        if net == sink:
            t = cm.sub(lambda q: q[1] + pn + q[3], t)
            wires.append(pn)
        elif net != pn:
            raise Unproven(f"ft_parallel: driver {name} Y on {net}, not {sink} / {pn}")
        done.append(name)
    if wires:
        m = re.search(r"^module\s+\\?" + re.escape(top) + r"\s*\(.*?\);", t, re.M | re.S)
        t = t[:m.end()] + "".join(f"\n  wire {w};" for w in wires) + t[m.end():]
    rec["ft_parallel"] = dict(drivers=done, remapped=wires, source=str(netlist))
    dst = Path(out) / "gate_ft_parallel.v"
    dst.write_text(t)
    return str(dst)


RESET_DEFAULT = 4
DEBUG_ENV = ("OT_LEC_RAW_BASE_STEPS",)


def reset_contract_gate(kit, top, environ=None):
    """The reset window of the no-reset constant base cases (OT_LEC_RESET_CYCLES) beyond the default 4 edges is a
    DECLARED die reset length (COORD 10-27): used only when KIT/reset_contract.json (or OT_LEC_RESET_CONTRACT)
    records an RTL proof that the die's reset generator holds reset for that many clocked edges, with a caught
    mutant control and a receipt file whose sha256 matches, and lists this core.  Otherwise it fails CLOSED to the
    default (a larger request is recorded and refused).  Schema opentallas.reset_contract.v1:
      {die, edges, modules: [core top, ...], proof: {verdict: PASS, assert_edges, mutant: CAUGHT,
       receipt: path relative to the contract, receipt_sha256}}
    Sets environ[OT_LEC_RESET_CYCLES] to the length used. -> report dict."""
    environ = os.environ if environ is None else environ
    req = environ.get("OT_LEC_RESET_CYCLES")
    path = environ.get("OT_LEC_RESET_CONTRACT") or str(Path(kit) / "reset_contract.json")
    # OT_LEC_RAW_BASE_STEPS is a DEBUG override only (COORD REBAL-7 ruling 10-28): the release reset window is the
    # declared contract above; any debug override in effect is recorded beside it in lec.json
    rep = dict(default=RESET_DEFAULT, requested=int(req) if req else None, contract=None, used=RESET_DEFAULT,
               debug_overrides={k: environ[k] for k in DEBUG_ENV if k in environ})

    def refuse(why):
        rep["refused"] = why
        environ["OT_LEC_RESET_CYCLES"] = str(RESET_DEFAULT)
        return rep
    if not Path(path).is_file():
        if req and int(req) > RESET_DEFAULT:
            return refuse("no reset contract: a reset window above the default needs a proven die reset length")
        if req:
            rep["used"] = int(req)         # a SHORTER window only removes base cases: always sound
        environ["OT_LEC_RESET_CYCLES"] = str(rep["used"])
        return rep
    try:
        c = json.loads(Path(path).read_text())
        pr = c["proof"]
        rcpt = (Path(path).parent / pr["receipt"]).resolve()
        rep["contract"] = dict(file=str(path), die=c.get("die"), edges=int(c["edges"]),
                               assert_edges=int(pr["assert_edges"]), receipt=str(rcpt))
        if c.get("schema") != "opentallas.reset_contract.v1":
            return refuse("reset contract schema")
        if pr.get("verdict") != "PASS" or pr.get("mutant") != "CAUGHT":
            return refuse("reset contract proof not PASS with a CAUGHT mutant control")
        if top not in c.get("modules", []):
            return refuse(f"reset contract does not list {top}")
        if not rcpt.is_file() or hashlib.sha256(rcpt.read_bytes()).hexdigest() != pr.get("receipt_sha256"):
            return refuse("reset contract receipt missing or sha256 mismatch")
        proven = min(int(c["edges"]), int(pr["assert_edges"]))
    except (OSError, ValueError, KeyError, TypeError) as e:
        return refuse(f"reset contract unreadable: {e}")
    want = int(req) if req else proven
    if want > proven:
        return refuse(f"requested {want} edges > proven {proven}")
    rep["used"] = max(want, 1)
    environ["OT_LEC_RESET_CYCLES"] = str(rep["used"])
    return rep


def check(kit, netlist=None, out=None, gold_frontend=None, conflicts=1000, port_map=None, reuse=False, hints=None):
    kit = str(Path(kit).resolve())
    out = Path(out or Path(kit) / "lec")
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rec = dict(schema=SCHEMA, kit=kit, generated=time.strftime("%Y-%m-%dT%H:%M:%S%z"), verdict="UNPROVEN")
    log = []
    try:
        env = parse_config(kit)
        top = env["DESIGN_NAME"]
        rec["reset_contract"] = reset_contract_gate(kit, top)
        netlist = netlist or find_netlist(kit)
        gate_fe = env.get("SYNTH_HDL_FRONTEND", "") or "verilog"
        gold_fe = gold_frontend or ("verilog" if gate_fe == "slang" else "slang")
        rec.update(top=top, netlist=netlist, synth_frontend=gate_fe, gold_frontend=gold_fe)
        if gold_fe == gate_fe:
            rec["warning"] = "gold frontend == synthesis frontend (frontend bugs are not independent)"
        netlist = ft_parallel_normalise(kit, top, netlist, out, rec)
        types = netlist_cell_types(netlist)
        latch_ok = os.environ.get("OT_LEC_LATCH", "1") != "0"
        bad = sorted(c for c in types if UNSUPPORTED_CELLS.match(c) and not ICG_CELLS.match(c)
                     and not (latch_ok and LOCKUP_CELLS.match(c)))
        if any(LOCKUP_CELLS.match(c) for c in types):
            env["_LEC_LATCH"] = "1"
            rec["lockup_latch_cells"] = sorted(c for c in types if LOCKUP_CELLS.match(c))
        if bad:
            raise Unproven(f"netlist holds cells LEC does not model: {bad[:8]}")
        srcmods, rtl_cells = set(), set()
        for f in env["VERILOG_FILES"].split():
            srcmods |= set(src_modules(kpath(kit, f)))
            try:
                rtl_cells |= set(re.findall(r"\bICG\w+_ASAP7_75t_[RLS]+\b", Path(kpath(kit, f)).read_text(errors="replace")))
            except OSError:
                pass
        icg = sorted({c for c in types if ICG_CELLS.match(c)} | (rtl_cells - srcmods))
        if any(not ICG_CELLS.match(c) for c in icg):
            raise Unproven(f"RTL instantiates clock-gate cells LEC does not model: {icg[:8]}")
        if icg:                           # clock-gate -> enable abstraction on both sides (icg_to_enable)
            (out / "icg_bb.v").write_text(icg_verilog(icg))
            env["_LEC_ICG_V"] = str(out / "icg_bb.v")
            gicg = sorted((rtl_cells - srcmods) & set(icg))
            if gicg:
                (out / "icg_gold_bb.v").write_text(icg_verilog(gicg))
                env["_LEC_ICG_GOLD_V"] = str(out / "icg_gold_bb.v")
            rec["clock_gate_cells"] = icg
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
        bbports = {k: v for k, v in bbports.items() if not k.startswith("$abstract") and not ICG_CELLS.match(k)}
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
                fg = ex.submit(run_gold, env, kit, gold_fe, lib_bbs, out, log, rec)
                ft = ex.submit(run_side, env, gate_script(env, netlist, out / "stubs.v", out / "wrap_gate.v",
                                                          out / "lecff.v", out / "gate"), out, "gate", log, rec)
                fg.result()
                ft.result()
        rec["t_aig_s"] = round(time.time() - t1, 1)
        # 3. key points, register correspondence, miter
        t1 = time.time()
        L = Lec(read_aig(out / "gold.aig"), read_map(out / "gold.map"),
                read_aig(out / "gate.aig"), read_map(out / "gate.map"), port_map)
        L.kit_reset_ports = kit_reset_ports(kit)
        rec["kit_reset_ports"] = L.kit_reset_ports
        hf = Path(hints) if hints else Path(kit) / "lec_hints.json"
        if hf.is_file():
            supplied = json.loads(hf.read_text())
            if os.environ.get("OT_LEC_HINTS_PRESEED") == "1":
                L.preseed_hints = supplied
                rec["hints_preseed_enabled"] = True
            L.fsm_hints = [e for e in supplied if isinstance(e, (list, tuple)) and e and
                           (e[0] == "cons" or (len(e) == 3 and isinstance(e[2], (list, tuple)) and
                                               e[2] and e[2][0] == "cube"))]
        correspond(L, out, conflicts, log)
        if hasattr(L, "early_compare"):
            rec["early_compare"] = L.early_compare
        if hf.is_file():
            import hashlib
            rec["hints"] = dict(file=str(hf), sha256=hashlib.sha256(hf.read_bytes()).hexdigest())
            rec["hints"].update(apply_hints(L, json.loads(hf.read_text()), out, conflicts, log))
            rec["hints"]["skipped"] = len(rec["hints"]["skipped"])
            rec["hints"]["dropped"] = dict(n=len(rec["hints"]["dropped"]), first=rec["hints"]["dropped"][:40])
        elif hints:
            raise LecError(f"hints file {hints} not found")
        noreset_filter(L, log, collections.Counter(), out, conflicts)
        rec["noreset_constants"] = noreset_report(L)
        rec["noreset_constants"]["listing"] = noreset_listing(L, out / "noreset_constants.tsv")
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
            gold_x_sources=len(L.gx), gold_unwritten_x=lst(getattr(L, "unwritten", [])), gate_x_sources=len(L.tx),
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
            e = dict(point=n, status=st, cone_unmatched=kinds, cone_unmatched_keys=keys,
                     cone_support_count=len(ins),
                     cone_state_keys=sorted({f"{kind[v][0]}:{kind[v][1]}" for v in ins})[:64])
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
            kdead = getattr(L, "kept_unobservable", [])
            rec["kept_registers"] = dict(declared=len(kdecl), in_netlist=len(kdecl) - len(kmiss) - len(kconst) - len(kdead),
                                         constant_proved=lst(kconst), missing=lst(kmiss),
                                         unobservable_removed=lst(kdead),
                                         unobservable_reason="no compare point (output / black-box input) observes "
                                                             "it in the gold AIG: dead logic, removal is not a merge" if kdead else None)
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
        if os.environ.get("OT_LEC_SUPERSET_VEC") == "1":
            rec["superset_vec"] = superset_report(L, m, kind, rec["verdict"])
            if rec["verdict"] == "EQUIVALENT" and not rec["superset_vec"]["all_shown"]:
                bad = [e["bit"] for e in rec["superset_vec"]["extra_bits"] if not e["shown"]]
                rec["verdict"] = "UNPROVEN"
                rec["reason"] = (f"OT_LEC_SUPERSET_VEC: {len(bad)} extra gate bit(s) not shown unobservable "
                                 f"(first: " + ", ".join(bad[:6]) + ")")
    except LintFail:
        pass
    except Unproven as e:
        rec["verdict"], rec["reason"] = "UNPROVEN", str(e)
    except (LecError, OSError, subprocess.SubprocessError, ValueError, KeyError) as e:
        rec["verdict"], rec["reason"] = "ERROR", f"{type(e).__name__}: {e}"
        import traceback
        log.append(traceback.format_exc())
    lc = locals().get("L")
    if lc is not None and getattr(lc, "cycle_dropped", None):   # hypotheses dropped to break binding cycles
        rec["cycle_dropped"] = dict(n=len(lc.cycle_dropped),
                                    first=[f"{sd}:{k} {list(h)}" for (sd, k), h in lc.cycle_dropped[:40]])
    if os.environ.get("OT_LEC_SUPERSET_VEC") == "1" and "superset_vec" not in rec:   # the check did not finish
        ex = list(getattr(lc, "superset_extra", []) or []) if lc is not None else []
        rec["superset_vec"] = dict(enabled=True, n_extra=len(ex), all_shown=False,
                                   extra_bits=[dict(bit=b, key=k, binding="not built", observers=None, shown=False)
                                               for b, k in ex],
                                   basis=f"not shown: verdict {rec.get('verdict')} before the miter was proved")
    rec["t_total_s"] = round(time.time() - t0, 1)
    rec["provenance"] = _provenance(kit)
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
           "-v", f"{out}:/lecout", "-v", f"{me}:/lec.py:ro", "-e", f"HUID={os.getuid()}", "-e", f"HGID={os.getgid()}", "-e", f"OT_LEC_REFINE_S={os.environ.get('OT_LEC_REFINE_S', '3600')}"]
    # optional XOR-aware SAT backend: OT_LEC_SOLVER = a host dir holding pycryptosat for the image's python (cp310)
    if os.environ.get("OT_LEC_SUPERSET_VEC") == "1":
        cmd += ["-e", "OT_LEC_SUPERSET_VEC=1"]
    if os.environ.get("OT_LEC_HINTS_PRESEED") == "1":
        cmd += ["-e", "OT_LEC_HINTS_PRESEED=1"]
    if os.environ.get("OT_LEC_EARLY_COMPARE") == "1":
        cmd += ["-e", "OT_LEC_EARLY_COMPARE=1"]
    if "OT_LEC_RAW_BASE_STEPS" in os.environ:
        cmd += ["-e", f"OT_LEC_RAW_BASE_STEPS={os.environ['OT_LEC_RAW_BASE_STEPS']}"]
    for k in ("OT_LEC_LATCH", "OT_LEC_RESET_CYCLES"):      # model switches (the reset contract is KIT/reset_contract.json)
        if os.environ.get(k):
            cmd += ["-e", f"{k}={os.environ[k]}"]
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
    if args.hints:
        shutil.copyfile(args.hints, Path(out) / "hints.json")
        inner += ["--hints", "/lecout/hints.json"]
    if args.port_map:
        shutil.copyfile(args.port_map, Path(out) / "port_map.json")
        inner += ["--port-map", "/lecout/port_map.json"]
    sh = " ".join(shlex.quote(x) for x in inner) + "; rc=$?; chown -R $HUID:$HGID /lecout; exit $rc"
    return subprocess.run(cmd + [sh]).returncode


def _repo_provenance(repo=None):
    """Existing repository provider; standalone kits may not ship its module."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import manifest_paths
        return manifest_paths.provenance(repo) if repo is not None else manifest_paths.provenance()
    except Exception as e:
        return dict(commit=None, dirty=None, source=f"error: {type(e).__name__}")


def _kit_input_identity(kit):
    kit = Path(kit).resolve()
    required = ["config.mk", "freeze.json", "lec.py"]
    paths = [kit / name for name in required]
    paths += [kit / name for name in ("core.json", "pins.json", "straps.json") if (kit / name).is_file()]
    rtl = sorted(p for p in (kit / "rtl").rglob("*") if p.is_file())
    if not rtl:
        raise ValueError("kit has no staged RTL inputs")
    paths += rtl
    result = {}
    for p in paths:
        p.resolve().relative_to(kit)  # no source outside the staged kit
        result[p.relative_to(kit).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def write_kit_provenance(kit, repo, provenance=None):
    """Generator-time receipt for the exact staged inputs and copied LEC tool."""
    kit = Path(kit)
    p = provenance if provenance is not None else _repo_provenance(repo)
    if not re.fullmatch(r"[0-9a-f]{40}", p.get("commit") or "") or p.get("dirty") is not False:
        raise ValueError("kit provenance needs a clean, committed source checkout")
    freeze = json.loads((kit / "freeze.json").read_text())
    if freeze.get("source_commit") != p["commit"]:
        raise ValueError("freeze/source commit mismatch")
    rec = dict(schema="opentallas.kit_provenance.v1", provenance=p,
               kit_hash=freeze.get("kit_hash"), files=_kit_input_identity(kit))
    (kit / "PROVENANCE.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def _provenance(kit=None):
    """Keep repository behavior; validate a generator receipt only as fallback."""
    p = _repo_provenance()
    if re.fullmatch(r"[0-9a-f]{7,40}", p.get("commit") or "") or kit is None:
        return p
    try:
        kit = Path(kit)
        rec = json.loads((kit / "PROVENANCE.json").read_text())
        source = rec["provenance"]
        freeze = json.loads((kit / "freeze.json").read_text())
        valid = (rec.get("schema") == "opentallas.kit_provenance.v1"
                 and re.fullmatch(r"[0-9a-f]{40}", source.get("commit") or "")
                 and source.get("dirty") is False
                 and freeze.get("source_commit") == source["commit"]
                 and rec.get("kit_hash") == freeze.get("kit_hash")
                 and rec.get("files") == _kit_input_identity(kit)
                 and rec["files"]["lec.py"] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        if not valid:
            raise ValueError("source, input or running-tool identity mismatch")
        return dict(source, source="validated kit PROVENANCE.json")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        return dict(commit=None, dirty=None, source=f"kit provenance invalid: {type(e).__name__}: {e}")


PROOF_OPTIONS = ("OT_LEC_HINTS_PRESEED", "OT_LEC_SUPERSET_VEC", "OT_LEC_EARLY_COMPARE")


def main(argv=None):
    global PROVE_JOBS
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ["--capabilities"]:
        print(json.dumps(dict(schema="opentallas.lec_capabilities.v1", proof_options=list(PROOF_OPTIONS))))
        return 0
    if argv[:1] == ["--require-options"]:
        missing = sorted(set(argv[1:]) - set(PROOF_OPTIONS))
        if missing:
            print("LEC CONFIG ERROR: unsupported proof option(s): " + ", ".join(missing), file=sys.stderr)
            return 2
        return 0
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kit")
    ap.add_argument("--netlist", help="gate netlist (default: KIT/run/results/asap7/*/base/1_2_yosys.v)")
    ap.add_argument("--out", help="output dir (default KIT/lec)")
    ap.add_argument("--jobs", type=int, default=1, help="parallel independent SAT-cone batches (admit matching threads/memory)")
    ap.add_argument("--gold-frontend", choices=("verilog", "slang"),
                    help="default: the frontend synthesis did NOT use")
    ap.add_argument("--port-map", help="JSON {gate port bit: gold port bit} (renamed packed buses)")
    ap.add_argument("--hints", help="untrusted correspondence hints JSON, each proved by induction (default: "
                    "KIT/lec_hints.json when present)")
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
            if not (r.get("provenance") or {}).get("commit"):   # the image may not see .git: stamp from the host
                r["provenance"] = _provenance()
                p.write_text(json.dumps(r, indent=1) + "\n")
            print(f"LEC {r['verdict']}: {r.get('top')} {r.get('reason', r.get('note', ''))} "
                  f"({r.get('t_total_s')} s)")
        return rc
    pm = json.loads(Path(a.port_map).read_text()) if a.port_map else None
    r = check(a.kit, a.netlist, a.out, a.gold_frontend, a.conflicts, pm, a.reuse, a.hints)
    c = r.get("counts", {})
    print(f"LEC {r['verdict']}: {r.get('top')} cp={c.get('compare_points')} proved={c.get('proved')} "
          f"differs={c.get('differs')} undecided={c.get('undecided')} {r.get('reason', r.get('note', ''))} "
          f"({r['t_total_s']} s)")
    return {"EQUIVALENT": 0, "NOT EQUIVALENT": 1, "LINT FAIL": 1, "KEEP FAIL": 1, "UNPROVEN": 2}.get(r["verdict"], 3)


if __name__ == "__main__":
    sys.exit(main())
