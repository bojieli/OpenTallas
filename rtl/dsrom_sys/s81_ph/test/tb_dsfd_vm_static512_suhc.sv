`timescale 1ns/1ps
// External address/stimulus component replay, actual on-chip VM only.
// L14 has no read-bank conflicts; other fixtures are not silently rescheduled.
module tb_dsfd_vm_static512_suhc;
 reg ck=0;always #2 ck=~ck;reg rn=0;
 reg [17:0] iv=0;reg [251:0] ir=0;reg [89:0] islot=0;reg [2:0] ig=0;
 reg [31:0] wv=0;reg [447:0] wr=0;reg [511:0] wm=0;reg [16383:0] wd=0;reg [255:0] wt=0;
 reg release_v=0;reg [2:0] release_group=0;reg [31:0] release_mask=0;
 reg prepare_v=0;reg [2:0] prepare_group=0;reg [31:0] prepare_mask=0;
 reg [17:0] expected=0;reg [89:0] release_slot=0;
 wire [71:0] nv;wire [9215:0] nd;wire [39:0] fault;wire [127:0] gv;wire [11:0] gid;
 dsfd_vm_static512_suhc mem(.ck_rscatter({16{ck}}),.ck_wcapture({128{ck}}),.ck_wscatter({16{ck}}),.ck_return({16{ck}}),
 .ck_bank({128{ck}}),.ck_relay_req({48{ck}}),.ck_relay_rsp({48{ck}}),
 .rst_rscatter_n({16{rn}}),.rst_return_n({4{rn}}),.rst_wcapture_n({128{rn}}),.rst_wscatter_n({16{rn}}),.rst_bank_n({128{rn}}),.rst_relay_n({48{rn}}),
 .native_rq_v(iv),.native_rq_row(ir),.native_rq_slot(islot),.native_rq_group(ig),
 .aux_rq_v(12'd0),.aux_rq_row(168'd0),.wq_v(wv),.wq_row(wr),.wq_mask(wm),.wq_data(wd),.wq_tag(wt),
 .release_v(release_v),.release_group(release_group),.release_mask(release_mask),
 .prepare_v(prepare_v),.prepare_group(prepare_group),.prepare_mask(prepare_mask),
 .native_expected_v(expected),.native_release_slot(release_slot),.native_v(nv),.native_data(nd),
 .group_v(gv),.group_data(),.group_id(gid),.commit_v(),.commit_addr(),.commit_mask(),.commit_tag(),.fault(fault));
 reg [17:0] hv[0:9];reg [251:0] hr[0:9];reg [89:0] hs[0:9];reg [2:0] hg[0:9];
 function automatic [31:0] value(input integer row,input integer word);
 value=32'(row*773+word*127+19);
 endfunction
 integer fd,rc,cy,src,r,s,g,bad=0,requests=0,restored=0,j,row;
 string path;
 task next_event;begin rc=$fscanf(fd,"%d %d %d %d %d\n",cy,src,r,s,g);end endtask
 initial begin
  if(!$value$plusargs("TRACE=%s",path))$fatal(1,"TRACE required");
  fd=$fopen(path,"r");if(!fd)$fatal(1,"missing trace");next_event();
  for(integer k=0;k<10;k=k+1)hv[k]=0;
  #9;rn=1;repeat(4)@(negedge ck);
  for(integer c=0;c<21000;c=c+1)begin
   @(negedge ck);iv=0;wv=0;
   if(c<512)begin
    wv='1;wm='1;
    for(integer k=0;k<32;k=k+1)begin
     row=32*c+k;j=8*(k%4)+((k/4)^(c%8));wr[14*j+:14]=row;wt[8*j+:8]=k;
     for(integer word=0;word<16;word=word+1)wd[512*j+32*word+:32]=value(row,word);
    end
   end
   while(rc==5 &&cy==c)begin
    if(iv[src])$fatal(1,"duplicate native source");
    iv[src]=1;ir[14*src+:14]=r;islot[5*src+:5]=s;ig=g;requests=requests+1;next_event();
   end
   release_v=|hv[9];release_group=hg[9];release_mask=0;
   expected=hv[9];release_slot=hs[9];
   for(integer p=0;p<18;p=p+1)if(expected[p])release_mask[hs[9][5*p+:5]]=1;
   // the same compiled descriptor one edge early (rsched stage9)
   prepare_v=|hv[8];prepare_group=hg[8];prepare_mask=0;
   for(integer p=0;p<18;p=p+1)if(hv[8][p])prepare_mask[hs[8][5*p+:5]]=1;
   @(posedge ck);#0.1;
   if(fault||nv!=={4{expected}}||gv!=={4{release_mask}})bad=bad+1;
   if(release_v&&gid!=={4{release_group}})bad=bad+1;
   for(integer p=0;p<18;p=p+1)if(expected[p])begin
    restored=restored+1;
    for(integer word=0;word<16;word=word+1)
     if(nd[512*p+32*word+:32]!==value(hr[9][14*p+:14],word))bad=bad+1;
   end
   for(integer k=9;k>0;k=k-1)begin hv[k]=hv[k-1];hr[k]=hr[k-1];hs[k]=hs[k-1];hg[k]=hg[k-1];end
   hv[0]=iv;hr[0]=ir;hs[0]=islot;hg[0]=ig;
  end
  if(rc==5)bad=bad+1;
  $display("RESULT requests%0d restored%0d bad%0d actual_SRAMs128 native_chip_qualified0",requests,restored,bad);
  if(bad==0&&requests==3857&&restored==3857)$display("PASS");else $display("FAIL");$finish;
 end
endmodule
