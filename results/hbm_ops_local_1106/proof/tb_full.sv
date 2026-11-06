module tb_full;
reg clk=0,rst_n=0;reg scalar_load,scalar_enable;reg[31:0]scalar_data;reg[15:0]rd_re;reg[383:0]rd_addr;reg[31:0]rd_src;reg[7:0]stage_v,old_v;reg[15:0]stage_group,old_group;reg[119:0]stage_addr,old_addr;reg[2047:0]stage_data,old_data;
always @(posedge clk)begin old_v<=stage_v;old_group<=stage_group;old_addr<=stage_addr;old_data<=stage_data;end
wire[511:0] d_old0;wire f_old0;
ot_hgi_sfu_opsa_gblock #(.G(2'd0)) u_old0 (.clk(clk),.rst_n(rst_n),.scalar_load(scalar_load),.scalar_enable(scalar_enable),.scalar_data(scalar_data),.rd_re(rd_re),.rd_addr(rd_addr),.rd_src(rd_src),.rd_q(d_old0),.stage_v(old_v),.stage_group(old_group),.stage_addr(old_addr),.stage_data(old_data),.flt(f_old0));
wire[511:0] d_a0;wire f_a0;
ot_hgi_sfu_opsa_gblock_dist_1106 #(.G(2'd0),.RREG(0)) u_a0 (.clk(clk),.rst_n(rst_n),.scalar_load(scalar_load),.scalar_enable(scalar_enable),.scalar_data(scalar_data),.rd_re(rd_re),.rd_addr(rd_addr),.rd_src(rd_src),.rd_q(d_a0),.stage_v(stage_v),.stage_group(stage_group),.stage_addr(stage_addr),.stage_data(stage_data),.flt(f_a0));
wire[511:0] d_b0;wire f_b0;
ot_hgi_sfu_opsa_gblock_dist_1106 #(.G(2'd0),.RREG(1)) u_b0 (.clk(clk),.rst_n(rst_n),.scalar_load(scalar_load),.scalar_enable(scalar_enable),.scalar_data(scalar_data),.rd_re(rd_re),.rd_addr(rd_addr),.rd_src(rd_src),.rd_q(d_b0),.stage_v(stage_v),.stage_group(stage_group),.stage_addr(stage_addr),.stage_data(stage_data),.flt(f_b0));
wire[511:0] d_old1;wire f_old1;
ot_hgi_sfu_opsa_gblock #(.G(2'd1)) u_old1 (.clk(clk),.rst_n(rst_n),.scalar_load(scalar_load),.scalar_enable(scalar_enable),.scalar_data(scalar_data),.rd_re(rd_re),.rd_addr(rd_addr),.rd_src(rd_src),.rd_q(d_old1),.stage_v(old_v),.stage_group(old_group),.stage_addr(old_addr),.stage_data(old_data),.flt(f_old1));
wire[511:0] d_a1;wire f_a1;
ot_hgi_sfu_opsa_gblock_dist_1106 #(.G(2'd1),.RREG(0)) u_a1 (.clk(clk),.rst_n(rst_n),.scalar_load(scalar_load),.scalar_enable(scalar_enable),.scalar_data(scalar_data),.rd_re(rd_re),.rd_addr(rd_addr),.rd_src(rd_src),.rd_q(d_a1),.stage_v(stage_v),.stage_group(stage_group),.stage_addr(stage_addr),.stage_data(stage_data),.flt(f_a1));
wire[511:0] d_b1;wire f_b1;
ot_hgi_sfu_opsa_gblock_dist_1106 #(.G(2'd1),.RREG(1)) u_b1 (.clk(clk),.rst_n(rst_n),.scalar_load(scalar_load),.scalar_enable(scalar_enable),.scalar_data(scalar_data),.rd_re(rd_re),.rd_addr(rd_addr),.rd_src(rd_src),.rd_q(d_b1),.stage_v(stage_v),.stage_group(stage_group),.stage_addr(stage_addr),.stage_data(stage_data),.flt(f_b1));
reg[511:0]p0,p1;integer checked=0,mut=0;integer rv,row;
initial begin
scalar_load=1;scalar_enable=1;scalar_data=32'h12345678;rd_re=16'hffff;rd_src=0;rd_addr=0;stage_v=0;stage_group=0;stage_addr=0;stage_data=0;
for(integer n=0;n<1300;n=n+1)begin
rst_n=(n>5 && !(n>=800&&n<808));
scalar_load=(n%7==0);scalar_data=$random;scalar_enable=(n<10)?1:((n%11)<4);
for(integer l=0;l<16;l=l+1)begin rv=$random;row=(rv&32'h7fffffff)%64;rd_addr[l*24+:24]=row*16+l;end
for(integer j=0;j<8;j=j+1)begin
 rv=$random;row=(rv&32'h7fffffff)%64;stage_addr[j*15+:15]=(n<140)?(((n/2)%64)*16+8*(j%2)):(row*16+8*(j%2));
 stage_group[j*2+:2]=(n<140)?(n%2):($random%4);
 for(integer k=0;k<8;k=k+1)stage_data[j*256+k*32+:32]=$random;
end
stage_v=(n<140)?8'h03:$random;
#5;clk=1;#1;
if(n>155)begin
if(d_a0!==d_old0||d_a1!==d_old1)$fatal(1,"A full group mismatch n%0d",n);
if(d_b0!==p0||d_b1!==p1)$fatal(1,"B full group mismatch n%0d",n);
if(f_a0!==f_old0||f_a1!==f_old1||f_b0!==f_old0||f_b1!==f_old1)$fatal(1,"fullgroupfault mismatch n%0d",n);
checked=checked+1;if(d_old0!==p0||d_old1!==p1)mut=mut+1;
end
p0=d_old0;p1=d_old1;#4;clk=0;
end
if(mut==0)$fatal(1,"latencycontrolvacuous");
$display("PASS full_opsA_G0_G1 checks=%0d wordcompares=%0d latency_mutant=%0d",checked,checked*64,mut);$finish;
end
endmodule
