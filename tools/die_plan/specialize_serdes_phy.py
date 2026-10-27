#!/usr/bin/env python3
"""Bind a native SD kit's x6 PHY to its exact fixed-W physical master.

The functional die bind is untouched. Only the kit-local provider definition
becomes a wire-only dispatcher to the declared physical view. The original W,
every port and the CDC wrapper stay unchanged. No PG or timing qualification is
implied by this source specialization.
"""
import argparse
import ast
import hashlib
import json
import re
import shutil
from pathlib import Path

LOGICAL = "ot_qfd_serdes_112g_x6_phy"
WRAPPER = LOGICAL + "_c45"


def ports(width):
    return dict(clk=("input", 1), rst_n=("input", 1), tx_up=("output", 1),
                tx_v=("input", 1), tx_flit=("input", width),
                rx_v=("output", 1), rx_flit=("output", width))


def expression(text, width):
    def value(node):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            return node.value
        if isinstance(node, ast.Name) and node.id == "W":
            return width
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
            a, b = value(node.left), value(node.right)
            return a + b if isinstance(node.op, ast.Add) else a - b
        raise ValueError(f"unsupported PHY width expression {text}")
    return value(ast.parse(text.strip(), mode="eval").body)


def module_match(text, name):
    return re.search(r"^[ \t]*(?:\(\*[^\n]*?\*\)\s*)?module\s+" + re.escape(name) +
                     r"\b.*?^[ \t]*endmodule\b[^\n]*", text, re.M | re.S)


def header_ports(text, name, width):
    match = module_match(text, name)
    if not match:
        raise ValueError(f"missing provider definition {name}")
    body = re.sub(r"//[^\n]*|/\*.*?\*/", "", match.group(), flags=re.S)
    pos = body.index(name) + len(name)
    while body[pos].isspace():
        pos += 1
    def parens(i):
        if body[i] != "(":
            raise ValueError("expected PHY header parentheses")
        start, depth = i + 1, 1
        for j in range(start, len(body)):
            depth += (body[j] == "(") - (body[j] == ")")
            if not depth:
                return body[start:j], j + 1
        raise ValueError("unclosed PHY header")
    if body[pos] == "#":
        pos += 1
        while body[pos].isspace():
            pos += 1
        _, pos = parens(pos)
        while body[pos].isspace():
            pos += 1
    header, _ = parens(pos)
    result, direction, count = {}, None, 1
    for field in header.split(","):
        field = field.strip()
        found = re.match(r"(input|output)\b\s*(.*)", field, re.S)
        if found:
            direction, field, count = found.group(1), found.group(2), 1
        field = re.sub(r"\b(wire|logic|reg|signed|unsigned)\b", "", field).strip()
        found = re.match(r"\[([^:]+):([^]]+)\]\s*(.*)", field, re.S)
        if found:
            count = abs(expression(found.group(1), width) - expression(found.group(2), width)) + 1
            field = found.group(3).strip()
        if direction is None or not re.fullmatch(r"[A-Za-z_]\w*", field):
            raise ValueError("PHY specialization requires an explicit ANSI port declaration")
        if field in result:
            raise ValueError("duplicate PHY port")
        result[field] = (direction, count)
    return result


def dispatcher(width, master):
    if width not in (521, 522) or master != LOGICAL + f"_w{width}":
        raise ValueError("unsupported x6 PHY specialization")
    return f"""// GENERATED: exact kit-only physical view; functional die source is unchanged.
module {LOGICAL} #(parameter integer W={width})(
 input wire clk, rst_n, output wire tx_up, input wire tx_v,
 input wire [W-1:0] tx_flit, output wire rx_v,
 output wire [W-1:0] rx_flit);
 generate if (W == {width}) begin:g_native
  {master} u_macro (.clk(clk), .rst_n(rst_n), .tx_up(tx_up),
   .tx_v(tx_v), .tx_flit(tx_flit), .rx_v(rx_v), .rx_flit(rx_flit));
 end else begin:g_wrong_width
  OT_ERROR_UNSUPPORTED_SERDES_PHY_WIDTH u_error();
 end endgenerate
endmodule
"""


def specialize(kit, view_root):
    kit, view_root = Path(kit).resolve(), Path(view_root).resolve()
    manifest_path = kit / "kit_rtl.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("physical_specializations"):
        raise ValueError("kit already specialized; use a fresh native kit")
    files = [Path(p) for p in manifest["files"]]
    bound = [p for p in files if p.stem == manifest["bound_module"]]
    if len(bound) != 1:
        raise ValueError("native bound module is not unique")
    instances = re.findall(r"\b" + WRAPPER + r"\s*#\(\s*\.W\(\s*(\d+)\s*\)\s*\)\s+(\w+)\s*\(", bound[0].read_text())
    if len(instances) != 1 or int(instances[0][0]) not in (521, 522):
        raise ValueError("SD kit must contain exactly one native c45 PHY with literal W=521 or 522")
    width, instance = int(instances[0][0]), instances[0][1]
    master = LOGICAL + f"_w{width}"
    view = view_root / master
    bb, lef = view / f"{master}_bb.v", view / f"{master}.lef"
    libs = [view / f"{master}_{corner}.lib" for corner in ("tt", "ff")]
    if not all(p.is_file() for p in (bb, lef, *libs)):
        raise ValueError("fixed physical view lacks BB, LEF or TT/FF library")
    if header_ports(bb.read_text(), master, width) != ports(width):
        raise ValueError("fixed physical view ABI differs from the native seven-port provider")
    definitions = [(p, module_match(p.read_text(), LOGICAL)) for p in files]
    definitions = [(p, m) for p, m in definitions if m]
    if len(definitions) != 1:
        raise ValueError("native raw PHY provider definition is missing or duplicated")
    original, match = definitions[0]
    text = original.read_text()
    if header_ports(text, LOGICAL, width) != ports(width):
        raise ValueError("original provider ABI differs from the declared physical view")
    # Validate all inputs before writing any kit-local replacement.
    target = kit / "physical_specialization"
    target.mkdir()
    stripped = target / ("provider_" + original.name)
    stripped.write_text(text[:match.start()] + "// Raw PHY replaced by exact fixed-W physical dispatcher.\n" + text[match.end():])
    wrapper = target / f"{LOGICAL}_physical.sv"
    wrapper.write_text(dispatcher(width, master))
    local_bb = target / bb.name
    shutil.copyfile(bb, local_bb)
    updated = [str(stripped) if p == original else str(p) for p in files] + [str(wrapper), str(local_bb)]
    record = dict(logical_module=LOGICAL, parameters=dict(W=width), physical_master=master,
                  original_source=str(original), source_sha256=hashlib.sha256(text.encode()).hexdigest(),
                  native_base_instance=f"u_bound.{instance}.u_phy",
                  expected_physical_instance=f"u_bound.{instance}.u_phy.g_native.u_macro",
                  actual_physical_instance_check="OWED after synthesis", added_cycles=0, added_state=0)
    manifest["files"] = updated
    manifest.setdefault("hard_macros", {}).pop(LOGICAL, None)
    manifest["hard_macros"][master] = dict(dir=str(view), bb=str(local_bb), model=None,
                                           lef=str(lef), libs=[str(p) for p in libs],
                                           logical_module=LOGICAL, parameters=dict(W=width))
    manifest["physical_specializations"] = [record]
    (kit / "kit_rtl.f").write_text("\n".join(updated) + "\n")
    # The prior raw PHY was also opaque; no new analog simulation model is claimed.
    (kit / "kit_rtl_sim.f").write_text("\n".join(updated) + "\n")
    manifest_path.write_text(json.dumps(manifest, indent=1) + "\n")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kit")
    parser.add_argument("view_root")
    args = parser.parse_args()
    print(json.dumps(specialize(args.kit, args.view_root), indent=1))
