#!/usr/bin/env python3
"""Opt-in stations on a checked direct native-top connection.

Only the selected sink bits are replaced. Source output connections and other
consumers are preserved. This emits source preparation, not a physical or token
qualification; every inserted cycle must be adopted by the parent plan/compiler.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

if __package__:
    from . import b2_top as B
else:
    import b2_top as B


def bits(segments):
    out = []
    for segment in segments:
        if segment[0] != "n":
            raise ValueError("direct station path contains a constant")
        _, net, lo, hi = segment
        if hi < lo:
            raise ValueError("ascending native ranges are unsupported")
        out.extend((net, bit) for bit in range(lo, hi + 1))
    return out


def expression(segments):
    terms = []
    for segment in reversed(segments):
        if segment[0] == "n":
            _, net, lo, hi = segment
            terms.append(f"{net}[{hi}:{lo}]")
        else:
            _, width, value = segment
            terms.append(f"{width}'bx" if value == "x" else f"{width}'h{value:x}")
    return terms[0] if len(terms) == 1 else "{" + ", ".join(terms) + "}"


def materialize(text, chains, *, enabled=False):
    if not enabled:
        return text, dict(enabled=False, added_cycles=0, chains=[])
    emitted = []
    seen = set()
    for chain in chains:
        if chain.get("runtime_adopt", False):
            raise ValueError("source preparation cannot adopt an incomplete parent timing bundle")
        ident = chain["name"]
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", ident) or ident in seen:
            raise ValueError("station names must be unique Verilog identifiers")
        seen.add(ident)
        prefix = "__ot_station_" + ident
        if re.search(r"\b" + re.escape(prefix) + r"(?:_\w+)?\b", text):
            raise ValueError("station name already present in source")
        stages = chain["stages"]
        if type(stages) is not int or stages < 1:
            raise ValueError("station stages must be a positive integer")
        if chain.get("transport", "fullwidth_k1") != "fullwidth_k1":
            raise ValueError("direct stations require fullwidth_k1; serialization needs its own source")
        top = re.search(r"\bmodule\s+(\w+)\s*\(.*?\);", text, re.S)
        if top is None or len(re.findall(r"\bmodule\s+", text)) != 1:
            raise ValueError("require exactly one native top module")
        end = text.find("endmodule", top.end())
        if end < 0:
            raise ValueError("native top has no endmodule")
        widths = {}
        for match in B.WIRE_RE.finditer(text[:end]):
            _, hi, lo, name = match.groups()
            widths[name] = (int(lo), int(hi)) if hi is not None else (0, 0)
        instances = {}
        for match in B.INST_RE.finditer(text, top.end(), end):
            name = match.group(3)
            ports = {}
            for line in match.group(4).splitlines():
                port = B.CONN_RE.match(line)
                if port:
                    ports[port.group(1)] = port.group(2)
            if name in instances:
                raise ValueError("duplicate native instance")
            instances[name] = (match, ports)
        sm, source_ports = instances[chain["source_instance"]]
        dm, sink_ports = instances[chain["sink_instance"]]
        source = B.parse_expr(source_ports[chain["source_port"]], widths)
        source_bits = bits(source)
        width = len(source_bits)
        if not width:
            raise ValueError("empty direct source")
        control_mask = chain.get("control_mask", 0)
        if type(control_mask) is not int or control_mask < 0 or control_mask >= (1 << width):
            raise ValueError("control mask outside source width")
        reset = None
        if control_mask:
            if chain.get("reset_kind") != "caller_sync_active_low":
                raise ValueError("control reset needs an explicit caller synchronous active-low contract")
            reset = source_ports[chain["source_reset_port"]]
            if len(bits(B.parse_expr(reset, widths))) != 1:
                raise ValueError("control reset must be an existing one-bit source reset")
        sink = B.parse_expr(sink_ports[chain["sink_port"]], widths)
        sink_width = B.width_of(sink)
        low = chain["sink_lsb"]
        if type(low) is not int or low < 0 or low + width > sink_width:
            raise ValueError("sink slice outside connected port")
        old_bits = bits(B.slice_segs(sink, low, low + width - 1))
        if old_bits != source_bits:
            raise ValueError("requested sink slice is not the exact direct source mapping")
        source_clock = source_ports[chain.get("source_clock_port", "clk")]
        sink_clock = sink_ports[chain.get("sink_clock_port", "clk")]
        clock_bits = bits(B.parse_expr(source_clock, widths))
        if len(clock_bits) != 1 or bits(B.parse_expr(sink_clock, widths)) != clock_bits:
            raise ValueError("source and sink do not share the declared one-bit clock")
        out = prefix + "_out"
        replacement = (B.slice_segs(sink, 0, low - 1) + [("n", out, 0, width - 1)] +
                       B.slice_segs(sink, low + width, sink_width - 1))
        new_expr = expression(replacement)
        conns = dm.group(4)
        pattern = re.compile(r"^(\s*\." + re.escape(chain["sink_port"]) +
                             r"\()(.*)(\),?\s*)$", re.M)
        rewritten, count = pattern.subn(lambda m: m.group(1) + new_expr + m.group(3), conns)
        if count != 1:
            raise ValueError("sink port does not occur exactly once")
        start, stop = dm.span(4)
        text = text[:start] + rewritten + text[stop:]
        names = [prefix + f"_s{index}" for index in range(stages)]
        declarations = [f"  // Direct stations {ident}: +{stages} source cycles, {width}-bit path; data has no reset."]
        declarations += [f'  (* keep = "true", dont_touch = "true" *) reg [{width-1}:0] {n};' for n in names]
        declarations += [f"  wire [{width-1}:0] {out};", f"  assign {out} = {names[-1]};",
                         f"  always @(posedge {source_clock}) begin"]
        # Each individual data bit remains resetless. Only explicitly declared
        # valid/status bits receive the existing delivered synchronous reset.
        # Group contiguous runs to avoid 257 individual bit assignments.
        runs = []
        lo = 0
        for bit in range(1, width + 1):
            if bit == width or bool(control_mask & (1 << bit)) != bool(control_mask & (1 << lo)):
                runs.append((lo, bit - 1, bool(control_mask & (1 << lo))))
                lo = bit
        for index, name in enumerate(names):
            for lo, hi, control in runs:
                lhs = f"{name}[{hi}:{lo}]"
                rhs = (expression(B.slice_segs(source, lo, hi)) if index == 0
                       else f"{names[index-1]}[{hi}:{lo}]")
                if control:
                    declarations += [f"    if (!{reset}) {lhs} <= {hi-lo+1}'b0;",
                                     f"    else {lhs} <= {rhs};"]
                else:
                    declarations += [f"    {lhs} <= {rhs};"]
        declarations += ["  end", ""]
        end = text.find("endmodule", top.end())
        text = text[:end] + "\n" + "\n".join(declarations) + text[end:]
        emitted.append(dict(name=ident, source_instance=chain["source_instance"],
                            source_port=chain["source_port"], source_segments=source,
                            sink_instance=chain["sink_instance"], sink_port=chain["sink_port"],
                            sink_lsb=low, sink_msb=low + width - 1, width=width,
                            source_cycles_before=0, source_cycles_after=stages,
                            added_cycles=stages, register_bits=width * stages,
                            register_names=names, clock=source_clock,
                            reset=reset or "none", control_mask=control_mask,
                            data_reset=False,
                            reset_delivery_qualified=False,
                            parent_budget_qualified=False))
    return text, dict(enabled=True, scope="SOURCE_PREP_ONLY", chains=emitted,
                      qualifies_physical=False, qualifies_token=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("contract", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--enable", action="store_true")
    args = parser.parse_args()
    if args.output.resolve() == args.source.resolve():
        parser.error("output must be a fresh candidate path, not the source")
    contract = json.loads(args.contract.read_text())
    result, receipt = materialize(args.source.read_text(), contract["chains"], enabled=args.enable)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
