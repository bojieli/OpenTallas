`timescale 1ns/1ps
module tb_hbm_su_static_scalar;
 reg clk=0;always #0.4166665 clk=~clk;
 reg rst_n=0,seed_v=0,drain_v=0;
 reg [8:0] seed_row=0,drain_row=0;
 reg [1741:0] control=0;
 reg [31:0] seed[0:2559],gold[0:319],r_gold[0:319];
 reg [1741:0] programme[0:1599];
 wire side_v;wire [31:0] side_x;wire [2:0] side_fn,side_fn_out;
 wire vi_re,vm_we,kv_we,ro_v,fault,coll;
 wire [23:0] vi_addr,vm_waddr,kv_waddr;
 wire [95:0] rd_addr;wire [3:0] rd_re;wire [7:0] rd_src;
 wire [31:0] vm_wdata,kv_wdata,ro_x,vi_q;
 wire [127:0] rd_q;
 ot_hbm_su_static_scalar dut(.clk_lane({8{clk}}),.clk_insert({4{clk}}),.clk_side({6{clk}}),.clk_bcast(clk),.rst_n(rst_n),
  .control(control),.vi_q(vi_q),.rd_q(rd_q),.side_v(side_v),.side_x(side_x),.side_fn(side_fn),.side_fn_out(side_fn_out),
  .vi_re(vi_re),.vm_we(vm_we),.kv_we(kv_we),.ro_v(ro_v),.fault(fault),.coll(coll),
  .vi_addr(vi_addr),.vm_waddr(vm_waddr),.kv_waddr(kv_waddr),.rd_addr(rd_addr),.rd_re(rd_re),.rd_src(rd_src),
  .vm_wdata(vm_wdata),.kv_wdata(kv_wdata),.ro_x(ro_x));
 wire [53:0] ra;wire [5:0] rv,ret;wire [191:0] q;
 for(genvar p=0;p<4;p=p+1)begin
  assign ra[p*9+:9]={rd_addr[p*24+16+:2],rd_addr[p*24+7+:7]};
  assign rv[p]=rd_re[p];assign rd_q[p*32+:32]=q[p*32+:32];
 end
 assign ra[4*9+:9]={vi_addr[16+:2],vi_addr[7+:7]};assign rv[4]=vi_re;assign vi_q=q[128+:32];
 assign ra[5*9+:9]=drain_row;assign rv[5]=drain_v;
 integer op=0,cycle=0,outputs=0,side_inputs=0,checks=0;
 integer count=0,side_count=0;
 integer fn_code[0:4],depth[0:4];
 reg mut_fn=0,mut_div=0;
 reg [1023:0] dir;
 wire [23:0] wa=vm_waddr;
 ot_hbm_su_static_pinned_bank bank(.clk(clk),.rst_n(rst_n),.read_v(rv),.read_addr(ra),.read_data(q),.read_return(ret),
  .write_v(seed_v||vm_we),.write_addr(seed_v?seed_row:{wa[17:16],wa[13:7]}),.write_data(seed_v?seed[op*512+seed_row]:vm_wdata));
 always @(posedge clk)if(rst_n&&!seed_v)begin
  if(side_v)begin
   if(side_count>=64)$fatal(1,"HEAD_SIDE_EXTRA");
   if(cycle != 8+16+(op==4?16:0)+side_count)$fatal(1,"HEAD_SIDE_PHASE op=%d actual=%d expected=%d",op,cycle,8+16+(op==4?16:0)+side_count);
   if(side_fn!==fn_code[op])$fatal(1,"HEAD_SIDE_FN");
   if(!mut_div && side_x!==r_gold[op*64+side_count])$fatal(1,"HEAD_SIDE_R op=%d word=%d actual=%h expected=%h",op,side_count,side_x,r_gold[op*64+side_count]);
   side_count=side_count+1;side_inputs=side_inputs+1;
  end
  if(vm_we)begin
   if(count>=64)$fatal(1,"HEAD_EXTRA");
   if(cycle != 8+23+depth[op]+(op==4?16:0)+count)$fatal(1,"HEAD_OUT_PHASE op=%d actual=%d expected=%d",op,cycle,8+23+depth[op]+(op==4?16:0)+count);
   if(vm_wdata!==gold[op*64+count])$fatal(1,"HEAD_WORD op=%d word=%d actual=%h expected=%h",op,count,vm_wdata,gold[op*64+count]);
   if(vm_waddr!==24'((((256+count)>>7)<<16)|(((256+count)&127)<<7)))$fatal(1,"HEAD_ADDR");
   count=count+1;outputs=outputs+1;checks=checks+1;
  end
  if(fault||coll)$fatal(1,"HEAD_FAULT");
 end
 initial begin
  fn_code[0]=2;fn_code[1]=3;fn_code[2]=6;fn_code[3]=7;fn_code[4]=2;
  depth[0]=37;depth[1]=31;depth[2]=162;depth[3]=104;depth[4]=37;
  mut_fn=$test$plusargs("MUT_FN");mut_div=$test$plusargs("MUT_DIV");
  if(!$value$plusargs("DATA=%s",dir))$fatal(1,"DATA");
  $readmemh({dir,"/seed.hex"},seed);$readmemh({dir,"/gold.hex"},gold);$readmemh({dir,"/r.hex"},r_gold);$readmemh({dir,"/control.hex"},programme);
  repeat(5)@(negedge clk);rst_n=1;
  for(op=0;op<5;op=op+1)begin
   seed_v=1;
   for(integer row=0;row<512;row=row+1)begin seed_row=9'(row);@(negedge clk);end
   seed_v=0;repeat(5)@(negedge clk);count=0;side_count=0;
   for(integer c=0;c<320;c=c+1)begin
    cycle=c;control=programme[op*320+c];
    if(mut_fn)control[72+:3]=3'(fn_code[op]^1);
    if(mut_div&&op==4)control[153+:32]=32'h44800000;
    @(negedge clk);
   end
   control=0;
   if(count!=64||side_count!=64)$fatal(1,"HEAD_COUNT %d %d",count,side_count);
   drain_v=1;
   for(integer row=0;row<68;row=row+1)begin
    drain_row=9'(255+row);@(posedge clk);#0.01;
    if(row>=2)begin
     if(q[160+:32] !== (row==2?seed[op*512+255]:row==67?seed[op*512+320]:gold[op*64+row-3]))
      $fatal(1,"HEAD_SRAM_COMMIT op=%d row=%d actual=%h",op,row,q[160+:32]);
     checks=checks+1;
    end
    @(negedge clk);
   end
   drain_v=0;
  end
  if(outputs!=320||side_inputs!=320)$fatal(1,"HEAD_TOTAL");
  $display("PASS actualKIND2head6SRAM nativeSIDE320outputs320inputs checks=%0d depths37/31/162/104 normDIVIMM19+EPS→RSQRT extra16 OUTemitdelta60/54/185/127/76 rootmax13902 fullN512UNQUALIFIED physicalUNQUALIFIED",checks);$finish;
 end
endmodule
