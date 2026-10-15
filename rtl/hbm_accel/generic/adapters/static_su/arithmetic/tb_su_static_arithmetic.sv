`timescale 1ns/1ps
module tb_su_static_arithmetic;
 parameter integer NOPS=12,MLAT=3,ALAT=3,LEAF=0;
 localparam integer LATENCY=23+4*(MLAT-3)+(ALAT-3)+LEAF;
 localparam integer FIRST_OUTPUT=8+LATENCY;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,seed_v=0,drain_v=0;
 reg[8:0]seed_row=0,drain_row=0;
 reg[6967:0]control=0;
 reg[31:0]seed[0:262143],gold[0:NOPS*32768-1];
 reg[6967:0]programme[0:NOPS*176-1];
 wire[511:0]vi_re,vm_we,kv_we,ro_v,fault,coll;
 wire[12287:0]vi_addr,vm_waddr,kv_waddr;
 wire[49151:0]rd_addr;wire[2047:0]rd_re;wire[4095:0]rd_src;
 wire[16383:0]vm_wdata,kv_wdata,ro_x,vi_q;
 wire[65535:0]rd_q;
 wire side_v;wire[31:0]side_x;
 wire[98303:0]bank_q;
 integer op=0,cycle=0,errors=0,checks=0,outputs=0;
 integer count[0:511];
 bit mut_addr,mut_phase,mut_data;
 string dir;
 ot_hbm_su_static_arithmetic #(.MLAT(MLAT),.ALAT(ALAT),.LEAF(LEAF)) dut(.clk_lane({4096{clk}}),.clk_insert({2048{clk}}),.rst_lane_n({512{rst_n}}),
  .clk_bcast({64{clk}}),.rst_bcast_n({64{rst_n}}),.control(control),
  .vi_q(vi_q),.rd_q(rd_q),.side_y(32'h0),.side_v(side_v),.side_x(side_x),
  .vi_re(vi_re),.vm_we(vm_we),.kv_we(kv_we),.ro_v(ro_v),.fault(fault),.coll(coll),
  .vi_addr(vi_addr),.vm_waddr(vm_waddr),.kv_waddr(kv_waddr),.rd_addr(rd_addr),
  .rd_re(rd_re),.rd_src(rd_src),.vm_wdata(vm_wdata),.kv_wdata(kv_wdata),.ro_x(ro_x));
 for(genvar l=0;l<512;l=l+1)begin:g_bank
  wire[53:0]ra;wire[5:0]rv,ret;wire[191:0]q;
  for(genvar p=0;p<4;p=p+1)begin:g_read
   wire[23:0]a=rd_addr[(l*4+p)*24+:24];
   assign ra[p*9+:9]={a[17:16],a[13:7]};assign rv[p]=rd_re[l*4+p];
   assign rd_q[(l*4+p)*32+:32]=q[p*32+:32]^(mut_data&&l==129&&p==0?32'h00010000:0);
  end
  assign ra[4*9+:9]={vi_addr[l*24+16+:2],vi_addr[l*24+7+:7]};
  assign rv[4]=vi_re[l];assign vi_q[l*32+:32]=q[4*32+:32];
  assign ra[5*9+:9]=drain_row;assign rv[5]=drain_v;
  assign bank_q[l*192+:192]=q;
  wire[23:0]wa=vm_waddr[l*24+:24];
  ot_hbm_su_static_pinned_bank bank(.clk(clk),.rst_n(rst_n),.read_v(rv),.read_addr(ra),
   .read_data(q),.read_return(ret),.write_v(seed_v||vm_we[l]),
   .write_addr(seed_v?seed_row:{wa[17:16],wa[13:7]}),
   .write_data(seed_v?seed[seed_row*512+l]:vm_wdata[l*32+:32]));
 end
 task fail(input string msg);
  if(errors<8)$display("SU_ARITH ERROR op=%0d cycle=%0d %s",op,cycle,msg);
  errors=errors+1;
 endtask
 always @(posedge clk)if(rst_n&&!seed_v)begin
  for(integer l=0;l<512;l=l+1)begin
   if(vm_we[l])begin
    checks=checks+1;outputs=outputs+1;
    if(count[l]>=64)fail("extra output");
    else begin
     // Compiler cycle8 issue -> registered output visible to the receiving
     // pin at cycle31. Every subsequent issued vector must appear next edge.
     if(cycle!=FIRST_OUTPUT+count[l])fail("compiled output cycle mismatch");
     if(vm_wdata[l*32+:32]!==gold[op*32768+count[l]*512+l])fail($sformatf("lane=%0d word=%0d got=%h want=%h",l,count[l],vm_wdata[l*32+:32],gold[op*32768+count[l]*512+l]));
     if(vm_waddr[l*24+:24]!==24'(((l/128)<<14)+(((256+count[l])>>7)<<16)+(((256+count[l])&127)<<7)+(l%128)))fail("output identity/address");
    end
    count[l]=count[l]+1;
   end
  end
  if(|coll||(|fault))fail("native pipeline fault/collision");
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR missing");
  mut_addr=$test$plusargs("MUT_ADDR");mut_phase=$test$plusargs("MUT_PHASE");mut_data=$test$plusargs("MUT_DATA");
  $readmemh({dir,"/seed.mem"},seed);$readmemh({dir,"/gold.mem"},gold);$readmemh({dir,"/control.mem"},programme);
  for(integer l=0;l<512;l=l+1)count[l]=0;
  repeat(4)@(negedge clk);rst_n=1;seed_v=1;
  for(integer r=0;r<512;r=r+1)begin seed_row=9'(r);@(negedge clk);end
  seed_v=0;repeat(5)@(negedge clk);
  for(integer j=0;j<NOPS;j=j+1)begin
   op=j;for(integer l=0;l<512;l=l+1)count[l]=0;
   for(integer c=0;c<176;c=c+1)begin
    cycle=c;
    control=programme[j*176+(mut_phase&&c>0?c-1:c)];
    // Corrupt the quarter1 A affine bit0 term, not golden or reference memory.
    if(mut_addr&&c==0)control[1742+540+:24]=24'd3;
    @(negedge clk);
   end
   control=0;
   for(integer l=0;l<512;l=l+1)if(count[l]!=64)fail("missing output");
   drain_v=1;
   for(integer r=0;r<66;r=r+1)begin
    drain_row=9'(256+r);
    @(posedge clk);#1;
    if(r>=2)for(integer l=0;l<512;l=l+1)begin
     checks=checks+1;
     if(bank_q[l*192+160+:32]!==gold[j*32768+(r-2)*512+l])fail("actual SRAM output commit mismatch");
    end
    @(negedge clk);
   end
   drain_v=0;
  end
  if(errors)$fatal(1,"SU_ARITH FAIL checks=%0d errors=%0d outputs=%0d",checks,errors,outputs);
  $display("SU_ARITH PASS lanes=512 FULL=1 SFU=127 LIGHT=384 actual_SRAMs=3072 outputs=%0d checks=%0d fixed_issue=64 first_output=%0d last_output=%0d issue_to_output=%0d II=1 MLAT=%0d ALAT=%0d LEAF=%0d",outputs,checks,FIRST_OUTPUT,FIRST_OUTPUT+63,LATENCY,MLAT,ALAT,LEAF);$finish;
 end
endmodule
