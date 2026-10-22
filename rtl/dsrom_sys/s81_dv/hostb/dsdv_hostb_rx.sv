`timescale 1ns/1ps
`default_nettype none
// HBE1v2 SOURCE component. Bind at actual s_0N entry BEFORE ordinary ring
// delivery. Counter/epoch/programme/TID pins are real compiled/armed sources;
// this module creates none of them. No production phase/anchor claim.
module dsdv_hostb_rx (
 input wire ck, rst_n,
 input wire configured, input wire [7:0] local_stage,
 input wire [1:0] local_rank, input wire [31:0] epoch_id,
 input wire [63:0] programme_id, input wire [47:0] receiver_edge,transit_body_edge,
 input wire [15:0] expected_tid, input wire [7:0] expected_header_stage,
 input wire [9:0] expected_user,input wire [20:0] expected_position,expected_token,
 input wire header_slot, input wire job_active, input wire starter_armed,
 input wire [1103:0] ring_i,
 output wire [1103:0] local_ring,
 output reg [1103:0] forward_ring,
 output wire [514:0] f_host,
 output reg [52:0] ks_descriptor,
 output reg [2:0] ks_slot,
 output reg [5:0] arm_mask,
 output reg arm_commit,
 output reg [7:0] fault
);
 wire rn;
 (* keep_hierarchy="yes" *) ot_reset_sync #(.ASYNC_STAGES(2)) u_reset(.clk(ck),.async_rst_n(rst_n),.sync_rst_n(rn));
 wire hv=ring_i[0] && ring_i[3:1]==3'd6;
 wire [511:0] p=ring_i[532:21];
 wire [3:0] op=p[39:36];
 wire addressed=(p[47:40]==local_stage && p[49:48]==local_rank);
 wire shape=p[31:0]==32'h31454248 && p[35:32]==4'd2 && p[47:40]<8'd241 && op<4;
 wire identity=configured && p[161:130]==epoch_id && p[273:210]==programme_id && p[65:50]==expected_tid &&
 p[87:78]==expected_user && p[108:88]==expected_position && p[129:109]==expected_token;
 reg pending, target;
 wire [47:0] body_edge;
 wire [31:0] expected_crc;
 wire [1:0] body_class;
 wire [33:0] class_crc;assign {body_class,expected_crc}=class_crc;
 genvar hb;
 generate for(hb=0;hb<4;hb=hb+1)begin:g_date
  (* keep_hierarchy="yes" *) dsdv_hostb_header_bank #(.ID(hb),.W(12)) u_bank(.ck(ck),.hv(hv),.pending(pending),.host0(op==0),
   .stage_id(p[47:40]),.local_stage(local_stage),.rank_id(p[49:48]),.local_rank(local_rank),
   .local_d(p[162+12*hb+:12]),.transit_d(transit_body_edge[12*hb+:12]),.q(body_edge[12*hb+:12]));
 end
 for(hb=0;hb<3;hb=hb+1)begin:g_crc_class
  localparam integer W=(34-12*hb<12)?34-12*hb:12;
  wire [33:0] field_d={p[77:76],p[305:274]};
  (* keep_hierarchy="yes" *) dsdv_hostb_header_bank #(.ID(4+hb),.W(W),.LOCAL_ONLY(1)) u_bank(.ck(ck),.hv(hv),.pending(pending),.host0(op==0),
   .stage_id(p[47:40]),.local_stage(local_stage),.rank_id(p[49:48]),.local_rank(local_rank),
   .local_d(field_d[12*hb+:W]),.transit_d({W{1'b0}}),.q(class_crc[12*hb+:W]));
 end endgenerate
 reg [511:0] b0,b1,b2;
 reg [31:0] crc1,expect0,expect1;
 reg [1:0] cl0,cl1,cl2;
 reg bv0,bv1,write2;
 wire [31:0] crc_value;
 dsdv_hostb_crc512 u_crc(.d(b0),.q(crc_value));
 assign f_host={cl2,b2,write2};
 // Only HBE traffic is intercepted. All other ring bits/cycles are unchanged.
 assign local_ring={ring_i[1103:1],ring_i[0] && !hv};
 wire body_now=hv && pending;
 wire body_good=body_now && receiver_edge==body_edge && target && fault==0;
 wire boot_write=cl1==0 && (b1[7:0]==8'h10 || b1[7:0]==8'h11 || b1[7:0]==8'h13 ||
                 b1[7:0]==8'h14 || b1[7:0]==8'h17 || b1[7:0]==8'h19);
 // Unreset data pipes; each payload is aligned to its independently reset valid.
 always @(posedge ck) begin
   b0<=p;b1<=b0;b2<=b1;
   crc1<=crc_value;expect0<=expected_crc;expect1<=expect0;
   cl0<=body_class;cl1<=cl0;cl2<=cl1;
   ks_descriptor[51:0]<=p[325:274];ks_slot<=p[329:327];arm_mask<=p[279:274];
   // Intercepted HFWD is exactly512 payload +routing; selected HEAD may
   // retain inactive ordinary upper bits. Normalize only the kind6 record.
   forward_ring[1103:1]<={571'd0,ring_i[532:1]};
 end
 always @(posedge ck or negedge rn) begin
   if(!rn) begin
     pending<=0;target<=0;
     bv0<=0;bv1<=0;write2<=0;ks_descriptor[52]<=0;arm_commit<=0;
     forward_ring[0]<=0;fault<=0;
   end else begin
     bv0<=body_good;bv1<=bv0;write2<=0;ks_descriptor[52]<=0;arm_commit<=0;forward_ring[0]<=0;
     if(bv1) begin
       if(crc1!=expect1) fault[0]<=1;
       else if(boot_write && job_active) fault[1]<=1;
       else if(fault==0) write2<=1;
     end
     // Exact edge, no wait until completion. A missing body never emits a write.
     if(pending && receiver_edge>=body_edge) begin
       if(!hv || receiver_edge!=body_edge) fault[2]<=1;
       pending<=0;
     end
     if(hv) begin
       if(pending) begin
         // Raw body may equal a header: NEVER inspect magic in this phase.
         if(receiver_edge!=body_edge) begin fault[2]<=1;pending<=0;end
         if(!target) forward_ring[0]<=1;
       end else if(!configured || !header_slot || p[47:40]!=expected_header_stage || p[49:48]!=local_rank) fault[7]<=1;
       else if(!shape) fault[3]<=1;
       else if(op==3) begin
         // RETURN stage field names its source; it travels to the actual head.
         if(p[75:66]!=10'd131 || |p[511:405]) fault[3]<=1;
         else forward_ring[0]<=1;
       end else if(!addressed) begin
         forward_ring[0]<=1;
         if(op==0) begin
           if(p[75:66]!=10'd514 || |p[511:306] || transit_body_edge<=receiver_edge) fault[3]<=1;
           else begin pending<=1;target<=0;end
         end
       end else if(!identity) fault[4]<=1;
       else case(op)
        0: if(p[75:66]!=10'd514 || |p[511:306] || p[209:162]<=receiver_edge) fault[3]<=1;
           else begin pending<=1;target<=1;end
        1: if(p[77:76]!=0 || p[75:66]!=10'd53 || |p[511:330] || !p[326] || p[329:327]>5 ||
              p[325:316]!=p[87:78] || p[315:295]!=p[129:109] || p[294:274]!=p[108:88] ||
              receiver_edge>p[209:162]) fault[5]<=1;
           else ks_descriptor[52]<=fault==0;
        2: if(!starter_armed || p[77:76]!=0 || p[75:66]!=0 || |p[511:280] || p[279:274]==0 || receiver_edge>p[209:162]) fault[6]<=1;
           else arm_commit<=fault==0;
        default: fault[3]<=1;
       endcase
     end
   end
 end
endmodule
`default_nettype wire
