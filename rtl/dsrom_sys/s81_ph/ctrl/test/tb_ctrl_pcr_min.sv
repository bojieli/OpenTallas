`timescale 1ps/1ps
module tb_ctrl_pcr_min;
 reg cks=0,ckh=0,rst=0;
 always #416 cks=~cks;
 always #512 ckh=~ckh;
 reg [340:0] rq=0;
 reg k_rdy=0,k_wr_done=0,kr_v=0;
 reg [16:0] kr_tag=0;
 reg [3:0] kr_beat=0;
 reg [255:0] kr_data=0;
 integer sent=0,credits=8,schecks=0,hchecks=0,nrefuse=0,naccept=0,nrd=0,nwd=0;
 integer hs=0,ss=0;
 wire [1:0] d_co,r_co;
 wire [0:0] d_rk,r_rk;
 wire [0:0] d_rv,r_rv;
 wire [255:0] d_r_data,r_r_data;
 wire [16:0] d_r_tag,r_r_tag;
 wire [3:0] d_r_beat,r_r_beat;
 wire [0:0] d_wd,r_wd;
 wire [0:0] d_s_ovf,r_s_ovf;
 wire [0:0] d_k_v,r_k_v;
 wire [29:0] d_k_addr,r_k_addr;
 wire [3:0] d_k_len,r_k_len;
 wire [16:0] d_k_tag,r_k_tag;
 wire [0:0] d_k_we,r_k_we;
 wire [255:0] d_k_wdata,r_k_wdata;
 wire [31:0] d_k_wstrb,r_k_wstrb;
 wire [0:0] d_kr_rdy,r_kr_rdy;
 ot_s81ph_ctrl_pcr dut(.cks(cks),.ckh(ckh),.rst(rst),.ci(2'b01),.rq(rq),.k_rdy(k_rdy),.k_wr_done(k_wr_done),.kr_v(kr_v),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data),.co(d_co),.rk(d_rk),.rv(d_rv),.r_data(d_r_data),.r_tag(d_r_tag),.r_beat(d_r_beat),.wd(d_wd),.s_ovf(d_s_ovf),.k_v(d_k_v),.k_addr(d_k_addr),.k_len(d_k_len),.k_tag(d_k_tag),.k_we(d_k_we),.k_wdata(d_k_wdata),.k_wstrb(d_k_wstrb),.kr_rdy(d_kr_rdy));
 ot_s81ph_ctrl_pcr_ref refp(.cks(cks),.ckh(ckh),.rst(rst),.ci(2'b01),.rq(rq),.k_rdy(k_rdy),.k_wr_done(k_wr_done),.kr_v(kr_v),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data),.co(r_co),.rk(r_rk),.rv(r_rv),.r_data(r_r_data),.r_tag(r_r_tag),.r_beat(r_r_beat),.wd(r_wd),.s_ovf(r_s_ovf),.k_v(r_k_v),.k_addr(r_k_addr),.k_len(r_k_len),.k_tag(r_k_tag),.k_we(r_k_we),.k_wdata(r_k_wdata),.k_wstrb(r_k_wstrb),.kr_rdy(r_kr_rdy));

 task check(input bit good,input string why);
  if(!good) begin $display("CTRL_PCR_MIN FAIL %s sent%0d accepts%0d refuses%0d",why,sent,naccept,nrefuse);$fatal(1);end
 endtask
 always @(negedge cks) begin
  if(!rst) begin rq=0;credits=8;sent=0;end
  else begin
   if(r_rk) credits=credits+1;
   rq=0;
   if(r_co[0] && credits>0 && sent<96 && ss%3!=0) begin
    rq={256'(sent*997+17),32'hfdcba987,17'(sent),4'd1,30'(sent*4),sent[0],1'b1};
    sent=sent+1;credits=credits-1;
   end
  end
  ss=ss+1;
 end
 always @(negedge ckh) begin
  hs=hs+1;
  k_rdy=(hs%9>=4);
  kr_v=rst && hs%7==2;
  kr_tag=17'(hs);kr_beat=hs[3:0];kr_data=256'(hs*2131);
  k_wr_done=rst && hs%11==4;
 end
 always @(posedge cks) begin
  #1;
  if(rst && dut.srst_n && refp.srst_n) begin
   schecks=schecks+1;
   check({d_co,d_rk,d_rv,d_wd,d_s_ovf}==={r_co,r_rk,r_rv,r_wd,r_s_ovf},"stream valid/credit/write-done/status");
   if(r_rv) begin nrd=nrd+1;check({d_r_data,d_r_tag,d_r_beat}==={r_r_data,r_r_tag,r_r_beat},"response payload");end
   if(r_wd)nwd=nwd+1;
  end
 end
 always @(posedge ckh) begin
  if(rst && r_k_v)begin if(k_rdy)naccept=naccept+1;else nrefuse=nrefuse+1;end
  #1;
  if(rst && dut.hrst_n && refp.hrst_n)begin
   hchecks=hchecks+1;
   check({d_k_v,d_kr_rdy}==={r_k_v,r_kr_rdy},"PHY refusal re-presentation");
   if(r_k_v)check({d_k_addr,d_k_len,d_k_tag,d_k_we,d_k_wdata,d_k_wstrb}==={r_k_addr,r_k_len,r_k_tag,r_k_we,r_k_wdata,r_k_wstrb},"PHY request payload");
  end
 end
 initial begin
  repeat(8)@(negedge cks);rst=1;
  repeat(1400)@(negedge cks);
  check(sent==96 && naccept==96 && nrefuse>10 && nrd>50 && nwd>20,"coverage first phase");
  rst=0;repeat(8)@(negedge cks);rst=1;
  repeat(1400)@(negedge cks);
  check(sent==96 && naccept==192 && nrefuse>20 && nrd>100 && nwd>40,"coverage reset phase");
  $display("CTRL_PCR_MIN PASS schecks%0d hchecks%0d accepts%0d refuses%0d reads%0d wd%0d",schecks,hchecks,naccept,nrefuse,nrd,nwd);$finish;
 end
endmodule
