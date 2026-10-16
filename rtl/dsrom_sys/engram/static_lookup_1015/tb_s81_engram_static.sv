`timescale 1ns/1ps
import ot_hdc_engram_tables_shipped_pkg::*;
module tb_s81_engram_static;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,wv=0,hv=0;reg [67:0] ids=0;reg [2:0] ht=0;reg [3:0] hi=0;
 reg [255:0] hd=0;reg [2:0] slot=0,hs=0;reg layer=0;reg[1:0] rank=0;
 reg [255:0] memory[0:5][0:8];
 reg [7:0] rowbytes[0:271];
 reg [31:0] crc;integer j,k,off,byteidx,bitidx;
 integer mut=0,cycle=0,phase,windows=0,areq=0,breq=0,an=0,bn=0,ast=0,bst=0,i;
 wire [5:0] ch={6{clk}} & (mut==1?6'b111110:6'b111111);
 wire [5:0] cr={6{clk}} & (mut==2?6'b111110:6'b111111);
 wire av,bv,asv,bsv,ab,bb,af,bf,ah,bh;wire [30:0] aa,ba;wire[2:0]at,bt;
 wire [4:0]ac,bc;wire[2:0]ak,bk,asl,bsl;wire[263:0]ad,bd;
 wire wr;
 ot_dsrom_engram_lookup #(.PIPE(1),.NSLOT(8)) reference(
 .clk(clk),.rst_n(rst_n),.cfg_layer(layer),.cfg_rank(rank),.win_valid(wv),.win_ready(wr),.win_ids(ids),.rel_valid(phase==220?4'b1111:4'b0000),
 .hq_valid(ah),.hq_ready(1'b1),.hq_atom(aa),.hq_len(),.hq_tag(at),
 .hr_valid(hv),.hr_ready(),.hr_tag(ht),.hr_idx(hi),.hr_data(hd),
 .o_valid(av),.o_ready(1'b1),.o_col(ac),.o_beat(ak),.o_slot(asl),.o_data(ad),.st_valid(asv),.st_slot(),.st_bad(ab),.fault(af));
 ot_s81_engram_lookup_static #(.PIPE(1),.NSLOT(8),.RETURN_AGE(128)) candidate(
 .clk(clk),.clk_seed(clk && mut!=7),.clk_hash(ch),.clk_rows(cr),.rst_n(rst_n),.cfg_layer(layer),.cfg_rank(rank),.win_valid(wv),.win_slot(slot),.win_ids(ids),
 .hq_valid(bh),.hq_atom(ba),.hq_len(),.hq_tag(bt),
 .hr_valid(hv),.hr_slot(hs),.hr_tag(ht),.hr_idx(hi),.hr_data(hd),
 .o_valid(bv),.o_col(bc),.o_beat(bk),.o_slot(bsl),.o_data(bd),.st_valid(bsv),.st_slot(),.st_bad(bb),.fault(bf));
 reg [271:0] expected[0:2047];reg [33:0] reqs[0:255];
 initial begin if($value$plusargs("MUT=%d",mut))begin end end
 always @(negedge clk)begin
  cycle=cycle+1;phase=cycle%256;rst_n=cycle>5;
  layer=(cycle/256/4)%2;rank=(cycle/256)%4;slot=(cycle/256)%8;hs=slot;
  wv=phase==20;if(wv)begin windows=windows+1;for(i=0;i<4;i=i+1)ids[i*17+:17]=$urandom;end
  if(phase==50) for(j=0;j<6;j=j+1)begin
   crc=32'hffffffff;
   for(k=0;k<264;k=k+1)begin
    rowbytes[k]=(j*37+k*11+cycle/256)&255;
    for(bitidx=7;bitidx>=0;bitidx=bitidx-1)
     crc={crc[30:0],1'b0}^((crc[31]^rowbytes[k][bitidx])?32'h04c11db7:32'd0);
   end
   for(k=0;k<4;k=k+1)rowbytes[264+k]=crc[k*8+:8];
   for(k=268;k<272;k=k+1)rowbytes[k]=0;
   // True memory fixture: byte placement uses the reference request address,
   // not the candidate's return selection. Independently check decoded words.
   off=reference.baddr[j][4:0];
   for(k=0;k<9;k=k+1)memory[j][k]=0;
   for(k=0;k<272;k=k+1)begin byteidx=k+off;memory[j][byteidx/32][8*(byteidx%32)+:8]=rowbytes[k];end
  end
  hv=phase>=60&&phase<114;
  ht=(phase-60)/9;hi=(phase-60)%9;
  if(mut==3&&phase==63)hv=0;
  if(mut==4&&phase==63)hs=slot^1;
  if(mut==5&&phase==64)hi=3;
  if(mut==6&&phase==64)begin rst_n=0;end
  hd=hv?memory[ht][hi]:0;
 end
 always @(posedge clk)begin
  #0.1;
  if(rst_n)begin
   if(ah)begin reqs[areq]={aa,at};areq=areq+1;end
   if(bh)begin if(breq>=areq||{ba,bt}!==reqs[breq])$fatal(1,"STATIC request mismatch cycle%0d a%0d b%0d got%h expected%h",cycle,areq,breq,{ba,bt},reqs[breq]);breq=breq+1;end
   if(av)begin expected[an]={ac,ak,ad};an=an+1;end
   if(bv)begin
    if(bn>=an||{bc,bk,bd}!==expected[bn]||bsl!==((bn/48)%8))$fatal(1,"STATIC beat mismatch cycle%0d beat%0d",cycle,bn);
    if(phase!=153+(bn%48))$fatal(1,"STATIC calendar mismatch phase%0d index%0d",phase,bn%48);
    for(i=0;i<32;i=i+1)
     if(bd[i*8+:8]!==((bn%48/8*37+bk*32*11+i*11+cycle/256)&255))
       $fatal(1,"STATIC independent byte mismatch beat%0d byte%0d",bn,i);
    if(bd[263:256]!==((bn%48/8*37+(256+bk)*11+cycle/256)&255))
     $fatal(1,"STATIC exponent mismatch");
    bn=bn+1;
   end
   if(asv)ast=ast+1;
   if(bsv)begin bst=bst+1;if(bb)$fatal(1,"STATIC unexpected poison mismatch");end
  end
  if(cycle==16*256-1)begin
   if(windows!=16||areq!=96||breq!=96||an!=768||bn!=768||ast!=96||bst!=96)$fatal(1,"STATIC coverage missing a%0d b%0d",an,bn);
   if(mut!=0)$fatal(1,"STATIC mutant survived");
   $display("STATIC PASS windows16 requests96 outputs768 statuses96 all8straps fixed_return_age128");$finish;
  end
 end
endmodule
