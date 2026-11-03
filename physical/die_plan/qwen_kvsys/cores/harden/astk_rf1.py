"""DIE-KV-64/RF-E 11-03 RE-FORM RF-KV1 of kv3_astk (two strikes: vA TT -7.83 / DRV 40, vB TT -11.37 / DRV 80).

Failure cause (both strikes, [CHECKED] signoff/tt/sta.log of die-kv-61 vA + vB): the worst TT path is ctl
u_leaf.m5.zh[0] -> zh decode (NOR2 fanout 13) -> placement/fanout buffer chain (fanout 17 -> 64, 183 ps slew) ->
zf_m[zk_r] / zh read mux -> ap[36..39].  The 2-bit head counter zh and the 4-bit read address zk_r each drive a
whole-word mux (zh: 32 b x 4 heads; zk_r: 133 b x 16 entries = 256+ loads per bit), so the tool builds deep
buffer trees on a timing-critical select.

Form (0 command / token cycles, exact): the selects become REGISTERED ONE-HOT replicas, each bit driving <= 16
data loads, computed from the same next-state values the original registers capture:
  * zk: 9 kept qkd_astk_rf1_oh16 slices (z_hd[132:5] in 8 x 16 b + tail z_hd[4:0]); d = 1 << 4'(z_age_rn / Z_STRIDE)
    (= the D of the original zk_r copies, no reset like them); z_hd = OR_k (oh[k] & zf_m[k]).
  * zh: 8 kept qkd_astk_rf1_oh4r slices (z_s in 4-b groups) with the async reset of zh (rn_q, reset value 4'b0001 =
    onehot(0)); d = onehot(zh next) where zh next = start ? 0 : (!l_pend && z_emit) ? zh + 1 : zh (the always-block
    priority: l_pend > z_emit; start last; 2-bit wrap = the zh == 3 -> 0 branch).
Invariant oh_zk == onehot(zk_r), oh_zh == onehot(zh) on every edge and under reset, so z_hd / z_s are unchanged.
Added flops: 9*16 + 8*4 - 5*4 (removed zk_r copies) = +156 FF (PG XCHECK-1: 156 / 0.0345 mm2 = 4.5k bits/mm2 < 6k).
"""
import hashlib
import json
import re
from pathlib import Path

CTL = "qkd_astk_ctl_s_g0"

OLD_ZK = re.compile(r"    genvar zg;\n    generate for \(zg = 0; zg < 5; zg = zg \+ 1\) begin : g_zk\n.*?    end endgenerate\n",
                    re.S)
OLD_ZS = "        for (m_ = 0; m_ < 4; m_ = m_ + 1) if (zh == m_) z_s = z_hd[5 + 32*m_ +: 32];\n"

NEW_ZK = """    // RF-KV1 (DIE-KV-64/RF-E 11-03): registered one-hot read selects, <= 16 loads per select bit, 0 cycles
    // (astk_rf1.py): oh_zk == onehot(original zk_r), oh_zh == onehot(zh) on every edge.
    wire [15:0] rf1_zk_oh_nx = 16'd1 << 4'(z_age_rn / Z_STRIDE);
    wire [1:0]  rf1_zh_nx = start ? 2'd0 : (!l_pend && z_emit) ? zh + 2'd1 : zh;
    wire [3:0]  rf1_zh_oh_nx = 4'b0001 << rf1_zh_nx;
    wire [31:0] rf1_z_s;
    genvar zg;
    generate for (zg = 0; zg < 9; zg = zg + 1) begin : g_zk
        localparam integer LO = (zg < 8) ? 5 + 16*zg : 0;
        localparam integer W = (zg < 8) ? 16 : 5;
        wire [15:0] koh;
        (* keep_hierarchy *) qkd_astk_rf1_oh16 u_zk (.ck(ck), .d(rf1_zk_oh_nx), .q(koh));
        assign z_hd[LO +: W] = rf1_rd16(koh, zf_m[0][LO +: W], zf_m[1][LO +: W], zf_m[2][LO +: W], zf_m[3][LO +: W],
            zf_m[4][LO +: W], zf_m[5][LO +: W], zf_m[6][LO +: W], zf_m[7][LO +: W], zf_m[8][LO +: W], zf_m[9][LO +: W],
            zf_m[10][LO +: W], zf_m[11][LO +: W], zf_m[12][LO +: W], zf_m[13][LO +: W], zf_m[14][LO +: W],
            zf_m[15][LO +: W]);
    end endgenerate
    generate for (zg = 0; zg < 8; zg = zg + 1) begin : g_zs
        wire [3:0] hoh;
        (* keep_hierarchy *) qkd_astk_rf1_oh4r u_zh (.ck(ck), .rn(rn_q), .d(rf1_zh_oh_nx), .q(hoh));
        assign rf1_z_s[4*zg +: 4] = ({4{hoh[0]}} & z_hd[5 + 4*zg +: 4]) | ({4{hoh[1]}} & z_hd[37 + 4*zg +: 4])
                                  | ({4{hoh[2]}} & z_hd[69 + 4*zg +: 4]) | ({4{hoh[3]}} & z_hd[101 + 4*zg +: 4]);
    end endgenerate
"""
FUNC = """    function automatic [15:0] rf1_rd16(input [15:0] oh, input [15:0] m0, input [15:0] m1, input [15:0] m2,
        input [15:0] m3, input [15:0] m4, input [15:0] m5, input [15:0] m6, input [15:0] m7, input [15:0] m8,
        input [15:0] m9, input [15:0] m10, input [15:0] m11, input [15:0] m12, input [15:0] m13, input [15:0] m14,
        input [15:0] m15);
        rf1_rd16 = ({16{oh[0]}} & m0) | ({16{oh[1]}} & m1) | ({16{oh[2]}} & m2) | ({16{oh[3]}} & m3)
                 | ({16{oh[4]}} & m4) | ({16{oh[5]}} & m5) | ({16{oh[6]}} & m6) | ({16{oh[7]}} & m7)
                 | ({16{oh[8]}} & m8) | ({16{oh[9]}} & m9) | ({16{oh[10]}} & m10) | ({16{oh[11]}} & m11)
                 | ({16{oh[12]}} & m12) | ({16{oh[13]}} & m13) | ({16{oh[14]}} & m14) | ({16{oh[15]}} & m15);
    endfunction
"""
MODS = """
(* keep_hierarchy *) module qkd_astk_rf1_oh16 (input wire ck, input wire [15:0] d, output reg [15:0] q);
    always @(posedge ck) q <= d;
endmodule

(* keep_hierarchy *) module qkd_astk_rf1_oh4r (input wire ck, input wire rn, input wire [3:0] d, output reg [3:0] q);
    always @(posedge ck or negedge rn) if (!rn) q <= 4'b0001; else q <= d;
endmodule
"""


def ctl_transform(text):
    """-> rewritten qkd_astk_ctl_s_g0 source; fail-closed on any unexpected shape"""
    if len(re.findall(rf"^module {CTL}\b", text, re.M)) != 1:
        raise ValueError(f"astk_rf1: expected one module {CTL}")
    if "rf1_" in text:
        raise ValueError("astk_rf1: already applied")
    if len(OLD_ZK.findall(text)) != 1 or text.count(OLD_ZS) != 1:
        raise ValueError("astk_rf1: ctl g_zk block / z_s head mux not in the expected form")
    decl = [re.search(rf"^\s*wire\s+(?:\[[^\]]*\]\s*)?{w}\s*=", text, re.M) for w in ("z_emit", "l_pend", "z_age_rn", "start")]
    if not all(decl) or "STATIC_SCHEDULE ? z_slot_r : z_ne" not in text:
        raise ValueError("astk_rf1: z_emit / l_pend / z_age_rn / start definitions not found")
    # they must be declared before the new block uses them
    if max(m.start() for m in decl) > OLD_ZK.search(text).start():
        raise ValueError("astk_rf1: z_emit / l_pend / z_age_rn / start declared after g_zk")
    text = OLD_ZK.sub(lambda m: NEW_ZK, text, count=1)
    text = text.replace(OLD_ZS, "        z_s = rf1_z_s;\n", 1)
    # the function before the first use (module scope, after the port list)
    anchor = "    localparam integer HEADS = 1, STATIC_SCHEDULE = 1;"
    if text.count(anchor) != 1:
        raise ValueError("astk_rf1: HEADS localparam anchor missing")
    text = text.replace(anchor, FUNC + anchor, 1)
    return text + MODS


def apply_kit(kd, mod):
    kd = Path(kd)
    if mod != "kv3_astk":
        raise SystemExit("--astk-rf1 only applies to kv3_astk")
    srcs = [p for p in sorted((kd / "rtl").glob("*.sv")) if re.search(rf"^module {CTL}\b", p.read_text(), re.M)]
    if len(srcs) != 1:
        raise SystemExit(f"--astk-rf1: expected one {CTL} source in the kit rtl, found {len(srcs)}")
    p = srcs[0]
    before = hashlib.sha256(p.read_bytes()).hexdigest()
    try:
        p.write_text(ctl_transform(p.read_text()))
    except ValueError as e:
        raise SystemExit(str(e))
    delta = dict(transform="physical/die_plan/qwen_kvsys/cores/harden/astk_rf1.py", file=p.name,
                 sha256_before=before, sha256_after=hashlib.sha256(p.read_bytes()).hexdigest(),
                 command_cycles=0, nominal_token_cycles=0, added_ff=9 * 16 + 8 * 4 - 5 * 4,
                 max_select_loads=16, form="registered one-hot zk / zh read selects (RF-KV1)")
    (kd / "astk_rf1_delta.json").write_text(json.dumps(delta, indent=1) + "\n")
    return delta
