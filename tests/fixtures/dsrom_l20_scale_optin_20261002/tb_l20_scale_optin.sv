`timescale 1ns/1ps
module tb_l20_scale_optin;
reg clk=0; always #0.5 clk=~clk;
reg rst_n=0,v=0; reg [1023:0] x=0;
wire vo,fo,pv,pf,ov,of,dv,df; wire [511:0] y,oy,dy;
wire [127:0] codes,dc;wire [15:0] scales,ds;wire dp, dpf;
ot_hdc_fp4qdq original(clk,rst_n,v,x,ov,oy,of);
ot_hdc_fp4qdq_l20_scale_optin defaults(.clk(clk),.rst_n(rst_n),.v(v),.x(x),.vo(dv),.y(dy),.fault(df),.packed_valid(dp),.packed_codes(dc),.packed_scales(ds),.packed_fault(dpf));
ot_hdc_fp4qdq_l20_scale_optin #(.QDQ4E_GOLDEN_SAT448(1),.CKV_PACKED_SIDEBAND(1)) repaired(.clk(clk),.rst_n(rst_n),.v(v),.x(x),.vo(vo),.y(y),.fault(fo),.packed_valid(pv),.packed_codes(codes),.packed_scales(scales),.packed_fault(pf));
localparam N=21088;
reg [1023:0] xin[0:N-1];reg [511:0] gold[0:N-1];reg [127:0] ec[0:N-1];reg [15:0] es[0:N-1];reg ef[0:N-1];
integer send=0,recv=0,cycle=0,j,epoch=0;integer due[0:N-1];
reg [8191:0] rowbf;reg [2047:0] rowcodes;reg [255:0] rowscales;
initial begin
$readmemh("inputs.hex",xin);$readmemh("golden.hex",gold);$readmemh("codes.hex",ec);$readmemh("scales.hex",es);$readmemh("faults.hex",ef);
repeat(4) @(negedge clk);rst_n=1;
while(send<N) begin
@(negedge clk);v=(send%19!=3 || cycle%2==0);
if(v) begin x=xin[send];due[send]=cycle+8;send=send+1;end
end
@(negedge clk);v=0;
wait(recv==N);repeat(12)@(negedge clk);
// Reset and drain exclude stale publication; no collector epoch implementation inferred.
rst_n=0;repeat(3)@(negedge clk);rst_n=1;repeat(12)@(negedge clk);
if(vo||pv||ov||dv)$fatal(1,"stale valid after reset/drain");
$display("PASS %0d beats including full512 rows, sidebands, optoff equality, invalid fault",N);$finish;
end
always @(posedge clk) begin
cycle=cycle+1;
#0.01;
if(rst_n) begin
if({dv,df,dy} !== {ov,of,oy})$fatal(1,"default-off differs original");
if(dp||dc!==0||ds!==0||dpf)$fatal(1,"default sideband not disabled");
if(vo!==ov)$fatal(1,"pipeline valid mismatch");
if(vo) begin
if(recv>=send || cycle!=due[recv])$fatal(1,"latency/order %0d cycle%0d due%0d",recv,cycle,due[recv]);
if(fo!==ef[recv]||pf!==fo||pv!==!ef[recv])$fatal(1,"fault/publication %0d",recv);
if(ef[recv] && {fo,y} !== {of,oy})$fatal(1,"invalid-row path changed");
if(!ef[recv])begin
if(y!==gold[recv]||codes!==ec[recv]||scales!==es[recv])$fatal(1,"golden/sideband mismatch beat%0d",recv);
rowbf[512*(recv%16)+:512]=y;rowcodes[128*(recv%16)+:128]=codes;rowscales[16*(recv%16)+:16]=scales;
if(recv%16==15)begin
for(j=0;j<16;j=j+1)begin
if(rowbf[512*j+:512]!==gold[recv-15+j]||rowcodes[128*j+:128]!==ec[recv-15+j]||rowscales[16*j+:16]!==es[recv-15+j])$fatal(1,"fullrow packing");
end end end
recv=recv+1;
end end end
initial begin repeat(63364)@(posedge clk);$fatal(1,"bounded watchdog");end
endmodule
