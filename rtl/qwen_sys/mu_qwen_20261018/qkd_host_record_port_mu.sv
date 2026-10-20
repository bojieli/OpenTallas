`timescale 1ns/1ps
// =====================================================================================================================
// qkd_host_record_port_mu -- the KV/system die HOST record port for Qwen ROM 4 users (MU-KV-CTX 2026-10-19, coordinator
// 0kg: the fillers' initial context comes from the KV die host plane over the EXISTING KV->compute d2d record stream, no
// new die port).  Drop-in for qkd_host_record_port (rtl/qwen_sys/context_transport_20261014, UNCHANGED): same ports, plus
// parameters MU / MUT.  MU 0 instantiates the original (behaviour-identical by construction).
//
// Why the original cannot serve MU: its kind-12 context TX holds ONE request (the latest native request) and ONE token
// epoch (the latest allocator pulse).  Under MU the guard endpoint (qkd_host_native_token_endpoint_cancel_mu) issues the
// requests of all 4 users and the allocator (ot_qwen_tp8_token_epoch_allocator_mu) pulses one epoch {seq14, user2} per
// user step, so (a) the token run's context slot would carry whichever user asked last (the compute face runs the
// latency user 0 only: a filler tag there corrupts its token / position) and (b) a request whose epoch is not the latest
// pulse faults the source check.
//
// MU 1 (the d2d field spec: results/rtl/mu_qwen_1018/kvctx/README.md section 2, posted to lanes/MU-QW-DIE.md):
//   * per-user context: epoch_q[u] <- token_epoch when token_epoch[1:0] == u; held tag / gen [u] <- the request whose TAG
//     epoch[1:0] (= tag[44:43]) == u.  Every request check of the original is kept, against the user's own epoch.
//   * the token run's kind-12 CONTEXT slots come in a compiled PAIR on consecutive edges (d2d_link_calendar.py --mu: an
//     extra S->C kind 12 beat 1 one cycle before the existing kind 12 beat 0; the KV d2d services map both to send_kind 3):
//       1st edge = the MU context slot: the INITIAL CONTEXT record of one pending filler u (1..3), else a copy of the user-0
//                  record (a no-op for the compute loader: it loads users 1..3 only);
//       2nd edge = the existing slot: user 0's record (held tag [0]) -- the slot the compute face consumes, so the face
//                  ends every pair on the latency user's context exactly as today.
//     A pair edge out of order (a 1st edge not followed by a 2nd, or three in a row) is a sticky fault.
//   * initial context of filler u = the first request of u after reset, or a request whose position is not the user's
//     previous request position + 1 (a new request: the previous one ended).  It is kept in its own register (later
//     steps of u do not overwrite it), marked pending, and sent in the next MU slot; pending users are served in a fixed
//     rotation 1 -> 2 -> 3.  A second admission of u before its pending record was sent is a sticky fault (the compiler
//     admits at most one request per user per 3 token runs).
//   * the record is the canonical opaque548 kind 12 of qkd_host_native_context_tx: {5'd0, 4'd12, 6'd63, epoch16, 5'd0,
//     {370'd0, digest64, image epoch16, cap, gen2, TAG59}}, TAG59 = {epoch {seq14, user2}, 6'd0, token18, position13,
//     6'd0}: the compute face's own kind-12 check accepts it unchanged.
//   Static schedule: the slots are compiled; nothing waits or stalls; a missing source is a sticky fault (as the original).
// MUT (bench only): 1 = the MU record's user field is (u mod 3) + 1 (tag and header epoch, consistently); 2 = the pair
//   order swapped (the MU record on the 2nd edge, user 0's on the 1st); 3 = producer off (the MU slot always carries the
//   user-0 copy).
// =====================================================================================================================
module qkd_host_record_port_mu #(
    parameter integer MU = 0,
    parameter integer MUT = 0
) (
 input wire ck,rst_n,input wire[1:0]send_kind,
 input wire request_v,input wire[58:0]request_tag,input wire[1:0]request_gen,
 input wire[17:0]request_token,request_position,
 input wire token_epoch_valid,input wire[15:0]token_epoch,
 input wire begin_v,input wire[15:0]begin_epoch,input wire[10:0]expected_pw,input wire[3:0]expected_dw,
 input wire auth_v,input wire[15:0]auth_epoch,input wire[63:0]auth_digest,
 input wire program_ready,input wire[15:0]program_epoch,input wire[63:0]program_digest,
 input wire authorized_footer_valid,input wire[63:0]authorized_footer,
 input wire witness_slot,rx_v,input wire[547:0]rx_record,
 output wire commit_v,installed_valid,installed_fusedcap,
 output wire[15:0]commit_epoch,output wire[63:0]commit_digest,
 output reg tx_v,tx_observed_v,output reg[547:0]tx_record,output wire fault
);
generate if (MU == 0) begin : g_orig
    wire o_tv, o_to; wire [547:0] o_tr;
    qkd_host_record_port u_orig(.ck(ck),.rst_n(rst_n),.send_kind(send_kind),.request_v(request_v),.request_tag(request_tag),
        .request_gen(request_gen),.request_token(request_token),.request_position(request_position),
        .token_epoch_valid(token_epoch_valid),.token_epoch(token_epoch),.begin_v(begin_v),.begin_epoch(begin_epoch),
        .expected_pw(expected_pw),.expected_dw(expected_dw),.auth_v(auth_v),.auth_epoch(auth_epoch),.auth_digest(auth_digest),
        .program_ready(program_ready),.program_epoch(program_epoch),.program_digest(program_digest),
        .authorized_footer_valid(authorized_footer_valid),.authorized_footer(authorized_footer),.witness_slot(witness_slot),
        .rx_v(rx_v),.rx_record(rx_record),.commit_v(commit_v),.installed_valid(installed_valid),
        .installed_fusedcap(installed_fusedcap),.commit_epoch(commit_epoch),.commit_digest(commit_digest),
        .tx_v(o_tv),.tx_observed_v(o_to),.tx_record(o_tr),.fault(fault));
    always @(*) begin tx_v = o_tv; tx_observed_v = o_to; tx_record = o_tr; end
end else begin : g_mu
    // BEGIN / AUTH TX and the WITNESS RX: the original codecs, unchanged
    wire av,ao,af,cv,co,cf,wf; wire[547:0] ar,cr;
    qkd_program_auth_tx u_auth(.ck(ck),.rst_n(rst_n),.send_slot(send_kind==1||send_kind==2),.send_type(send_kind),
        .begin_v(begin_v),.begin_epoch(begin_epoch),.expected_pw(expected_pw),.expected_dw(expected_dw),
        .auth_v(auth_v),.auth_epoch(auth_epoch),.auth_digest(auth_digest),.tx_v(av),.tx_observed_v(ao),.tx_record(ar),.fault(af));
    qkd_host_native_context_tx_mu #(.MUT(MUT)) u_context(.ck(ck),.rst_n(rst_n),.send_slot(send_kind==3),
        .request_v(request_v),.request_tag(request_tag),.request_gen(request_gen),.request_token(request_token),
        .request_position(request_position),.token_epoch_valid(token_epoch_valid),.token_epoch(token_epoch),
        .program_ready(program_ready),.installed_fusedcap(installed_fusedcap),.program_epoch(program_epoch),
        .program_digest(program_digest),.tx_v(cv),.tx_observed_v(co),.tx_record(cr),.fault(cf));
    qkd_program_witness_rx u_witness(.ck(ck),.rst_n(rst_n),.program_begin_v(begin_v),.receive_slot(witness_slot),.rx_v(rx_v),
        .rx_record(rx_record),.expected_epoch(auth_epoch),.expected_digest(auth_digest),
        .authorized_footer_valid(authorized_footer_valid),.authorized_footer(authorized_footer),
        .program_commit_v(commit_v),.program_commit_epoch(commit_epoch),.program_commit_digest(commit_digest),
        .program_installed_valid(installed_valid),.installed_fusedcap(installed_fusedcap),.fault(wf));
    assign fault = af|cf|wf;
    // the shared pin register (as the original)
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin tx_v<=0; tx_observed_v<=0; tx_record<=0; end
        else begin tx_v<=av|cv; tx_observed_v<=ao|co; tx_record<=cv?cr:ar; end
end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// qkd_host_native_context_tx_mu: the 4-user kind-12 context TX (see the header above).  One register edge, as the original.
// ---------------------------------------------------------------------------------------------------------------------
module qkd_host_native_context_tx_mu #(parameter integer MUT = 0) (
 input wire ck,rst_n,send_slot,
 input wire request_v,input wire[58:0]request_tag,input wire[1:0]request_gen,
 input wire[17:0]request_token,request_position,
 input wire token_epoch_valid,input wire[15:0]token_epoch,
 input wire program_ready,installed_fusedcap,input wire[15:0]program_epoch,input wire[63:0]program_digest,
 output reg tx_v,tx_observed_v,output reg[547:0]tx_record,output reg fault
);
    reg  [3:0]  held, ev;                   // per user: a request held / an epoch seen
    reg  [15:0] ep  [0:3];
    reg  [58:0] tag [0:3];
    reg  [1:0]  gen [0:3];
    reg  [3:1]  seen, pend;                 // fillers: a request seen since reset / an initial context not yet sent
    reg  [12:0] lpos [1:3];
    reg  [58:0] itag [1:3];                 // fillers: the initial context (admission request)
    reg  [1:0]  igen [1:3];
    reg  [1:0]  rr;                         // rotation pointer 1..3
    reg         slot_q;                     // send_slot on the previous edge (pair phase)
    reg         pair2_q;                    // the previous edge was the 2nd of a pair
    wire [1:0]  ru = request_tag[44:43];    // the request's user (TAG epoch[1:0])
    wire [1:0]  eu = token_epoch[1:0];
    // pair phase: 1st edge of a pair = send_slot with no slot on the previous edge
    wire        first = send_slot && !slot_q;
    wire        second = send_slot && slot_q && !pair2_q;
    // pending filler chosen in rotation rr, rr+1, rr+2 (1-based, wraps 3 -> 1)
    function [1:0] nx(input [1:0] u); nx = (u == 2'd3) ? 2'd1 : u + 2'd1; endfunction
    wire [1:0]  c0 = rr, c1 = nx(rr), c2 = nx(nx(rr));
    wire        any_p = (MUT != 3) && (pend != 3'd0);
    wire [1:0]  pick = pend[c0] ? c0 : pend[c1] ? c1 : c2;
    // the record of a chosen source
    function [547:0] rec(input [58:0] t, input [1:0] g, input cap, input [15:0] pe, input [63:0] pd);
        rec = {5'd0, 4'd12, 6'd63, t[58:43], 5'd0, {370'd0, pd, pe, cap, g, t}};
    endfunction
    function [58:0] urot(input [58:0] t);   // MUT 1: user field (u mod 3) + 1
        urot = t; urot[44:43] = (t[44:43] == 2'd3) ? 2'd1 : t[44:43] + 2'd1;
    endfunction
    wire        mu_sel = (MUT == 2) ? second : first;      // the edge that carries the filler record
    wire        f_send = mu_sel && any_p;
    wire [58:0] f_tag = (MUT == 1) ? urot(itag[pick]) : itag[pick];
    wire        ok0 = held[0] && ev[0] && tag[0][58:43] == ep[0] && program_ready;
    wire        okf = program_ready && pend[pick];
    integer     i;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            held <= 0; ev <= 0; seen <= 0; pend <= 0; rr <= 2'd1; slot_q <= 0; pair2_q <= 0;
            tx_v <= 0; tx_observed_v <= 0; tx_record <= 0; fault <= 0;
            for (i = 0; i < 4; i = i + 1) begin ep[i] <= 0; tag[i] <= 0; gen[i] <= 0; end
            for (i = 1; i < 4; i = i + 1) begin lpos[i] <= 0; itag[i] <= 0; igen[i] <= 0; end
        end else begin
            slot_q <= send_slot; pair2_q <= second;
            tx_v <= send_slot;
            tx_observed_v <= send_slot && (f_send ? okf : ok0);
            if (token_epoch_valid) begin ev[eu] <= 1'b1; ep[eu] <= token_epoch; end
            if (request_v) begin
                // the original's request checks, against the request user's own epoch
                if (!ev[ru] || request_tag[58:43] != ep[ru] || request_tag[42:37] != 0 || request_tag[5:0] != 0 ||
                    request_token >= 151936 || request_position >= 8192 || request_tag[36:19] != request_token ||
                    request_tag[18:6] != request_position[12:0]) fault <= 1'b1;
                held[ru] <= 1'b1; tag[ru] <= request_tag; gen[ru] <= request_gen;
                if (ru != 2'd0) begin
                    if (!seen[ru] || request_position[12:0] != lpos[ru] + 13'd1) begin   // admission: a new request
                        if (pend[ru]) fault <= 1'b1;                                // previous initial context never sent
                        pend[ru] <= 1'b1; itag[ru] <= request_tag; igen[ru] <= request_gen;
                    end
                    seen[ru] <= 1'b1; lpos[ru] <= request_position[12:0];
                end
            end
            // pair order: a 1st edge must be followed by a 2nd; a slot after a 2nd is a new 1st (checked next edge)
            if (slot_q && !pair2_q && !send_slot) fault <= 1'b1;          // 1st edge without its 2nd
            if (send_slot && slot_q && pair2_q) fault <= 1'b1;            // three slots in a row
            if (send_slot) begin
                if (f_send) begin
                    tx_record <= rec(f_tag, igen[pick], installed_fusedcap, program_epoch, program_digest);
                    if (okf !== 1'b1) fault <= 1'b1;
                    pend[pick] <= 1'b0; rr <= nx(pick);
                end else begin
                    tx_record <= rec(tag[0], gen[0], installed_fusedcap, program_epoch, program_digest);
                    if (ok0 !== 1'b1) fault <= 1'b1;
                end
            end
            if (request_v && ru != 2'd0 && f_send && pick == ru) fault <= 1'b1;   // admission on its own send edge
        end
    end
endmodule
