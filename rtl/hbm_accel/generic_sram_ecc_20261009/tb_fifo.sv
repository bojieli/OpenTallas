`timescale 1ns/1ps
module tb_fifo;
 reg clk=0;always #0.416666667 clk=~clk;
 reg rst_n=0,push=0,pop=0;reg[544:0] din='0;
 wire ee,re,eov,rov,ce,ue,drop;wire[544:0] ed,rd;wire[8:0] ec,rc;
 ot_hcoll_sfifo #(.W(545),.AW(8),.PAYLOAD_ECC(1)) dut(.clk(clk),.rst_n(rst_n),.push(push),.din(din),.pop(pop),.empty(ee),.dout(ed),.ovf(eov),.count(ec),.ecc_ce(ce),.ecc_ue(ue),.ecc_drop(drop));
 ot_hcoll_sfifo #(.W(545),.AW(8)) refraw(.clk(clk),.rst_n(rst_n),.push(push),.din(din),.pop(pop),.empty(re),.dout(rd),.ovf(rov),.count(rc));
 integer checks=0;
 task flip(input integer b);
 begin case(b/256)
 0:dut.g_bk[0].u_m.g_m[0].u_sram.arr[0][b%256]=~dut.g_bk[0].u_m.g_m[0].u_sram.arr[0][b%256];
 1:dut.g_bk[0].u_m.g_m[1].u_sram.arr[0][b%256]=~dut.g_bk[0].u_m.g_m[1].u_sram.arr[0][b%256];
 2:dut.g_bk[0].u_m.g_m[2].u_sram.arr[0][b%256]=~dut.g_bk[0].u_m.g_m[2].u_sram.arr[0][b%256];
 endcase end endtask
 task trial(input integer a,input integer b);
 integer c,u,seen;
 begin
 @(negedge clk);rst_n=0;push=0;pop=0;repeat(2)@(negedge clk);rst_n=1;push=1;din={17'h175ab,{16{32'h12345678}},16'hffff};
 @(negedge clk);push=0;@(negedge clk);flip(a);if(b>=0)flip(b);c=0;u=0;seen=0;
 repeat(15)begin
 c=c+ce;u=u+ue;
 if(!ee)begin if(b>=0)$fatal(1,"FIFO UE publication"); if(ed!==din)$fatal(1,"FIFO corrupt CE");seen=seen+1;pop=1;end else pop=0;
 @(negedge clk);
 end
 if(b<0 && (c!=1||u||seen!=1))$fatal(1,"FIFO CE counts %0d %0d %0d",c,u,seen);
 if(b>=0 && (u!=1||seen||!ee||dut.ocr!=4||ec!=0))$fatal(1,"FIFO UE credit/refusal %0d ocr=%0d",u,dut.ocr);
 checks=checks+1;
 end endtask
 initial begin
 repeat(2)@(negedge clk);rst_n=1;
 // Full-rate, bubbles, stalls, both128-deep macro banks and pointer wrap.
 for(integer i=0;i<1500;i=i+1)begin
 @(negedge clk);
 if(ee!==re||ec!==rc||eov!==rov||(!ee&&ed!==rd)||ce||ue)$fatal(1,"DS cycle lockstep %0d",i);
 push=(i%7!=0)&&ec<200;pop=(i%5!=0);din={17'(i),{16{32'(i)}},16'(i)};
 end
 @(negedge clk);push=0;pop=1;repeat(300)@(negedge clk);
 for(integer i=0;i<648;i=i+1)trial(i,-1);
 for(integer c=0;c<9;c=c+1)trial(c*72,c*72+2);
 $display("PAYLOAD_FIFO PASS lockstep=1500 faultchecks=%0d",checks);$finish;
 end
endmodule
