`timescale 1ns/1ps
// Behavioural equivalence of the systolic hardened partition (ot_s81_hcx_projection_sys) against the flat leaf
// (ot_s81_hcx_projection_leaf): both instantiated side by side on the SAME stimulus and the same resident ROM image
// (OT_ROM_DIR, INSTANCE names hcx_r0_b<k>_l<m>_p<pg>).  Blocks 0/1: the released x vectors (x0/x1.mem) against the
// golden (expected.mem); blocks 2..NRAND+1: random finite BF16 x, flat vs partition.  Every block must give the
// identical o_d, fault 0 in both, and each leaf a fixed (data-independent) latency; the cycle delta is reported.
// +define+MUT_BANK builds the partition with bank 7 half 0's ROM data zeroed -> must FAIL.
module tb_s81_hcx_projection_sys;
 reg clk=0;always #5 clk=~clk;
 reg rn=0,sb=0,sv=0,cv=0,ffn=0;reg[6:0]a=0;reg[4095:0]d=0;
 wire ov_f,ov_s,f_f,f_s;wire[31:0]od_f,od_s;
 reg[4095:0]x0[0:79],x1[0:79],xr[0:79];reg[31:0]expectm[0:1],eps[0:0];
 reg[5:0]layer=0;integer layer_arg,nrand=4,seed=1;string dir;
 integer cyc=0,t0,lat_f=-1,lat_s=-1,errors=0;
 reg[31:0]res_f,res_s;integer tf,ts;
`ifdef MUT_BANK
 localparam integer MUT=1;
`else
 localparam integer MUT=0;
`endif
`ifndef HL
 `define HL 1
`endif
 ot_s81_hcx_projection_leaf #(.HLAYOUT(`HL)) flat(.clk(clk),.rst_n(rn),.stage_begin(sb),.stage_v(sv),.stage_word(a),.stage_d(d),
  .cmd_v(cv),.cmd_ffn(ffn),.cmd_layer(layer),.norm_eps(eps[0]),.o_v(ov_f),.o_d(od_f),.fault(f_f));
 ot_s81_hcx_projection_sys #(.HLAYOUT(`HL),.MUT_BANK(MUT)) part(.clk(clk),.rst_n(rn),.stage_begin(sb),.stage_v(sv),.stage_word(a),.stage_d(d),
  .cmd_v(cv),.cmd_ffn(ffn),.cmd_layer(layer),.norm_eps(eps[0]),.o_v(ov_s),.o_d(od_s),.fault(f_s));
 always @(posedge clk)cyc<=cyc+1;
 // capture each leaf's first o_v per block
 always @(posedge clk) begin
  if(ov_f && tf<0) begin tf=cyc-t0; res_f=od_f; end
  if(ov_s && ts<0) begin ts=cyc-t0; res_s=od_s; end
 end
 function automatic [15:0] rbf();
  reg[15:0]v; v[15]=$urandom()&1; v[14:7]=8'(118+($urandom()%20)); v[6:0]=7'($urandom()); return v;
 endfunction
 task automatic run_block(input integer b,input integer src);
  integer w;
  sb=1;@(negedge clk);sb=0;
  for(integer i=0;i<80;i=i+1)begin
   w=`HL?(20*(i%4)+i/4):i;
   sv=1;a=7'(w);d=(src==0)?x0[w]:(src==1)?x1[w]:xr[w];@(negedge clk);
  end
  sv=0;repeat(3)@(negedge clk);
  ffn=b[0];cv=1;t0=cyc;tf=-1;ts=-1;@(negedge clk);cv=0;
  while((tf<0||ts<0) && cyc-t0<3000)@(negedge clk);
  repeat(2)@(negedge clk);
  if(tf<0||ts<0)begin errors++;$display("HCX SYS ERR block%0d no output tf%0d ts%0d",b,tf,ts);end
  if(f_f||f_s)begin errors++;$display("HCX SYS ERR block%0d fault flat%0d part%0d",b,f_f,f_s);end
  if(res_f!==res_s)begin errors++;$display("HCX SYS ERR block%0d flat%h part%h",b,res_f,res_s);end
  if(src<2 && res_s!==expectm[src])begin errors++;$display("HCX SYS ERR block%0d golden%h part%h",b,expectm[src],res_s);end
  if(lat_f<0)lat_f=tf;else if(tf!=lat_f)begin errors++;$display("HCX SYS ERR flat latency %0d vs %0d",tf,lat_f);end
  if(lat_s<0)lat_s=ts;else if(ts!=lat_s)begin errors++;$display("HCX SYS ERR part latency %0d vs %0d",ts,lat_s);end
  $display("HCX SYS block%0d src%0d flat%h@%0d part%h@%0d golden_ok%0d",b,src,res_f,tf,res_s,ts,src<2?res_s===expectm[src]:-1);
  repeat(4)@(negedge clk);
 endtask
 initial begin
  if($value$plusargs("LAYER=%d",layer_arg))layer=6'(layer_arg);
  void'($value$plusargs("NRAND=%d",nrand));void'($value$plusargs("SEED=%d",seed));
  // Seed once: $urandom(seed) on every field would repeat one constant vector in Verilator.
  void'($urandom(seed));
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR required");
  $readmemh({dir,"/x0.mem"},x0);$readmemh({dir,"/x1.mem"},x1);$readmemh({dir,"/expected.mem"},expectm);$readmemh({dir,"/eps.mem"},eps);
  repeat(3)@(negedge clk);rn=1;
  run_block(0,0);run_block(1,1);
  for(integer r=0;r<nrand;r=r+1)begin
   for(integer w=0;w<80;w=w+1)for(integer l=0;l<256;l=l+1)xr[w][16*l+:16]=rbf();
   run_block(2+r,2);
  end
  if(errors)$fatal(1,"HCX_SYS_EQUIV FAIL errors%0d",errors);
  $display("HCX_SYS_EQUIV PASS blocks%0d flat_cycles%0d part_cycles%0d delta%0d",2+nrand,lat_f,lat_s,lat_s-lat_f);$finish;
 end
 initial begin #2000000;$fatal(1,"timeout");end
endmodule
