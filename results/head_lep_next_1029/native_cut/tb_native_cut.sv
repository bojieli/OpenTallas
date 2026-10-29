`timescale 1ns/1ps
module tb_native_cut;
reg clk=0; always #5 clk=~clk;
integer n,j; reg [31:0] rnd=32'h71bc2d09;
function automatic [31:0] rng(input [31:0] x); rng=x^(x<<13)^((x^(x<<13))>>17)^(((x^(x<<13))^((x^(x<<13))>>17))<<5); endfunction
reg [16:0] ep_rst_v;
reg [175:0] ep_mem_rst_n;
reg ep_in_valid;
wire ep_in_ready_g,ep_in_ready_d;
reg [551:0] ep_in_data;
reg ep_in_last;
wire ep_out_valid_g,ep_out_valid_d;
reg [2:0] ep_out_ready_v;
wire [551:0] ep_out_data_g,ep_out_data_d;
wire ep_out_last_g,ep_out_last_d;
wire ep_f_tx_v_g,ep_f_tx_v_d;
wire [594:0] ep_f_tx_g,ep_f_tx_d;
reg ep_f_rx_v;
reg [594:0] ep_f_rx;
wire ep_r_tx_v_g,ep_r_tx_v_d;
wire [52:0] ep_r_tx_g,ep_r_tx_d;
reg ep_r_rx_v;
reg [52:0] ep_r_rx;
wire ep_fault_g,ep_fault_d;
ot_s81hd_ep_native dut_ep(.clk(clk),.rst_v(ep_rst_v),.mem_rst_n(ep_mem_rst_n),.in_valid(ep_in_valid),.in_ready(ep_in_ready_d),.in_data(ep_in_data),.in_last(ep_in_last),.out_valid(ep_out_valid_d),.out_ready_v(ep_out_ready_v),.out_data(ep_out_data_d),.out_last(ep_out_last_d),.f_tx_v(ep_f_tx_v_d),.f_tx(ep_f_tx_d),.f_rx_v(ep_f_rx_v),.f_rx(ep_f_rx),.r_tx_v(ep_r_tx_v_d),.r_tx(ep_r_tx_d),.r_rx_v(ep_r_rx_v),.r_rx(ep_r_rx),.fault(ep_fault_d));
ot_s81ph_link_ep_safe4 #(.ACK_TIMEOUT(0),.ARS(24),.CHANNEL_CYCLES(100),.CHANNEL_CYCLES_B(700),.CREDITS(512),.DNR(1),.FCOPY(1),.FFW_P(595),.FLIT_BYTES(69),.KEEPALIVE(16),.MAX_RETRY(8),.MEM_NA(18),.MEM_NS(70),.MWR(1),.OLDREAD(1),.ORN(3),.PHY_DEN(4096),.PHY_NUM(211761),.PIPE(2),.REPLAY(0),.RFW_P(53),.RN(17),.RXPIPE(1),.RX_STAGES(5),.SEQW(10),.SRAM(1),.TOREG(1),.TX_STAGES(2),.WRL(2)) ref_ep(.clk(clk),.rst_v(ep_rst_v),.mem_rst_n(ep_mem_rst_n),.in_valid(ep_in_valid),.in_ready(ep_in_ready_g),.in_data(ep_in_data),.in_last(ep_in_last),.out_valid(ep_out_valid_g),.out_ready_v(ep_out_ready_v),.out_data(ep_out_data_g),.out_last(ep_out_last_g),.f_tx_v(ep_f_tx_v_g),.f_tx(ep_f_tx_g),.f_rx_v(ep_f_rx_v),.f_rx(ep_f_rx),.r_tx_v(ep_r_tx_v_g),.r_tx(ep_r_tx_g),.r_rx_v(ep_r_rx_v),.r_rx(ep_r_rx),.fault(ep_fault_g),.ch_b(1'b1));
reg credit_rst_in_n;
reg [34:0] credit_head_rst_n;
reg credit_rst_out_n;
reg credit_lo_v;
reg [552:0] credit_lo_d;
wire credit_lo_r_g,credit_lo_r_d;
wire credit_ep_in_v_g,credit_ep_in_v_d;
reg credit_ep_in_r;
wire [552:0] credit_ep_in_d_g,credit_ep_in_d_d;
reg credit_ep_out_v;
wire [2:0] credit_ep_out_r_g,credit_ep_out_r_d;
reg [552:0] credit_ep_out_d;
wire credit_li_v_g,credit_li_v_d;
wire [552:0] credit_li_d_g,credit_li_d_d;
reg credit_li_r;
wire credit_fault_g,credit_fault_d;
ot_s81hd_credit_native dut_credit(.clk(clk),.rst_in_n(credit_rst_in_n),.head_rst_n(credit_head_rst_n),.rst_out_n(credit_rst_out_n),.lo_v(credit_lo_v),.lo_d(credit_lo_d),.lo_r(credit_lo_r_d),.ep_in_v(credit_ep_in_v_d),.ep_in_r(credit_ep_in_r),.ep_in_d(credit_ep_in_d_d),.ep_out_v(credit_ep_out_v),.ep_out_r(credit_ep_out_r_d),.ep_out_d(credit_ep_out_d),.li_v(credit_li_v_d),.li_d(credit_li_d_d),.li_r(credit_li_r),.fault(credit_fault_d));
ot_link_credit_rx_b64 #(.W(553),.DEPTH(12),.WFREE(1),.LOCAL_HIT(1),.LOCAL_POP(1)) ref_ski(.clk(clk),.rst_n(credit_rst_in_n),.head_rst_n(credit_head_rst_n),.l_valid(credit_lo_v),.l_data(credit_lo_d),.l_credit(credit_lo_r_g),.o_valid(credit_ep_in_v_g),.o_ready(credit_ep_in_r),.o_data(credit_ep_in_d_g),.fault(credit_fault_g));
ot_link_credit_tx_rc #(.W(553),.CRED(12),.NR(3)) ref_sko(.clk(clk),.rst_n(credit_rst_out_n),.i_valid(credit_ep_out_v),.i_ready(credit_ep_out_r_g),.i_data(credit_ep_out_d),.l_valid(credit_li_v_g),.l_data(credit_li_d_g),.l_credit(credit_li_r));
initial begin
ep_rst_v=0;
ep_mem_rst_n=0;
ep_in_valid=0;
ep_in_data=0;
ep_in_last=0;
ep_out_ready_v=0;
ep_f_rx_v=0;
ep_f_rx=0;
ep_r_rx_v=0;
ep_r_rx=0;
credit_rst_in_n=0;
credit_head_rst_n=0;
credit_rst_out_n=0;
credit_lo_v=0;
credit_lo_d=0;
credit_ep_in_r=0;
credit_ep_out_v=0;
credit_ep_out_d=0;
credit_li_r=0;
for(n=0;n<1024;n=n+1) begin
@(negedge clk);
ep_rst_v= (n<8 || (n>=510 && n<518)) ? 0 : '1;
ep_mem_rst_n= (n<8 || (n>=510 && n<518)) ? 0 : '1;
for(j=0;j<$bits(ep_in_valid);j=j+1) begin rnd=rng(rnd); ep_in_valid = (ep_in_valid << 1) | rnd[0]; end
for(j=0;j<$bits(ep_in_data);j=j+1) begin rnd=rng(rnd); ep_in_data = (ep_in_data << 1) | rnd[0]; end
for(j=0;j<$bits(ep_in_last);j=j+1) begin rnd=rng(rnd); ep_in_last = (ep_in_last << 1) | rnd[0]; end
for(j=0;j<$bits(ep_out_ready_v);j=j+1) begin rnd=rng(rnd); ep_out_ready_v = (ep_out_ready_v << 1) | rnd[0]; end
for(j=0;j<$bits(ep_f_rx_v);j=j+1) begin rnd=rng(rnd); ep_f_rx_v = (ep_f_rx_v << 1) | rnd[0]; end
for(j=0;j<$bits(ep_f_rx);j=j+1) begin rnd=rng(rnd); ep_f_rx = (ep_f_rx << 1) | rnd[0]; end
for(j=0;j<$bits(ep_r_rx_v);j=j+1) begin rnd=rng(rnd); ep_r_rx_v = (ep_r_rx_v << 1) | rnd[0]; end
for(j=0;j<$bits(ep_r_rx);j=j+1) begin rnd=rng(rnd); ep_r_rx = (ep_r_rx << 1) | rnd[0]; end
credit_rst_in_n= (n<8 || (n>=510 && n<518)) ? 0 : '1;
credit_head_rst_n= (n<8 || (n>=510 && n<518)) ? 0 : '1;
credit_rst_out_n= (n<8 || (n>=510 && n<518)) ? 0 : '1;
for(j=0;j<$bits(credit_lo_v);j=j+1) begin rnd=rng(rnd); credit_lo_v = (credit_lo_v << 1) | rnd[0]; end
for(j=0;j<$bits(credit_lo_d);j=j+1) begin rnd=rng(rnd); credit_lo_d = (credit_lo_d << 1) | rnd[0]; end
for(j=0;j<$bits(credit_ep_in_r);j=j+1) begin rnd=rng(rnd); credit_ep_in_r = (credit_ep_in_r << 1) | rnd[0]; end
for(j=0;j<$bits(credit_ep_out_v);j=j+1) begin rnd=rng(rnd); credit_ep_out_v = (credit_ep_out_v << 1) | rnd[0]; end
for(j=0;j<$bits(credit_ep_out_d);j=j+1) begin rnd=rng(rnd); credit_ep_out_d = (credit_ep_out_d << 1) | rnd[0]; end
for(j=0;j<$bits(credit_li_r);j=j+1) begin rnd=rng(rnd); credit_li_r = (credit_li_r << 1) | rnd[0]; end
@(posedge clk); #1;
if (ep_in_ready_d !== ep_in_ready_g) $fatal(1,"MISMATCH ep_in_ready at %0d",n);
if (ep_out_valid_d !== ep_out_valid_g) $fatal(1,"MISMATCH ep_out_valid at %0d",n);
if (ep_out_data_d !== ep_out_data_g) $fatal(1,"MISMATCH ep_out_data at %0d",n);
if (ep_out_last_d !== ep_out_last_g) $fatal(1,"MISMATCH ep_out_last at %0d",n);
if (ep_f_tx_v_d !== ep_f_tx_v_g) $fatal(1,"MISMATCH ep_f_tx_v at %0d",n);
if (ep_f_tx_d !== ep_f_tx_g) $fatal(1,"MISMATCH ep_f_tx at %0d",n);
if (ep_r_tx_v_d !== ep_r_tx_v_g) $fatal(1,"MISMATCH ep_r_tx_v at %0d",n);
if (ep_r_tx_d !== ep_r_tx_g) $fatal(1,"MISMATCH ep_r_tx at %0d",n);
if (ep_fault_d !== ep_fault_g) $fatal(1,"MISMATCH ep_fault at %0d",n);
if (credit_lo_r_d !== credit_lo_r_g) $fatal(1,"MISMATCH credit_lo_r at %0d",n);
if (credit_ep_in_v_d !== credit_ep_in_v_g) $fatal(1,"MISMATCH credit_ep_in_v at %0d",n);
if (credit_ep_in_d_d !== credit_ep_in_d_g) $fatal(1,"MISMATCH credit_ep_in_d at %0d",n);
if (credit_ep_out_r_d !== credit_ep_out_r_g) $fatal(1,"MISMATCH credit_ep_out_r at %0d",n);
if (credit_li_v_d !== credit_li_v_g) $fatal(1,"MISMATCH credit_li_v at %0d",n);
if (credit_li_d_d !== credit_li_d_g) $fatal(1,"MISMATCH credit_li_d at %0d",n);
if (credit_fault_d !== credit_fault_g) $fatal(1,"MISMATCH credit_fault at %0d",n);
if(n==20 && $test$plusargs("mutant")) begin if ((~credit_lo_r_d) !== credit_lo_r_g) $fatal(1,"MUTANT CAUGHT ready polarity"); end
end
$display("NATIVE_CUT PASS cycles=%0d",n); $finish; end
endmodule
