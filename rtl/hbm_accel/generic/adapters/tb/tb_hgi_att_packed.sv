`timescale 1ns/1ps
// Actual ATT engine/reader/row assembly; sparse logical full-address packet peer.
module tb_hgi_att_packed;
`include "sizes.svh"
reg clk=0; always #1 clk=~clk;
reg rst_n=0, rec_v=0; reg[1215:0] cur; wire ready,done,fault,halted;
wire[337:0] mq,sq; reg[273:0] mr=0,sr=0; reg srdy=0;
wire hv; wire[34:0] ha; wire[7:0] ht;
ot_hgi_att_unit #(.H(1),.D(64),.TD(64),.NL(2),.BLK(64),.PACKED_ROWS(1),.SELECTED_VM(1),.SELECTED_C_ONLY(0)) u
(.clk(clk),.rst_n(rst_n),.rec_v(rec_v),.rec_rdy(ready),.rec_hdr(cur[127:0]),.rec_a(cur[383:128]),
 .rec_b(cur[639:384]),.rec_c(cur[895:640]),.rec_o(cur[1151:896]),.rec_n_b(cur[1172:1152]),
 .rec_n_c(cur[1193:1173]),.rec_pos1(cur[1214:1194]),.rec_done(done),.rec_fault(fault),.halted(halted),
 .vmq(mq),.vmr(mr),.hq_v(hv),.hq_rdy(1'b0),.hq_addr(ha),.hq_tag(ht),.hr_v(1'b0),.hr_tag(8'd0),.hr_data(256'd0),
 .selected_vmq(sq),.selected_vmq_rdy(srdy),.selected_vmr(sr));
reg[63:0] initm[0:NM-1],expm[0:NE-1];reg[1215:0] recm[0:1];
reg[31:0] mem[longint]; reg[337:0] mainq[$],selq[$]; reg[337:0] req;
reg[255:0] data; integer j,b,word,cycles=0,nd=0,errors=0; string dir;
always @(posedge clk) begin
 cycles<=cycles+1;mr<=0;sr<=0;srdy<=cycles%4!=0;
 if(rst_n) begin
  if(mq[337]) mainq.push_back(mq);
  if(sq[337]&&srdy) selq.push_back(sq);
  if(mainq.size()>0 && cycles%3==0) begin
   req=mainq.pop_front();word=req[335:304]/4;data=0;
   for(b=0;b<8;b=b+1) begin
    if(req[336]) begin
     for(j=0;j<4;j=j+1) if(req[16+4*b+j]) mem[word+b][8*j+:8]=req[48+32*b+8*j+:8];
    end
    data[32*b+:32]=mem.exists(word+b)?mem[word+b]:0;
   end
   mr<={1'b1,req[15:0],1'b0,data};
  end
  if(selq.size()>0 && cycles%3==1) begin
   req=selq.pop_front();word=req[335:304]/4;data=0;
   for(b=0;b<8;b=b+1) begin
    if(!mem.exists(word+b)) $fatal(1,"cold selected word %0d",word+b);
    data[32*b+:32]=mem[word+b];
   end
   sr<={1'b1,req[15:0],1'b0,data};
  end
  if(hv) $fatal(1,"unexpected HBM request");
  if(fault) $fatal(1,"ATT fault state %0d",u.st);
  if(done) nd<=nd+1;
 end
end
integer r,start;
initial begin
 if(!$value$plusargs("DIR=%s",dir)) dir=".";
 $readmemh({dir,"/mem.mem"},initm);$readmemh({dir,"/exp.mem"},expm);$readmemh({dir,"/rec.mem"},recm);
 for(r=0;r<NM;r=r+1) mem[initm[r][63:32]]=initm[r][31:0];
 repeat(3) @(negedge clk);rst_n=1;
 for(r=0;r<2;r=r+1) begin
  @(negedge clk);cur=recm[r];rec_v=1;while(!ready) @(negedge clk);
  @(negedge clk);rec_v=0;start=cycles;
  while(nd<=r) @(negedge clk);
  $display("packed record %0d cycles %0d",r,cycles-start);
 end
 for(r=0;r<NE;r=r+1) if(mem[expm[r][63:32]]!==expm[r][31:0]) begin
  if(errors<8) $display("wrong [%0d] got%h expected%h",expm[r][63:32],mem[expm[r][63:32]],expm[r][31:0]);
  errors=errors+1;
 end
 if(errors) $fatal(1,"PACKED ATT errors%0d",errors);
 $display("PACKED ATT PASS H1 D64 T130 three jobs %0d words",NE);$finish;
end
endmodule
