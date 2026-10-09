`timescale 1ns/1ps
module tb_payload;
 reg clk=0;always #0.416666667 clk=~clk;
 reg rst_n=0,v=0;reg[544:0] din='0;
 wire ev,rv,ce,ue,drop;wire[544:0] ed,rd;
 ot_hcoll_sdelay #(.W(545),.D(6),.PAYLOAD_ECC(1)) dut(.clk(clk),.rst_n(rst_n),.v_in(v),.d_in(din),.v_out(ev),.d_out(ed),.ecc_ce(ce),.ecc_ue(ue),.ecc_drop(drop));
 ot_hcoll_sdelay #(.W(545),.D(6)) refraw(.clk(clk),.rst_n(rst_n),.v_in(v),.d_in(din),.v_out(rv),.d_out(rd));
 integer checks=0, cycles=0;
 task flip(input integer bitno,input integer addr);
 begin
 case(bitno/256)
 0:dut.u_m.g_m[0].u_sram.arr[addr][bitno%256]=~dut.u_m.g_m[0].u_sram.arr[addr][bitno%256];
 1:dut.u_m.g_m[1].u_sram.arr[addr][bitno%256]=~dut.u_m.g_m[1].u_sram.arr[addr][bitno%256];
 2:dut.u_m.g_m[2].u_sram.arr[addr][bitno%256]=~dut.u_m.g_m[2].u_sram.arr[addr][bitno%256];
 endcase
 end endtask
 task trial(input integer a,input integer b,input integer expectue);
 integer addr,n,seen;
 begin
 @(negedge clk);rst_n=0;v=0; repeat(2)@(negedge clk);rst_n=1;
 din={17'h175ab,{16{32'h7facba98}} ,16'h32af};v=1;
 @(negedge clk);v=0;addr=dut.cnt;
 @(negedge clk);
 if(a>=0)flip(a,addr);if(b>=0)flip(b,addr);
 seen=0;
 for(n=0;n<9;n=n+1)begin
 if(rv)begin
 seen=seen+1;
 if(expectue)begin if(ev||!ue||!drop)$fatal(1,"UE published a=%0d b=%0d",a,b);end
 else begin
 if(!ev||ue||ed!==rd)$fatal(1,"CE/lockstep mismatch a=%0d b=%0d",a,b);
 if(a>=0 && !ce)$fatal(1,"CE missing a=%0d",a);
 end
 end else if(ev||ue||ce||drop)$fatal(1,"spurious status");
 @(negedge clk);cycles=cycles+1;
 end
 if(seen!=1)$fatal(1,"missing raw valid");checks=checks+1;
 end endtask
 initial begin
 trial(-1,-1,0);
 for(integer i=0;i<648;i=i+1)trial(i,-1,0);
 for(integer c=0;c<9;c=c+1)for(integer a=0;a<72;a=a+1)for(integer b=a+1;b<72;b=b+1)trial(c*72+a,c*72+b,1);
 trial(0,72,0);
 $display("PAYLOAD_SRAM PASS checks=%0d cycles=%0d single=648 double=23004",checks,cycles);$finish;
 end
endmodule
