#!/usr/bin/env python3
"""STW-S81c-TOK4-BAND 10-22: derive the R band (dsdv_idx_rg3_br) of the banded idx rg3 from dsdv_idx_rg3.sv by
exact, counted text edits (every edit must match once): the reader control keeps its source; the response datapath
(RH relays, rrr data, landing writes, landing SRAMs, key mux) moves to X, the engine (4 chunk columns + tail) to the S
bands, the OH output relays to S23 (one stage) and the qo / so / st pins leave through S23.
  mk_rg3_br.py <dsdv_idx_rg3.sv> <out.sv>"""
import sys, re
src = open(sys.argv[1]).read()
out = src

def sub(old, new, count=1):
    global out
    n = out.count(old)
    if n != count:
        sys.exit(f"mk_rg3_br: expected {count} x {old[:70]!r}, found {n}")
    out = out.replace(old, new)

def cut(start, end, new):
    """replace the text from the (unique) start marker through the (first following) end marker"""
    global out
    i = out.find(start)
    if i < 0 or out.find(start, i + 1) >= 0:
        sys.exit(f"mk_rg3_br: start marker not unique: {start[:70]!r}")
    j = out.find(end, i)
    if j < 0:
        sys.exit(f"mk_rg3_br: end marker missing: {end[:70]!r}")
    out = out[:i] + new + out[j + len(end):]

# ---- module header: R band ports
cut("module dsdv_idx_rg3 #(", "    output reg  [9:0]    st\n);", """module dsdv_idx_rg3_br #(
    parameter integer MUT = 0,
    parameter bit SRAM_MACRO = 0,
    parameter integer DQR = 24,
    parameter integer IQD = 512,
    parameter integer SQD = 256,
    parameter integer LFD = 256,
    parameter integer EL = 124,
    parameter integer IH = 0,
    parameter integer KR = 1,
    // banded: LX = edges the landed parent adds on the engine loop (R -> X, X -> S, S01 -> S23, S23 -> R); the metadata
    // ring reads EL + KR + LX - 1 behind (0 = the flat banded parent, cycle-exact to dsdv_idx_rg3)
    parameter integer LX = 0
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [3:0]    sid,
    input  wire [512:0]  qi,
    input  wire [275:0]  si,
    output reg  [183:0]  rqo,
    output wire [512:0]  qoi_o,         // q chain (S23 relays it to qo; S01 / S23 take the query codes from it)
    output wire [275:0]  soi_o,         // s chain (S23 relays it to so)
    output reg  [9:0]    st_o,          // status (S23 relays it to st)
    output wire [56:0]   ql_o,          // {ql_v, ql_h, ql_sw}: query load to the chunk columns
    output wire [17:0]   sx_o,          // S stage to X: {gatk[1], s_vx[3:0], s_it[34:25], s_it[2:0]}
    input  wire [67:0]   xr_i,          // from X: {rkc[3:0], rrr[3][15:0], .., rrr[0][15:0]}
    input  wire [16:0]   sc_i           // from S23: {o_fault, o_score}
);""")
sub("    initial if (IQD > 1024 || SQD > 1024 || LFD > 1024 || DQR > 31 || DQR < 1) $fatal(1, \"dsdv_idx_rg3: queue / budget sizes\");",
    "    initial if (IQD > 1024 || SQD > 1024 || LFD > 1024 || DQR > 31 || DQR < 1 || KR < 1 || EL + KR + LX + 2 > 255)\n"
    "        $fatal(1, \"dsdv_idx_rg3_br: queue / budget sizes / KR >= 1 (X holds kr[0])\");")
# ---- response lanes: rrr control fields + rkc arrive from X
sub("    reg [3:0][271:0] rrr;                           // response lanes at the pin\n",
    "    wire [3:0][15:0] rrr;                           // X band rrr[u][15:0] = {tag10, beat 4, pop, v}\n"
    "    assign rrr = xr_i[63:0];\n")
cut("    // S81-COLLECT2/L20KIT: RH response relay hops", "rrr[3][271:2] <= rrh[1087:818];\n    end\n", "")
# that block also held the q / s data capture (qr / sr [n:1]): keep it (10-22 lpc0 / probe: qo data 0, the regression)
sub("        else begin qr[0] <= qih[0]; sr[0] <= sih[0]; end\n",
    "        else begin qr[0] <= qih[0]; sr[0] <= sih[0]; end\n    always @(posedge ck) begin qr[512:1] <= qih[512:1]; sr[275:1] <= sih[275:1]; end\n")
cut("    (* keep = \"true\" *) reg [3:0]  rkc;\n", "    always @(posedge ck) begin\n        rkc <= {rrh[817], rrh[545], rrh[273], rrh[1]};\n        qvk <= {3{qih[0]}};\n    end\n",
    "    wire [3:0] rkc = xr_i[67:64];                  // X band pin copies of the pops\n"
    "    (* keep = \"true\" *) reg [2:0]  qvk;             // [2]: leftk replica (S81-IDXRD-1021)\n"
    "    always @(posedge ck) qvk <= {3{qih[0]}};\n")
cut("    generate if (OH == 0) begin : g_khz", "    end endgenerate\n    wire [3:0] rk_in",
    "    assign qoi_o = qoi; assign soi_o = soi;     // the OH relay is S23's one chain stage\n    wire [3:0] rk_in")
sub("    wire [3:0][255:0] rdd;\n", "")
sub("        assign rdd[gu] = rrr[gu][271:16];\n", "")
# ---- query load: ql_c (unused since the per-column copies) is gone; the bundle leaves to the S bands
sub("    reg  [511:0] ql_c;\n", "")
sub("    always @(posedge ck) begin ql_c <= qoi[512:1]; ql_sw <= q_d[47:0]; ql_h <= 8'(pw[6:1]); end\n",
    "    always @(posedge ck) begin ql_sw <= q_d[47:0]; ql_h <= 8'(pw[6:1]); end\n    assign ql_o = {ql_v, ql_h, ql_sw};\n")
# ---- landing writes: R keeps the valid / slot copy (slot counts, faults); data / address / halves are X's
sub("    reg  [3:0]  lw_v, lw_h1;\n    reg  [3:0][9:0] lw_a;\n    reg  [3:0][255:0] lw_d;\n", "    reg  [3:0]  lw_v;\n")
cut("    always @(posedge ck) for (u = 0; u < 4; u = u + 1) begin : g_rsp\n", "        else lw_a[u] <= {2'b10, s_, cl};\n    end\n",
    "    always @(posedge ck) for (u = 0; u < 4; u = u + 1) lw_sl[u] <= {rt[u][5], rt[u][13:11]};\n")
# ---- landing memories / key mux -> X (R keeps the S / C / K item stages and sends the S stage)
cut("    (* keep = \"true\" *) reg [1:0] su_a, su_b;      // S-stage PC copies", "    end endgenerate\n\n    // ================================================================== item queue",
    "    (* keep = \"true\" *) reg [3:0] s_vx;   // s_v copies, one per landing unit (X: <= 32 loads a copy)\n"
    "    assign sx_o = {gatk[1], s_vx, s_it[34:25], s_it[2:0]};\n\n    // ================================================================== item queue")
sub("s_v <= 1'b0; c_v <= 1'b0;", "s_v <= 1'b0; s_vx <= 4'd0; c_v <= 1'b0;")
sub("s_v <= ipop_b; c_v <= s_v;", "s_v <= ipop_b; s_vx <= {4{ipop_b}}; c_v <= s_v;")
sub("s_it <= ih; su_a <= ih[34:33]; su_b <= ih[34:33]; c_it <= s_it;", "s_it <= ih; c_it <= s_it;")
cut("    // scale extraction select (C stage", "    assign k_key[543:512] = k_sc;\n", "")
# ---- engine -> S bands; the score returns from S23
cut("    // ================================================================== engine: 4 chunk columns", "o_score(o_s), .o_fault(o_f));\n",
    "    // ================================================================== engine: S01 / S23 bands (score returns from S23)\n"
    "    wire [15:0] o_s = sc_i[15:0];\n    wire        o_f = sc_i[16];\n")
sub(".ra(mw - 10'(EL + KR - 1))", ".ra(mw - 10'(EL + KR + LX - 1))")
sub("if (warm_n == 8'(EL + KR + 2)) warm <= 1'b1;", "if (warm_n == 8'(EL + KR + LX + 2)) warm <= 1'b1;")
# ---- status leaves to S23
sub("if (!rl[39]) begin fc <= 8'd0; st <= 10'd0; end else begin fc <= fc | fc_set | fw; st <= {fc, act, fault}; end",
    "if (!rl[39]) begin fc <= 8'd0; st_o <= 10'd0; end else begin fc <= fc | fc_set | fw; st_o <= {fc, act, fault}; end")
if "qr[512:1] <= qih[512:1]" not in out or "sr[275:1] <= sih[275:1]" not in out:
    sys.exit("mk_rg3_br: q / s data capture missing")
for bad in ("rdd", "lw_d", "lw_a", "lw_h1", "k_key", "h0q", "g_ch", "u_t ", "OH", "rrh", "g_khop"):
    body = out[out.find("module dsdv_idx_rg3_br"):]
    body = re.sub(r"//[^\n]*", "", body)
    if re.search(r"\b" + re.escape(bad.strip()) + (r"\b" if bad[-1].isalnum() else ""), body):
        sys.exit(f"mk_rg3_br: {bad} still referenced")
hdr = ("// GENERATED by results/arch/s81_band_1022/mk_rg3_br.py from rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg3.sv -- do not edit.\n"
       "// STW-S81c-TOK4-BAND 10-22: R band (reader control) of the banded idx rg3 (dsdv_idx_rg3_band.sv holds X, S01, S23 and\n"
       "// the wires-only parent).  Every edit is a counted text substitution of the source module.\n")
open(sys.argv[2], "w").write(hdr + out[out.find("module dsdv_idx_rg3_br"):])
