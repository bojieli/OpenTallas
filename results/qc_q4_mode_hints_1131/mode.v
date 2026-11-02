(* keep_hierarchy="yes" *) module qfd_dv_station_mode #(parameter integer ID=0,USE2=1)(input wire ck,rst_n,cfg_v,input wire[1:0] mode,output wire[3:0] q);
reg[2:0] used_q;
always @(posedge ck or negedge rst_n) if(!rst_n) used_q<=3'b001;else if(cfg_v) used_q<={mode==3,mode==1,mode==0};
assign {q[3],q[1],q[0]}=used_q;
generate if(USE2) begin:g_two
reg m2;always @(posedge ck or negedge rst_n) if(!rst_n)m2<=0;else if(cfg_v)m2<=mode==2;assign q[2]=m2;
end else begin:g_no_two assign q[2]=1'b0;end endgenerate
endmodule
module mode_miter #(parameter MUT=0)(input ck,rst_n,cfg_v,input [1:0]mode,output eq);
wire[3:0]a,b;
qfd_dv_station_mode #(.ID(16),.USE2(1)) x(.ck(ck),.rst_n(rst_n),.cfg_v(cfg_v),.mode(mode),.q(a));
qfd_dv_station_mode #(.ID(17),.USE2(0)) y(.ck(ck),.rst_n(rst_n),.cfg_v(cfg_v),.mode(mode ^ (MUT ? 2'd1 : 2'd0)),.q(b));
assign eq= a[0]==b[0] && a[1]==b[1];
endmodule
