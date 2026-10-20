`timescale 1ns/1ps
// KV-CTL3 10-20: qkd_kv_die_cfg S32 1 (explicit kept POR copies per config field) in lockstep with S32 0 (NRST 43, CAP 1,
// PCOPIES 8 as bound in qkd_kvs_ctl).  Episodes: random POR pulses; mostly the legal image (sequential addresses, legal
// data, seal) with random gaps, plus corrupt words (bad address / data / seal) -> fault paths.  Every output on every edge.
// PASS: PASS KV_DCFG_S32_LOCKSTEP ...; FAIL KV_DCFG_S32_LOCKSTEP mismatches<n> ...
module tb_kv_dcfg_s32_lockstep;
 localparam integer NRST = 43, NW = 32 + NRST + 1;
 reg ck=0; always #1 ck=~ck;
 reg por_n=0, we=0; reg [7:0] a=0; reg [63:0] d=0;
 wire [159:0] ea0,eb0,ec0,ea1,eb1,ec1; wire [NRST*8-1:0] rd0,rd1; wire c0,c1,s0,s1,f0,f1;
 qkd_kv_die_cfg #(.NRST(NRST),.CAP(1),.MUT(0),.PCOPIES(8)) ref0(.ck(ck),.por_n(por_n),.cfg_we(we),.cfg_addr(a),.cfg_data(d),
  .ectl_a_cfg(ea0),.ectl_b_cfg(eb0),.ectl_c_cfg(ec0),.rst_dly(rd0),.fused_program_capability(c0),.sealed(s0),.fault(f0));
 qkd_kv_die_cfg_s32 #(.NRST(NRST),.CAP(1),.MUT(0),.PCOPIES(8),.S32(1)) dut(.ck(ck),.por_n(por_n),.cfg_we(we),.cfg_addr(a),.cfg_data(d),
  .ectl_a_cfg(ea1),.ectl_b_cfg(eb1),.ectl_c_cfg(ec1),.rst_dly(rd1),.fused_program_capability(c1),.sealed(s1),.fault(f1));
 integer mism=0,cycles=0,seals=0,flts=0,nz=0,i,w;
 always @(posedge ck) begin
  #0.1; cycles=cycles+1;
  if({ea0,eb0,ec0,rd0,c0,s0,f0}!=={ea1,eb1,ec1,rd1,c1,s1,f1}) begin mism=mism+1;
   if(mism<=5)$display("MISMATCH cyc %0d ea %h/%h rd %h/%h s %b/%b f %b/%b",cycles,ea0,ea1,rd0,rd1,s0,s1,f0,f1); end
  if(s0)seals=seals+1; if(f0)flts=flts+1; if(|ea0 || |rd0)nz=nz+1;
 end
 initial begin
  w=0;
  for(i=0;i<300000;i=i+1) begin
   @(negedge ck);
   if(i%3000==0) begin por_n=0; w=0; end else if(i%3000==3) por_n=1;
   if(i%3000==1500 && ($urandom%4==0)) por_n=0;           // mid-image POR (async assert)
   if(i%3000==1503) por_n=1;
   we=0; a=$urandom; d={$urandom,$urandom};
   if($urandom%3==0) begin
    we=1;
    if(((i/3000)%5)!=0 || ($urandom%8!=0)) begin           // legal word w
     a=w[7:0];
     if(w<32) d[63:15]=0; else if(w<32+NRST) d[63:8]=0; else if(w==32+NRST) d[63:1]=0; else d=64'h514b5644_43464731;
     w=(w<NW)?w+1:w;
    end
   end
  end
  if(mism!=0||seals<1000||flts<100||nz<10000) $display("FAIL KV_DCFG_S32_LOCKSTEP mismatches%0d cycles %0d sealed %0d fault %0d nonzero %0d",mism,cycles,seals,flts,nz);
  else $display("PASS KV_DCFG_S32_LOCKSTEP mismatches0 cycles %0d sealed_edges %0d fault_edges %0d nonzero_cfg_edges %0d",cycles,seals,flts,nz);
  $finish;
 end
endmodule
