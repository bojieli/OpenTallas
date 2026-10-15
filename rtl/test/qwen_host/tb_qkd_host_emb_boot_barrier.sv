`timescale 1ns/1ps
module tb_qkd_host_emb_boot_barrier;
 parameter MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rn=0,iv=0,ocr=0,require_fresh=1;reg[12:0]est=0;wire ic,ov,fault;wire[65:0]od;
 qkd_host_emb_boot_barrier #(.MUT(MUT))dut(ck,rn,iv,66'h29a,ic,est,require_fresh,ov,od,ocr,fault);
 initial begin
 repeat(3)@(negedge ck);rn=1;est=1;repeat(4)@(negedge ck);iv=1;@(negedge ck);iv=0;
 repeat(8)begin @(negedge ck);if(ov||ic)$fatal(1,"marker bypassed gateway check");end
 est=0;repeat(4)@(negedge ck);est=1;wait(ov);@(negedge ck);if(od!=66'h29a||fault)$fatal(1,"marker changed");ocr=1;@(negedge ck);ocr=0;wait(ic);
 @(negedge ck);require_fresh=0;iv=1;@(negedge ck);iv=0;wait(ov);
 @(negedge ck);ocr=1;@(negedge ck);ocr=0;wait(ic);
 @(negedge ck);require_fresh=1;rn=0;@(negedge ck);rn=1;iv=1;est=2;@(negedge ck);iv=0;
 repeat(8)begin @(negedge ck);if(ov||ic)$fatal(1,"bad image accepted");end
 if(!fault)$fatal(1,"gateway fault lost");$display("PASS embedding marker held until verified STATUS and fails closed");$finish;
 end
 initial begin #2000;$fatal(1,"watchdog");end
endmodule
