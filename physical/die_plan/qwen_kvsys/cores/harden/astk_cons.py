"""DIE-KV-64/RF-E 11-03 CONSERVATIVE form of kv3_astk (OWNER 19:00 directive; on top of RF-KV1 astk_rf1.py).

Blocker class FEED-FORWARD ([CHECKED] rfA signoff TT -17.94: u_leaf.m2.zq[3] -> fanout tree 17/44/64 loads -> 16:1 x 128-b
sd[k] read mux -> u_leaf.m2.oa[30]).  Every Z tree node (qkd_astk_zn m2..m4 and the chain head qkd_astk_zn_head_p m1)
keeps a 16-entry x 128-b operand store sd addressed by the binary k = zq[5:2]: one flop bit drives ~1000 read-mux loads
plus the 16 x 128 write enables, and slot[0] / put drive 256 + 2048 loads.

Form (exact, 0 command / token cycles): the store becomes 8 column slices of 16 b; each slice owns a kept
(keep_hierarchy) replica register captured on the SAME edge as zq from the value zq loads (zi in qkd_astk_zn, whose zi is
the previous node's zo register; zl, the pin landing register, in the chain head):
    koh = onehot(k) (16 b, <= 16 read AND loads + 1 write-enable gate per bit), s0 = slot[0], pv = zq[0] && !slot[0]
    (async reset with rn_q exactly like zq[0]).
  write : sd_s[j] <= d_s   when pv_s && (stl == 0) && pb && koh_s[j]       (== put && k == j)
  read  : oa_s <= s0_s ? OR_j(koh_s[j] & sd_s[j]) : d_s ; ob_s <= s0_s ? d_s : 0   (== slot[0] ? sd[k] : d)
pb (cb vs T compare) and the sv / f / ot / ov logic are untouched (binary k, 16 b).  Added flops per node 8 x 18 = 144.
"""
import hashlib
import json
import re
from pathlib import Path

ZN_OLD = [
    ("    reg  [127:0] sd [0:15];\n", ""),
    ("        if (put) sd[k] <= d;\n", ""),
    ("        oa <= slot[0] ? sd[k] : d;\n", ""),
    ("        ob <= slot[0] ? d : 128'd0;\n", ""),
]
NS = 8
W = 128 // NS


def block(src):
    return f"""    // CONS (DIE-KV-64/RF-E 11-03, astk_cons.py): sliced operand store, same-edge kept one-hot replicas per slice
    // (captured from {src}, the value zq loads): koh == onehot(k), cs0 == slot[0], cpv == zq[0] && !slot[0]
    wire [15:0] cons_koh_d = 16'd1 << {src}[5:2];
    wire        cons_s0_d = {src}[6];
    wire        cons_pv_d = {src}[0] && !{src}[6];
    wire        cons_wq = (stl == 6'd0) && pb;
    genvar cs, ce;
    generate for (cs = 0; cs < {NS}; cs = cs + 1) begin : g_cs
        wire [15:0] koh; wire cs0, cpv;
        (* keep_hierarchy *) qkd_astk_cons_zrep u_rep (.ck(ck), .rn(rn_q), .koh_d(cons_koh_d), .s0_d(cons_s0_d),
            .pv_d(cons_pv_d), .koh(koh), .s0(cs0), .pv(cpv));
        wire        wen = cpv && cons_wq;
        wire [{16*W-1}:0] ef;
        for (ce = 0; ce < 16; ce = ce + 1) begin : g_e
            reg [{W-1}:0] e;
            always @(posedge ck) if (wen && koh[ce]) e <= d[{W}*cs +: {W}];
            assign ef[{W}*ce +: {W}] = e;
        end
        reg [{W-1}:0] rmux;
        integer ri;
        always @* begin
            rmux = {W}'d0;
            for (ri = 0; ri < 16; ri = ri + 1) rmux = rmux | ({{{W}{{koh[ri]}}}} & ef[{W}*ri +: {W}]);
        end
        always @(posedge ck) begin
            oa[{W}*cs +: {W}] <= cs0 ? rmux : d[{W}*cs +: {W}];
            ob[{W}*cs +: {W}] <= cs0 ? d[{W}*cs +: {W}] : {W}'d0;
        end
    end endgenerate
"""


REP_MOD = """
// CONS (DIE-KV-64/RF-E 11-03): Z node store select replicas; a keep_hierarchy module instance is never merged
(* keep_hierarchy *) module qkd_astk_cons_zrep (input wire ck, input wire rn, input wire [15:0] koh_d, input wire s0_d,
    input wire pv_d, output reg [15:0] koh, output reg s0, output reg pv);
    always @(posedge ck) begin koh <= koh_d; s0 <= s0_d; end
    always @(posedge ck or negedge rn) if (!rn) pv <= 1'b0; else pv <= pv_d;
endmodule
"""


def zn_transform(text, name, src):
    m = re.search(rf"^module {name}\b", text, re.M)
    if not m or len(re.findall(rf"^module {name}\b", text, re.M)) != 1:
        raise ValueError(f"astk_cons: expected one module {name}")
    j = text.index("endmodule", m.start())
    s = text[m.start():j]
    if "cons_" in s:
        raise ValueError(f"astk_cons: {name} already transformed")
    for a, _ in ZN_OLD:
        if s.count(a) != 1:
            raise ValueError(f"astk_cons: {name}: expected exactly one {a.strip()!r}")
    for need in ("wire        pb = ", "wire         put = v && !slot[0] && pb;", "wire        v = zq[0] && stl == 6'd0",
                 "wire [3:0]  k = zq[5:2], slot = zq[9:6];", f"zq[137:1] <= {src}[137:1]", f"zq[0] <= {src}[0]"):
        if need not in s:
            raise ValueError(f"astk_cons: {name}: {need!r} not found")
    # sd is used nowhere else
    s2 = s
    for a, b in ZN_OLD:
        s2 = s2.replace(a, b, 1)
    if re.search(r"\bsd\b", s2.replace("// ", "")):
        raise ValueError(f"astk_cons: {name}: sd still referenced")
    anchor = "    always @(posedge ck) begin\n        ot <= "
    if s2.count(anchor) != 1:
        raise ValueError(f"astk_cons: {name}: ot anchor missing")
    s2 = s2.replace(anchor, block(src) + anchor, 1)
    return text[:m.start()] + s2 + text[j:]


def apply_kit(kd, mod):
    kd = Path(kd)
    if mod != "kv3_astk":
        raise SystemExit("--astk-cons only applies to kv3_astk")
    out = []
    for fn, name, src, rep in (("qkd_astk_leaves.sv", "qkd_astk_zn", "zi", True),
                               ("qkd_astk_zn_head_p.sv", "qkd_astk_zn_head_p", "zl", False)):
        p = kd / "rtl" / fn
        before = hashlib.sha256(p.read_bytes()).hexdigest()
        try:
            t = zn_transform(p.read_text(), name, src)
        except ValueError as e:
            raise SystemExit(str(e))
        p.write_text(t + (REP_MOD if rep else ""))
        out.append(dict(file=fn, module=name, replica_src=src, sha256_before=before,
                        sha256_after=hashlib.sha256(p.read_bytes()).hexdigest()))
    delta = dict(transform="physical/die_plan/qwen_kvsys/cores/harden/astk_cons.py", files=out, command_cycles=0,
                 nominal_token_cycles=0, added_ff_per_node=NS * 18, nodes=4, added_ff=4 * NS * 18,
                 max_select_loads=17, form="CONS: sliced Z-node operand store, kept one-hot k / slot[0] / put replicas")
    (kd / "astk_cons_delta.json").write_text(json.dumps(delta, indent=1) + "\n")
    return delta
