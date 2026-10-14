`timescale 1ps/1fs
// Actual production q10 source39f276214. STORE/FENCE descriptors use its real
// record, KV issuer, hold SRAM and HBM ports. The VM read group is external:
// all payloads come through the real owned bridge and actual B2 SECDED SRAM.
module ot_native_dma_core_stimulus #(parameter integer MUT=0)(
 input wire clk,rst_n,go,input wire [3:0] bridge_released,
 output wire [512:0] legacy_q,input wire [8256:0] legacy_r,
 output reg done=0,output integer checked_words=0,request_count=0,peak_pending=0
);
 reg [703:0] rec=0;wire [3:0] ret;
 wire kv,krwe,krrdy;wire [36:0] ka;wire [255:0] kwd;wire [31:0] kstr;wire [15:0] kt;
 wire rv,rwe,rrrdy;wire [36:0] ra;wire [3:0] rlen;wire [15:0] rtag;wire [255:0] rwd;wire [31:0] rstr;
 reg rrvalid=0;reg [15:0] rrtag=0;wire [337:0] vmq;wire [279:0] wl;wire [4:0] wbank;
 ot_hgi_b2_dma_q #(.HARD_CLOCKS(1),.MUT_B2(MUT==21?1:0)) producer(
  .clk(clk),.leaf_clk({10{clk}}),.rst_n(rst_n),.qid(2'b0),.dma_rec(rec),.dma_ret(ret),
  .k_req_v(kv),.k_req_rdy(1'b1),.k_req_we(krwe),.k_req_addr(ka),.k_req_wdata(kwd),.k_req_wstrb(kstr),.k_req_tag(kt),
  .k_rsp_v(1'b0),.k_rsp_rdy(krrdy),.k_rsp_we(1'b0),.k_rsp_data(256'b0),
  .r_req_v(rv),.r_req_rdy(1'b1),.r_req_addr(ra),.r_req_len(rlen),.r_req_tag(rtag),.r_req_we(rwe),.r_req_wdata(rwd),.r_req_wstrb(rstr),
  .r_rsp_v(rrvalid),.r_rsp_we(1'b1),.r_rsp_rdy(rrrdy),.r_rsp_tag(rrtag),.r_rsp_last(1'b1),.r_rsp_data(256'b0),
  .vmq(vmq),.vmr(274'b0),.vr2q(legacy_q),.vr2r(legacy_r),.wl(wl),.wl_bank(wbank),.wl_done(1'b0));
 integer cyc=0,nret=0,qn=0,qh=0;reg [15:0] tags[0:127];integer dates[0:127];
 reg [31:0] expected[int];bit written[int];integer pend[0:31],peak[0:31];
 always @(posedge clk)begin
  cyc<=cyc+1;
  if(!rst_n)begin qn=0;qh=0;rrvalid<=0;nret=0;for(integer l=0;l<32;l++)begin pend[l]=0;peak[l]=0;end end
  else begin
   if(ret[2])$fatal(1,"THREEOWNER actual q10 DMA fault");
   if(ret[1])nret++;
   if(kv||vmq[337]||wl[279])$fatal(1,"THREEOWNER aligned STORE escaped native read group: k%0d packet%0d wide%0d",kv,vmq[337],wl[279]);
   if(rrvalid&&rrrdy)begin qh++;qn--;end
   if(rv)begin
    if(!rwe||rlen!=1||ra[36:35]!=0||ra[4:0]!=0||qn>=128)$fatal(1,"THREEOWNER actual q10 unexpected burst request");
    for(integer w=0;w<8;w++)begin
     integer addr;addr=int'(ra)+w*4;
     if(rstr[w*4+:4]!=4'hf||!expected.exists(addr)||written.exists(addr)||rwd[w*32+:32]!==expected[addr])
      $fatal(1,"THREEOWNER actual q10 STORE golden mismatch HBMaddr%h data%h expected%h",addr,rwd[w*32+:32],expected[addr]);
     written[addr]=1;checked_words++;
    end
    tags[(qh+qn)%128]=rtag;dates[(qh+qn)%128]=cyc+7;qn++;
   end
   if(!rrvalid||rrrdy)begin
    rrvalid<=qn>0&&dates[qh%128]<=cyc;
    if(qn>0&&dates[qh%128]<=cyc)rrtag<=tags[qh%128];
   end
   for(integer l=0;l<32;l++)begin
    if(legacy_q[l*16+15])begin request_count++;pend[l]++;end
    if(legacy_r[l*257+256])pend[l]--;
    if(pend[l]<0||pend[l]>32)$fatal(1,"THREEOWNER source39 causal pending outside GLQ32 lane%0d count%0d",l,pend[l]);
    if(pend[l]>peak[l])peak[l]=pend[l];if(pend[l]>peak_pending)peak_pending=pend[l];
   end
  end
 end
 task automatic send_record(input [703:0] payload);
  integer prior,start;begin
   prior=nret;start=cyc;@(negedge clk);rec=payload;
   while(!ret[0])begin @(negedge clk);if(cyc-start>20000)$fatal(1,"THREEOWNER actual q10 record admission timeout");end
   @(negedge clk);rec[0]=0;
   while(nret==prior)begin @(negedge clk);if(cyc-start>40000)$fatal(1,"THREEOWNER actual q10 record retirement timeout");end
  end
 endtask
 task automatic store(input integer abase,nn,mm,astride,hbase);
  reg [127:0] h;reg [255:0] a,o;integer start;
  begin
   for(integer r=0;r<mm;r++)for(integer w=0;w<nn;w++)expected[hbase+r*nn*4+w*4]=32'hA5A50000+abase+r*astride+w;
   h=0;h[127:124]=8;h[123:118]=1;h[93]=1;h[97]=1;
   a=0;a[1:0]=1;a[47:8]=40'(abase);a[67:48]=20'(nn);a[87:68]=20'(mm);a[119:88]=32'(astride);
   o=0;o[47:8]=40'(hbase);o[67:48]=20'(nn);o[87:68]=20'(mm);o[119:88]=32'(nn*4);
   start=cyc;send_record({21'd1,21'(nn),21'(nn),o,a,h,1'b1});
   h=0;h[127:124]=8;h[123:118]=2;send_record({21'd1,42'b0,512'b0,h,1'b1});
   if(qn!=0||rrvalid)$fatal(1,"THREEOWNER FENCE retired before actual modeled HBM write responses");
   for(integer r=0;r<mm;r++)for(integer w=0;w<nn;w++)if(!written.exists(hbase+r*nn*4+w*4))$fatal(1,"THREEOWNER actual q10 FENCE missing golden word");
   while(bridge_released!=4'hf)begin @(negedge clk);if(cyc-start>40000)$fatal(1,"THREEOWNER actual read leases not ACKed");end
   $display("THREEOWNER_DMA_STORE PASS base%0d n%0d rows%0d stride%0d checked%0d source39_peak_pending%0d",abase,nn,mm,astride,checked_words,peak_pending);$fflush();
  end
 endtask
 initial begin
  wait(rst_n&&go);repeat(3)@(negedge clk);
  store(0,64,4,65536,4096);       // Same legacy lanes travel through all four SID destinations.
  store(65528,128,1,128,8192);   // Slice boundary, changing legacy bank/owner and native bank.
  store(32768,8,64,256,16384);   //64 requests on one legacy lane, actual source32 credits.
  store(131008,128,1,128,24576); // Different slice boundary and legacy owners.
  if(checked_words!=1024||request_count!=128||nret!=8)$fatal(1,"THREEOWNER actual q10 shape changed words%0d requests%0d records%0d",checked_words,request_count,nret);
  done=1;$display("THREEOWNER_DMA_CORE PASS source39f276214 STORE4 FENCE4 native_requests128 words1024 peak_pending%0d",peak_pending);$fflush();
 end
endmodule
