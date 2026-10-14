`timescale 1ps/1ps
`default_nettype none
// Fault injection at real one-hot FF state. A paused finite consumer holds
// issued beats, then reset flushes that pending work through the real relay.
module tb_hgi_qdq_core_fin2_corruption;
 reg cf=0,cc=0,rst_n=0;reg[682:0]rec=0;
 initial begin #61;forever begin cf=1;#416;cf=0;#417;end end
 initial begin #487;forever begin cc=1;#416;cc=0;#417;end end
 wire s1v,s3v,nf;wire[189:0]s3;
 ot_hgi_qdq_fr #(.SPANPIPE(1)) front(.clk(cf),.rst_n(rst_n),.rec(rec),.s1_v(s1v),.s3_v(s3v),.s3(s3),.nfault(nf));
 wire[2:0]ret;wire[127:0]wrq;wire rg,ar,bv,act;wire[39:0]bp;
 integer pending_beats=0,pending_requests=0,cycles=0,tests=0;
 wire aidle=pending_beats==0, widle=pending_beats==0;
 ot_hgi_qdq_core_fin2 #(.FIN_BYPASS(2),.SPANPIPE(1)) dut(
 .clk(cc),.rst_n(rst_n),.i_s1_v(s1v),.i_s3_v(s3v),.i_s3(s3),.i_nfault(nf),
 .ret(ret),.wrq(wrq),.wrq_cr(8'd0),.rg_req(rg),.rg_gnt(rg),.asm_rst_n(ar),.bp_v(bv),.bp(bp),
 .i_pop(8'd0),.i_fire(1'b0),.i_abad(1'b0),.i_aidle(aidle),.o_act(act),.i_fin(1'b0),.i_wbad(1'b0),.i_widle(widle));
 always @(negedge cc)begin
   cycles=cycles+1;
   if(!ar)begin pending_beats=0;pending_requests=0;end
   else begin
     if(bv)pending_beats=pending_beats+1;
     for(integer l=0;l<8;l=l+1)if(wrq[l*16+15])pending_requests=pending_requests+1;
     if(pending_beats>32 || pending_requests>80)$fatal(1,"CORRUPTION_SERVICE_CAPACITY");
   end
 end
 task automatic reset_real;
   begin @(negedge cf);rec=0;rst_n=0;repeat(16)@(negedge cf);rst_n=1;repeat(16)@(negedge cf);
     if(dut.head_oh!==16'h0001 || dut.finish_oh!==32'h00000001 || dut.bad || dut.q_v!=0 || pending_beats!=0 || pending_requests!=0)
       $fatal(1,"CORRUPTION_RESET_STALE");
   end
 endtask
 task automatic live_record;
   reg[255:0]a,o;reg[127:0]h;integer start;
   begin
     @(negedge cf);while(!ret[0])@(negedge cf);
     a=0;a[1:0]=1;a[47:8]=8192;a[67:48]=128;a[87:68]=3;a[119:88]=128;
     o=a;o[47:8]=12288;h=0;h[127:124]=4;h[123:118]=4;h[99:93]=7'b0010001;h[71:64]=8'h42;
     rec={21'd128,21'd128,o,a,h,1'b1};@(negedge cf);rec=0;
     start=cycles;
     while(!bv)begin @(negedge cc);#1;if(cycles-start>256)$fatal(1,"CORRUPTION_NO_REAL_ISSUE");end
     // At least one public issued beat exists and another beat is eligible.
     #1;if(dut.q_v==0 || !dut.r_act || !dut.r_issue || pending_beats==0 || pending_requests==0)
       $fatal(1,"CORRUPTION_INJECTION_NOT_LIVE");
   end
 endtask
 task automatic contain(input integer kind);
   begin
     live_record();
     if(kind==0)force dut.head_oh=16'h0003;
     else force dut.finish_oh=32'h00000003;
     #1;
     if(!dut.encoding_bad || dut.r_issue || dut.n_load)$fatal(1,"CORRUPTION_IMMEDIATE_CONTAINMENT kind=%0d",kind);
     if(kind==0 && $countones(dut.head_oh)!=2)$fatal(1,"CORRUPTION_HEAD_NOT_FORCED");
     if(kind==1 && $countones(dut.finish_oh)!=2)$fatal(1,"CORRUPTION_FINISH_NOT_FORCED");
     repeat(8)begin
       @(negedge cc);#1;
       if(bv || !ret[2] || ret[1] || !dut.bad || dut.r_issue || dut.n_load)$fatal(1,"CORRUPTION_REGISTERED_CONTAINMENT kind=%0d ret=%b",kind,ret);
       for(integer l=0;l<8;l=l+1)if(wrq[l*16+15])$fatal(1,"CORRUPTION_NEW_REQUEST kind=%0d",kind);
     end
     if(kind==0)force dut.head_oh=16'h0001;
     else force dut.finish_oh=32'h00000001;
     #1;if(dut.encoding_bad || !dut.bad || dut.r_issue || dut.n_load)$fatal(1,"CORRUPTION_NOT_LATCHED kind=%0d",kind);
     @(negedge cc);#1;
     if(bv || dut.r_issue || dut.n_load)$fatal(1,"CORRUPTION_RESTARTED_WITHOUT_RESET kind=%0d",kind);
     if(kind==0)release dut.head_oh;else release dut.finish_oh;
     tests=tests+1;
     $display("PASS CORE_FIN2_CORRUPTION_CASE kind=%0d pending_beats=%0d pending_requests=%0d",kind,pending_beats,pending_requests);
   end
 endtask
 initial begin
   reset_real();contain(0);reset_real();live_record();
   reset_real();contain(1);reset_real();live_record();
   if(tests!=2)$fatal(1,"CORRUPTION_COVERAGE");
   $display("PASS CORE_FIN2_CORRUPTION tests=%0d recovery_issues=2",tests);$finish;
 end
endmodule
`default_nettype wire
