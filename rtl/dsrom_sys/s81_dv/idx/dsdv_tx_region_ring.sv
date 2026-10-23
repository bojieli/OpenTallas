`timescale 1ns/1ps
// Fixed calendar boundary; no credit, enable, occupancy or backpressure.
// All pointers start at the same reset epoch. K is priced in the TX lookup pipe.
// Separate narrow slices keep mux selects and slot enables local (<=16 bits).
(* keep_hierarchy = "yes" *)
module dsdv_tx_ring_slice #(parameter integer W=16, D=4, K=2, ID=0,
    AW=$clog2(D)) (
    input wire src_ck,dst_ck,src_rn,dst_rn,input wire[W-1:0]d,output reg[W-1:0]q);
    (* keep="true" *) reg[AW-1:0]wp,rp;
    reg[$clog2(K+2)-1:0]warm;
    (* keep="true" *) reg[W-1:0]bank[0:D-1];
    always @(posedge src_ck or negedge src_rn)
        if(!src_rn)wp<=0;else wp<=wp+1'b1;
    for(genvar s=0;s<D;s=s+1)begin:g_slot
        always @(posedge src_ck)if(wp==AW'(s))bank[s]<=d;
    end
    always @(posedge dst_ck or negedge dst_rn)
        if(!dst_rn)begin rp<=0;warm<=0;end
        else begin rp<=rp+1'b1;if(warm<K+1)warm<=warm+1'b1;end
    always @(posedge dst_ck)q<=(warm>=K)?bank[AW'(rp-K)]:{W{1'b0}};
endmodule

(* keep_hierarchy="yes" *)
module dsdv_tx_region_ring #(parameter integer W=300,D=4,K=2,ID=0,
    SL=(D<=4)?16:8, NS=(W+SL-1)/SL)(input wire src_ck,dst_ck,rn,input wire[W-1:0]d,output wire[W-1:0]q);
    wire[NS-1:0]sr,dr;
    // Independent synchronous release in each physical region. The first local
    // synchronizer stage asserts the bounded leaves asynchronously; common rn
    // sees only two reset pins per group, never all slice pointers.
    dsdv_tx_ring_resets #(.N(NS),.ID(2*ID))u_src_reset(.ck(src_ck),.rn(rn),.q(sr));
    dsdv_tx_ring_resets #(.N(NS),.ID(2*ID+1))u_dst_reset(.ck(dst_ck),.rn(rn),.q(dr));
    for(genvar s=0;s<NS;s=s+1)begin:g_slice
        localparam integer SW=(s*SL+SL>W)?W-s*SL:SL;
        dsdv_tx_ring_slice #(.W(SW),.D(D),.K(K),.ID(ID+s))u(
            .src_ck(src_ck),.dst_ck(dst_ck),.src_rn(sr[s]),.dst_rn(dr[s]),.d(d[s*SL+:SW]),.q(q[s*SL+:SW]));
    end
endmodule

(* keep_hierarchy="yes" *)
module dsdv_tx_ring_resets #(parameter integer N=19,ID=0,NG=(N+18)/19)(
 input wire ck,rn,output wire[N-1:0]q);
 for(genvar g=0;g<NG;g=g+1)begin:g_group
  localparam integer NN=(19*g+19>N)?N-19*g:19;
  (* async_reg="true",keep="true" *) reg[1:0]sync_q;
  (* keep="true",dont_touch="true" *)reg[NN-1:0]leaf;
  always @(posedge ck or negedge rn)
   if(!rn)sync_q<=0;else sync_q<={sync_q[0],1'b1};
  always @(posedge ck or negedge sync_q[0])
   if(!sync_q[0])leaf<=0;else leaf<={NN{sync_q[1]}};
  assign q[19*g+:NN]=leaf;
 end
endmodule

// Physical region branch; identity in behavioural simulation.
(* keep_hierarchy="yes" *)
module dsdv_tx_clock_branch #(parameter integer ID=0)(input wire ck,output wire ck_o);
`ifdef SYNTHESIS
    (* keep="true",dont_touch="true" *) BUFx24_ASAP7_75t_R u_ck(.A(ck),.Y(ck_o));
`else
`ifdef OT_TX_REGION_PHASE_PS
    // Transport every edge: a delayed continuous assignment is inertial and
    // would erase all pulses when phase exceeds the half period.
    if(ID==1 && `OT_TX_REGION_PHASE_PS!=0)begin:g_phase
        reg ck_sim=1'b0;
        always @(ck)ck_sim <= #(`OT_TX_REGION_PHASE_PS*0.001) ck;
        assign ck_o=ck_sim;
    end else begin:g_zero_phase
        assign ck_o=ck;
    end
`else
    assign ck_o=ck;
`endif
`endif
endmodule
