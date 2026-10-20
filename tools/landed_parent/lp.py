#!/usr/bin/env python3
"""PARENTS-LANDED (coordinator 10-18, standard landed-regions-standard-1018): ONE generator for "landed parents".

A hardened parent bigger than ~1 mm (or with hard children of very different insertion) is clocked like a die:
  * one LOCAL clock region per child group, each region its own clock port ck_<r> and its own small tree;
  * EVERY child-to-child (or port-to-child) net that crosses regions is LANDED: ring ot_pl_land_w on the source region
    root beside the source, read ot_pl_land_r on the destination root beside the reader (LANDING-CONTRACT L1-L7, D slots,
    E = K, +E+1 edges, fixed latency, no ready / credit / backpressure);
  * the only plain cross-region hops are the 1-bit regional reset runs (they define the landing epochs, G == R0);
  * the gate judges per region at the child flops (pre_route_gate multiple_cts_roots + child pairs).
The landing / reset / SDC logic is Q-CLUSTER-LANDALL's (tools/qwen_cluster/qc_gen.py --landings all, qc_kit.py),
generalised from a generated fabric to ANY wires-only flat parent:

  lp.py gen   SPEC.json [--mut-unland]   flat parent RTL -> <top>_lp.sv, <top>_lp.sdc, <top>_lp_record.json,
                                         tb_<top>_lp.sv (lockstep vs the flat parent), <top>_lp_bench.sh
  lp.py audit SPEC.json [--rtl F]        region audit of the generated RTL: every cross-region net is a landing
                                         (ring -> read) or a 1-bit reset run; exit 1 otherwise
  lp.py selftest                         toy parent: gen + audit (+ the unland mutant must FAIL the audit)

Equivalence (what the lockstep bench proves).  Each node (child, port) gets a time offset t (edges later than in the flat
parent): t(reader) >= t(driver) + add, add = E + 1 on a landed net, 0 otherwise (longest path; a cross-region LOOP has no
solution and is reported: the compiler must re-schedule it, lockstep cannot hold).  Where t(reader) > t(driver) + add an
alignment pad of that many register stages goes in front of the reader (in its region).  Every child's reset pin is fed
by its region's reset run delayed by t(child) more stages, so the child's static calendar starts t(child) edges later
too.  Then the landed parent == the flat parent with its reset delayed by RB (the regional reset depth), every input
port p presented off_in(p) edges later and every output port p observed off_out(p) edges later.  Those offsets, the
per-landing added edges and the flop cost are the COMPILER record (<top>_lp_record.json "compiler").

SPEC (JSON; paths relative to the repo root):
  top            flat parent module (wires-only: child instances, wires, assigns; no always / generate)
  sources        files holding the flat parent; child_sources: files declaring every child module (ANSI headers)
  defines        [..]; params {name: value} for width evaluation (defaults from the parent header otherwise)
  out_dir        where <top>_lp.sv / .sdc / tb / bench go; record_dir: where <top>_lp_record.json goes
  clock_ports    flat parent clock port(s) (removed; replaced by ck_<region>)
  clock_pins     child pin names that are clocks      reset_port: parent reset port   reset_pins: child reset pin names
  reset_net      optional internal one-bit child-generated reset, reschedule mode only; reset_port remains external
  reset_active_low (default true)
  regions        [{name, insts: [fnmatch patterns], centre: [x, y] (um, optional)}]   the FIRST is the core region: its
                 clock port is the kit's clock_port (core_clk in the base SDC)
  port_regions   {port: region} overrides (default: input = region of its first reader, output = its driver's region)
  static         [ports / nets] identity straps: never landed (case-analysed), constant in the bench (tb_static {p: v})
  D, E           ring depth / read offset (default 4 / 2: as Q-CLUSTER-LANDALL)
  mut4_stages    MUT 4 holds the first child's reset this many stages longer (default 1: a calendar slip).  Event-driven
                 children (valid-qualified, no free-running calendar) hide a 1-stage slip from random lockstep, so such a
                 parent sets it past the bench warm-up (the mutant then proves the reset run reaches the child).
  reach_um       reset-run hop reach (default 405)         residual_ps: inter-region die residual on the 1-bit reset hops (60)
  bench          {cycles, reset_cycles, sim: iverilog|verilator, child_lockstep: [fnmatch patterns], expr: {input port:
                 per-cycle stimulus expression (default uniform $urandom; may use the tb cycle counter cyc), e.g. to keep a
                 sticky fault from saturating or to make writes legal}, mut_waivers: {mutant number: reason} (that mutant is
                 not run; the record keeps the reason)}
                 child_lockstep (schedule "reference" only; default none): also compare every non-clock pin of the
                 matching children, landed vs flat, at the child (hierarchical u_lp.<inst>.<pin> vs u_flat.<inst>.<pin>):
                 reset pins from reset_cycles on, the rest after warm-up.  Use it when the parent's own outputs do not
                 expose a landed bundle under random stimulus (a centre that ignores ill-formed commands): the
                 landing / reset mutants are then seen where they act, at the child's pins.
  schedule       "offsets" (default: the time-offset method above) | "reference" (cross-region LOOPS, e.g. a centre that
                 commands leaves and collects their results): no offsets / pads; every child's reset run is held
                 reset_extra (default E + 1 + D) more stages so all landings are warm before any child leaves reset, and
                 the lockstep REFERENCE is the flat parent with ref_params (the flat parent's own latency parameters
                 re-scheduled by +E+1 per landed crossing, e.g. relay depths), reset delayed RB + reset_extra, ports at
                 offset 0.  The record's "compiler" block carries ref_params as the re-schedule.
  ref_params     {name: value} parameters of the reference flat instance (schedule "reference"; default = params)
  loose          [nets] STICKY STATUS nets (fault / cause flags that never change a reservation, valid or payload): a
                 cross-region reader is still LANDED (ring + read, the audit sees a landing) but the net is left out of
                 the offset solve, so a status feedback (child fault -> fault join beside the issuer) is not a
                 cross-region loop.  The record lists each loose landing's lag = t(src) + E + 1 - t(reader) (edges the
                 reader sees the flag later than the flat parent); lag < 0 is padded to exact.
  tb_stimulus    optional module-level Verilog include for the lockstep tb: drives fi_<port> and rst (release at
                 bench.reset_cycles) with a real programme instead of random words and ends with lp_finish("<name>")
  sticky_outputs {port: max_lag} outputs fed through loose nets, compared in the bench as sticky (monotone) flags:
                 landed(c) subset of flat(c) and (flat(c - max_lag) & flat(c)) subset of landed(c) (a reset clears).
  out_regs       {output port: stages >= 1} region register stages in front of the output (in the output's region,
                 ot_pl_pad u_lpo_<port>); the port's offset grows by the stages.  REQUIRED for a port -> port pass-through
                 (an output fed combinationally from an input port): the landed standard launches every output from a
                 region flop, so gen fails closed on an unregistered pass-through.  Give a port that is consumed
                 together with the pass-through (same capture edge downstream) the same stages to keep them aligned.
  lag_pins       [{inst: fnmatch pattern, pins: [..], why}]  STATUS-RETURN reader pins (e.g. a head's fault / valid-lockstep
                 inputs fed back from the children it configures).  A head that both configures and collects status from
                 children in other regions is a cross-region LOOP; its status pins are taken OUT of the schedule: they are
                 landed as usual, then padded so every lag pin of that reader sees its net exactly lag(reader) edges later
                 than the reader's own time (one common lag per reader).  The lockstep reference becomes <top>_lagref (the
                 flat parent with those pins delayed lag(reader) stages, generated beside the landed top), and the record's
                 compiler block lists the lag: the status those pins carry reaches the reader's outputs lag edges late.
  mut_child      child whose reset run MUT 4 lengthens (default: the first child with a reset pin); pick one whose state
                 outlives the reset (a sticky flag / counter): a pure pipeline register forgets a late reset in one edge
Child clock pins wider than one bit (a child with several entry clocks in one region) get {W{ck_<r>}}.
  reschedule     true: the parent's children form cross-region LOOPS (e.g. a bidirectional rung stack), so no offset
                 schedule keeps the flat calendar.  Then every child keeps t = 0 (all resets released together, no pads)
                 and every landed net is a COMPILER RE-SCHEDULE of +E+1 edges.  The lockstep reference becomes
                 <top>_rsref = the flat parent with an (E+1)-stage delay on each landed net (zero until E+2 edges after
                 the reset release, as the ring reads), written into the tb file: the bench proves the landing hardware
                 and reset epochs exactly; whether the children's static calendars tolerate the re-schedule is the
                 parent's own behavioural bench (run it on the landed parent), and the record lists every re-scheduled net.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIB_RTL = "rtl/common/landed_parent/ot_pl_land.sv"
RESET_FOREST_RTL = ["rtl/common/landed_parent/ot_pl_land_field_copies.sv",
                    "rtl/common/landed_parent/ot_pl_land_reset_forest.sv"]
KW = {"module", "endmodule", "input", "output", "inout", "wire", "reg", "logic", "assign", "always", "always_ff",
      "always_comb", "initial", "generate", "endgenerate", "parameter", "localparam", "if", "else", "for", "begin", "end",
      "case", "endcase", "function", "endfunction", "genvar", "integer", "signed", "unsigned", "default_nettype"}
LIB_PORTS = {"ot_pl_land_w": {"ck": "in", "rsi": "in", "i": "in", "bank": "out", "epo": "out", "vld": "out"},
             "ot_pl_land_r": {"ck": "in", "rsi": "in", "bank": "in", "epo": "in", "vld": "in", "o": "out"},
             "ot_pl_pad": {"ck": "in", "d": "in", "q": "out"}}
# Chunked primitives preserve the same top-level source/read contract.
LIB_PORTS['ot_pl_land_chunk_w'] = dict(LIB_PORTS['ot_pl_land_w'])
LIB_PORTS['ot_pl_land_chunk_r'] = dict(LIB_PORTS['ot_pl_land_r'])
LIB_PORTS['ot_pl_land_vector_reset_w'] = dict(LIB_PORTS['ot_pl_land_w'])
LIB_PORTS['ot_pl_land_vector_reset_r'] = dict(LIB_PORTS['ot_pl_land_r'])
LIB_PORTS['ot_pl_land_reset_forest'] = dict(LIB_PORTS['ot_pl_pad'])



# ----------------------------------------------------------------------------------------------------- verilog parsing
def preprocess(text: str, defines) -> str:
    """comments stripped, `ifdef / `ifndef / `elsif / `else / `endif resolved (as pre_route_gate._vlog_preprocess)"""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    defs = {str(d).split("=", 1)[0].lstrip("-D") for d in defines or []}
    out, stack = [], []
    for line in text.splitlines():
        m = re.match(r"\s*`(ifdef|ifndef|elsif|else|endif)\b\s*(\w*)", line)
        live = all(x[0] for x in stack)
        if not m:
            if live and not re.match(r"\s*`", line):
                out.append(line)
            continue
        kw, name = m.groups()
        if kw in ("ifdef", "ifndef"):
            on = (name in defs) == (kw == "ifdef")
            stack.append([on, on])
        elif kw == "elsif" and stack:
            on = not stack[-1][1] and name in defs
            stack[-1] = [on, stack[-1][1] or on]
        elif kw == "else" and stack:
            stack[-1] = [not stack[-1][1], True]
        elif kw == "endif" and stack:
            stack.pop()
    return "\n".join(out)


def split_top(s: str, sep=","):
    """split on sep outside (), [], {}"""
    out, depth, cur = [], 0, []
    for ch in s:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == sep and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if "".join(cur).strip():
        out.append("".join(cur))
    return out


def match_paren(s: str, i: int) -> int:
    """index of the ')' matching s[i] == '('"""
    d = 0
    for j in range(i, len(s)):
        if s[j] == "(":
            d += 1
        elif s[j] == ")":
            d -= 1
            if d == 0:
                return j
    raise ValueError("unbalanced parentheses")


def parse_module(text: str, name: str) -> dict:
    """ANSI module: params (defaults), ports [{name, dir, range}], body text, header pieces"""
    m = re.search(rf"\bmodule\s+{re.escape(name)}\b", text)
    if not m:
        raise SystemExit(f"module {name} not found")
    i = m.end()
    params_txt = None
    j = i
    while text[j].isspace():
        j += 1
    if text[j] == "#":
        k = text.index("(", j)
        e = match_paren(text, k)
        params_txt = text[k + 1:e]
        j = e + 1
        while text[j].isspace():
            j += 1
    if text[j] != "(":
        raise SystemExit(f"{name}: non-ANSI header not supported")
    e = match_paren(text, j)
    ports_txt = text[j + 1:e]
    semi = text.index(";", e)
    end = text.index("endmodule", semi)
    body = text[semi + 1:end]
    params = {}
    for it in split_top(params_txt or ""):
        mm = re.match(r"\s*(?:parameter|localparam)?\s*(?:integer|int|logic|bit|signed|\[[^\]]*\])?\s*(\w+)\s*=\s*(.+)", it, re.S)
        if mm:
            params[mm.group(1)] = mm.group(2).strip()
    for mm in re.finditer(r"\blocalparam\b\s*(?:integer|int|\[[^\]]*\])?\s*(\w+)\s*=\s*([^;,]+)", body):
        params[mm.group(1)] = mm.group(2).strip()
    ports, d, rng = [], None, None
    names = [" ".join(it.split()) for it in split_top(ports_txt)]
    if names and all(re.fullmatch(r"\w+", n) for n in names):
        # non-ANSI (Verilog-1995) header: directions / ranges from the body's port declarations, which are then
        # removed from the body (with their 'wire X;' twins) so emit() re-declares each port exactly once
        decl = {}
        def take(mm):
            ds, r, ns = mm.group(1), mm.group(2), [x.strip() for x in mm.group(3).split(",")]
            if all(x in names for x in ns):
                for x in ns:
                    decl[x] = (ds, r)
                return ""
            return mm.group(0)
        body = re.sub(r"\b(input|output|inout)\b\s*(?:wire|reg|logic)?\s*(?:signed)?\s*(\[[^\]]*\])?\s*([\w\s,]+?)\s*;",
                      take, body)
        body = re.sub(r"\bwire\b\s*(?:signed)?\s*(\[[^\]]*\])?\s*(\w+)\s*;",
                      lambda mm: "" if mm.group(2) in decl else mm.group(0), body)
        for n in names:
            if n not in decl:
                raise SystemExit(f"{name}: non-ANSI port {n} has no input/output declaration")
            ds, r = decl[n]
            item = f"{ds} wire {r + ' ' if r else ''}{n}"
            ports.append(dict(name=n, dir={"input": "in", "output": "out", "inout": "inout"}[ds], range=r, item=item))
        return dict(name=name, params=params, params_txt=params_txt, ports=ports, body=body)
    for it in split_top(ports_txt):
        it = " ".join(it.split())
        mm = re.match(r"(input|output|inout)?\s*(?:wire|reg|logic)?\s*(?:signed)?\s*(\[[^\]]*\])?\s*(\w+)$", it)
        if not mm:
            raise SystemExit(f"{name}: cannot parse port item '{it}'")
        if mm.group(1):
            d, rng = mm.group(1), mm.group(2)
        elif mm.group(2):
            rng = mm.group(2)
        ports.append(dict(name=mm.group(3), dir={"input": "in", "output": "out", "inout": "inout"}[d], range=rng,
                          item=f"{d} wire {rng + ' ' if rng else ''}{mm.group(3)}"))
    return dict(name=name, params=params, params_txt=params_txt, ports=ports, body=body)




def parse_body(body: str):
    """wires {name: range}, assigns [(lhs_idents, rhs_idents)], instances [{module, params, inst, conns, span}]"""
    if re.search(r"\b(always|always_ff|always_comb|generate|initial)\b", body):
        raise SystemExit("the flat parent has procedural logic or a generate block: lp.py needs a wires-only parent "
                         "(plain child instances, wires, assigns); move glue into a child or expand the generate")
    wires = {}
    for mm in re.finditer(r"\b(?:wire|logic)\b\s*(?:signed)?\s*(\[[^\]]*\])?\s*([^;=]+?)\s*(=\s*[^;]+)?;", body):
        for n in mm.group(2).split(","):
            n = n.strip()
            if re.fullmatch(r"\w+", n):
                wires[n] = mm.group(1)
    assigns = []
    for mm in re.finditer(r"\bassign\b\s*(.+?)\s*=\s*(.+?);", body, re.S):
        assigns.append((idents(mm.group(1)), idents(mm.group(2))))
    for mm in re.finditer(r"\bwire\b\s*(?:signed)?\s*(\[[^\]]*\])?\s*([^;]*=[^;]*);", body):
        for it in split_top(mm.group(2)):          # wire [r] a = x, b = y;  (several initialised declarators)
            m2 = re.match(r"\s*(\w+)\s*=\s*(.+)$", it, re.S)
            if m2:
                assigns.append(({m2.group(1)}, idents(m2.group(2))))
                wires[m2.group(1)] = mm.group(1)
    insts = []
    pos = 0
    head = re.compile(r"\b([A-Za-z_]\w*)\s*(#\s*\()?")
    while True:
        mm = head.search(body, pos)
        if not mm:
            break
        mod = mm.group(1)
        if mod in KW:
            pos = mm.end()
            continue
        j, par = mm.end(), ""
        if mm.group(2):
            e = match_paren(body, mm.end() - 1)
            par, j = body[mm.start(2):e + 1], e + 1
        m2 = re.compile(r"\s*([A-Za-z_]\w*)\s*\(").match(body, j)
        if not m2 or m2.group(1) in KW:
            pos = mm.end()
            continue
        inst = m2.group(1)
        po = m2.end() - 1
        pe = match_paren(body, po)
        m3 = re.compile(r"\s*;").match(body, pe + 1)
        if not m3:
            pos = mm.end()
            continue
        semi = m3.end() - 1
        conns = {}
        for it in split_top(body[po + 1:pe]):
            c = re.match(r"\s*\.\s*(\w+)\s*\((.*)\)\s*$", it, re.S)
            if not c:
                raise SystemExit(f"instance {inst}: only named connections are supported ('{it.strip()[:60]}')")
            conns[c.group(1)] = c.group(2).strip()
        insts.append(dict(module=mod, params=par.strip(), inst=inst, conns=conns, span=(mm.start(), semi + 1)))
        pos = semi + 1
    return wires, assigns, insts


def full_item(p: dict) -> str:
    """a port item that stands alone ('input logic a, b' lists carry the direction on the first item only)"""
    if re.match(r"(input|output|inout)\b", p["item"]):
        return p["item"]
    d = {"in": "input", "out": "output", "inout": "inout"}[p["dir"]]
    return f"{d} wire {p['range'] + ' ' if p['range'] else ''}{p['name']}"


def idents(expr: str) -> set:
    expr = re.sub(r"\d+'[sS]?[bBoOdDhH][0-9a-fA-F_xXzZ]+", " ", expr)
    return {n for n in re.findall(r"(?<![\w'$`.])([A-Za-z_]\w*)\b", expr) if n not in KW}


def c_to_py(x: str) -> str:
    """C / Verilog constant expression -> Python: c ? a : b (innermost first), &&, ||, ! (TW2-COLLAR 10-19: a child
    port [PW-1:0] with PW=(ROWS>64)?7:6, the XDIE-HBM4 issuer / fj, failed eval)"""
    x = x.replace("&&", " and ").replace("||", " or ")
    x = re.sub(r"!(?!=)", " not ", x)
    while "?" in x:
        q = x.rindex("?")
        d, i = 0, q - 1                       # condition: back to the enclosing '(' (or the start)
        while i >= 0 and not (x[i] == "(" and d == 0):
            d += {")": 1, "(": -1}.get(x[i], 0)
            i -= 1
        d, j, c = 0, q + 1, None              # ':' at depth 0, then the false branch to the enclosing ')' (or the end)
        while j < len(x) and not (x[j] == ")" and d == 0):
            if x[j] == ":" and d == 0 and c is None:
                c = j
            d += {"(": 1, ")": -1}.get(x[j], 0)
            j += 1
        if c is None:
            raise ValueError(f"ternary without ':' in {x!r}")
        x = x[:i + 1] + f"(({x[q + 1:c]}) if ({x[i + 1:q]}) else ({x[c + 1:j]}))" + x[j:]
    return x


def split_range(rng: str):
    """[msb:lsb] -> (msb, lsb): the range ':' is the one at paren depth 0 not paired with a ternary '?'"""
    t, d, q = rng.strip()[1:-1], 0, 0
    for i, ch in enumerate(t):
        d += {"(": 1, ")": -1}.get(ch, 0)
        if d == 0 and ch == "?":
            q += 1
        elif d == 0 and ch == ":":
            if q:
                q -= 1
            else:
                return t[:i], t[i + 1:]
    raise ValueError(f"no range ':' in {rng!r}")


def eval_width(rng: str | None, env: dict) -> int:
    if not rng:
        return 1
    a, b = split_range(rng)
    def ev(x):
        x = x.replace("$clog2", "_clog2")
        for _ in range(8):
            for k, v in env.items():
                x = re.sub(rf"\b{re.escape(k)}\b", f"({v})", x)
        return int(eval(c_to_py(x), {"_clog2": lambda v: max(0, math.ceil(math.log2(v))) if v > 0 else 0}))
    return abs(ev(a) - ev(b)) + 1


def width_text(rng: str | None) -> str:
    if not rng:
        return "1"
    a, b = split_range(rng)
    return f"(({a.strip()}) - ({b.strip()}) + 1)"


# ----------------------------------------------------------------------------------------------------------- the model
def regional_bindings(spec, insts, csrc):
    """Exact LSB-first regional clock/reset vector bindings; no datapath waiver.

    Flat inputs must be a literal replication of the parent clock/reset. Vector
    aliases, expressions and parameter-dependent port shapes are rejected so
    the generated bit-to-root contract can be audited without interpretation.
    """
    result = {}
    regions = {r['name'] for r in spec['regions']}
    by_inst = {i['inst']: i for i in insts}
    for role in ('clocks', 'resets'):
        key = 'regional_child_' + role
        rows = spec.get(key) or []
        if not isinstance(rows,list):
            raise SystemExit(f'{key}: requires a list')
        for row in rows:
            if not isinstance(row,dict) or set(row) != {'inst', 'pin', 'regions'}:
                raise SystemExit(f'{key}: requires exact inst/pin/regions fields')
            inst, pin, rs = row['inst'], row['pin'], row['regions']
            if not isinstance(inst,str) or not isinstance(pin,str) or inst not in by_inst or (inst, pin) in result:
                raise SystemExit(f'{key}: missing or duplicate instance/pin {inst}.{pin}')
            i = by_inst[inst]
            cm = parse_module(csrc, i['module'])
            port = next((p for p in cm['ports'] if p['name'] == pin), None)
            declared = spec.get('clock_pins' if role == 'clocks' else 'reset_pins') or []
            if not port or port['dir'] != 'in' or pin not in declared or pin not in i['conns']:
                raise SystemExit(f'{key}: {inst}.{pin} is not a declared {role} input')
            if not isinstance(rs, list) or len(rs) < 2 or any(not isinstance(r,str) for r in rs) or len(set(rs)) != len(rs) or any(r not in regions for r in rs):
                raise SystemExit(f'{key}: regions must be distinct known roots in LSB-first order')
            # The initial interface is deliberately constant-sized, descending,
            # zero-based; accept no vector direction or param alias ambiguity.
            rng = re.sub(r'\s+', '', port['range'] or '')
            if rng != f'[{len(rs)-1}:0]':
                raise SystemExit(f'{key}: {inst}.{pin} must have literal range [{len(rs)-1}:0]')
            roots = (spec.get('clock_ports') or []) if role == 'clocks' else [spec.get('reset_port')]
            ex = re.sub(r'\s+', '', i['conns'][pin])
            if ex not in {f'{{{len(rs)}{{{r}}}}}' for r in roots}:
                raise SystemExit(f'{key}: {inst}.{pin} must replicate one parent {role} root, no aliases')
            result[inst, pin] = dict(role=role, regions=list(rs))
    if result:
        clock_roots = {r for b in result.values() if b['role']=='clocks' for r in b['regions']}
        ordinary_roots = {r['name'] for r in spec['regions'] if any(
            fnmatch.fnmatchcase(i['inst'],pattern) for i in insts for pattern in r['insts'])}
        if regions - ordinary_roots - clock_roots:
            raise SystemExit('regional_child_clocks: every extra root needs an explicit child clock bit')
        for (inst,pin), b in result.items():
            if b['role']=='resets' and not any(j==inst and q['role']=='clocks' and q['regions']==b['regions']
                                               for (j,p),q in result.items()):
                raise SystemExit(f'regional_child_resets: {inst}.{pin} has no matching clock-bit epochs')
            if b['role']=='clocks' and not any(j==inst and q['role']=='resets' and q['regions']==b['regions']
                                               for (j,p),q in result.items()):
                raise SystemExit(f'regional_child_clocks: {inst}.{pin} needs explicit matching reset-bit epochs; reset-free exceptions unsupported')
    return result


class Parent:
    def __init__(self, spec: dict):
        self.S = spec
        src = "\n".join(preprocess((ROOT / f).read_text(errors="replace"), spec.get("defines")) for f in spec["sources"])
        self.mod = parse_module(src, spec["top"])
        csrc = "\n".join(preprocess((ROOT / f).read_text(errors="replace"), spec.get("defines"))
                         for f in spec.get("child_sources", []))
        self.wires, self.assigns, self.insts = parse_body(self.mod["body"])
        hard = spec.get("synthesis_hard_instances", [])
        if not isinstance(hard, list) or any(not isinstance(x, str) for x in hard) or len(set(hard)) != len(hard):
            raise SystemExit("synthesis_hard_instances must be a list of unique exact instance names")
        unknown = set(hard) - {ins["inst"] for ins in self.insts}
        if unknown:
            raise SystemExit(f"unknown synthesis hard instances: {sorted(unknown)}")
        self.env = {k: v for k, v in self.mod["params"].items()}
        self.env.update({k: str(v) for k, v in (spec.get("params") or {}).items()})
        self.regional_bindings = regional_bindings(spec, self.insts, csrc)
        self.cports, self.cwidth = {}, {}
        for ins in self.insts:
            m = ins["module"]
            if m not in self.cports:
                cm = parse_module(csrc, m)
                self.cports[m] = {p["name"]: p["dir"] for p in cm["ports"]}
                self.cwidth[m] = {p["name"]: eval_width(p["range"], dict(cm["params"])) for p in cm["ports"]}
        self.ports = {p["name"]: p for p in self.mod["ports"]}
        self.ck = set(spec.get("clock_ports") or [])
        self.preserve_ck = set(spec.get("preserve_clock_ports") or [])
        if self.ck & self.preserve_ck:
            raise SystemExit("a clock port cannot be both regional and preserved")
        self.reset_port = spec.get("reset_port")
        self.rst = spec.get("reset_net") or self.reset_port
        if self.reset_port not in self.ports:
            raise SystemExit("reset_port must name a parent input port")
        if spec.get("reset_net") and not spec.get("reschedule"):
            raise SystemExit("reset_net currently requires reschedule mode")
        self.static = set(spec.get("static") or [])
        self.loose = set(spec.get("loose") or [])
        self.regions = [r["name"] for r in spec["regions"]]
        self.region = {}
        for ins in self.insts:
            hit = [r["name"] for r in spec["regions"] if any(fnmatch.fnmatchcase(ins["inst"], p) for p in r["insts"])]
            if len(hit) != 1:
                raise SystemExit(f"instance {ins['inst']} matches regions {hit}: every child needs exactly one region")
            self.region[ins["inst"]] = hit[0]
        self.D, self.E = int(spec.get("D", 4)), int(spec.get("E", 2))
        self.K = self.E
        self.direct_timing = bool(spec.get("landing_direct_timing", False))
        self.chunk_bits = int(spec.get("landing_chunk_bits", 0))
        self.reset_forest = spec.get("landing_reset_forest", False)
        if type(self.reset_forest) is not bool:
            raise SystemExit("landing_reset_forest must be an explicit boolean")
        if self.reset_forest and not self.chunk_bits:
            raise SystemExit("landing_reset_forest requires explicit landing_chunk_bits")
        if self.chunk_bits and not 1 <= self.chunk_bits <= 24:
            raise SystemExit("landing_chunk_bits must be 1..24 (kept local selector fanout)")
        if self.direct_timing and (self.D != 4 or self.E != 2):
            raise SystemExit("landing_direct_timing requires the proven D4/E2 phase envelope")
        self.A = self.E + 1
        self.lag = set()
        for g in spec.get("lag_pins") or []:
            hit = [i["inst"] for i in self.insts if fnmatch.fnmatchcase(i["inst"], g["inst"])]
            if not hit:
                raise SystemExit(f"lag_pins: no instance matches {g['inst']}")
            for i in hit:
                for pin in g["pins"]:
                    self.lag.add((i, pin))
        self.AW = 1 if self.D <= 2 else math.ceil(math.log2(self.D))
        self.reference = spec.get("schedule", "offsets") == "reference"
        self.rx = int(spec.get("reset_extra", self.A + self.D)) if self.reference else 0
        if spec.get("reset_net"):
            if self.rng(self.rst) is not None:
                raise SystemExit("reset_net must be one bit")
            drivers = [i for i in self.insts if any(
                self.cports[i["module"]][pin] == "out" and self.rst in idents(ex)
                for pin, ex in i["conns"].items())]
            if len(drivers) != 1:
                raise SystemExit("reset_net must have exactly one child driver")
            self.reset_driver = drivers[0]["inst"]
            spec.setdefault("reset_region", self.region[self.reset_driver])

    def rng(self, n):
        if n in self.wires:
            return self.wires[n]
        if n in self.ports:
            return self.ports[n]["range"]
        raise SystemExit(f"net {n} has no declaration in {self.S['top']}")

    def graph(self):
        """drivers {net: {node}}, readers [(net, node, pin)]; node = inst name or 'port:<p>'"""
        excl = self.ck | self.preserve_ck | {self.rst} | self.static
        drv = {}
        for ins in self.insts:
            for pin, ex in ins["conns"].items():
                d = self.cports[ins["module"]].get(pin)
                if d is None:
                    raise SystemExit(f"{ins['inst']}: pin {pin} not in module {ins['module']}")
                if d == "out":
                    for n in idents(ex):
                        drv.setdefault(n, set()).add(ins["inst"])
        for p in self.mod["ports"]:
            if p["dir"] == "in" and p["name"] not in excl:
                drv.setdefault(p["name"], set()).add(f"port:{p['name']}")
        for _ in range(len(self.assigns) + 1):          # transitive through assigns
            for lhs, rhs in self.assigns:
                src = set().union(*(drv.get(n, set()) for n in rhs - excl)) if rhs - excl else set()
                for n in lhs:
                    if not src <= drv.get(n, set()):
                        drv[n] = drv.get(n, set()) | src
        rd = []
        for ins in self.insts:
            for pin, ex in ins["conns"].items():
                if self.cports[ins["module"]][pin] != "in":
                    continue
                if pin in (self.S.get("clock_pins") or []) or pin in (self.S.get("reset_pins") or []):
                    continue
                for n in sorted(idents(ex) - excl):     # sorted: a set's order is PYTHONHASHSEED-random (pslice real7)
                    if n in self.env:
                        continue
                    rd.append((n, ins["inst"], pin))
        out_drv = {}
        for p in self.mod["ports"]:
            if p["dir"] == "out":
                out_drv[p["name"]] = drv.get(p["name"], set())
        return drv, rd, out_drv

    def node_region(self, node, drv, rd, out_drv):
        if not node.startswith("port:"):
            return self.region[node]
        p = node[5:]
        if p in (self.S.get("port_regions") or {}):
            return self.S["port_regions"][p]
        if self.ports[p]["dir"] == "in":
            rs = [self.region[i] for n, i, _ in rd if n == p]
            return rs[0] if rs else self.regions[0]
        regs = {self.region[d] for d in out_drv[p] if not d.startswith("port:")}
        if len(regs) > 1:
            raise SystemExit(f"output port {p} is driven from regions {sorted(regs)}: split the port")
        return regs.pop() if regs else self.regions[0]

    def plan(self, mut_unland=False):
        drv, rd, out_drv = self.graph()
        nreg = {}
        for n, ds in drv.items():
            for d in ds:
                nreg[d] = self.node_region(d, drv, rd, out_drv)
        for p in out_drv:
            nreg[f"port:{p}"] = self.node_region(f"port:{p}", drv, rd, out_drv)
        edges = []          # (src node, dst node, net, add, landed?, reader pin)
        loose = []          # the same for STICKY STATUS nets: landed, not in the offset solve
        lands = {}          # (net, dst region) -> landing
        for n, inst, pin in rd:
            ds = drv.get(n, set())
            if not ds:
                raise SystemExit(f"net {n} read by {inst}.{pin} has no driver (open input: no stubs, owner 10-14)")
            sregs = {nreg[d] for d in ds}
            if len(sregs) > 1:
                raise SystemExit(f"net {n} is driven from regions {sorted(sregs)}: split it per region")
            s, r = sregs.pop(), self.region[inst]
            landed = s != r
            # TW2-PSLICE2 10-19 (opt-in reader_per_inst): one read half per READER INSTANCE (beside it), not per region
            key = (n, inst) if self.S.get("reader_per_inst") else (n, r)
            if landed and key not in lands:
                lands[key] = dict(name=f"{len(lands)}", net=n, src_region=s, dst_region=r,
                                  src_nodes=sorted(ds), width=eval_width(self.rng(n), self.env), readers=[])
                if self.S.get("reader_per_inst"):
                    lands[key]["dst_inst"] = inst
            if landed:
                lands[key]["readers"].append(f"{inst}.{pin}")
            if landed and n in self.loose:
                lands[key]["loose"] = True
            for d in ds:
                (loose if n in self.loose else edges).append((d, inst, n, self.A if landed else 0, landed, pin))
        oregs = {k: int(v) for k, v in (self.S.get("out_regs") or {}).items()}
        for p, k in oregs.items():
            if p not in out_drv or k < 1:
                raise SystemExit(f"out_regs {p}: not an output port of {self.S['top']} or stages {k} < 1")
            if any(n == p for n, _, _ in rd):
                raise SystemExit(f"out_regs {p}: the port is also read inside the parent; register a dedicated output net")
        for p, ds in out_drv.items():
            thru = sorted(d for d in ds if d.startswith("port:"))
            if thru and not oregs.get(p):
                raise SystemExit(f"output {p} is a port pass-through of {', '.join(thru)}: the landed standard launches "
                                 f"every output from a region flop (OT_MULTI_ROOT refuses it); add out_regs {{\"{p}\": 1}} "
                                 "(and the same stages on any port captured together with it)")
            for d in ds:
                edges.append((d, f"port:{p}", p, oregs.get(p, 0), False, None))
        nodes = sorted({e[0] for e in edges + loose} | {e[1] for e in edges + loose} | set(self.region))
        lagged = [e for e in edges if (e[1], e[5]) in self.lag]
        edges_all, edges = edges, [e for e in edges if (e[1], e[5]) not in self.lag]
        t = {v: 0 for v in nodes}
        if self.reference:
            lst = sorted(lands.values(), key=lambda L: int(L["name"]))
            if mut_unland and lst:
                lst[0]["unlanded_mutant"] = True
            return dict(t=t, edges=edges, lands=lst, landkey=lands, pads={}, nreg=nreg, drv=drv, rd=rd, out_drv=out_drv)
        resched = bool(self.S.get("reschedule"))
        for it in ([] if resched else range(len(nodes) + 1)):
            ch = False
            for a, b, n, add, _, _ in edges:
                if t[a] + add > t[b]:
                    t[b] = t[a] + add
                    ch = True
            if not ch:
                break
        else:
          if not resched:
            loop = [f"{a}->{b} ({n}, +{add})" for a, b, n, add, _, _ in edges if t[a] + add > t[b]]
            raise SystemExit("cross-region LOOP: the landed parent cannot keep the flat schedule (the compiler must "
                             "re-schedule, or keep the loop inside one region): " + "; ".join(loop[:8]))
        for v in ([] if resched else nodes):    # input ports: as late as their earliest reader allows (no pad there)
            if v.startswith("port:") and self.ports[v[5:]]["dir"] == "in":
                outs = [t[b] - add for a, b, n, add, _, _ in edges if a == v]
                if outs:
                    t[v] = min(outs)
                elif any(a == v for a, *_ in lagged):
                    t[v] = min(t[b] for a, b, *_ in lagged if a == v)
        for p, ds in out_drv.items():
            ts = {t[d] for d in ds}
            if len(ts) > 1:
                raise SystemExit(f"output port {p} merges drivers with offsets {sorted(ts)}: split the port")
        pads = {}           # (net, reader inst) -> stages
        for a, b, n, add, landed, pin in edges:
            if b.startswith("port:"):
                continue
            k = t[b] - t[a] - add
            if resched:
                continue
            if k > 0:
                pads[(n, b)] = max(pads.get((n, b), 0), k)
            if k < 0:
                raise SystemExit("internal: negative pad")
        lags = {}
        for a, b, n, add, landed, pin in loose:
            k = t[b] - t[a] - add
            if k > 0:
                pads[(n, b)] = max(pads.get((n, b), 0), k)
            lags[(n, b)] = max(lags.get((n, b), -10 ** 9), -k)
        lag = {}            # reader inst -> common status lag (edges after the reader's own time)
        for a, b, n, add, landed, pin in lagged:
            lag[b] = max(lag.get(b, 0), t[a] + add - t[b])
        for a, b, n, add, landed, pin in lagged:
            k = t[b] + lag[b] - t[a] - add
            if k > 0:
                pads[(n, b)] = max(pads.get((n, b), 0), k)
        edges = edges_all
        # strict landings first (MUT 1 / 2 act on landing 0: it must be schedule-bearing), loose ones last; renumber
        lst = sorted(lands.values(), key=lambda L: (bool(L.get("loose")), int(L["name"])))
        for j, L in enumerate(lst):
            L["name"] = str(j)
        if self.S.get("share_rings"):
            # TW2-PSLICE2 10-19 (opt-in share_rings): ONE write ring per (net, source region), beside the source; every read
            # half of that net (each destination region / reader instance) reads the same ring bank (LANDING-CONTRACT
            # unchanged: equal-depth reset runs G == R0, so every reader keeps K = E; the ring -> read multicycle is per pair)
            own = {}
            for L in lst:
                L["ring_of"] = own.setdefault((L["net"], L["src_region"]), L["name"])
        if mut_unland and lst:
            lst[0]["unlanded_mutant"] = True
        loose_lag = [dict(net=n, reader=b, lag_edges=max(0, v)) for (n, b), v in sorted(lags.items())]
        return dict(t=t, edges=edges, lands=lst, landkey=lands, pads=pads, nreg=nreg, drv=drv, rd=rd, out_drv=out_drv,
                    loose=loose, loose_lag=loose_lag, oregs=oregs, lag=lag, lagged=lagged, resched=resched)

    def emit_lagref(self, P):
        """<top>_lagref: the FLAT parent with every lag pin delayed lag(reader) stages (the lockstep reference)"""
        S, top = self.S, self.S["top"] + "_lagref"
        ck = sorted(self.ck)[0]
        L = ["`timescale 1ns/1ps", f"// GENERATED by tools/landed_parent/lp.py: {S['top']} with its status-return (lag_pins) "
             f"inputs delayed {dict(sorted(P['lag'].items()))} stages -- the lockstep reference of the landed parent.",
             f"module {top} " + (f"#({self.mod['params_txt']}) " if self.mod["params_txt"] and self.mod["params_txt"].strip() else "")
             + "(\n    " + ",\n    ".join(full_item(p) for p in self.mod["ports"]) + "\n);"]
        body, keep, pos = self.mod["body"], [], 0
        for ins in self.insts:
            keep.append(body[pos:ins["span"][0]])
            pos = ins["span"][1]
        keep.append(body[pos:])
        L += [ln.rstrip() for ch in keep for ln in ch.splitlines() if ln.strip()]
        sub = {}
        for j, (a, b, n, add, landed, pin) in enumerate(sorted(P["lagged"], key=lambda e: (e[1], e[5], e[2]))):
            if (b, pin, n) in sub or P["lag"][b] == 0:
                continue
            rng = self.rng(n)
            q = f"{n}__lag_{b}_{pin}"
            L.append(f"    wire {rng or ''} {q};  ot_pl_pad #(.W({width_text(rng)}), .N({P['lag'][b]})) u_lag_{j} (.ck({ck}), "
                     f".d({n}), .q({q}));")
            sub[(b, pin, n)] = q
        for ins in self.insts:
            cs = []
            for pin, ex in ins["conns"].items():
                for (bi, bp, n), q in sub.items():
                    if bi == ins["inst"] and bp == pin:
                        ex = re.sub(rf"(?<![\w$]){re.escape(n)}\b", q, ex)
                cs.append(f".{pin}({ex})")
            L.append(f"    {ins['module']} {ins['params'] + ' ' if ins['params'] else ''}{ins['inst']} (" + ", ".join(cs) + ");")
        L.append("endmodule")
        return top, "\n".join(L) + "\n"

    def rsref(self, P):
        """reschedule mode: the flat parent with an (E+1)-stage delay on every landed net at its landed readers, zero
        until E+2 edges after the reset release (exactly what ot_pl_land_w/_r deliver); single flat clock"""
        S, A = self.S, self.A
        ck = sorted(self.ck)[0]
        items = [p["item"] for p in self.mod["ports"]]
        par = ("#(\n    " + self.mod["params_txt"].strip() + "\n) ") if (self.mod["params_txt"] or "").strip() else ""
        L = [f"// GENERATED by tools/landed_parent/lp.py (reschedule): {S['top']} with +{A} edges on each of the "
             f"{len(P['lands'])} landed nets (the compiler re-schedule) -- the lockstep reference of {S['top']}_lp",
             f"module {S['top']}_rsref {par}(\n    " + ",\n    ".join(items) + "\n);"]
        body = self.mod["body"]
        pos = 0
        for ins in self.insts:
            L += [ln.rstrip() for ln in body[pos:ins["span"][0]].splitlines() if ln.strip()]
            pos = ins["span"][1]
        L += [ln.rstrip() for ln in body[pos:].splitlines() if ln.strip()]
        ref_reset = self.rst
        if S.get("reset_net"):
            _, _, RB = self.reset_tree()
            L.append(f"    wire lprs_reset; ot_pl_pad #(.W(1), .N({RB})) u_lprs_reset (.ck({ck}), .d({self.rst}), .q(lprs_reset));")
            ref_reset = "lprs_reset"
        rel = ref_reset if S.get("reset_active_low", True) else f"~{ref_reset}"
        L.append(f"    wire lprs_g;  ot_pl_pad #(.W(1), .N({A + 1})) u_lprs_g (.ck({ck}), .d({rel}), .q(lprs_g));")
        sub = {}
        for Ld in P["lands"]:
            n, net, r = Ld["name"], Ld["net"], Ld["dst_region"]
            rng = self.rng(net)
            wt = width_text(rng)
            q, o = f"{net}__rq_{r}", f"{net}__rs_{r}"
            L.append(f"    wire {rng or ''} {q}, {o};  ot_pl_pad #(.W({wt}), .N({A})) u_lprs_{n} (.ck({ck}), .d({net}), .q({q}));"
                     f"  assign {o} = lprs_g ? {q} : {{({wt}){{1'b0}}}};")
            for rp in Ld["readers"]:
                sub[(rp.split(".")[0], net)] = o
        for ins in self.insts:
            i = ins["inst"]
            cs = []
            for pin, ex in ins["conns"].items():
                if S.get("reset_net") and self.cports[ins["module"]][pin] == "in" and pin in (S.get("reset_pins") or []) and ex.strip() == self.rst:
                    ex = ref_reset
                elif self.cports[ins["module"]][pin] == "in":
                    for (si, net), rep_ in sub.items():
                        if si == i:
                            ex = re.sub(rf"(?<![\w$]){re.escape(net)}\b", rep_, ex)
                cs.append(f".{pin}({ex})")
            L.append(f"    {ins['module']} {ins['params'] + ' ' if ins['params'] else ''}{i} (" + ", ".join(cs) + ");")
        L.append("endmodule")
        return "\n".join(L) + "\n"

    # ---------------------------------------------------------------------------------------------------- emitters
    def reset_tree(self):
        rr = (self.S.get("reset_region") or self.regions[0])
        cen = {r["name"]: r.get("centre") for r in self.S["regions"]}
        reach = float(self.S.get("reach_um", 405))
        hops = {}
        for r in self.regions:
            if r == rr:
                hops[r] = 0
            elif cen.get(r) and cen.get(rr):
                d = abs(cen[r][0] - cen[rr][0]) + abs(cen[r][1] - cen[rr][1])
                hops[r] = max(1, math.ceil(d / reach))
            else:
                hops[r] = 1
        RB = 1 + max(max(hops.values()), 1)
        return rr, hops, RB

    def reset_forest_plan(self, P):
        """Exact per-chunk leaf allocation at unchanged regional reset depth."""
        if not self.reset_forest:
            return None
        _, _, RB = self.reset_tree()
        depth = RB - 1
        if depth < 2:
            raise SystemExit("landing_reset_forest needs at least two already-priced regional stages; no free reset edge")
        regions = {r: dict(leaves=1, terms=['1'], bindings=[]) for r in self.regions}
        for land in P['lands']:
            n = land['name']
            roles = [('r', land['dst_region'])]
            if land.get('ring_of', n) == n:
                roles.insert(0, ('w', land['src_region']))
            wt = width_text(self.rng(land['net']))
            count_expr = f'((({wt})+{self.chunk_bits}-1)/{self.chunk_bits})'
            count = math.ceil(land['width'] / self.chunk_bits)
            for role, region in roles:
                row = regions[region]
                row['bindings'].append(dict(landing=n, role=role, first_leaf=row['leaves'],
                    chunks=count, first_expr='+'.join(row['terms']), chunks_expr=count_expr))
                row['leaves'] += count
                row['terms'].append(count_expr)
        for region, row in regions.items():
            if row['leaves'] > 1024:
                raise SystemExit(f'landing_reset_forest {region}: {row["leaves"]} leaves exceeds1024')
            row['branches'] = math.ceil(row['leaves'] / 32)
            row['FFs'] = depth - 2 + row['branches'] + row['leaves']
            scalar_uses = sum(self.region[ins['inst']] == region and any(
                pin in (self.S.get('reset_pins') or []) and ex.strip() == self.rst
                for pin, ex in ins['conns'].items()) for ins in self.insts)
            scalar_uses += sum(binding['regions'].count(region) for binding in self.regional_bindings.values()
                               if binding['role'] == 'resets')
            row['scalar_child_pad_port_uses'] = scalar_uses
            if scalar_uses > 32:
                raise SystemExit(f'landing_reset_forest {region} scalar child reset boundary has {scalar_uses} ports; partition still required')
        root_loads = sum(v['branches'] if depth == 2 else 1 for v in regions.values())
        if root_loads > 32:
            raise SystemExit(f'landing_reset_forest root has {root_loads} registered loads; no added edge credited')
        return dict(regional_stages=depth, root_D_loads=root_loads, regions=regions,
                    incremental_FFs=sum(v['FFs']-depth for v in regions.values()),
                    required_rtl_sources=RESET_FOREST_RTL,
                    scope='Source leaf allocation only. Scalar child internals, actual parameter binding, native reset phase/reach and all clock entries remain unqualified.')

    def emit(self, P, top_lp, mut=True):
        S, D, E, K, AW = self.S, self.D, self.E, self.K, self.AW
        rr, hops, RB = self.reset_tree()
        forest = self.reset_forest_plan(P)
        L = []
        w = L.append
        # header
        items = [full_item(p) for p in self.mod["ports"] if p["name"] not in self.ck]
        items += [f"input wire ck_{r}" for r in self.regions]
        par = (self.mod["params_txt"] + ",\n    " if self.mod["params_txt"] and self.mod["params_txt"].strip() else "")
        w("`timescale 1ns/1ps")
        w(f"// GENERATED by tools/landed_parent/lp.py from {S['top']} ({', '.join(S['sources'])}) -- do not edit.")
        w(f"// LANDED PARENT (PARENTS-LANDED 10-18): {len(self.regions)} clock regions ({', '.join(self.regions)}), "
          f"{len(P['lands'])} landed crossings (D {D}, E = K = {E}, +{self.A} edges each), {len(P['pads'])} alignment pads,")
        w(f"// regional reset runs depth {RB} (+ t(child) per child).  Record: {S.get('record_dir', S['out_dir'])}/{top_lp}_record.json")
        w(f"// MUT (bench only; 0 in every kit): 1 = landing 0 bypassed, 2 = landing 0 read K+1, 3 = pad 0 one stage short,")
        w(f"//     4 = child reset run of '{self.mut_child(P)}' {int(S.get('mut4_stages', 1))} stage(s) long")
        w(f"module {top_lp} #(\n    {par}parameter integer MUT = 0\n) (\n    " + ",\n    ".join(items) + "\n);")
        body = self.mod["body"]
        # strip instance statements; they are re-emitted below
        keep, pos = [], 0
        for ins in self.insts:
            keep.append(body[pos:ins["span"][0]])
            pos = ins["span"][1]
        keep.append(body[pos:])
        oregs = P.get("oregs") or {}
        def oren(txt):      # out_regs ports: the flat body drives <p>__o; the region register drives the port
            for p in oregs:
                txt = re.sub(rf"(?<![\w$.]){re.escape(p)}\b", f"{p}__o", txt)
            return txt
        for p in sorted(oregs):         # declared before the flat body that drives them
            w(f"    wire {self.ports[p]['range'] or ''} {p}__o;   // out_regs: flat driver of {p}")
        for chunk in keep:
            for line in oren(chunk).splitlines():
                if line.strip():
                    w(line.rstrip())
        for p, k in sorted(oregs.items()):
            rng = self.ports[p]["range"]
            w(f"    // ---- OUTPUT REGISTER {p}: +{k} edge(s) in region {P['nreg'][f'port:{p}']} (out_regs; port offset +{k})")
            w(f"    ot_pl_pad #(.W({width_text(rng)}), .N({k})) u_lpo_{p} "
              f"(.ck(ck_{P['nreg'][f'port:{p}']}), .d({p}__o), .q({p}));")
        # reset tree
        w(f"    // ---- regional reset runs (1-bit plain hops: they define the landing epochs; region {rr} holds the root)")
        w(f"    wire lpr_root;  ot_pl_pad #(.W(1), .N(1)) u_lpr_root (.ck(ck_{rr}), .d({self.rst}), .q(lpr_root));")
        if forest:
            for r in self.regions:
                expression = '+'.join(forest['regions'][r]['terms'])
                w(f'    localparam integer LPR_LEAVES_{r} = {expression};')
            root_load_expr = ('+'.join(f'((LPR_LEAVES_{r}+31)/32)' for r in self.regions)
                              if RB-1 == 2 else str(len(self.regions)))
        for r in self.regions:
            if forest:
                w(f'    wire [LPR_LEAVES_{r}-1:0] lpr_{r}_leaves; wire lpr_{r} = lpr_{r}_leaves[0];')
                w(f'    ot_pl_land_reset_forest #(.DEPTH({RB-1}), .LEAVES(LPR_LEAVES_{r}), .ROOT_LOADS({root_load_expr})) u_lpr_{r} '
                  f'(.ck(ck_{r}), .d(lpr_root), .q(lpr_{r}_leaves)); // same reset age; physical reach unproved')
            else:
                w(f"    wire lpr_{r};  ot_pl_pad #(.W(1), .N({RB - 1})) u_lpr_{r} (.ck(ck_{r}), .d(lpr_root), .q(lpr_{r}));"
                  f"   // {hops[r]} hop(s) from {rr}")
        # landings
        sub = {}            # (inst, net) -> replacement net
        for Ld in P["lands"]:
            n, net, s, r = Ld["name"], Ld["net"], Ld["src_region"], Ld["dst_region"]
            rng = self.rng(net)
            wt = width_text(rng)
            primitive = "ot_pl_land_vector_reset" if forest else ("ot_pl_land_chunk" if self.chunk_bits else "ot_pl_land")
            def reset_input(role, region):
                if not forest:
                    return f'lpr_{region}'
                binding = next(v for v in forest['regions'][region]['bindings'] if v['landing']==n and v['role']==role)
                return f'lpr_{region}_leaves[({binding["first_expr"]}) +: {binding["chunks_expr"]}]'
            cp = f", .CHUNK_BITS({self.chunk_bits})" if self.chunk_bits else ""
            vld_hi = f"{D}*((({wt})+{self.chunk_bits}-1)/{self.chunk_bits})-1" if self.chunk_bits else str(D - 1)
            decl = rng or ""
            out = f"{net}__l_{r}" if "dst_inst" not in Ld else f"{net}__l_{Ld['dst_inst']}"
            g = Ld.get("ring_of", n)
            w(f"    // ---- LANDING {n}: {net} {s} -> {r}, {Ld['width']} b ({', '.join(Ld['readers'])})"
              + (f" -- reads ring {g}" if g != n else ""))
            if g == n:
                w(f"    wire [{D}*{wt}-1:0] lpl_{n}_bank;  wire [{D * (AW + 1) - 1}:0] lpl_{n}_epo;  wire [{vld_hi}:0] lpl_{n}_vld;"
                  f"  wire {decl} {out}, lpl_{n}_o;")
                w(f"    {primitive}_w #(.W({wt}), .D({D}){cp}) u_lpl_{n}_w (.ck(ck_{s}), .rsi({reset_input('w',s)}), .i({net}), "
                  f".bank(lpl_{n}_bank), .epo(lpl_{n}_epo), .vld(lpl_{n}_vld));")
            else:
                w(f"    wire {decl} {out}, lpl_{n}_o;")
            kk = f"(MUT == 2) ? {K + 1} : {K}" if n == "0" and mut else f"{K}"
            w(f"    {primitive}_r #(.W({wt}), .D({D}), .K({kk}){cp}) u_lpl_{n}_r (.ck(ck_{r}), .rsi({reset_input('r',r)}), "
              f".bank(lpl_{g}_bank), .epo(lpl_{g}_epo), .vld(lpl_{g}_vld), .o(lpl_{n}_o));")
            if Ld.get("unlanded_mutant"):
                w(f"    assign {out} = {net};   // --mut-unland: the region audit must FAIL on this crossing")
            elif n == "0" and mut:
                w(f"    assign {out} = (MUT == 1) ? {net} : lpl_{n}_o;")
            else:
                w(f"    assign {out} = lpl_{n}_o;")
            for rp in Ld["readers"]:
                sub[(rp.split(".")[0], net)] = out
        # pads
        for j, ((net, inst), k) in enumerate(sorted(P["pads"].items())):
            rng = self.rng(net)
            src = sub.get((inst, net), net)
            q = f"{net}__p_{inst}"
            kk = f"(MUT == 3) ? {k - 1} : {k}" if j == 0 and mut else f"{k}"
            w(f"    wire {rng or ''} {q};  ot_pl_pad #(.W({width_text(rng)}), .N({kk})) u_lpp_{j} (.ck(ck_{self.region[inst]}), "
              f".d({src}), .q({q}));   // align {inst}: +{k}")
            sub[(inst, net)] = q
        # child resets
        mc = self.mut_child(P)
        rsub = {}
        for ins in self.insts:
            i, r = ins["inst"], self.region[ins["inst"]]
            tc = P["t"].get(i, 0) + self.rx
            if any(self.cports[ins["module"]][pin] == "in" and pin in (S.get("reset_pins") or []) and ex.strip() == self.rst for pin, ex in ins["conns"].items()):
                m4 = int(S.get("mut4_stages", 1))
                kk = f"(MUT == 4) ? {tc + m4} : {tc}" if i == mc and mut else f"{tc}"
                w(f"    wire lpr_c_{i};  ot_pl_pad #(.W(1), .N({kk})) u_lprc_{i} (.ck(ck_{r}), .d(lpr_{r}), .q(lpr_c_{i}));"
                  + (f"   // t({i}) = {tc}" if not self.reference else f"   // reference schedule: held {tc} past the landing epochs"))
                rsub[i] = f"lpr_c_{i}"
        # Internal regional reset ports receive the same logical child delay as
        # the ordinary child reset, each on its own root. No reset/data mask.
        brsub = {}
        for (i,pin), binding in self.regional_bindings.items():
            if binding['role'] != 'resets':
                continue
            tc = P['t'].get(i, 0) + self.rx
            names = []
            for bit,r in enumerate(binding['regions']):
                name = f'lpr_b_{i}_{pin}_{bit}'
                kk = f'(MUT == 4) ? {tc+1} : {tc}' if i == mc and mut else str(tc)
                w(f'    wire {name}; ot_pl_pad #(.W(1), .N({kk})) u_lprb_{i}_{pin}_{bit} '
                  f'(.ck(ck_{r}), .d(lpr_{r}), .q({name}));')
                names.append(name)
            brsub[i,pin] = '{' + ', '.join(reversed(names)) + '}'
        # children
        w("    // ---- children (clock pins -> their region root; reset pins -> their reset run; landed / padded inputs)")
        for ins in self.insts:
            i, r = ins["inst"], self.region[ins["inst"]]
            cs = []
            for pin, ex in ins["conns"].items():
                binding = self.regional_bindings.get((i,pin))
                if binding:
                    ex = ('{' + ', '.join('ck_'+r for r in reversed(binding['regions'])) + '}'
                          if binding['role']=='clocks' else brsub[i,pin])
                elif pin in (S.get("clock_pins") or []) and idents(ex) & self.ck:
                    cw = self.cwidth[ins["module"]].get(pin, 1)
                    ex = f"ck_{r}" if cw == 1 else f"{{{cw}{{ck_{r}}}}}"
                elif i in rsub and self.cports[ins["module"]][pin] == "in" and pin in (S.get("reset_pins") or []) and ex.strip() == self.rst:
                    ex = rsub[i]
                elif self.cports[ins["module"]][pin] == "in":
                    for (si, net), rep in sub.items():
                        if si == i:
                            ex = re.sub(rf"(?<![\w$]){re.escape(net)}\b", rep, ex)
                if self.cports[ins["module"]][pin] == "out":
                    ex = oren(ex)
                cs.append(f".{pin}({ex})")
            hard = S.get("synthesis_hard_instances", [])
            if i in hard and ins["params"]:
                w(f"    {ins['module']}")
                w("`ifndef SYNTHESIS")
                w(f"    {ins['params']}")
                w("`endif")
                w(f"    {i} (" + ", ".join(cs) + f");   // region {r}, t = {P['t'].get(i, 0)}")
            else:
                w(f"    {ins['module']} {ins['params'] + ' ' if ins['params'] else ''}{i} (" + ", ".join(cs) + f");   // region {r}, t = {P['t'].get(i, 0)}")
        w("endmodule")
        return "\n".join(L) + "\n", dict(reset_region=rr, hops=hops, RB=RB)

    def mut_child(self, P):
        kids = [ins["inst"] for ins in self.insts
                if any(self.cports[ins["module"]][pin] == "in" and pin in (self.S.get("reset_pins") or []) and ex.strip() == self.rst for pin, ex in ins["conns"].items())]
        want = self.S.get("mut_child")       # a child whose late reset is observable after warm-up (state that outlives
        if want:                             # the reset, e.g. a sticky flag); a pure pipeline child forgets it in 1 edge
            if want not in kids:
                raise SystemExit(f"mut_child {want} is not a child with a reset pin on {self.rst}: {kids}")
            return want
        return kids[0] if kids else None

    def sdc(self, P, top_lp):
        S, D, E = self.S, self.D, self.E
        core, rest = self.regions[0], self.regions[1:]
        res = int(S.get("residual_ps", 60))
        clk = {r: ("core_clk" if r == core else f"ck_{r}") for r in self.regions}
        rr, hops, RB = self.reset_tree()
        o = [f"# GENERATED by tools/landed_parent/lp.py for {top_lp} (PARENTS-LANDED): regional roots, landing multicycles.",
             "# Every region root: same period as core_clk (related, neighbour-relative die delivery).",
             "set ot_lp_per [get_property [get_clocks core_clk] period]"]
        o += [f"create_clock -name ck_{r} -period $ot_lp_per [get_ports ck_{r}]" for r in rest]
        if rest:
            lst = " ".join(f"ck_{r}" for r in rest)
            o += [f"set_clock_uncertainty -setup 60 [get_clocks {{{lst}}}]", f"set_clock_uncertainty -hold 25 [get_clocks {{{lst}}}]"]
        o.append(f"# 1-bit reset runs {rr} -> every region: single-cycle with the {res}-ps die residual on top of 60 / 25")
        for r in self.regions:
            if r != rr:
                for f_, t_ in ((rr, r), (r, rr)):
                    o.append(f"set_clock_uncertainty -setup {60 + res} -from [get_clocks {clk[f_]}] -to [get_clocks {clk[t_]}]")
                    o.append(f"set_clock_uncertainty -hold {25 + res} -from [get_clocks {clk[f_]}] -to [get_clocks {clk[t_]}]")
        if P["lands"] and not self.direct_timing:
            o.append(f"# {len(P['lands'])} landings (LANDING-CONTRACT L5): ring -> read multicycle -setup {E} -hold {D - 1}, "
                     f"window ({E} - {D}) T + t_hold < dL < {E} T - t_cq - t_setup")
            shared = any(L.get("ring_of", L["name"]) != L["name"] for L in P["lands"])
            if shared:      # share_rings: (ring, read) pairs; the ring of landing n is u_lpl_<ring_of>_w
                o.append("set ot_lp_pairs {" + " ".join(f"{L.get('ring_of', L['name'])} {L['name']}" for L in P["lands"]) + "}")
                o.append("set ot_lp_lands {}; foreach {ot_lw ot_ln} $ot_lp_pairs { lappend ot_lp_lands $ot_ln; set ot_lp_ring($ot_ln) $ot_lw }")
            else:
                o.append("set ot_lp_lands {" + " ".join(L["name"] for L in P["lands"]) + "}")
            o += ["set ot_lp_miss 0", "foreach ot_ln $ot_lp_lands {"]
            if shared:
                o += ["  set ot_lw $ot_lp_ring($ot_ln)",
                      "  set ot_lf [get_cells -quiet u_lpl_${ot_lw}_w.*]",
                      "  set ot_lt [get_cells -quiet u_lpl_${ot_ln}_r.*]",
                      "  if {[llength $ot_lf] == 0} { set ot_lf [get_cells -quiet u_lpl_${ot_lw}_w/*] }",
                      "  if {[llength $ot_lt] == 0} { set ot_lt [get_cells -quiet u_lpl_${ot_ln}_r/*] }"]
            else:
                o += ["  set ot_lf [get_cells -quiet u_lpl_${ot_ln}_w.*]",
                      "  set ot_lt [get_cells -quiet u_lpl_${ot_ln}_r.*]",
                      "  if {[llength $ot_lf] == 0} { set ot_lf [get_cells -quiet u_lpl_${ot_ln}_w/*] }",
                      "  if {[llength $ot_lt] == 0} { set ot_lt [get_cells -quiet u_lpl_${ot_ln}_r/*] }"]
            o += ["  if {[llength $ot_lf] == 0 || [llength $ot_lt] == 0} { incr ot_lp_miss; continue }",
                  f"  set_multicycle_path -setup {E} -from $ot_lf -to $ot_lt",
                  f"  set_multicycle_path -hold {D - 1} -from $ot_lf -to $ot_lt", "}",
                  'puts "OT_LP_LAND_SDC [expr {[llength $ot_lp_lands] - $ot_lp_miss}] of [llength $ot_lp_lands] landings constrained"']
        if P["lands"] and self.direct_timing:
            o.append("# D4/E2 directly timed landing: supported compensated phase +/-0.75T; "
                     "sample age1.25..2.75T, overwrite gap>=1.25T.")
            o.append(f"# Conservative quarter-T setup envelope; ordinary60ps/25ps plus residual{res}ps remains charged. No data exceptions.")
            pairs = sorted({(L["src_region"], L["dst_region"]) for L in P["lands"]})
            for a, b in pairs:
                for f_, t_ in ((a, b), (b, a)):
                    o.append(f"set_clock_uncertainty -setup -from [get_clocks {clk[f_]}] "
                             f"-to [get_clocks {clk[t_]}] [expr {{{60 + res}.0 + 0.75 * $ot_lp_per}}]")
                    o.append(f"set_clock_uncertainty -hold -from [get_clocks {clk[f_]}] "
                             f"-to [get_clocks {clk[t_]}] {25 + res}.0")
        for p in self.mod["ports"]:
            n = p["name"]
            if n in self.ck or n in self.static or n == self.rst:
                continue
            r = P["nreg"].get(f"port:{n}", core)
            if r == core:
                continue
            k = "input" if p["dir"] == "in" else "output"
            o.append(f"set_{k}_delay [expr {{0.2 * $ot_lp_per}}] -clock ck_{r} [get_ports {{{n}{'[*]' if p['range'] else ''}}}]")
        if rest:
            o.append(f"if {{!$::ot_ref_pre_cts}} {{ set_propagated_clock [get_clocks {{{' '.join(f'ck_{r}' for r in rest)}}}] }}")
        for n in sorted(self.static):
            if n in self.ports:
                o.append(f"set_case_analysis 0 [get_ports {{{n}{'[*]' if self.ports[n]['range'] else ''}}}]   ;# identity strap")
        return "\n".join(o) + "\n"

    def record(self, P, top_lp, rt):
        S = self.S
        t = P["t"]
        flops_land = sum((self.D * L["width"] + self.D + (self.AW + 1) + 1 if L.get("ring_of", L["name"]) == L["name"] else 0)
                         + L["width"] + (self.AW + 1) + 2 for L in P["lands"])
        if self.chunk_bits:
            # Every extra kept chunk owns writer/read counters and physical valid
            # bits. Only assertion epoch tags are shared; data storage is unchanged.
            flops_land += sum((math.ceil(L["width"] / self.chunk_bits) - 1) *
                              ((self.D + self.AW + 2 if L.get("ring_of", L["name"]) == L["name"] else 0) + self.AW + 3)
                              for L in P["lands"])
            flops_land += sum(math.ceil(L["width"] / self.chunk_bits) * self.D *
                              (2 if L.get("ring_of", L["name"]) == L["name"] else 1) for L in P["lands"])
        flops_pad = sum(eval_width(self.rng(n), self.env) * k for (n, _), k in P["pads"].items())
        flops_oreg = sum(eval_width(self.ports[p]["range"], self.env) * k for p, k in (P.get("oregs") or {}).items())
        flops_rst = 1 + len(self.regions) * (rt["RB"] - 1) + sum(t.get(i["inst"], 0) + self.rx for i in self.insts if any(
            pin in (S.get("reset_pins") or []) and ex.strip() == self.rst for pin, ex in i["conns"].items()))
        # emit() creates a distinct W1 u_lprb pad for EVERY regional reset
        # vector bit, in addition to the ordinary scalar child reset pad.
        regional_reset_pads = [dict(instance=i, pin=pin, bit=bit,
                                   stages=t.get(i, 0) + self.rx)
            for (i, pin), binding in self.regional_bindings.items()
            if binding['role'] == 'resets' for bit in range(len(binding['regions']))]
        regional_reset_FFs = sum(pad['stages'] for pad in regional_reset_pads)
        flops_rst += regional_reset_FFs
        forest = self.reset_forest_plan(P)
        if forest:
            flops_rst += forest['incremental_FFs']
        pairs = sorted({"-".join(sorted((L["src_region"], L["dst_region"]))) for L in P["lands"]})
        rpairs = sorted({"-".join(sorted((rt["reset_region"], r))) for r in self.regions if r != rt["reset_region"]})
        port_in = {p["name"]: t.get(f"port:{p['name']}", 0) for p in self.mod["ports"]
                   if p["dir"] == "in" and p["name"] not in self.ck | self.preserve_ck | self.static | {self.rst, self.reset_port}}
        port_out = {p["name"]: t.get(f"port:{p['name']}", 0) for p in self.mod["ports"] if p["dir"] == "out"}
        no_rst = [i["inst"] for i in self.insts if t.get(i["inst"], 0) and not any(
            self.cports[i["module"]][pin] == "in" and pin in (S.get("reset_pins") or []) and ex.strip() == self.rst for pin, ex in i["conns"].items())]
        return dict(
            lane="PARENTS-LANDED", generator="tools/landed_parent/lp.py", flat=S["top"], top=top_lp,
            standard="landed-regions-standard-1018: local region trees, every cross-region net LANDED, per-region "
                     "child-flop gate (TT and FF <= 80 ps); 1-bit reset runs are the only plain cross-region hops",
            preserved_clock_ports=sorted(self.preserve_ck),
            regions={r: dict(clock_port=f"ck_{r}", children=sorted(i for i, rg in self.region.items() if rg == r))
                     for r in self.regions},
            D=self.D, E=self.E, K=self.K, added_edges_per_landing=self.A,
            window=("direct quarter-T setup envelope; D4/E2 sample age1.25..2.75T at compensated phase +/-0.75T; "
                    "overwrite gap>=1.25T at TT/FF" if self.direct_timing else
                    f"({self.E} - {self.D}) T + t_hold < dL < {self.E} T - t_cq - t_setup at TT and FF"),
            landings=[dict(L, ring=f"u_lpl_{L.get('ring_of', L['name'])}_w (ck_{L['src_region']})",
                           read=f"u_lpl_{L['name']}_r (ck_{L['dst_region']})", added_edges=self.A,
                           sdc=(f"direct related-root quarter-T setup envelope, setup60+res{S.get('residual_ps', 60)}ps, hold25+res" if self.direct_timing else f"set_multicycle_path -setup {self.E} / -hold {self.D - 1} -from u_lpl_{L.get('ring_of', L['name'])}_w.* "
                               f"-to u_lpl_{L['name']}_r.*"))
                      for L in P["lands"]],
            pads=[dict(net=n, reader=i, stages=k) for (n, i), k in sorted(P["pads"].items())],
            loose_status=dict(nets=sorted(self.loose), lag=P.get("loose_lag", []),
                              sticky_outputs=S.get("sticky_outputs") or {},
                              note="sticky status flags (no reservation / valid / payload effect): landed, outside the "
                                   "offset solve; the reader sees each flag lag_edges later than the flat parent"),
            reset=dict(port=self.reset_port, net=S.get("reset_net"), root_region=rt["reset_region"], depth=rt["RB"], hops=rt["hops"],
                       **(dict(same_depth_forest=forest) if forest else {}),
                       **(dict(regional_vector_padding_FFs=regional_reset_FFs,
                               regional_vector_padding=regional_reset_pads) if regional_reset_pads else {}),
                       note="flat reference == landed parent with its reset delayed by depth; child c's reset run is "
                            "depth + t(c)"),
            flops=dict(landing=flops_land, pads=flops_pad, reset=flops_rst, **({"out_regs": flops_oreg} if flops_oreg else {})),
            **({"out_regs": [dict(port=p, stages=k, region=P["nreg"][f"port:{p}"], inst=f"u_lpo_{p}")
                             for p, k in sorted(P["oregs"].items())]} if P.get("oregs") else {}),
            communicating_region_pairs=dict(landed=pairs, reset_hops=rpairs),
            compiler=dict(
                note="every latency change vs the flat parent; the compiler schedule takes these (static calendar, no "
                     "runtime flow control)",
                child_offset_edges={i["inst"]: t.get(i["inst"], 0) for i in self.insts},
                input_port_offset_edges=port_in, output_port_offset_edges=port_out,
                reset_release_added_edges=rt["RB"] + self.rx,
                status_flag_lag_edges={f"{x['net']}->{x['reader']}": x["lag_edges"] for x in P.get("loose_lag", [])},
                schedule=("reference: cross-region loops re-scheduled; the landed parent == the flat parent with ref_params "
                          "(+E+1 per landed crossing on that path), reset delayed reset_release_added_edges, ports at offset 0"
                          if self.reference else "offsets"),
                ref_params=dict(S.get("ref_params") or S.get("params") or {}) if self.reference else None,
                **({} if not P.get("lag") else dict(status_lag_edges={
                    b: dict(lag=k, pins=sorted({e[5] for e in P["lagged"] if e[1] == b}),
                            note="these status-return inputs reach the reader lag edges after its own time "
                                 "(flat == <top>_lagref: the reader's outputs carry that status lag edges "
                                 "later than in the flat parent)") for b, k in sorted(P["lag"].items())})),
                rescheduled_nets=([dict(net=L["net"], src_region=L["src_region"], dst_region=L["dst_region"],
                                        readers=L["readers"], width=L["width"], added_edges=self.A) for L in P["lands"]]
                                  if P.get("resched") else []),
                reschedule_note=("RESCHEDULE mode: cross-region loops; every child keeps its flat calendar (t = 0) and "
                                 f"each landed net above arrives +{self.A} edges later than in the flat parent: the "
                                 "compiler / the children's static calendars must absorb these" if P.get("resched") else None),
                max_added_edges=max([0] + list(port_out.values()))),
            **({} if not (S.get("bench") or {}).get("mut_waivers") else dict(mutant_waivers=S["bench"]["mut_waivers"])),
            warnings=[f"child {i} runs t = {t[i]} edges late but has no reset pin on {self.rst}: its free-running state "
                      "is NOT re-aligned (check it in the bench)" for i in no_rst],
            **({} if not (self.chunk_bits or self.direct_timing) else dict(
                landing_implementation=dict(chunk_bits=self.chunk_bits, direct_quarter_period_timing=self.direct_timing,
                                            compensated_phase_T=[-0.75, 0.75], sample_age_T=[1.25, 2.75],
                                            overwrite_gap_min_T=1.25))),
            **({} if not self.regional_bindings else dict(
                regional_child_bindings=[dict(inst=i,pin=p,role=b['role'],
                    bits=[dict(bit=j,region=r,clock_port='ck_'+r,
                               reset_net=(f'lpr_b_{i}_{p}_{j}' if b['role']=='resets' else None),
                               reset_delay_edges=(t.get(i,0)+self.rx if b['role']=='resets' else None))
                          for j,r in enumerate(b['regions'])])
                    for (i,p),b in sorted(self.regional_bindings.items())],
                internal_crossing_obligation='Vector binding is clock/reset connectivity only. Every declared root must appear in native entry and internal crossing audits; no internal datapath coverage is implied.')),
            die_obligations=[
                "drop one clock per region at the region's clock port (ck_<r>); each region builds its own local tree",
                "communicating regions (landed pairs) need NO phase alignment inside the landing window at TT and FF",
                f"reset-hop pairs {rpairs}: region skew within about +/-400 ps at TT and FF (1-bit single-cycle hops)",
                "boundary ports are timed against the region in port_regions / the record; die links into them land on THAT clock"])

    def tb(self, P, top_lp, rt):
        S = self.S
        B = S.get("bench") or {}
        cyc, rcy = int(B.get("cycles", 2000)), int(B.get("reset_cycles", 16))
        RB = rt["RB"] + self.rx
        t = P["t"]
        act_low = S.get("reset_active_low", True)
        ins = [p for p in self.mod["ports"] if p["dir"] == "in" and p["name"] not in self.ck | self.preserve_ck and p["name"] != self.reset_port]
        outs = [p for p in self.mod["ports"] if p["dir"] == "out"]
        W = {p["name"]: eval_width(p["range"], self.env) for p in self.mod["ports"]}
        maxoff = max([0] + [t.get(f"port:{p['name']}", 0) for p in outs] + [t.get(f"port:{p['name']}", 0) for p in ins]
                     + [int(v) for v in (S.get("sticky_outputs") or {}).values()])
        warm = rcy + RB + maxoff + self.A + 8
        tbs = S.get("tb_static") or {}
        sticky = {k: int(v) for k, v in (S.get("sticky_outputs") or {}).items()}
        L = ["`timescale 1ns/1ps", f"// GENERATED by tools/landed_parent/lp.py: lockstep {S['top']} (flat, reset delayed {RB}) vs "
             f"{top_lp}; every input presented off_in edges later, every output compared off_out edges later.",
             f"module tb_{top_lp};", "    parameter integer MUT = 0;", "    reg clk = 1'b0;  always #0.5 clk = ~clk;",
             f"    reg rst = {'1' if not act_low else '0'};  reg [{RB - 1}:0] rst_dl;",
             f"    wire rst_f = rst_dl[{RB - 1}];",
             f"    always @(posedge clk) rst_dl <= {{rst_dl[{max(RB - 2, 0)}:0], rst}};" if RB > 1 else "    always @(posedge clk) rst_dl <= rst;"]
        for p in ins:
            n, w_ = p["name"], W[p["name"]]
            off = t.get(f"port:{n}", 0)
            L.append(f"    reg [{w_ - 1}:0] fi_{n};")
            if n in self.static:
                L.append(f"    wire [{w_ - 1}:0] li_{n} = fi_{n};")
            else:
                L.append(f"    reg [{w_ - 1}:0] dli_{n} [0:{off}];  wire [{w_ - 1}:0] li_{n} = "
                         f"{('dli_' + n + '[' + str(off - 1) + ']') if off else ('fi_' + n)};")
                L.append(f"    always @(posedge clk) begin : g_dli_{n} integer j; dli_{n}[0] <= fi_{n}; "
                         f"for (j = 1; j <= {off}; j = j + 1) dli_{n}[j] <= dli_{n}[j - 1]; end")
        for p in outs:
            n, w_ = p["name"], W[p["name"]]
            off = t.get(f"port:{n}", 0)
            dep = off + sticky.get(n, 0)
            L.append(f"    wire [{w_ - 1}:0] fo_{n}, lo_{n};  reg [{w_ - 1}:0] dlo_{n} [0:{dep}];")
            L.append(f"    always @(posedge clk) begin : g_dlo_{n} integer j; dlo_{n}[0] <= fo_{n}; "
                     f"for (j = 1; j <= {dep}; j = j + 1) dlo_{n}[j] <= dlo_{n}[j - 1]; end")
        ck = sorted(self.ck | self.preserve_ck)
        fc = [f".{c}(clk)" if W.get(c, 1) == 1 else f".{c}({{{W[c]}{{clk}}}})" for c in ck] + [f".{self.reset_port}({'rst' if S.get('reset_net') else 'rst_f'})"] + [f".{p['name']}(fi_{p['name']})" for p in ins] + \
             [f".{p['name']}(fo_{p['name']})" for p in outs]
        lc = [f".ck_{r}(clk)" for r in self.regions] + [f".{c}({{{W[c]}{{clk}}}})" for c in sorted(self.preserve_ck)] + [f".{self.reset_port}(rst)"] + [f".{p['name']}(li_{p['name']})" for p in ins] + \
             [f".{p['name']}(lo_{p['name']})" for p in outs]
        pv = ", ".join(f".{k}({v})" for k, v in (S.get("params") or {}).items())
        pr = ", ".join(f".{k}({v})" for k, v in ((S.get("ref_params") if self.reference else None) or S.get("params") or {}).items())
        ref = (S["top"] + "_rsref") if P.get("resched") else (S["top"] + "_lagref" if P.get("lag") else S["top"])
        L.append(f"    {ref} {('#(' + pr + ') ') if pr else ''}u_flat (" + ", ".join(fc) + ");")
        L.append(f"    {top_lp} #({(pv + ', ') if pv else ''}.MUT(MUT)) u_lp (" + ", ".join(lc) + ");")
        L.append("    function [31:0] rnd; input integer k; rnd = $urandom; endfunction")
        if S.get("tb_stimulus"):
            return self.tb_scripted(L, outs, t, warm, sticky, W)
        L.append("    integer cyc, nc, bad;")
        L.append("    initial begin")
        L.append("        nc = 0; bad = 0;")
        for p in ins:
            n = p["name"]
            v = tbs.get(n)
            L.append(f"        fi_{n} = {v if v is not None else '{' + ','.join(['$urandom'] * ((W[n] + 31) // 32)) + '}'};")
        L.append(f"        for (cyc = 0; cyc < {cyc}; cyc = cyc + 1) begin")
        L.append("            @(negedge clk);")
        L.append(f"            if (cyc == {rcy}) rst = {'1' if act_low else '0'};")
        tbx = B.get("expr") or {}
        for p in ins:
            n = p["name"]
            if n not in self.static:
                L.append(f"            fi_{n} = " + (f"{tbx[n]};" if n in tbx else f"{{{','.join(['$urandom'] * ((W[n] + 31) // 32))}}};"))
        L.append(f"            if (cyc > {warm}) begin")
        for p in outs:
            n = p["name"]
            off = t.get(f"port:{n}", 0)
            ref = f"dlo_{n}[{off - 1}]" if off > 0 else f"fo_{n}"
            if n in sticky:
                lagref = f"dlo_{n}[{off + sticky[n] - 1}]" if off + sticky[n] > 0 else f"fo_{n}"
                L.append(f"                nc = nc + 1; if (((lo_{n} & ~{ref}) | ({lagref} & {ref} & ~lo_{n})) !== 0) begin bad = bad + 1; "
                         f"if (bad <= 5) $display(\"LP_MISMATCH sticky port={n} cycle=%0d flat=%h landed=%h\", cyc, {ref}, lo_{n}); end")
                continue
            L.append(f"                nc = nc + 1; if (lo_{n} !== {ref}) begin bad = bad + 1; "
                     f"if (bad <= 5) $display(\"LP_MISMATCH port={n} cycle=%0d flat=%h landed=%h\", cyc, {ref}, lo_{n}); end")
        L.append("            end")
        cls = B.get("child_lockstep") or []
        if cls:
            if not self.reference:
                raise SystemExit("bench.child_lockstep needs schedule 'reference' (children are not time-shifted there)")
            ckp = set(S.get("clock_pins") or [])
            rsp = set(S.get("reset_pins") or [])
            hit = [i for i in self.insts if any(fnmatch.fnmatchcase(i["inst"], q) for q in cls)]
            if not hit:
                raise SystemExit(f"bench.child_lockstep {cls} matches no child")
            for i in hit:
                for pin in sorted(i["conns"]):
                    if pin in ckp:
                        continue
                    f_, l_ = f"u_flat.{i['inst']}.{pin}", f"u_lp.{i['inst']}.{pin}"
                    gate = f"cyc > {rcy}" if pin in rsp else f"cyc > {warm}"
                    L.append(f"            if ({gate}) begin nc = nc + 1; if ({l_} !== {f_}) begin bad = bad + 1; "
                             f"if (bad <= 5) $display(\"LP_MISMATCH child={i['inst']}.{pin} cycle=%0d flat=%h landed=%h\", "
                             f"cyc, {f_}, {l_}); end end")
        L.append("        end")
        L.append(f"        if (bad == 0 && nc > 0) $display(\"LP_LOCKSTEP PASS MUT=%0d compared=%0d cycles={cyc} warm={warm}\", MUT, nc);")
        L.append("        else $display(\"LP_LOCKSTEP FAIL MUT=%0d mismatches=%0d of %0d\", MUT, bad, nc);")
        L.append("        $finish;")
        L.append("    end")
        L.append("endmodule")
        if P.get("resched"):
            L.append(self.rsref(P))
        return "\n".join(L) + "\n"

    def tb_scripted(self, L, outs, t, warm, sticky, W):
        """spec tb_stimulus: a module-level include that drives fi_<port> (and rst, released at bench.reset_cycles) with a
        real programme instead of random words, and calls lp_finish; the compare runs every negedge after warm"""
        S = self.S
        L.append("    integer cyc = 0, nc = 0, bad = 0;")
        L.append("    always @(negedge clk) begin")
        L.append("        cyc <= cyc + 1;")
        L.append(f"        if (cyc > {warm}) begin")
        for p in outs:
            n = p["name"]
            off = t.get(f"port:{n}", 0)
            ref = f"dlo_{n}[{off - 1}]" if off > 0 else f"fo_{n}"
            if n in sticky:
                lagref = f"dlo_{n}[{off + sticky[n] - 1}]" if off + sticky[n] > 0 else f"fo_{n}"
                L.append(f"            nc = nc + 1; if (((lo_{n} & ~{ref}) | ({lagref} & {ref} & ~lo_{n})) !== 0) begin bad = bad + 1; "
                         f"if (bad <= 5) $display(\"LP_MISMATCH sticky port={n} cycle=%0d flat=%h landed=%h\", cyc, {ref}, lo_{n}); end")
            else:
                L.append(f"            nc = nc + 1; if (lo_{n} !== {ref}) begin bad = bad + 1; "
                         f"if (bad <= 5) $display(\"LP_MISMATCH port={n} cycle=%0d flat=%h landed=%h\", cyc, {ref}, lo_{n}); end")
        L.append("        end")
        L.append("    end")
        L.append("    task lp_finish; input [8*48-1:0] what; begin")
        L.append("        if (bad == 0 && nc > 0) $display(\"LP_LOCKSTEP PASS MUT=%0d compared=%0d cycles=%0d warm=" + str(warm) + " stimulus=%0s\", MUT, nc, cyc, what);")
        L.append("        else $display(\"LP_LOCKSTEP FAIL MUT=%0d mismatches=%0d of %0d stimulus=%0s\", MUT, bad, nc, what);")
        L.append("        $finish; end endtask")
        L.append(f"    `include \"{S['tb_stimulus']}\"")
        L.append("endmodule")
        return "\n".join(L) + "\n"

    def bench_sh(self, top_lp, rel_out, P=None):
        muts = [0] + ([1, 2] if P and P["lands"] else []) + ([3] if P and P["pads"] else []) + ([4] if self.mut_child(P) else [])
        waived = {int(k): v for k, v in ((self.S.get("bench") or {}).get("mut_waivers") or {}).items()}
        muts = [m for m in muts if m not in waived]
        up = "/".join([".."] * len(Path(rel_out).parts))
        srcs = " ".join(self.S["sources"] + self.S.get("child_sources", []) + [LIB_RTL] +
                        (RESET_FOREST_RTL if self.reset_forest else []) +
                        ([f"{rel_out}/{self.S['top']}_lagref.sv"] if P and P.get("lag") else []))
        defs = " ".join(f"-D{d}" for d in self.S.get("defines") or [])
        return f"""#!/usr/bin/env bash
# GENERATED by tools/landed_parent/lp.py: lockstep bench {self.S['top']} (flat) vs {top_lp} + mutants {muts[1:]} + region audit.
# Run on the FLEET (ot-run), never on localhost.  Exit 0 iff MUT 0 PASSES, every mutant FAILS and the audit PASSES.
#   bash {rel_out}/{top_lp}_bench.sh OUTDIR        (SIM=iverilog default | verilator; VERILATOR, VL_JOBS, VL_EXTRA,
#   MUTS="0 1 .." optional overrides)
set -u
cd "${{LP_ROOT:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/{up}" && pwd))}}"
OUT=${{1:-lp_bench_out}}; mkdir -p "$OUT"; SIM=${{SIM:-iverilog}}; rc=0
SRCS="{srcs} {rel_out}/{top_lp}.sv {rel_out}/tb_{top_lp}.sv"
python3 tools/landed_parent/lp.py audit {self.S['_spec_path']} > "$OUT/audit.log" 2>&1 && echo "AUDIT PASS" || {{ echo "AUDIT FAIL"; rc=1; }}
python3 tools/landed_parent/lp.py audit {self.S['_spec_path']} --rtl "$OUT/unland.sv" --make-unland > "$OUT/audit_unland.log" 2>&1 \\
  && {{ echo "AUDIT-UNLAND PASSED (should FAIL)"; rc=1; }} || echo "AUDIT-UNLAND FAIL (expected)"
for m in ${{MUTS:-{" ".join(map(str, muts))}}}; do
  if [ "$SIM" = verilator ]; then
    ${{VERILATOR:-verilator}} --binary -j ${{VL_JOBS:-8}} -I. -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -O1 ${{VL_EXTRA:-}} --top-module tb_{top_lp} -GMUT=$m {defs} $SRCS -Mdir "$OUT/obj$m" > "$OUT/build_$m.log" 2>&1 \\
      && "$OUT/obj$m/Vtb_{top_lp}" > "$OUT/mut$m.log" 2>&1
  else
    iverilog -g2012 -I. -o "$OUT/sim$m" -s tb_{top_lp} -Ptb_{top_lp}.MUT=$m {defs} $SRCS > "$OUT/build_$m.log" 2>&1 \\
      && vvp -n "$OUT/sim$m" > "$OUT/mut$m.log" 2>&1
  fi
  r=$(grep -o 'LP_LOCKSTEP [A-Z]*' "$OUT/mut$m.log" 2>/dev/null | head -1)
  echo "MUT $m: ${{r:-NO_RESULT (see $OUT/build_$m.log)}}"
  if [ $m -eq 0 ]; then [ "$r" = "LP_LOCKSTEP PASS" ] || rc=1; else [ "$r" = "LP_LOCKSTEP FAIL" ] || rc=1; fi
done
echo "BENCH_EXIT $rc"; exit $rc
"""


# ------------------------------------------------------------------------------------------------------------- audit
def ckname(ex: str):
    """region clock of a child clock connection: ck_<r> or the replicated {W{ck_<r>}} (multi-bit clock pin)"""
    m = re.fullmatch(r"(ck_\w+)|\{\s*\d+\s*\{\s*(ck_\w+)\s*\}\s*\}", ex.strip())
    return (m.group(1) or m.group(2)) if m else None


def audit(spec: dict, rtl_text: str) -> dict:
    """R6 (as qwen_cluster/region_audit.py): in the GENERATED top every net whose driver and reader instances sit on
    different region clocks is (a) a landing's ring -> read bank / epo / vld or (b) a 1-bit reset run.  Everything else
    FAILS (an unlanded crossing)."""
    top_lp = spec.get("top_lp") or spec["top"] + "_lp"
    pre = preprocess(rtl_text, spec.get("defines"))
    pre = re.sub(r"\(MUT == \d+\) \? ([^:;]+?) : ([^;]+?);", r"\2;", pre)     # the kit elaborates MUT = 0
    mod = parse_module(pre, top_lp)
    _, assigns, insts = parse_body(mod["body"])
    csrc = "\n".join(preprocess((ROOT / f).read_text(errors="replace"), spec.get("defines")) for f in spec.get("child_sources", []))
    dirs = dict(LIB_PORTS)
    for i in insts:
        if i["module"] not in dirs:
            dirs[i["module"]] = {p["name"]: p["dir"] for p in parse_module(csrc, i["module"])["ports"]}
    bindings = Parent(spec).regional_bindings if (spec.get('regional_child_clocks') or spec.get('regional_child_resets')) else {}
    for (name,pin), binding in bindings.items():
        child = next((i for i in insts if i['inst']==name), None)
        expected = ('{' + ','.join('ck_'+r for r in reversed(binding['regions'])) + '}'
                    if binding['role']=='clocks' else
                    '{' + ','.join(f'lpr_b_{name}_{pin}_{j}' for j in reversed(range(len(binding['regions'])))) + '}')
        if child is None or re.sub(r'\s+','',child['conns'].get(pin,'')) != expected:
            return dict(ok=False, fails=[f'{name}.{pin}: regional {binding["role"]} bit mapping differs from declared contract'])
    rcks = {f"ck_{r['name']}" for r in spec["regions"]}     # region clocks only (a parent port may be named ck_*)
    reg = {}
    for i in insts:
        cks = [ckname(ex) for pin, ex in i["conns"].items() if ckname(ex) in rcks and (i['inst'],pin) not in bindings]
        if not cks:
            # Existing forwarded-clock output stations belong to the external
            # interface domains, not to a fabricated local region clock.
            cks = [ex.strip() for pin, ex in i["conns"].items()
                   if pin in (spec.get("clock_pins") or [])
                   and dirs[i["module"]].get(pin) == "in"
                   and idents(ex) & set(spec.get("preserve_clock_ports") or [])]
        if len(set(cks)) != 1:
            return dict(ok=False, fails=[f"{i['inst']}: clock pins on {sorted(set(cks)) or 'no region clock'}"])
        reg[i["inst"]] = cks[0][3:] if cks[0].startswith("ck_") else "external:" + cks[0]
    drv = {}
    for i in insts:
        for pin, ex in i["conns"].items():
            if dirs[i["module"]].get(pin) == "out":
                for n in idents(ex):
                    drv.setdefault(n, set()).add(i["inst"])
    for _ in range(len(assigns) + 1):
        for lhs, rhs in assigns:
            src = set().union(*(drv.get(n, set()) for n in rhs)) if rhs else set()
            for n in lhs:
                drv[n] = drv.get(n, set()) | src
    fails, landed, rst = [], 0, 0
    for i in insts:
        for pin, ex in i["conns"].items():
            if dirs[i["module"]].get(pin) != "in" or ckname(ex) in rcks or (i['inst'],pin) in bindings:
                continue
            for n in idents(ex):
                for d in drv.get(n, ()):
                    if reg[d] == reg[i["inst"]]:
                        continue
                    di = next(x for x in insts if x["inst"] == d)
                    if di["module"] in ("ot_pl_land_w", "ot_pl_land_chunk_w", "ot_pl_land_vector_reset_w") and i["module"] in ("ot_pl_land_r", "ot_pl_land_chunk_r", "ot_pl_land_vector_reset_r") and \
                            (d[:-2] == i["inst"][:-2] or n in {f"lpl_{d[6:-2]}_{x}" for x in ("bank", "epo", "vld")}):
                        landed += pin == "bank"
                    elif n.startswith("lpr_") and d.startswith("u_lpr_"):
                        rst += 1
                    else:
                        fails.append(f"UNLANDED {n}: {d} ({reg[d]}) -> {i['inst']}.{pin} ({reg[i['inst']]})")
    return dict(ok=not fails, landings=landed, reset_hops=rst, fails=fails)


# -------------------------------------------------------------------------------------------------------------- main
def load(path: str) -> dict:
    p = Path(path)
    S = json.loads(p.read_text())
    S["_spec_path"] = str(p.resolve().relative_to(ROOT)) if p.resolve().is_relative_to(ROOT) else str(p.resolve())
    return S


def gen(S: dict, mut_unland=False, rtl_out=None):
    Pm = Parent(S)
    top_lp = S.get("top_lp") or S["top"] + "_lp"
    P = Pm.plan(mut_unland=mut_unland)
    rtl, rt = Pm.emit(P, top_lp)
    out = ROOT / S["out_dir"]
    out.mkdir(parents=True, exist_ok=True)
    if rtl_out:
        Path(rtl_out).write_text(rtl)
        return P
    (out / f"{top_lp}.sv").write_text(rtl)
    if P.get("lag"):
        lt, ltxt = Pm.emit_lagref(P)
        (out / f"{lt}.sv").write_text(ltxt)
    (out / f"{top_lp}.sdc").write_text(Pm.sdc(P, top_lp))
    (out / f"tb_{top_lp}.sv").write_text(Pm.tb(P, top_lp, rt))
    sh = out / f"{top_lp}_bench.sh"
    sh.write_text(Pm.bench_sh(top_lp, S["out_dir"], P))
    sh.chmod(0o755)
    rec = Pm.record(P, top_lp, rt)
    rec["audit"] = audit(S, rtl)
    rd = ROOT / S.get("record_dir", S["out_dir"])
    rd.mkdir(parents=True, exist_ok=True)
    (rd / f"{top_lp}_record.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(f"{top_lp}: {len(P['lands'])} landings, {len(P['pads'])} pads, reset depth {rt['RB']}, flops {rec['flops']}, "
          f"audit {'PASS' if rec['audit']['ok'] else 'FAIL'}; outputs in {out}")
    for x in rec["warnings"]:
        print("WARN", x)
    return P


SELFTEST_CHILD = """module lpt_leaf #(parameter integer W = 8) (input wire clk, input wire rst_n, input wire [W-1:0] a,
    input wire [W-1:0] b, output reg [W-1:0] y);
    reg [3:0] c;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin c <= 0; y <= 0; end else begin c <= c + 1; y <= a + b + c; end
endmodule
"""
SELFTEST_TOP = """module lpt_top #(parameter integer W = 8) (input wire clk, input wire rst_n, input wire [W-1:0] x,
    output wire [W-1:0] z, output wire [W-1:0] z3);
    wire [W-1:0] y0, y1, y2, y3;
    lpt_leaf #(.W(W)) u0 (.clk(clk), .rst_n(rst_n), .a(x), .b(x), .y(y0));
    lpt_leaf #(.W(W)) u1 (.clk(clk), .rst_n(rst_n), .a(y0), .b(x), .y(y1));
    lpt_leaf #(.W(W)) u2 (.clk(clk), .rst_n(rst_n), .a(y1), .b(y0), .y(y2));
    lpt_leaf #(.W(W)) u3 (.clk(clk), .rst_n(rst_n), .a(y1), .b(x), .y(y3));
    assign z = y2;
    assign z3 = y3;
endmodule
"""


def selftest():
    d = Path(tempfile.mkdtemp(prefix="lp_selftest_", dir=ROOT / "tools/landed_parent"))
    try:
        (d / "child.sv").write_text(SELFTEST_CHILD)
        (d / "top.sv").write_text(SELFTEST_TOP)
        rel = d.relative_to(ROOT)
        S = dict(top="lpt_top", sources=[f"{rel}/top.sv"], child_sources=[f"{rel}/child.sv"], out_dir=str(rel),
                 clock_ports=["clk"], clock_pins=["clk"], reset_port="rst_n", reset_pins=["rst_n"],
                 regions=[dict(name="ra", insts=["u0", "u3"], centre=[0, 0]), dict(name="rb", insts=["u1", "u2"], centre=[900, 0])],
                 _spec_path=f"{rel}/spec.json")
        (d / "spec.json").write_text(json.dumps(S))
        P = gen(S)
        t = P["t"]
        assert t["u0"] == 0 and t["u1"] == 3 and t["u2"] == 3 and t["u3"] == 6, t
        assert len(P["lands"]) == 3 and {L["net"] for L in P["lands"]} == {"y0", "x", "y1"}, P["lands"]
        assert P["pads"] == {("x", "u3"): 6}, P["pads"]
        rec = json.loads((d / "lpt_top_lp_record.json").read_text())
        assert rec["audit"]["ok"] and rec["compiler"]["output_port_offset_edges"]["z"] == 3, rec["audit"]
        assert rec["compiler"]["input_port_offset_edges"]["x"] == 0
        gen(S, mut_unland=True, rtl_out=d / "unland.sv")
        A = audit(S, (d / "unland.sv").read_text())
        assert not A["ok"] and any("UNLANDED" in f for f in A["fails"]), A
        print("SELFTEST PASS (offsets", {k: v for k, v in t.items() if not k.startswith("port:")}, "; unland mutant audit FAIL:",
              A["fails"][0], ")")
    finally:
        if "--keep" not in sys.argv:
            shutil.rmtree(d)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["gen", "audit", "selftest"])
    ap.add_argument("spec", nargs="?")
    ap.add_argument("--mut-unland", action="store_true")
    ap.add_argument("--rtl")
    ap.add_argument("--make-unland", action="store_true", help="audit: first write the unland-mutant RTL to --rtl")
    ap.add_argument("--sim", action="store_true")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest()
    S = load(a.spec)
    if a.cmd == "gen":
        gen(S, mut_unland=a.mut_unland)
        return
    top_lp = S.get("top_lp") or S["top"] + "_lp"
    if a.make_unland:
        gen(S, mut_unland=True, rtl_out=a.rtl)
    rtl = Path(a.rtl) if a.rtl else ROOT / S["out_dir"] / f"{top_lp}.sv"
    A = audit(S, rtl.read_text())
    print(json.dumps(A, indent=1))
    print("LP_AUDIT", "PASS" if A["ok"] else "FAIL")
    sys.exit(0 if A["ok"] else 1)


if __name__ == "__main__":
    main()
