`timescale 1ns/1ps
`default_nettype none
// Loader memory port -> four HBM stack services (hgi-takeover die integration, 2026-10-09; die-evidence-2 gap 1;
// hbm-phys [svc] 2026-10-10: native BURSTS + MULTI-OUTSTANDING reads, budget audit hbm_ds_cp_fetch / F5(3)).
//
// The loader's ND memory lanes (ot_hbm_accel_loader_host_addr ADDR_W 37: {stack 2, local byte 35}) reach the stream
// service of the stack that owns the address over the die's per-stack loader_mem chains (lq_<st> / lr_<st>):
//
//   lq_<st> = {native_len 4, outer_write_pending, native_rsp_rdy, native_tag 16, native_addr 30, native_pc 5, native_v,
//              wq_d 292 = {wr_packet 291, wr_v}}                                      (350 b, loader -> svc)
//   lr_<st> = {wq_source_fault, ack_gray 8 (wq_source_g[31:24], source 2), native_fault,
//              native_rsp_data 256, native_rsp_beat 4, native_rsp_tag 16, native_rsp_pc 5, native_rsp_v, native_rdy}
//                                                                                      (293 b, svc -> loader)
// Lane protocol: req_v / req_rdy (acceptance), req_len = 1..8 consecutive sectors for a read (0 = 1; writes are one
// sector); a read of length L answers with L responses (one sector each, address order, rsp_tag = the request's tag,
// rsp_last on the L-th).  A lane may hold up to NO reads outstanding, all on ONE stack (a request for another stack
// waits until the lane drained), answered in request order; a write is alone on its lane and on its stack.
// Per stack: READS -- a request FIFO (4) -> splitter at the 4-sector row boundaries (a row is one PC,
// ot_hbm_loader_kport_address) -> native transactions <= 4 sectors (bursts, ot_hbm_loader_service_boundary).  The lq / lr
// chains are forwarded multi-cycle wires, so the native channel is CREDITED (ot_hbm_svc_core_native NATIVE_CHAIN 1):
// native_v is one pulse a transaction against NQ credits of the svc request queue, lr native_rdy returns one credit
// pulse a pop, and the kport reserves RB sectors of response FIFO at issue so the svc streams responses without
// back-pressure (lq native_rsp_rdy is held 1).  Up to NO transactions issued-not-consumed, answered in issue order (the
// svc boundary's owner FIFO; every arriving beat is checked against the oldest unarrived transaction's tag + beat),
// steered to the lanes by the in-flight FIFO {lane, tag, len, last}.  WRITES -- the qualified one-transaction endpoint
// (ot_hbm_loader_native_endpoint, Gray write acknowledgement: latency tolerant) exactly as before; a stack runs reads
// or one write, never both.  Rate: min(NO x 4, RB) sectors per round trip a stack (RB 16, RTT 160: ~3.2 B/cycle)
// against one sector per round trip before.  BURST = 0: one-sector reads (len ignored).
module ot_hfd_loader_kport #(
    parameter integer ENABLE = 0,
    parameter integer ND = 2,
    parameter [35:0] STACK_BYTES = 36'd22500000000,
    parameter integer BURST = 1,
    parameter integer NO = 8,          // native read transactions issued and not consumed per stack (svc NATIVE_NO)
    parameter integer NQ = 4,          // svc request queue credits (= ot_hbm_svc_core_native NATIVE_NQ)
    parameter integer RB = 16,         // response FIFO a stack, sectors (reserved at issue; the rate is ~RB x 32 B / RTT)
    parameter integer MUT = 0          // bench mutants: 1 every response to lane 0; 2 stack bit 1 ignored;
                                       // 3 the splitter ignores the row boundary (a burst crosses PCs); 4 credits ignored
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
    input  wire [ND*4-1:0]    req_len,
    output wire [ND-1:0]      rsp_v,
    input  wire [ND-1:0]      rsp_rdy,
    output wire [ND-1:0]      rsp_we,
    output wire [ND*16-1:0]   rsp_tag,
    output wire [ND*256-1:0]  rsp_data,
    output wire [ND-1:0]      rsp_last,
    output wire [4*350-1:0]   lq,
    input  wire [4*293-1:0]   lr,
    output wire               fault
);
    localparam integer NA = (NO <= 1) ? 1 : $clog2(NO);
    localparam integer CW = $clog2(NO + 1);
    localparam integer RA = $clog2(RB);
    genvar s, d;
    // ---- per lane address translation and request length
    wire [1:0]  l_stack [0:ND-1];
    wire [1:0]  l_stack_m [0:ND-1];
    wire [4:0]  l_pc    [0:ND-1];
    wire [29:0] l_sec   [0:ND-1];
    wire        l_ok    [0:ND-1];
    wire [3:0]  l_len   [0:ND-1];
    reg  [ND-1:0] l_bad;                                   // sticky: an untranslatable request (fail closed)
    reg  [CW-1:0] l_cnt [0:ND-1];                          // reads outstanding on the lane
    reg  [1:0]  l_stk [0:ND-1];                            // ... all on this stack
    reg  [ND-1:0] l_wr;                                    // a write outstanding on the lane
    for (d = 0; d < ND; d = d + 1) begin : g_map
        ot_hbm_loader_kport_address #(.ENABLE(ENABLE)) u_map (.byte_address(req_addr[d*37 +: 37]),
            .stack_bytes(STACK_BYTES), .stack(l_stack_m[d]), .pc(l_pc[d]), .sector_address(l_sec[d]), .valid(l_ok[d]));
        assign l_stack[d] = (MUT == 2) ? (l_stack_m[d] & 2'b01) : l_stack_m[d];
        wire [3:0] ln_ = req_len[d*4 +: 4];
        assign l_len[d] = (req_we[d] || BURST == 0 || ln_ == 4'd0) ? 4'd1 : (ln_ > 4'd8 ? 4'd8 : ln_);
    end
    // ---- per stack
    wire [3:0]  e_req_rdy_raw, acc_s;
    wire [3:0]  e_req_rdy, e_rsp_v, e_rsp_we, e_busy, e_fault, r_fault, r_idle;
    wire [15:0] e_rsp_tag [0:3];
    wire [255:0] e_rsp_data [0:3];
    reg  [ND-1:0] owner [0:3];                             // lane holding the stack's WRITE (one-hot)
    reg  [1:0]  rr [0:3];
    wire [ND-1:0] grant [0:3];
    wire [3:0]  r_hv;                                      // read response head valid (n_rsp_v steered)
    wire [1:0]  r_hl [0:3];                                // ... to this lane
    wire [15:0] r_ht [0:3];
    wire [255:0] r_hd [0:3];
    wire [3:0]  r_hlast;
    wire [3:0]  r_take;                                    // the read head's response handshake
    wire [3:0]  r_acc;                                     // a lane read accepted into the stack's request FIFO
    for (s = 0; s < 4; s = s + 1) begin : g_st
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
        reg [52:0] rq [0:3]; reg [1:0] rqh, rqt; reg [2:0] rqn;   // {lane 2, tag 16, sector 30, len 4, spare}
        reg [24:0] fl [0:NO-1]; reg [NA-1:0] fh, ft; reg [CW-1:0] fn;  // issued, not consumed {lane 2, tag 16, len 4, last, spare 2}
        // ---------------- lane grant (rotating): a read into the request FIFO, or a write to the endpoint
        wire [ND-1:0] want;
        for (d = 0; d < ND; d = d + 1) begin : g_want
            wire rd_ok = !req_we[d] && rqn != 3'd4 && !e_busy[s] && !(|owner[s]) &&
                         (l_cnt[d] == 0 || (l_stk[d] == s && l_cnt[d] != CW'(NO)));
            wire wr_ok = req_we[d] && r_idle[s] && !(|owner[s]) && l_cnt[d] == 0 && e_req_rdy_raw[s];
            assign want[d] = ENABLE && req_v[d] && !l_wr[d] && l_ok[d] && l_stack[d] == s && (rd_ok || wr_ok);
        end
        reg [ND-1:0] gr_; reg [1:0] gs_;
        always @* begin : arb
            integer t, dd; reg found;
            gr_ = {ND{1'b0}}; gs_ = 2'd0; found = 1'b0;
            for (t = 0; t < ND; t = t + 1) begin
                dd = (rr[s] + t) % ND;
                if (!found && want[dd]) begin gr_[dd] = 1'b1; gs_ = 2'(dd); found = 1'b1; end
            end
        end
        assign grant[s] = gr_;
        wire [1:0] gsel_s = gs_;
        assign r_acc[s] = |gr_ && !req_we[gs_];
        wire        ev   = |gr_ && req_we[gs_];
        assign acc_s[s] = r_acc[s] || (ev && e_req_rdy[s]);
        wire [36:0] ea   = req_addr[gs_*37 +: 37];
        wire [255:0] ed  = req_wdata[gs_*256 +: 256];
        wire [31:0] es   = req_wstrb[gs_*32 +: 32];
        wire [15:0] et   = req_tag[gs_*16 +: 16];
        // ---------------- read engine (die-chain protocol: lq / lr are forwarded multi-cycle chains)
        //  issue: one native_v PULSE per native transaction against NQ credits (the svc request queue; native_rdy comes
        //  back as one credit pulse per pop), at most NO transactions not yet consumed, and only with RB sectors of
        //  response room reserved here -> the svc never needs back-pressure (native_rsp_rdy is held 1).
        //  arrival: every response beat must belong to the oldest unarrived transaction (tag, beat < len, not seen yet),
        //  else fault; it lands in its own slot of the stack's response buffer (RB sectors, allocated at issue: the PHY
        //  may return a burst's beats in any order) and is consumed by its lane in issue + address order.
        reg [29:0] cs; reg [3:0] rem; reg hact;                   // splitter state on the request FIFO head
        reg [3:0] bt, ba;                                          // beats consumed / arrived of the head / arrival txn
        reg [NA-1:0] fa; reg [CW-1:0] an;                          // arrival pointer, issued-not-fully-arrived count
        reg [$clog2(NQ+1)-1:0] cr;                                 // svc request queue credits
        reg [RA:0] rres;                                           // response sectors reserved (issued, not consumed)
        reg [255:0] rb [0:RB-1]; reg [RB-1:0] rbv; reg [RA-1:0] rbi, rbr; // response buffer, slot valid, alloc / read
        reg [RA-1:0] fb [0:NO-1];                                  // a transaction's first buffer slot
        reg [7:0] ga;                                              // beats arrived of the arrival transaction
        reg rsticky;
        wire [52:0] qh_ = rq[rqh];
        wire [29:0] sc = hact ? cs : qh_[34:5];
        wire [3:0] rm = hact ? rem : qh_[4:1];
        wire [3:0] room4 = 4'd4 - {2'b00, sc[1:0]};
        wire [3:0] chunk = (MUT == 3) ? rm : ((rm < room4) ? rm : room4);
        wire [4:0] cpc = sc[6:2] ^ sc[11:7] ^ sc[16:12];
        wire rd_go = ENABLE && rqn != 3'd0 && fn != CW'(NO) && (cr != 0 || MUT == 4) && (rres + (RA+1)'(chunk) <= (RA+1)'(RB)) &&
                     !rsticky && !n_fault;
        wire rlast = chunk == rm;
        wire [24:0] fh_ = fl[fh];
        wire [24:0] fa_ = fl[fa];
        wire arr = n_rsp_v;                                        // a response beat arrives (never refused)
        // the PHY controller may return a burst's beats in any order (FR-FCFS per sector): a beat lands in its own slot
        wire arr_ok = an != 0 && n_rsp_tag == fa_[22:7] && n_rsp_beat < fa_[6:3] && !ga[n_rsp_beat[2:0]];
        wire arr_end = arr && ba + 4'd1 == fa_[6:3];
        wire [RA:0] slot_ = {1'b0, fb[fa]} + {{(RA-2){1'b0}}, n_rsp_beat[2:0]};
        wire [RA-1:0] aslot = (slot_ >= (RA+1)'(RB)) ? RA'(slot_ - (RA+1)'(RB)) : RA'(slot_);
        assign r_hv[s] = rbv[rbr] && fn != 0 && !rsticky;
        assign r_hl[s] = fh_[24:23];
        assign r_ht[s] = fh_[22:7];
        assign r_hd[s] = rb[rbr];
        assign r_hlast[s] = fh_[2] && (bt + 4'd1 == fh_[6:3]);
        assign r_take[s] = r_hv[s] && rsp_rdy[r_hl[s]];
        wire c_end = r_take[s] && bt + 4'd1 == fh_[6:3];
        assign r_idle[s] = rqn == 3'd0 && fn == 0;
        assign r_fault[s] = rsticky;
        always @(posedge clk) begin
            if (r_acc[s]) rq[rqt] <= {2'(gsel_s), req_tag[gsel_s*16 +: 16], l_sec[gsel_s], l_len[gsel_s], 1'b0};
            if (rd_go) begin fl[ft] <= {qh_[52:51], qh_[50:35], chunk, rlast, 2'b00}; fb[ft] <= rbi; end
            if (arr) rb[aslot] <= n_rsp_data;
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin rqh <= 2'd0; rqt <= 2'd0; rqn <= 3'd0; fh <= {NA{1'b0}}; ft <= {NA{1'b0}}; fn <= {CW{1'b0}};
                              cs <= 30'd0; rem <= 4'd0; hact <= 1'b0; bt <= 4'd0; ba <= 4'd0; fa <= {NA{1'b0}};
                              an <= {CW{1'b0}}; cr <= NQ; rres <= '0; rbi <= '0; rbr <= '0; rbv <= '0; ga <= 8'd0; rsticky <= 1'b0; end
            else begin
                if (r_acc[s]) rqt <= rqt + 2'd1;
                if (rd_go) begin
                    ft <= (ft == NA'(NO - 1)) ? {NA{1'b0}} : ft + 1'b1;
                    if (rlast) begin rqh <= rqh + 2'd1; hact <= 1'b0; end
                    else begin hact <= 1'b1; cs <= sc + 30'(chunk); rem <= rm - chunk; end
                    rbi <= ({1'b0, rbi} + (RA+1)'(chunk) >= (RA+1)'(RB)) ? RA'({1'b0, rbi} + (RA+1)'(chunk) - (RA+1)'(RB))
                                                                        : RA'({1'b0, rbi} + (RA+1)'(chunk));
                end
                rqn <= rqn + (r_acc[s] ? 3'd1 : 3'd0) - ((rd_go && rlast) ? 3'd1 : 3'd0);
                cr <= cr - (rd_go ? 1'b1 : 1'b0) + (n_rdy ? 1'b1 : 1'b0);
                if (n_rdy && cr + (rd_go ? 0 : 1) > NQ) rsticky <= 1'b1;          // a credit nobody spent
                rres <= rres + (rd_go ? (RA+1)'(chunk) : '0) - (r_take[s] ? 1'b1 : 1'b0);
                // arrival
                if (arr) begin
                    if (!arr_ok) rsticky <= 1'b1;
                    if (arr_ok && arr_end) begin ba <= 4'd0; ga <= 8'd0; fa <= (fa == NA'(NO - 1)) ? {NA{1'b0}} : fa + 1'b1; end
                    else if (arr_ok) begin ba <= ba + 4'd1; ga[n_rsp_beat[2:0]] <= 1'b1; end
                end
                an <= an + (rd_go ? 1'b1 : 1'b0) - ((arr && arr_ok && arr_end) ? 1'b1 : 1'b0);
                // consumption
                if (arr && arr_ok) rbv[aslot] <= 1'b1;
                if (r_take[s]) rbv[rbr] <= 1'b0;
                if (r_take[s]) begin
                    rbr <= (rbr == RA'(RB - 1)) ? '0 : rbr + 1'b1;
                    if (c_end) begin bt <= 4'd0; fh <= (fh == NA'(NO - 1)) ? {NA{1'b0}} : fh + 1'b1; end
                    else bt <= bt + 4'd1;
                end
                fn <= fn + (rd_go ? 1'b1 : 1'b0) - (c_end ? 1'b1 : 1'b0);
            end
        wire wr_v; wire [290:0] wr_packet; wire e_rd_v, e_rd_rsp_rdy; wire [4:0] e_rd_pc; wire [29:0] e_rd_addr; wire [15:0] e_rd_tag;
        ot_hbm_loader_native_endpoint #(.ENABLE(ENABLE), .ADDR_W(37)) u_ep (
            .clk(clk), .rst_n(rst_n), .req_v(ev), .req_rdy(e_req_rdy[s]), .req_we(1'b1), .req_addr(ea),
            .req_wdata(ed), .req_wstrb(es), .req_tag(et),
            .translation_valid(ev && l_ok[gs_]), .translated_pc(l_pc[gs_]), .translated_addr(l_sec[gs_]),
            .rsp_v(e_rsp_v[s]), .rsp_rdy(|(owner[s] & rsp_rdy)), .rsp_we(e_rsp_we[s]), .rsp_tag(e_rsp_tag[s]),
            .rsp_data(e_rsp_data[s]),
            .wr_v(wr_v), .wr_rdy(1'b1), .wr_packet(wr_packet), .wr_ack(wr_ack),   // svc wq: one write in flight (endpoint waits for its ack)
            .rd_v(e_rd_v), .rd_rdy(1'b0), .rd_pc(e_rd_pc), .rd_addr(e_rd_addr), .rd_tag(e_rd_tag),
            .rd_rsp_v(1'b0), .rd_rsp_rdy(e_rd_rsp_rdy), .rd_rsp_pc(5'd0), .rd_rsp_tag(16'd0),
            .rd_rsp_beat(4'd0), .rd_rsp_data(256'd0),
            .service_fault(n_fault || src_fault), .busy(e_busy[s]), .fault(e_fault[s]));
        // the endpoint's own readiness (IDLE, no fault), without the write-only translation check of this cycle
        wire e_req_rdy_raw_ = !e_busy[s] && !e_fault[s];
        assign e_req_rdy_raw[s] = e_req_rdy_raw_;
        wire owp = e_busy[s] && |(owner[s]) && !e_rsp_v[s];
        assign lq[s*350 +: 350] = {(BURST != 0) ? chunk : 4'd1, owp, 1'b1, qh_[50:35], sc, cpc, rd_go, wr_packet, wr_v};
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin owner[s] <= {ND{1'b0}}; rr[s] <= 2'd0; end
            else begin
                if (acc_s[s]) rr[s] <= 2'((gs_ + 2'd1) % ND);
                if (ev && e_req_rdy[s]) owner[s] <= gr_;
                else if (e_rsp_v[s] && |(owner[s] & rsp_rdy)) owner[s] <= {ND{1'b0}};
            end
    end
    // ---- lanes: ready, response return, outstanding state
    for (d = 0; d < ND; d = d + 1) begin : g_lane
        wire [3:0] g_d = {grant[3][d], grant[2][d], grant[1][d], grant[0][d]};
        wire [3:0] o_w = {owner[3][d], owner[2][d], owner[1][d], owner[0][d]};
        wire [3:0] o_r;
        for (s = 0; s < 4; s = s + 1) begin : g_or
            assign o_r[s] = r_hv[s] && ((MUT == 1) ? (d == 0) : (r_hl[s] == 2'(d)));
        end
        assign req_rdy[d] = |(g_d & acc_s);
        assign rsp_v[d] = |(o_w & e_rsp_v) | |o_r;
        assign rsp_we[d] = |(o_w & e_rsp_we);
        assign rsp_last[d] = |(o_w & e_rsp_v) | |(o_r & r_hlast);
        assign rsp_tag[d*16 +: 16] = ({16{o_w[0]}} & e_rsp_tag[0]) | ({16{o_w[1]}} & e_rsp_tag[1]) |
                                     ({16{o_w[2]}} & e_rsp_tag[2]) | ({16{o_w[3]}} & e_rsp_tag[3]) |
                                     ({16{o_r[0]}} & r_ht[0]) | ({16{o_r[1]}} & r_ht[1]) |
                                     ({16{o_r[2]}} & r_ht[2]) | ({16{o_r[3]}} & r_ht[3]);
        assign rsp_data[d*256 +: 256] = ({256{o_w[0]}} & e_rsp_data[0]) | ({256{o_w[1]}} & e_rsp_data[1]) |
                                        ({256{o_w[2]}} & e_rsp_data[2]) | ({256{o_w[3]}} & e_rsp_data[3]) |
                                        ({256{o_r[0]}} & r_hd[0]) | ({256{o_r[1]}} & r_hd[1]) |
                                        ({256{o_r[2]}} & r_hd[2]) | ({256{o_r[3]}} & r_hd[3]);
        wire [CW-1:0] l_cnt_dbg = l_cnt[d];
        wire acc_r = req_v[d] && req_rdy[d] && !req_we[d];
        wire done_r = |(o_r & r_hlast) && rsp_rdy[d];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin l_cnt[d] <= {CW{1'b0}}; l_stk[d] <= 2'd0; l_wr[d] <= 1'b0; l_bad[d] <= 1'b0; end
            else begin
                l_cnt[d] <= l_cnt[d] + (acc_r ? 1'b1 : 1'b0) - (done_r ? 1'b1 : 1'b0);
                if (acc_r) l_stk[d] <= l_stack[d];
                if (req_v[d] && req_rdy[d] && req_we[d]) l_wr[d] <= 1'b1;
                else if (|(o_w & e_rsp_v) && rsp_rdy[d]) l_wr[d] <= 1'b0;
                if (ENABLE && req_v[d] && !l_ok[d]) l_bad[d] <= 1'b1;
            end
    end
    assign fault = |e_fault | |r_fault | |l_bad;
endmodule
`default_nettype wire
