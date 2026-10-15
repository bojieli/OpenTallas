`timescale 1ps/1fs
module tb_hbm_svc_mapped4_offset_owner;
 parameter integer MODE=1;
 reg clk=0;always #512 clk=~clk;reg rst_n=0,descriptor_v=0,block_active=0,stop=0,k_ready=0,kr_v=0,response_take=0;
 reg[29:0] descriptor_base=0,block_base=0;reg[19:0]descriptor_pcs=0,block_pcs=0;
 reg[14:0]descriptor_row_base=16640,block_row_base=16640;reg[11:0]descriptor_total=0,block_total=0;
 reg descriptor_bank=0,block_bank=0;reg[15:0]descriptor_epoch=37,block_epoch=37;reg[16:0]kr_tag=0;reg[3:0]kr_beat=0;
 wire k_v,response_ok,response_bank,fault;wire[29:0]k_addr;wire[3:0]k_len;wire[16:0]k_tag;wire[10:0]response_ordinal;wire[15:0]response_epoch;
 ot_hbm_svc_prefetch_mapped4_offset_owner #(.PACKED_OFFSET_MODE(MODE),.PC(18)) dut(.*);
 function automatic[29:0] address(input integer rowanchor,input integer globalt);reg[29:0]s;integer r,b,c;begin
  r=rowanchor+(globalt/1024);b=(((globalt>>7)&7)<<2)|(globalt&3);c=(globalt>>2)&31;
  s=r<<15;s[14:12]=(b>>2)^((r>>2)&7);s[11:7]=c;s[1:0]=(b&3)^(r&3);s[6:2]=18^s[11:7]^s[16:12];address=s;
 end endfunction
 integer checks=0,respchecks=0;
 task tick;begin @(posedge clk);#1;end endtask
 task run(input integer off,input integer n,input integer anchor);integer t,words,g,expectlen,beat,localword;reg[16:0]tag;reg[29:0]a;begin
  rst_n=0;descriptor_v=0;block_active=0;k_ready=0;kr_v=0;response_take=0;tick;tick;rst_n=1;tick;
  descriptor_pcs={5'd27,5'd18,5'd9,5'd3};block_pcs=descriptor_pcs;descriptor_base=off;block_base=off;descriptor_total=n;block_total=n;descriptor_row_base=anchor;block_row_base=anchor;descriptor_v=1;
  t=0;words=(n+1)/4; // PC18 is slot2: ceil((n-2)/4).
  while(t<words)begin
   #1;g=(MODE?off/4:0)+t;expectlen=words-t>=4&&(!MODE||(g%4)==0)?4:1;
   a=address(anchor,expectlen==4?((g/4)*4+((anchor+g/1024)&3)):g);
   if(!k_v||k_len!==expectlen||k_addr!==a||fault)$fatal(1,"offset owner address/length mismatch off=%0d t=%0d actual=%h expected=%h",off,t,k_addr,a);
   tag=k_tag;k_ready=1;#1;tick;k_ready=0;descriptor_v=0;block_active=1;checks=checks+1;
   for(beat=0;beat<expectlen;beat=beat+1)begin
    kr_v=1;kr_tag=tag;kr_beat=beat;response_take=1;#1;
    localword=t+(expectlen==4?(beat^((anchor+g/1024)&3)):0);
    if(!response_ok||response_ordinal!==localword*4+2||response_epoch!==37||response_bank)$fatal(1,"offset owner inverse beat mismatch off=%0d t=%0d beat=%0d gotord=%0d want=%0d ok=%0d epoch=%0d bank=%0d",off,t,beat,response_ordinal,localword*4+2,response_ok,response_epoch,response_bank);
    tick;respchecks=respchecks+1;
   end
   kr_v=0;response_take=0;t=t+expectlen;
  end
  #1;if(k_v||fault)$fatal(1,"owner overfetch/fault");block_active=0;
 end endtask
 initial begin
  run(MODE?4:0,73,16640);run(MODE?12:0,272,16641);run(MODE?4092:0,73,16640);run(MODE?4096:0,272,16640);run(MODE?4080:0,16,18687);run(0,5,16643);
  $display("MAPPED4_OFFSET_OWNER PASS mode=%0d requests=%0d exact_inverse_beats=%0d",MODE,checks,respchecks);$finish;
 end
endmodule
