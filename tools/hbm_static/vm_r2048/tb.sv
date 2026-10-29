`timescale 1ps/1ps
module tb_vm_r2048;
 parameter integer MUT=0;
 reg clk=0; initial forever begin #416 clk=1; #417 clk=0; end
 reg rst_n=0, legacy=0;
 reg [84:0] old_rq=0; reg [89:0] rq=0;
 reg [561:0] old_wq=0; reg [563:0] wq=0;
 reg [280:0] old_dq=0,old_kq=0; reg [281:0] dq=0,kq=0;
 reg [275:0] old_xq=0,old_xq2=0; reg [276:0] xq=0,xq2=0;
 reg [284:0] old_pq=0; reg [285:0] pq=0;
 reg rv=0,wv=0; reg [2:0] rs=0,ws=0;
 wire [1284:0] old_rr,rr; wire [265:0] old_pr,pr;
 wire [275:0] old_eg; wire [276:0] eg;
 wire [17:0] old_status,status; wire [5:0] old_done,done;
hfd_vms_bank_native_q0_facesolder(.clk(clk),.clk_n(clk),.clk_s(clk),.clk_e(clk),.clk_w(clk),.clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),.rst_n(rst_n),.bid(3'd0),.sid(2'd0),.rslot_v(rv),.rslot(rs),.wslot_v(wv),.wslot(ws),.rq0(old_rq[0+:17]),.rr0(old_rr[0+:257]),.rq1(old_rq[17+:17]),.rr1(old_rr[257+:257]),.rq2(old_rq[34+:17]),.rr2(old_rr[514+:257]),.rq3(old_rq[51+:17]),.rr3(old_rr[771+:257]),.rq4(old_rq[68+:17]),.rr4(old_rr[1028+:257]),.wq0(old_wq[0+:281]),.wq_done0(old_done[0]),.wq1(old_wq[281+:281]),.wq_done1(old_done[1]),.dq(old_dq),.dq_done(old_done[2]),.kq(old_kq),.kq_done(old_done[3]),.xq(old_xq),.xq_done(old_done[4]),.xq2(old_xq2),.xq2_done(old_done[5]),.eg(old_eg),.pq(old_pq),.pr(old_pr),.status(old_status));
hfd_vms_bank_native_q0_faces_r2048 #(.MUT(MUT)) newer(.clk(clk),.clk_n(clk),.clk_s(clk),.clk_e(clk),.clk_w(clk),.clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),.rst_n(rst_n),.bid(3'd0),.sid(2'd0),.rslot_v(rv),.rslot(rs),.wslot_v(wv),.wslot(ws),.clk_macro3(clk),.rq0(rq[0+:18]),.rr0(rr[0+:257]),.rq1(rq[18+:18]),.rr1(rr[257+:257]),.rq2(rq[36+:18]),.rr2(rr[514+:257]),.rq3(rq[54+:18]),.rr3(rr[771+:257]),.rq4(rq[72+:18]),.rr4(rr[1028+:257]),.wq0(wq[0+:282]),.wq_done0(done[0]),.wq1(wq[282+:282]),.wq_done1(done[1]),.dq(dq),.dq_done(done[2]),.kq(kq),.kq_done(done[3]),.xq(xq),.xq_done(done[4]),.xq2(xq2),.xq2_done(done[5]),.eg(eg),.pq(pq),.pr(pr),.status(status));
 reg [255:0] model[0:3071];
 reg [5:0] exp_done[0:20000]; reg [5:0] exp_read[0:20000]; reg exp_packet[0:20000];
 reg [255:0] exp_data[0:20000]; reg [7:0] exp_tag[0:20000];
 integer cycle=0,checks=0,legacy_checks=0,reads=0,writes=0; reg fault_ok=0;
 function automatic [255:0] dataword(input integer row,domain,owner);
  for(integer j=0;j<8;j=j+1)dataword[32*j+:32]=32'h1234abcd ^ 32'(row*271+domain*8192+owner*1027+j*137);
 endfunction
 function automatic [16:0] sector(input integer row,mir);
  sector={1'(mir),1'(row>>10),2'd0,10'(row),3'd0};
 endfunction
 task clear;
  begin old_rq=0;rq=0;old_wq=0;wq=0;old_dq=0;dq=0;old_kq=0;kq=0;old_xq=0;xq=0;old_xq2=0;xq2=0;old_pq=0;pq=0;rv=0;wv=0;rs=0;ws=0;end
 endtask
 task tick;
  begin
   @(posedge clk);#2;
   if(rst_n)begin
    if(!fault_ok && status!==18'd0)$fatal(1,"unexpected status %h edge%0d",status,cycle);
    if(done!==exp_done[cycle])$fatal(1,"commit edge mismatch cycle%0d got%b expected%b",cycle,done,exp_done[cycle]);
    for(integer g=0;g<5;g=g+1)begin
     if(rr[g*257+256]!==exp_read[cycle][g])$fatal(1,"read valid mismatch cycle%0d group%0d",cycle,g);
     if(exp_read[cycle][g] && rr[g*257+:256]!==exp_data[cycle])$fatal(1,"read data mismatch cycle%0d group%0d",cycle,g);
    end
    if(pr[265]!==exp_read[cycle][5])$fatal(1,"packet valid edge mismatch cycle%0d",cycle);
    if(exp_read[cycle][5] && pr!=={1'b1,exp_packet[cycle],exp_tag[cycle],exp_data[cycle]})$fatal(1,"packet data/tag mismatch");
    if(legacy)begin
     if(done!==old_done || status!==old_status)$fatal(1,"legacy done/status not exact");
     for(integer g=0;g<5;g=g+1)if(rr[g*257+256]!==old_rr[g*257+256] || (old_rr[g*257+256] && rr[g*257+:256]!==old_rr[g*257+:256]))$fatal(1,"legacy lockstep group%0d edge%0d",g,cycle);
     if(pr[265]!==old_pr[265] || (old_pr[265] && pr!==old_pr))$fatal(1,"legacy packet lockstep");
     if(eg[276]!==old_eg[275] || (old_eg[275] && eg!=={old_eg[275:274],1'b0,old_eg[273:0]}))$fatal(1,"legacy egress lockstep");
     legacy_checks=legacy_checks+1;
    end
    checks=checks+1;
   end
   cycle=cycle+1;@(negedge clk);
  end
 endtask
 task write_row(input integer owner,row,mir,input [255:0] data,input [7:0] mask);
  reg [16:0] sec;reg [11:0] loc;reg [15:0] os;reg [10:0] ol;integer ix;
  begin
   clear();wv=1;ws=3'(owner);sec=sector(row,mir);loc={1'(mir),11'(row)};os={1'(mir),2'd0,10'(row),3'd0};ol={1'(mir),10'(row)};
   case(owner)
    0,1:begin wq[owner*282+:282]={1'b1,sec,data,mask};if(legacy)old_wq[owner*281+:281]={1'b1,os,data,mask};exp_done[cycle+4][owner]=1;end
    2:begin kq={1'b1,sec,data,mask};if(legacy)old_kq={1'b1,os,data,mask};exp_done[cycle+4][3]=1;end
    3:begin xq={1'b1,loc,data,mask};if(legacy)old_xq={1'b1,ol,data,mask};exp_done[cycle+4][4]=1;end
    4:begin pq={1'b1,1'b1,loc,data,mask,8'h5a};if(legacy)old_pq={1'b1,1'b1,ol,data,mask,8'h5a};exp_read[cycle+7][5]=1;exp_packet[cycle+7]=1;exp_tag[cycle+7]=8'h5a;exp_data[cycle+7]=0;end
    5:begin xq2={1'b1,loc,data,mask};if(legacy)old_xq2={1'b1,ol,data,mask};exp_done[cycle+4][5]=1;end
    6:begin dq={1'b1,sec,data,mask};if(legacy)old_dq={1'b1,os,data,mask};exp_done[cycle+4][2]=1;end
   endcase
   if(!(mir && row>=1024))begin
    ix=mir?2048+row:row;for(integer j=0;j<8;j=j+1)if(mask[j])model[ix][32*j+:32]=data[32*j+:32];
   end
   writes=writes+1;tick();
  end
 endtask
 task read_row(input integer owner,row,mir);
  reg [16:0] sec;reg [11:0] loc;integer ix;
  begin clear();rv=1;rs=3'(owner);sec=sector(row,mir);loc={1'(mir),11'(row)};ix=mir?2048+row:row;
   if(owner<5)begin rq[owner*18+:18]={1'b1,sec};if(legacy)old_rq[owner*17+:17]={1'b1,1'(mir),2'd0,10'(row),3'd0};end
   else begin pq={1'b1,1'b0,loc,256'd0,8'd0,8'hc7};if(legacy)old_pq={1'b1,1'b0,1'(mir),10'(row),256'd0,8'd0,8'hc7};end
   exp_read[cycle+7][owner]=1;exp_packet[cycle+7]=0;exp_data[cycle+7]=model[ix];exp_tag[cycle+7]=8'hc7;reads=reads+1;tick();
  end
 endtask
 task flush;begin clear();repeat(10)tick();end endtask
 initial begin
  for(integer i=0;i<20001;i=i+1)begin exp_done[i]=0;exp_read[i]=0;exp_packet[i]=0;exp_data[i]=0;exp_tag[i]=0;end
  for(integer i=0;i<3072;i=i+1)model[i]=0;
  repeat(6)tick();rst_n=1;repeat(12)tick();legacy=1;
  // Same-address legacy regular/mirror domains, every write source and every read owner.
  for(integer d=0;d<2;d=d+1)for(integer row=0;row<64;row=row+1)write_row(row%7,row,d,dataword(row,d,0),8'hff);
  for(integer d=0;d<2;d=d+1)for(integer row=0;row<64;row=row+1)write_row((row+3)%7,row,d,dataword(row,d,1),8'h5a);
  flush();for(integer d=0;d<2;d=d+1)for(integer row=0;row<64;row=row+1)read_row(row%6,row,d);flush();legacy=0;
  // Full high regular half; exact same lower rows retain their legacy/mirror contents.
  for(integer row=1024;row<2048;row=row+1)write_row(row%7,row,0,dataword(row,2,2),8'hff);
  flush();for(integer row=1024;row<2048;row=row+1)read_row(row%6,row,0);flush();
  for(integer d=0;d<2;d=d+1)for(integer row=0;row<64;row=row+1)read_row(row%6,row,d);flush();
  // Both exact addresses that exposed a122's bit15 collision (bank0/SID0).
  write_row(0,336+1024,0,dataword(1360,3,3),8'hff);flush();read_row(0,1360,0);flush();
  // Existing SECDED remains active for the newly grown regular storage.
  fault_ok=1;newer.u_ot_pr_core.bank.u_h.arr[0][0]=~newer.u_ot_pr_core.bank.u_h.arr[0][0];
  read_row(0,1024,0);flush();if(status[16]!==0 || status[15:0]!==16'd1)$fatal(1,"grown high data SECDED correction missing status%h",status);
  // High mirror rows are outside the retained mirror capacity: fault and suppress write.
  write_row(0,1024,1,256'hdeadbeef,8'hff);flush();if(status[17]!==1)$fatal(1,"high mirror did not reject");
  rst_n=0;repeat(6)tick();rst_n=1;repeat(12)tick();read_row(0,0,1);flush();
  $display("VM_R2048 PASS cycles=%0d legacy_lockstep=%0d checks=%0d writes=%0d reads=%0d SRAMs=4 regular_rows=2048 mirror_rows=1024 return_edges=7 write_edges=4 added_cycles=0 SECDED_high=1 highmirror_rejected=1",cycle,legacy_checks,checks,writes,reads);$finish;
 end
endmodule
