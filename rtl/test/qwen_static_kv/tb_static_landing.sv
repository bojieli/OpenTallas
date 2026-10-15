`timescale 1ns/1ps
// Production port shape: 32 simultaneous K row ports, two active V requests
// among four faces, 128 physical SRAM quarters, ctx8192. Stimuli are at the
// declared corrected-PC-return boundary. This is a landing component proof,
// not the missing controller/PHY/full-attention composition qualification.
module tb_static_landing;
 reg ck=0;always #0.416667 ck=~ck;
 reg rst=0,arm=0;
 reg [31:0] put=0,av=0,rq=0;
 reg [31:0] vv=0;
 reg [9:0] sec[0:31];reg [13:0] tt[0:31];
 wire [31:0] ov,ff;wire [1023:0] od[0:31];wire [13:0] ot[0:31];wire [31:0] outv;
 reg [1023:0] wd[0:31];
 reg [3:0] ap[0:31];reg [39:0] as[0:31];
 integer faultmode=0,errors=0,seen=0,cycles=0,tx=0;
 function automatic [13:0] kt(input integer i,s,e);
  kt=14'(((i>>3)&15)*512+s*128+((i>>7)&1)*64+(i&7)*8+e);
 endfunction
 function automatic [9:0] js(input integer t,v);
  js={1'(v),1'b0,1'((t>>6)&1),4'((t>>9)&15),3'((t>>3)&7)};
 endfunction
 function automatic [13:0] vt(input integer o,s,e);
  vt=14'(((o>>4)&15)*512+s*128+((o>>3)&1)*64+(o&7)*8+e);
 endfunction
 function automatic [1023:0] pattern(input integer t,v);
  for(integer j=0;j<32;j=j+1)pattern[32*j+:32]=32'h19e30000^(32'(t)*32'h9e3779b9)^(32'(v)<<31)^32'(j*71);
 endfunction
 genvar g;
 generate for(g=0;g<32;g=g+1)begin:groups
  wire [15:0] oe;wire [5:0] ol;wire rv;
  qkd_static_kv_landing_grp #(.STACK(g/8),.GROUP(g%8))dut(
   .ck(ck),.ck_pc({4{ck}}),.rst_n(rst),.arm(arm),.epoch(16'd7),.layer(6'd3),
   .expected_put({4{put[g]}}),.expected_sector({4{sec[g]}}),.actual_valid(ap[g]),.actual_sector(as[g]),
   .actual_epoch({4{16'd7}}),.actual_layer({4{6'd3}}),.actual_data(wd[g]),
   .req_valid(rq[g]),.req_t(tt[g]),.req_v(vv[g]),.req_epoch(16'd7),.req_layer(6'd3),
   .rsp_valid(ov[g]),.rsp_data(od[g]),.rsp_t(ot[g]),.rsp_v(outv[g]),.rsp_epoch(oe),.rsp_layer(ol),.fault(ff[g]));
 end endgenerate
 reg [31:0] expv[0:5],expkind[0:5];
 reg [13:0] expt[0:5][0:31];reg [1023:0] expd[0:5][0:31];
 always @(posedge ck)begin
  cycles++;
  if(!rst)for(integer d=0;d<6;d=d+1)expv[d]<=0;
  else begin
   expv[0]<=rq;expkind[0]<=vv;
   for(integer n=0;n<32;n=n+1)begin expt[0][n]<=tt[n];expd[0][n]<=pattern(tt[n],vv[n]);end
   for(integer d=1;d<6;d=d+1)begin
    expv[d]<=expv[d-1];expkind[d]<=expkind[d-1];
    for(integer n=0;n<32;n=n+1)begin expt[d][n]<=expt[d-1][n];expd[d][n]<=expd[d-1][n];end
   end
  end
  #0.001;
  if(rst)begin
   if(ov!==expv[5])begin if(errors<8)$display("BAD valid c%0d actual%h expected%h",cycles,ov,expv[5]);errors++;end
   for(integer n=0;n<32;n=n+1)if(ov[n])begin
    seen++;
    if(od[n]!==expd[5][n]||ot[n]!==expt[5][n]||outv[n]!==expkind[5][n])begin
     if(errors<8)$display("BAD row c%0d group%0d t%0d expected%0d",cycles,n,ot[n],expt[5][n]);errors++;
    end
   end
  end
 end
 task automatic idle;
  put=0;rq=0;vv=0;
  for(integer g=0;g<32;g=g+1)begin ap[g]=0;as[g]=0;end
 endtask
 task automatic loadrow(input integer g,o,v);
  automatic integer t=v?vt(o,g/8,g%8):kt(o,g/8,g%8);
  reg [1023:0] oldword;
  put[g]=1;sec[g]=js(t,v);ap[g]=4'hf;as[g]={4{sec[g]}};wd[g]=pattern(t,v);
  if(g==0&&o==17)begin
   if(faultmode==1)ap[g][0]=0;
   if(faultmode==2)as[g][0]=~as[g][0];
   if(faultmode==3)begin ap[g][0]=0;end
   if(faultmode==4)wd[g][0]=~wd[g][0];
  end
  if(g==0&&o==18&&faultmode==3)begin as[g][9:0]=js(v?vt(17,0,0):kt(17,0,0),v);oldword=pattern(v?vt(17,0,0):kt(17,0,0),v);wd[g][255:0]=oldword[255:0];end
 endtask
 initial begin
  void'($value$plusargs("faultmode=%d",faultmode));
  for(integer n=0;n<32;n=n+1)begin sec[n]=0;tt[n]=0;wd[n]=0;ap[n]=0;as[n]=0;end
  repeat(8)@(negedge ck);rst=1;repeat(8)@(negedge ck);arm=1;@(negedge ck);arm=0;repeat(4)@(negedge ck);
  for(integer i=0;i<64;i=i+1)begin idle();for(integer g=0;g<32;g=g+1)loadrow(g,i,0);@(negedge ck);end
  for(integer i=0;i<256;i=i+1)begin
   idle();for(integer g=0;g<32;g=g+1)begin rq[g]=1;tt[g]=kt(i,g/8,g%8);if(i+64<256)loadrow(g,i+64,0);end
   @(negedge ck);
  end
  idle();repeat(8)@(negedge ck);
  for(integer i=0;i<64;i=i+1)begin idle();for(integer g=0;g<32;g=g+1)loadrow(g,i,1);@(negedge ck);end
  for(integer n=0;n<32;n=n+1)for(integer c=0;c<128;c=c+1)begin
   idle();
   for(integer p=0;p<2;p=p+1)begin
    automatic integer t=n*256+p*128+c;
    automatic integer g=((t>>7)&3)*8+(t&7);
    automatic integer o=(((t>>9)&15)<<4)|(((t>>6)&1)<<3)|((t>>3)&7);
    rq[g]=1;tt[g]=14'(t);vv[g]=1;if(o+64<256)loadrow(g,o+64,1);
   end
   @(negedge ck);
  end
  idle();repeat(10)@(negedge ck);
  if((|ff)||errors||seen!=16384)begin $display("FAIL staticlanding ctx8192 rows%0d errors%0d fault%h mode%0d",seen,errors,ff,faultmode);$fatal(1);end
  $display("PASS staticlanding ctx8192 groups32 PCs128 rows%0d sectors65536 fixed_latency5 cycles%0d",seen,cycles);$finish;
 end
endmodule
