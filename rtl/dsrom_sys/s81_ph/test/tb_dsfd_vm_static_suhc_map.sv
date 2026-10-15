`timescale 1ns/1ps
// Component boundaries only: native address pins and returned row data are
// external stimuli. Does not replace internal memory in a chip qualification.
module tb_dsfd_vm_static_suhc_map;
 reg ck=0;always #2 ck=~ck;reg rn=0;
 reg [17:0] iv=0;reg [251:0] ir=0;reg [89:0] islot=0;reg [2:0] ig=0;
 wire [31:0] ov;wire [287:0] oa;wire [255:0] ot;wire fault;
 dsfd_vm_static_suhc_fsr fsr(.ck(ck),.rst_n(rn),.i_v(iv),.i_row(ir),.i_slot(islot),.i_group(ig),
 .i_aux_v(12'd0),.i_aux_row(168'd0),.o_v(ov),.o_addr(oa),.o_tag(ot),.fault(fault));
 reg [31:0] mv=0;reg [4095:0] md=0;reg [17:0] expected=0;reg [89:0] select_slot=0;
 wire [17:0] mapped_v;wire [2303:0] mapped_data;wire mapped_fault;
 dsfd_vm_static_suhc_return_map map(.i_v(mv),.i_data(md),.expected_v(expected),.release_slot(select_slot),
 .o_v(mapped_v),.o_data(mapped_data),.fault(mapped_fault));
 reg [17:0] hv[0:9];reg [251:0] hr[0:9];reg [89:0] hs[0:9];reg [2:0] hg[0:9];
 integer cnt[0:31],rcnt[0:31];reg [31:0] ev;reg [287:0] ea;reg [255:0] et;
 reg [17:0] em;reg sticky=0,release_bad;integer bank,row,slot;
 function automatic [127:0] value(input integer r,input integer p);
 value={32'(r*771+p),32'(r*271+p*17),32'(r*127+p*31),32'(r*31+p*77)};
 endfunction
 integer fd,rc,cy,src,r,s,g,bad=0,requests=0,accepted=0,collision_buckets=0,restored=0;
 string path;
 task next_event;begin rc=$fscanf(fd,"%d %d %d %d %d\n",cy,src,r,s,g);end endtask
 initial begin
  if(!$value$plusargs("TRACE=%s",path))$fatal(1,"TRACE required");
  fd=$fopen(path,"r");if(!fd)$fatal(1,"missing trace");next_event();
  for(integer k=0;k<10;k=k+1)hv[k]=0;
  #9;rn=1;repeat(4)@(negedge ck);
  for(integer c=0;c<36020;c=c+1)begin
   @(negedge ck);iv=0;
   while(rc==5 &&cy==c)begin
    if(iv[src])$fatal(1,"duplicate native source");
    iv[src]=1;ir[14*src+:14]=r;islot[5*src+:5]=s;ig=g;requests=requests+1;next_event();
   end
   ev=0;ea=0;et=0;mv=0;md=0;expected=hv[9];select_slot=hs[9];em=0;release_bad=0;
   for(integer b=0;b<32;b=b+1)begin cnt[b]=0;rcnt[b]=0;end
   for(integer p=0;p<18;p=p+1)begin
    if(hv[0][p])begin row=hr[0][14*p+:14];bank=(row%32)^(((row/32)%8)*4);cnt[bank]=cnt[bank]+1;end
    if(hv[9][p])begin row=hr[9][14*p+:14];bank=(row%32)^(((row/32)%8)*4);rcnt[bank]=rcnt[bank]+1;end
   end
   for(integer b=0;b<32;b=b+1)if(cnt[b]>1)begin collision_buckets=collision_buckets+1;sticky=1;end
   for(integer p=0;p<18;p=p+1)begin
    if(hv[0][p])begin
     row=hr[0][14*p+:14];bank=(row%32)^(((row/32)%8)*4);slot=hs[0][5*p+:5];
     ea[9*bank+:9]=ea[9*bank+:9]|9'(row/32);et[8*bank+:8]=et[8*bank+:8]|{hg[0],5'(slot)};
     if(cnt[bank]==1)begin ev[bank]=1;accepted=accepted+1;end
    end
    if(hv[9][p])begin
     row=hr[9][14*p+:14];bank=(row%32)^(((row/32)%8)*4);slot=hs[9][5*p+:5];
     md[128*slot+:128]=value(row,p);
     if(rcnt[bank]==1)begin mv[slot]=1;em[p]=1;end else release_bad=1;
    end
   end
   #0.1;
   if(mapped_v!==em ||mapped_fault!==release_bad)bad=bad+1;
   for(integer p=0;p<18;p=p+1)if(em[p])begin
    restored=restored+1;if(mapped_data[128*p+:128]!==value(hr[9][14*p+:14],p))bad=bad+1;
   end
   @(posedge ck);#0.1;
   if(ov!==ev ||fault!==sticky)bad=bad+1;
   for(integer b=0;b<32;b=b+1)if(ov[b])begin
    if(oa[9*b+:9]!==ea[9*b+:9]||ot[8*b+:8]!==et[8*b+:8])bad=bad+1;
   end
   for(integer k=9;k>0;k=k-1)begin hv[k]=hv[k-1];hr[k]=hr[k-1];hs[k]=hs[k-1];hg[k]=hg[k-1];end
   hv[0]=iv;hr[0]=ir;hs[0]=islot;hg[0]=ig;
  end
  if(rc==5||accepted!=restored)bad=bad+1;
  $display("RESULT requests%0d accepted%0d restored%0d collision_buckets%0d bad%0d native_qualified0",requests,accepted,restored,collision_buckets,bad);
  if(bad==0&&requests>0)$display("PASS");else $display("FAIL");$finish;
 end
endmodule
