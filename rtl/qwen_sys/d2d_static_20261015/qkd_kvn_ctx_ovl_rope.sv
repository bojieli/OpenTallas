`timescale 1ns/1ps
// Real recurring Ckind12 authority. Copies keep the original three sampled
// edges: input capture, owner/stage update, output capture. No queue or stall.
module qkd_kvn_ctx_ovl_rope #(
 parameter integer MUT_USER=0, parameter integer MUT_STALE=0
)(
 input wire ck,rst_n,
 input wire [551:0] head_record,
 input wire [3:0] ovl_users,calrx,
 input wire adm_done,reseed,
 output reg [58:0] compiled_identity,
 output reg [1:0] compiled_generation,
 output reg fault
);
 (* keep=1,dont_touch=1 *)reg reset_first,reset_last;
 (* keep=1,dont_touch=1 *)reg [3:0] reset_bank;
 always @(posedge ck)begin
   reset_first<=rst_n;reset_last<=reset_first;reset_bank<={4{reset_first}};
 end
 wire [1:0] rx_user=ovl_users[3:2], cal_user_rx=calrx[3:2];
 reg [551:0] hq;
 reg [1:0] uq,cuser_q;
 reg cstart_q,cseg_q,adm_q;
 // Read selectors are independent same-edge captures, eight owner bits each.
 (* keep=1,dont_touch=1 *)reg [1:0] uq_read[0:15];
 (* keep=1,dont_touch=1 *)reg [1:0] cu_read[0:7];
 (* keep=1,dont_touch=1 *)reg [1:0] uq_write[0:3];
 (* keep=1,dont_touch=1 *)reg [3:0] take_legal_q;
 // Two same-edge copies of the stage selector (r3 single copy: 38 native loads).
 (* keep=1,dont_touch=1 *)reg [1:0] stage_user_q;
 (* keep=1,dont_touch=1 *)reg [1:0] stage_user_q2;
 function automatic legal_head(input[551:0] h,input[1:0]u);
   reg[60:0]o;reg[35:0]hd;
   begin o=h[64:4];hd=h[551:516];
   legal_head=hd[35:31]==0&&hd[26:21]==63&&hd[4:0]==0&&
     hd[20:5]==o[58:43]&&o[42:37]==0&&o[5:0]==0&&o[36:19]<151936&&
     (MUT_USER!=0||o[44:43]==u);
   end
 endfunction
 wire take_in=head_record[3]&&head_record[546:543]==4'd12;
 integer i;
 always @(posedge ck)begin
   hq<=head_record;uq<=rx_user;cuser_q<=cal_user_rx;
   cstart_q<=calrx[0];cseg_q<=calrx[1];adm_q<=adm_done;
   stage_user_q<=cal_user_rx;stage_user_q2<=cal_user_rx;
   for(i=0;i<16;i=i+1)uq_read[i]<=rx_user;
   for(i=0;i<8;i=i+1)cu_read[i]<=cal_user_rx;
   for(i=0;i<4;i=i+1)begin
     uq_write[i]<=rx_user;take_legal_q[i]<=take_in&&legal_head(head_record,rx_user);
   end
 end
 reg [60:0] owners[0:3];
 reg [3:0] have;
 reg [5:0] stage[0:3];
 reg [3:0] stage_valid;
 wire [60:0] owner=hq[64:4];
 wire take=hq[3]&&hq[546:543]==4'd12;
 wire legal=legal_head(hq,uq);
 wire [60:0] previous,chosen;
 genvar g,b;
 generate for(g=0;g<8;g=g+1)begin:read_group
   localparam integer LO=g*8;
   localparam integer N=(LO+8>61)?61-LO:8;
   assign chosen[LO+:N]=owners[cu_read[g]][LO+:N];
 end
 for(g=0;g<16;g=g+1)begin:previous_group
   localparam integer LO=g*4;
   localparam integer N=(LO+4>61)?61-LO:4;
   if(N>0)assign previous[LO+:N]=owners[uq_read[g]][LO+:N];
 end endgenerate
 wire have_u=have[uq];
 wire bad_previous=have_u&&(owner[58:45]<previous[58:45]||
   (owner[58:45]==previous[58:45]&&owner!=previous));
 wire previous_ok=!reseed&&!bad_previous&&(MUT_STALE==0||!have_u);
 wire [5:0] selected_stage;
 assign selected_stage[2:0]=stage_valid[stage_user_q]?stage[stage_user_q][2:0]:3'd0;
 assign selected_stage[5:3]=stage_valid[stage_user_q2]?stage[stage_user_q2][5:3]:3'd0;
 wire bad_stage=selected_stage==0||selected_stage>=36;
 // Fault timing and sticky behavior are unchanged, including reseed priority.
 always @(posedge ck or negedge reset_last)
   if(!reset_last)fault<=0;
   else if(!reseed)begin
     if(take&&(!legal||bad_previous))fault<=1;
     if(cstart_q&&adm_q&&!cseg_q&&bad_stage)fault<=1;
   end
 generate for(b=0;b<4;b=b+1)begin:owner_bank
   // Reset/reseed invalidate the stage; the private counter is unreset.
   // A segment start overwrites it before it is visible, preserving stage0.
   always @(posedge ck or negedge reset_bank[b])
     if(!reset_bank[b])begin have[b]<=0;stage_valid[b]<=0;end
     else if(reseed)begin have[b]<=0;stage_valid[b]<=0;end
     else begin
       if(take&&legal&&previous_ok&&uq==b)have[b]<=1;
       if(cstart_q&&adm_q&&cuser_q==b&&cseg_q)stage_valid[b]<=1;
     end
   always @(posedge ck)if(cstart_q&&adm_q&&cuser_q==b)begin
     if(cseg_q)stage[b]<=1;
     else if(stage_valid[b]&&stage[b]>0&&stage[b]<36)stage[b]<=stage[b]+1;
   end
   for(g=0;g<4;g=g+1)begin:write_group
     localparam integer LO=g*16;
     localparam integer N=(LO+16>61)?61-LO:16;
     // Keep the complete enable as a boundary: do not factor a shared
     // predicate through all244 owner-bit muxes. Each cone owns <=16 bits.
     // SQC-HROOT r4: a kept wire did not stop ABC from re-factoring previous_ok into all 244
     // owner-bit muxes (r1-r3 native census max 260 on one AO21). The enable is now an
     // instantiated library AND4 under SYNTHESIS: previous_ok drives the 16 enable cells only,
     // each enable drives its own <=16 owner bits. Same logic, same edges.
     (* keep=1,dont_touch=1 *)wire write_enable;
     wire user_hit=uq_write[g]==b;
`ifdef SYNTHESIS
     AND4x1_ASAP7_75t_R u_we (.A(reset_bank[b]),.B(take_legal_q[g]),.C(user_hit),.D(previous_ok),.Y(write_enable));
`else
     assign write_enable=reset_bank[b]&&take_legal_q[g]&&user_hit&&previous_ok;
`endif
     always @(posedge ck)
       if(write_enable)
         owners[b][LO+:N]<=owner[LO+:N];
   end
 end endgenerate
 always @(posedge ck)begin
   compiled_identity<={chosen[58:43],have[cuser_q]&&!fault?selected_stage:6'd0,chosen[36:6],6'd0};
   compiled_generation<=chosen[60:59];
 end
`ifdef OT_FO_CHECK
 integer n;
 always @(posedge ck)if(reset_last)begin
   for(n=0;n<16;n=n+1)if(uq_read[n]!==uq)$fatal(1,"CTX_COPY_MISMATCH previous");
   for(n=0;n<8;n=n+1)if(cu_read[n]!==cuser_q)$fatal(1,"CTX_COPY_MISMATCH chosen");
   for(n=0;n<4;n=n+1)if(uq_write[n]!==uq||take_legal_q[n]!==(take&&legal))$fatal(1,"CTX_COPY_MISMATCH write");
   if(stage_user_q!==cuser_q||stage_user_q2!==cuser_q)$fatal(1,"CTX_COPY_MISMATCH stage");
 end
`endif
endmodule
