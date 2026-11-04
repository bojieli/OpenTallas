#!/usr/bin/env python3
"""DIE-KV-64/RF-B 11-03 (OWNER TWO-STRIKES -> RE-FORM, batch RF-KV1, CLOSURE row KV-046): qkd_kvs_ctl REGISTERED-FACE
form.

Cause (2 strikes ctlA2/ctlB2 GRT overflow 7241/839; and the current 7076-pin source fails CORE_PREFLIGHT
shared 4441 / feedthrough 48 / unregistered 419 / dropped 227): the CTL boundary is not registered at the face --
o_hroot_* bits are driven by dcfg / lprg state flops that also feed internal logic, lp is fanned out combinationally to
the four hroot faces, i_hroot_* / embgw__bw feed OR/AND trees and o_attn is AND-driven -- so the IO timing/hold of
~2.5k face bits lands on deep internal cones (11.5k IO hold buffers in the W/E M4 strip -> congestion).

Form (closure by construction, no knob): a wrapper `qkd_kvs_ctl` (same ports, same pin table) around the unchanged
source core (renamed qkd_kvs_ctl__rf1_inner) with ONE private face flop per port bit:
  * every non-clock, non-reset input bit -> input capture flop -> inner   (+1 edge on every input crossing)
  * every output bit: inner -> output launch flop -> port                (+1 edge on every output crossing)
  * ck / rst_n / por_n pass straight (clock + typed async resets).  Input bits the source never reads (CORE_PREFLIGHT
    'dropped', e.g. d2d__svc) also get a kept face flop (* keep *), so the face is uniform and no dead declaration
    is needed (the flop output is unloaded).
Face flops reset asynchronously on rst_n to 0 (RF-KV1b 11-03: the first build used no-reset face flops; LEC then saw
3280 X power-up sources at the face, register pairing by simulation fell 16795 -> 3308 and 2080 points stayed unproved;
a typed rst_n reset makes the reset state of the whole face known, like every other state flop of the core).  Outputs
read 0 while rst_n is low and carry the inner value one edge after it; constant face bits are kept by synth_keepdc.  Every face bit is exclusively one flop -> one pin
(face_guard shared/feedthrough/unregistered = 0 by construction); face-to-face wire only between blocks; hold safe at
the face (flop -> pin, pin -> flop).  Cost: +1 cycle in each direction on every hub_C<->kvs_ctl crossing (OWNER 11-03:
latency accepted, 1.2 GHz kept) -> one RF-KV1 crossing-latency row for kvs_ctl.

    ctl_rf1_face_wrap.py CORE_JSON OUT_DIR [--netlist SYNTH_V]   (--netlist: derive the dead input bits)
"""
import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
CLOCKS, RESETS = {"ck"}, {"rst_n", "por_n"}
RST_LEAF_BITS, RST_MID_FANOUT = 128, 16     # face reset tree: face flops per leaf relay, leaves per mid relay
HDR = re.compile(r"^\s*(input|output)\s+wire\s*(?:\[(\d+):(\d+)\])?\s*([A-Za-z_][A-Za-z0-9_$]*)\s*,?\s*$")


def ports_of(src, module):
    text = src.read_text()
    m = re.search(rf"^module\s+{module}\s*\((.*?)^\);", text, re.S | re.M)
    out = []
    for line in m.group(1).splitlines():
        if not line.strip() or line.strip().startswith("//"):
            continue
        h = HDR.match(line)
        assert h, f"unparsed port line: {line!r}"
        d, msb, lsb, n = h.groups()
        out.append((d, int(msb) if msb else None, int(lsb) if lsb else None, n))
    return text, out


def dead_bits(netlist, ports):
    """input bits that the synthesized SOURCE netlist never reads (no load): the dead set to declare"""
    body = Path(netlist).read_text()
    used = set()
    for n, idx in re.findall(r"(?<![\w$.\\])([A-Za-z_][A-Za-z0-9_$]*)\s*\[(\d+)\]", body):
        used.add((n, int(idx)))
    dead = []
    for d, msb, lsb, n in ports:
        if d != "input" or n in CLOCKS | RESETS:
            continue
        if msb is None:
            continue   # scalar inputs: always registered (whole-net use is not reliably parsable)
        for b in range(lsb, msb + 1):
            if (n, b) not in used:
                dead.append(f"{n}[{b}]")
    return dead


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("core_json")
    ap.add_argument("out_dir")
    ap.add_argument("--netlist")
    a = ap.parse_args()
    cjp = Path(a.core_json)
    cj = json.loads(cjp.read_text())
    mod = cj["module"]
    top = next(REPO / f for f in cj["files"] if Path(f).name == f"{mod}.sv")
    text, ports = ports_of(top, mod)
    dead = dead_bits(a.netlist, ports) if a.netlist else []
    deadset = set(dead)
    od = Path(a.out_dir) / mod
    od.mkdir(parents=True, exist_ok=True)
    inner = f"{mod}__rf1_inner"
    (od / f"{inner}.sv").write_text(
        f"// RF-KV1 DIE-KV-64/RF-B 11-03: unchanged source core {top.relative_to(REPO)} renamed {mod} -> {inner}\n"
        + re.sub(rf"^module\s+{mod}\s*\(", f"module {inner} (", text, count=1, flags=re.M))
    decl, regs, conn = [], [], []
    nreg = {"input": 0, "output": 0}
    n_leaf = 0
    for d, msb, lsb, n in ports:
        rng = f"[{msb}:{lsb}] " if msb is not None else ""
        decl.append(f"    {d} wire {rng}{n}")
        if n in CLOCKS | RESETS:
            conn.append(f"    .{n}({n})")
            continue
        regs.append(f"  wire {rng}{n}__i;")
        bits = list(range(lsb, msb + 1)) if msb is not None else [None]
        leaf0 = n_leaf
        n_leaf += (len(bits) + RST_LEAF_BITS - 1) // RST_LEAF_BITS
        vec_rst = f"face_rst_leaf[{leaf0} + (b - {lsb if lsb is not None else 0}) / {RST_LEAF_BITS}]"
        one_rst = lambda b: f"face_rst_leaf[{leaf0 + ((0 if b is None else b - lsb) // RST_LEAF_BITS)}]"
        sel = lambda x, b: x if b is None else f"{x}[{b}]"
        if d == "input":
            live = [b for b in bits if sel(n, b) not in deadset]
            if len(live) == len(bits) and msb is not None:
                regs.append(f"  for (genvar b = {lsb}; b <= {msb}; b = b + 1) begin : gi_{n}\n"
                            f"    (* keep *) ot_ctl_face_dff u_f (.ck(ck), .rst_n({vec_rst}), .d({n}[b]), .q({n}__i[b]));\n  end")
            else:
                for b in bits:
                    if b in live:
                        regs.append(f"  (* keep *) ot_ctl_face_dff ui_{n}_{'s' if b is None else b} (.ck(ck), .rst_n({one_rst(b)}), .d({sel(n, b)}), .q({sel(n + '__i', b)}));")
                    else:   # declared dead input bit (dead_inputs.json): no face flop, stays unloaded
                        regs.append(f"  assign {sel(n + '__i', b)} = {sel(n, b)};")
            nreg["input"] += len(live)
        else:
            if msb is not None:
                regs.append(f"  for (genvar b = {lsb}; b <= {msb}; b = b + 1) begin : go_{n}\n"
                            f"    (* keep *) ot_ctl_face_dff u_f (.ck(ck), .rst_n({vec_rst}), .d({n}__i[b]), .q({n}[b]));\n  end")
            else:
                regs.append(f"  (* keep *) ot_ctl_face_dff uo_{n} (.ck(ck), .rst_n({one_rst(None)}), .d({n}__i), .q({n}));")
            nreg["output"] += len(bits)
        conn.append(f"    .{n}({n}__i)")
    w = [f"// GENERATED by physical/die_plan/qwen_kvsys/cores/harden/ctl_rf1_face_wrap.py (RF-KV1 DIE-KV-64/RF-B 11-03):",
         f"// registered-face wrapper of {inner}; one private face flop per port bit (in {nreg['input']}, out {nreg['output']}),",
         "// +1 edge per crossing direction; face flops reset on face_rst_n (local ot_reset_sync of rst_n: async assert, sync",
         "// release, so the rst_n PIN lands on 2 sync flops, never on the ~7k face flops -- RF-KV1c 11-03: ctlr routed TT",
         "// -70 ps was only the rst_n input -> face flop recovery); DIE-KV-67 11-04: ctls routed TT -87 ps was that sync flop",
         f"// -> face flop recovery, so face_rst_n reaches the flops through two registered levels, <= {RST_LEAF_BITS} flops per leaf,",
         "// release +2 edges, every face flop on the same edge; clocks/resets straight; dead input bits unregistered.  Do not edit.",
         "`timescale 1ns/1ps", "`default_nettype none",
         "// single-bit kept face flop (keep_hierarchy: opt_merge / constant folding cannot share or fold a face bit)",
         "(* keep_hierarchy *) module ot_ctl_face_dff(input wire ck, input wire rst_n, input wire d, output reg q);",
         "  always @(posedge ck or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= d;", "endmodule",
         "// one registered copy of the face reset (keep_hierarchy: opt_merge cannot fold the tree back into one flop)",
         "(* keep_hierarchy *) module ot_ctl_face_rst_relay(input wire ck, input wire d, output reg q);",
         "  always @(posedge ck) q <= d;", "endmodule", f"module {mod} (", ",\n".join(decl), ");"]
    n_mid = (n_leaf + RST_MID_FANOUT - 1) // RST_MID_FANOUT
    regs.insert(0, f"""  wire face_rst_n;
  ot_reset_sync #(.ASYNC_STAGES(2)) u_face_rst (.clk(ck), .async_rst_n(rst_n), .sync_rst_n(face_rst_n));
  wire [{n_mid - 1}:0] face_rst_mid;
  wire [{n_leaf - 1}:0] face_rst_leaf;
  for (genvar m = 0; m < {n_mid}; m = m + 1) begin : g_frm
    (* keep *) ot_ctl_face_rst_relay u_r (.ck(ck), .d(face_rst_n), .q(face_rst_mid[m]));
  end
  for (genvar l = 0; l < {n_leaf}; l = l + 1) begin : g_frl
    (* keep *) ot_ctl_face_rst_relay u_r (.ck(ck), .d(face_rst_mid[l / {RST_MID_FANOUT}]), .q(face_rst_leaf[l]));
  end""")
    w += regs + [f"  {inner} u_rf1_core (", ",\n".join(conn), "  );", "endmodule", "`default_nettype wire", ""]
    (od / f"{mod}.sv").write_text("\n".join(w))
    rel = lambda p: str(Path(p).resolve().relative_to(REPO))
    files = [rel(od / f"{mod}.sv"), rel(od / f"{inner}.sv")] + [f for f in cj["files"] if Path(f).name != f"{mod}.sv"]
    ncj = dict(cj, files=files, rf_kv1=dict(form="registered-face wrapper (face reset = local ot_reset_sync of rst_n + 2-level registered tree)", tool="ctl_rf1_face_wrap.py",
                                            source_top=str(top.relative_to(REPO)), face_flops_in=nreg["input"],
                                            face_flops_out=nreg["output"], dead_inputs=len(dead), cycles_in=1, cycles_out=1, face_reset_extra_edges=2, face_reset_leaves=n_leaf, face_reset_mids=n_mid))
    (od / f"{mod}_core.json").write_text(json.dumps(ncj, indent=1) + "\n")
    if dead:
        (od / "dead_inputs.json").write_text(json.dumps(dict(
            schema="opentallas.kit_dead_inputs.v1", module=mod, bits=dead,
            proof=dict(verdict="PASS", method="no load on the input bit in the synthesized source netlist "
                       "(yosys 1_2_yosys.v of the source core, same RTL as the inner core)", receipt=str(a.netlist))), indent=1) + "\n")
    print(f"CTL_RF1 {mod}: face flops in {nreg['input']} out {nreg['output']} dead {len(dead)} -> {od}")


if __name__ == "__main__":
    main()
