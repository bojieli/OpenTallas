`timescale 1ns/1ps
module tb_xload_cadence;
`ifdef XW_FLOW
 localparam integer FLOW=1;
`else
 localparam integer FLOW=0;
`endif
 integer sink_period=1;
 wire sink_ready=sink_period<=1 || cyc%sink_period==0;
 wire last_beat;
 reg clk=0; always #1 clk=~clk;
 reg rst_n=0,x_v=0; reg[39:0] base=0; reg[20:0] n=0; reg[3:0] p=0; reg[31:0] stride=0; reg[1:0] fmt=0;
 wire ready,done,fault,en,req; wire[6:0] addr,grp; wire[2047:0] data;
 wire[1351:0] vmq; wire[1095:0] vmr; wire[511:0] q; wire[31:0] cr; wire[8223:0] rsp;
 ot_hgi_sm_xload #(.XW_FLOW(FLOW),.BD(1),.BW8(1),.PMAX(8),.W8LQ(10)) u (.clk(clk),.rst_n(rst_n),.x_v(x_v),.x_rdy(ready),
 .x_base(base),.x_n(n),.x_p(p),.x_stride(stride),.x_space(2'd1),.x_fmt(fmt),.x_xb(7'd0),
 .xw_ready(sink_ready),.xw_last(last_beat),.x_done(done),.x_fault(fault),.xw_en(en),.xw_addr(addr),.xw_grp(grp),.xw_data(data),
 .vmq(vmq),.vmr(vmr),.rg_req(req),.rg_gnt(1'b1),.wrq(q),.wrq_cr(cr),.wrr(rsp));
 function automatic [255:0] sector(input integer s);
  for(integer t=0;t<8;t=t+1) sector[32*t+:32]=32'h3f800000+32'(((s*8+t)%127)<<16);
 endfunction
 genvar b;
 generate for(b=0;b<8;b=b+1) begin:g_l
  reg[256:0] pipe[0:7];
  always @(posedge clk) begin
   pipe[0]<=rst_n&&q[b*16+15]?{1'b1,sector(q[b*16+:15])}:257'd0;
   for(integer z=1;z<8;z=z+1) pipe[z]<=pipe[z-1];
  end
  assign rsp[b*257+:257]=pipe[7]; assign cr[b]=pipe[7][256];
 end endgenerate
 assign rsp[8223:2056]=0; assign cr[31:8]=0;
 generate for(b=0;b<4;b=b+1) begin:g_p
  reg[273:0] pipe[0:7];
  always @(posedge clk) begin
   pipe[0]<=rst_n&&vmq[b*338+337]?{1'b1,vmq[b*338+:16],1'b0,sector(vmq[b*338+309+:27])}:274'd0;
   for(integer z=1;z<8;z=z+1) pipe[z]<=pipe[z-1];
  end
  assign vmr[b*274+:274]=pipe[7];
 end endgenerate
 reg held=0;reg[2062:0] held_payload;
 always @(posedge clk)begin
  if(FLOW!=0 && held && (!en || {addr,grp,data,last_beat}!==held_payload))$fatal(1,"held producer changed before acceptance");
  held<=FLOW!=0 && en && !sink_ready;
  if(en && !sink_ready)held_payload<={addr,grp,data,last_beat};
 end
 integer cyc=0,count=0,run=0,maxrun=0,first=-1,last=-1,prev=-2,fd,id=0,startcyc=0;
 always @(posedge clk) begin
  cyc<=cyc+1;
  if(en && (FLOW==0 || sink_ready)) begin
   count=count+1; if(first<0)first=cyc;
   run=cyc==prev+1?run+1:1; if(run>maxrun)maxrun=run;
   prev=cyc;last=cyc;
   $fdisplay(fd,"%0d %0d %0d %0d %0512h",id,cyc,addr,grp,data);
  end
 end
 task automatic command(input integer k,input integer slots,input integer f);
  integer expected,timeout,completed;
  begin
   while(!ready) @(negedge clk);
   n=k;p=slots;fmt=f;stride=k;count=0;run=0;maxrun=0;first=-1;last=-1;prev=-2;
   startcyc=cyc; @(negedge clk);x_v=1;@(negedge clk);x_v=0;
   timeout=0;while(!done&&timeout<200000)begin @(negedge clk);timeout=timeout+1;end
   completed=done;repeat(2)@(negedge clk); // x_done and final xw pins launch together; sample the final sink edge
   expected=((k+(f==0?511:f==1?1023:2047))/(f==0?512:f==1?1024:2048))*8*((slots*3152+2047)/2048);
   if(!completed||fault||count!=expected)$fatal(1,"cadence failed k%0d p%0d f%0d count%0d expected%0d fault%0d",k,slots,f,count,expected,fault);
   $display("CADENCE id=%0d K=%0d P=%0d fmt=%0d beats=%0d max_contiguous=%0d first=%0d last=%0d service=%0d",id,k,slots,f,count,maxrun,first-startcyc,last-startcyc,cyc-startcyc);
   id=id+1;repeat(8)@(negedge clk);
  end
 endtask
 initial begin
  if(!$value$plusargs("SINK_PERIOD=%d",sink_period))sink_period=1;
  fd=$fopen("beats.txt","w");repeat(5)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
  command(5120,1,0);command(5120,1,1);command(5120,1,2);
  command(7168,4,0);command(7168,4,1);command(7168,4,2);
  command(8192,8,0);command(16384,8,1);command(32768,8,2);
  $fclose(fd);$display("XLOAD_CADENCE PASS records=9");$finish;
 end
endmodule
