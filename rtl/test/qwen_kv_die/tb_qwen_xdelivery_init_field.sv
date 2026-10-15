// Logical initialization composition only. Diagnostic 1..16 stage transport,
// component acceptance/retirement/seals; no production tile or VM certificates.
module tb_qwen_xdelivery_init_field;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,offer_v=0,acquire_ready=0,accept_v=0,source_output_drained=0,release_ready=0,transport_flush_ack=0;
 wire offer_ready,acquire_v,dispatch_v,banks_begin,release_v,flush_req,fault;
 reg [378:0] offer_ib=379'h123;reg offer_mode=0;reg [767:0] offer_participants={768{1'b1}};
 reg [31:0] acquire_version=32'hc1234567;
 wire [767:0] held_participants;
 wire [378:0] held_ib;wire held_mode;wire [15:0] held_context;wire [31:0] held_version;
 reg [9:0] accept_tile=0;reg [15:0] accept_context=0;reg [31:0] accept_version=32'hc1234567;reg [378:0] accept_ib=379'h123;
 wire [15:0] bank_drained,bank_init_v,bank_init_ack,bank_fault;
 wire [255:0] bank_init_context;wire [511:0] bank_init_version;wire [767:0] bank_init_participants;
 wire [767:0] issue_ready,retire_ready;reg issue=0,retire=0,seal=0,corrupt_receipt=0;
 ot_qwen_xdelivery_lifetime_init_ctrl #(.ENABLE(1)) dut(.*);
 for(genvar b=0;b<16;b=b+1) begin: bank
  reg [b:0] bp;
  reg [15:0] cp[0:b];reg [31:0] vp[0:b];reg [47:0] mp[0:b];
  wire ready;wire [15:0] actual_context;
  always @(posedge clk)begin
   if(!rst_n)begin bp<=0;for(integer j=0;j<=b;j=j+1)begin cp[j]<=0;vp[j]<=0;mp[j]<=0;end end
   else begin
    bp[0]<=banks_begin;cp[0]<=held_context;vp[0]<=held_version;mp[0]<=held_participants[b*48+:48];
    for(integer j=1;j<=b;j=j+1)begin bp[j]<=bp[j-1];cp[j]<=cp[j-1];vp[j]<=vp[j-1];mp[j]<=mp[j-1];end
    if(bp[b]&&!ready)$fatal(1,"diagnostic BEGIN transport lost admission");
   end
  end
  assign bank_init_context[b*16+:16]=actual_context ^ ((b==15 && corrupt_receipt)?16'd1:16'd0);
  ot_qwen_xdelivery_ack_vector_init #(.ENABLE(1)) ledger(
   .clk(clk),.rst_n(rst_n),.begin_v(bp[b]),.fenced_clear(1'b0),.begin_context(cp[b]),.begin_version(vp[b]),.participant_mask(mp[b]),
   .begin_ready(ready),.init_v(bank_init_v[b]),.init_ack(bank_init_ack[b]),.init_context(actual_context),.init_version(bank_init_version[b*32+:32]),.init_participants(bank_init_participants[b*48+:48]),
   .issue_v({48{issue}}),.issue_ready(issue_ready[b*48+:48]),.issue_seq(1920'd0),.issue_context({48{held_context}}),.issue_version({48{held_version}}),
   .retire_v({48{retire}}),.retire_ready(retire_ready[b*48+:48]),.retire_seq(1920'd0),.retire_context({48{held_context}}),.retire_version({48{held_version}}),
   .seal_v({48{seal}}),.seal_context({48{held_context}}),.seal_version({48{held_version}}),.drained(bank_drained[b]),.fault(bank_fault[b])
  );
 end
 task step;begin @(posedge clk);#1;@(negedge clk);end endtask
 task reset;begin rst_n=0;offer_v=0;acquire_ready=0;accept_v=0;issue=0;retire=0;seal=0;source_output_drained=0;release_ready=0;transport_flush_ack=0;offer_participants={768{1'b1}};offer_ib=379'h123;acquire_version=32'hc1234567;step;rst_n=1;step;if(!flush_req)$fatal(1,"reset initialization lost flush fence");transport_flush_ack=1;step;transport_flush_ack=0;end endtask
 task acquire;begin offer_v=1;step;offer_v=0;acquire_ready=1;step;acquire_ready=0;end endtask
 integer cycles,i;
 initial begin
 reset;acquire;cycles=0;offer_participants=0;offer_ib=379'h456;acquire_version=0;
 while(!dispatch_v)begin
  if(fault||(|bank_fault))$fatal(1,"actual bank initialization fault");
  if(cycles>40)$fatal(1,"actual bank initialization stuck");
  step;cycles=cycles+1;
 end
 if(cycles<18)$fatal(1,"field dispatch before delayed final actual receipt");
 if(issue_ready!={768{1'b1}})$fatal(1,"field bank state not actually initialized");
 accept_v=1;for(i=0;i<768;i=i+1)begin accept_tile=i;step;end accept_v=0;step;
 issue=1;step;issue=0;if(retire_ready!={768{1'b1}})$fatal(1,"field query counters not issued");
 source_output_drained=1;#1;if(release_v)$fatal(1,"field released unretired component queries");
 retire=1;step;retire=0;#1;if(release_v)$fatal(1,"field released unsealed component banks");
 seal=1;step;seal=0;#1;if(!release_v||fault||(|bank_fault))$fatal(1,"matching component ledger drain failed");release_ready=1;step;release_ready=0;
 reset;acquire;repeat(6)step;rst_n=0;step;rst_n=1;step;if(dispatch_v||!flush_req||(|bank_init_v))$fatal(1,"partial initialization reset published dispatch");
 corrupt_receipt=1;reset;acquire;repeat(30)step;if(!fault||dispatch_v)$fatal(1,"delayed corrupt bank receipt escaped");
 $display("PASS actual16x48 initialization composition delayedBEGIN receipts,768componentqueries,resetpartial/stalebank fence; no production seals");$finish;
 end
endmodule
