`timescale 1ns/1ps
module tb_selector_link_static;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[3:0]op=0;reg[1:0]pass=0;reg[7:0]addr=0;reg[9:0]k=512;
 reg[2367:0]in_line=0;wire[3:0]out_v;wire[2367:0]out_line;wire fault;
 wire[3:0]selected_v;wire[2367:0]selected_line;
 wire[15:0]threshold_observe;wire[55:0]selected_observe;
 ot_hbm_idx_selector_static #(.MUT(0)) dut(.clk_ctl(clk),.clk_q({4{clk}}),.clk_mem({12{clk}}),.*);
 reg[2367:0]lines[0:170];reg gold[0:10943];reg[15:0]scores[0:10943];reg seen[0:10943];
 integer errors=0,checked=0,frame,cyc=0,firstemit,beginframe;string fn;
 reg clear=0,flush=0,emit_v=0;reg[3:0]emit_group=0;
 wire[3:0]tx_v;wire[2179:0]tx;wire link_fault;wire[9:0]selected_count;
 ot_hbm_idx_topk_link_static #(.MUT(MUT))link(.clk(clk),.clk_mem({8{clk}}),.rst_n(rst_n),.clear(clear),
  .ingest_v(&selected_v),.selected_line(selected_line),.flush(flush),.emit_v(emit_v),.emit_group(emit_group),.rank(8'd3),.gbase(8'd1),
  .tx_v(tx_v),.tx(tx),.fault(link_fault),.selected_count(selected_count));
 integer flits=0,records=0,lasttx=-1,firsttx=-1;
 reg linkseen[0:10943];
 always @(posedge clk)cyc<=cyc+1;
 task automatic tick(input integer o,input integer a,input integer p);
  begin @(negedge clk);op=4'(o);addr=8'(a);pass=2'(p);end
 endtask
 always @(negedge clk)begin
  if(|tx_v)begin
   if(firsttx<0)firsttx=cyc;
   if(lasttx>=0&&cyc-lasttx!=8)errors++;
   lasttx=cyc;
   for(integer lane=0;lane<4;lane=lane+1)begin
    if(!tx_v[lane])errors++;
    if(tx[lane*545+544]!==1'b1||tx[lane*545+536+:8]!==8'hff||tx[lane*545+528+:8]!==8'd3||
     tx[lane*545+512+:16]!==16'(128+flits))errors++;
    flits++;
    for(integer r=0;r<8;r=r+1)begin
     integer id;reg[31:0]val;
     id=int'(tx[lane*545+256+r*32+:32]);val=tx[lane*545+r*32+:32];records++;
     if(id>=10944)errors++;
     else begin if(!gold[id]||linkseen[id]||val!=={scores[id],16'd0})errors++;linkseen[id]=1;end
    end
   end
  end
  for(integer q=0;q<4;q=q+1)if(out_v[q])begin
   if(firstemit<0)firstemit=cyc;
   for(integer l=0;l<16;l=l+1)if(out_line[q*592+l*37])begin
    integer id;id=int'(out_line[q*592+l*37+17+:20]);checked++;
    if(id>=10944)errors++;
    else begin
     if(!gold[id]||seen[id]||scores[id]!==out_line[q*592+l*37+1+:16])begin errors++;if(errors<8)$display("bad id%0d frame%0d",id,frame);end
     seen[id]=1;
    end
   end
  end
 end
 initial begin
  repeat(4)@(negedge clk);rst_n=1;
  for(frame=0;frame<3;frame=frame+1)begin
   fn=$sformatf("lines%0d.hex",frame);$readmemh(fn,lines);
   fn=$sformatf("gold%0d.hex",frame);$readmemh(fn,gold);
   fn=$sformatf("scores%0d.hex",frame);$readmemh(fn,scores);
   for(integer j=0;j<10944;j=j+1)begin seen[j]=0;linkseen[j]=0;end
   checked=0;flits=0;records=0;lasttx=-1;firsttx=-1;firstemit=-1;beginframe=cyc;
   clear=1;tick(0,0,0);clear=0;
   tick(1,0,0);tick(3,0,0);
   for(integer a=0;a<171;a=a+1)begin tick(2,a,0);in_line=lines[a];end
   tick(0,0,0);tick(0,0,0);
   for(integer b=31;b>=0;b=b-1)tick(5,b,0);
   tick(0,0,0);
   for(integer p=1;p<3;p=p+1)begin
    tick(3,0,p);
    for(integer a=0;a<171;a=a+1)tick(4,a,p);
    tick(0,0,p);tick(0,0,p);
    for(integer b=(p==2?63:31);b>=0;b=b-1)tick(5,b,p);
    tick(0,0,p);
   end
   for(integer a=0;a<171;a=a+1)tick(6,a,2);
   tick(0,0,2);tick(0,0,2);tick(7,0,2);tick(0,0,2);
   flush=1;tick(0,0,2);flush=0;
   for(integer a=0;a<16;a=a+1)begin emit_v=1;emit_group=4'(a);tick(0,0,2);emit_v=0;repeat(7)tick(0,0,2);end
   tick(0,0,2);repeat(3)tick(0,0,2);
   for(integer j=0;j<10944;j=j+1)if(gold[j]!==linkseen[j])errors++;
   if(records!=512||flits!=64||fault||link_fault||selected_count!=512)errors++;
   $display("IDX_SELECTOR_LINK_STATIC MUT%0d frame%0d records%0d errors%0d fault%0d edges%0d firstemit%0d threshold%h selected%h",MUT,frame,records,errors,fault,cyc-beginframe,firsttx-beginframe,threshold_observe,selected_observe);
  end
  if(errors)$fatal(1,"fullshape exact selector mismatch");$finish;
 end
endmodule
