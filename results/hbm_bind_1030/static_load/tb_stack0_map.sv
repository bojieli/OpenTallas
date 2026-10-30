`timescale 1ns/1ps
module tb_stack0_map;
 parameter MUT=0;
 reg v=0;reg[39:0]a,d;reg[2:0]fmt;reg b;reg[15:0]ep;reg[14:0]row;reg[3:0]col;
 wire lv,fault;wire[61:0]cmd;wire[2:0]leaf;wire[1:0]quad;
 reg[185:0]mem[0:1151];integer i;
 ot_hbm_static_load_addr_map #(.MUT_PC(MUT),.SOURCE_STACK(0),.SOURCE_LOW_QUAD(0))dut(v,a,d,fmt,4'd1,b,ep,row,col,lv,fault,cmd,leaf,quad);
 initial begin
 $readmemh("addr_map_vectors.mem",mem);
 for(i=0;i<1152;i=i+1)begin
 {a,d,fmt,b,ep,row,col}=mem[i][185:67];a[36:35]=0;v=1;#1;
 if(!lv||fault||{cmd,leaf,quad}!=={mem[i][66:2],mem[i][1:0]-2'd2})$fatal(1,"ADDR_MAP_MISMATCH i=%0d",i);
 col=col^4'd1;#1;if(lv||!fault)$fatal(1,"STALE_WINDOW_ESCAPED");
 end
 // This source instance accepts actual stack0 only; no truncation/mirror guessing.
 a[36:35]=3;#1;if(lv||!fault)$fatal(1,"UNBOUND_STACK_ESCAPED");
 a[36:35]=0;col=col^4'd1;d[18]=1;#1;if(lv||!fault)$fatal(1,"UNDEFINED_VM_APERTURE_ESCAPED");
 $display("PASS ADDR_MAP exact_TOK62bit_reference=1152 formats=6 stale_windows=1152 stack0_parameter_exact_and_stack3_highVM_rejected combinational_added_cycles=0");$finish;
 end
endmodule
