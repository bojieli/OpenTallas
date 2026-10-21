`timescale 1ns/1ps
module tb_hostb;
 reg ck=0;always #0.5 ck=~ck;
 reg rst_n=0;integer cyc=-1,bad=0,got0=0,got1=0,ksgot=0;
 reg [1103:0] ri=0,local0=0,local1=0;
 wire [1103:0] tolocal0,tolocal1,next0,next1;
 wire [514:0] host0,host1;wire [52:0] ks0,ks1;wire [11:0] fault0,fault1;
 wire [2:0] sl0,sl1;wire [5:0] am0,am1;wire ac0,ac1;
 reg hs0=0,hs1=0,fw0=0,fw1=0;
 reg [47:0] te0=0,te1=0;reg [7:0] expect0=1,expect1=1;
 reg [1103:0] events[0:9999];reg [1103:0] ordinary[0:9999];
 reg [47:0] transit[0:9999];reg [3:0] book[0:9999];
 reg [514:0] expected0[0:9999],expected1[0:9999];
 reg [52:0] expectedks[0:9999];
 integer stopat=100,mode=0,i;string vectors;
 localparam [52:0] KS=53'h1000082e4fffff;
 dsdv_hostb_stage #(.ENABLE(1)) a(.ck(ck),.rst_n(rst_n),.configured(1'b1),.local_stage(8'd0),.local_rank(2'd0),
 .epoch_id(32'h1021),.programme_id(64'hf1c617d9224a57bf),.receiver_edge(48'(cyc)),.transit_body_edge(te0),
 .expected_tid(16'd37),.expected_header_stage(expect0),.expected_user(10'd0),.expected_position(21'd1048575),.expected_token(21'd16754),
 .header_slot(hs0),.job_active(mode==14),.starter_armed(1'b1),.from_prev(ri),.local_ro(local0),.return_ro(1104'd0),
 .forward_slot(fw0),.return_slot(1'b0),.to_local(tolocal0),.next_ro(next0),.f_host(host0),.ks_descriptor(ks0),
 .ks_slot(sl0),.arm_mask(am0),.arm_commit(ac0),.fault(fault0));
 dsdv_hostb_stage #(.ENABLE(1)) b(.ck(ck),.rst_n(rst_n),.configured(1'b1),.local_stage(8'd1),.local_rank(2'd0),
 .epoch_id(32'h1021),.programme_id(64'hf1c617d9224a57bf),.receiver_edge(48'(cyc)),.transit_body_edge(te1),
 .expected_tid(16'd37),.expected_header_stage(expect1),.expected_user(10'd0),.expected_position(21'd1048575),.expected_token(21'd16754),
 .header_slot(hs1),.job_active(mode==14),.starter_armed(1'b1),.from_prev(next0),.local_ro(local1),.return_ro(1104'd0),
 .forward_slot(fw1),.return_slot(1'b0),.to_local(tolocal1),.next_ro(next1),.f_host(host1),.ks_descriptor(ks1),
 .ks_slot(sl1),.arm_mask(am1),.arm_commit(ac1),.fault(fault1));
 // Actual distinct head collector and actual source-return interface component.
 reg sample=0,send=0;reg [76:0] th=0;reg [53:0] tk=0;
 wire [1103:0] ret,toctl;wire [3:0] rf,hf;wire htv;wire [552:0] htd;
 reg returnslot=0;
 reg [76:0] sampled_th;reg [53:0] sampled_tk;
`ifdef HBE_REAL_CONSUMER
 localparam REQUIRE_KIT=0; // Real status return; no job/KIT is fabricated.
`else
 localparam REQUIRE_KIT=1;
`endif
 always @(posedge ck)if(sample)begin sampled_th<=th;sampled_tk<=tk;end
 dsdv_hostb_return r(.ck(ck),.rst_n(rst_n),.configured(1'b1),.sample_slot(sample),.send_slot(send),.require_kit(REQUIRE_KIT),.context_valid(1'b1),
 .stage_id(8'd1),.rank_id(2'd0),.tid(16'd37),.user_id(10'd0),.position(21'd1048575),.token(21'd16754),.epoch_id(32'h1021),
 .arrival_deadline(48'd9999),.programme_id(64'hf1c617d9224a57bf),.t_host(th),.t_kd(tk),.return_ring(ret),.fault(rf));
 dsdv_hostb_head h(.ck(ck),.rst_n(rst_n),.configured(1'b1),.return_slot(returnslot),.expected_stage(8'd1),.expected_rank(2'd0),.local_group(2'd2),
 .expected_tid(mode==19?16'd38:16'd37),.expected_user(10'd0),.expected_position(21'd1048575),.expected_token(21'd16754),.epoch_id(32'h1021),
 .programme_id(64'hf1c617d9224a57bf),.receiver_edge(48'(cyc)),.ring_i(ret),.to_ctl(toctl),.htv(htv),.htd(htd),.fault(hf));
`ifdef HBE_REAL_CONSUMER
 `include "consumer_instance.svh"
`endif
 initial begin
  if(!$value$plusargs("VECTORS=%s",vectors))$fatal(1,"VECTORS required");
  if(!$value$plusargs("STOP=%d",stopat))$fatal(1,"STOP required");
  if(!$value$plusargs("MODE=%d",mode))mode=0;
  for(i=0;i<10000;i=i+1)begin events[i]=0;ordinary[i]=0;transit[i]=0;book[i]=0;expected0[i]=0;expected1[i]=0;expectedks[i]=0;end
  $readmemh({vectors,"/events.memh"},events);$readmemh({vectors,"/ordinary.memh"},ordinary);
  $readmemh({vectors,"/transit.memh"},transit);$readmemh({vectors,"/book.memh"},book);
  $readmemh({vectors,"/expected0.memh"},expected0);$readmemh({vectors,"/expected1.memh"},expected1);$readmemh({vectors,"/expectedks.memh"},expectedks);
 end
 always @(negedge ck)begin
  cyc=cyc+1;rst_n=cyc>=5;
  ri=events[cyc];local0=ordinary[cyc];local1=0;
  te0=transit[cyc];hs0=book[cyc][0];hs1=book[cyc][1];fw0=book[cyc][2];fw1=book[cyc][3];
  // Real source bits at fixtureboundary only, no stagecompletion fabricated.
  sample=cyc==stopat-10;send=cyc==stopat-8&&mode!=18;returnslot=cyc==stopat-7;
`ifdef HBE_REAL_CONSUMER
  th=actual_th;tk=actual_tk;
`else
  th=77'h123456789abcdef;tk={1'b1,(mode==20?21'd16755:21'd16754),32'h0};
`endif
 end
 integer retgot=0;
 always @(posedge ck)begin
  #0.01;
  if(cyc>=0)begin
   if(host0!==expected0[cyc] && (host0[0]||expected0[cyc][0]))begin bad++;$display("BAD HOST0 cycle%0d got%h expected%h",cyc,host0,expected0[cyc]);end
   if(host1!==expected1[cyc] && (host1[0]||expected1[cyc][0]))begin bad++;$display("BAD HOST1 cycle%0d",cyc);end
   if(ks1[52]||expectedks[cyc][52])begin if(ks1!==expectedks[cyc])begin bad++;$display("BAD KS cycle%0d",cyc);end end
   if(host0[0])got0++;if(host1[0])got1++;if(ks1[52])ksgot++;
   // Ordinary output is same-cycle payload: new component adds no register.
   if(mode!=13 && ordinary[cyc][0] && next0!==ordinary[cyc])begin bad++;$display("BAD ordinary bypass cycle%0d",cyc);end
   if(htv)begin
     retgot++;
     if(htd[3:0]!=10||htd[7:6]!=2||htd[366:290]!==sampled_th||htd[420:367]!==sampled_tk||toctl[0])begin bad++;$display("BAD RETURN HSF0");end
   end
   if(cyc==stopat)begin
     if((mode==0||mode==5||mode==6) && (fault0||fault1||rf||hf||retgot!=1))begin bad++;$display("BAD faults %h %h %h %h ret%0d",fault0,fault1,rf,hf,retgot);end
     if(mode!=0&&mode!=5&&mode!=6 && !(fault0||fault1||rf||hf))begin bad++;$display("BAD causal nofault");end
     if(bad)$fatal(1,"FAIL HBE1 mode%0d bad%0d host%0d/%0d KS%0d",mode,bad,got0,got1,ksgot);
     $display("PASS HBE1 mode%0d host%0d/%0d KS%0d return%0d faults%h/%h",mode,got0,got1,ksgot,retgot,fault0,fault1);$finish;
   end
  end
 end
endmodule
