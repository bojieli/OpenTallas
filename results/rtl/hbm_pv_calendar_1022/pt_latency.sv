module tb;
reg clk=0; always #5 clk=~clk;
reg rst_n=0; reg[11:0] cmd[0:3]; reg[1023:0] x[0:3]; reg[31:0] v[0:3];
wire[267:0] t; wire[3:0] sf; wire jv,jm,jf; wire[31:0] jx;
for(genvar g=0;g<4;g++) begin
ot_hbm_su_red_pretree_s_m72 #(.LAT(6)) s(.clk(clk),.rst_n(rst_n),.tree_cmd(cmd[g]),.ro_x(x[g]),.ro_v(v[g]),.tree_o(t[67*g+:67]),.fault(sf[g]));
end
ot_hbm_su_red_pretree_j_r13_m73 #(.LAT(6)) j(.clk(clk),.rst_n(rst_n),.slice_t(t),.tree_v(jv),.tree_x(jx),.tree_max(jm),.fault(jf));
integer edge_n=0;
always @(posedge clk) begin
 if(rst_n) begin
  if(cmd[0][11]) $display("PT_LAT INPUT edge=%0d",edge_n);
  if(t[65]||t[32]) $display("PT_LAT SLICE edge=%0d t=%h",edge_n,t[66:0]);
  if(jv) $display("PT_LAT JOIN edge=%0d x=%h max=%b fault=%b/%b",edge_n,jx,jm,jf,sf);
 end
 edge_n<=edge_n+1;
end
initial begin
for(integer g=0;g<4;g++) begin cmd[g]=0;x[g]=0;v[g]=0;end
repeat(5) @(negedge clk);rst_n=1;
repeat(3) @(negedge clk);cmd[0]=12'h801;x[0]=32'h3f800000;v[0]=1;
@(negedge clk);cmd[0]=0;v[0]=0;
repeat(120) @(negedge clk);$finish;
end
endmodule
