#!/usr/bin/env python3
"""Core-to-core paths of one partition type from its kit's synthesized netlist (FABLE-FIX-S81-LEAF 11-19).

core_conns_from_bind reads the bound module, so it sees a hard core only when the core is an instance of that module.
Types whose bound module keeps a whole as-built wrapper (S81 bk_sel `u_core`, HEAD `u_core`, QC fabric stations) hide
their cores from it and relay_depth measures nothing there (RELAY-DEPTH-BLIND).  The kit's own synthesized netlist
(results/.../1_2_yosys.v) has every hard core as an instance of the top module, named by the kit receipt
bound_macro_paths.json.  This tool walks back from each core input bit through

  buffers / inverters                0 stages
  flops (D -> Q/QN)                  1 stage
  latches (D -> Q)                   0 stages (lockup)
  kept sub-modules (ot_dp_rrelay..)  their own buffer / flop chain, port to port

to a core output bit, and returns the paths in the core_conns_from_bind.trace format (dir "in" + partner).  Anything
else (a gate with several inputs, a top port, a constant) ends the walk and is only counted: this is a wiring and
register-chain tracer, not a timing tool.

usage: core_conns_from_netlist.py PLAN TYPE NETLIST.v OUT.json [--macro-paths bound_macro_paths.json] [--repo R]
"""
import json
import re
import sys
from collections import Counter, defaultdict

NAME = r"(?:\\\S+|[A-Za-z_][A-Za-z0-9_$]*)"
_DECL = re.compile(r"(?m)^\s*(wire|input|output|inout)\s+(?:\[\s*(-?\d+)\s*:\s*(-?\d+)\s*\]\s+)?(" + NAME + r")\s*;")
_INST = re.compile(r"(?ms)^\s*(" + NAME + r")\s+(" + NAME + r")\s*\(\s*\n(.*?)\n\s*\);")
_PORT = re.compile(r"(?m)^\s*\.(" + NAME + r")\s*\((.*)\)\s*,?\s*$")
_ASSIGN = re.compile(r"(?m)^\s*assign\s+(.*?)\s*=\s*(.*?)\s*;\s*$")
_BUF = re.compile(r"^(BUF|HB\d|CKBUF)")
_INV = re.compile(r"^(INV|CKINV)")
_DFF = re.compile(r"^(DFF|SDF|ASYNC_DFF)")
_LAT = re.compile(r"^(DLL|DHL)")
_TIE = re.compile(r"^TIE(HI|LO)")
STD_OUT = {"Y", "Q", "QN", "CON", "SN", "CO", "GCLK"}
DEPTH = 256


def _name(s):
    return s[1:] if s.startswith("\\") else s


def modules(text):
    """{module name: body text}; yosys writes one `module NAME (...);` ... `endmodule` per kept module."""
    out = {}
    for m in re.finditer(r"(?ms)^module\s+(" + NAME + r")\s*\(.*?\);(.*?)^endmodule", text):
        out[_name(m[1])] = m[2]
    return out


def expr_bits(expr, widths):
    """MSB-first bits of a yosys connection expression: (name, index) or None for a constant bit."""
    out, i, n = [], 0, len(expr)
    while i < n:
        c = expr[i]
        if c in " \t\n{},":
            i += 1
            continue
        if c == "\\":
            j = i
            while j < n and not expr[j].isspace():
                j += 1
            name, i = expr[i + 1:j], j
        else:
            m = re.compile(r"(\d+)'[sS]?[bBhHdDoO]?[0-9a-fA-FxXzZ_?]+|\d+|[A-Za-z_][A-Za-z0-9_$]*").match(expr, i)
            if not m:
                raise ValueError("unsupported netlist expression: " + expr[:80])
            i = m.end()
            if m[0][0].isdigit():
                out.extend([None] * (int(m[1]) if m[1] else 32))
                continue
            name = m[0]
        m = re.compile(r"\s*\[\s*(-?\d+)\s*(?::\s*(-?\d+)\s*)?\]").match(expr, i)
        if m and name in widths:
            i = m.end()
            hi = int(m[1]); lo = int(m[2]) if m[2] is not None else hi
            step = -1 if hi >= lo else 1
            out.extend((name, k) for k in range(hi, lo + step, step))
        else:
            hi, lo = widths.get(name, (0, 0))
            step = -1 if hi >= lo else 1
            out.extend((name, k) for k in range(hi, lo + step, step))
    return out


class Mod:
    def __init__(self, body):
        self.widths, self.dirs = {}, {}
        for m in _DECL.finditer(body):
            nm = _name(m[4])
            self.widths[nm] = (int(m[2]), int(m[3])) if m[2] is not None else (0, 0)
            if m[1] != "wire":
                self.dirs[nm] = m[1]
        self.insts = []                 # (module, inst, {pin: [bits]})
        for m in _INST.finditer(body):
            mod, inst = _name(m[1]), _name(m[2])
            if mod in ("module", "wire", "input", "output", "assign"):
                continue
            pins = {}
            for p in _PORT.finditer(m[3]):
                try:
                    pins[_name(p[1])] = expr_bits(p[2], self.widths)
                except ValueError:
                    pins[_name(p[1])] = []
            self.insts.append((mod, inst, pins))
        self.alias = {}                 # lhs bit -> rhs bit
        for m in _ASSIGN.finditer(body):
            try:
                lhs, rhs = expr_bits(m[1], self.widths), expr_bits(m[2], self.widths)
            except ValueError:
                continue
            if len(lhs) == len(rhs):
                for a, b in zip(lhs, rhs):
                    if a is not None:
                        self.alias[a] = b
        self.driver = None


def _port_bits(mod, port):
    hi, lo = mod.widths.get(port, (0, 0))
    step = -1 if hi >= lo else 1
    return list(range(hi, lo + step, step))


class Netlist:
    def __init__(self, text, top=None):
        self.mods = {n: None for n in modules(text)}
        self._bodies = modules(text)
        self.top = top if top in self._bodies else list(self._bodies)[-1]
        self._sum = {}

    def mod(self, name):
        if self.mods[name] is None:
            self.mods[name] = Mod(self._bodies[name])
        return self.mods[name]

    def drivers(self, name, core_out):
        """{net bit: (kind, inst index, pin, position)} of module `name`; core_out(mod, inst) -> {pin: [indices]} or None."""
        m = self.mod(name)
        if m.driver is not None:
            return m.driver
        d = {}
        for k, (mod, inst, pins) in enumerate(m.insts):
            co = core_out(mod, inst) if core_out else None
            if co is not None:
                for pin, idx in co.items():
                    bb = pins.get(pin, [])
                    ii = idx if len(idx) == len(bb) else list(range(len(bb) - 1, -1, -1))
                    for b, i in zip(bb, ii):
                        if b is not None:
                            d[b] = ("core", k, pin, i)
            elif mod in self.mods:
                sub = self.mod(mod)
                for pin, bb in pins.items():
                    if sub.dirs.get(pin) == "output":
                        for b, i in zip(bb, _port_bits(sub, pin)):
                            if b is not None:
                                d[b] = ("sub", k, pin, i)
            else:
                for pin, bb in pins.items():
                    if (pin in STD_OUT or (pin in ("H", "L") and _TIE.match(mod))) and bb and bb[0] is not None:
                        d[bb[0]] = ("cell", k, pin, 0)
        m.driver = d
        return d

    def back(self, name, bit, core_out=None, depth=0):
        """walk back from net `bit` of module `name` -> (kind, payload, stages, latches); kind = core | port | stop"""
        m = self.mod(name)
        drv = self.drivers(name, core_out)
        st = lat = 0
        for _ in range(DEPTH):
            if bit is None:
                return ("stop", "constant", st, lat)
            if bit in m.alias:
                bit = m.alias[bit]
                continue
            d = drv.get(bit)
            if d is None:
                if m.dirs.get(bit[0]) == "input":
                    return ("port", bit, st, lat)
                return ("stop", "undriven", st, lat)
            kind, k, pin, pos = d
            mod, inst, pins = m.insts[k]
            if kind == "core":
                return ("core", (inst, pin, pos), st, lat)
            if kind == "sub":
                if depth > 8:
                    return ("stop", "hierarchy too deep", st, lat)
                key = (mod, pin, pos)
                if key not in self._sum:
                    self._sum[key] = self.back(mod, (pin, pos), None, depth + 1)
                r = self._sum[key]
                if r[0] != "port":
                    return ("stop", "logic in " + mod if r[0] == "stop" and r[1] == "logic" else "sub-module " + mod + ": " + str(r[1]), st, lat)
                sub = self.mod(mod)
                ip, ii = r[1]
                bb = pins.get(ip, [])
                pb = _port_bits(sub, ip)
                if len(bb) != len(pb) or ii not in pb:
                    return ("stop", "sub-module port width", st, lat)
                bit = bb[pb.index(ii)]
                st += r[2]; lat += r[3]
                continue
            if _TIE.match(mod):
                return ("stop", "constant", st, lat)
            if _BUF.match(mod) or _INV.match(mod):
                bit = (pins.get("A") or [None])[0]
            elif _DFF.match(mod):
                bit = (pins.get("D") or [None])[0]
                st += 1
            elif _LAT.match(mod):
                bit = (pins.get("D") or [None])[0]
                lat += 1
            else:
                return ("stop", "logic", st, lat)
        return ("stop", "chain too long", st, lat)


def trace(text, cores, top=None):
    """cores = {netlist instance name: (plan core name, {pin: direction}, {pin: [bit indices, MSB first]})}

    -> dict(paths=[trace rows, dir "in"], stops={reason: input bits}, cores_found=[plan names], top=module)"""
    nl = Netlist(text, top)
    if top is None:      # the module that holds the cores
        for name in reversed(list(nl.mods)):
            if any(i in cores for _, i, _ in nl.mod(name).insts):
                nl.top = name
                break
    m = nl.mod(nl.top)

    def core_out(mod, inst):
        if inst not in cores:
            return None
        _, dirs, idx = cores[inst]
        return {p: idx.get(p, []) for p, d_ in dirs.items() if d_ == "OUTPUT"}
    paths, stops, found = {}, Counter(), set()
    for mod, inst, pins in m.insts:
        if inst not in cores:
            continue
        plan_name, dirs, idx = cores[inst]
        found.add(plan_name)
        for pin, bb in pins.items():
            if dirs.get(pin) != "INPUT":
                continue
            ii = idx.get(pin, [])
            if len(ii) != len(bb):
                ii = list(range(len(bb) - 1, -1, -1))
            for b, i in zip(bb, ii):
                kind, payload, st, lat = nl.back(nl.top, b, core_out)
                if kind != "core":
                    stops[payload if kind == "stop" else "top port"] += 1
                    continue
                sinst, spin, _ = payload
                key = (plan_name, pin, cores[sinst][0] + "." + spin, st, lat)
                paths.setdefault(key, set()).add(i)
    rows = []
    for (core, pin, partner, st, lat), bits in sorted(paths.items()):
        bb, ranges = sorted(bits), []
        for b in bb:
            if ranges and b == ranges[-1][1] + 1:
                ranges[-1][1] = b
            else:
                ranges.append([b, b])
        rows.append(dict(core=core, port=pin, dir="in", partner=partner, stages_existing=st, via=[], latches=lat,
                         bits_connected=len(bb), bit_sample=bb[:8], bit_ranges=ranges, source="netlist"))
    return dict(paths=rows, stops=dict(stops), cores_found=sorted(found), top=nl.top)


def plan_cores(plan, tn, macro_paths=None, repo=None):
    """{netlist instance: (plan core, directions, indices)} from the plan type and the kit receipt bound_macro_paths.json."""
    import core_conns_from_bind as CC
    t = plan["partition_types"][tn]
    phys = {r["inst"]: r["physical_inst"] for r in (macro_paths or {}).get("rows", [])}
    out = {}
    for hc in t.get("hard_cores", []):
        inst = phys.get(hc["inst"]) or hc.get("physical_inst") or hc["inst"]
        out[inst] = (hc["inst"], CC.hc_port_directions(hc, repo), CC.hc_port_bit_indices(hc, repo))
    return out


def main(argv):
    import argparse
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan"); ap.add_argument("type"); ap.add_argument("netlist"); ap.add_argument("out")
    ap.add_argument("--macro-paths"); ap.add_argument("--repo")
    a = ap.parse_args(argv[1:])
    plan = json.loads(Path(a.plan).read_text())
    mp = json.loads(Path(a.macro_paths).read_text()) if a.macro_paths else None
    cores = plan_cores(plan, a.type, mp, a.repo)
    res = trace(Path(a.netlist).read_text(), cores)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(f"{a.type}: {len(res['cores_found'])}/{len(cores)} cores in {res['top']}, {len(res['paths'])} core-to-core paths, "
          f"{sum(r['bits_connected'] for r in res['paths'])} bits; stopped: {res['stops']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
