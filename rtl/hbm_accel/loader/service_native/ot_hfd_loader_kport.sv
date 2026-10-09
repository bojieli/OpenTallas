`timescale 1ns/1ps
`default_nettype none
// Loader memory port -> four HBM stack services (hgi-takeover die integration, 2026-10-09; die-evidence-2 gap 1).
//
// The loader's ND memory lanes (ot_hbm_accel_loader_host_addr ADDR_W 37: {stack 2, local byte 35}) reach the stream
// service of the stack that owns the address over the die's per-stack loader_mem chains (lq_<st> / lr_<st>):
//
//   lane d -> ot_hbm_loader_kport_address (stack, controller PC, sector; capacity check) -> the stack's
//   ot_hbm_loader_native_endpoint (one transaction at a time, the qualified pairing of
//   tb_loader_service_core_native) -> lq_<st> = {outer_write_pending, native_rsp_rdy, native_tag 16,
//   native_addr 30, native_pc 5, native_v, wq_d 292 = {wr_packet 291, wr_v}}           (346 b, loader -> svc)
//   lr_<st> = {wq_source_fault, ack_gray 8 (wq_source_g[31:24], source 2), native_fault,
//   native_rsp_data 256, native_rsp_beat 4, native_rsp_tag 16, native_rsp_pc 5, native_rsp_v, native_rdy}
//                                                                                      (293 b, svc -> loader)
// Arbitration: per stack one transaction at a time (the endpoint's), lanes alternate; per lane one transaction
// outstanding, so a response returns to the one lane that owns it (exact, in order).  Writes and reads on a stack are
// serialised, so the per-source (2) write acknowledgement is unambiguous.  Cost: boot-time load / store bandwidth is
// one sector per stack per round trip (priced in tools/uarch_model.py hgi_loader_kport_model).
module ot_hfd_loader_kport #(
    parameter integer ENABLE = 0,
    parameter integer ND = 2,
    parameter [35:0] STACK_BYTES = 36'd22500000000,
    parameter integer MUT = 0          // bench mutants: 1 every response to lane 0; 2 stack bit 1 ignored
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire [ND-1:0]      req_v,
    output wire [ND-1:0]      req_rdy,
    input  wire [ND-1:0]      req_we,
    input  wire [ND*37-1:0]   req_addr,
    input  wire [ND*256-1:0]  req_wdata,
    input  wire [ND*32-1:0]   req_wstrb,
    input  wire [ND*16-1:0]   req_tag,
    output wire [ND-1:0]      rsp_v,
    input  wire [ND-1:0]      rsp_rdy,
    output wire [ND-1:0]      rsp_we,
    output wire [ND*16-1:0]   rsp_tag,
    output wire [ND*256-1:0]  rsp_data,
    output wire [4*346-1:0]   lq,
    input  wire [4*293-1:0]   lr,
    output wire               fault
);
    genvar s, d;
    // ---- per lane address translation
    wire [1:0]  l_stack [0:ND-1];
    wire [1:0]  l_stack_m [0:ND-1];
    wire [4:0]  l_pc    [0:ND-1];
    wire [29:0] l_sec   [0:ND-1];
    wire        l_ok    [0:ND-1];
    reg  [ND-1:0] l_busy;                                  // one transaction outstanding per lane
    reg  [ND-1:0] l_bad;                                   // sticky: an untranslatable request (fail closed)
    for (d = 0; d < ND; d = d + 1) begin : g_map
        ot_hbm_loader_kport_address #(.ENABLE(ENABLE)) u_map (.byte_address(req_addr[d*37 +: 37]),
            .stack_bytes(STACK_BYTES), .stack(l_stack_m[d]), .pc(l_pc[d]), .sector_address(l_sec[d]), .valid(l_ok[d]));
        assign l_stack[d] = (MUT == 2) ? (l_stack_m[d] & 2'b01) : l_stack_m[d];
    end
    // ---- per stack: lane grant, endpoint, die packing
    wire [3:0]  e_req_rdy, e_rsp_v, e_rsp_we, e_busy, e_fault;
    wire [15:0] e_rsp_tag [0:3];
    wire [255:0] e_rsp_data [0:3];
    reg  [ND-1:0] owner [0:3];                             // lane holding the stack's transaction (one-hot)
    reg  [3:0]  rr;                                        // per stack: lane 1 has priority next
    wire [ND-1:0] want [0:3];
    wire [ND-1:0] grant [0:3];
    for (s = 0; s < 4; s = s + 1) begin : g_st
        for (d = 0; d < ND; d = d + 1) begin : g_want
            assign want[s][d] = ENABLE && req_v[d] && !l_busy[d] && l_ok[d] && l_stack[d] == s && !(|owner[s]);
        end
        if (ND == 1) begin : g_g1
            assign grant[s] = want[s];
        end else begin : g_g2
            assign grant[s][0] = want[s][0] && !(rr[s] && want[s][1]);
            assign grant[s][1] = want[s][1] && !grant[s][0];
        end
        wire gsel = (ND > 1) && grant[s][ND > 1 ? 1 : 0];
        wire        ev   = |grant[s];
        wire        ewe  = req_we[gsel];
        wire [36:0] ea   = req_addr[gsel*37 +: 37];
        wire [255:0] ed  = req_wdata[gsel*256 +: 256];
        wire [31:0] es   = req_wstrb[gsel*32 +: 32];
        wire [15:0] et   = req_tag[gsel*16 +: 16];
        // svc side (lr) and the write acknowledgement (Gray token of write source 2)
        wire [292:0] r = lr[s*293 +: 293];
        wire n_rdy = r[0], n_rsp_v = r[1];
        wire [4:0] n_rsp_pc = r[6:2];
        wire [15:0] n_rsp_tag = r[22:7];
        wire [3:0] n_rsp_beat = r[26:23];
        wire [255:0] n_rsp_data = r[282:27];
        wire n_fault = r[283];
        wire [7:0] ack_g = r[291:284];
        wire src_fault = r[292];
        reg [7:0] ack_prev; wire [7:0] ack_now;
        assign ack_now[7] = ack_g[7];
        for (d = 6; d >= 0; d = d - 1) begin : g_ungray
            assign ack_now[d] = ack_now[d + 1] ^ ack_g[d];
        end
        always @(posedge clk or negedge rst_n) if (!rst_n) ack_prev <= 8'd0; else ack_prev <= ack_now;
        wire wr_ack = ack_now != ack_prev;
        wire wr_v, rd_v, rd_rsp_rdy; wire [290:0] wr_packet; wire [4:0] rd_pc; wire [29:0] rd_addr; wire [15:0] rd_tag;
        ot_hbm_loader_native_endpoint #(.ENABLE(ENABLE), .ADDR_W(37)) u_ep (
            .clk(clk), .rst_n(rst_n), .req_v(ev), .req_rdy(e_req_rdy[s]), .req_we(ewe), .req_addr(ea),
            .req_wdata(ed), .req_wstrb(es), .req_tag(et),
            .translation_valid(ev && l_ok[gsel]), .translated_pc(l_pc[gsel]), .translated_addr(l_sec[gsel]),
            .rsp_v(e_rsp_v[s]), .rsp_rdy(|(owner[s] & rsp_rdy)), .rsp_we(e_rsp_we[s]), .rsp_tag(e_rsp_tag[s]),
            .rsp_data(e_rsp_data[s]),
            .wr_v(wr_v), .wr_rdy(1'b1), .wr_packet(wr_packet), .wr_ack(wr_ack),   // svc wq: one write in flight (endpoint waits for its ack)
            .rd_v(rd_v), .rd_rdy(n_rdy), .rd_pc(rd_pc), .rd_addr(rd_addr), .rd_tag(rd_tag),
            .rd_rsp_v(n_rsp_v), .rd_rsp_rdy(rd_rsp_rdy), .rd_rsp_pc(n_rsp_pc), .rd_rsp_tag(n_rsp_tag),
            .rd_rsp_beat(n_rsp_beat), .rd_rsp_data(n_rsp_data),
            .service_fault(n_fault || src_fault), .busy(e_busy[s]), .fault(e_fault[s]));
        wire owp = e_busy[s] && |(owner[s] & req_we) && !e_rsp_v[s];
        assign lq[s*346 +: 346] = {owp, rd_rsp_rdy, rd_tag, rd_addr, rd_pc, rd_v, wr_packet, wr_v};
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin owner[s] <= {ND{1'b0}}; rr[s] <= 1'b0; end
            else begin
                if (ev && e_req_rdy[s]) begin owner[s] <= grant[s]; rr[s] <= ~gsel; end
                else if (e_rsp_v[s] && |(owner[s] & rsp_rdy)) owner[s] <= {ND{1'b0}};
            end
    end
    // ---- lanes: ready, response return, busy
    for (d = 0; d < ND; d = d + 1) begin : g_lane
        wire [3:0] g_d = {grant[3][d], grant[2][d], grant[1][d], grant[0][d]};
        wire [3:0] o_t = {owner[3][d], owner[2][d], owner[1][d], owner[0][d]};
        wire [3:0] o_any = {|owner[3], |owner[2], |owner[1], |owner[0]};
        wire [3:0] o_d = (MUT == 1) ? ((d == 0) ? o_any : 4'd0) : o_t;
        assign req_rdy[d] = |(g_d & e_req_rdy);
        assign rsp_v[d] = |(o_d & e_rsp_v);
        assign rsp_we[d] = |(o_d & e_rsp_we);
        assign rsp_tag[d*16 +: 16] = ({16{o_d[0]}} & e_rsp_tag[0]) | ({16{o_d[1]}} & e_rsp_tag[1]) |
                                     ({16{o_d[2]}} & e_rsp_tag[2]) | ({16{o_d[3]}} & e_rsp_tag[3]);
        assign rsp_data[d*256 +: 256] = ({256{o_d[0]}} & e_rsp_data[0]) | ({256{o_d[1]}} & e_rsp_data[1]) |
                                        ({256{o_d[2]}} & e_rsp_data[2]) | ({256{o_d[3]}} & e_rsp_data[3]);
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin l_busy[d] <= 1'b0; l_bad[d] <= 1'b0; end
            else begin
                if (req_v[d] && req_rdy[d]) l_busy[d] <= 1'b1;
                else if (rsp_v[d] && rsp_rdy[d]) l_busy[d] <= 1'b0;
                if (ENABLE && req_v[d] && !l_busy[d] && !l_ok[d]) l_bad[d] <= 1'b1;
            end
    end
    assign fault = |e_fault | |l_bad;
endmodule
`default_nettype wire
