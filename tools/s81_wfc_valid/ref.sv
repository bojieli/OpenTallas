// Frozen8ea40420a WFC with original serial operation-valid OR.
`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------
// dsfd_vm_static_wfc_valid_ref (claude S81 VM owner r9, 2026-10-14): the STATIC VM end of the WFC stage kit's VM channels
// (die master dsfd_wfc_stg = dsfd_wfc_stg_cl: t_swv/t_swd, t_srv/t_srd out, f_swr, f_srr, f_swa, f_srq in).
// Successor of dsfd_vm_wfc_ep (RTT grant receivers lrx_rtt + one in-order op pipe): the static VM takes EVERY kit
// request the serial cycle it arrives (one write and one read pair a serial cycle, never stalled), so the grants are
// constant-high levels from flops and no receiver queue exists (owner rule 2026-10-14T18:59).
// Die ports (serial domain, directions the VM's; S-BIND packing):
//   f_wfc 560 = {f_srd 31 {v1, row1 15, row0 15}, f_srv, f_swd 527 {addr 15, data 512}, f_swv}   (lsb f_swv)
//   t_wfc 1029 = {t_err, t_srq 1026 {rv1, rq1 512, rv, rq 512}, t_srg, t_swg}                    (lsb t_swg)
// Function (stream domain after the fixed 3:4 transfer ot_s81_vm_x34 W 560):
//   write  addr 0 .. 16383 -> VM write source 52 {row addr[13:0], mask ffff, data}; addr 15'h7fff = the kit's START
//          doorbell (POSTED kit: its own t_ks carries START to the capture; the doorbell is not a VM op and is
//          ordered after every earlier write of the channel by construction: one request a serial cycle, in order,
//          each written at a fixed edge); any other addr >= 16384 -> t_err (sticky), nothing written.
//   read   row0 (and row1 when v1) -> aux read ports 8 + row[1:0] (FSR lane rule; a pair on one lane = fault);
//          the returned rows leave on t_srq at ONE fixed latency (the core's L 12 + this block's two registers +
//          the transfers): r6 adds one complete epoch to the r9 return schedule (+4core/+3serial).
//          Reads and writes of one serial cycle: the read sees the VM before that write (separate fixed paths; the
//          kit never reads a row it writes in the same cycle: its prefetch runs after k_done).
//   t_swg / t_srg  = serial live (constant high after reset: every request is accepted, never a back-pressure level)
//   t_err          = sticky: write/read range error, read lane collision, return-slot mismatch, x34/x43 assertion,
//                    or the VM's own fault level (POSTED kit: checked at the transaction end, as the legacy t_err).
// Phase bookkeeping: x34 presents requests at stream sample indices 2 / 3 / 0; the fixed 15-edge stream path
// (legacy decode 1 + core 13 + return 1, plus r6 epoch 4) lands every response on sample index 2 / 3 / 0 of x43.
// Mutant OT_VM_WFC_MUT_PAIR: row1's response is returned in the rq slot (pair swapped): must FAIL.
// ---------------------------------------------------------------------------------------------------------------
// r6 (Codex S81 VM): native r5 capture311.1ps failed on102pins. Registered request
// and return pins remove decode and lane-mux logic from the boundary. Write/read requests
// move +1 core edge; returned data moves +4 core edges = +3 serial edges (complete epoch).
// A small physical fault bridge restores BOTH legacy diagnostic directions. It requires
// its OWN two physical clock entries in both parent variants. Every entry requires its
// own phi-minus-R delivery from the die; source benches cannot establish this.
module dsfd_vm_wfc_request_valid_ref #(parameter integer RLAT=13) (
 input wire ck,rn,xv,input wire[559:0] xd,input wire x34f,vm_fault,
 output reg w_v,output reg[13:0] w_row,output reg[511:0] w_d,
 output reg[3:0] a_v,output reg[55:0] a_row,
 output wire[1:0] return_valid,output wire[3:0] return_lane,output reg fault
);
    reg [1:0] tq;
    always @(posedge ck or negedge rn) if (!rn) tq <= 2'b00; else tq <= {tq[0], 1'b1};
    wire tn = tq[1];
    // r6: real boundary capture before decode, and before lane selection. One stage each.
    // The return metadata is extended one stage to follow captured core results. Two fixed tail
    // stages make the total request-to-serial delta four core edges (one full 4:3 epoch).
    reg xv_pin; reg [559:0] xd_pin;
    always @(posedge ck) begin
        xv_pin <= tn && xv; xd_pin <= xd;
    end
`ifdef OT_VM_WFC_CTL_MUT_CAPTURE
    wire use_xv = xv;
`else
    wire use_xv = xv_pin;
`endif
    wire        q_wv  = use_xv && xd_pin[0];
    wire [14:0] q_wa  = xd_pin[527:513];
    wire [511:0] q_wd = xd_pin[512:1];
    wire        q_rv  = use_xv && xd_pin[528];
    wire [14:0] q_r0  = xd_pin[529 +: 15];
    wire [14:0] q_r1  = xd_pin[544 +: 15];
    wire        q_v1  = xd_pin[559];
    reg err;
    reg [RLAT:0] dv0, dv1; reg [1:0] dl0 [0:RLAT]; reg [1:0] dl1 [0:RLAT];
    always @(posedge ck) begin : p_dec integer k; reg r0ok, r1ok;
        if (!tn) begin w_v <= 1'b0; a_v <= 4'd0; err <= 1'b0; dv0 <= '0; dv1 <= '0; end
        else begin
            w_v <= q_wv && q_wa < 15'd16384;
            if (q_wv && q_wa >= 15'd16384 && q_wa != 15'h7fff) err <= 1'b1;
            r0ok = q_rv && q_r0 < 15'd16384;
            r1ok = q_rv && q_v1 && q_r1 < 15'd16384;
            if ((q_rv && q_r0 >= 15'd16384) || (q_rv && q_v1 && q_r1 >= 15'd16384)) err <= 1'b1;
            if (r0ok && r1ok && q_r0[1:0] == q_r1[1:0]) err <= 1'b1;
            a_v <= (r0ok ? (4'd1 << q_r0[1:0]) : 4'd0) | ((r1ok && !(r0ok && q_r0[1:0] == q_r1[1:0])) ? (4'd1 << q_r1[1:0]) : 4'd0);
            dv0 <= {dv0[RLAT-1:0], r0ok}; dv1 <= {dv1[RLAT-1:0], r1ok && !(r0ok && q_r0[1:0] == q_r1[1:0])};
        end
        w_row <= q_wa[13:0]; w_d <= q_wd;
        for (k = 0; k < 4; k = k + 1) a_row[14*k +: 14] <= (q_rv && q_r1[1:0] == k[1:0] && !(q_r0[1:0] == k[1:0])) ? q_r1[13:0] : q_r0[13:0];
        dl0[0] <= q_r0[1:0]; dl1[0] <= q_r1[1:0];
        for (k = 1; k <= RLAT; k = k + 1) begin dl0[k] <= dl0[k-1]; dl1[k] <= dl1[k-1]; end
    end
    assign return_valid={dv1[RLAT],dv0[RLAT]};
    assign return_lane={dl1[RLAT],dl0[RLAT]};
    always @(posedge ck) if(!tn) fault<=0; else fault<=err|x34f|vm_fault;
endmodule

module dsfd_vm_wfc_return_valid_ref #(parameter integer RESPONSE_PAD=0) (
 input wire ck,rn,input wire[1:0] return_valid,input wire[3:0] return_lane,
 input wire[3:0] e_v,input wire[2047:0] e_d,
 output wire s_v,output wire[1025:0] s_d,output reg r_bad
);
 reg[1:0] tq;
 always @(posedge ck or negedge rn) if(!rn)tq<=0;else tq<={tq[0],1'b1};
 wire tn=tq[1];
 reg[3:0] ev_pin;reg[2047:0] ed_pin;reg[1:0] valid_pin;reg[3:0] lane_pin;
 always @(posedge ck)begin ev_pin<=tn?e_v:4'd0;ed_pin<=e_d;valid_pin<=tn?return_valid:2'd0;lane_pin<=return_lane;end
    reg [1025:0] r_q; reg r_qv; 
    // decoded constant-index lane select (one-hot AND-OR), replaces the runtime part-select e_d[512*l +: 512]
    // (no wide $shiftx for synthesis; S-VM 0030, daemon runtime_partselect WARN)
    function automatic [511:0] lane512(input [2047:0] d, input [1:0] l);
        lane512 = ({512{l == 2'd0}} & d[0    +: 512]) | ({512{l == 2'd1}} & d[512  +: 512]) |
                  ({512{l == 2'd2}} & d[1024 +: 512]) | ({512{l == 2'd3}} & d[1536 +: 512]);
    endfunction
    wire e0 = valid_pin[0], e1=valid_pin[1];
    wire [1:0] l0=lane_pin[1:0],l1=lane_pin[3:2];
    always @(posedge ck) begin
        if (!tn) begin r_q <= 1026'd0; r_qv <= 1'b0; r_bad <= 1'b0; end
        else begin
`ifdef OT_VM_WFC_MUT_PAIR
            r_q <= {e0, e0 ? lane512(ed_pin, l0) : 512'd0, e1, e1 ? lane512(ed_pin, l1) : 512'd0};
`else
            r_q <= {e1, e1 ? lane512(ed_pin, l1) : 512'd0, e0, e0 ? lane512(ed_pin, l0) : 512'd0};
`endif
`ifdef OT_VM_WFC_CTL_MUT_LANE
            if (e1) r_q[1024:513] <= lane512(ed_pin, l0);   // MUTANT: second response from the first lane
`endif
            r_qv <= e0 | e1;
            if (ev_pin != ((e0 ? (4'd1 << l0) : 4'd0) | (e1 ? (4'd1 << l1) : 4'd0))) r_bad <= 1'b1;
        end
    end
    localparam integer TAIL_PAD = RESPONSE_PAD + 2;
    generate if (TAIL_PAD == 0) begin : no_pad
        assign s_d = r_q; assign s_v = r_qv;
    end else begin : fixed_pad
        reg [1025:0] pad [0:TAIL_PAD-1]; reg [TAIL_PAD-1:0] padv; integer k;
        always @(posedge ck) begin
            if (!tn) begin for (k=0;k<TAIL_PAD;k=k+1) pad[k]<=1026'd0; padv <= '0; end
            else begin pad[0]<=r_q; for(k=1;k<TAIL_PAD;k=k+1) pad[k]<=pad[k-1];
                       padv <= {padv, r_qv}; end
        end
        assign s_d = pad[TAIL_PAD-1]; assign s_v = padv[TAIL_PAD-1];
    end endgenerate
endmodule

// Sticky diagnostic joins capture every incoming pin in its own native domain.
// Real W1 epoch transports carry fault levels, using the already implemented
// 3:4 bank/parity/marker schedule. Raw 4:3 two-flop crossing failed measured STA.
module dsfd_vm_wfc_fault_core_valid_ref(input wire ck,rn,core_fault,core_fault_b,transfer_fault,remote_fault,
 output reg source_fault,summary,tx_valid);
 reg req_pin,ret_pin,transfer_pin,remote_pin;reg[7:0] warm;reg[1:0] phase;
 always @(posedge ck or negedge rn)begin
  if(!rn)begin req_pin<=0;ret_pin<=0;transfer_pin<=0;remote_pin<=0;warm<=0;phase<=3;source_fault<=0;summary<=0;tx_valid<=0;end
  else begin
   req_pin<=core_fault;ret_pin<=core_fault_b;transfer_pin<=transfer_fault;remote_pin<=remote_fault;
   warm<={warm[6:0],1'b1};phase<=phase+2'd1;
   // At the NEXT edge x43 consumes this v: phase1 is the permanently idle slot.
`ifdef OT_VM_WFC_CTL_MUT_EPOCH
   tx_valid<=1'b1;
`else
   tx_valid<=phase!=2'd3;
`endif
`ifdef OT_VM_WFC_CTL_MUT_FAULT
   source_fault<=source_fault|req_pin|transfer_pin;
`else
   source_fault<=source_fault|req_pin|ret_pin|transfer_pin;
`endif
   summary<=summary|source_fault|(warm[7]&&remote_pin);
  end
 end
endmodule
module dsfd_vm_wfc_fault_serial_valid_ref(input wire ck,rn,serial_fault,transfer_fault,remote_fault,
 output reg source_fault,g_q,e_q);
 reg own_pin,transfer_pin,remote_pin,summary;reg[5:0] warm;reg[1:0] sq;
 always @(posedge ck or negedge rn)begin
  if(!rn)begin own_pin<=0;transfer_pin<=0;remote_pin<=0;summary<=0;source_fault<=0;warm<=0;sq<=0;g_q<=0;e_q<=0;end
  else begin
   own_pin<=serial_fault;transfer_pin<=transfer_fault;remote_pin<=remote_fault;
   warm<={warm[4:0],1'b1};sq<={sq[0],1'b1};source_fault<=source_fault|own_pin|transfer_pin;
`ifdef OT_VM_WFC_CTL_MUT_CDC
   summary<=summary|source_fault;
`else
   summary<=summary|source_fault|(warm[5]&&remote_pin);
`endif
   g_q<=sq[1];e_q<=sq[1]&&summary;
  end
 end
endmodule
module dsfd_vm_wfc_fault_bridge_valid_ref (
 input wire ck_t,ck_s,rst_t,rst_s,
 input wire ck_x34_s,ck_x34_t,ck_x43_t,ck_x43_s,
 input wire rst_x34_s,rss_x34_t,rss_x43_t,rst_x43_s,
 input wire core_fault,core_fault_b,serial_fault,
 output wire core_summary,g_q,e_q
);
 wire core_source,serial_source,core_receive,serial_receive,tx_v;
 wire xf34,xf43;wire unused_v34,unused_v43;
 wire[1:0] b340,b341,b342,b430,b432,b433;wire[2:0] bp34,bp43;wire m34,m43,p43;
 dsfd_vm_wfc_fault_core_valid_ref u_core(ck_t,rst_t,core_fault,core_fault_b,xf34,core_receive,core_source,core_summary,tx_v);
 dsfd_vm_wfc_fault_serial_valid_ref u_serial(ck_s,rst_s,serial_fault,xf43,serial_receive,serial_source,g_q,e_q);
 ot_s81_vm_fault_x34_s_w1 u_x34_s(ck_x34_s,rst_x34_s,1'b1,serial_source,b340,b341,b342,bp34,m34);
 ot_s81_vm_fault_x34_t_w1 u_x34_t(ck_x34_t,rss_x34_t,b340,b341,b342,bp34,m34,unused_v34,core_receive,xf34);
 ot_s81_vm_fault_x43_t_w1 u_x43_t(ck_x43_t,rss_x43_t,tx_v,core_source,b430,b432,b433,bp43,m43,p43);
 ot_s81_vm_fault_x43_s_w1 u_x43_s(ck_x43_s,rst_x43_s,b430,b432,b433,bp43,m43,p43,unused_v43,serial_receive,xf43);
endmodule

module dsfd_vm_static_wfc_valid_ref #(parameter integer RLAT = 13, parameter integer RESPONSE_PAD = 0) (
    input wire ck_control_s, ck_control_t,
    input wire ck_fault_s, ck_fault_t, rst_fault_s, rss_fault_t,
    input wire ck_return_t,rss_return_t,
    input wire ck_fault_x34_s,ck_fault_x34_t,ck_fault_x43_t,ck_fault_x43_s,
    input wire rst_fault_x34_s,rss_fault_x34_t,rss_fault_x43_t,rst_fault_x43_s,
    input wire ck_x34_s, ck_x34_t, ck_x43_s, ck_x43_t,
    input wire rst_control_s, rss_control_t,
    input wire rst_x34_s, rss_x34_t, rst_x43_s, rss_x43_t,
    input  wire [559:0]  f_wfc,
    output wire [1028:0] t_wfc,
    // stream side to / from dsfd_vm_static_core
    output wire          w_v, output wire [13:0] w_row, output wire [511:0] w_d,
    output wire [3:0]    a_v, output wire [55:0] a_row,         // aux ports 8..11
    input  wire [3:0]    e_v, input wire [2047:0] e_d,          // aux ports 8..11 returns (core output registers)
    input  wire          vm_fault,                              // stream level
    output wire          fault                                  // core summary from u_fault; diagnostic delay only
);
    // Wires only: x34, request/return control leaf, fault bridge and x43.
    wire xv; wire [559:0] xd; wire x34f; wire ov; wire [1025:0] od; wire x43f; wire sv; wire [1025:0] sd; wire g_q, e_q; wire native_core_fault;
    ot_s81_vm_x34 #(.W(560)) u_xi (.s_ck(ck_x34_s), .s_rst_n(rst_x34_s), .s_v(f_wfc[0] | f_wfc[528]), .s_d(f_wfc),
        .t_ck(ck_x34_t), .t_rst_n(rss_x34_t), .o_v(xv), .o_d(xd), .fault(x34f));
    wire [1:0] return_valid;wire[3:0] return_lane;wire return_fault;
    dsfd_vm_wfc_request_valid_ref #(.RLAT(RLAT)) u_req (
      .ck(ck_control_t),.rn(rss_control_t),.xv(xv),.xd(xd),.x34f(x34f),.vm_fault(vm_fault),
      .w_v(w_v),.w_row(w_row),.w_d(w_d),.a_v(a_v),.a_row(a_row),
      .return_valid(return_valid),.return_lane(return_lane),.fault(native_core_fault));
    dsfd_vm_wfc_return_valid_ref #(.RESPONSE_PAD(RESPONSE_PAD)) u_ret (
      .ck(ck_return_t),.rn(rss_return_t),.return_valid(return_valid),.return_lane(return_lane),
      .e_v(e_v),.e_d(e_d),.s_v(sv),.s_d(sd),.r_bad(return_fault));
    dsfd_vm_wfc_fault_bridge_valid_ref u_fault (.ck_t(ck_fault_t), .ck_s(ck_fault_s),
      .rst_t(rss_fault_t), .rst_s(rst_fault_s),
      .ck_x34_s(ck_fault_x34_s),.ck_x34_t(ck_fault_x34_t),.ck_x43_t(ck_fault_x43_t),.ck_x43_s(ck_fault_x43_s),
      .rst_x34_s(rst_fault_x34_s),.rss_x34_t(rss_fault_x34_t),.rss_x43_t(rss_fault_x43_t),.rst_x43_s(rst_fault_x43_s), .core_fault(native_core_fault),.core_fault_b(return_fault),.serial_fault(x43f),
      .core_summary(fault),.g_q(g_q),.e_q(e_q));
    ot_s81_vm_x43 #(.W(1026)) u_xo (.t_ck(ck_x43_t), .t_rst_n(rss_x43_t), .s_v(sv), .s_d(sd),
        .s_ck(ck_x43_s), .s_rst_n(rst_x43_s), .o_v(ov), .o_d(od), .fault(x43f));
    assign t_wfc = {e_q, od, g_q, g_q};
endmodule
`default_nettype wire
