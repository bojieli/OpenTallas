module ver_native #(parameter integer CS_VER_D=0)(input wire clk,rst_n,input wire[227:0]din,input wire[2:0]vin,output wire[227:0]dout,output wire[2:0]vout);
wire[1:0]vp_c_e,vo_c_e,vp_c,vo_c;
wire[31:0]vp_hh_e,vp_kk_e,vp_dd_e,vp_hh,vp_kk,vp_dd;
wire[127:0]vo_y_e,vo_y;
wire vp_v_e,vo_v_e,vef_e,vp_v,vo_v,vef;
assign {vp_c_e,vp_hh_e,vp_kk_e,vp_dd_e,vo_c_e,vo_y_e}=din;
assign {vp_v_e,vo_v_e,vef_e}=vin;
    ot_s81sl_cst #(.W(2 + 96 + 2 + 128), .V(3), .D(CS_VER_D)) u_cst_ver (.clk(clk), .rst_n(rst_n),
        .d({vp_c_e, vp_hh_e, vp_kk_e, vp_dd_e, vo_c_e, vo_y_e}), .dv({vp_v_e, vo_v_e, vef_e}),
        .q({vp_c, vp_hh, vp_kk, vp_dd, vo_c, vo_y}), .qv({vp_v, vo_v, vef}));
assign dout={vp_c,vp_hh,vp_kk,vp_dd,vo_c,vo_y};assign vout={vp_v,vo_v,vef};
endmodule
module ver_top(input wire clk,rst_n,input wire[227:0]din,input wire[2:0]vin,input wire[1:0]mutsel,output wire[227:0]q0,q1,output wire[2:0]v0,v1,output wire[234:0]views);
wire[2:0]goodv;
ver_native #(.CS_VER_D(0)) old0(clk,rst_n,din,vin,q0,v0);
ver_native #(.CS_VER_D(1)) new1(clk,rst_n,din,vin,q1,goodv);
reg skew;always @(posedge clk or negedge rst_n) if(!rst_n)skew<=1'b0;else skew<=goodv[0];
reg noreset;always @(posedge clk)noreset<=vin[0];
assign v1={goodv[2:1],mutsel==2'd1?skew:mutsel==2'd2?noreset:goodv[0]};
//19weighted terminal groups:228unique payload bits plus7valid/fault views.
assign views={v1[0],q1[128],v1[1],q1[63:0],v1[0],q1[226],q1[145:130],q1[209:194],q1[177:162],v1[2],v1[0],q1[129],v1[1],q1[127:64],q1[227],q1[161:146],q1[225:210],q1[193:178],v1[2]};
endmodule
