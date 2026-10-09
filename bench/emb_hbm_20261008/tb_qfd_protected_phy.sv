`timescale 1ns/1ps
module tb_qfd_protected_phy;
 import ot_gpu_w6_secded_pkg::*;
 parameter integer MUT=0,ENABLE=1;
 reg clk=0;always #0.512 clk=~clk;
 reg rst_n=0,q_v=0,q_we=0,q_emb=0;wire q_rdy;
 reg[18:0] q_row;reg[4:0]q_bank,q_col;reg[16:0]q_sec;reg[7:0]q_lrow;reg[63:0]q_id;reg[287:0]q_code;
 wire o_v,o_we,o_emb,fault;reg o_rdy=1;
 wire[16:0]o_sec;wire[7:0]o_lrow;wire[63:0]o_id;wire[18:0]o_row;wire[4:0]o_bank,o_col;wire[287:0]o_code;
 wire p_v,p_rdy,p_we;wire[30:0]p_addr;wire[4:0]p_len;wire[15:0]p_tag;wire[255:0]p_data;
 wire[31:0]rv,rr;wire[511:0]rt;wire[127:0]rb;wire[8191:0]rd;
 wire r_rdy;integer reads=0,writes=0,cycles=0;reg[255:0]expectdata;
 wire[15:0]tagin=rt[7*16+:16]^((MUT==1)?16'd1:16'd0);
 wire[255:0]datain=rd[7*256+:256]^((MUT==3 && reads>=3)?256'd1:256'd0);
 assign rr=32'hffffffff;
 ot_qfd_protected_phy_pc #(.ENABLE(ENABLE),.PC(7)) dut(.*,
 .r_v(rv[7]),.r_pc((MUT==2)?5'd6:5'd7),.r_tag(tagin),.r_beat(rb[7*4+:4]),.r_data(datain));
 ot_hdc_hbm_model #(.NPC(32),.AW(31),.MEM_WORDS(65521),.CLK_PS(1024),.QD(8),.RQD(4),.RW(4)) mem(
 .clk(clk),.rst_n(rst_n),.req_v(p_v),.req_rdy(p_rdy),.req_we(p_we),.req_addr(p_addr),.req_len(p_len),.req_tag(p_tag),.req_wdata(p_data),.pc_room(),.rsp_v(rv),.rsp_rdy(rr),.rsp_tag(rt),.rsp_beat(rb),.rsp_data(rd));
 function automatic[287:0]encode(input[255:0]d);integer w;begin for(w=0;w<4;w=w+1)encode[w*72+:72]=encode64(d[w*64+:64]);end endfunction
 task automatic transaction(input integer n,input bit we);
 integer w;reg[255:0]d;reg[287:0]c;begin
 d={8{32'h76543210^32'(n)}};c=encode(d);
 @(negedge clk);while(!q_rdy)@(negedge clk);
 q_we=we;q_emb=n>=32;q_row=n>=32?19'd24427+19'((n-32)/16):19'(n/16);
 q_bank=5'(n%4);q_col=5'(n%16);q_sec=17'(n*13+9);q_lrow=8'(n/16);q_id=64'h1234567800000000+64'(n);q_code=c;
 if(MUT==4)q_row=64;
 q_v=1;@(negedge clk);q_v=0;
 while(!o_v && !fault)@(negedge clk);
 if(fault)$fatal(1,"provider fault MUT=%0d n=%0d",MUT,n);
 if(o_we!==we||o_emb!==q_emb||o_row!==q_row||o_bank!==q_bank||o_col!==q_col||o_sec!==q_sec||o_lrow!==q_lrow||o_id!==q_id||o_code!==c)$fatal(1,"metadata/code mismatch n=%0d",n);
 @(negedge clk);end endtask
 always @(posedge clk)if(rst_n)begin cycles<=cycles+1;if(cycles>40000)$fatal(1,"finite test incomplete");if(p_v&&p_rdy)begin
 if(p_we)writes<=writes+1;else reads<=reads+1;
 if(mem.pc_of(p_addr)!=7)$fatal(1,"address PC mismatch");
 if(p_len!=1)$fatal(1,"physical burst length");end end
 integer i;initial begin
 for(i=0;i<65521;i=i+1)mem.mem[i]=0;
 repeat(5)@(negedge clk);rst_n=1;
 if(!ENABLE)begin q_v=1;repeat(50)@(negedge clk);if(q_rdy||p_v||o_v||fault)$fatal(1,"default off");$display("PASS default off");$finish;end
 for(i=0;i<64;i=i+1)transaction(i,1);
 for(i=0;i<64;i=i+1)transaction(i,0);
 if(writes!=128||reads!=320)$fatal(1,"actual transaction count %0d %0d",writes,reads);
 $display("PASS 64 WR 64 RD writes=%0d reads=%0d cycles=%0d real256 tagged64id visibility",writes,reads,cycles);$finish;
 end
endmodule
