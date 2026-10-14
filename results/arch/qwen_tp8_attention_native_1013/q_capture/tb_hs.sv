module tb;
reg clk=0; always #5 clk=~clk;
reg rn=0,qv=0;reg[5:0] qb=0;reg[511:0] qd=0;
reg[31:0] raw[0:511];reg[15:0] golden[0:511];integer b,i,bad=0;
ot_qwen_nearhbm_head_hs #(.HD(128),.H(2)) dut(.clk(clk),.rst_n(rn),.c_in(4'd0),.row_in(1024'd0),.e_in(16'd0),.lt_in(12'd0),.hid(2'd2),.q_valid_in(qv),.q_beat_in(qb),.q_data_in(qd));
initial begin
$readmemh("raw.hex",raw);$readmemh("rounded.hex",golden);
repeat(5) @(negedge clk);rn=1;repeat(8) @(negedge clk);
for(b=0;b<32;b=b+1) begin qv=1;qb=b;for(i=0;i<16;i=i+1) qd[32*i+:32]=raw[16*b+i];@(negedge clk);end
qv=0;repeat(12) @(negedge clk);
for(i=0;i<8;i=i+1) if(dut.g_t[0].u_l8.q0[16*i+:16]!==golden[256+0+i]) begin bad=bad+1;$display("bad tile0 lane%0d got=%h expected=%h",i,dut.g_t[0].u_l8.q0[16*i+:16],golden[256+0+i]);end
for(i=0;i<8;i=i+1) if(dut.g_t[1].u_l8.q0[16*i+:16]!==golden[256+8+i]) begin bad=bad+1;$display("bad tile1 lane%0d got=%h expected=%h",i,dut.g_t[1].u_l8.q0[16*i+:16],golden[256+8+i]);end
for(i=0;i<8;i=i+1) if(dut.g_t[2].u_l8.q0[16*i+:16]!==golden[256+16+i]) begin bad=bad+1;$display("bad tile2 lane%0d got=%h expected=%h",i,dut.g_t[2].u_l8.q0[16*i+:16],golden[256+16+i]);end
for(i=0;i<8;i=i+1) if(dut.g_t[3].u_l8.q0[16*i+:16]!==golden[256+24+i]) begin bad=bad+1;$display("bad tile3 lane%0d got=%h expected=%h",i,dut.g_t[3].u_l8.q0[16*i+:16],golden[256+24+i]);end
for(i=0;i<8;i=i+1) if(dut.g_t[4].u_l8.q0[16*i+:16]!==golden[256+32+i]) begin bad=bad+1;$display("bad tile4 lane%0d got=%h expected=%h",i,dut.g_t[4].u_l8.q0[16*i+:16],golden[256+32+i]);end
for(i=0;i<8;i=i+1) if(dut.g_t[5].u_l8.q0[16*i+:16]!==golden[256+40+i]) begin bad=bad+1;$display("bad tile5 lane%0d got=%h expected=%h",i,dut.g_t[5].u_l8.q0[16*i+:16],golden[256+40+i]);end
for(i=0;i<8;i=i+1) if(dut.g_t[6].u_l8.q0[16*i+:16]!==golden[256+48+i]) begin bad=bad+1;$display("bad tile6 lane%0d got=%h expected=%h",i,dut.g_t[6].u_l8.q0[16*i+:16],golden[256+48+i]);end
for(i=0;i<8;i=i+1) if(dut.g_t[7].u_l8.q0[16*i+:16]!==golden[256+56+i]) begin bad=bad+1;$display("bad tile7 lane%0d got=%h expected=%h",i,dut.g_t[7].u_l8.q0[16*i+:16],golden[256+56+i]);end
for(i=0;i<8;i=i+1) if(dut.g_t[8].u_l8.q0[16*i+:16]!==golden[256+64+i]) begin bad=bad+1;$display("bad tile8 lane%0d got=%h expected=%h",i,dut.g_t[8].u_l8.q0[16*i+:16],golden[256+64+i]);end
for(i=0;i<8;i=i+1) if(dut.g_t[9].u_l8.q0[16*i+:16]!==golden[256+72+i]) begin bad=bad+1;$display("bad tile9 lane%0d got=%h expected=%h",i,dut.g_t[9].u_l8.q0[16*i+:16],golden[256+72+i]);end
for(i=0;i<8;i=i+1) if(dut.g_t[10].u_l8.q0[16*i+:16]!==golden[256+80+i]) begin bad=bad+1;$display("bad tile10 lane%0d got=%h expected=%h",i,dut.g_t[10].u_l8.q0[16*i+:16],golden[256+80+i]);end
for(i=0;i<8;i=i+1) if(dut.g_t[11].u_l8.q0[16*i+:16]!==golden[256+88+i]) begin bad=bad+1;$display("bad tile11 lane%0d got=%h expected=%h",i,dut.g_t[11].u_l8.q0[16*i+:16],golden[256+88+i]);end
for(i=0;i<8;i=i+1) if(dut.g_t[12].u_l8.q0[16*i+:16]!==golden[256+96+i]) begin bad=bad+1;$display("bad tile12 lane%0d got=%h expected=%h",i,dut.g_t[12].u_l8.q0[16*i+:16],golden[256+96+i]);end
for(i=0;i<8;i=i+1) if(dut.g_t[13].u_l8.q0[16*i+:16]!==golden[256+104+i]) begin bad=bad+1;$display("bad tile13 lane%0d got=%h expected=%h",i,dut.g_t[13].u_l8.q0[16*i+:16],golden[256+104+i]);end
for(i=0;i<8;i=i+1) if(dut.g_t[14].u_l8.q0[16*i+:16]!==golden[256+112+i]) begin bad=bad+1;$display("bad tile14 lane%0d got=%h expected=%h",i,dut.g_t[14].u_l8.q0[16*i+:16],golden[256+112+i]);end
for(i=0;i<8;i=i+1) if(dut.g_t[15].u_l8.q0[16*i+:16]!==golden[256+120+i]) begin bad=bad+1;$display("bad tile15 lane%0d got=%h expected=%h",i,dut.g_t[15].u_l8.q0[16*i+:16],golden[256+120+i]);end
if(bad) $fatal(1,"native capture failed");if(dut.q_pack_fault) $fatal(1,"native pack fault");$display("PASS native HSUB FP32 Q transport / canonical BF16 rounding 128/128, tie/negative/subnormal probes");qv=1;qb=1;@(negedge clk);qv=0;repeat(8) @(negedge clk);if(!dut.q_pack_fault) $fatal(1,"orphan half not rejected");$display("PASS native HSUB orphan odd-half mutation rejected by sticky pack fault");$finish;
end
endmodule
