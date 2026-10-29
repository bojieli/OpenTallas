module tb;reg clk=0,rst_n=0,clear=0,in_v=0,load_v=0,add_read=0,add_issue=0,pub_read=0,pub_issue=0,pub_bf16=0,pub_release=0;
reg [544:0] in_flit=0;reg [3:0] load_tag=0,read_tag=0,pub_tag_a=0,pub_tag_b=0;reg [32:0] pub_meta=0;
wire av,bv,af,bf;wire[544:0] ad,bd;wire[7:0] ac,bc;integer errors=0,checks=0;integer seed=32'h6211aa37;
ot_hgi_coll_reduce_static #(.LOCAL_CTRL(0)) a(.clk_control(clk),.clk_state({16{clk}}),.clk_add({16{clk}}),.rst_n(rst_n),.clear(clear),.in_v(in_v),.in_flit(in_flit),.load_v(load_v),.load_tag(load_tag),.add_read(add_read),.read_tag(read_tag),.add_issue(add_issue),.pub_read(pub_read),.pub_tag_a(pub_tag_a),.pub_tag_b(pub_tag_b),.pub_bf16(pub_bf16),.pub_meta(pub_meta),.pub_release(pub_release),.pub_issue(pub_issue),.out_v(av),.out_flit(ad),.fault(af),.fault_cause(ac));
ot_hgi_coll_reduce_static #(.LOCAL_CTRL(1)) b(.clk_control(clk),.clk_state({16{clk}}),.clk_add({16{clk}}),.rst_n(rst_n),.clear(clear),.in_v(in_v),.in_flit(in_flit),.load_v(load_v),.load_tag(load_tag),.add_read(add_read),.read_tag(read_tag),.add_issue(add_issue),.pub_read(pub_read),.pub_tag_a(pub_tag_a),.pub_tag_b(pub_tag_b),.pub_bf16(pub_bf16),.pub_meta(pub_meta),.pub_release(pub_release),.pub_issue(pub_issue),.out_v(bv),.out_flit(bd),.fault(bf),.fault_cause(bc));
task tick;begin #5;clk=1;#1;checks=checks+1;
if({av,ad,af,ac}!=={bv,bd,bf,bc})begin errors=errors+1;if(errors<5)$display("MISMATCH checks=%0d",checks);end
#4;clk=0;end endtask
initial begin repeat(2)tick();rst_n=1;
for(integer n=0;n<4096;n=n+1)begin
rst_n=(n%997!=0);clear=($random(seed)%127==0);
in_v=$random(seed);load_v=$random(seed);add_read=$random(seed);add_issue=$random(seed);
pub_read=$random(seed);pub_issue=$random(seed);pub_release=$random(seed);pub_bf16=$random(seed);
load_tag=$random(seed);read_tag=$random(seed);pub_tag_a=$random(seed);pub_tag_b=$random(seed);pub_meta={$random(seed),1'b0};
for(integer j=0;j<17;j=j+1)in_flit[j*32+:32]=$random(seed);in_flit[544]=$random(seed);
tick();end
$display("LOCKSTEP checks=%0d errors=%0d",checks,errors);if(errors)$fatal(1);$finish;end endmodule
