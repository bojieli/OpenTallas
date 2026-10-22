`timescale 1ns/1ps
module tb_sysface_reset_same3;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0;reg[1:0]s;reg[37:0]q;wire[37:0]actual;integer n=0;
 always @(posedge ck or negedge rst_n)if(!rst_n)begin s<=0;q<=0;end else begin s<={s[0],1'b1};q<={38{s[1]}};end
 qfd_sysface_reset_same3 d(.ck(ck),.rst_n(rst_n),.leaf_n(actual));
 always @(posedge ck)begin #1;if(actual!==q)$fatal(1,"RESET_RELEASE_DIFF edge%0d",n);n=n+1;end
 always @(negedge rst_n)begin #1;if(actual!==0)$fatal(1,"ASYNC_ASSERT_DIFF");end
 initial begin repeat(3)@(negedge ck);rst_n=1;repeat(8)@(negedge ck);
 #2;rst_n=0;#1;rst_n=1;repeat(8)@(negedge ck);rst_n=0;repeat(3)@(negedge ck);rst_n=1;repeat(8)@(negedge ck);
 $display("PASS RESET_SAME3 edges=%0d all38outputs match original third-edge release and async assertion",n);$finish;end
endmodule
