`timescale 1ns/1ps
module tb_dsfd_vm_seq_sparse;
reg ck=0,rst=0; always #0.417 ck=~ck;
reg [84:0] cmd=0; wire [8:0] done; wire [1:0] st;
reg [127:0] cv=0; reg [1151:0] ca=0; reg [511:0] cm=0;
reg [31:0] rv=0; reg [447:0] rr=0; wire nv;wire[83:0]nd;wire su,hc;
dsfd_vm_seq_static dut(.ck(ck),.rst(rst),.c_cmd(cmd),.c_done(done),.c_st(st),.o_cv(cv),.o_ca(ca),.o_cm(cm),.o_rv(rv),.o_rr(rr),.v_cv(nv),.v_cd(nd),.v_dv(1'b0),.v_dt(8'd0),.v_flt(1'b0),.t_inp_su(su),.t_inp_hc(hc));
integer cy=0,bad=0,mode=0,ncmd=0,ndone=0,k,s,row,words=0;integer base[0:6]; reg[8:0]exp[0:1999];integer j;
initial for(j=0;j<2000;j=j+1)exp[j]=0;
always @(posedge ck) if(rst) begin
 #0.01;
 if(done!==exp[cy])begin bad=bad+1;if(bad<8)$display("DONE cy%0d got%h exp%h",cy,done,exp[cy]);end
 if(done[8])ndone=ndone+1;
 if(nv)begin bad=bad+1;$display("SPARSE FORWARDED");end
end
task step;begin @(negedge ck);cy=cy+1;cmd=0;cv=0;rv=0;cm=0;end endtask
task issue(input[23:0]arg);begin cmd={1'b1,1'b0,10'd0,21'd0,21'd0,arg,7'(ncmd)};exp[cy+6]={1'b1,1'b0,7'(ncmd)};ncmd=ncmd+1;end endtask
function[23:0] arm(input integer slot,input integer lo,input integer n);arm={3'(slot<4?5:7),2'(slot%4),10'(lo/16),2'(lo%4),7'(n-1)};endfunction
function[23:0] check(input integer slot);check={3'(slot<4?5:7),2'(slot%4),19'h7ffff};endfunction
task commit(input integer r);integer b,g,p;reg[8:0]a;begin
 a=9'(r>>5);b=(r%32)^((a%8)<<2);
 for(g=0;g<4;g=g+1)begin p=32*g+b;cv[p]=1;ca[9*p+:9]=a;cm[4*p+:4]=15;end
 words=words+16;
end endtask
initial begin
 if(!$value$plusargs("mode=%d",mode))mode=0;
 base[0]=6000;base[1]=6321;base[2]=6642;base[3]=6963;base[4]=7312;base[5]=7633;base[6]=7954;
 repeat(4)@(negedge ck);rst=1;repeat(5)step;
 if(mode<=4)begin
  for(s=0;s<7;s=s+1)begin step;issue(arm(s,base[s],80));end
  repeat(3)step;
  // Every slot stays open throughout the560distinct actual row observations.
  for(k=0;k<80;k=k+1)begin
   step;
   for(s=0;s<7;s=s+1)begin
    row=base[s]+4*k;
    if(!(mode==3&&s==2&&k==30))commit(row);
    else commit(row+1); // wrongcolor cannot substitute for the owned row
   end
   if(mode==2&&k==20)begin rv[0]=1;rr[13:0]=14'(base[4]+4*k);end
  end
  // Writes and reads of every address hole must not affect sparse completion.
  if(mode!=4)for(k=0;k<3;k=k+1)begin step;for(s=0;s<7;s=s+1)begin commit(base[s]+k+1);rv[s]=1;rr[14*s+:14]=14'(base[s]+k+1);end end
  if(mode==1)begin step;commit(base[0]);end
  repeat(8)step;
  for(s=0;s<7;s=s+1)begin step;issue(check(s));end
 end else if(mode==5)begin step;issue(arm(0,16368,80));end
 else if(mode==6)begin step;issue(check(6));end
 else if(mode==7)begin // disjoint sparsecolors overlap bounds legally; dense intersection is real
  step;issue(arm(0,6000,2));step;issue(arm(1,6001,2));
  step;issue({3'd2,1'b0,10'(6000/16),10'd0});
 end else if(mode==8)begin // Dense row inside sparse bounding interval, but in an unowned hole.
  step;issue(arm(0,6001,2));step;issue({3'd1,1'b0,10'(6000/16),10'd0});
  repeat(3)step;step;commit(6000);step;commit(6001);step;commit(6005);
  repeat(8)step;step;issue(check(0));step;issue({3'd1,1'b0,20'hfffff});
 end else if(mode==9)begin
  step;issue(arm(0,6000,2));step;issue(arm(1,6000,2));
 end
 repeat(20)step;
 if(mode==0||mode==4)begin
  for(s=0;s<7;s=s+1)if(dut.cnt[s]!==1280||!dut.s_ok[s])begin bad=bad+1;$display("COUNT slot%0d cnt%0d ok%b",s,dut.cnt[s],dut.s_ok[s]);end
  if(st[0]||!su||hc)bad=bad+1;
  if(ncmd!=14||ndone!=14)bad=bad+1;
  $display("SPARSE %s mode%0d words%0d commands%0d done%0d bad%0d",bad==0?"PASS":"FAIL",mode,words,ncmd,ndone,bad);
 end else if(mode==8)begin
  if(st[0]||dut.cnt[0]!=32||dut.cnt[1]!=16||!dut.s_ok[0]||!dut.s_ok[1])bad=bad+1;
  $display("SPARSE %s mode8 bad%0d",bad==0?"PASS":"FAIL",bad);
 end else begin
  case(mode)
   1:j=dut.flt[1]&&dut.flt[0];2:j=dut.flt[7];3:j=dut.flt[0];5:j=dut.flt[6];6:j=dut.flt[2];7:j=dut.flt[5];9:j=dut.flt[5];default:j=0;
  endcase
  $display("SPARSE %s mode%0d fault%h bad%0d",j&&st[0]&&bad==0?"PASS":"FAIL",mode,dut.flt,bad);
 end
 $finish;
end
endmodule
