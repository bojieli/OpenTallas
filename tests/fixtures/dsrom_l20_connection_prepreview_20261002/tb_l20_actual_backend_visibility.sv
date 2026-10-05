`timescale 1ns/1ps
// PREPARED ONLY; no compilation or simulation authorized.
module tb_l20_actual_backend_visibility;
localparam NPC=32, AW=30, HAW=30, TAGW=16, LENW=4, BEATW=4, DW=256;
reg clk=0,rst_n=0; always #0.5 clk=~clk;
reg [3:0] w_v=0; wire [3:0] w_rdy,w_wr_done; localparam [255:0] DATA={32{8'hA5}};
integer pc; longint observed_ps,column_ps,earliest_visible_ps;
wire [3:0] m_v;
wire [3:0] m_rdy;
wire [4*HAW-1:0] m_addr;
wire [15:0] m_len;
wire [4*TAGW-1:0] m_tag;
wire [3:0] m_we;
wire [1023:0] m_wdata;
wire [127:0] m_wstrb;
wire [3:0] m_wr_done;
wire [3:0] s_v;
wire [3:0] s_rdy;
wire [4*TAGW-1:0] s_tag;
wire [15:0] s_beat;
wire [1023:0] s_data;
wire [3:0] mux_w_sv;
wire [4*TAGW-1:0] mux_w_stag;
wire [15:0] mux_w_sbeat;
wire [1023:0] mux_w_sdata;
wire [3:0] mux_c_rdy;
wire [3:0] mux_c_wr_done;
wire [3:0] mux_c_sv;
wire [4*TAGW-1:0] mux_c_stag;
wire [15:0] mux_c_sbeat;
wire [1023:0] mux_c_sdata;
wire [3:0] mux_p_rdy;
wire [3:0] mux_p_wr_done;
wire [3:0] mux_p_sv;
wire [4*TAGW-1:0] mux_p_stag;
wire [15:0] mux_p_sbeat;
wire [1023:0] mux_p_sdata;
wire  mux_fault;
wire [31:0] mux_rope_grants;
wire [31:0] mux_rope_wait_cycles;
ot_chip_v41x_kv_rope_reqmux #(.HAW(30),.TAGW(16)) mux(.clk(clk),.rst_n(rst_n),.w_v(w_v),.w_rdy(w_rdy),.w_addr({30'd311,90'd0}),.w_len(16'h1111),.w_tag(64'd0),.w_we(4'b1000),.w_wdata({DATA,768'd0}),.w_wstrb({32'hffffffff,96'd0}),.w_wr_done(w_wr_done),.w_sv(mux_w_sv),.w_srdy(4'hf),.w_stag(mux_w_stag),.w_sbeat(mux_w_sbeat),.w_sdata(mux_w_sdata),.c_v('0),.c_rdy(mux_c_rdy),.c_addr('0),.c_len('0),.c_tag('0),.c_we('0),.c_wdata('0),.c_wstrb('0),.c_wr_done(mux_c_wr_done),.c_sv(mux_c_sv),.c_srdy(4'hf),.c_stag(mux_c_stag),.c_sbeat(mux_c_sbeat),.c_sdata(mux_c_sdata),.p_v('0),.p_rdy(mux_p_rdy),.p_addr('0),.p_len('0),.p_tag('0),.p_we('0),.p_wdata('0),.p_wstrb('0),.p_wr_done(mux_p_wr_done),.p_sv(mux_p_sv),.p_srdy(4'hf),.p_stag(mux_p_stag),.p_sbeat(mux_p_sbeat),.p_sdata(mux_p_sdata),.m_v(m_v),.m_rdy(m_rdy),.m_addr(m_addr),.m_len(m_len),.m_tag(m_tag),.m_we(m_we),.m_wdata(m_wdata),.m_wstrb(m_wstrb),.m_wr_done(m_wr_done),.s_v(s_v),.s_rdy(s_rdy),.s_tag(s_tag),.s_beat(s_beat),.s_data(s_data),.fault(mux_fault),.rope_grants(mux_rope_grants),.rope_wait_cycles(mux_rope_wait_cycles));
assign m_rdy[2:0]=0;assign m_wr_done[2:0]=0;assign s_v[2:0]=0;assign s_tag[47:0]=0;assign s_beat[11:0]=0;assign s_data[767:0]=0;
wire [NPC-1:0] h_v;
wire [NPC-1:0] h_rdy;
wire [NPC*AW-1:0] h_addr;
wire [NPC*LENW-1:0] h_len;
wire [NPC*(TAGW+1)-1:0] h_tag;
wire [NPC-1:0] h_we;
wire [NPC*DW-1:0] h_wdata;
wire [NPC*DW/8-1:0] h_wstrb;
wire [NPC-1:0] h_wr_done;
wire [NPC-1:0] r_v;
wire [NPC-1:0] r_rdy;
wire [NPC*(TAGW+1)-1:0] r_tag;
wire [NPC*BEATW-1:0] r_beat;
wire [NPC*DW-1:0] r_data;
wire [NPC-1:0] arb_b_rdy;
wire [NPC-1:0] arb_b_wr_done;
wire [NPC-1:0] arb_b_rsp_v;
wire [NPC*TAGW-1:0] arb_b_rsp_tag;
wire [NPC*BEATW-1:0] arb_b_rsp_beat;
wire [NPC*DW-1:0] arb_b_rsp_data;
wire [31:0] arb_k_grants;
wire [31:0] arb_b_grants;
wire [31:0] arb_contended;
ot_chip_v41x_hbm_karb #(.NPC(32),.AW(30),.TAGW(16),.LENW(4),.BEATW(4),.DW(256),.PIPE_OUT(0),.PIPE_RSP(0)) arb(.clk(clk),.rst_n(rst_n),.b_v('0),.b_rdy(arb_b_rdy),.b_addr('0),.b_len('0),.b_tag('0),.b_we('0),.b_wdata('0),.b_wstrb('0),.b_wr_done(arb_b_wr_done),.b_rsp_v(arb_b_rsp_v),.b_rsp_rdy('1),.b_rsp_tag(arb_b_rsp_tag),.b_rsp_beat(arb_b_rsp_beat),.b_rsp_data(arb_b_rsp_data),.k_v(m_v[3+:1]),.k_rdy(m_rdy[3+:1]),.k_addr(m_addr[90+:30]),.k_len(m_len[12+:4]),.k_tag(m_tag[48+:16]),.k_we(m_we[3+:1]),.k_wdata(m_wdata[768+:256]),.k_wstrb(m_wstrb[96+:32]),.k_wr_done(m_wr_done[3+:1]),.k_rsp_v(s_v[3+:1]),.k_rsp_rdy(s_rdy[3+:1]),.k_rsp_tag(s_tag[48+:16]),.k_rsp_beat(s_beat[12+:4]),.k_rsp_data(s_data[768+:256]),.h_v(h_v),.h_rdy(h_rdy),.h_addr(h_addr),.h_len(h_len),.h_tag(h_tag),.h_we(h_we),.h_wdata(h_wdata),.h_wstrb(h_wstrb),.h_wr_done(h_wr_done),.r_v(r_v),.r_rdy(r_rdy),.r_tag(r_tag),.r_beat(r_beat),.r_data(r_data),.k_grants(arb_k_grants),.b_grants(arb_b_grants),.contended(arb_contended));
ot_hdc_v41x_idx_hbm #(.NPC(32),.AW(30),.TAGW(17),.LENW(4),.BEATW(4),.DW(256),.MEM_WORDS(2048),.MEM_MODE(0),.QD(64),.RQD(32),.REFPB(3),.CLK_PS(1000)) backend(.clk(clk),.rst_n(rst_n),.req_v(h_v),.req_rdy(h_rdy),.req_addr(h_addr),.req_len(h_len),.req_tag(h_tag),.req_we(h_we),.req_wdata(h_wdata),.req_wstrb(h_wstrb),.wr_done(h_wr_done),.rsp_v(r_v),.rsp_rdy(r_rdy),.rsp_tag(r_tag),.rsp_beat(r_beat),.rsp_data(r_data));
initial begin for(integer z=0;z<2048;z=z+1) backend.mem[z]=0;
 pc=((311>>2)^(311>>7)^(311>>12))&31;
 repeat(4) @(negedge clk);rst_n=1; @(negedge clk);w_v=8;
 do @(posedge clk); while(!w_rdy[3]); @(negedge clk);w_v=0;
 end
always @(negedge clk) if(rst_n && w_wr_done[3]) begin
 column_ps=backend.h_tcol[pc];observed_ps=(backend.cyc-1)*1000;earliest_visible_ps=column_ps+backend.CWL_PS+backend.BURST_PS;
 if(backend.mem[311]!==DATA || backend.st_wr[pc]!=1 || observed_ps<column_ps || observed_ps>=earliest_visible_ps) $fatal(1,"actual backend early completion witness mismatch");
 $display("NEGATIVE_WITNESS actual W backing update and WRdone at %0dps, column %0dps, earliest burst visibility %0dps; NOT_VISIBLE_ACK",observed_ps,column_ps,earliest_visible_ps);$finish;
end
initial begin repeat(3000) @(posedge clk);$fatal(1,"bounded actual backend witness timeout");end
endmodule
