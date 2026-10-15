`timescale 1ns/1ps
`default_nettype none
// ot_hbm_idx_vm_adapter (Claude hbm-group-B3, 2026-10-14): native IDX <-> B2 VM slice read adapter.
//
// The native IDX parent issues per-lane reads {v, sec16} (lane b <-> bank b, sec16 = {m, S[14:0]}, S = global word >> 3)
// and expects the B2 wide read lane contract: one credit back when a request leaves the lane queue, rr {v, data 256} in
// request order with no back-pressure.  A B2 wide read lane only serves its OWN slice (ot_vms_bank: main op with
// S[14:13] != sid, or a bank != lane, latches FAULT), so the 15-bit global -> SID routing happens here:
//   local   m = 1 (mirror window: replicated in every slice) or S[14:13] == sid  -> VM wide read lane S[2:0]
//   remote  m = 0 and S[14:13] != sid                                          -> the slice hub's packet client
//           (old VM packet ABI: <= PK outstanding, responses in request order, any slice via the CW / CCW ring)
// Ordering per lane without a data reorder buffer: a lane never has local and remote reads outstanding at the same time
// (a request of the other kind waits until the lane's outstanding count is zero), so local responses (in order on the
// wide lane) and remote responses (in order on the packet client; tag = lane) can never overtake each other on a lane.
// Cost: one round trip of bubble at each local <-> remote switch of a lane; zero for the all-local (mirror / own slice)
// placement the IDX allocator is asked for.
// Held lease (ot_hbm_b2_peer_lease, source side): the wide lane group's LQ credits per lane belong to the lease owner.
// Local reads issue only while l_grant; l_req is held while any local read is queued or outstanding; l_drained = no
// local read queued or outstanding AND every VM lane credit returned (credits == LQ).  The packet client needs no lease.
// Every input is pin-flopped and every output is a flop.
module ot_hbm_idx_vm_adapter #(
    parameter integer LQ  = 10,    // VM wide lane credits held under the lease (4 + 2 x relay stages, B2 D-B2-12)
    parameter integer AQ  = 10,    // adapter lane queue = credits handed to IDX per lane
    parameter integer PK  = 4,     // packet client outstanding limit (ot_vms_hub: at most 4)
    parameter integer MUT = 0      // 1: SID compare on S[13:12] (mis-route); 2: no kind blocking (reorder);
                                   // 3: lease request / drained ignore outstanding reads (early release)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [1:0]        sid,
    // IDX side (looks like a B2 wide read lane group of 8 lanes)
    input  wire [8*17-1:0]   i_rq,
    output reg  [7:0]        i_rq_cr,
    output reg  [8*257-1:0]  i_rr,
    // VM wide read lanes
    output reg  [8*17-1:0]   v_rq,
    input  wire [7:0]        v_rq_cr,
    input  wire [8*257-1:0]  v_rr,
    // VM hub packet client: req {v, we, addr 32, wdata 256, bmask 32, tag 16}; rsp {v, tag 16, we, rdata 256}
    output reg  [337:0]      v_cq,
    input  wire [273:0]      v_cr,
    // lease (source side of ot_hbm_b2_peer_lease)
    output reg               l_req,
    input  wire              l_grant,
    output reg               l_drained,
    input  wire              l_drain_ack,
    output reg               fault
);
    localparam integer QW = $clog2(AQ + 1), CW = $clog2(LQ + 1), OW = $clog2(LQ + AQ + 1), PW = $clog2(PK + 1);
    // ---- pin flops
    reg [8*17-1:0] rq_f; reg [7:0] vcr_f; reg [8*257-1:0] vrr_f; reg [273:0] vcr_pf; reg grant_f, dack_f; reg [1:0] sid_f;
    always @(posedge clk) begin rq_f <= i_rq; vcr_f <= v_rq_cr; vrr_f <= v_rr; vcr_pf <= v_cr; sid_f <= sid; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin grant_f <= 1'b0; dack_f <= 1'b0; end
        else begin grant_f <= l_grant; dack_f <= l_drain_ack; end
    // ---- per lane state
    reg [15:0] q [0:7][0:AQ-1];
    reg [QW-1:0] qn [0:7]; reg [$clog2(AQ)-1:0] qr [0:7], qw [0:7];
    reg [CW-1:0] vcr [0:7];                 // VM credits held
    reg [OW-1:0] lo_n [0:7];                // local reads outstanding (issued, response not yet seen)
    reg [PW-1:0] rm_n [0:7];                // remote reads outstanding on the lane
    reg [PW-1:0] pk_n;                      // packet client outstanding
    reg [2:0] rr_ptr;                       // packet round robin
    wire [15:0] hd [0:7]; wire [7:0] hv, hrem, can_l, can_r;
    genvar b;
    for (b = 0; b < 8; b = b + 1) begin : g_l
        assign hd[b] = q[b][qr[b]];
        assign hv[b] = qn[b] != 0;
        wire [1:0] ssl = (MUT == 1) ? hd[b][13:12] : hd[b][14:13];
        assign hrem[b] = !hd[b][15] && ssl != sid_f;
        assign can_l[b] = hv[b] && !hrem[b] && (rm_n[b] == 0 || MUT == 2) && vcr[b] != 0 && grant_f;
        assign can_r[b] = hv[b] &&  hrem[b] && (lo_n[b] == 0 || MUT == 2);
    end
    // one packet a cycle: round robin over lanes with a remote head
    reg [3:0] pick;
    always @* begin
        pick = 4'd0;
        for (integer k = 7; k >= 0; k = k - 1)
            if (can_r[3'(rr_ptr + 3'(k))] && pk_n < PW'(PK)) pick = {1'b1, 3'(rr_ptr + 3'(k))};
    end
    wire [7:0] pr_lane = 8'(1) << v_tag_lane;
    wire       pr_v = vcr_pf[273];
    wire [2:0] v_tag_lane = vcr_pf[272:270];  // tag 16 = {lane 3, 13'b0} (the top of the response's tag field)
    integer k2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (integer l = 0; l < 8; l = l + 1) begin
                qn[l] <= 0; qr[l] <= 0; qw[l] <= 0; vcr[l] <= CW'(LQ); lo_n[l] <= 0; rm_n[l] <= 0;
            end
            pk_n <= 0; rr_ptr <= 3'd0; i_rq_cr <= 8'd0; v_cq[337] <= 1'b0; fault <= 1'b0;
            l_req <= 1'b0; l_drained <= 1'b1;
            for (integer l = 0; l < 8; l = l + 1) begin i_rr[l*257 + 256] <= 1'b0; v_rq[l*17 + 16] <= 1'b0; end
        end else begin
            begin : lanes
                reg [7:0] take_l, take_r; reg any_l, any_out;
                take_l = can_l;
                take_r = pick[3] ? (8'(1) << pick[2:0]) : 8'd0;
                any_l = 1'b0; any_out = 1'b0;
                for (integer l = 0; l < 8; l = l + 1) begin
                    reg push, pop, rr_l, cr_l, rr_r;
                    push = rq_f[l*17 + 16]; pop = take_l[l] || take_r[l];
                    rr_l = vrr_f[l*257 + 256]; cr_l = vcr_f[l]; rr_r = pr_v && pr_lane[l];
                    if (push) begin q[l][qw[l]] <= rq_f[l*17 +: 16]; qw[l] <= (qw[l] == AQ-1) ? 0 : qw[l] + 1'b1; end
                    if (pop) qr[l] <= (qr[l] == AQ-1) ? 0 : qr[l] + 1'b1;
                    qn[l] <= qn[l] + QW'(push) - QW'(pop);
                    if (push && qn[l] == QW'(AQ) && !pop) fault <= 1'b1;                        // IDX overran its credits
                    if (push && rq_f[l*17 +: 3] != 3'(l)) fault <= 1'b1;                       // lane != bank: mis-routed
                    i_rq_cr[l] <= pop;
                    // local issue
                    v_rq[l*17 +: 17] <= {take_l[l], hd[l]};
                    vcr[l] <= vcr[l] - CW'(take_l[l]) + CW'(cr_l);
                    lo_n[l] <= lo_n[l] + OW'(take_l[l]) - OW'(rr_l);
                    rm_n[l] <= rm_n[l] + PW'(take_r[l]) - PW'(rr_r);
                    if (rr_l && rr_r) fault <= 1'b1;                                          // both kinds answered at once
                    // response to IDX: local wide lane or packet, in lane order
                    i_rr[l*257 +: 257] <= rr_r ? {1'b1, vcr_pf[255:0]} : {rr_l, vrr_f[l*257 +: 256]};
                    if ((qn[l] != 0 && !hrem[l]) || (lo_n[l] != 0 && MUT != 3)) any_l = 1'b1;
                    if (lo_n[l] != 0 || vcr[l] != CW'(LQ)) any_out = 1'b1;
                end
                pk_n <= pk_n + PW'(pick[3]) - PW'(pr_v);
                if (pick[3]) rr_ptr <= pick[2:0] + 3'd1;
                v_cq <= {pick[3], 1'b0, {11'd0, hd[pick[2:0]], 5'd0}, 256'd0, 32'd0, {pick[2:0], 13'd0}};
                l_req <= any_l;
                l_drained <= !any_l && (!any_out || MUT == 3);
            end
        end
    end
endmodule
`default_nettype wire
