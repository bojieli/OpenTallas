`timescale 1ns/1ps
module tb_hgi_vm_wide_bank #(parameter integer TEST_MUT=0);
 localparam integer MUT=0; // independent golden always correct, regardless DUT mutation
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0,w_v=0,r_v=0;wire w_rdy,r_rdy;
 reg[7:0]w_addr=0,r_addr=0,w_mask=0;reg[255:0]w_data=0;
 reg[19:0]w_tag=0,r_tag=0;wire w_done,r_done;
 wire[19:0]w_done_tag,r_done_tag;wire[255:0]r_data;wire[3:0]r_ce;wire r_ue,fault;
 reg inj_v=0;reg[2:0]inj_word=0;reg[38:0]inj_mask=0;
 ot_hgi_vm_wide_bank #(.ENABLE(1),.MUT(TEST_MUT)) dut(.*);
 wire off_wr,off_rr,off_wd,off_rd,off_fault;
 ot_hgi_vm_wide_bank disabled(.clk(clk),.rst_n(rst_n),.w_v(w_v),.w_rdy(off_wr),.w_addr(w_addr),.w_data(w_data),.w_mask(w_mask),.w_tag(w_tag),
 .w_done(off_wd),.r_v(r_v),.r_rdy(off_rr),.r_addr(r_addr),.r_tag(r_tag),.r_done(off_rd),.fault(off_fault),.inj_v(1'b0),.inj_word(3'd0),.inj_mask(39'd0));
    function automatic [6:0] chk(input [31:0] d);
        integer i; reg [6:0] c; reg [6:0] col;
        begin
            c = 7'd0;
            for (i = 0; i < 32; i = i + 1) begin
                col = colv(i);
                if (d[i]) c = c ^ col;
            end
            chk = c;
        end
    endfunction
    // column of data bit i: the i-th 7-bit vector with 3 ones (35 of them; the first 32 used)
    function automatic [6:0] colv(input integer i);
        integer a, b, c, n; reg [6:0] v;
        begin
            n = 0; v = 7'd0;
            for (a = 0; a < 7; a = a + 1)
                for (b = a + 1; b < 7; b = b + 1)
                    for (c = b + 1; c < 7; c = c + 1) begin
                        if (n == i) v = (7'd1 << a) | (7'd1 << b) | (7'd1 << c);
                        n = n + 1;
                    end
            colv = v;
        end
    endfunction
    function automatic [38:0] enc(input [31:0] d);
        enc = {chk(d), d};
    endfunction
    // decode: {ue, ce, corrected data}
    function automatic [33:0] dec(input [38:0] w);
        reg [6:0] syn; integer i; reg [31:0] d; reg hit;
        begin
            d = w[31:0]; syn = chk(w[31:0]) ^ w[38:32]; hit = 1'b0;
            if (syn != 7'd0) begin
                for (i = 0; i < 32; i = i + 1) if (syn == colv(i)) begin d[i] = ~d[i]; hit = 1'b1; end
                // a check-bit error (weight-1 syndrome) leaves the data correct
                if (syn == 7'd1 || syn == 7'd2 || syn == 7'd4 || syn == 7'd8 || syn == 7'd16 || syn == 7'd32 || syn == 7'd64) hit = 1'b1;
            end
            dec = {(syn != 7'd0) && !hit, (syn != 7'd0) && hit, (MUT == 1) ? w[31:0] : d};
        end
    endfunction

 localparam integer NT=4096;
 reg[38:0]mem[0:255][0:7];reg[311:0]wc[0:NT-1];reg[7:0]wm[0:NT-1],addr[0:NT-1],raddr[0:NT-1];
 integer wcommit[0:NT-1],wack[0:NT-1],readedge[0:NT-1],rack[0:NT-1];
 reg[255:0]expected[0:NT-1];reg[3:0]expectedce[0:NT-1];reg expectedue[0:NT-1];
 reg last_wa=0,last_ra=0;
 integer cycle=0,nwa=0,nra=0,nwd=0,nrd=0,lastw=-99,lastr=-99,nexttag=1;
 integer a,b,t;reg[33:0]d;
 initial begin
  for(a=0;a<256;a=a+1)for(b=0;b<8;b=b+1)mem[a][b]=enc(32'd0);
  for(t=0;t<NT;t=t+1)begin wcommit[t]=-1;wack[t]=-1;readedge[t]=-1;rack[t]=-1;end
 end
 always @(posedge clk)if(rst_n)begin
  cycle=cycle+1;last_wa=w_v&&w_rdy;last_ra=r_v&&r_rdy;
  // Actual macro read-before-write ordering, not request acceptance ordering.
  for(t=1;t<nexttag;t=t+1)if(readedge[t]==cycle)begin
   expected[t]=0;expectedce[t]=0;expectedue[t]=0;
   for(b=0;b<8;b=b+1)begin d=dec(mem[raddr[t]][b]);expected[t][b*32+:32]=d[31:0];expectedce[t]=expectedce[t]+4'(d[32]);expectedue[t]=expectedue[t]|d[33];end
  end
  for(t=1;t<nexttag;t=t+1)if(wcommit[t]==cycle)for(b=0;b<8;b=b+1)if(wm[t][b])mem[addr[t]][b]=wc[t][b*39+:39];
  if(w_v&&w_rdy)begin
   if(cycle-lastw<2)$fatal(1,"WRITE_II");lastw=cycle;nwa=nwa+1;
   if(w_tag>=NT||wack[w_tag]!=-1)$fatal(1,"WRITE_TAG");
   addr[w_tag]=w_addr;wm[w_tag]=w_mask;wcommit[w_tag]=cycle+3;wack[w_tag]=cycle+4;
   for(b=0;b<8;b=b+1)begin wc[w_tag][b*39+:39]=enc(w_data[b*32+:32]);if(inj_v&&inj_word==b)wc[w_tag][b*39+:39]=wc[w_tag][b*39+:39]^inj_mask;end
  end
  if(r_v&&r_rdy)begin
   if(cycle-lastr<2)$fatal(1,"READ_II");lastr=cycle;nra=nra+1;
   if(r_tag>=NT||rack[r_tag]!=-1)$fatal(1,"READ_TAG");
   raddr[r_tag]=r_addr;readedge[r_tag]=cycle+1;rack[r_tag]=cycle+5;
  end
  #0.05;
  if({off_wr,off_rr,off_wd,off_rd,off_fault}!==5'd0)$fatal(1,"DEFAULT_OFF");
  if(^({w_done,r_done,w_done_tag,r_done_tag,r_data,r_ce,r_ue,fault})===1'bx)$fatal(1,"OUTPUT_X");
  if(w_done)begin
   if(wack[w_done_tag]!=cycle)$fatal(1,"WRITE_ACK_TIME_OR_ID cycle%0d tag%0d due%0d",cycle,w_done_tag,wack[w_done_tag]);
   wack[w_done_tag]=-2;nwd=nwd+1;
  end
  if(r_done)begin
   if(rack[r_done_tag]!=cycle)$fatal(1,"READ_RESPONSE_TIME_OR_ID");
   if(r_data!==expected[r_done_tag]||r_ce!==expectedce[r_done_tag]||r_ue!==expectedue[r_done_tag])$fatal(1,"READ_EXACT tag%0d CE%0d/%0d UE%0d/%0d",r_done_tag,r_ce,expectedce[r_done_tag],r_ue,expectedue[r_done_tag]);
   rack[r_done_tag]=-2;nrd=nrd+1;
  end
 end
 function automatic[255:0]pattern(input integer row,input integer salt);
  integer i;begin for(i=0;i<8;i=i+1)pattern[i*32+:32]=(32'h9e3779b9*(row+1))^(32'h85ebca6b*(i+salt+1));end
 endfunction
 task write_sector(input[7:0]row,input[255:0]data,input[7:0]mask,input bit inject,input[2:0]word,input[38:0]flip);
 begin
  @(negedge clk);while(!w_rdy)@(negedge clk);
  w_addr=row;w_data=data;w_mask=mask;w_tag=20'(nexttag);nexttag=nexttag+1;inj_v=inject;inj_word=word;inj_mask=flip;w_v=1;
  @(negedge clk);w_v=0;inj_v=0;
 end endtask
 task read_sector(input[7:0]row);
 begin
  @(negedge clk);while(!r_rdy)@(negedge clk);
  r_addr=row;r_tag=20'(nexttag);nexttag=nexttag+1;r_v=1;
  @(negedge clk);r_v=0;
 end endtask
 task drain;
 begin repeat(10)@(negedge clk);if(nwd!=nwa||nrd!=nra)$fatal(1,"DROP W%0d/%0d R%0d/%0d",nwd,nwa,nrd,nra);end
 endtask
 integer row,bitno,stream_count;
 initial begin
  repeat(4)@(negedge clk);rst_n=1;
  // Entire actual physical depth, masked sectors (including word6 crossing macro boundary).
  for(row=0;row<256;row=row+1)write_sector(8'(row),pattern(row,0),8'hff,0,0,0);
  drain;
  for(row=0;row<256;row=row+1)write_sector(8'(row),pattern(row,13),8'(row),0,0,0);
  drain;
  for(row=0;row<256;row=row+1)read_sector(8'(row));
  drain;
  // Continuous valid: retain all producer fields on withheld ready; normal acceptance II2.
  @(negedge clk);w_v=1;w_addr=200;w_data=pattern(200,31);w_mask=8'hff;w_tag=20'(nexttag);nexttag=nexttag+1;stream_count=0;
  while(stream_count<16)begin
   @(negedge clk);
   if(last_wa)begin
    stream_count=stream_count+1;
    if(stream_count==16)w_v=0;
    else begin w_addr=8'(200+stream_count);w_data=pattern(200+stream_count,31);w_tag=20'(nexttag);nexttag=nexttag+1;end
   end
  end
  drain;
  @(negedge clk);r_v=1;r_addr=200;r_tag=20'(nexttag);nexttag=nexttag+1;stream_count=0;
  while(stream_count<16)begin
   @(negedge clk);
   if(last_ra)begin
    stream_count=stream_count+1;
    if(stream_count==16)r_v=0;
    else begin r_addr=8'(200+stream_count);r_tag=20'(nexttag);nexttag=nexttag+1;end
   end
  end
  drain;
  // Simultaneous independent ports plus upstream held-valid stalls.
  fork
   begin for(integer x=0;x<24;x=x+1)write_sector(8'(x+64),pattern(x,7),8'hff,0,0,0);end
   begin for(integer x=0;x<24;x=x+1)read_sector(8'(x+128));end
  join
  drain;
  // Same accept edge RW observes old value; independent ports truly operate together.
  @(negedge clk);while(!w_rdy||!r_rdy)@(negedge clk);
  w_addr=255;w_data=pattern(255,21);w_mask=8'hff;w_tag=20'(nexttag);nexttag=nexttag+1;w_v=1;
  r_addr=255;r_tag=20'(nexttag);nexttag=nexttag+1;r_v=1;
  @(negedge clk);w_v=0;r_v=0;drain;
  // A held-valid read of an older accepted write must stall until actual publication.
  @(negedge clk);while(!w_rdy)@(negedge clk);
  w_addr=254;w_data=pattern(254,23);w_mask=8'hff;w_tag=20'(nexttag);nexttag=nexttag+1;w_v=1;
  @(negedge clk);w_v=0;r_addr=254;r_tag=20'(nexttag);nexttag=nexttag+1;r_v=1;
  #0.01;if(r_rdy)$fatal(1,"RAW_MISSING_RESERVATION");
  while(!r_rdy)@(negedge clk);
  @(negedge clk);r_v=0;drain;
  // All39 single-bit positions corrected in a boundary-crossing word.
  for(bitno=0;bitno<39;bitno=bitno+1)begin
   write_sector(250,pattern(bitno,9),8'hff,1,6,39'd1<<bitno);drain;read_sector(250);drain;
  end
  // Every protected word contributes to CE count (8) without losing exact data.
  for(row=0;row<8;row=row+1)write_sector(251,pattern(251,9),8'd1<<row,1,3'(row),39'd1);
  drain;read_sector(251);drain;
  if(fault)$fatal(1,"UNEXPECTED_FAULT");
  write_sector(252,pattern(252,9),8'hff,1,3,39'd3);drain;read_sector(252);drain;
  if(!fault||w_rdy||r_rdy)$fatal(1,"UE_NOT_FAIL_CLOSED");
  $display("BANK_DATA_PASS W%0d R%0d physical_rows256 ECC_single39 CE8 UEdrain actual_write5edges_4elapsed read6edges_5elapsed II2",nwd,nrd);
  // Single mutable identity-rail corruption must stop admission before macro commit and emit no success ACK.
  @(negedge clk);rst_n=0;repeat(3)@(negedge clk);rst_n=1;
  @(negedge clk);w_addr=10;w_data=pattern(10,17);w_mask=8'hff;w_tag=20'(nexttag);nexttag=nexttag+1;w_v=1;
  @(negedge clk);w_v=0;dut.wm_n[0]=dut.wm_n[0]^36'd1;
  repeat(8)begin @(negedge clk);if(w_done||r_done)$fatal(1,"CONTROL_FAULT_SUCCESS");end
  if(!fault||w_rdy||r_rdy)$fatal(1,"CONTROL_FAULT_NOT_CLOSED");
  $display("BANK_PASS control_railfault_rejected defaultOFF noX");$finish;
 end
endmodule
