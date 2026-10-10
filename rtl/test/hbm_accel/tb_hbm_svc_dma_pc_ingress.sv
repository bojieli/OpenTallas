`timescale 1ns/1ps
module tb_hbm_svc_dma_pc_ingress #(parameter MUT=0);
 reg clk=0;always #5 clk=~clk;reg rst=1;
 wire reserve_ready;reg reserve_take=0;reg[1:0]reserve_bank=0;reg[3:0]reserve_len=4;
 reg in_v=0;reg[1:0]in_bank=0;reg[5:0]in_slot=0;reg[7:0]in_idx=0;reg[255:0]in_data=0;reg in_fault=0;
 reg[3:0]write_ready=0;wire out_v;wire[1:0]out_bank;wire[5:0]out_slot;wire[7:0]out_idx;wire[255:0]out_data;wire out_fault,control_fault;
 integer i,b,ordinal,drained=0,cycles=0,qhead[0:3];
 ot_hbm_svc_dma_pc_ingress #(.DEPTH(32),.SLOT_BITS(6))dut(.*);
 function automatic[255:0]payload(input integer slot,input integer bank);integer w;begin for(w=0;w<8;w=w+1)payload[w*32+:32]=32'hcafe9870^(slot<<12)^(bank<<8)^w;end endfunction
 function automatic bit fault(input integer slot,input integer bank);fault=((slot+bank)%7==0);endfunction
 always @(posedge clk)if(!rst&&out_v)begin
 if(qhead[out_bank]<32)ordinal=(7*qhead[out_bank]+9)%32;else ordinal=64+(7*(qhead[out_bank]-32)+5)%64;
 if(out_slot!==6'(ordinal)||out_idx!==8'(out_bank+(qhead[out_bank]>=32?16:0))||out_data!==payload(ordinal,out_bank)||out_fault!==fault(ordinal,out_bank))$fatal(1,"ingress FIFO identity/order bank=%0d head=%0d",out_bank,qhead[out_bank]);
 qhead[out_bank]=qhead[out_bank]+1;drained=drained+1;
 end
 task tick;begin @(posedge clk);#1;end endtask
 task unexpected;begin repeat(3)tick();$display("UNEXPECTED_ACCEPT ingress protocol violation");$finish;end endtask
 initial begin
 for(b=0;b<4;b=b+1)qhead[b]=0;repeat(3)tick();@(negedge clk);rst=0;
 if(MUT==2)begin in_v=1;in_bank=0;unexpected();end
 if(MUT==3)begin reserve_take=1;reserve_len=0;unexpected();end
 for(i=0;i<32;i=i+1)begin
 @(negedge clk);reserve_take=1;reserve_bank=i%4;reserve_len=4;#1;
 if(!reserve_ready)$fatal(1,"reservation capacity underfilled group=%0d",i);tick();
 end
 @(negedge clk);reserve_take=0;#1;
 if(reserve_ready)$fatal(1,"full bank reservations still ready");
 if(MUT==1)begin reserve_take=1;reserve_len=4;unexpected();end
 // Every native return arrives without a ready signal, after the complete reservation.
 for(i=0;i<32;i=i+1)begin
 ordinal=(7*i+9)%32;
 for(b=3;b>=0;b=b-1)begin
 @(negedge clk);in_v=1;in_bank=(MUT==5)?((b+1)%4):b;in_slot=ordinal;in_idx=b;in_data=payload(ordinal,b);in_fault=fault(ordinal,b);tick();
 if(control_fault)$fatal(1,"reserved unbackpressured return failed");
 end end
 @(negedge clk);in_v=0;
 if(MUT==4)begin in_v=1;in_bank=0;unexpected();end
 while(drained<128)begin
 @(negedge clk);cycles=cycles+1;
 write_ready=(cycles%3==0)?4'b0000:((cycles%3==1)?4'b0101:4'b1111);#1;
 tick();if(control_fault)$fatal(1,"drain control fault");if(cycles>300)$fatal(1,"finite FIFO drain failed");
 end
 @(negedge clk);write_ready=0;#1;
 if(out_v||!reserve_ready)$fatal(1,"drain did not restore reservation capacity");
for(b=0;b<4;b=b+1)if(qhead[b]!=32)$fatal(1,"bank transaction conservation");
 // Reuse wrapped pointers with issue, native returns and bank draining in flight together.
 for(i=0;i<64;i=i+1)begin
 @(negedge clk);reserve_take=1;reserve_bank=i%4;reserve_len=4;in_v=0;write_ready=4'b1111;#1;
 if(!reserve_ready)$fatal(1,"interleaved reservations unexpectedly full");tick();
 @(negedge clk);reserve_take=0;
 for(b=3;b>=0;b=b-1)begin
 in_v=1;in_bank=b;in_slot=64+(7*i+5)%64;in_idx=b+16;in_data=payload(64+(7*i+5)%64,b);in_fault=fault(64+(7*i+5)%64,b);
 write_ready=((i+b)%5==0)?4'b0000:4'b1111;tick();@(negedge clk);
 end
 in_v=0;
 end
 while(drained<384)begin write_ready=4'b1111;tick();@(negedge clk);end
 write_ready=0;#1;
 if(out_v||!reserve_ready||control_fault)$fatal(1,"interleaved wrap/drain state");
 for(b=0;b<4;b=b+1)if(qhead[b]!=96)$fatal(1,"wrapped bank conservation");
 $display("PASS minimum_one_PC four32deep_bank_FIFOs wholeburst_reservation unbackpressured128returns reversedbankreturns FIFOidentity stalledbankdrain interleavedissue_return_drain pointerwrap");$finish;
 end
endmodule
