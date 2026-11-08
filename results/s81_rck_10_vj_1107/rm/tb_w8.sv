`timescale 1ns/1ps
// S81-RCK-10: lock-step of OT_S81_RM_WFULL8 against RM_LOCAL4 (the vI source) fed through ONE wclk register
// (the declared +1 wclk PIN CYCLE).  Outputs r_d / fault compared at every rclk edge; mem / wp at every wclk edge.
module tb;
reg wclk=0,rclk=0,wen=1,ren=1,rst=0,wv=0; reg[511:0]wd=2;
always #0.417 if(wen)wclk=~wclk;else wclk=0;
initial begin #0.137;forever #0.4165 if(ren)rclk=~rclk;else rclk=0;end
reg wv_d; reg [511:0] wd_d;
always @(posedge wclk) begin wv_d<=wv; wd_d<=wd; end
wire [511:0] qr,qn; wire fr,fn;
rm_ref  R(.wclk(wclk),.wrst_n(rst),.w_v(wv_d),.w_d(wd_d),.rclk(rclk),.rrst_n(rst),.r_d(qr),.fault(fr));
rm_new  N(.wclk(wclk),.wrst_n(rst),.w_v(wv),.w_d(wd),.rclk(rclk),.rrst_n(rst),.r_d(qn),.fault(fn));
integer checks=0,err=0,fulls=0,sheds=0,pushes=0,faults=0,epochs=0,wchk=0,i,k,mode=0;
always @(posedge rclk) begin #0.001; if(rst) begin checks++; if(qr!==qn||fr!==fn) begin err++; if(err<6)$display("MISMATCH r t=%0t",$time); end end end
always @(posedge wclk) begin
  if(rst) begin if(R.w_v&&R.full)fulls++; if(R.w_v&&R.idle&&!R.full&&R.fill_w>=6)sheds++; if(R.push)pushes++; end
  #0.001; if(rst) begin wchk++; if(R.wp!==N.wp||R.wp_g!==N.wp_g||R.flt!==N.flt) begin err++; if(err<6)$display("MISMATCH w t=%0t",$time); end
    for(k=0;k<8;k++) if(R.mem[k]!==N.mem[k]) begin err++; if(err<6)$display("MISMATCH mem%0d t=%0t",k,$time); end end
end
function automatic[511:0] payload(input integer n);integer b;begin for(b=0;b<16;b=b+1)payload[b*32+:32]=$urandom;payload[0]=1;payload[1]=n[0];end endfunction
task reset_epoch;begin @(negedge wclk);rst=0;wv=0;wd=2;repeat(70)@(negedge rclk);rst=1;epochs++;end endtask
initial begin
  for(mode=0;mode<6;mode++) begin
    reset_epoch;
    for(i=0;i<3000;i++) begin
      @(negedge wclk);
      // mixed payload / idle beats; idle = bit1 set bit0 clear
      wv=(($urandom%8)!=0);
      wd=(($urandom%3)==0) ? 512'd2 : payload(i);
      if(mode>=2) ren=(($urandom%(mode+1))!=0);   // stall the reader: drives occupancy to 6..8 and full
      if(mode==5 && ($urandom%200)==0) begin ren=0; repeat(12)@(negedge wclk); end
    end
    ren=1; wv=0; wd=2; repeat(40)@(negedge wclk);
  end
  $display("RMW8_RESULT checks=%0d wchecks=%0d errors=%0d epochs=%0d pushes=%0d full_hits=%0d idle_sheds=%0d fault_ref=%0b",checks,wchk,err,epochs,pushes,fulls,sheds,fr);
  if(err) $fatal(1,"RMW8 lockstep FAILED");
  if(!fulls||!sheds) $fatal(1,"coverage hole");
  $finish;
end
initial begin #200000;$fatal(1,"timeout");end
endmodule
