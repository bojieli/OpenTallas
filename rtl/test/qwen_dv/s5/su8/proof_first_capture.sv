module proof #(parameter MUT=0)(input wire ck,input wire [456:0] word,output wire fail);
reg [5:0] age=0;always @(posedge ck)if(age<63)age<=age+1;
wire rst_n=(age>=8);wire start=(age==15);wire [456:0] si={word[456:37],18'd8,18'd2,word[0]};
reg [456:0] si0,si1;always @(posedge ck)begin si0<=si;si1<=si0;end
wire [243:0] r_gb,n_gb;
wire [2:0] r_gv,n_gv;
wire [7:0] r_lv1,n_lv1;
wire [767:0] r_pd1,n_pd1;
wire [0:0] r_su_nr,n_su_nr;
wire [0:0] r_su_idle,n_su_idle;
wire [0:0] r_su_fault,n_su_fault;
wire [15:0] r_su_prog,n_su_prog;
wire [15:0] r_su_rows,n_su_rows;
qfd_dv_su7_control_projection u_ref(.ck(ck),.rst_n(rst_n),.start(start),.si(si),.l_retire(1'd0),.l_last(1'd0),.l_fault(8'd0),.kv_we(8'd0),.rd_v(1'd0),.red_busy(1'd0),.red_fault(1'd0),.lvm_we(8'd0),.gb(r_gb),.gv(r_gv),.lv1(r_lv1),.pd1(r_pd1),.su_nr(r_su_nr),.su_idle(r_su_idle),.su_fault(r_su_fault),.su_prog(r_su_prog),.su_rows(r_su_rows));
qfd_dv_s5_su8_rst3 #(.MUT(MUT)) u_new(.ck(ck),.rst_n(rst_n),.start(start),.si(si1),.l_retire(1'd0),.l_last(1'd0),.l_fault(8'd0),.kv_we(8'd0),.rd_v(1'd0),.red_busy(1'd0),.red_fault(1'd0),.lvm_we(8'd0),.gb(n_gb),.gv(n_gv),.lv1(n_lv1),.pd1(n_pd1),.su_nr(n_su_nr),.su_idle(n_su_idle),.su_fault(n_su_fault),.su_prog(n_su_prog),.su_rows(n_su_rows));
wire [1057:0] r_all={r_gb,r_gv,r_lv1,r_pd1,r_su_nr,r_su_idle,r_su_fault,r_su_prog,r_su_rows};
wire [1057:0] n_all={n_gb,n_gv,n_lv1,n_pd1,n_su_nr,n_su_idle,n_su_fault,n_su_prog,n_su_rows};
reg [1057:0] r0,r1,r2,r3;always @(posedge ck)begin r0<=r_all;r1<=r0;r2<=r1;r3<=r2;end
// No output-valid mask: EVERY raw output bit compares after first-command state capture.
assign fail=(age>=24)&&(|(n_all^r3));
endmodule
