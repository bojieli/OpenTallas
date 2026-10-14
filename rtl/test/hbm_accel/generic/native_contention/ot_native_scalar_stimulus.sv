`timescale 1ps/1fs
// VM-domain service stimulus. Independent oracle only; all data is served by
// actual native packet hubs/banks/rings. This is not a C/V transport proof.
module ot_native_scalar_stimulus #(parameter integer MUT=0)(
 input wire clk,rst_n,go,input wire [16*274-1:0] cr,
 input wire [2047:0] mirror_seen,input wire [11:0] hub_status,
 output reg [16*338-1:0] cq=0,output reg done=0,
 output integer requests=0,responses=0,checked_words=0,mirror_completions=0);
 integer phase=0,cyc=0,start_cycle=0,started=0;
 integer sent[0:15],outstanding[0:15],peak[0:15],head[0:15],tail[0:15];
 reg [15:0] tags[0:15][0:3];reg wes[0:15][0:3],mirrors[0:15][0:3];
 reg [8:0] offsets[0:15][0:3];reg [255:0] gold[0:15][0:3];
 function automatic [31:0] value(input integer kind,q,c,slot,w);
  value=(kind==0?32'h51CA0000:kind==1?32'h6A5C0000:32'hC0DE0000)^32'(q<<20)^32'(c<<16)^32'(slot<<8)^32'(w);
 endfunction
 function automatic [7:0] wordmask(input integer slot);
  wordmask=(slot&1)?8'h5a:8'ha5;
 endfunction
 function automatic [255:0] data(input integer kind,q,c,slot);
  for(integer w=0;w<8;w++)data[w*32+:32]=value(kind,q,c,slot,w);
 endfunction
 function automatic [255:0] masked(input integer q,c,slot);
  reg [7:0] mask;begin mask=wordmask(slot);for(integer w=0;w<8;w++)masked[w*32+:32]=value(mask[w]?1:0,q,c,slot,w);end
 endfunction
 function automatic [31:0] expected_word(input integer globalword,input [31:0] fallback);
  integer sec,off,q,c,slot,dest,w;reg [7:0] wm;begin
   sec=(globalword%65536)/8;off=sec-7168;q=off/128;c=(off%128)/32;slot=off%32;dest=(q+c+slot)%4;w=globalword%8;
   expected_word=fallback;wm=wordmask(slot);
   if(off>=0&&off<512&&slot<16&&globalword/65536==dest)expected_word=value(wm[w]?1:0,q,c,slot,w);
  end
 endfunction
 initial for(integer k=0;k<16;k++)begin sent[k]=0;outstanding[k]=0;peak[k]=0;head[k]=0;tail[k]=0;end
 always @(negedge clk)if(rst_n)begin:drive
  integer n,q,c,slot,sourceq,sec,dest,limit,all_done;
  reg we,ismirror;reg [255:0] wd,expected;reg [31:0] addr,bm;reg [7:0] wm;reg [15:0] tag;reg [273:0] rsp;
  cyc++;
  if(!started&&go)begin started=1;start_cycle=cyc;end
  cq=0;
  if(started&&!done)begin
   if(hub_status)$fatal(1,"SCALAR actual hub status %h phase%0d",hub_status,phase);
   if(cyc-start_cycle>40000)$fatal(1,"SCALAR actual service timeout phase%0d requests%0d responses%0d",phase,requests,responses);
   for(integer k=0;k<16;k++)begin
    rsp=cr[k*274+:274];
    if(rsp[273])begin
     n=head[k];
     if(outstanding[k]<=0)$fatal(1,"SCALAR unowed actual response client%0d",k);
     if(rsp[272:257]!==tags[k][n]||rsp[256]!==wes[k][n])$fatal(1,"SCALAR actual order/tag/echo mismatch client%0d tag%h expected%h we%b/%b",k,rsp[272:257],tags[k][n],rsp[256],wes[k][n]);
     if(rsp[255:0]!==gold[k][n])$fatal(1,"SCALAR actual SRAM data mismatch client%0d tag%h actual%h expected%h",k,rsp[272:257],rsp[255:0],gold[k][n]);
     if(!wes[k][n])checked_words+=8;
     if(mirrors[k][n])begin
      for(integer d=0;d<4;d++)if(!mirror_seen[d*512+offsets[k][n]])$fatal(1,"SCALAR premature mirror response client%0d tag%h missing_actual_C_copy%0d offset%0d",k,rsp[272:257],d,offsets[k][n]);
      mirror_completions++;
     end
     head[k]=(head[k]+1)%4;outstanding[k]--;responses++;
    end
   end
   limit=phase==5?64:16;all_done=1;
   for(integer k=0;k<16;k++)if(sent[k]<limit||outstanding[k]!=0)all_done=0;
   if(all_done)begin
    phase++;for(integer k=0;k<16;k++)sent[k]=0;
    if(phase==6)begin
     for(integer k=0;k<16;k++)if(peak[k]!=4)$fatal(1,"SCALAR client%0d did not observe four outstanding peak%0d",k,peak[k]);
     if(requests!=2304||responses!=2304||checked_words!=12288||mirror_completions!=256)$fatal(1,"SCALAR minimum exact counts absent %0d/%0d words%0d mirror%0d",requests,responses,checked_words,mirror_completions);
     done=1;$display("SCALAR_VM_DOMAIN PASS hubs4 clients16 requests2304 responses2304 peak4_each main_and_mirror_golden_words12288 mirrored_completions256 all4_C_copies_before_response cycles%0d CDC_qualificationOPEN",cyc-start_cycle);
    end
   end
   if(!done)for(integer k=0;k<16;k++)if(sent[k]<(phase==5?64:16)&&outstanding[k]<4)begin
    q=k/4;c=k%4;slot=sent[k]%16;sourceq=phase==5?sent[k]/16:q;
    sec=7168+sourceq*128+c*32+slot;dest=(sourceq+c+slot)%4;
    ismirror=phase>=4;we=(phase==0||phase==2||phase==4);
    addr=32'(sec<<5)|(ismirror?32'h00100000:32'(dest<<18));
    wd=data(phase==2?1:phase==4?2:0,sourceq,c,slot);wm=phase==2?wordmask(slot):8'hff;
    bm=0;for(integer w=0;w<8;w++)bm[w*4+:4]={4{wm[w]}};
    if(MUT==31&&phase==2&&k==0&&slot==0)bm=32'h00000001;
    expected=we?256'd0:phase==1?data(0,sourceq,c,slot):phase==3?masked(sourceq,c,slot):data(2,sourceq,c,slot);
    tag=16'((q<<14)|(c<<12)|(phase<<8)|sent[k]);
    cq[k*338+:338]={1'b1,we,addr,wd,bm,tag};
    n=tail[k];tags[k][n]=tag;wes[k][n]=we;mirrors[k][n]=phase==4;offsets[k][n]=9'(sec-7168);gold[k][n]=expected;
    tail[k]=(tail[k]+1)%4;outstanding[k]++;if(outstanding[k]>peak[k])peak[k]=outstanding[k];sent[k]++;requests++;
   end
  end
 end
endmodule
