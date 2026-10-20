module tb_io_copy;
reg ck=0; always #5 ck=~ck;
reg rn=0,hs_start=0,rz_publish=0,hub_fault=0;
reg [15:0] hs_ep=0,hs_cal_r=0,rz_epoch=0;
reg [5:0] hs_layer=0;
reg [13:0] hs_ctx=0;
reg [111:0] hs_cal_lo=0;
reg [127:0] rz_vector=0;
wire a_start,b_start,a_fv,b_fv,a_fault,b_fault;
wire [15:0] a_ep,b_ep,a_fe,b_fe;
wire [5:0] a_layer,b_layer;
wire [13:0] a_t,b_t;
wire [191:0] a_cal,b_cal;
wire [63:0] a_se,b_se;
wire [23:0] a_sl,b_sl;
wire [127:0] a_fr,b_fr;
qkd_ahub_static_io_safe a(.ck(ck),.rst_n(rn),.hs_start(hs_start),.hs_ep(hs_ep),.hs_layer(hs_layer),.hs_ctx(hs_ctx),.hs_cal_lo(hs_cal_lo),.hs_cal_r(hs_cal_r),.start(a_start),.epoch(a_ep),.layer(a_layer),.T(a_t),.hub_cal(a_cal),.si_epoch(a_se),.si_layer(a_sl),.rz_publish(rz_publish),.rz_epoch(rz_epoch),.rz_vector(rz_vector),.hub_fault(hub_fault),.fr_valid(a_fv),.fr_epoch(a_fe),.fr_rz(a_fr),.fault(a_fault));
qkd_ahub6_static_io_safe b(.ck(ck),.rst_group({4{rn}}),.hs_start(hs_start),.hs_ep(hs_ep),.hs_layer(hs_layer),.hs_ctx(hs_ctx),.hs_cal_lo(hs_cal_lo),.hs_cal_r(hs_cal_r),.start(b_start),.start_all(),.epoch(b_ep),.layer(b_layer),.T(b_t),.hub_cal(b_cal),.si_epoch(b_se),.si_layer(b_sl),.rz_publish(rz_publish),.rz_epoch(rz_epoch),.rz_vector(rz_vector),.hub_fault(hub_fault),.fr_valid(b_fv),.fr_epoch(b_fe),.fr_rz(b_fr),.fault(b_fault));
integer n,checked=0;
reg [31:0] seed=32'h196cc012;
function automatic [31:0] rnd();seed=seed^(seed<<13);seed=seed^(seed>>17);seed=seed^(seed<<5);return seed;endfunction
initial begin
for(n=0;n<12000;n=n+1)begin
 @(negedge ck);
 rn=(n%997)>3; hs_start=(n%71)==8 || (n%511)>506;
 hs_ep=rnd();hs_layer=rnd();hs_ctx=rnd();
 hs_cal_lo={rnd(),rnd(),rnd(),16'(3+rnd()%40)}; hs_cal_r=rnd()%5;
 rz_publish=(rnd()%10)==0;hub_fault=(rnd()%50)==0;
 rz_epoch=rnd();rz_vector={rnd(),rnd(),rnd(),rnd()};
 @(posedge ck);#1;
 if(n>8)begin
 checked=checked+1;
 if({a_start,a_ep,a_layer,a_t,a_cal,a_se,a_sl,a_fv,a_fe,a_fr,a_fault} !== {b_start,b_ep,b_layer,b_t,b_cal,b_se,b_sl,b_fv,b_fe,b_fr,b_fault})begin
 $display("AHUB6_IO_FAIL n=%0d fv=%b/%b fault=%b/%b",n,a_fv,b_fv,a_fault,b_fault);$fatal(1);
 end
 end
end
$display("AHUB6_IO_PASS checked=%0d",checked);$finish;
end
endmodule
