`timescale 1ns/1ps
module tb_hbm_svc_dma_pc_ingress_protected #(parameter MUT=0,ERR_LANE=0,ERR_BIT=0);
 reg clk=0;always #5 clk=~clk;reg rst=1;
 wire reserve_ready;reg reserve_take=0;reg[1:0]reserve_bank=0;reg[3:0]reserve_len=4;
 reg in_v=0;reg[1:0]in_bank=0;reg[5:0]in_slot=0;reg[7:0]in_idx=0;reg[255:0]in_data=0;reg in_fault=0;
 reg[3:0]write_ready=0;wire out_v;wire[1:0]out_bank;wire[5:0]out_slot;wire[7:0]out_idx;wire[255:0]out_data;wire out_fault,out_epoch,control_fault;reg in_epoch=0;
 integer i,b,ordinal,drained=0,cycles=0,qhead[0:3];
 ot_hbm_svc_dma_pc_ingress_protected #(.ENABLE(MUT!=13),.DEPTH(32),.SLOT_BITS(6))dut(.*);
 function automatic[255:0]payload(input integer slot,input integer bank);integer w;begin for(w=0;w<8;w=w+1)payload[w*32+:32]=32'hcafe9870^(slot<<12)^(bank<<8)^w;end endfunction
 function automatic bit fault(input integer slot,input integer bank);fault=((slot+bank)%7==0);endfunction
 always @(posedge clk)if(!rst&&out_v)begin
 if(qhead[out_bank]<32)ordinal=(7*qhead[out_bank]+9)%32;else if(qhead[out_bank]<96)ordinal=64+(7*(qhead[out_bank]-32)+5)%64;else ordinal=128+(3*(qhead[out_bank]-96)+1)%64;
 if(out_slot!==6'(ordinal)||out_idx!==8'(out_bank+(qhead[out_bank]>=96?32:(qhead[out_bank]>=32?16:0)))||out_epoch!==(ordinal%2))$fatal(1,"ingress metadata identity/order");
 if(MUT==11&&out_bank==0&&qhead[out_bank]==10)begin if(out_data!==256'd0||!out_fault)$fatal(1,"double error did not poison whole sector");end
 else if(out_data!==payload(ordinal,out_bank)||out_fault!==fault(ordinal,out_bank))$fatal(1,"ingress FIFO identity/order bank=%0d head=%0d",out_bank,qhead[out_bank]);
 qhead[out_bank]=qhead[out_bank]+1;drained=drained+1;
 end
 task tick;begin @(posedge clk);#1;end endtask
 task unexpected;begin repeat(3)tick();if(!control_fault)$fatal(1,"protocol violation did not fault");$display("EXPECTED_FAULT protected protocol violation");$finish;end endtask
 initial begin
 for(b=0;b<4;b=b+1)qhead[b]=0;repeat(3)tick();@(negedge clk);rst=0;
 if(MUT==13)begin reserve_take=1;in_v=1;write_ready=15;repeat(10)tick();if(reserve_ready||out_v||control_fault)$fatal(1,"disabled protected ingress changed");$display("PASS disabled_opt_in");$finish;end
 if(MUT==2)begin in_v=1;in_bank=0;repeat(3)tick();if(!control_fault)$fatal(1,"unreserved return did not fault");$display("EXPECTED_FAULT unreserved");$finish;end
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
 @(negedge clk);in_v=1;in_bank=(MUT==5)?((b+1)%4):b;in_slot=ordinal;in_idx=b;in_data=payload(ordinal,b);in_fault=fault(ordinal,b);in_epoch=ordinal%2;tick();
 if(control_fault)$fatal(1,"reserved unbackpressured return failed");
 end end
 @(negedge clk);in_v=0;
 if(MUT==4)begin in_v=1;in_bank=0;unexpected();end
 repeat(8)tick();
 if(reserve_ready||dut.pub_used!=4||dut.arrived[0]!=32||dut.reserved[0]!=32)$fatal(1,"finite publication backpressure/debt");
 if(MUT==9||MUT==10||MUT==11)begin
 @(negedge clk);
 if(MUT==9)dut.payload[0][10]=dut.payload[0][10]^(288'd1<<(ERR_LANE*72+ERR_BIT));
 if(MUT==10)dut.payload[0][10]=dut.payload[0][10]^(288'd1<<(ERR_LANE*72+64+ERR_BIT));
 if(MUT==11)dut.payload[0][10]=dut.payload[0][10]^(288'd3<<(ERR_LANE*72));
 end
 if(MUT==6)begin @(negedge clk);dut.metadata_n[0][5]=dut.metadata_n[0][5]^(16'd1<<ERR_BIT);#1;if(!control_fault||reserve_ready||out_v)$fatal(1,"metadata corruption not immediately fail closed");tick();@(negedge clk);dut.metadata_n[0][5]=dut.metadata_n[0][5]^(16'd1<<ERR_BIT);repeat(2)tick();if(!control_fault)$fatal(1,"metadata fault not sticky");$display("EXPECTED_FAULT metadata");$finish;end
 if(MUT==7)begin @(negedge clk);dut.reserved_n[1]=dut.reserved_n[1]^6'd1;#1;if(!control_fault||reserve_ready||out_v)$fatal(1,"control corruption not immediately fail closed");tick();@(negedge clk);dut.reserved_n[1]=dut.reserved_n[1]^6'd1;repeat(2)tick();if(!control_fault)$fatal(1,"control fault not sticky");$display("EXPECTED_FAULT control");$finish;end
 if(MUT==8)begin @(negedge clk);dut.pub_data_n[0]=dut.pub_data_n[0]^256'd1;#1;if(!control_fault||out_v)$fatal(1,"publication corruption not fail closed");tick();@(negedge clk);dut.pub_data_n[0]=dut.pub_data_n[0]^256'd1;repeat(2)tick();if(!control_fault)$fatal(1,"publication fault not sticky");$display("EXPECTED_FAULT publication");$finish;end
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
 in_v=1;in_bank=b;in_slot=64+(7*i+5)%64;in_idx=b+16;in_data=payload(64+(7*i+5)%64,b);in_fault=fault(64+(7*i+5)%64,b);in_epoch=(64+(7*i+5)%64)%2;
 write_ready=((i+b)%5==0)?4'b0000:4'b1111;tick();@(negedge clk);
 end
 in_v=0;
 end
 while(drained<384)begin write_ready=4'b1111;tick();@(negedge clk);end
 write_ready=0;#1;
 if(out_v||!reserve_ready||control_fault)$fatal(1,"interleaved wrap/drain state");
 for(b=0;b<4;b=b+1)if(qhead[b]!=96)$fatal(1,"wrapped bank conservation");
 // Unbalanced partial bursts saturate bank0 independently; bank1 remains admissible.
 for(i=0;i<32;i=i+1)begin
 @(negedge clk);reserve_take=1;reserve_bank=0;reserve_len=1;write_ready=0;in_v=0;#1;
 if(!reserve_ready)$fatal(1,"partial bank0 admission");tick();
 @(negedge clk);reserve_take=0;in_v=1;in_bank=0;in_slot=128+(3*i+1)%64;in_idx=32;
 in_data=payload(128+(3*i+1)%64,0);in_fault=fault(128+(3*i+1)%64,0);in_epoch=(128+(3*i+1)%64)%2;tick();
 end
 @(negedge clk);in_v=0;reserve_bank=0;#1;if(reserve_ready)$fatal(1,"full single bank admitted");
 reserve_bank=1;#1;if(!reserve_ready)$fatal(1,"unrelated free bank blocked");
 while(drained<416)begin @(negedge clk);write_ready=1;tick();end
 @(negedge clk);write_ready=0;#1;
 if(control_fault||out_v||!reserve_ready||qhead[0]!=128)$fatal(1,"unbalanced partial conservation");
 if(MUT==9||MUT==10||MUT==11)$display("PASS actual_SECDED_fault_injection mutation=%0d lane=%0d bit=%0d",MUT,ERR_LANE,ERR_BIT);
 $display("PASS protected_one_PC four32deep_bank_FIFOs wholeburst_reservation unbackpressured128returns reversedbankreturns FIFOidentity stalledbankdrain interleavedissue_return_drain pointerwrap unbalanced_partial_banks");$finish;
 end
endmodule
