#!/usr/bin/env python3
"""Opt-in coherent one-edge input capture collar for unsigned KVS_PC.

All functional inputs, including delivered reset/control, are sampled on the core
clock before the unchanged leaf. Data flops have no reset. Clocks and declared
quasi-static straps pass through. The parent plan prices +1 input/boot edge and
pads coherent neighbours. This is a source candidate, not a physical closure.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

_PORT = re.compile(r"^\s*(input|output)\s+wire\s*(\[[^]\n]+\])?\s*(\w+)\s*[,)]", re.M)

def transform_wrapper(text: str, *, enabled: bool = False,
                      declared_straps=(), clock_port: str = "ck",
                      leaf_instance: str = "u_leaf"):
    if not enabled:
        return text, dict(enabled=False, input_cycles=0, boot_cycles=0, flops=0)
    if "KVSPC_COHERENT_INPUT_COLLAR" in text:
        raise ValueError("input collar already present")
    stop = text.index(");") + 2
    ports = [(direction, width or "", name)
             for direction, width, name in _PORT.findall(text[:stop])]
    if not ports or not any(d == "input" and n == clock_port for d, _, n in ports):
        raise ValueError("missing explicit core clock/ANSI port inventory")
    straps = set(declared_straps)
    input_names = {n for d, _, n in ports if d == "input"}
    if straps - input_names:
        raise ValueError("declared strap is not an input: " + str(sorted(straps - input_names)))
    clocks = {n for d, _, n in ports if d == "input" and
              (n == clock_port or re.fullmatch(r"ft_ck_i_\d+", n))}
    inputs = [(w, n) for d, w, n in ports if d == "input" and n not in clocks
              and n not in straps and not n.startswith("strap_")]
    if not inputs:
        raise ValueError("no functional input ports")
    inst = list(re.finditer(r"\b" + re.escape(leaf_instance) + r"\s*\(", text[stop:]))
    if len(inst) != 1:
        raise ValueError("expected exactly one unchanged leaf instance")
    start = stop + inst[0].end()
    end = text.index("\n    );", start)
    body = text[start:end]
    original_body = body
    captured = []
    declarations = ["\n    // KVSPC_COHERENT_INPUT_COLLAR: one coherent input/boot edge; no data resets."]
    flops = 0
    for width, name in inputs:
        if not re.search(r"\b" + re.escape(name) + r"\b", body):
            raise ValueError("functional input has no leaf use: " + name)
        alias = "pcin_" + name
        body = re.sub(r"(?<![.\w])" + re.escape(name) + r"\b", alias, body)
        declarations += [f"    (* keep = 1, face_keep = 1 *) reg {width} {alias};",
                         f"    always @(posedge {clock_port}[0]) {alias} <= {name};"]
        bits = 1
        if width:
            m = re.fullmatch(r"\[(\d+):(\d+)\]", width)
            if m is None:
                raise ValueError("non-literal width for " + name)
            bits = abs(int(m[1]) - int(m[2])) + 1
        flops += bits
        captured.append(dict(port=name, width=bits, register=alias))
    restored = body
    for _, name in inputs:
        restored = re.sub(r"\bpcin_" + re.escape(name) + r"\b", name, restored)
    if restored != original_body:
        raise ValueError("unchanged leaf connection invariant failed")
    out = text[:stop] + "\n".join(declarations) + "\n" + text[stop:start] + body + text[end:]
    return out, dict(schema="opentallas.kvspc.input_collar.v1", enabled=True,
                     input_cycles=1, boot_cycles=1, throughput_cycles=0,
                     flops=flops, captured=captured, clocks=sorted(clocks),
                     strap_passthrough=sorted(straps | {n for _, _, n in ports if n.startswith("strap_")}),
                     leaf_logic_changed=False, default_enabled=False)


def interior_captures(pins, captured):
    """Interior reset/data pins stay local; the generic face hook uses outer edges."""
    ports = {r["port"] for r in captured}
    return [p for p in pins if p.get("bus") in ports and p.get("face") == "interior"]

def interior_tcl(pins):
    lines = ["# Source-defined interior input-collar capture sites, after face_flops.tcl",
             "uplevel #0 {"]
    for p in pins:
        name = p["bus"] + ("[" + str(p["bit"]) + "]" if p.get("bit") is not None else "")
        lines += ["set ci_bt [$ff_blk findBTerm {" + name + "}]",
                  'if {$ci_bt eq "NULL"} { error "PC_INPUT_COLLAR: missing interior input pin" }',
                  "set ci_f [ff_from_in [$ci_bt getNet] 0]",
                  'if {$ci_f eq ""} { error "PC_INPUT_COLLAR: missing interior capture" }',
                  "set ci_x [expr {round(" + str(float(p["x"])) + "*$ff_dbu)}]",
                  "set ci_y [expr {round(" + str(float(p["y"])) + "*$ff_dbu)}]",
                  "lassign [ff_put_near $ci_f $ci_x $ci_y] ci_ax ci_ay",
                  'if {abs($ci_ax-$ci_x)+abs($ci_ay-$ci_y) > 30*$ff_dbu} { error "PC_INPUT_COLLAR: interior capture exceeds30um" }',
                  'puts "PC_INPUT_COLLAR interior [$ci_bt getName] -> [$ci_f getName] at $ci_ax $ci_ay"']
    return "\n".join(lines + ["}", ""])

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("wrapper", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--enable", action="store_true")
    ap.add_argument("--strap", action="append", default=[])
    a=ap.parse_args()
    text, receipt=transform_wrapper(a.wrapper.read_text(),enabled=a.enable,declared_straps=a.strap)
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/a.wrapper.name).write_text(text)
    (a.out/"input_collar.json").write_text(json.dumps(receipt,indent=2)+"\n")
if __name__ == "__main__":
    main()
