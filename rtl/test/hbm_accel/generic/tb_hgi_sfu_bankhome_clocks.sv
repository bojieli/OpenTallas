`timescale 1ns/1ps
module tb_hgi_sfu_bankhome_clocks;
 parameter MUT=0;
 reg[3:0]roots=0;always #2 roots[0]=~roots[0];always #3 roots[1]=~roots[1];always #5 roots[2]=~roots[2];always #7 roots[3]=~roots[3];
 wire[3:0]bound=MUT==1?{4{roots[0]}}:MUT==2?{roots[2],roots[3],roots[0],roots[1]}:roots;
 integer expected[0:3],errors=0,checks=0;
 for(genvar h=0;h<4;h++)begin:g_expected
 initial expected[h]=0;
 always @(posedge roots[h])expected[h]++;
 end
 ot_hgi_sfu_bankhome_store dut(.clk_home(bound),.rst_n(1'b0),
 .scalar_load(4'd0),.scalar_enable(4'd0),.scalar_addr(96'd0),.scalar_data(128'd0),
 .rd_re(64'd0),.rd_addr(1536'd0),.rd_src(128'd0),.vm_we(16'd0),.vm_waddr(384'd0),.vm_wdata(512'd0),
 .stage_v(8'd0),.stage_group(16'd0),.stage_addr(120'd0),.stage_mask(64'd0),.stage_data(2048'd0),.drain_v(2'd0),.drain_addr(30'd0),
 .rd_q(),.drain_data(),.drain_result_v(),.fault());
 for(genvar h=0;h<4;h++)begin:g_home
 for(genvar g=0;g<5;g++)begin:g_group
 for(genvar b=0;b<4;b++)begin:g_bank
 integer edges=0;
 if(g<4)begin:g_operand
 always @(posedge dut.g_home[h].leaf.core.g_operand[g].u_group.g_bank[h*4+b].g_owned.u_b.g_m11.u_m.clk)edges++;
 end else begin:g_output
 always @(posedge dut.g_home[h].leaf.core.u_output.g_bank[h*4+b].g_owned.u_b.g_m11.u_m.clk)edges++;
 end
 initial begin #1001;checks++;if(edges!=expected[h])begin errors++;$display("CLOCK_ERROR home%0d group%0d bank%0d edges%0d expected%0d",h,g,b,edges,expected[h]);end end
 end end end
 initial begin #1002;$display("SFU_HOME_CLOCKS checks=%0d errors=%0d macros=80 roots=4 MUT=%0d",checks,errors,MUT);if(errors)$fatal(1,"CLOCKS_FAIL");if(checks!=80)$fatal(1,"COUNT_FAIL");$display("SFU_HOME_CLOCKS_PASS");$finish;end
endmodule
