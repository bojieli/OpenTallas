`timescale 1ns/1ps
module tb_state_capture_miter;
parameter integer MUT=0;
reg clk=0;always #5 clk=~clk;
  reg  lp_we=0;
  reg [2:0] lp_tag=0;
  reg [31:0] lp_data=0;
  reg  acc_we=0;
  reg [2:0] acc_tag=0;
  reg [31:0] acc_data=0;
  reg [1:0] carry_we=0;
  reg [2:0] carry0_tag=0;
  reg [2:0] carry1_tag=0;
  reg [1:0] carry0_src=0;
  reg [1:0] carry1_src=0;
  reg [31:0] carry0_data=0;
  reg [31:0] carry1_data=0;
  reg  read_add=0;
  reg  read_tx=0;
  reg  read_rr=0;
  reg  read_rhs_acc=0;
  reg  read_tx_acc=0;
  reg [2:0] add_tag=0;
  reg [2:0] tx_tag=0;
  reg [2:0] rr_tag=0;
  reg [1:0] add_src=0;
  wire [31:0] ref_rhs_add;
  wire [31:0] ref_carry_add;
  wire [31:0] ref_tx_data;
  wire [31:0] ref_acc_rr;
  wire [31:0] got_rhs_add; reg [31:0] delayed_rhs_add;
  wire [31:0] got_carry_add; reg [31:0] delayed_carry_add;
  wire [31:0] got_tx_data; reg [31:0] delayed_tx_data;
  wire [31:0] got_acc_rr; reg [31:0] delayed_acc_rr;
ot_hgi_coll_pring_static_state_lane ref_dut(
.clk(clk),
.lp_we(lp_we),
.lp_tag(lp_tag),
.lp_data(lp_data),
.acc_we(acc_we),
.acc_tag(acc_tag),
.acc_data(acc_data),
.carry_we(carry_we),
.carry0_tag(carry0_tag),
.carry1_tag(carry1_tag),
.carry0_src(carry0_src),
.carry1_src(carry1_src),
.carry0_data(carry0_data),
.carry1_data(carry1_data),
.read_add(read_add),
.read_tx(read_tx),
.read_rr(read_rr),
.read_rhs_acc(read_rhs_acc),
.read_tx_acc(read_tx_acc),
.add_tag(add_tag),
.tx_tag(tx_tag),
.rr_tag(rr_tag),
.add_src(add_src),
.rhs_add(ref_rhs_add),
.carry_add(ref_carry_add),
.tx_data(ref_tx_data),
.acc_rr(ref_acc_rr)
);
ot_hgi_coll_pring_static_state_capture_lane dut(
.clk(clk),
.lp_we(lp_we),
.lp_tag(lp_tag),
.lp_data(lp_data),
.acc_we(acc_we),
.acc_tag(acc_tag),
.acc_data(acc_data),
.carry_we(carry_we),
.carry0_tag(carry0_tag),
.carry1_tag(carry1_tag),
.carry0_src(carry0_src),
.carry1_src(carry1_src),
.carry0_data(carry0_data),
.carry1_data(carry1_data),
.read_add(read_add),
.read_tx(read_tx),
.read_rr(read_rr),
.read_rhs_acc(read_rhs_acc),
.read_tx_acc(read_tx_acc),
.add_tag(add_tag),
.tx_tag(tx_tag),
.rr_tag(rr_tag),
.add_src((add_src ^ (MUT==1 ? 2'b01:2'b00))),
.rhs_add(got_rhs_add),
.carry_add(got_carry_add),
.tx_data(got_tx_data),
.acc_rr(got_acc_rr)
);
always @(posedge clk) begin
delayed_rhs_add <= ref_rhs_add;
delayed_carry_add <= ref_carry_add;
delayed_tx_data <= ref_tx_data;
delayed_acc_rr <= ref_acc_rr;
end
reg [31:0] rng=32'h935271d3;
function automatic [31:0] nextval(input [31:0] a); reg [31:0] x;begin x=a^(a<<13);x=x^(x>>17);nextval=x^(x<<5);end endfunction
integer checks=0;
initial begin
for(integer cycle=0;cycle<8192;cycle=cycle+1)begin
@(negedge clk);
rng=nextval(rng); lp_we=rng;
rng=nextval(rng); lp_tag=rng;
rng=nextval(rng); lp_data=rng;
rng=nextval(rng); acc_we=rng;
rng=nextval(rng); acc_tag=rng;
rng=nextval(rng); acc_data=rng;
rng=nextval(rng); carry_we=rng;
rng=nextval(rng); carry0_tag=rng;
rng=nextval(rng); carry1_tag=rng;
rng=nextval(rng); carry0_src=rng;
rng=nextval(rng); carry1_src=rng;
rng=nextval(rng); carry0_data=rng;
rng=nextval(rng); carry1_data=rng;
rng=nextval(rng); read_add=rng;
rng=nextval(rng); read_tx=rng;
rng=nextval(rng); read_rr=rng;
rng=nextval(rng); read_rhs_acc=rng;
rng=nextval(rng); read_tx_acc=rng;
rng=nextval(rng); add_tag=rng;
rng=nextval(rng); tx_tag=rng;
rng=nextval(rng); rr_tag=rng;
rng=nextval(rng); add_src=rng;
@(posedge clk);#1;
if(cycle>128)begin
if(got_rhs_add !== delayed_rhs_add)$fatal(1,"CAPTURE_MITER mismatch cycle=%0d field=rhs_add got=%h expected=%h",cycle,got_rhs_add,delayed_rhs_add); checks=checks+1;
if(got_carry_add !== delayed_carry_add)$fatal(1,"CAPTURE_MITER mismatch cycle=%0d field=carry_add got=%h expected=%h",cycle,got_carry_add,delayed_carry_add); checks=checks+1;
if(got_tx_data !== delayed_tx_data)$fatal(1,"CAPTURE_MITER mismatch cycle=%0d field=tx_data got=%h expected=%h",cycle,got_tx_data,delayed_tx_data); checks=checks+1;
if(got_acc_rr !== delayed_acc_rr)$fatal(1,"CAPTURE_MITER mismatch cycle=%0d field=acc_rr got=%h expected=%h",cycle,got_acc_rr,delayed_acc_rr); checks=checks+1;
end
end
$display("CAPTURE_MITER PASS cycles=8192 checks=%0d actual_old_RTL_delay=1 input_bits=164 payload_bits=1536 read_face_bits=128 II=1",checks);$finish;
end
endmodule
