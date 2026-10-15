`timescale 1ns/1ps
import ot_hdc_engram_tables_shipped_pkg::*;
module tb_s81_engram_clock_roots;
 reg ck=0; always #0.5 ck=~ck;
 reg rst_n=0,cfg_layer=0,win_v=0,hq_cred=0,hr_v=0,o_cred=0;
 reg [1:0] cfg_rank=0; reg [4*ENG_ID_W-1:0] win_ids=0;
 reg [3:0] rel=0,hr_idx=0; reg [2:0] hr_tag=0; reg [255:0] hr_d=0;
 wire [5:0] ck_hash={6{ck}} & (mutant==1?6'b111110:6'b111111);
 wire [5:0] ck_rows={6{ck}} & (mutant==2?6'b111110:6'b111111);
 wire aw,bw,ahv,bhv,aov,bov,asv,bsv,asbad,bsbad,af,bf;
 wire [30:0] aha,bha; wire [2:0] aht,bht,aob,bob,aos,bos,ass,bss;
 wire [4:0] aoc,boc; wire [263:0] aod,bod;
 dsfd_engram_lkp #(.PIPE(1),.NSLOT(8)) reference (
 .ck(ck),.rst_n(rst_n),.cfg_layer(cfg_layer),.cfg_rank(cfg_rank),.win_v(win_v),.win_ids(win_ids),.win_cred(aw),.rel(rel),
 .hq_v(ahv),.hq_atom(aha),.hq_tag(aht),.hq_cred(hq_cred),.hr_v(hr_v),.hr_tag(hr_tag),.hr_idx(hr_idx),.hr_d(hr_d),
 .o_v(aov),.o_col(aoc),.o_beat(aob),.o_slot(aos),.o_d(aod),.o_cred(o_cred),.st_v(asv),.st_slot(ass),.st_bad(asbad),.fault(af));
 dsfd_engram_lkp_clock_roots #(.PIPE(1),.NSLOT(8)) candidate (
 .ck(ck),.ck_hash(ck_hash),.ck_rows(ck_rows),.rst_n(rst_n),.cfg_layer(cfg_layer),.cfg_rank(cfg_rank),.win_v(win_v),.win_ids(win_ids),.win_cred(bw),.rel(rel),
 .hq_v(bhv),.hq_atom(bha),.hq_tag(bht),.hq_cred(hq_cred),.hr_v(hr_v),.hr_tag(hr_tag),.hr_idx(hr_idx),.hr_d(hr_d),
 .o_v(bov),.o_col(boc),.o_beat(bob),.o_slot(bos),.o_d(bod),.o_cred(o_cred),.st_v(bsv),.st_slot(bss),.st_bad(bsbad),.fault(bf));
 integer cycles=0,phase,win=0,requests=0,beats=0,statuses=0,mutant=0,i;
 initial begin if($value$plusargs("MUTANT=%d",mutant)) begin end end
 always @(negedge ck) begin
  cycles=cycles+1; phase=cycles%2048;
  rst_n=cycles>5; cfg_layer=((cycles/2048)/4)%2; cfg_rank=(cycles/2048)%4;
  win_v=cycles>20 && phase==40;
  if(win_v) for(i=0;i<4;i=i+1) win_ids[ENG_ID_W*i+:ENG_ID_W]=$urandom;
  hq_cred=ahv; o_cred=aov; rel=phase==1500?4'b1111:4'b0000;
  hr_v=phase>=200 && phase<254;
  if(hr_v) begin hr_tag=(phase-200)/9;hr_idx=(phase-200)%9;for(i=0;i<8;i=i+1)hr_d[32*i+:32]=$urandom;end
 end
 always @(posedge ck) begin
  #0.1;
  if(rst_n && cycles>10) begin
   if({aw,ahv,aov,asv,af} !== {bw,bhv,bov,bsv,bf}) $fatal(1,"CLOCK_ROOT_EQ control mismatch cycle%0d mutant%0d",cycles,mutant);
   if(af || bf) $fatal(1,"CLOCK_ROOT_EQ unexpected fault cycle%0d",cycles);
   if(ahv) begin requests=requests+1;if({aha,aht} !== {bha,bht})$fatal(1,"CLOCK_ROOT_EQ request mismatch cycle%0d mutant%0d",cycles,mutant);end
   if(aov) begin beats=beats+1;if({aoc,aob,aos,aod} !== {boc,bob,bos,bod})$fatal(1,"CLOCK_ROOT_EQ beat mismatch cycle%0d mutant%0d",cycles,mutant);end
   if(asv) begin statuses=statuses+1;if({ass,asbad} !== {bss,bsbad})$fatal(1,"CLOCK_ROOT_EQ status mismatch cycle%0d mutant%0d",cycles,mutant);end
   if(aw)win=win+1;
  end
  if(cycles==24*2048-1) begin
   if(win!=24 || requests!=144 || beats!=1152 || statuses!=144)$fatal(1,"CLOCK_ROOT_EQ insufficient actual coverage windows%0d requests%0d beats%0d status%0d",win,requests,beats,statuses);
   if(mutant!=0)$fatal(1,"CLOCK_ROOT_EQ mutant survived");
   $display("CLOCK_ROOT_EQ PASS windows=%0d requests=%0d beats=%0d status=%0d all8layer_rank_straps roots=13",win,requests,beats,statuses);$finish;
  end
 end
endmodule
