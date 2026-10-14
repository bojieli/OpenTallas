`timescale 1ns/1ps
module tb_hgi_coll_tkm_packer;
 parameter MUT=0,ACK_SEAM=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0,cv=0,last=0,hasr=0,ready=0;
 reg[12:0]nout;reg[39:0]ob,rb;reg[339:0]ct;reg[1:0]slot;
 reg ack=0;wire seq;
 wire wv,empty;wire[39:0]wa;wire[15:0]wm;wire[511:0]wd;wire[3:0]queued;wire[9:0]lp;
 ot_hgi_coll_tkm_packer #(.MUT(MUT),.ACK_SEAM(ACK_SEAM))dut(.clk(clk),.rst_n(rst_n),.start(start),.cfg_nout(nout),.cfg_obase(ob),.cfg_rbase(rb),.cfg_has_r(hasr),.cell_v(cv),.cell_t(ct),.cell_slot(slot),.cell_last(last),.w_rdy(ready),.w_ack(ack),.w_seq(seq),.w_v(wv),.w_addr(wa),.w_mask(wm),.w_data(wd),.queued(queued),.lines_pushed(lp),.empty(empty));
 integer run=0,cycles=0,accepted=0,checked=0,nlines,ix,ln,lane,idx,cellno,expected_lines;
 reg[31:0]prng=32'h6a77e8f1,expected;
 reg[39:0]addr_expected;reg[15:0]mask_expected;
 always @(negedge clk)begin prng={prng[30:0],prng[31]^prng[21]^prng[1]^prng[0]};ready=prng[0]|prng[4];end
 always @(posedge clk)begin
  cycles=cycles+1;
  if(cycles>50000)$fatal(1,"PACKER FAIL timeout");
  if(wv&&ready&&(!ACK_SEAM||(seq!=ack)))begin
   if(ACK_SEAM)ack<=seq;
   ln=hasr?(accepted/2):accepted;
   addr_expected=(hasr&&accepted%2)?rb+16*ln:ob+16*ln;
   mask_expected=((nout-16*ln)>=16)?16'hffff:((17'd1<<(nout-16*ln))-1);
   if(wa!==addr_expected||wm!==mask_expected)$fatal(1,"PACKER FAIL address/mask run=%0d line=%0d got=%h/%h expected=%h/%h",run,accepted,wa,wm,addr_expected,mask_expected);
   for(lane=0;lane<16;lane=lane+1)begin
    idx=16*ln+lane;
    expected=(idx>=nout)?0:((hasr&&accepted%2)?((idx%7==0)?32'h80000000:32'h3f800000):(32'h12340000+idx));
    if(wd[32*lane+:32]!==expected)$fatal(1,"PACKER FAIL payload run=%0d line=%0d lane=%0d got=%h expected=%h",run,accepted,lane,wd[32*lane+:32],expected);
    checked=checked+1;
   end
   accepted=accepted+1;
  end
 end
 initial begin
  repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
  for(run=0;run<64;run=run+1)begin
   nout=1+(run*37)%128;hasr=run%2;
   // Cross low-address carry boundaries, retaining all 40 native address bits.
   ob=40'hc71234fff0+run*16;rb=40'h1b8765fff0+run*16;
   accepted=0;nlines=(nout+15)/16;expected_lines=nlines*(hasr?2:1);
   start=1;@(negedge clk);start=0;repeat(4)@(negedge clk);
   for(cellno=0;cellno<(nout+3)/4;cellno=cellno+1)begin
    while(queued>4)@(negedge clk);
    ct=0;
    for(ix=0;ix<4;ix=ix+1)begin
     idx=4*cellno+ix;
     // Region-1 chain key: valid, ~region, ~id, ordered value, q/j, nz.
     ct[85*ix+:85]={1'b1,1'b0,~(32'h12340000+idx),32'hbf800000,18'd0,(idx%7==0)};
    end
    cv=1;slot=cellno%4;last=(cellno==(nout+3)/4-1);@(negedge clk);
   end
   cv=0;last=0;
   while(accepted<expected_lines)@(negedge clk);
   repeat(4)@(negedge clk);
   if(!empty||lp!=nlines)$fatal(1,"PACKER FAIL drain");
  end
  $display("PACKER PASS configurations=64 checked=%0d cycles=%0d",checked,cycles);$finish;
 end
endmodule
