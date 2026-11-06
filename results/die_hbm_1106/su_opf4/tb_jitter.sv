`timescale 1ns/1ps
// Exact bench of ONE hardened static-SU lane leaf (the physical wrapper module named by `LEAF_TOP, e.g.
// ot_hbm_su_static_kind0_lat4_leaf1_physical) at the production shape of its lane: the real quarter control image of
// su_arith_compile.py (31 baseline classes, 176 edges each, 64 fixed issues), its own pinned store bank
// (ot_hbm_su_static_pinned_bank, 6 real 128x256 SRAM models) seeded with its column of the N512 seed, one broadcast
// register in front of the leaf (as in ot_hbm_su_static_pgslice), and the independent NumPy hdc_golden expected words.
// Checks: every output on its compiled edge (8 + LATENCY + issue), exact data, exact address identity, the actual SRAM
// commit read back, no lane fault/collision. Mutants (plusargs): +MUT_ADDR (actual A SRAM read request wrong row), +MUT_DATA (one
// SRAM read bit flipped), +MUT_PHASE (control one edge late).
`ifndef LEAF_TOP
`define LEAF_TOP ot_hbm_su_static_kind0_lat4_leaf1_physical
`endif
module tb_su_static_lane_leaf;
 parameter integer NOPS=31,MLAT=5,ALAT=3,LEAF=1,LANE=288,PINREG=1;  // PINREG: leaf is pin-registered (outputs +4 edges)          // global lane (quarter LANE/128, local LANE%128)
 localparam integer LATENCY=23+4*(MLAT-3)+(ALAT-3)+LEAF;
 localparam integer FIRST_OUTPUT=8+LATENCY+4*PINREG+4;   // pin regs: command +1, store round trip +2, write +1
 localparam integer Q=LANE/128,LOCAL=LANE%128;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,seed_v=0,drain_v=0;
 reg [8:0] seed_row=0,drain_row=0;
 reg [6967:0] programme [0:NOPS*240-1];
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
 wire [23:0] vi_addr; wire [17:0] vm_waddr,kv_waddr; wire [95:0] rd_addr; wire [3:0] rd_re; wire [7:0] rd_src; wire [127:0] rd_q;
 wire [159:0] q;
 bit mut_addr,mut_data,mut_phase;
 wire [127:0] external_rd_q=q[127:0] ^ (mut_data?128'h00010000:128'd0);
 ot_hbm_su_pg_lane1_opf4_core dut(
 .clk(clk),.bank0_rst_n(rst_n),.lane0_rst_n(rst_n),
 .bank0_read_v({drain_v,rd_re}),.bank0_read_addr(drain_row),
 .bank0_write_v(seed_v||vm_we),.bank0_write_addr(seed_v?seed_row:{vm_waddr[17:16],vm_waddr[13:7]}),
 .bank0_write_data(seed_v?seed[seed_row*512+LANE]:vm_wdata),.bank0_read_data(q),
 .lane0_rd_q(external_rd_q),.lane0_rd_addr(),
 .lane0_bank(bank),
 .lane0_co_rnd(co_rnd),
 .lane0_cpair(cpair),
 .lane0_cx_amin(cx_amin),
 .lane0_cx_arelu(cx_arelu),
 .lane0_cx_arnd(cx_arnd),
 .lane0_cx_cclip(cx_cclip),
 .lane0_emit(emit),
 .lane0_ld(ld),
 .lane0_ld_bank(ld_bank),
 .lane0_aibase(aibase),
 .lane0_aind(aind),
 .lane0_ca_ad(ca_ad),
 .lane0_ca_imm2(ca_imm2),
 .lane0_ce_e2(ce_e2),
 .lane0_ce_imm1(ce_imm1),
 .lane0_ci_sfu(ci_sfu),
 .lane0_cm_imm1(cm_imm1),
 .lane0_cm_m1(cm_m1),
 .lane0_cm_m2(cm_m2),
 .lane0_cm_qm(cm_qm),
 .lane0_co_dst(co_dst),
 .lane0_cp_imm1(cp_imm1),
 .lane0_cp_m1(cp_m1),
 .lane0_cs_e1(cs_e1),
 .lane0_cs_imm2(cs_imm2),
 .lane0_cs_sfu(cs_sfu),
 .lane0_cx_imm3(cx_imm3),
 .lane0_dst(dst),
 .lane0_gsh(gsh),
 .lane0_i_v(i_v),
 .lane0_krow(krow),
 .lane0_lane_id(lane_id),
 .lane0_ld_c(ld_c),
 .lane0_ls(ls),
 .lane0_lvw(lvw),
 .lane0_ni(ni),
 .lane0_no(no),
 .lane0_o_v(o_v),
 .lane0_obase(obase),
 .lane0_ro_v(ro_v),
 .lane0_ro_x(ro_x),
 .lane0_rd_re(rd_re),
 .lane0_rd_src(rd_src),
 .lane0_side_y(side_y),
 .lane0_srcs(srcs),
 .lane0_vb(vb),
 .lane0_vm_we(vm_we),
 .lane0_vm_waddr(vm_waddr),
 .lane0_vm_wdata(vm_wdata),
 .lane0_kv_we(kv_we),
 .lane0_kv_waddr(kv_waddr),
 .lane0_kv_wdata(kv_wdata),
 .lane0_fault(fault),
 .lane0_coll(coll)
 );
 integer op=0,cycle=0,errors=0,checks=0,outputs=0,count=0;
 reg [31:0] issue_cycles[0:NOPS*64-1];
 bit reset_between;
 string dir;
 task fail(input string m); begin if(errors<8)$display("SU_LANE ERROR op=%0d cycle=%0d %s",op,cycle,m); errors=errors+1; end endtask
 always @(posedge clk) if(rst_n&&!seed_v)begin
  if(vm_we)begin
   checks=checks+1;outputs=outputs+1;
   if(count<64 && cycle!=integer'(issue_cycles[op*64+count])+40)fail("per-word selected-profile edge");
   if(count>=64)fail("extra output");
   else begin
    if(count==0)begin $display("PHASE op=%0d first_output=%0d",op,cycle); if(cycle!=FIRST_OUTPUT)fail("selected profile first-output edge");end
    if(vm_wdata!==gold[op*32768+count*512+LANE])fail($sformatf("word=%0d got=%h want=%h",count,vm_wdata,gold[op*32768+count*512+LANE]));
    if(vm_waddr!==18'((Q<<14)+(((256+count)>>7)<<16)+(((256+count)&127)<<7)+LOCAL))fail("output identity/address");
   end
   count=count+1;
  end
  if(fault||coll)fail("lane fault/collision");
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR missing");
  mut_addr=$test$plusargs("MUT_ADDR");mut_data=$test$plusargs("MUT_DATA");mut_phase=$test$plusargs("MUT_PHASE");
  $readmemh({dir,"/seed.mem"},seed);$readmemh({dir,"/gold.mem"},gold);$readmemh({dir,"/control.mem"},programme);$readmemh({dir,"/issue_cycles.mem"},issue_cycles); reset_between=$test$plusargs("RESET_BETWEEN");
  repeat(4)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);seed_v=1;
  for(integer r=0;r<512;r=r+1)begin seed_row=9'((197*r+17)%512);@(negedge clk);if(r%7==3)begin seed_v=0;repeat((r%3)+1)@(negedge clk);seed_v=1;end end
  seed_v=0;repeat(5)@(negedge clk);
  for(integer j=0;j<NOPS;j=j+1)begin
   op=j;count=0;
   if(reset_between)begin
    seed_v=1;control=0;rst_n=0;repeat(12)@(negedge clk);
    if(vm_we||ro_v)fail("reset did not flush outputs");
    rst_n=1;repeat(12)@(negedge clk);
    for(integer sr=0;sr<512;sr=sr+1)begin seed_row=9'((197*sr+17)%512);@(negedge clk);if(sr%7==3)begin seed_v=0;repeat((sr%3)+1)@(negedge clk);seed_v=1;end end
    seed_v=0;repeat(5)@(negedge clk);
   end
   for(integer c=0;c<240;c=c+1)begin
    reg [6967:0] full;
    cycle=c;
    full=programme[j*240+(mut_phase&&c>0?c-1:c)];
    control=full[Q*1742+:1742];
    @(negedge clk);
   end
   control=0;
   if(count!=64)fail($sformatf("outputs %0d of 64",count));
   drain_v=1;
   for(integer r=0;r<69;r=r+1)begin
    drain_row=9'(256+r);
    @(posedge clk);#1;
    if(r>=5)begin checks=checks+1; if(q[128+:32]!==gold[j*32768+(r-5)*512+LANE])fail("SRAM commit readback"); end
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
