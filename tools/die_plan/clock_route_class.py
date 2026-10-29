#!/usr/bin/env python3
"""Opt-in OpenDB CLOCK classification for an exact generated ctree netlist.

create_clock/assign_ndr do not set OpenDB SigType. Source the emitted Tcl
after link/placement and before GRT. The target design may contain data,
but only the source tree's validated root-connected buffer/inverter pins
are selected. Connectivity must match before any net is changed. NDR stays
unchanged. This does not choose routing layers or qualify an RC model.
"""
import argparse
import re
from pathlib import Path

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*\Z")
MASTER = re.compile(r"(?:BUF\w*|CKINV\w*)_ASAP7_75t_R\Z")
INST = re.compile(r"^\s*(\w+)\s+(\w+)\s*\((.*?)\);", re.M)
PIN = re.compile(r"\.(\w+)\(\s*([^\s()]+)\s*\)")


def tree_parents(text, root="root"):
    aliases = dict(re.findall(r"\bassign\s+(\w+)\s*=\s*(\w+)\s*;", text))
    cells = {}; drivers = {}
    for m in INST.finditer(text):
        master, name, body = m.groups(); pins = dict(PIN.findall(body))
        if master == "module":continue
        if not MASTER.fullmatch(master) or set(pins) != {"A", "Y"}:
            raise ValueError("source must be a dedicated generated buffer/inverter ctree: " + name)
        if name in cells or pins["Y"] in drivers:
            raise ValueError("duplicate clock cell or multiple drivers: " + name)
        cells[name] = pins; drivers[pins["Y"]] = name
    if not cells:
        raise ValueError("source contains no clock tree cells")
    def resolve(net):
        seen = set()
        while net in aliases:
            if net in seen:raise ValueError("clock assign cycle: " + net)
            seen.add(net);net=aliases[net]
        return net
    parents={}
    for name,pins in cells.items():
        net=resolve(pins["A"])
        if net == root:parents[name]=None
        elif net in drivers:parents[name]=drivers[net]
        else:raise ValueError("clock tree cell is not rooted at declared source: " + name)
    done=set()
    for name in parents:
        cur=name;seen=set()
        while cur is not None and cur not in done:
            if cur in seen:raise ValueError("clock cell cycle: " + cur)
            seen.add(cur);cur=parents[cur]
        done.update(seen)
    return parents


def emit(text, prefix="", root_net="root", source_root="root"):
    parents=tree_parents(text,source_root)
    masters={m.group(2):m.group(1) for m in INST.finditer(text) if m.group(1)!="module"}
    if not IDENT.fullmatch(root_net) or (prefix and not IDENT.fullmatch(prefix)):
        raise ValueError("generated source/prefix must be simple identifiers")
    if any(not IDENT.fullmatch(prefix+n) for n in parents):
        raise ValueError("generated instance name is not a simple identifier")
    L=["# Explicit opt-in CLOCK route classification; NDR/geometry/constraints unchanged.",
       "set ot_cc_b [ord::get_db_block]",f"set ot_cc_root [$ot_cc_b findNet {{{root_net}}}]",
       'if {$ot_cc_root eq "NULL"} {error "OT_CLOCK_CLASS missing declared root net"}',
       "set ot_cc_nets {}; set ot_cc_cells {}"]
    # First collect exact instance pins and expected parent relationships.
    for name in sorted(parents):
        nm=prefix+name
        L += [f"set ot_cc_i [$ot_cc_b findInst {{{nm}}}]",
              f'if {{$ot_cc_i eq "NULL"}} {{error "OT_CLOCK_CLASS missing cell {nm}"}}',
              f'if {{[[$ot_cc_i getMaster] getName] ne "{masters[name]}"}} {{error "OT_CLOCK_CLASS master mismatch at {nm}"}}',
              "foreach ot_cc_p {A Y} {",
              " set ot_cc_t [$ot_cc_i findITerm $ot_cc_p]",
              ' if {$ot_cc_t eq "NULL"} {error "OT_CLOCK_CLASS missing clock cell pin"}',
              " set ot_cc_n [$ot_cc_t getNet]",
              ' if {$ot_cc_n eq "NULL" || [$ot_cc_n getSigType] in {POWER GROUND}} {error "OT_CLOCK_CLASS invalid clock pin net"}',
              f" dict set ot_cc_cells {{{name}}} $ot_cc_p $ot_cc_n",
              " dict set ot_cc_nets [$ot_cc_n getName] $ot_cc_n", "}"]
    for name,parent in sorted(parents.items()):
        expected="$ot_cc_root" if parent is None else f"[dict get $ot_cc_cells {{{parent}}} Y]"
        L += [f'if {{[dict get $ot_cc_cells {{{name}}} A] ne {expected}}} {{error "OT_CLOCK_CLASS source connectivity mismatch at {prefix+name}"}}']
    L += ["foreach ot_cc_n [dict values $ot_cc_nets] { $ot_cc_n setSigType CLOCK }",
          'puts "OT_CLOCK_CLASS cells=[dict size $ot_cc_cells] nets=[dict size $ot_cc_nets]"']
    return "\n".join(L)+"\n"


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("ctree");p.add_argument("out")
    p.add_argument("--prefix",default="");p.add_argument("--root-net",default="root")
    p.add_argument("--source-root",default="root")
    a=p.parse_args()
    Path(a.out).write_text(emit(Path(a.ctree).read_text(),a.prefix,a.root_net,a.source_root))


if __name__=="__main__":main()
