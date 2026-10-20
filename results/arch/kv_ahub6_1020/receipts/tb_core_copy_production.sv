module tb_core_copy;
reg clk=0;always #5 clk=~clk;
integer n,checked=0;reg [31:0] seed=32'h196cc012;
function automatic [31:0] rnd();seed=seed^(seed<<13);seed=seed^(seed>>17);seed=seed^(seed<<5);return seed;endfunction
reg [207:0] cal=0;
reg  rst_n=0;
reg  start=0;
reg  active_layer_parity=0;
reg [15:0] request_epoch=0;
reg [5:0] active_layer=0;
reg [13:0] T=0;
reg [3:0] si_valid=0;
reg [3:0] si_g=0;
reg [3:0] si_any=0;
reg [63:0] si_epoch=0;
reg [23:0] si_layer=0;
reg [7:0] si_type=0;
reg [7:0] si_hh=0;
reg [15:0] si_k=0;
reg [127:0] si_data=0;
wire [143:0] a_am;
wire [143:0] b_am;
wire [3:0] a_zh_start;
wire [3:0] b_zh_start;
wire [511:0] a_zh_we;
wire [511:0] b_zh_we;
wire [511:0] a_zh_sid;
wire [511:0] b_zh_sid;
wire [15:0] a_zh_iv;
wire [15:0] b_zh_iv;
wire [3:0] a_zh_g;
wire [3:0] b_zh_g;
wire [23:0] a_zh_p;
wire [23:0] b_zh_p;
reg [255:0] zh_root=0;
reg [15:0] zh_err=0;
wire  a_rc_v;
wire  b_rc_v;
wire [31:0] a_rc_x;
wire [31:0] b_rc_x;
reg [31:0] rc_y=0;
reg  rc_vo=0;
reg  rc_fault=0;
wire  a_rz_valid;
wire  b_rz_valid;
wire [1:0] a_rz_head;
wire [1:0] b_rz_head;
wire [31:0] a_rz_data;
wire [31:0] b_rz_data;
wire [15:0] a_rz_epoch;
wire [15:0] b_rz_epoch;
wire  a_rz_publish;
wire  b_rz_publish;
wire [127:0] a_rz4;
wire [127:0] b_rz4;
wire  a_fault;
wire  b_fault;
qkd_ahub_static_core_la_safe #(.Z_IN_STRIDE(4),.RS_RLY(1),.Z_RT(6)) a(.cal(cal),.clk(clk),.rst_n(rst_n),.start(start),.active_layer_parity(active_layer_parity),.request_epoch(request_epoch),.active_layer(active_layer),.T(T),.si_valid(si_valid),.si_g(si_g),.si_any(si_any),.si_epoch(si_epoch),.si_layer(si_layer),.si_type(si_type),.si_hh(si_hh),.si_k(si_k),.si_data(si_data),.am(a_am),.zh_start(a_zh_start),.zh_we(a_zh_we),.zh_sid(a_zh_sid),.zh_iv(a_zh_iv),.zh_g(a_zh_g),.zh_p(a_zh_p),.zh_root(zh_root),.zh_err(zh_err),.rc_v(a_rc_v),.rc_x(a_rc_x),.rc_y(rc_y),.rc_vo(rc_vo),.rc_fault(rc_fault),.rz_valid(a_rz_valid),.rz_head(a_rz_head),.rz_data(a_rz_data),.rz_epoch(a_rz_epoch),.rz_publish(a_rz_publish),.rz4(a_rz4),.fault(a_fault));
qkd_ahub6_static_core_la_safe #(.Z_IN_STRIDE(4),.RS_RLY(1),.Z_RT(6)) b(.cal(cal),.clk(clk),.rst_n(rst_n),.start(start),.active_layer_parity(active_layer_parity),.request_epoch(request_epoch),.active_layer(active_layer),.T(T),.si_valid(si_valid),.si_g(si_g),.si_any(si_any),.si_epoch(si_epoch),.si_layer(si_layer),.si_type(si_type),.si_hh(si_hh),.si_k(si_k),.si_data(si_data),.am(b_am),.zh_start(b_zh_start),.zh_we(b_zh_we),.zh_sid(b_zh_sid),.zh_iv(b_zh_iv),.zh_g(b_zh_g),.zh_p(b_zh_p),.zh_root(zh_root),.zh_err(zh_err),.rc_v(b_rc_v),.rc_x(b_rc_x),.rc_y(rc_y),.rc_vo(rc_vo),.rc_fault(rc_fault),.rz_valid(b_rz_valid),.rz_head(b_rz_head),.rz_data(b_rz_data),.rz_epoch(b_rz_epoch),.rz_publish(b_rz_publish),.rz4(b_rz4),.fault(b_fault),.start_all({32{start}}));
initial begin
for(n=0;n<12000;n=n+1)begin
@(negedge clk);
rst_n=(n%997)>3;start=(n%220)==8 || (n%997)==5 || (n%997)==6;
cal={16'd200,16'd170,16'd150,16'd40,16'd30,{4{16'd16}},{4{16'd10}}};
active_layer_parity={rnd()};
request_epoch={rnd()};
active_layer={rnd()};
case((n/220)%6)0:T=1;1:T=128;2:T=513;3:T=1024;4:T=4096;default:T=8192;endcase
si_valid={rnd()};
si_g={rnd()};
si_any={rnd()};
si_epoch={rnd(),rnd()};
si_layer={rnd()};
si_type={rnd()};
si_hh={rnd()};
si_k={rnd()};
si_data={rnd(),rnd(),rnd(),rnd()};
zh_root={rnd(),rnd(),rnd(),rnd(),rnd(),rnd(),rnd(),rnd()};
zh_err={rnd()};
rc_y={rnd()};
rc_vo={rnd()};
rc_fault={rnd()};
@(posedge clk);#1;
if(n>8)begin
checked=checked+1;
if({a_am,a_zh_start,a_zh_we,a_zh_sid,a_zh_iv,a_zh_g,a_zh_p,a_rc_v,a_rc_x,a_rz_valid,a_rz_head,a_rz_data,a_rz_epoch,a_rz_publish,a_rz4,a_fault}!=={b_am,b_zh_start,b_zh_we,b_zh_sid,b_zh_iv,b_zh_g,b_zh_p,b_rc_v,b_rc_x,b_rz_valid,b_rz_head,b_rz_data,b_rz_epoch,b_rz_publish,b_rz4,b_fault})begin
$display("AHUB6_CORE_FAIL n=%0d start=%b zh=%h/%h fault=%b/%b",n,start,a_zh_start,b_zh_start,a_fault,b_fault);$fatal(1);end
end
end
$display("AHUB6_CORE_PASS checked=%0d",checked);$finish;end
endmodule
