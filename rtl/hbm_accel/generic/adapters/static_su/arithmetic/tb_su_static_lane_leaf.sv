`timescale 1ns/1ps
// Exact bench of ONE hardened static-SU lane leaf (the physical wrapper module named by `LEAF_TOP, e.g.
// ot_hbm_su_static_kind0_lat4_leaf1_physical) at the production shape of its lane: the real quarter control image of
// su_arith_compile.py (31 baseline classes, 176 edges each, 64 fixed issues), its own pinned store bank
// (ot_hbm_su_static_pinned_bank, 6 real 128x256 SRAM models) seeded with its column of the N512 seed, one broadcast
// register in front of the leaf (as in ot_hbm_su_static_pgslice), and the independent NumPy hdc_golden expected words.
// Checks: every output on its compiled edge (8 + LATENCY + issue), exact data, exact address identity, the actual SRAM
// commit read back, no lane fault/collision. Mutants (plusargs): +MUT_ADDR (A affine bit-0 term +128: wrong row), +MUT_DATA (one
// SRAM read bit flipped), +MUT_PHASE (control one edge late).
`ifndef LEAF_TOP
`define LEAF_TOP ot_hbm_su_static_kind0_lat4_leaf1_physical
`endif
module tb_su_static_lane_leaf;
 parameter integer NOPS=31,MLAT=4,ALAT=3,LEAF=1,LANE=205,PINREG=0;  // PINREG: leaf is pin-registered (outputs +4 edges)          // global lane (quarter LANE/128, local LANE%128)
 localparam integer LATENCY=23+4*(MLAT-3)+(ALAT-3)+LEAF;
 localparam integer FIRST_OUTPUT=8+LATENCY+4*PINREG;   // pin regs: command +1, store round trip +2, write +1
 localparam integer Q=LANE/128,LOCAL=LANE%128;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,seed_v=0,drain_v=0;
 reg [8:0] seed_row=0,drain_row=0;
 reg [6967:0] programme [0:NOPS*176-1];
 reg [31:0] seed [0:262143],gold [0:NOPS*32768-1];
 reg [1741:0] control=0,ctl=0;
 always @(posedge clk or negedge rst_n) if(!rst_n) ctl<=0; else ctl<=control;   // the slice's broadcast register
 wire clk_stage_0=clk,clk_stage_1=clk,clk_stage_2=clk,clk_stage_3=clk,clk_stage_4=clk,clk_stage_5=clk,clk_stage_6=clk,clk_stage_7=clk;
 wire clk_insert_0=clk,clk_insert_1=clk,clk_insert_2=clk,clk_insert_3=clk;
 wire [10:0] lane_id=11'(LOCAL);
 wire ld,ld_bank,emit,bank,cpair,cx_arnd,cx_arelu,cx_amin,cx_cclip,co_rnd;
 wire [1199:0] ld_c_full; wire [839:0] ld_c;
 wire [23:0] o_v,i_v,no,ni,krow,obase,aibase; wire [3:0] ls,lvw; wire [119:0] vb;
 wire [1:0] aind,dst,cm_m2,ce_e2,co_dst; wire [4:0] gsh; wire [7:0] srcs,cx_srcs;
 wire [31:0] cx_imm3,cp_imm1,cm_imm1,ca_imm2,cs_imm2,ce_imm1; wire [2:0] cp_m1,cm_m1,cm_qm,ca_ad,ci_sfu,cs_sfu,cs_e1;
 assign {ld,ld_bank,ld_c_full,emit,bank,o_v,i_v,no,ni,ls,lvw,vb,krow,obase,aibase,aind,gsh,cpair,dst,srcs,cx_arnd,cx_arelu,cx_amin,cx_cclip,cx_imm3,cp_m1,cp_imm1,cm_m1,cm_m2,cm_qm,cm_imm1,ca_ad,ca_imm2,ci_sfu,cs_sfu,cs_e1,cs_imm2,ce_e2,ce_imm1,co_rnd,co_dst}=ctl;
 assign cx_srcs=srcs;
 for(genvar s=0;s<5;s=s+1)begin:g_terms assign ld_c[s*168+:168]=ld_c_full[s*240+:168]; end
 wire vi_re,vm_we,kv_we,ro_v,fault,coll,side_v; wire [31:0] vi_q,vm_wdata,kv_wdata,ro_x,side_x; wire [31:0] side_y=32'd0;
 wire [23:0] vi_addr,vm_waddr,kv_waddr; wire [95:0] rd_addr; wire [3:0] rd_re; wire [7:0] rd_src; wire [127:0] rd_q;
 `LEAF_TOP dut(.*);
 // the lane's own pinned bank (6 readers: A/B/C/D, gather index, drain)
 wire [53:0] ra; wire [5:0] rv; wire [191:0] q;
 bit mut_addr,mut_data,mut_phase;
 for(genvar p=0;p<4;p=p+1)begin:g_rd
  wire [23:0] a=rd_addr[p*24+:24];
  assign ra[p*9+:9]={a[17:16],a[13:7]}; assign rv[p]=rd_re[p];
  assign rd_q[p*32+:32]=q[p*32+:32]^(mut_data&&p==0?32'h00010000:32'h0);
 end
 assign ra[4*9+:9]={vi_addr[16+:2],vi_addr[7+:7]}; assign rv[4]=vi_re; assign vi_q=q[4*32+:32];
 assign ra[5*9+:9]=drain_row; assign rv[5]=drain_v;
 ot_hbm_su_static_pinned_bank bank_u(.clk(clk),.clk_macro({6{clk}}),.rst_n(rst_n),.read_v(rv),.read_addr(ra),.read_data(q),.read_return(),
  .write_v(seed_v||vm_we),.write_addr(seed_v?seed_row:{vm_waddr[17:16],vm_waddr[13:7]}),
  .write_data(seed_v?seed[seed_row*512+LANE]:vm_wdata));
 integer op=0,cycle=0,errors=0,checks=0,outputs=0,count=0;
 string dir;
 task fail(input string m); begin if(errors<8)$display("SU_LANE ERROR op=%0d cycle=%0d %s",op,cycle,m); errors=errors+1; end endtask
 always @(posedge clk) if(rst_n&&!seed_v)begin
  if(vm_we)begin
   checks=checks+1;outputs=outputs+1;
   if(count>=64)fail("extra output");
   else begin
    if(cycle!=FIRST_OUTPUT+count)fail($sformatf("output edge %0d want %0d",cycle,FIRST_OUTPUT+count));
    if(vm_wdata!==gold[op*32768+count*512+LANE])fail($sformatf("word=%0d got=%h want=%h",count,vm_wdata,gold[op*32768+count*512+LANE]));
    if(vm_waddr!==24'((Q<<14)+(((256+count)>>7)<<16)+(((256+count)&127)<<7)+LOCAL))fail("output identity/address");
   end
   count=count+1;
  end
  if(fault||coll)fail("lane fault/collision");
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR missing");
  mut_addr=$test$plusargs("MUT_ADDR");mut_data=$test$plusargs("MUT_DATA");mut_phase=$test$plusargs("MUT_PHASE");
  $readmemh({dir,"/seed.mem"},seed);$readmemh({dir,"/gold.mem"},gold);$readmemh({dir,"/control.mem"},programme);
  repeat(4)@(negedge clk);rst_n=1;seed_v=1;
  for(integer r=0;r<512;r=r+1)begin seed_row=9'(r);@(negedge clk);end
  seed_v=0;repeat(5)@(negedge clk);
  for(integer j=0;j<NOPS;j=j+1)begin
   op=j;count=0;
   for(integer c=0;c<176;c=c+1)begin
    reg [6967:0] full;
    cycle=c;
    full=programme[j*176+(mut_phase&&c>0?c-1:c)];
    control=full[Q*1742+:1742];
    if(mut_addr&&c==0)control[540+:24]=24'd129;   // +128 on bit-0 lanes: crosses into the row bits
    @(negedge clk);
   end
   control=0;
   if(count!=64)fail($sformatf("outputs %0d of 64",count));
   drain_v=1;
   for(integer r=0;r<66;r=r+1)begin
    drain_row=9'(256+r);
    @(posedge clk);#1;
    if(r>=2)begin checks=checks+1; if(q[160+:32]!==gold[j*32768+(r-2)*512+LANE])fail("SRAM commit readback"); end
    @(negedge clk);
   end
   drain_v=0;
  end
  if(errors)$fatal(1,"SU_LANE FAIL checks=%0d errors=%0d outputs=%0d",checks,errors,outputs);
  $display("SU_LANE PASS lane=%0d quarter=%0d outputs=%0d checks=%0d first_output=%0d issue_to_output=%0d MLAT=%0d ALAT=%0d LEAF=%0d",
           LANE,Q,outputs,checks,FIRST_OUTPUT,LATENCY,MLAT,ALAT,LEAF);
  $finish;
 end
endmodule
