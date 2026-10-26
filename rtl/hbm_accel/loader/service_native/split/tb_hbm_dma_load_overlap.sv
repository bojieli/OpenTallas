`timescale 1ns/1ps
module tb_hbm_dma_load_overlap;
 reg clk=0,rst_n=0;always #1 clk=~clk;
 reg bv=0,bb=0,start=0,lv=0;reg[15:0]ep=0;reg[61:0]cmd=0;
 reg[1:0]fv=0,fb=0;reg[11:0]fs=0;reg[511:0]fd=0;
 wire f0,f1,pb,ft,bz,ov;wire[1:0]ready,dqdest;wire[2:0]db;wire[280:0]raw,load;
 ot_hbm_svc_vmdel_lane_load_static #(.NPC(2))u(.clk(clk),.rst_n(rst_n),.bank_id(3'd0),
 .begin_v_i(bv),.begin_bank_i(bb),.begin_epoch_i(ep),.start_i(start),.start_bank_i(1'b1),.start_epoch_i(16'd8),.start_base_sector_i(16'd0),
 .fill_v_i(fv),.fill_bank_i(fb),.fill_slot_i(fs),.fill_epoch_i({2{ep}}),.fill_data_i(fd),
 .full0_all({8{f0}}),.full1_all({8{f1}}),.pcbad_all({8{pb}}),.full0(f0),.full1(f1),.pcbad(pb),.block_ready(ready),.busy(bz),.fault(ft),.dq(raw),
 .load_v_i(lv),.load_cmd_i(cmd),.load_dest_bank(db),.load_dest_q(dqdest),.load_dq(load),.load_out_v(ov));
 function automatic[255:0]data(input integer bank,input integer group_id,input integer slot);
 for(integer j=0;j<32;j=j+1)data[j*8+:8]=8'(j+17*slot+91*group_id+13*bank);
 endfunction
 reg[255:0]expected_load;integer errors=0,nraw=0,nload=0,overlap=0;integer bank,slot,j;
 reg[280:0]expected_raw;
 always @(posedge clk)begin #0.1;
 if(rst_n&&raw[280])begin
 expected_raw={1'b1,16'((nraw/2)*16+(nraw%2)*8),data(1,nraw%2,nraw/2),8'hff};
 if(raw!==expected_raw)begin errors=errors+1;if(errors<4)$display("RAW_OVERLAP_MISMATCH %0d",nraw);end
 nraw=nraw+1;
 end
 if(rst_n&&ov)begin
 if(load!=={1'b1,16'd1001,expected_load,8'hff}||db!=2||dqdest!=3)begin errors=errors+1;$display("LOAD_OVERLAP_MISMATCH %h",load);end
 nload=nload+1;
 end
 if(rst_n&&ov&&raw[280])overlap=overlap+1;
 end
 initial begin
 for(j=0;j<8;j=j+1)expected_load[j*32+:32]={8'(2*j+1),8'(2*j),16'd0};
 repeat(5)@(negedge clk);rst_n=1;repeat(6)@(negedge clk);
 for(bank=0;bank<2;bank=bank+1)begin
 bb=1'(bank);ep=16'(7+bank);bv=1;@(negedge clk);bv=0;repeat(4)@(negedge clk);
 for(slot=0;slot<64;slot=slot+1)begin
 fv=3;fb={2{1'(bank)}};fs={2{6'(slot)}};fd={data(bank,1,slot),data(bank,0,slot)};@(negedge clk);
 end
 fv=0;repeat(8)@(negedge clk);
 end
 if(ready!=3||ft)$fatal(1,"OVERLAP banks not ready");
 cmd=0;cmd[16:1]=7;cmd[32:30]=1;cmd[48:33]=1001;cmd[55:52]=8;cmd[59:57]=2;cmd[61:60]=3;
 lv=1;@(negedge clk);lv=0;start=1;@(negedge clk);start=0;
 repeat(150)@(negedge clk);
 if(errors||ft||nraw!=128||nload!=1||overlap!=1)$fatal(1,"DMA_LOAD_OVERLAP FAIL errors=%0d fault=%0b raw=%0d load=%0d overlap=%0d",errors,ft,nraw,nload,overlap);
 $display("DMA_LOAD_OVERLAP PASS raw_packets=128 converted_packets=1 simultaneous_outputs=1");$finish;
 end
endmodule
