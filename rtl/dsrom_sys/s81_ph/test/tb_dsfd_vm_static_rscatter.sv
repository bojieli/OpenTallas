`timescale 1ns/1ps
module tb_dsfd_vm_static_rscatter;
 reg ck=0;always #2 ck=~ck;reg rn=0;
 reg [31:0] iv=0,iw=0;reg [447:0] ir=0;reg [127:0] im=0;
 reg [4095:0] id=0;reg [255:0] it=0;
 wire [31:0] ov,ow;wire [287:0] oa;wire [127:0] om;
 wire [4095:0] od;wire [255:0] ot;wire fault;
 dsfd_vm_static_rscatter u(.ck(ck),.rst_n(rn),.i_v(iv),.i_row(ir),.i_tag(it),.o_v(ov),.o_addr(oa),.o_tag(ot),.fault(fault));
 reg [31:0] ev,ew;reg [287:0] ea;reg [127:0] em;reg [4095:0] ed;reg [255:0] et;
 integer bad=0,checks=0;integer lane_n[0:3];integer row,bank,j,lane;
 task drive(input integer base,input integer qr,input integer count);
 begin
  @(negedge ck);iv=0;ev=0;ew=0;ea=0;em=0;ed=0;et=0;
  for(integer q=0;q<4;q=q+1)lane_n[q]=0;
  for(integer n=0;n<count;n=n+1)begin
   row=base+(qr ?32*(n/4)+28+n%4:n);lane=row%4;j=8*lane+lane_n[lane];lane_n[lane]=lane_n[lane]+1;
   bank=(row%32)^(((row/32)%8)*4);
   iv[j]=1;iw[j]=n%2;ir[14*j+:14]=row;im[4*j+:4]=(n%15)+1;
   id[128*j+:128]={32'(row),32'(n),32'h12345678,32'(base)};it[8*j+:8]=n;
   ev[bank]=1;ew[bank]=iw[j];ea[9*bank+:9]=row/32;em[4*bank+:4]=im[4*j+:4];
   ed[128*bank+:128]=id[128*j+:128];et[8*bank+:8]=n;
  end
  // Exactly two receiving edges from pin sampling to registered bank outputs.
  @(posedge ck);@(posedge ck);#0.1;
  if({ov,oa,ot}!={ev,ea,et} || fault)bad=bad+1;
  checks=checks+1;@(negedge ck);iv=0;@(posedge ck);@(posedge ck);#0.1;
  if(ov!=0)bad=bad+1;
 end endtask
 initial begin
  #9;rn=1;repeat(4)@(negedge ck);
  // Exhaust all aligned16-row dense windows and all legal QR32-row windows.
  for(integer b=0;b<=16368;b=b+16)drive(b,0,16);
  for(integer b=0;b<=16352;b=b+32)drive(b,0,32);
  for(integer b=0;b<=16128;b=b+16)drive(b,1,32);
  $display("RESULT checks%0d bad%0d fault%0d",checks,bad,fault);
  if(bad==0 && !fault)$display("PASS");else $display("FAIL");$finish;
 end
endmodule
