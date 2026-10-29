`timescale 1ns/1ps
module tb_idx_link_wpipe;
 parameter integer MUT=0,WPIPE=2;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,clear=0,ingest_v=0,flush=0,emit_v=0;
 reg[3:0]emit_group=0;reg[2367:0]selected_line=0;
 wire[3:0]av,bv;wire[2179:0]atx,btx;wire af,bf;wire[9:0]ac,bc;
 ot_hbm_idx_topk_link_static_serial_reference refdut(.clk(clk),.clk_mem({8{clk}}),.rst_n(rst_n),.clear(clear),.ingest_v(ingest_v),
 .selected_line(selected_line),.flush(flush),.emit_v(emit_v),.emit_group(emit_group),.rank(8'd3),.gbase(8'd1),.tx_v(av),.tx(atx),.fault(af),.selected_count(ac));
 ot_hbm_idx_topk_link_static_core #(.MUT(MUT),.WRITE_PIPE_STAGES(WPIPE)) dut(.clk(clk),.clk_mem({8{clk}}),.rst_n(rst_n),.clear(clear),.ingest_v(ingest_v),
 .selected_line(selected_line),.flush(flush),.emit_v(emit_v),.emit_group(emit_group),.rank(8'd3),.gbase(8'd1),.tx_v(bv),.tx(btx),.fault(bf),.selected_count(bc));
 integer cycle=0,errors=0,miter=0,records=0,flits=0,total_records=0,frame=0,issued=0;
 integer write_vectors_checked=0;
 reg[7:0]hw0,hw1;reg[47:0]ha0,ha1;reg[4095:0]hd0,hd1;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin hw0<=0;hw1<=0;end
  else if(clear)begin hw0<=0;hw1<=0;end
  else begin hw0<=refdut.we;hw1<=hw0;end
 end
 always @(posedge clk)begin
  ha0<=refdut.wa;ha1<=ha0;hd0<=refdut.wd;hd1<=hd0;
  if(rst_n&&!clear&&WPIPE==2)begin
   if(dut.mem_we!==hw1)begin errors++;if(errors<5)$display("PIPE_WE_MITER cycle%0d",cycle);end
   for(integer b=0;b<8;b=b+1)if(hw1[b])begin
    write_vectors_checked++;
    if(dut.mem_wa[b*6+:6]!==ha1[b*6+:6]||dut.mem_wd[b*512+:512]!==hd1[b*512+:512])begin errors++;if(errors<5)$display("PIPE_ADDR_DATA_MITER cycle%0d bank%0d",cycle,b);end
   end
  end
 end
 reg[63:0]gold[0:511];reg due[0:4095];
 always @(posedge clk)cycle<=cycle+1;
 always @(negedge clk)if(rst_n)begin
  miter++;
  if({av,af,ac}!={bv,bf,bc} || ((|av)&&atx!==btx))begin errors++;if(errors<5)$display("TREE_MITER cycle%0d",cycle);end
  if(bv!=={4{due[cycle]}})begin errors++;if(errors<5)$display("TREE_TIMELINE cycle%0d",cycle);end
  if(|bv)for(integer l=0;l<4;l=l+1)begin
   if(btx[l*545+512+:16]!==16'(128+flits))errors++;flits++;
   for(integer r=0;r<8;r=r+1)begin
    reg[63:0]rec;rec={btx[l*545+256+r*32+:32],btx[l*545+r*32+:32]};
    if(records>=512 || rec!==gold[records])begin errors++;if(errors<5)$display("TREE_RECORD frame%0d record%0d expected%h got%h",frame,records,gold[records],rec);end
    records++;total_records++;
   end
  end
 end
 initial begin
  for(integer i=0;i<4096;i=i+1)due[i]=0;
  repeat(4)@(negedge clk);rst_n=1;
  for(frame=0;frame<4;frame=frame+1)begin
   if(frame==2)begin rst_n=0;repeat(4)@(negedge clk);rst_n=1;repeat(2)@(negedge clk);end
   clear=1;@(negedge clk);if(frame==1)@(negedge clk);clear=0;issued=0;records=0;flits=0;
   for(integer beat=0;beat<171;beat=beat+1)begin
    selected_line=0;ingest_v=1;
    for(integer j=0;j<64;j=j+1)begin
     reg chosen;reg[15:0]score;integer id;
     chosen=(frame==0)||(frame==3?(beat<168?j<3:(beat==170&&j<8)):(frame==2?(beat%2==0?j==0:j<63):((beat*17+j*13+frame*11)%23)<(frame+1)));
     if(chosen&&issued<512)begin
      id=frame==3?((issued*371)^20'hf5a5a):frame*1024+issued;score=frame==0?16'hffff:16'(16'h3f00+((issued*17)%127));
      selected_line[j*37+:37]={20'(id),score,1'b1};gold[issued]={32'(id),score,16'd0};issued++;
     end
    end
    @(negedge clk);
   end
   ingest_v=0;selected_line=0;repeat(3)@(negedge clk);flush=1;@(negedge clk);flush=0;repeat(1)@(negedge clk);
   for(integer g=0;g<16;g=g+1)begin
    emit_v=1;emit_group=4'(g);due[cycle+2]=1;@(negedge clk);emit_v=0;repeat(7)@(negedge clk);
   end
   repeat(4)@(negedge clk);
   if(issued!=512||records!=512||flits!=64||af||bf||bc!=512)errors++;
   $display("IDX_LINK_TREE frame%0d MUT%0d records%0d flits%0d errors%0d fault%0d",frame,MUT,records,flits,errors,bf);
  end
  $display("IDX_LINK_WPIPE_TOTAL WPIPE%0d MUT%0d records%0d miter%0d write_vectors%0d errors%0d",WPIPE,MUT,total_records,miter,write_vectors_checked,errors);
  if(errors)$fatal(1,"dense compaction exact/miter/timeline mismatch");
  $display("IDX_LINK_WPIPE PASS");$finish;
 end
endmodule
