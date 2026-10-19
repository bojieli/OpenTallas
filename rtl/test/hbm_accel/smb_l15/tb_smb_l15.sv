`timescale 1ns/1ps
// Minimum component: actual RUN collar -> actual relative descriptor issuer ->
// actual2048word calendar. Dense id_sel0, so this does not qualify router IDs.
module tb_smb_l15;
 parameter integer MUT=0;
 reg clk=0; always #1 clk=~clk;
 reg rst_n=0,cfg_v=0,desc_v=0,launch_v=0;
 reg[7:0]cfg_target=8'd64;reg[11:0]cfg_addr=0,desc_base=0;reg[12:0]desc_limit=0;reg[15:0]desc_loops=0;reg[255:0]cfg_data=0;
 wire a_we,b_we,rv,configured,cfault,cactive;wire[10:0]aa;wire[7:0]ba,rb,arg;wire[8:0]rc;wire[255:0]ad,bd;
 wire running,rdone,ifault,calactive,caldone,calfault;
 ot_static_run_target #(.AWA(11),.AWB(8),.RBW(8),.RCW(9),.NA(2),.NF(1),.TGT_PIN(1),.RSYNC(1)) cp(
 .clk(clk),.rst_n(rst_n),.tgt(8'd64),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
 .tgt_active({calactive,running}),.tgt_fault(ifault|calfault),.a_we(a_we),.a_addr(aa),.a_data(ad),.b_we(b_we),.b_addr(ba),.b_data(bd),
 .run_v(rv),.run_base(rb),.run_count(rc),.run_arg(arg),.configured(configured),.fault(cfault),.active(cactive));
 wire reserve,start,ps;wire[31:0]reserve_base;wire[14:0]reserve_row;wire[11:0]total;wire[1:0]rbank,sbank;
 wire[15:0]epoch,sepoch,ploops;wire[6:0]rows;wire[9:0]tag;wire[10:0]pbase;wire[11:0]plimit;wire[45:0]ctx;
 wire[7:0]layer_arg=arg ^ ((MUT==2)?8'd1:8'd0);
 ot_hbm_svc_sm_issuer_rel #(.LBANKS(4),.NID(6),.IDW(9),.PAW(11),.DD(256)) issuer(
 .clk(clk),.rst_n(rst_n),.desc_we(b_we),.desc_addr(ba),.desc_data(bd),.run_v(rv),.run_base(rb),.run_count(rc),.run_layer(layer_arg),
 .ids_v(1'b0),.ids_layer(8'd0),.ids(54'd0),.running(running),.run_done(rdone),.fault(ifault),
 .reserve_v(reserve),.reserve_ready(1'b1),.reserve_base(reserve_base),.reserve_row_base(reserve_row),.reserve_total(total),
 .reserve_bank(rbank),.reserve_epoch(epoch),.reserve_rows(rows),.reserve_tag_base(tag),.block_ready(4'hf),
 .cache_ready(2'b11),.cache_owned(2'b00),.start_v(start),.start_bank(sbank),.start_epoch(sepoch),
 .program_start_v(ps),.program_start_base(pbase),.program_start_limit(plimit),.program_start_loops(ploops),.program_start_ctx(ctx),.program_done(caldone));
 wire[10:0]program_addr=(MUT==1)?{1'b0,aa[9:0]}:aa;
 wire[15:0]word,iter;wire[45:0]wordctx;wire lastit,cv;wire[31:0]ordinal;
 ot_smh_calendar_static_x #(.W(16),.AW(11),.XW(46)) calendar(
 .clk(clk),.rst_n(rst_n),.cfg_we(a_we),.cfg_addr(program_addr),.cfg_data(ad),.start_v(ps),.start_base(pbase),.start_limit(plimit),
 .start_loops(ploops),.start_ctx(ctx),.calendar(word),.calendar_ctx(wordctx),.calendar_iter(iter),.calendar_lastit(lastit),
 .calendar_v(cv),.ordinal(ordinal),.active(calactive),.done(caldone),.fault(calfault));
 integer pe=0,cfg_at=-99,launch_at=-99;
 always @(posedge clk)begin pe<=pe+1;if(cfg_v)cfg_at<=pe;if(launch_v)launch_at<=pe;end
 integer wc=0,reserves=0,runs=0,dones=0,c=0;reg[255:0]d;
 task fail(input string why);$display("SMB_L15_FAIL %s",why);$fatal(1,"SMB_L15_FAIL");endtask
 task cfg(input[11:0]addr,input[255:0]data);
  @(negedge clk);cfg_addr=addr;cfg_data=data;cfg_v=1;
  @(negedge clk);cfg_v=0;repeat(5)@(negedge clk);
 endtask
 always @(negedge clk) if(rst_n) begin
  c=c+1;
  if(cfault||ifault||calfault) fail("unexpected fault");
  if(a_we||b_we)if(pe-cfg_at!=2)fail("cfg-to-write cadence");
  if(rv)begin if(pe-launch_at!=2)fail("launch-to-run cadence");runs=runs+1;if(rb!=255||rc!=1||arg!=3)fail("run base/count/layer width");end
  if(reserve)begin reserves=reserves+1;if(reserve_row!=103||reserve_base[9:7]!=0||rows!=1||tag!=7)fail("relative row/layer map");end
  if(cv)begin
   if(word!==((wc==0)?16'hbeef:16'hcafe)||ordinal!=wc||wordctx[45:34]!=5)fail("programme bank/context");
   wc=wc+1;
  end
  if(rdone)dones=dones+1;
  if(c>250)fail("watchdog missing high-bank programme");
 end
 initial begin
  repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
  d=0;d[255:240]=16'hc7a1;d[234:224]=11'd1024;d[15:0]=16'hbeef;cfg(12'h800,d);
  d[234:224]=11'd1025;d[15:0]=16'hcafe;cfg(12'h801,d);
  d=0;d[255:240]=16'h5d15;d[239:232]=8'd255;d[46:32]=15'd100;d[71:65]=7'd1;
  d[81:72]=10'd7;d[189]=1;d[102:92]=11'd1026;d[118:103]=16'd1;d[142:119]=24'd40;
  d[157:143]=15'd8;d[188:177]=12'd5;cfg(12'h4ff,d);
  @(negedge clk);desc_base=255;desc_limit=256;desc_loops=4;desc_v=1;
  @(negedge clk);desc_v=0;repeat(5)@(negedge clk);launch_v=1;
  @(negedge clk);launch_v=0;
  wait(dones==1);repeat(4)@(negedge clk);
  if(wc!=2||reserves!=1||runs!=1)fail("vacuous transaction");
  $display("SMB_L15_PASS program1024_1025 descriptor255 layer3 rows103 words%0d latency_cfg2_run2 reset2",wc);$finish;
 end
endmodule
