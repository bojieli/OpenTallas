module hbm_arch_q_b110 (
    input  wire clk,
    input  wire arst_n,
    input wire [3:0] strap_u_sfucore_Q_lane0_map_lane_j,    
    input wire [3:0] strap_u_sfucore_Q_lane1_map_lane_j,    
    input wire [3:0] strap_u_sfucore_Q_lane2_map_lane_j,    
    input wire [3:0] strap_u_sfucore_Q_lane3_map_lane_j,    
    output wire rst_o_0,    
    input  wire [128:0] L5_i,    
    input  wire [256:0] xi_u_sfucore_Q_lane0_lane_rd_q__0,    
    input  wire [256:0] xi_u_sfucore_Q_lane0_lane_rd_q__1,    
    input  wire [1022:0] xi_u_sfucore_Q_lane0_map_i_emit,    
    output wire [330:0] L23_o,    
    output wire [96:0] xo_u_sfucore_Q_lane0_lane_rd_addr,    
    output wire [4:0] xo_u_sfucore_Q_lane0_lane_rd_re,    
    output wire [8:0] xo_u_sfucore_Q_lane0_lane_rd_src,    
    output wire [1:0] xo_u_sfucore_Q_lane0_lane_ro_v,    
    output wire [32:0] xo_u_sfucore_Q_lane0_lane_ro_x,    
    output wire [24:0] xo_u_sfucore_Q_lane0_lane_vm_waddr,    
    output wire [32:0] xo_u_sfucore_Q_lane0_lane_vm_wdata,    
    output wire [1:0] xo_u_sfucore_Q_lane0_lane_vm_we,    
    output wire [1:0] xo_u_sfucore_Q_lane1_lane_coll,    
    output wire [1:0] xo_u_sfucore_Q_lane1_lane_fault,    
    output wire [96:0] xo_u_sfucore_Q_lane1_lane_rd_addr,    
    output wire [4:0] xo_u_sfucore_Q_lane1_lane_rd_re,    
    output wire [8:0] xo_u_sfucore_Q_lane1_lane_rd_src,    
    output wire [1:0] xo_u_sfucore_Q_lane1_lane_ro_v,    
    output wire [32:0] xo_u_sfucore_Q_lane1_lane_ro_x,    
    output wire [24:0] xo_u_sfucore_Q_lane1_lane_vm_waddr,    
    output wire [32:0] xo_u_sfucore_Q_lane1_lane_vm_wdata,    
    output wire [1:0] xo_u_sfucore_Q_lane1_lane_vm_we,    
    output wire [1:0] xo_u_sfucore_Q_lane2_lane_coll,    
    output wire [1:0] xo_u_sfucore_Q_lane2_lane_fault,    
    output wire [96:0] xo_u_sfucore_Q_lane2_lane_rd_addr,    
    output wire [4:0] xo_u_sfucore_Q_lane2_lane_rd_re,    
    output wire [8:0] xo_u_sfucore_Q_lane2_lane_rd_src,    
    output wire [1:0] xo_u_sfucore_Q_lane2_lane_ro_v,    
    output wire [32:0] xo_u_sfucore_Q_lane2_lane_ro_x,    
    output wire [24:0] xo_u_sfucore_Q_lane2_lane_vm_waddr,    
    output wire [32:0] xo_u_sfucore_Q_lane2_lane_vm_wdata,    
    output wire [1:0] xo_u_sfucore_Q_lane2_lane_vm_we,    
    output wire [1:0] xo_u_sfucore_Q_lane3_lane_coll,    
    output wire [1:0] xo_u_sfucore_Q_lane3_lane_fault,    
    output wire [96:0] xo_u_sfucore_Q_lane3_lane_rd_addr,    
    output wire [4:0] xo_u_sfucore_Q_lane3_lane_rd_re,    
    output wire [8:0] xo_u_sfucore_Q_lane3_lane_rd_src,    
    output wire [1:0] xo_u_sfucore_Q_lane3_lane_ro_v,    
    output wire [32:0] xo_u_sfucore_Q_lane3_lane_ro_x,    
    output wire [24:0] xo_u_sfucore_Q_lane3_lane_vm_waddr,    
    output wire [32:0] xo_u_sfucore_Q_lane3_lane_vm_wdata,    
    output wire [1:0] xo_u_sfucore_Q_lane3_lane_vm_we,    
    input  wire [11:0] L117x6_i,    
    output wire [11:0] L117x6_o,    
    input  wire [2:0] L138x6_i,    
    output wire [2:0] L138x6_o,    
    input  wire [634:0] L48x9_i,    
    output wire [634:0] L48x9_o,    
    input  wire [612:0] L53x3_i,    
    output wire [612:0] L53x3_o,    
    input  wire [828:0] L6br0_2_i,    
    output wire [828:0] L6br0_2_o    
);
    wire [127:0] L5_i_q;
    wire L5_i_eq;
    wire [255:0] xi_u_sfucore_Q_lane0_lane_rd_q__0_q;
    wire xi_u_sfucore_Q_lane0_lane_rd_q__0_eq;
    wire [255:0] xi_u_sfucore_Q_lane0_lane_rd_q__1_q;
    wire xi_u_sfucore_Q_lane0_lane_rd_q__1_eq;
    wire [1021:0] xi_u_sfucore_Q_lane0_map_i_emit_q;
    wire xi_u_sfucore_Q_lane0_map_i_emit_eq;
    wire [0:0] w_u_sfucore_Q_lane0_lane_coll;
    wire [0:0] w_u_sfucore_Q_lane0_lane_fault;
    wire [23:0] w_u_sfucore_Q_lane0_lane_kv_waddr;
    wire [31:0] w_u_sfucore_Q_lane0_lane_kv_wdata;
    wire [0:0] w_u_sfucore_Q_lane0_lane_kv_we;
    wire [95:0] w_u_sfucore_Q_lane0_lane_rd_addr;
    wire [3:0] w_u_sfucore_Q_lane0_lane_rd_re;
    wire [7:0] w_u_sfucore_Q_lane0_lane_rd_src;
    wire [0:0] w_u_sfucore_Q_lane0_lane_ro_v;
    wire [31:0] w_u_sfucore_Q_lane0_lane_ro_x;
    wire [23:0] w_u_sfucore_Q_lane0_lane_vi_addr;
    wire [0:0] w_u_sfucore_Q_lane0_lane_vi_re;
    wire [23:0] w_u_sfucore_Q_lane0_lane_vm_waddr;
    wire [31:0] w_u_sfucore_Q_lane0_lane_vm_wdata;
    wire [0:0] w_u_sfucore_Q_lane0_lane_vm_we;
    wire [0:0] w_u_sfucore_Q_lane1_lane_coll;
    wire [0:0] w_u_sfucore_Q_lane1_lane_fault;
    wire [23:0] w_u_sfucore_Q_lane1_lane_kv_waddr;
    wire [31:0] w_u_sfucore_Q_lane1_lane_kv_wdata;
    wire [0:0] w_u_sfucore_Q_lane1_lane_kv_we;
    wire [95:0] w_u_sfucore_Q_lane1_lane_rd_addr;
    wire [3:0] w_u_sfucore_Q_lane1_lane_rd_re;
    wire [7:0] w_u_sfucore_Q_lane1_lane_rd_src;
    wire [0:0] w_u_sfucore_Q_lane1_lane_ro_v;
    wire [31:0] w_u_sfucore_Q_lane1_lane_ro_x;
    wire [23:0] w_u_sfucore_Q_lane1_lane_vi_addr;
    wire [0:0] w_u_sfucore_Q_lane1_lane_vi_re;
    wire [23:0] w_u_sfucore_Q_lane1_lane_vm_waddr;
    wire [31:0] w_u_sfucore_Q_lane1_lane_vm_wdata;
    wire [0:0] w_u_sfucore_Q_lane1_lane_vm_we;
    wire [0:0] w_u_sfucore_Q_lane2_lane_coll;
    wire [0:0] w_u_sfucore_Q_lane2_lane_fault;
    wire [23:0] w_u_sfucore_Q_lane2_lane_kv_waddr;
    wire [31:0] w_u_sfucore_Q_lane2_lane_kv_wdata;
    wire [0:0] w_u_sfucore_Q_lane2_lane_kv_we;
    wire [95:0] w_u_sfucore_Q_lane2_lane_rd_addr;
    wire [3:0] w_u_sfucore_Q_lane2_lane_rd_re;
    wire [7:0] w_u_sfucore_Q_lane2_lane_rd_src;
    wire [0:0] w_u_sfucore_Q_lane2_lane_ro_v;
    wire [31:0] w_u_sfucore_Q_lane2_lane_ro_x;
    wire [23:0] w_u_sfucore_Q_lane2_lane_vi_addr;
    wire [0:0] w_u_sfucore_Q_lane2_lane_vi_re;
    wire [23:0] w_u_sfucore_Q_lane2_lane_vm_waddr;
    wire [31:0] w_u_sfucore_Q_lane2_lane_vm_wdata;
    wire [0:0] w_u_sfucore_Q_lane2_lane_vm_we;
    wire [0:0] w_u_sfucore_Q_lane3_lane_coll;
    wire [0:0] w_u_sfucore_Q_lane3_lane_fault;
    wire [23:0] w_u_sfucore_Q_lane3_lane_kv_waddr;
    wire [31:0] w_u_sfucore_Q_lane3_lane_kv_wdata;
    wire [0:0] w_u_sfucore_Q_lane3_lane_kv_we;
    wire [95:0] w_u_sfucore_Q_lane3_lane_rd_addr;
    wire [3:0] w_u_sfucore_Q_lane3_lane_rd_re;
    wire [7:0] w_u_sfucore_Q_lane3_lane_rd_src;
    wire [0:0] w_u_sfucore_Q_lane3_lane_ro_v;
    wire [31:0] w_u_sfucore_Q_lane3_lane_ro_x;
    wire [23:0] w_u_sfucore_Q_lane3_lane_vi_addr;
    wire [0:0] w_u_sfucore_Q_lane3_lane_vi_re;
    wire [23:0] w_u_sfucore_Q_lane3_lane_vm_waddr;
    wire [31:0] w_u_sfucore_Q_lane3_lane_vm_wdata;
    wire [0:0] w_u_sfucore_Q_lane3_lane_vm_we;
    wire [11:0] L117x6_o_s0;
    wire [2:0] L138x6_o_s0;
    wire [634:0] L48x9_o_s0;
    wire [634:0] L48x9_o_s1;
    wire [634:0] L48x9_o_s2;
    wire [612:0] L53x3_o_s0;
    wire [612:0] L53x3_o_s1;
    wire [828:0] L6br0_2_o_s0;
     
    wire rst_root_n;
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));   
    wire rst_n_t0;
    wire rst_n_t1;
    wire rst_n_t2;
    wire rst_n_t3;
    wire rst_n_t4;
    wire rst_n_t5;
    wire rst_n_t6;
    wire rst_n_t7;
    wire rst_n_t8;
    wire rst_rl_0;
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));   
    wire rst_rl_1;
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));   
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_n_t3));   
    wire rst_rl_3;
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_0), .q(rst_rl_3));   
    ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_n_t1));   
    wire rst_rl_5;
    ot_dp_rrelay u_rrl_5 (.clk(clk), .d(rst_root_n), .q(rst_rl_5));   
    wire rst_rl_6;
    ot_dp_rrelay u_rrl_6 (.clk(clk), .d(rst_rl_5), .q(rst_rl_6));   
    ot_dp_rrelay u_rrl_7 (.clk(clk), .d(rst_rl_6), .q(rst_n_t4));   
    wire rst_rl_8;
    ot_dp_rrelay u_rrl_8 (.clk(clk), .d(rst_rl_5), .q(rst_rl_8));   
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_n_t2));   
    ot_dp_rrelay u_rrl_10 (.clk(clk), .d(rst_rl_8), .q(rst_n_t0));   
    wire rst_rl_11;
    ot_dp_rrelay u_rrl_11 (.clk(clk), .d(rst_rl_5), .q(rst_rl_11));   
    ot_dp_rrelay u_rrl_12 (.clk(clk), .d(rst_rl_11), .q(rst_n_t6));   
    wire rst_rl_13;
    ot_dp_rrelay u_rrl_13 (.clk(clk), .d(rst_root_n), .q(rst_rl_13));   
    wire rst_rl_14;
    ot_dp_rrelay u_rrl_14 (.clk(clk), .d(rst_rl_13), .q(rst_rl_14));   
    ot_dp_rrelay u_rrl_15 (.clk(clk), .d(rst_rl_14), .q(rst_n_t5));   
    wire rst_rl_16;
    ot_dp_rrelay u_rrl_16 (.clk(clk), .d(rst_rl_13), .q(rst_rl_16));   
    ot_dp_rrelay u_rrl_17 (.clk(clk), .d(rst_rl_16), .q(rst_n_t7));   
    wire rst_rl_18;
    ot_dp_rrelay u_rrl_18 (.clk(clk), .d(rst_root_n), .q(rst_rl_18));   
    wire rst_rl_19;
    ot_dp_rrelay u_rrl_19 (.clk(clk), .d(rst_rl_18), .q(rst_rl_19));   
    ot_dp_rrelay u_rrl_20 (.clk(clk), .d(rst_rl_19), .q(rst_o_0));   
    ot_dp_rrelay u_rrl_20_t (.clk(clk), .d(rst_rl_19), .q(rst_n_t8));   
    wire rst_n = rst_n_t4;
    ot_dp_st #(.W(128)) u_bin_L5_i (.clk(clk), .rst_n(rst_n), .d(L5_i[127:0]), .ea(L5_i[128]), .q(L5_i_q), .eq(L5_i_eq));
    ot_dp_st #(.W(256)) u_bin_xi_u_sfucore_Q_lane0_lane_rd_q__0 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_lane0_lane_rd_q__0[255:0]), .ea(xi_u_sfucore_Q_lane0_lane_rd_q__0[256]), .q(xi_u_sfucore_Q_lane0_lane_rd_q__0_q), .eq(xi_u_sfucore_Q_lane0_lane_rd_q__0_eq));
    ot_dp_st #(.W(256)) u_bin_xi_u_sfucore_Q_lane0_lane_rd_q__1 (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_lane0_lane_rd_q__1[255:0]), .ea(xi_u_sfucore_Q_lane0_lane_rd_q__1[256]), .q(xi_u_sfucore_Q_lane0_lane_rd_q__1_q), .eq(xi_u_sfucore_Q_lane0_lane_rd_q__1_eq));
    ot_dp_st #(.W(1022)) u_bin_xi_u_sfucore_Q_lane0_map_i_emit (.clk(clk), .rst_n(rst_n), .d(xi_u_sfucore_Q_lane0_map_i_emit[1021:0]), .ea(xi_u_sfucore_Q_lane0_map_i_emit[1022]), .q(xi_u_sfucore_Q_lane0_map_i_emit_q), .eq(xi_u_sfucore_Q_lane0_map_i_emit_eq));
    ot_dp_st #(.W(330)) u_bout_L23_o (.clk(clk), .rst_n(rst_n), .d({w_u_sfucore_Q_lane0_lane_fault[0], w_u_sfucore_Q_lane0_lane_coll[0], w_u_sfucore_Q_lane3_lane_vi_re[0], w_u_sfucore_Q_lane3_lane_vi_addr[23:0], w_u_sfucore_Q_lane3_lane_kv_we[0], w_u_sfucore_Q_lane3_lane_kv_wdata[31:0], w_u_sfucore_Q_lane3_lane_kv_waddr[23:0], w_u_sfucore_Q_lane2_lane_vi_re[0], w_u_sfucore_Q_lane2_lane_vi_addr[23:0], w_u_sfucore_Q_lane2_lane_kv_we[0], w_u_sfucore_Q_lane2_lane_kv_wdata[31:0], w_u_sfucore_Q_lane2_lane_kv_waddr[23:0], w_u_sfucore_Q_lane1_lane_vi_re[0], w_u_sfucore_Q_lane1_lane_vi_addr[23:0], w_u_sfucore_Q_lane1_lane_kv_we[0], w_u_sfucore_Q_lane1_lane_kv_wdata[31:0], w_u_sfucore_Q_lane1_lane_kv_waddr[23:0], w_u_sfucore_Q_lane0_lane_vi_re[0], w_u_sfucore_Q_lane0_lane_vi_addr[23:0], w_u_sfucore_Q_lane0_lane_kv_we[0], w_u_sfucore_Q_lane0_lane_kv_wdata[31:0], w_u_sfucore_Q_lane0_lane_kv_waddr[23:0]}), .ea(rst_n), .q(L23_o[329:0]), .eq(L23_o[330]));
    ot_dp_st #(.W(96)) u_bout_xo_u_sfucore_Q_lane0_lane_rd_addr (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane0_lane_rd_addr[95:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane0_lane_rd_addr[95:0]), .eq(xo_u_sfucore_Q_lane0_lane_rd_addr[96]));
    ot_dp_st #(.W(4)) u_bout_xo_u_sfucore_Q_lane0_lane_rd_re (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane0_lane_rd_re[3:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane0_lane_rd_re[3:0]), .eq(xo_u_sfucore_Q_lane0_lane_rd_re[4]));
    ot_dp_st #(.W(8)) u_bout_xo_u_sfucore_Q_lane0_lane_rd_src (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane0_lane_rd_src[7:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane0_lane_rd_src[7:0]), .eq(xo_u_sfucore_Q_lane0_lane_rd_src[8]));
    ot_dp_st #(.W(1)) u_bout_xo_u_sfucore_Q_lane0_lane_ro_v (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane0_lane_ro_v[0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane0_lane_ro_v[0:0]), .eq(xo_u_sfucore_Q_lane0_lane_ro_v[1]));
    ot_dp_st #(.W(32)) u_bout_xo_u_sfucore_Q_lane0_lane_ro_x (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane0_lane_ro_x[31:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane0_lane_ro_x[31:0]), .eq(xo_u_sfucore_Q_lane0_lane_ro_x[32]));
    ot_dp_st #(.W(24)) u_bout_xo_u_sfucore_Q_lane0_lane_vm_waddr (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane0_lane_vm_waddr[23:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane0_lane_vm_waddr[23:0]), .eq(xo_u_sfucore_Q_lane0_lane_vm_waddr[24]));
    ot_dp_st #(.W(32)) u_bout_xo_u_sfucore_Q_lane0_lane_vm_wdata (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane0_lane_vm_wdata[31:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane0_lane_vm_wdata[31:0]), .eq(xo_u_sfucore_Q_lane0_lane_vm_wdata[32]));
    ot_dp_st #(.W(1)) u_bout_xo_u_sfucore_Q_lane0_lane_vm_we (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane0_lane_vm_we[0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane0_lane_vm_we[0:0]), .eq(xo_u_sfucore_Q_lane0_lane_vm_we[1]));
    ot_dp_st #(.W(1)) u_bout_xo_u_sfucore_Q_lane1_lane_coll (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane1_lane_coll[0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane1_lane_coll[0:0]), .eq(xo_u_sfucore_Q_lane1_lane_coll[1]));
    ot_dp_st #(.W(1)) u_bout_xo_u_sfucore_Q_lane1_lane_fault (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane1_lane_fault[0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane1_lane_fault[0:0]), .eq(xo_u_sfucore_Q_lane1_lane_fault[1]));
    ot_dp_st #(.W(96)) u_bout_xo_u_sfucore_Q_lane1_lane_rd_addr (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane1_lane_rd_addr[95:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane1_lane_rd_addr[95:0]), .eq(xo_u_sfucore_Q_lane1_lane_rd_addr[96]));
    ot_dp_st #(.W(4)) u_bout_xo_u_sfucore_Q_lane1_lane_rd_re (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane1_lane_rd_re[3:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane1_lane_rd_re[3:0]), .eq(xo_u_sfucore_Q_lane1_lane_rd_re[4]));
    ot_dp_st #(.W(8)) u_bout_xo_u_sfucore_Q_lane1_lane_rd_src (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane1_lane_rd_src[7:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane1_lane_rd_src[7:0]), .eq(xo_u_sfucore_Q_lane1_lane_rd_src[8]));
    ot_dp_st #(.W(1)) u_bout_xo_u_sfucore_Q_lane1_lane_ro_v (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane1_lane_ro_v[0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane1_lane_ro_v[0:0]), .eq(xo_u_sfucore_Q_lane1_lane_ro_v[1]));
    ot_dp_st #(.W(32)) u_bout_xo_u_sfucore_Q_lane1_lane_ro_x (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane1_lane_ro_x[31:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane1_lane_ro_x[31:0]), .eq(xo_u_sfucore_Q_lane1_lane_ro_x[32]));
    ot_dp_st #(.W(24)) u_bout_xo_u_sfucore_Q_lane1_lane_vm_waddr (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane1_lane_vm_waddr[23:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane1_lane_vm_waddr[23:0]), .eq(xo_u_sfucore_Q_lane1_lane_vm_waddr[24]));
    ot_dp_st #(.W(32)) u_bout_xo_u_sfucore_Q_lane1_lane_vm_wdata (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane1_lane_vm_wdata[31:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane1_lane_vm_wdata[31:0]), .eq(xo_u_sfucore_Q_lane1_lane_vm_wdata[32]));
    ot_dp_st #(.W(1)) u_bout_xo_u_sfucore_Q_lane1_lane_vm_we (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane1_lane_vm_we[0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane1_lane_vm_we[0:0]), .eq(xo_u_sfucore_Q_lane1_lane_vm_we[1]));
    ot_dp_st #(.W(1)) u_bout_xo_u_sfucore_Q_lane2_lane_coll (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane2_lane_coll[0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane2_lane_coll[0:0]), .eq(xo_u_sfucore_Q_lane2_lane_coll[1]));
    ot_dp_st #(.W(1)) u_bout_xo_u_sfucore_Q_lane2_lane_fault (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane2_lane_fault[0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane2_lane_fault[0:0]), .eq(xo_u_sfucore_Q_lane2_lane_fault[1]));
    ot_dp_st #(.W(96)) u_bout_xo_u_sfucore_Q_lane2_lane_rd_addr (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane2_lane_rd_addr[95:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane2_lane_rd_addr[95:0]), .eq(xo_u_sfucore_Q_lane2_lane_rd_addr[96]));
    ot_dp_st #(.W(4)) u_bout_xo_u_sfucore_Q_lane2_lane_rd_re (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane2_lane_rd_re[3:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane2_lane_rd_re[3:0]), .eq(xo_u_sfucore_Q_lane2_lane_rd_re[4]));
    ot_dp_st #(.W(8)) u_bout_xo_u_sfucore_Q_lane2_lane_rd_src (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane2_lane_rd_src[7:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane2_lane_rd_src[7:0]), .eq(xo_u_sfucore_Q_lane2_lane_rd_src[8]));
    ot_dp_st #(.W(1)) u_bout_xo_u_sfucore_Q_lane2_lane_ro_v (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane2_lane_ro_v[0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane2_lane_ro_v[0:0]), .eq(xo_u_sfucore_Q_lane2_lane_ro_v[1]));
    ot_dp_st #(.W(32)) u_bout_xo_u_sfucore_Q_lane2_lane_ro_x (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane2_lane_ro_x[31:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane2_lane_ro_x[31:0]), .eq(xo_u_sfucore_Q_lane2_lane_ro_x[32]));
    ot_dp_st #(.W(24)) u_bout_xo_u_sfucore_Q_lane2_lane_vm_waddr (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane2_lane_vm_waddr[23:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane2_lane_vm_waddr[23:0]), .eq(xo_u_sfucore_Q_lane2_lane_vm_waddr[24]));
    ot_dp_st #(.W(32)) u_bout_xo_u_sfucore_Q_lane2_lane_vm_wdata (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane2_lane_vm_wdata[31:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane2_lane_vm_wdata[31:0]), .eq(xo_u_sfucore_Q_lane2_lane_vm_wdata[32]));
    ot_dp_st #(.W(1)) u_bout_xo_u_sfucore_Q_lane2_lane_vm_we (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane2_lane_vm_we[0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane2_lane_vm_we[0:0]), .eq(xo_u_sfucore_Q_lane2_lane_vm_we[1]));
    ot_dp_st #(.W(1)) u_bout_xo_u_sfucore_Q_lane3_lane_coll (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane3_lane_coll[0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane3_lane_coll[0:0]), .eq(xo_u_sfucore_Q_lane3_lane_coll[1]));
    ot_dp_st #(.W(1)) u_bout_xo_u_sfucore_Q_lane3_lane_fault (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane3_lane_fault[0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane3_lane_fault[0:0]), .eq(xo_u_sfucore_Q_lane3_lane_fault[1]));
    ot_dp_st #(.W(96)) u_bout_xo_u_sfucore_Q_lane3_lane_rd_addr (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane3_lane_rd_addr[95:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane3_lane_rd_addr[95:0]), .eq(xo_u_sfucore_Q_lane3_lane_rd_addr[96]));
    ot_dp_st #(.W(4)) u_bout_xo_u_sfucore_Q_lane3_lane_rd_re (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane3_lane_rd_re[3:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane3_lane_rd_re[3:0]), .eq(xo_u_sfucore_Q_lane3_lane_rd_re[4]));
    ot_dp_st #(.W(8)) u_bout_xo_u_sfucore_Q_lane3_lane_rd_src (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane3_lane_rd_src[7:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane3_lane_rd_src[7:0]), .eq(xo_u_sfucore_Q_lane3_lane_rd_src[8]));
    ot_dp_st #(.W(1)) u_bout_xo_u_sfucore_Q_lane3_lane_ro_v (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane3_lane_ro_v[0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane3_lane_ro_v[0:0]), .eq(xo_u_sfucore_Q_lane3_lane_ro_v[1]));
    ot_dp_st #(.W(32)) u_bout_xo_u_sfucore_Q_lane3_lane_ro_x (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane3_lane_ro_x[31:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane3_lane_ro_x[31:0]), .eq(xo_u_sfucore_Q_lane3_lane_ro_x[32]));
    ot_dp_st #(.W(24)) u_bout_xo_u_sfucore_Q_lane3_lane_vm_waddr (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane3_lane_vm_waddr[23:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane3_lane_vm_waddr[23:0]), .eq(xo_u_sfucore_Q_lane3_lane_vm_waddr[24]));
    ot_dp_st #(.W(32)) u_bout_xo_u_sfucore_Q_lane3_lane_vm_wdata (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane3_lane_vm_wdata[31:0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane3_lane_vm_wdata[31:0]), .eq(xo_u_sfucore_Q_lane3_lane_vm_wdata[32]));
    ot_dp_st #(.W(1)) u_bout_xo_u_sfucore_Q_lane3_lane_vm_we (.clk(clk), .rst_n(rst_n), .d(w_u_sfucore_Q_lane3_lane_vm_we[0]), .ea(rst_n), .q(xo_u_sfucore_Q_lane3_lane_vm_we[0:0]), .eq(xo_u_sfucore_Q_lane3_lane_vm_we[1]));
    ot_dp_st #(.W(11)) u_ft_L117x6_o_0 (.clk(clk), .rst_n(rst_n), .d(L117x6_i[10:0]), .ea(L117x6_i[11]), .q(L117x6_o_s0[10:0]), .eq(L117x6_o_s0[11]));
    ot_dp_st #(.W(11)) u_ft_L117x6_o_1 (.clk(clk), .rst_n(rst_n), .d(L117x6_o_s0[10:0]), .ea(L117x6_o_s0[11]), .q(L117x6_o[10:0]), .eq(L117x6_o[11]));
    ot_dp_st #(.W(2)) u_ft_L138x6_o_0 (.clk(clk), .rst_n(rst_n), .d(L138x6_i[1:0]), .ea(L138x6_i[2]), .q(L138x6_o_s0[1:0]), .eq(L138x6_o_s0[2]));
    ot_dp_st #(.W(2)) u_ft_L138x6_o_1 (.clk(clk), .rst_n(rst_n), .d(L138x6_o_s0[1:0]), .ea(L138x6_o_s0[2]), .q(L138x6_o[1:0]), .eq(L138x6_o[2]));
    ot_dp_st #(.W(634)) u_ft_L48x9_o_0 (.clk(clk), .rst_n(rst_n), .d(L48x9_i[633:0]), .ea(L48x9_i[634]), .q(L48x9_o_s0[633:0]), .eq(L48x9_o_s0[634]));
    ot_dp_st #(.W(634)) u_ft_L48x9_o_1 (.clk(clk), .rst_n(rst_n), .d(L48x9_o_s0[633:0]), .ea(L48x9_o_s0[634]), .q(L48x9_o_s1[633:0]), .eq(L48x9_o_s1[634]));
    ot_dp_st #(.W(634)) u_ft_L48x9_o_2 (.clk(clk), .rst_n(rst_n), .d(L48x9_o_s1[633:0]), .ea(L48x9_o_s1[634]), .q(L48x9_o_s2[633:0]), .eq(L48x9_o_s2[634]));
    ot_dp_st #(.W(634)) u_ft_L48x9_o_3 (.clk(clk), .rst_n(rst_n), .d(L48x9_o_s2[633:0]), .ea(L48x9_o_s2[634]), .q(L48x9_o[633:0]), .eq(L48x9_o[634]));
    ot_dp_st #(.W(612)) u_ft_L53x3_o_0 (.clk(clk), .rst_n(rst_n), .d(L53x3_i[611:0]), .ea(L53x3_i[612]), .q(L53x3_o_s0[611:0]), .eq(L53x3_o_s0[612]));
    ot_dp_st #(.W(612)) u_ft_L53x3_o_1 (.clk(clk), .rst_n(rst_n), .d(L53x3_o_s0[611:0]), .ea(L53x3_o_s0[612]), .q(L53x3_o_s1[611:0]), .eq(L53x3_o_s1[612]));
    ot_dp_st #(.W(612)) u_ft_L53x3_o_2 (.clk(clk), .rst_n(rst_n), .d(L53x3_o_s1[611:0]), .ea(L53x3_o_s1[612]), .q(L53x3_o[611:0]), .eq(L53x3_o[612]));
    ot_dp_st #(.W(828)) u_ft_L6br0_2_o_0 (.clk(clk), .rst_n(rst_n), .d(L6br0_2_i[827:0]), .ea(L6br0_2_i[828]), .q(L6br0_2_o_s0[827:0]), .eq(L6br0_2_o_s0[828]));
    ot_dp_st #(.W(828)) u_ft_L6br0_2_o_1 (.clk(clk), .rst_n(rst_n), .d(L6br0_2_o_s0[827:0]), .ea(L6br0_2_o_s0[828]), .q(L6br0_2_o[827:0]), .eq(L6br0_2_o[828]));
     
    ot_hnx_sfu_lane__cf694489f05c u_u_sfucore_Q_lane0 (
        .lane_coll(w_u_sfucore_Q_lane0_lane_coll),
        .lane_fault(w_u_sfucore_Q_lane0_lane_fault),
        .lane_kv_waddr(w_u_sfucore_Q_lane0_lane_kv_waddr),
        .lane_kv_wdata(w_u_sfucore_Q_lane0_lane_kv_wdata),
        .lane_kv_we(w_u_sfucore_Q_lane0_lane_kv_we),
        .lane_rd_addr(w_u_sfucore_Q_lane0_lane_rd_addr),
        .lane_rd_q({xi_u_sfucore_Q_lane0_lane_rd_q__1_q[63:0], xi_u_sfucore_Q_lane0_lane_rd_q__0_q[63:0]}),
        .lane_rd_re(w_u_sfucore_Q_lane0_lane_rd_re),
        .lane_rd_src(w_u_sfucore_Q_lane0_lane_rd_src),
        .lane_ro_v(w_u_sfucore_Q_lane0_lane_ro_v),
        .lane_ro_x(w_u_sfucore_Q_lane0_lane_ro_x),
        .lane_vi_addr(w_u_sfucore_Q_lane0_lane_vi_addr),
        .lane_vi_q(L5_i_q[31:0]),
        .lane_vi_re(w_u_sfucore_Q_lane0_lane_vi_re),
        .lane_vm_waddr(w_u_sfucore_Q_lane0_lane_vm_waddr),
        .lane_vm_wdata(w_u_sfucore_Q_lane0_lane_vm_wdata),
        .lane_vm_we(w_u_sfucore_Q_lane0_lane_vm_we),
        .map_clk(clk),
        .map_i_emit(xi_u_sfucore_Q_lane0_map_i_emit_q[539]),
        .map_i_i_v(xi_u_sfucore_Q_lane0_map_i_emit_q[513:490]),
        .map_i_krow(xi_u_sfucore_Q_lane0_map_i_emit_q[313:290]),
        .map_i_ls(xi_u_sfucore_Q_lane0_map_i_emit_q[441:438]),
        .map_i_lvw(xi_u_sfucore_Q_lane0_map_i_emit_q[437:434]),
        .map_i_o_v(xi_u_sfucore_Q_lane0_map_i_emit_q[537:514]),
        .map_i_pass({xi_u_sfucore_Q_lane0_map_i_emit_q[1021:1020], xi_u_sfucore_Q_lane0_map_i_emit_q[538], xi_u_sfucore_Q_lane0_map_i_emit_q[489:442], xi_u_sfucore_Q_lane0_map_i_emit_q[433:314], xi_u_sfucore_Q_lane0_map_i_emit_q[289:0]}),
        .map_lane_j(strap_u_sfucore_Q_lane0_map_lane_j[3:0]),
        .map_ld_terms(xi_u_sfucore_Q_lane0_map_i_emit_q[1019:540]),
        .map_rst_n(rst_n)
    );
     
    ot_hnx_sfu_lane__cf694489f05c u_u_sfucore_Q_lane1 (
        .lane_coll(w_u_sfucore_Q_lane1_lane_coll),
        .lane_fault(w_u_sfucore_Q_lane1_lane_fault),
        .lane_kv_waddr(w_u_sfucore_Q_lane1_lane_kv_waddr),
        .lane_kv_wdata(w_u_sfucore_Q_lane1_lane_kv_wdata),
        .lane_kv_we(w_u_sfucore_Q_lane1_lane_kv_we),
        .lane_rd_addr(w_u_sfucore_Q_lane1_lane_rd_addr),
        .lane_rd_q({xi_u_sfucore_Q_lane0_lane_rd_q__1_q[127:64], xi_u_sfucore_Q_lane0_lane_rd_q__0_q[127:64]}),
        .lane_rd_re(w_u_sfucore_Q_lane1_lane_rd_re),
        .lane_rd_src(w_u_sfucore_Q_lane1_lane_rd_src),
        .lane_ro_v(w_u_sfucore_Q_lane1_lane_ro_v),
        .lane_ro_x(w_u_sfucore_Q_lane1_lane_ro_x),
        .lane_vi_addr(w_u_sfucore_Q_lane1_lane_vi_addr),
        .lane_vi_q(L5_i_q[63:32]),
        .lane_vi_re(w_u_sfucore_Q_lane1_lane_vi_re),
        .lane_vm_waddr(w_u_sfucore_Q_lane1_lane_vm_waddr),
        .lane_vm_wdata(w_u_sfucore_Q_lane1_lane_vm_wdata),
        .lane_vm_we(w_u_sfucore_Q_lane1_lane_vm_we),
        .map_clk(clk),
        .map_i_emit(xi_u_sfucore_Q_lane0_map_i_emit_q[539]),
        .map_i_i_v(xi_u_sfucore_Q_lane0_map_i_emit_q[513:490]),
        .map_i_krow(xi_u_sfucore_Q_lane0_map_i_emit_q[313:290]),
        .map_i_ls(xi_u_sfucore_Q_lane0_map_i_emit_q[441:438]),
        .map_i_lvw(xi_u_sfucore_Q_lane0_map_i_emit_q[437:434]),
        .map_i_o_v(xi_u_sfucore_Q_lane0_map_i_emit_q[537:514]),
        .map_i_pass({xi_u_sfucore_Q_lane0_map_i_emit_q[1021:1020], xi_u_sfucore_Q_lane0_map_i_emit_q[538], xi_u_sfucore_Q_lane0_map_i_emit_q[489:442], xi_u_sfucore_Q_lane0_map_i_emit_q[433:314], xi_u_sfucore_Q_lane0_map_i_emit_q[289:0]}),
        .map_lane_j(strap_u_sfucore_Q_lane1_map_lane_j[3:0]),
        .map_ld_terms(xi_u_sfucore_Q_lane0_map_i_emit_q[1019:540]),
        .map_rst_n(rst_n)
    );
     
    ot_hnx_sfu_lane__cf694489f05c u_u_sfucore_Q_lane2 (
        .lane_coll(w_u_sfucore_Q_lane2_lane_coll),
        .lane_fault(w_u_sfucore_Q_lane2_lane_fault),
        .lane_kv_waddr(w_u_sfucore_Q_lane2_lane_kv_waddr),
        .lane_kv_wdata(w_u_sfucore_Q_lane2_lane_kv_wdata),
        .lane_kv_we(w_u_sfucore_Q_lane2_lane_kv_we),
        .lane_rd_addr(w_u_sfucore_Q_lane2_lane_rd_addr),
        .lane_rd_q({xi_u_sfucore_Q_lane0_lane_rd_q__1_q[191:128], xi_u_sfucore_Q_lane0_lane_rd_q__0_q[191:128]}),
        .lane_rd_re(w_u_sfucore_Q_lane2_lane_rd_re),
        .lane_rd_src(w_u_sfucore_Q_lane2_lane_rd_src),
        .lane_ro_v(w_u_sfucore_Q_lane2_lane_ro_v),
        .lane_ro_x(w_u_sfucore_Q_lane2_lane_ro_x),
        .lane_vi_addr(w_u_sfucore_Q_lane2_lane_vi_addr),
        .lane_vi_q(L5_i_q[95:64]),
        .lane_vi_re(w_u_sfucore_Q_lane2_lane_vi_re),
        .lane_vm_waddr(w_u_sfucore_Q_lane2_lane_vm_waddr),
        .lane_vm_wdata(w_u_sfucore_Q_lane2_lane_vm_wdata),
        .lane_vm_we(w_u_sfucore_Q_lane2_lane_vm_we),
        .map_clk(clk),
        .map_i_emit(xi_u_sfucore_Q_lane0_map_i_emit_q[539]),
        .map_i_i_v(xi_u_sfucore_Q_lane0_map_i_emit_q[513:490]),
        .map_i_krow(xi_u_sfucore_Q_lane0_map_i_emit_q[313:290]),
        .map_i_ls(xi_u_sfucore_Q_lane0_map_i_emit_q[441:438]),
        .map_i_lvw(xi_u_sfucore_Q_lane0_map_i_emit_q[437:434]),
        .map_i_o_v(xi_u_sfucore_Q_lane0_map_i_emit_q[537:514]),
        .map_i_pass({xi_u_sfucore_Q_lane0_map_i_emit_q[1021:1020], xi_u_sfucore_Q_lane0_map_i_emit_q[538], xi_u_sfucore_Q_lane0_map_i_emit_q[489:442], xi_u_sfucore_Q_lane0_map_i_emit_q[433:314], xi_u_sfucore_Q_lane0_map_i_emit_q[289:0]}),
        .map_lane_j(strap_u_sfucore_Q_lane2_map_lane_j[3:0]),
        .map_ld_terms(xi_u_sfucore_Q_lane0_map_i_emit_q[1019:540]),
        .map_rst_n(rst_n)
    );
     
    ot_hnx_sfu_lane__cf694489f05c u_u_sfucore_Q_lane3 (
        .lane_coll(w_u_sfucore_Q_lane3_lane_coll),
        .lane_fault(w_u_sfucore_Q_lane3_lane_fault),
        .lane_kv_waddr(w_u_sfucore_Q_lane3_lane_kv_waddr),
        .lane_kv_wdata(w_u_sfucore_Q_lane3_lane_kv_wdata),
        .lane_kv_we(w_u_sfucore_Q_lane3_lane_kv_we),
        .lane_rd_addr(w_u_sfucore_Q_lane3_lane_rd_addr),
        .lane_rd_q({xi_u_sfucore_Q_lane0_lane_rd_q__1_q[255:192], xi_u_sfucore_Q_lane0_lane_rd_q__0_q[255:192]}),
        .lane_rd_re(w_u_sfucore_Q_lane3_lane_rd_re),
        .lane_rd_src(w_u_sfucore_Q_lane3_lane_rd_src),
        .lane_ro_v(w_u_sfucore_Q_lane3_lane_ro_v),
        .lane_ro_x(w_u_sfucore_Q_lane3_lane_ro_x),
        .lane_vi_addr(w_u_sfucore_Q_lane3_lane_vi_addr),
        .lane_vi_q(L5_i_q[127:96]),
        .lane_vi_re(w_u_sfucore_Q_lane3_lane_vi_re),
        .lane_vm_waddr(w_u_sfucore_Q_lane3_lane_vm_waddr),
        .lane_vm_wdata(w_u_sfucore_Q_lane3_lane_vm_wdata),
        .lane_vm_we(w_u_sfucore_Q_lane3_lane_vm_we),
        .map_clk(clk),
        .map_i_emit(xi_u_sfucore_Q_lane0_map_i_emit_q[539]),
        .map_i_i_v(xi_u_sfucore_Q_lane0_map_i_emit_q[513:490]),
        .map_i_krow(xi_u_sfucore_Q_lane0_map_i_emit_q[313:290]),
        .map_i_ls(xi_u_sfucore_Q_lane0_map_i_emit_q[441:438]),
        .map_i_lvw(xi_u_sfucore_Q_lane0_map_i_emit_q[437:434]),
        .map_i_o_v(xi_u_sfucore_Q_lane0_map_i_emit_q[537:514]),
        .map_i_pass({xi_u_sfucore_Q_lane0_map_i_emit_q[1021:1020], xi_u_sfucore_Q_lane0_map_i_emit_q[538], xi_u_sfucore_Q_lane0_map_i_emit_q[489:442], xi_u_sfucore_Q_lane0_map_i_emit_q[433:314], xi_u_sfucore_Q_lane0_map_i_emit_q[289:0]}),
        .map_lane_j(strap_u_sfucore_Q_lane3_map_lane_j[3:0]),
        .map_ld_terms(xi_u_sfucore_Q_lane0_map_i_emit_q[1019:540]),
        .map_rst_n(rst_n)
    );
endmodule
