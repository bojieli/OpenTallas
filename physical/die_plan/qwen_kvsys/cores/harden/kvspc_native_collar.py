#!/usr/bin/env python3
"""Opt-in input collar in the actual native PC provider, before parent binding.

The physical-kit collar is a prototype of this event, not a substitute for it.
Only the live physical input projection is captured; eliminated native input
bits retain their original connection and clocks/straps remain direct.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

PARAM = "KVSPC_INPUT_COLLAR"
TARGETS = ("qkd_kvs_pc", "qkd_kvs_pc_h_head_p")
PORT = re.compile(r"^\s*(input|output)\s+wire\s*(\[[^]\n]+\])?\s*(\w+)\s*[,)]", re.M)


def projection(module):
    common = [("hrst_n", None, "hrst_n"), ("i_grp", (127, 0), "i_grp"),
              ("pc__cfg_stack", (1, 0), "pc__cfg_stack"),
              ("pc__pi", (288, 0), "pc__pi"),
              ("x__est__0_1", (0, 0), "x__est__0_1"),
              ("pc__hes", (287, 0), "pc__hes"),
              ("i_next", (779, 0), "i_next"),
              ("pc__land_er", (0, 0), "pc__land_er"),
              ("pc__land_er", (260, 259), "pc__land_er_259"),
              ("rst_n", None, "rst_n")]
    if module == "qkd_kvs_pc":
        return common + [("pc__pc", (4, 0), "pc__pc"),
                         ("i_prev", (298, 0), "i_prev"),
                         ("pc__fi", (0, 0), "pc__fi"),
                         ("pc__ki", (32, 0), "pc__ki")]
    if module == "qkd_kvs_pc_h_head_p":
        return common + [("pc__ki", (0, 0), "pc__ki"),
                         ("pc__ki", (20, 15), "pc__ki_15"),
                         ("pc__ki", (32, 31), "pc__ki_31")]
    raise ValueError("not a PC event module: " + module)


def transform(text, module):
    matches = list(re.finditer(r"\bmodule\s+" + re.escape(module) + r"\b", text))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {module} definition")
    a = matches[0].start()
    z = text.index("endmodule", a) + len("endmodule")
    original = text[a:z]
    if PARAM in original or "pcin_native_" in original:
        raise ValueError("native input collar already present")
    header_end = original.index(");") + 2
    header, body = original[:header_end], original[header_end:]
    original_body = body
    ports = {n: (d, w or "") for d, w, n in PORT.findall(header)}
    if ports.get("ck") != ("input", ""):
        raise ValueError("native provider must have its actual scalar ck")
    groups = {}
    for raw, span, canonical in projection(module):
        if raw not in ports or ports[raw][0] != "input":
            raise ValueError("missing actual native input " + raw)
        if span is None and ports[raw][1]:
            raise ValueError("expected scalar native reset " + raw)
        groups.setdefault(raw, []).append((span, canonical))
    declarations = ["\n    // KVSPC_NATIVE_INPUT_COLLAR: parent and physical sources must select exactly once."]
    captures = []
    for raw, rows in groups.items():
        width = ports[raw][1]
        alias = "pcin_native_" + raw
        # Do not rename a named connection's .port label, only actual input uses.
        body = re.sub(r"(?<![.\w])" + re.escape(raw) + r"\b", alias, body)
        declarations.append(f"    wire {width} {alias};")
        declarations.append(f"    generate if ({PARAM}) begin : g_pcin_{raw}")
        bits = {}
        for span, canonical in rows:
            rw = "" if span is None else f"[{span[0]}:{span[1]}]"
            register = "pcin_" + canonical
            source = raw if span is None else f"{raw}{rw}"
            declarations += [f"        (* keep = 1, face_keep = 1 *) reg {rw} {register};",
                             f"        always @(posedge ck) {register} <= {source};"]
            captures.append(dict(port=canonical, native_port=raw, span=span,
                                 width=1 if span is None else span[0]-span[1]+1))
            if span is None:
                bits[None] = register
            else:
                for bit in range(span[1], span[0]+1):
                    if bit in bits:
                        raise ValueError("overlapping captured bit")
                    bits[bit] = f"{register}[{bit}]"
        if width:
            m = re.fullmatch(r"\[(\d+):(\d+)\]", width)
            if not m:
                raise ValueError("nonliteral native width")
            hi, lo = map(int, m.groups())
            if set(bits) - set(range(lo, hi+1)):
                raise ValueError("capture outside actual native width")
            value = "{" + ", ".join(bits.get(bit, f"{raw}[{bit}]")
                                      for bit in range(hi, lo-1, -1)) + "}"
        else:
            value = bits[None]
        declarations += [f"        assign {alias} = {value};", "    end else begin",
                         f"        assign {alias} = {raw};", "    end endgenerate"]
    restored = body
    for raw in groups:
        restored = re.sub(r"\bpcin_native_" + re.escape(raw) + r"\b", raw, restored)
    if restored != original_body:
        raise ValueError("native body changed beyond input reference substitution")
    # Existing HHP PC parameter and all native child parameters remain intact.
    pos = header.index(module) + len(module)
    tail = header[pos:]
    if re.match(r"\s*#\s*\(", tail):
        k = pos + re.search(r"#\s*\(", tail).end()
        header = header[:k] + f"\n    parameter {PARAM} = 0," + header[k:]
    else:
        header = header[:pos] + f" #(parameter {PARAM} = 0)" + header[pos:]
    output = text[:a] + header + "\n".join(declarations) + "\n" + body + text[z:]
    receipt = dict(schema="opentallas.kvspc.native_input_collar.v1", module=module,
                   parameter=PARAM, default=0, input_cycles=1, boot_cycles=1,
                   throughput_cycles=0, captures=captures,
                   flops=sum(r["width"] for r in captures),
                   source_before=hashlib.sha256(text.encode()).hexdigest(),
                   source_after=hashlib.sha256(output.encode()).hexdigest(),
                   body_change="input references only; same native leaf arithmetic/control",
                   clocks_direct=["ck", "hck"], dead_bits="original direct connection")
    return output, receipt


def regen_parameters(ctx):
    """Compose into the existing param_regen hook, after all existing rules."""
    selected = [c for c in ctx.F.cells if c.module in TARGETS]
    if not selected or {c.module for c in selected} != set(TARGETS):
        raise ValueError("native collar event requires actual PC and HHP leaves")
    params = {}
    for c in selected:
        defaults = ctx.param_defaults.get((c.ytype, c.module), {})
        if PARAM not in defaults and PARAM not in c.params:
            raise ValueError(f"{c.path}: native provider lacks {PARAM}; install source before binding")
        if str(c.params.get(PARAM, defaults.get(PARAM))).strip('"') not in ("0", "1"):
            raise ValueError("nonliteral collar selection")
        params[c.path] = {PARAM: 1}
    return dict(params=params, record=dict(parameter=PARAM, value=1,
                input_cycles=1, boot_cycles=1, throughput_cycles=0,
                instances=[dict(path=c.path, module=c.module) for c in selected],
                rule="one capture per instantiated PC type, never add two for two types"))


def enabled_in_wrapper(text):
    return bool(re.search(r"\." + PARAM + r"\s*\(\s*(?:(?:\d+)'s?[db])?1\s*\)", text))


def physical_receipt(module):
    captures = [dict(port=canonical, width=1 if span is None else span[0]-span[1]+1,
                     register="native.pcin_" + canonical)
                for _, span, canonical in projection(module)]
    return dict(schema="opentallas.kvspc.input_collar.v1", enabled=True,
                source="actual native provider parameter KVSPC_INPUT_COLLAR=1",
                outer_collar_added=False, input_cycles=1, boot_cycles=1,
                throughput_cycles=0, flops=sum(r["width"] for r in captures),
                captured=captures, default_enabled=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--module", choices=TARGETS, required=True)
    a = ap.parse_args()
    text, receipt = transform(a.source.read_text(), a.module)
    a.output.write_text(text)
    a.output.with_suffix(a.output.suffix + ".collar.json").write_text(json.dumps(receipt, indent=2)+"\n")


if __name__ == "__main__":
    main()
