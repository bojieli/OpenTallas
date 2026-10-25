#!/usr/bin/env python3
"""KV-CORES 10-25 ECTLK face ports (kit-copy RTL transform; module names / ports / cycles unchanged).

The 3-root ECTLK synth preflight (face_guard) found live output regs that also feed core logic ("shared"):
  * ot_qkd_ectl_part : sc_valid, sc_data, lmax, lmax_any, fault   (so[13], so[153:26], so[281:154], so[411:410], so[412])
  * qkd_static_k_issuer : req_valid, req_t, req_epoch, req_layer, fault (fault is sticky: its own hold loop)
and one input strap landing in three leaves (cfg[4:0] -> leaf A / B / C, one per ck root).
Fix (industry practice: private output flops, register duplication):
  * every such output becomes a private port flop loaded only by its pin; the logic keeps an internal copy `<name>_i`
    with the identical next-state (same edge, same reset). Sticky / held state of the port copy is taken from the
    internal copy (`port <= port_i` default), so the port flop has no feedback loop and both stay equal on every edge.
  * cfg lands once at the core top (qkd_ectl3_kiss_st, on ck[0]) and that one flop feeds the three leaves. cfg is a
    static strap: the one extra settle edge after a strap change is not a schedule cycle (OWNER? noted in the report).
`MUT` (tb only) injects one error into the port copies so the miter proves it observes them.
"""
import re
import sys
from pathlib import Path


def _module(text, name):
    i = text.index("module " + name + " ")
    j = text.index("endmodule", i) + len("endmodule")
    return i, j


def _rename_body(body, names):
    pat = re.compile(r"(?<![.\w])(" + "|".join(sorted(names, key=len, reverse=True)) + r")(?!\w)")
    return pat.sub(lambda m: m.group(1) + "_i", body)


def _keep_ports(head, names):
    # yosys opt_merge would fold a port flop and its equal-next-state internal copy back into one: keep both
    pat = re.compile(r"(?<![\w*] )(output reg\b(?:\s*\[[^\]]*\])?\s*(?:" + "|".join(names) + r")\b)")
    out, n = pat.subn(lambda m: "(* keep *) " + m.group(1), head)
    assert n == len(names), (n, names)
    return out


def ectl_part(text, mut=False):
    name = "ot_qkd_ectl_part"
    i, j = _module(text, name)
    s = text[i:j]
    h = s.index("\n);\n") + len("\n);\n")
    head, body = s[:h], s[h:]
    names = ["sc_valid", "sc_data", "lmax_any", "lmax", "fault"]
    head = _keep_ports(head, names)
    body = _rename_body(body, names)
    decl = ("    // KV-CORES 10-25 ECTLK face ports: internal copies of the port regs (the port regs are private pin flops)\n"
            "    (* keep *) reg sc_valid_i; (* keep *) reg [127:0] sc_data_i; (* keep *) reg [2*4*32-1:0] lmax_i;\n"
            "    (* keep *) reg [1:0] lmax_any_i; (* keep *) reg fault_i;\n")
    body = decl + body
    # the lmax / lmax_any / fault block, renamed: copy it for the port flops
    b0 = body.index("    integer hh;\n")
    b1 = body.index("endmodule")
    blk = body[b0:b1]
    assert blk.count("always @(posedge clk or negedge rsc) begin") == 1, "lmax block"
    cp = blk.replace("integer hh;", "integer hp;").replace("hh", "hp")
    subs = [
        ("if (!rsc) begin lmax_i <= 0; lmax_any_i <= 2'b00; fault_i <= 1'b0; end\n        else begin\n",
         "if (!rsc) begin lmax <= 0; lmax_any <= 2'b00; fault <= 1'b0; end\n        else begin\n"
         "            lmax <= lmax_i; lmax_any <= lmax_any_i; fault <= fault_i;\n"),
        ("if (start) begin lmax_any_i <= 2'b00; fault_i <= 1'b0; end",
         "if (start) begin lmax_any <= 2'b00; fault <= 1'b0; end"),
        ("lmax_i[32*(4*sc_addr[11] + hp) +: 32] <= sc_data_i[32*hp +: 32]",
         "lmax[32*(4*sc_addr[11] + hp) +: 32] <= sc_data_i[32*hp +: 32]" + (" ^ 32'd1" if mut else "")),
        ("lmax_any_i[sc_addr[11]] <= 1'b1;", "lmax_any[sc_addr[11]] <= 1'b1;"),
        (") fault_i <= 1'b1;", ") fault <= 1'b1;"),
    ]
    for a, b in subs:
        assert cp.count(a) == 1, a
        cp = cp.replace(a, b)
    assert "lmax_i <=" not in cp.replace("lmax <= lmax_i", "") and "fault_i <=" not in cp, "port copy still writes internals"
    sv_old = ("        if (!rsc) begin sc_valid_i <= 1'b0; tf2 <= 1'b0; end\n"
              "        else begin sc_valid_i <= sc_v_n; tf2 <= |t_sf; end\n")
    sd_old = "    always @(posedge clk) begin sc_data_i <= t_sc; sc_addr <= tag_sc; end\n"
    assert body.count(sv_old) == 1 and body.count(sd_old) == 1
    port = ("    // KV-CORES 10-25 ECTLK face ports: private port flops (same edge, same next state as the *_i copies)\n"
            "    always @(posedge clk or negedge rsc)\n"
            "        if (!rsc) sc_valid <= 1'b0; else sc_valid <= sc_v_n;\n"
            "    always @(posedge clk) sc_data <= t_sc;\n" + cp)
    body = body[:b1] + port + body[b1:]
    s = head + body
    return text[:i] + s + text[j:]


def k_issuer(text, mut=False):
    name = "qkd_static_k_issuer"
    i, j = _module(text, name)
    s = text[i:j]
    h = s.index("\n);\n") + len("\n);\n")
    head, body = s[:h], s[h:]
    # vectors: keep the port flops; scalar core-pin ports (req_valid, fault) are NOT kept (a kept scalar port net gets a
    # dangling alias buffer that face_guard counts as a second load); their internal copies are kept instead.
    head = _keep_ports(head, ["req_t", "req_epoch", "req_layer"])
    # req_valid: the internal copy uses a synchronous clear by rn (rn is itself a ck flop, so the async clear of the
    # port flop and the sync clear agree at every edge once rn has been low for one edge); the different D structure
    # keeps opt_merge from folding them without a kept alias net (a kept scalar port name gets a dangling buffer).
    old_v = " always @(posedge ck or negedge rn)\n  if(!rn)req_valid<=0;\n  else req_valid<=rq[0];\n"
    assert body.count(old_v) == 1
    body = body.replace(old_v, " always @(posedge ck) req_valid<=rn&&rq[0];\n")
    body = _rename_body(body, ["req_valid", "req_t", "req_epoch", "req_layer", "fault"])
    m = re.search(r"\n   if\((.*?)\)fault_i<=1;\n", body, re.S)
    assert m, "fault condition"
    cond = m.group(1)
    old_d = "  req_t_i<={1'b0,rq[15:3]};req_epoch_i<=ep;req_layer_i<=(MUT==1)?(ly^6'd1):ly;\n"
    assert body.count(old_d) == 1
    xr = " ^ 1'b1" if mut else ""
    port = (" // KV-CORES 10-25 ECTLK face ports: private port flops (same edge, same next state as the *_i copies)\n"
            " always @(posedge ck) begin req_t<={1'b0,rq[15:3]};req_epoch<=ep;req_layer<=(MUT==1)?(ly^6'd1):ly; end\n"
            " always @(posedge ck or negedge rn) if(!rn) req_valid<=0; else req_valid<=rq[0];\n"
            " always @(posedge ck or negedge rn)\n"
            "  if(!rn) fault<=0;\n"
            f"  else fault<=fault_i || ({cond}){xr};\n")
    e = body.index("endmodule")
    body = (" (* keep *) reg req_valid_i; (* keep *) reg [13:0] req_t_i; (* keep *) reg [15:0] req_epoch_i; (* keep *) reg [5:0] req_layer_i;"
            " (* keep *) reg fault_i;  // KV-CORES 10-25 internal copies\n"
            + body[:e] + port + body[e:])
    s = head + body
    return text[:i] + s + text[j:]


def cfg_land(text):
    name = "qkd_ectl3_kiss_st"
    i, j = _module(text, name)
    s = text[i:j]
    assert s.count(".cfg(cfg)") == 3, "three leaf cfg bindings"
    s = s.replace(".cfg(cfg)", ".cfg(cfg_q)")
    h = s.index(");\n") + len(");\n")
    s = (s[:h] + "    // KV-CORES 10-25: the static strap lands once (one landing flop per pin); that flop feeds the three leaves\n"
         "    (* keep *) reg [4:0] cfg_q;\n    always @(posedge ck[0]) cfg_q <= cfg;\n" + s[h:])
    return text[:i] + s + text[j:]


def apply_kit(rtl_dir, mut=False, cfg=True):
    d = Path(rtl_dir)
    p = d / "ot_qkd_ectl_parts.sv"
    p.write_text(ectl_part(p.read_text(), mut))
    p = d / "qkd_static_k_issuer.sv"
    p.write_text(k_issuer(p.read_text(), mut))
    if cfg:
        p = d / "qkd_static_ectl_st.sv"
        p.write_text(cfg_land(p.read_text()))


if __name__ == "__main__":
    apply_kit(sys.argv[1], len(sys.argv) > 2 and sys.argv[2] == "mut")
