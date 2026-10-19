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
  reset_active_low (default true)
  regions        [{name, insts: [fnmatch patterns], centre: [x, y] (um, optional)}]   the FIRST is the core region: its
                 clock port is the kit's clock_port (core_clk in the base SDC)
  port_regions   {port: region} overrides (default: input = region of its first reader, output = its driver's region)
  static         [ports / nets] identity straps: never landed (case-analysed), constant in the bench (tb_static {p: v})
  D, E           ring depth / read offset (default 4 / 2: as Q-CLUSTER-LANDALL)
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
  lag_pins       [{inst: fnmatch pattern, pins: [..], why}]  STATUS-RETURN reader pins (e.g. a head's fault / valid-lockstep
                 inputs fed back from the children it configures).  A head that both configures and collects status from
                 children in other regions is a cross-region LOOP; its status pins are taken OUT of the schedule: they are
                 landed as usual, then padded so every lag pin of that reader sees its net exactly lag(reader) edges later
                 than the reader's own time (one common lag per reader).  The lockstep reference becomes <top>_lagref (the
                 flat parent with those pins delayed lag(reader) stages, generated beside the landed top), and the record's
                 compiler block lists the lag: the status those pins carry reaches the reader's outputs lag edges late.
  mut_child      child whose reset run MUT 4 lengthens (default: the first child with a reset pin); pick one whose state
                 outlives the reset (a sticky flag / counter): a pure pipeline register forgets a late reset in one edge
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
KW = {"module", "endmodule", "input", "output", "inout", "wire", "reg", "logic", "assign", "always", "always_ff",
      "always_comb", "initial", "generate", "endgenerate", "parameter", "localparam", "if", "else", "for", "begin", "end",
      "case", "endcase", "function", "endfunction", "genvar", "integer", "signed", "unsigned", "default_nettype"}
LIB_PORTS = {"ot_pl_land_w": {"ck": "in", "rsi": "in", "i": "in", "bank": "out", "epo": "out", "vld": "out"},
             "ot_pl_land_r": {"ck": "in", "rsi": "in", "bank": "in", "epo": "in", "vld": "in", "o": "out"},
             "ot_pl_pad": {"ck": "in", "d": "in", "q": "out"}}
# Chunked primitives preserve the same top-level source/read contract.
LIB_PORTS['ot_pl_land_chunk_w'] = dict(LIB_PORTS['ot_pl_land_w'])
LIB_PORTS['ot_pl_land_chunk_r'] = dict(LIB_PORTS['ot_pl_land_r'])



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
                          item=it))
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
    for mm in re.finditer(r"\bwire\b\s*(?:signed)?\s*(?:\[[^\]]*\])?\s*(\w+)\s*=\s*([^;]+);", body):
        assigns.append(({mm.group(1)}, idents(mm.group(2))))
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


def eval_width(rng: str | None, env: dict) -> int:
    if not rng:
        return 1
    a, b = rng.strip()[1:-1].split(":")
    def ev(x):
        x = x.replace("$clog2", "_clog2")
        for _ in range(8):
            for k, v in env.items():
                x = re.sub(rf"\b{re.escape(k)}\b", f"({v})", x)
        return int(eval(x, {"_clog2": lambda v: max(0, math.ceil(math.log2(v))) if v > 0 else 0}))
    return abs(ev(a) - ev(b)) + 1


def width_text(rng: str | None) -> str:
    if not rng:
        return "1"
    a, b = rng.strip()[1:-1].split(":")
    return f"(({a.strip()}) - ({b.strip()}) + 1)"


# ----------------------------------------------------------------------------------------------------------- the model
class Parent:
    def __init__(self, spec: dict):
        self.S = spec
        src = "\n".join(preprocess((ROOT / f).read_text(errors="replace"), spec.get("defines")) for f in spec["sources"])
        self.mod = parse_module(src, spec["top"])
        csrc = "\n".join(preprocess((ROOT / f).read_text(errors="replace"), spec.get("defines"))
                         for f in spec.get("child_sources", []))
        self.wires, self.assigns, self.insts = parse_body(self.mod["body"])
        self.env = {k: v for k, v in self.mod["params"].items()}
        self.env.update({k: str(v) for k, v in (spec.get("params") or {}).items()})
        self.cports = {}
        for ins in self.insts:
            m = ins["module"]
            if m not in self.cports:
                cm = parse_module(csrc, m)
                self.cports[m] = {p["name"]: p["dir"] for p in cm["ports"]}
        self.ports = {p["name"]: p for p in self.mod["ports"]}
        self.ck = set(spec.get("clock_ports") or [])
        self.rst = spec.get("reset_port")
        self.static = set(spec.get("static") or [])
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

    def rng(self, n):
        if n in self.wires:
            return self.wires[n]
        if n in self.ports:
            return self.ports[n]["range"]
        raise SystemExit(f"net {n} has no declaration in {self.S['top']}")

    def graph(self):
        """drivers {net: {node}}, readers [(net, node, pin)]; node = inst name or 'port:<p>'"""
        excl = self.ck | {self.rst} | self.static
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
            for d in ds:
                edges.append((d, inst, n, self.A if landed else 0, landed, pin))
        for p, ds in out_drv.items():
            for d in ds:
                edges.append((d, f"port:{p}", p, 0, False, None))
        nodes = sorted({e[0] for e in edges} | {e[1] for e in edges} | set(self.region))
        lagged = [e for e in edges if (e[1], e[5]) in self.lag]
        edges_all, edges = edges, [e for e in edges if (e[1], e[5]) not in self.lag]
        t = {v: 0 for v in nodes}
        if self.reference:
            lst = sorted(lands.values(), key=lambda L: int(L["name"]))
            if mut_unland and lst:
                lst[0]["unlanded_mutant"] = True
            return dict(t=t, edges=edges, lands=lst, landkey=lands, pads={}, nreg=nreg, drv=drv, rd=rd, out_drv=out_drv)
        for it in range(len(nodes) + 1):
            ch = False
            for a, b, n, add, _, _ in edges:
                if t[a] + add > t[b]:
                    t[b] = t[a] + add
                    ch = True
            if not ch:
                break
        else:
            loop = [f"{a}->{b} ({n}, +{add})" for a, b, n, add, _, _ in edges if t[a] + add > t[b]]
            raise SystemExit("cross-region LOOP: the landed parent cannot keep the flat schedule (the compiler must "
                             "re-schedule, or keep the loop inside one region): " + "; ".join(loop[:8]))
        for v in nodes:                         # input ports: as late as their earliest reader allows (no pad there)
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
            if k > 0:
                pads[(n, b)] = max(pads.get((n, b), 0), k)
            if k < 0:
                raise SystemExit("internal: negative pad")
        lag = {}            # reader inst -> common status lag (edges after the reader's own time)
        for a, b, n, add, landed, pin in lagged:
            lag[b] = max(lag.get(b, 0), t[a] + add - t[b])
        for a, b, n, add, landed, pin in lagged:
            k = t[b] + lag[b] - t[a] - add
            if k > 0:
                pads[(n, b)] = max(pads.get((n, b), 0), k)
        edges = edges_all
        lst = sorted(lands.values(), key=lambda L: int(L["name"]))
        if self.S.get("share_rings"):
            # TW2-PSLICE2 10-19 (opt-in share_rings): ONE write ring per (net, source region), beside the source; every read
            # half of that net (each destination region / reader instance) reads the same ring bank (LANDING-CONTRACT
            # unchanged: equal-depth reset runs G == R0, so every reader keeps K = E; the ring -> read multicycle is per pair)
            own = {}
            for L in lst:
                L["ring_of"] = own.setdefault((L["net"], L["src_region"]), L["name"])
        if mut_unland and lst:
            lst[0]["unlanded_mutant"] = True
        return dict(t=t, edges=edges, lands=lst, landkey=lands, pads=pads, nreg=nreg, drv=drv, rd=rd, out_drv=out_drv,
                    lag=lag, lagged=lagged)

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

    def emit(self, P, top_lp, mut=True):
        S, D, E, K, AW = self.S, self.D, self.E, self.K, self.AW
        rr, hops, RB = self.reset_tree()
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
        w(f"//     4 = child reset run of '{self.mut_child(P)}' one stage long")
        w(f"module {top_lp} #(\n    {par}parameter integer MUT = 0\n) (\n    " + ",\n    ".join(items) + "\n);")
        body = self.mod["body"]
        # strip instance statements; they are re-emitted below
        keep, pos = [], 0
        for ins in self.insts:
            keep.append(body[pos:ins["span"][0]])
            pos = ins["span"][1]
        keep.append(body[pos:])
        for chunk in keep:
            for line in chunk.splitlines():
                if line.strip():
                    w(line.rstrip())
        # reset tree
        w(f"    // ---- regional reset runs (1-bit plain hops: they define the landing epochs; region {rr} holds the root)")
        w(f"    wire lpr_root;  ot_pl_pad #(.W(1), .N(1)) u_lpr_root (.ck(ck_{rr}), .d({self.rst}), .q(lpr_root));")
        for r in self.regions:
            w(f"    wire lpr_{r};  ot_pl_pad #(.W(1), .N({RB - 1})) u_lpr_{r} (.ck(ck_{r}), .d(lpr_root), .q(lpr_{r}));"
              f"   // {hops[r]} hop(s) from {rr}")
        # landings
        sub = {}            # (inst, net) -> replacement net
        for Ld in P["lands"]:
            n, net, s, r = Ld["name"], Ld["net"], Ld["src_region"], Ld["dst_region"]
            rng = self.rng(net)
            wt = width_text(rng)
            primitive = "ot_pl_land_chunk" if self.chunk_bits else "ot_pl_land"
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
                w(f"    {primitive}_w #(.W({wt}), .D({D}){cp}) u_lpl_{n}_w (.ck(ck_{s}), .rsi(lpr_{s}), .i({net}), "
                  f".bank(lpl_{n}_bank), .epo(lpl_{n}_epo), .vld(lpl_{n}_vld));")
            else:
                w(f"    wire {decl} {out}, lpl_{n}_o;")
            kk = f"(MUT == 2) ? {K + 1} : {K}" if n == "0" and mut else f"{K}"
            w(f"    {primitive}_r #(.W({wt}), .D({D}), .K({kk}){cp}) u_lpl_{n}_r (.ck(ck_{r}), .rsi(lpr_{r}), "
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
            if any(pin in (S.get("reset_pins") or []) and ex.strip() == self.rst for pin, ex in ins["conns"].items()):
                kk = f"(MUT == 4) ? {tc + 1} : {tc}" if i == mc and mut else f"{tc}"
                w(f"    wire lpr_c_{i};  ot_pl_pad #(.W(1), .N({kk})) u_lprc_{i} (.ck(ck_{r}), .d(lpr_{r}), .q(lpr_c_{i}));"
                  + (f"   // t({i}) = {tc}" if not self.reference else f"   // reference schedule: held {tc} past the landing epochs"))
                rsub[i] = f"lpr_c_{i}"
        # children
        w("    // ---- children (clock pins -> their region root; reset pins -> their reset run; landed / padded inputs)")
        for ins in self.insts:
            i, r = ins["inst"], self.region[ins["inst"]]
            cs = []
            for pin, ex in ins["conns"].items():
                if pin in (S.get("clock_pins") or []) and idents(ex) & self.ck:
                    ex = f"ck_{r}"
                elif i in rsub and pin in (S.get("reset_pins") or []) and ex.strip() == self.rst:
                    ex = rsub[i]
                elif self.cports[ins["module"]][pin] == "in":
                    for (si, net), rep in sub.items():
                        if si == i:
                            ex = re.sub(rf"(?<![\w$]){re.escape(net)}\b", rep, ex)
                cs.append(f".{pin}({ex})")
            w(f"    {ins['module']} {ins['params'] + ' ' if ins['params'] else ''}{i} (" + ", ".join(cs) + f");   // region {r}, t = {P['t'].get(i, 0)}")
        w("endmodule")
        return "\n".join(L) + "\n", dict(reset_region=rr, hops=hops, RB=RB)

    def mut_child(self, P):
        kids = [ins["inst"] for ins in self.insts
                if any(pin in (self.S.get("reset_pins") or []) and ex.strip() == self.rst for pin, ex in ins["conns"].items())]
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
        flops_rst = 1 + len(self.regions) * (rt["RB"] - 1) + sum(t.get(i["inst"], 0) + self.rx for i in self.insts if any(
            pin in (S.get("reset_pins") or []) and ex.strip() == self.rst for pin, ex in i["conns"].items()))
        pairs = sorted({"-".join(sorted((L["src_region"], L["dst_region"]))) for L in P["lands"]})
        rpairs = sorted({"-".join(sorted((rt["reset_region"], r))) for r in self.regions if r != rt["reset_region"]})
        port_in = {p["name"]: t.get(f"port:{p['name']}", 0) for p in self.mod["ports"]
                   if p["dir"] == "in" and p["name"] not in self.ck | self.static | {self.rst}}
        port_out = {p["name"]: t.get(f"port:{p['name']}", 0) for p in self.mod["ports"] if p["dir"] == "out"}
        no_rst = [i["inst"] for i in self.insts if t.get(i["inst"], 0) and not any(
            pin in (S.get("reset_pins") or []) and ex.strip() == self.rst for pin, ex in i["conns"].items())]
        return dict(
            lane="PARENTS-LANDED", generator="tools/landed_parent/lp.py", flat=S["top"], top=top_lp,
            standard="landed-regions-standard-1018: local region trees, every cross-region net LANDED, per-region "
                     "child-flop gate (TT and FF <= 80 ps); 1-bit reset runs are the only plain cross-region hops",
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
            reset=dict(port=self.rst, root_region=rt["reset_region"], depth=rt["RB"], hops=rt["hops"],
                       note="flat reference == landed parent with its reset delayed by depth; child c's reset run is "
                            "depth + t(c)"),
            flops=dict(landing=flops_land, pads=flops_pad, reset=flops_rst),
            communicating_region_pairs=dict(landed=pairs, reset_hops=rpairs),
            compiler=dict(
                note="every latency change vs the flat parent; the compiler schedule takes these (static calendar, no "
                     "runtime flow control)",
                child_offset_edges={i["inst"]: t.get(i["inst"], 0) for i in self.insts},
                input_port_offset_edges=port_in, output_port_offset_edges=port_out,
                reset_release_added_edges=rt["RB"] + self.rx,
                schedule=("reference: cross-region loops re-scheduled; the landed parent == the flat parent with ref_params "
                          "(+E+1 per landed crossing on that path), reset delayed reset_release_added_edges, ports at offset 0"
                          if self.reference else "offsets"),
                ref_params=dict(S.get("ref_params") or S.get("params") or {}) if self.reference else None,
                **({} if not P.get("lag") else dict(status_lag_edges={
                    b: dict(lag=k, pins=sorted({e[5] for e in P["lagged"] if e[1] == b}),
                            note="these status-return inputs reach the reader lag edges after its own time "
                                 "(flat == <top>_lagref: the reader's outputs carry that status lag edges "
                                 "later than in the flat parent)") for b, k in sorted(P["lag"].items())})),
                max_added_edges=max([0] + list(port_out.values()))),
            **({} if not (S.get("bench") or {}).get("mut_waivers") else dict(mutant_waivers=S["bench"]["mut_waivers"])),
            warnings=[f"child {i} runs t = {t[i]} edges late but has no reset pin on {self.rst}: its free-running state "
                      "is NOT re-aligned (check it in the bench)" for i in no_rst],
            **({} if not (self.chunk_bits or self.direct_timing) else dict(
                landing_implementation=dict(chunk_bits=self.chunk_bits, direct_quarter_period_timing=self.direct_timing,
                                            compensated_phase_T=[-0.75, 0.75], sample_age_T=[1.25, 2.75],
                                            overwrite_gap_min_T=1.25))),
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
        ins = [p for p in self.mod["ports"] if p["dir"] == "in" and p["name"] not in self.ck and p["name"] != self.rst]
        outs = [p for p in self.mod["ports"] if p["dir"] == "out"]
        W = {p["name"]: eval_width(p["range"], self.env) for p in self.mod["ports"]}
        maxoff = max([0] + [t.get(f"port:{p['name']}", 0) for p in outs] + [t.get(f"port:{p['name']}", 0) for p in ins])
        warm = rcy + RB + maxoff + self.A + 8
        tbs = S.get("tb_static") or {}
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
            L.append(f"    wire [{w_ - 1}:0] fo_{n}, lo_{n};  reg [{w_ - 1}:0] dlo_{n} [0:{off}];")
            L.append(f"    always @(posedge clk) begin : g_dlo_{n} integer j; dlo_{n}[0] <= fo_{n}; "
                     f"for (j = 1; j <= {off}; j = j + 1) dlo_{n}[j] <= dlo_{n}[j - 1]; end")
        ck = sorted(self.ck)
        fc = [f".{c}(clk)" for c in ck] + [f".{self.rst}(rst_f)"] + [f".{p['name']}(fi_{p['name']})" for p in ins] + \
             [f".{p['name']}(fo_{p['name']})" for p in outs]
        lc = [f".ck_{r}(clk)" for r in self.regions] + [f".{self.rst}(rst)"] + [f".{p['name']}(li_{p['name']})" for p in ins] + \
             [f".{p['name']}(lo_{p['name']})" for p in outs]
        pv = ", ".join(f".{k}({v})" for k, v in (S.get("params") or {}).items())
        pr = ", ".join(f".{k}({v})" for k, v in ((S.get("ref_params") if self.reference else None) or S.get("params") or {}).items())
        ref = S["top"] + "_lagref" if P.get("lag") else S["top"]
        L.append(f"    {ref} {('#(' + pr + ') ') if pr else ''}u_flat (" + ", ".join(fc) + ");")
        L.append(f"    {top_lp} #({(pv + ', ') if pv else ''}.MUT(MUT)) u_lp (" + ", ".join(lc) + ");")
        L.append("    function [31:0] rnd; input integer k; rnd = $urandom; endfunction")
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
        return "\n".join(L) + "\n"

    def bench_sh(self, top_lp, rel_out, P=None):
        muts = [0] + ([1, 2] if P and P["lands"] else []) + ([3] if P and P["pads"] else []) + ([4] if self.mut_child(P) else [])
        waived = {int(k): v for k, v in ((self.S.get("bench") or {}).get("mut_waivers") or {}).items()}
        muts = [m for m in muts if m not in waived]
        up = "/".join([".."] * len(Path(rel_out).parts))
        srcs = " ".join(self.S["sources"] + self.S.get("child_sources", []) + [LIB_RTL] +
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
    ${{VERILATOR:-verilator}} --binary -j ${{VL_JOBS:-8}} -Wno-fatal ${{VL_EXTRA:-}} --top-module tb_{top_lp} -GMUT=$m {defs} $SRCS -Mdir "$OUT/obj$m" > "$OUT/build_$m.log" 2>&1 \\
      && "$OUT/obj$m/Vtb_{top_lp}" > "$OUT/mut$m.log" 2>&1
  else
    iverilog -g2012 -o "$OUT/sim$m" -s tb_{top_lp} -Ptb_{top_lp}.MUT=$m {defs} $SRCS > "$OUT/build_$m.log" 2>&1 \\
      && vvp -n "$OUT/sim$m" > "$OUT/mut$m.log" 2>&1
  fi
  r=$(grep -o 'LP_LOCKSTEP [A-Z]*' "$OUT/mut$m.log" 2>/dev/null | head -1)
  echo "MUT $m: ${{r:-NO_RESULT (see $OUT/build_$m.log)}}"
  if [ $m -eq 0 ]; then [ "$r" = "LP_LOCKSTEP PASS" ] || rc=1; else [ "$r" = "LP_LOCKSTEP FAIL" ] || rc=1; fi
done
echo "BENCH_EXIT $rc"; exit $rc
"""


# ------------------------------------------------------------------------------------------------------------- audit
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
    rcks = {f"ck_{r['name']}" for r in spec["regions"]}     # region clocks only (a parent port may be named ck_*)
    reg = {}
    for i in insts:
        cks = [ex.strip() for pin, ex in i["conns"].items() if ex.strip() in rcks]
        if len(set(cks)) != 1:
            return dict(ok=False, fails=[f"{i['inst']}: clock pins on {sorted(set(cks)) or 'no region clock'}"])
        reg[i["inst"]] = cks[0][3:]
    drv = {}
    for i in insts:
        for pin, ex in i["conns"].items():
            if dirs[i["module"]].get(pin) == "out":
                for n in idents(ex):
                    drv.setdefault(n, set()).add(i["inst"])
    # OWN-QWEN/SLICE-E 10-18: input ports placed by port_regions are drivers in THAT region, so a port -> reader crossing
    # without its ring / read is an UNLANDED crossing too (before, a port-sourced crossing was never audited and the
    # --mut-unland mutant passed the audit whenever landing 0 came from a port).
    for p, r in (spec.get("port_regions") or {}).items():
        if any(q["name"] == p and q["dir"] == "in" for q in mod["ports"]):
            drv.setdefault(p, set()).add(f"port:{p}")
            reg[f"port:{p}"] = r
    for _ in range(len(assigns) + 1):
        for lhs, rhs in assigns:
            src = set().union(*(drv.get(n, set()) for n in rhs)) if rhs else set()
            for n in lhs:
                drv[n] = drv.get(n, set()) | src
    fails, landed, rst = [], 0, 0
    for i in insts:
        for pin, ex in i["conns"].items():
            if dirs[i["module"]].get(pin) != "in" or ex.strip() in rcks:
                continue
            for n in idents(ex):
                for d in drv.get(n, ()):
                    if reg[d] == reg[i["inst"]]:
                        continue
                    if d.startswith("port:"):
                        fails.append(f"UNLANDED {n}: {d} ({reg[d]}) -> {i['inst']}.{pin} ({reg[i['inst']]})")
                        continue
                    di = next(x for x in insts if x["inst"] == d)
                    if di["module"] in ("ot_pl_land_w", "ot_pl_land_chunk_w") and i["module"] in ("ot_pl_land_r", "ot_pl_land_chunk_r") and \
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
