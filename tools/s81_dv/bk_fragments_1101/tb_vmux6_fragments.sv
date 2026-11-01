`timescale 1ps/1fs
module tb_vmux6_fragments;
reg ck=0;always #416.5 ck=~ck;reg rst_n=0;reg[275:0]i[0:5];wire[275:0]got,old;wire fault,oldfault;
dsdv_idx_vmux6 dut(.ck(ck),.rst(rst_n),.i_r(i[0]),.i_s(i[1]),.i_a(i[2]),.i_b(i[3]),.i_n(i[4]),.i_l(i[5]),.o(got),.fault(fault));
dsdv_idx_vmux6_legacy before_fix(.ck(ck),.rst(rst_n),.i_r(i[0]),.i_s(i[1]),.i_a(i[2]),.i_b(i[3]),.i_n(i[4]),.i_l(i[5]),.o(old),.fault(oldfault));
reg[275:0]expected[0:4095];integer cyc=0,errors=0,checks=0,legacy_fragment_errors=0,fragments=0,trial,slot,lane,kind,mut=0;reg[275:0]word_;
function automatic[275:0]payload(input integer n);reg[275:0]w;begin
 w={8{32'h2468ac00+32'(n)}};w[275:256]=20'hba000+20'(n);payload=w;end endfunction
always @(negedge ck)begin
 rst_n=(cyc>=32);for(integer j=0;j<6;j++)begin i[j]=payload(7*j+cyc);i[j][0]=0;end
 word_=0;
 if(cyc>=80&&cyc<1680&&(cyc-80)%3==0)begin
  trial=(cyc-80)/3;lane=trial%6;kind=trial%6;kind=(kind==0)?0:kind+2;
  word_=payload(trial);word_[0]=1;word_[3:1]=3'(kind);i[lane]=word_;
 end
 if(cyc>=1800&&cyc<3336)begin
  trial=(cyc-1800)/8;slot=(cyc-1800)%8;lane=trial%6;
  if(slot<4)begin word_=payload(1000+4*trial+slot);word_[7:0]=8'(slot);if(slot==0)begin word_[0]=1;word_[3:1]=3'(1+(trial/6)%2);end i[lane]=word_;end
 end
 expected[cyc+2]=word_;
 if(cyc>=3500&&cyc<3504)begin
  for(integer j=0;j<6;j++)i[j]=0;
  i[0]=payload(cyc);i[0][0]=1;
  if(cyc==3500)i[0][3:1]=3'd1;
  if(cyc==3502)begin i[0]=0;i[1]=payload(77);i[1][0]=1;i[1][3:1]=3'd0;end
 end
end
always @(posedge ck)begin cyc=cyc+1;#0.001;
 if(cyc>70&&cyc<3460)begin
  checks++;
  if(got!==(expected[cyc]^((mut&&cyc==1802)?276'd1<<100:276'd0)))begin errors++;if(errors<5)$display("VMUX_DATA cycle%0d got%h expected%h",cyc,got,expected[cyc]);end
  if(fault)begin errors++;if(errors<5)$display("VMUX_UNEXPECTED_FAULT cycle%0d",cyc);end
  if(cyc<1700&&(got!==old||fault!==oldfault))errors++;
  if(cyc>=1802&&cyc<3338&&expected[cyc]!=0)begin fragments++;if(old!==expected[cyc])legacy_fragment_errors++;end
 end
 if(cyc==3540)begin
  if(!fault||oldfault||fragments!=768||legacy_fragment_errors!=192)errors++;
  $display("VMUX6_FRAGMENTS checks%0d literal_fragments%0d legacy_lost%0d zero_fragment_collision%0d legacy_collision%0d errors%0d clock833",checks,fragments,legacy_fragment_errors,fault,oldfault,errors);
  if(errors==0)$display("VMUX6_FRAGMENTS_PASS");else $fatal(1,"VMUX6_FRAGMENTS_FAIL");$finish;
 end
end
initial begin mut=$test$plusargs("mut_payload");for(integer j=0;j<4096;j++)expected[j]=0;for(integer j=0;j<6;j++)i[j]=0;end
endmodule
