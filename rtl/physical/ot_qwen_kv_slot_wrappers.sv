// Qwen ROM TP8 die (track B, KV merged): slot-shaped KV cells of contract v3
// (results/arch/hier_contract_1012/qwen_rom_tp8.json), hardened under the die master name so the die binds the view by
// name.  Each wrapper is wiring around a closed, benched body plus, where the die hop check asked for it, a pin stage.
//
//   qkd_kvwq_ctl_bin   KV landing write-queue control (4 instances: wctl_{W,E}{S,N}); body = ot_qkvd_kv_wq_ctl_binary
//                      #(FLANE_BINARY=1) (closed at 172.8 x 518.4 as qkd_kvwq_ctl_bin_a-9b01712f2, M8 era, other cell
//                      name and pin faces).  Slot 172.776 x 518.376, cap M5.
//
// Bundle packing (first field = MSB; tools/qwen_kv_die/kv_die.py BINDINGS order):
//   kvn[1047:0]   = {kvw_v, kvw_vg[1:0], kvw_t[13:0], kvw_layer[5:0], kvw_d[1023:0]} (in)  + kvw_cr (out, against the
//                   flow): one RTL port cannot carry both directions -> kvn_d[1046:0] + kvn_cr on the bundle's face.
//   f<g>[292:0]   = {f_v[g], f_d[g] 256, f_sec[g] 24, f_lane[g][2:0], f_tag[g] 9}   (out).  FLANE_BINARY=1: the lane is
//                   a 3-bit index, the body's upper five lane bits are constant 0 and are not ports (298 -> 293).
//   r<g>[1:0]     = {r_v[g], r_bad[g]}   (in)
//   durable[22:0] = {rw_v, rw_id[21:0]}  (out)
// Every port is register-at-the-pin in the body (input capture flops iv/id/rv_r, registered outputs).
// sl2 (el1013-qwen-small-masters, per-pair die hop check 10-13 13:32): f0..f3 and fault get ONE MORE register in this
// cell, a pure pin stage with no other load (the body's feed flops also load the head mux / tag logic and sat mid-cell:
// f0 / f1 left the pin 462-465 ps after the compensated clock).  +1 cycle on the feed beats and on the fault level; the
// feed is posted (f_v pulse, the report r<g> comes back whenever the leaf is done), so no handshake counts that cycle.
//
// OT_QKD_SLOT_MUT (bench mutant only, never synthesized): one f2 data bit inverted.
module qkd_kvwq_ctl_bin #(
    parameter integer HD   = 128,
    parameter integer QD   = 4,
    parameter integer TAGW = 9
) (
    input  wire                    ck,
    input  wire                    rst_n,
    input  wire [HD*8+23-1:0]      kvn_d,
    output wire                    kvn_cr,
    output wire [1+256+24+3+TAGW-1:0] f0,
    output wire [1+256+24+3+TAGW-1:0] f1,
    output wire [1+256+24+3+TAGW-1:0] f2,
    output wire [1+256+24+3+TAGW-1:0] f3,
    input  wire [1:0]              r0,
    input  wire [1:0]              r1,
    input  wire [1:0]              r2,
    input  wire [1:0]              r3,
    output wire [22:0]             durable,
    output wire                    fault
);
    localparam integer FW = 1 + 256 + 24 + 3 + TAGW;
    wire [3:0]        f_v;
    wire [4*256-1:0]  f_d;
    wire [4*24-1:0]   f_sec;
    wire [4*8-1:0]    f_lane;
    wire [4*TAGW-1:0] f_tag;
    wire              rw_v;
    wire [21:0]       rw_id;
    wire              fault_b;
    ot_qkvd_kv_wq_ctl_binary #(.HD(HD), .QD(QD), .TAGW(TAGW), .MUT(0), .HEAD_PIPE(0), .FLANE_BINARY(1)) u_body (
        .clk(ck), .rst_n(rst_n),
        .kvw_v(kvn_d[HD*8+22]), .kvw_vg(kvn_d[HD*8+21 -: 2]), .kvw_t(kvn_d[HD*8+19 -: 14]),
        .kvw_layer(kvn_d[HD*8+5 -: 6]), .kvw_d(kvn_d[HD*8-1:0]), .kvw_cr(kvn_cr),
        .f_v(f_v), .f_d(f_d), .f_sec(f_sec), .f_lane(f_lane), .f_tag(f_tag),
        .r_v({r3[1], r2[1], r1[1], r0[1]}), .r_bad({r3[0], r2[0], r1[0], r0[0]}),
        .rw_v(rw_v), .rw_id(rw_id), .fault(fault_b));
    wire [FW-1:0] fp [0:3];
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : g_pack
        assign fp[g] = {f_v[g], f_d[256*g +: 256], f_sec[24*g +: 24], f_lane[8*g +: 3], f_tag[TAGW*g +: TAGW]};
    end endgenerate
    wire [FW-1:0] fm [0:3];
    assign fm[0] = fp[0];
    assign fm[1] = fp[1];
`ifdef OT_QKD_SLOT_MUT
    assign fm[2] = fp[2] ^ ({{(FW-1){1'b0}}, 1'b1} << 100);
`else
    assign fm[2] = fp[2];
`endif
    assign fm[3] = fp[3];
    // pin stage: valid bits and the fault level reset, payload free-running
    (* keep *) reg [3:0]      fo_v;
    (* keep *) reg [FW-2:0]   fo_d [0:3];
    (* keep *) reg            fault_o;
    integer k;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin fo_v <= 4'd0; fault_o <= 1'b0; end
        else begin fo_v <= {fm[3][FW-1], fm[2][FW-1], fm[1][FW-1], fm[0][FW-1]}; fault_o <= fault_b; end
    always @(posedge ck) for (k = 0; k < 4; k = k + 1) fo_d[k] <= fm[k][FW-2:0];
    assign f0 = {fo_v[0], fo_d[0]};
    assign f1 = {fo_v[1], fo_d[1]};
    assign f2 = {fo_v[2], fo_d[2]};
    assign f3 = {fo_v[3], fo_d[3]};
    assign fault = fault_o;
    assign durable = {rw_v, rw_id};
endmodule
