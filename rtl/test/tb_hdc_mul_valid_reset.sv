`timescale 1ns/1ps
module tb_mul_valid_reset;
reg ck=0,rn=0,iv=0;reg[31:0]a=0,b=0;always #5 ck=~ck;
wire[31:0]yr,yn;wire[1:0]er,en;wire vr,vn;
ot_hdc_fp32_mul_lat #(.LAT(5),.DRST(1)) refu(ck,rn,iv,a,b,yr,er,vr);
ot_hdc_fp32_mul_lat #(.LAT(5),.DRST(0)) dutu(ck,rn,iv,a,b,yn,en,vn);
integer i,seed=827,checked=0,resets=0,errors=0;
always @(negedge ck) begin
 if(vr!==vn) begin errors=errors+1;$display("VALID_MISMATCH");end
 if(vr) begin checked=checked+1;if(yr!==yn||er!==en) begin errors=errors+1;$display("DATA_MISMATCH %h %h %d %d",yr,yn,er,en);end end
end
initial begin
 repeat(3)@(posedge ck);rn=1;
 for(i=0;i<4000;i=i+1)begin
 @(posedge ck);#1;
 iv=(i%7!=0);a=$random(seed);b=$random(seed);
 if(i%11==0) a={a[31],8'hff,a[22:0]};
 if(i%13==0) b={b[31],8'h00,b[22:0]};
 if(i%31==0)begin #1;rn=0;resets=resets+1;#1;if(vr!==0||vn!==0)errors=errors+1;end
 if(i%31==2)rn=1;
 end
 @(posedge ck);#1;iv=0;rn=1;repeat(15)@(posedge ck);#1;
 if(errors||checked<2500||resets!=130)$fatal(1,"FAIL reset err=%0d checked=%0d resets=%0d",errors,checked,resets);
 $display("PASS valid-only multiplier reset checked=%0d asynchronous_resets=%0d",checked,resets);$finish;
end
endmodule
