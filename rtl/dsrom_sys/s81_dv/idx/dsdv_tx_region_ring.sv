`timescale 1ns/1ps
// Fixed calendar boundary; no credit, enable, occupancy or backpressure.
// All pointers start at the same reset epoch. K is priced in the TX lookup pipe.
// Separate narrow slices keep mux selects and slot enables local (<=16 bits).
(* keep_hierarchy = "yes" *)
module dsdv_tx_ring_slice #(parameter integer W=16, D=4, K=2, ID=0,
    AW=$clog2(D)) (
    input wire src_ck,dst_ck,rn,input wire[W-1:0]d,output reg[W-1:0]q);
    (* keep="true" *) reg[AW-1:0]wp,rp;
    reg[$clog2(K+2)-1:0]warm;
    (* keep="true" *) reg[W-1:0]bank[0:D-1];
    always @(posedge src_ck or negedge rn)
        if(!rn)wp<=0;else wp<=wp+1'b1;
    for(genvar s=0;s<D;s=s+1)begin:g_slot
        always @(posedge src_ck)if(wp==AW'(s))bank[s]<=d;
    end
    always @(posedge dst_ck or negedge rn)
        if(!rn)begin rp<=0;warm<=0;end
        else begin rp<=rp+1'b1;if(warm<K+1)warm<=warm+1'b1;end
    always @(posedge dst_ck)q<=(warm>=K)?bank[AW'(rp-K)]:{W{1'b0}};
endmodule

(* keep_hierarchy="yes" *)
module dsdv_tx_region_ring #(parameter integer W=300,D=4,K=2,ID=0,
    SL=(D<=4)?16:8, NS=(W+SL-1)/SL)(input wire src_ck,dst_ck,rn,input wire[W-1:0]d,output wire[W-1:0]q);
    wire[NS-1:0]lr;
    if(NS<=30)begin:g_one_reset
        ot_rst_relay #(.REGIONS(NS))u_rr(.clk(dst_ck),.rst_n_in(rn),.rst_n(lr));
    end else begin:g_two_reset
        localparam integer N0=NS/2,N1=NS-N0;
        wire[1:0]rr;
        ot_rst_relay #(.REGIONS(2))u_root(.clk(dst_ck),.rst_n_in(rn),.rst_n(rr));
        ot_rst_relay #(.REGIONS(N0))u_low(.clk(dst_ck),.rst_n_in(rr[0]),.rst_n(lr[N0-1:0]));
        ot_rst_relay #(.REGIONS(N1))u_high(.clk(dst_ck),.rst_n_in(rr[1]),.rst_n(lr[NS-1:N0]));
    end
    for(genvar s=0;s<NS;s=s+1)begin:g_slice
        localparam integer SW=(s*SL+SL>W)?W-s*SL:SL;
        dsdv_tx_ring_slice #(.W(SW),.D(D),.K(K),.ID(ID+s))u(
            .src_ck(src_ck),.dst_ck(dst_ck),.rn(lr[s]),.d(d[s*SL+:SW]),.q(q[s*SL+:SW]));
    end
endmodule

// Physical region branch; identity in behavioural simulation.
(* keep_hierarchy="yes" *)
module dsdv_tx_clock_branch #(parameter integer ID=0)(input wire ck,output wire ck_o);
`ifdef SYNTHESIS
    (* keep="true",dont_touch="true" *) BUFx24_ASAP7_75t_R u_ck(.A(ck),.Y(ck_o));
`else
    assign ck_o=ck;
`endif
endmodule
