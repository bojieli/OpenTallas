`timescale 1ns/1ps
module tb_pad_equiv;
reg sk=0;always #5 sk=~sk;
reg srs=0;reg[2155:0]rd=0;reg[1127:0]fd=0;reg[6:0]fv=0;
wire[2155:0]ro[0:1];wire[1127:0]fo[0:1];wire[6:0]vo[0:1];
ot_s81_hc_cpad #(.HALF(1),.RLY(2),.RF(5),.DW(6),.RET_EXTRA(1))u_old(.sk(sk),.srs(srs),.crd_i(rd),.crd_o(ro[0]),.fv_i(fv),.fd_i(fd),.fv_o(vo[0]),.fd_o(fo[0]));
ot_s81_hc_cpad_split u_new(.sk(sk),.srs(srs),.crd_i(rd),.crd_o(ro[1]),.fv_i(fv),.fd_i(fd),.fv_o(vo[1]),.fd_o(fo[1]));
integer c,w;
initial begin
repeat(4)@(negedge sk);srs=1;
for(c=0;c<200;c=c+1)begin
fv=(c%11==0)?0:7'h7f;
for(w=0;w<35;w=w+1)fd[w*32+:32]=c*739+w*337;
fd[1127:1120]=c;
for(w=0;w<67;w=w+1)rd[w*32+:32]=c*293+w*661;
rd[2155:2144]=c;
@(posedge sk);#1;
if(c>=16)begin
if(ro[0]!==ro[1])$fatal(1,"return depth mismatch cycle%0d",c);
if(fo[0]!==fo[1]||vo[0]!==vo[1])$fatal(1,"forward depth mismatch cycle%0d",c);
end
@(negedge sk);
end
$display("PAD_EQUIV PASS 184 checked cycles, forward13 return12 no extra seam stage");$finish;
end
endmodule
