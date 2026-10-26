`timescale 1ns/1ps
module tb;
 reg ck=0;always #5 ck=~ck;
 reg rn=0;reg [15:0] prn=0;
 reg [847:0] im=0;reg [27135:0] id=0;
 wire [847:0] dm,rm;wire [27135:0] dd,rd;wire [47:0] ep,mon;wire [2:0] he;
 wire [15:0] faults;
 s81_a2_w0_header hdr(.ck(ck),.rst_n(rn),.i_v(53'd0),.i_row(742'd0),.i_tag(424'd0),.o_epoch(he));
 s81_a2_payload33_epoch_groups group_epochs(ep,mon);
 genvar x,q;
 generate for(x=0;x<4;x=x+1)begin:slice
  wire [3:0] fc;wire [39:0] fj;
  s81_a2_w0_payload_split4 dut(.ck({4{ck}}),.rst_n(prn[4*x+:4]),.i_mask(im[212*x+:212]),.i_data(id[6784*x+:6784]),.o_mask(dm[212*x+:212]),.o_data(dd[6784*x+:6784]),.o_epoch(ep[12*x+:12]));
  s81_a2_w0_payload old(.ck(ck),.rst_n(rn),.i_mask(im[212*x+:212]),.i_data(id[6784*x+:6784]),.o_mask(rm[212*x+:212]),.o_data(rd[6784*x+:6784]));
  s81_a2f_control4_resetlocal ctl(.ck_control(ck),.rst_n(rn),.src_v(53'd0),.src_bank(424'd0),.header_epoch(he),.payload_epoch(mon[12*x+:12]),.fault(fc));
  for(q=0;q<4;q=q+1)begin:fault_bits
   assign fj[10*q+:10]={9'd0,fc[q]}; // actual slice's controller position
  end
  s81_a2f_fault_join4 join_fault(ck,rn,fj,faults[4*x+:4]);
 end endgenerate
 // Independent scheduled oracle for the production OR boundary. Controller
 // phase sampling -> sticky fault -> fault_join pin register -> output register.
 reg crst=0,frst=0;reg [1:0] crr=0,frr=0;reg [2:0] ce=0,own_prev=0,hprev=0;
 reg [47:0] eprev=0;reg sticky=0,fp=0,expected=0;reg bad;
 integer c,j,t,target,seed=3328,seen=0;
 initial begin
  for(c=0;c<808;c=c+1)begin
   @(negedge ck);rn=(c>=7);prn={16{rn}};
   if(c>=40)begin
    target=(c-40)/48;t=(c-40)%48;
    if(t<((target%2)?1:3))prn[target]=0;
    if(t>=21&&t<28)begin rn=0;prn=0;end
   end
   for(j=0;j<848;j=j+1)im[j]=$random(seed);
   for(j=0;j<848;j=j+1)id[32*j+:32]=$random(seed);
   @(posedge ck);
   expected=frr[1]?fp:0;fp=sticky;
   bad=(hprev!==own_prev);
   for(j=0;j<16;j=j+1)if(eprev[3*j+:3]!==own_prev)bad=1;
   sticky=crr[1]?(sticky|bad):0;
   own_prev=ce;ce=crr[1]?ce+1:0;hprev=he;eprev=ep;
   crr=crst?{crr[0],1'b1}:0;crst=rn;
   frr=frst?{frr[0],1'b1}:0;frst=rn;
   #1;
   if(c>9)begin
    if(dm!==rm||dd!==rd)$fatal(1,"PAY33_OR FAIL data/mask edge %0d",c);
    if((|faults)!==expected)$fatal(1,"PAY33_OR FAIL global fault edge %0d actual%h expected%h",c,|faults,expected);
    if(c>=40&&t==15)begin
     if((|faults)!==1)$fatal(1,"PAY33_OR FAIL missing root witness %0d",target);
     seen=seen+1;
    end
   end
  end
  if(seen!=16)$fatal(1,"PAY33_OR FAIL witness census %0d",seen);
  $display("PAY33_OR PASS 808 edges; 16 independent short/held payload resets witnessed; 27984 data/mask bits; scheduled global OR exact");$finish;
 end
endmodule
