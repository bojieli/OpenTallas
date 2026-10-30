`timescale 1ps/1fs
module tb;
integer edge_x_su_l0_ctl_o=0;
integer edge_x_fw_ctl_p2_o=0;
integer edge_cws3_o=0;
integer edge_x_su_l0_sc_i=0;
integer edge_x_su_l0_ctl_i=0;
integer edge_x_st_b_i=0;
integer edge_x_st_a_i=0;
integer edge_cws3_i=0;
reg clk=0,fclk=0; real phase;integer phase_i,cycle=0,fcycle=0;reg arst_n=0,start_i=0,cland_rstart_in=0;reg [31:0] word=0;
always #416.5 clk=~clk; initial begin if(!$value$plusargs("PHASE=%d",phase_i))phase_i=166; phase=phase_i; #(phase);forever #416.5 fclk=~fclk;end
always @(posedge fclk) begin fcycle=fcycle+1;word<=word+1;end
always @(posedge clk) cycle=cycle+1;
reg fs_cws3_i=0;
always @(negedge fclk) begin if(fcycle==86 || fcycle==686)fs_cws3_i<=1;if(fcycle==400)fs_cws3_i<=0;end
reg fs_x_st_a_i=0;
always @(negedge fclk) begin if(fcycle==90 || fcycle==690)fs_x_st_a_i<=1;if(fcycle==400)fs_x_st_a_i<=0;end
reg fs_x_st_b_i=0;
always @(negedge fclk) begin if(fcycle==86 || fcycle==686)fs_x_st_b_i<=1;if(fcycle==400)fs_x_st_b_i<=0;end
reg fs_x_su_l0_ctl_i=0;
always @(negedge fclk) begin if(fcycle==90 || fcycle==690)fs_x_su_l0_ctl_i<=1;if(fcycle==400)fs_x_su_l0_ctl_i<=0;end
reg fs_x_su_l0_sc_i=0;
always @(negedge fclk) begin if(fcycle==90 || fcycle==690)fs_x_su_l0_sc_i<=1;if(fcycle==400)fs_x_su_l0_sc_i<=0;end
wire [514:0] baseline_l9_eo;
wire [516:0] baseline_cws3_o;
wire [536:0] baseline_x_fw_ctl_p2_o;
wire [456:0] baseline_x_su_l0_ctl_o;
wire [38:0] baseline_x_su_l0_sc_o;
wire  baseline_fclk_out_cws3_o;
wire  baseline_cland_fstart_out_cws3_o;
wire  baseline_fclk_out_x_fw_ctl_p2_o;
wire  baseline_cland_fstart_out_x_fw_ctl_p2_o;
wire  baseline_fclk_out_x_su_l0_ctl_o;
wire  baseline_cland_fstart_out_x_su_l0_ctl_o;
wire  baseline_cland_up_ready;
wire  baseline_cland_up_fault;
wire  baseline_fclk_out_cland_up;
baseline_controls baseline(.clk(clk),.clk_t1(clk),.clk_t2(clk),.clk_t3(clk),.clk_t4(clk),.clk_t5(clk),.clk_t6(clk),.clk_t7(clk),.arst_n(arst_n),.start_i(start_i),.x_fw_i({508'd0,word}),.x_fw_p1_i({508'd0,word}),.x_fw_p2_i({507'd0,word}),.x_stm_i({513'd0,word}),.x_stm_p1_i({513'd0,word}),.x_sc_i({17'd0,word}),.x_st_a_i({227'd0,word}),.x_st_b_i({225'd0,word}),.l9_eo(baseline_l9_eo),.cws3_i({485'd0,word}),.cws3_o(baseline_cws3_o),.x_fw_ctl_p2_i({505'd0,word}),.x_fw_ctl_p2_o(baseline_x_fw_ctl_p2_o),.x_su_l0_ctl_i({425'd0,word}),.x_su_l0_ctl_o(baseline_x_su_l0_ctl_o),.x_su_l0_sc_i({7'd0,word}),.x_su_l0_sc_o(baseline_x_su_l0_sc_o),.fclk_out_cws3_o(baseline_fclk_out_cws3_o),.cland_fstart_out_cws3_o(baseline_cland_fstart_out_cws3_o),.fclk_out_x_fw_ctl_p2_o(baseline_fclk_out_x_fw_ctl_p2_o),.cland_fstart_out_x_fw_ctl_p2_o(baseline_cland_fstart_out_x_fw_ctl_p2_o),.fclk_out_x_su_l0_ctl_o(baseline_fclk_out_x_su_l0_ctl_o),.cland_fstart_out_x_su_l0_ctl_o(baseline_cland_fstart_out_x_su_l0_ctl_o),.fclk_in_cws3_i(fclk),.cland_fstart_in_cws3_i(fs_cws3_i),.strap_ca_k_cws3_i(6'd23),.fclk_in_x_st_a_i(fclk),.cland_fstart_in_x_st_a_i(fs_x_st_a_i),.strap_ca_k_x_st_a_i(6'd27),.fclk_in_x_st_b_i(fclk),.cland_fstart_in_x_st_b_i(fs_x_st_b_i),.strap_ca_k_x_st_b_i(6'd23),.fclk_in_x_su_l0_ctl_i(fclk),.cland_fstart_in_x_su_l0_ctl_i(fs_x_su_l0_ctl_i),.strap_ca_k_x_su_l0_ctl_i(6'd27),.fclk_in_x_su_l0_sc_i(fclk),.cland_fstart_in_x_su_l0_sc_i(fs_x_su_l0_sc_i),.strap_ca_k_x_su_l0_sc_i(6'd27),.cland_rstart_in(cland_rstart_in),.cland_up_ready(baseline_cland_up_ready),.cland_up_fault(baseline_cland_up_fault),.fclk_out_cland_up(baseline_fclk_out_cland_up));
wire [514:0] candidate_l9_eo;
wire [516:0] candidate_cws3_o;
wire [536:0] candidate_x_fw_ctl_p2_o;
wire [456:0] candidate_x_su_l0_ctl_o;
wire [38:0] candidate_x_su_l0_sc_o;
wire  candidate_fclk_out_cws3_o;
wire  candidate_cland_fstart_out_cws3_o;
wire  candidate_fclk_out_x_fw_ctl_p2_o;
wire  candidate_cland_fstart_out_x_fw_ctl_p2_o;
wire  candidate_fclk_out_x_su_l0_ctl_o;
wire  candidate_cland_fstart_out_x_su_l0_ctl_o;
wire  candidate_cland_up_ready;
wire  candidate_cland_up_fault;
wire  candidate_fclk_out_cland_up;
candidate_controls candidate(.clk(clk),.clk_t1(clk),.clk_t2(clk),.clk_t3(clk),.clk_t4(clk),.clk_t5(clk),.clk_t6(clk),.clk_t7(clk),.arst_n(arst_n),.start_i(start_i),.x_fw_i({508'd0,word}),.x_fw_p1_i({508'd0,word}),.x_fw_p2_i({507'd0,word}),.x_stm_i({513'd0,word}),.x_stm_p1_i({513'd0,word}),.x_sc_i({17'd0,word}),.x_st_a_i({227'd0,word}),.x_st_b_i({225'd0,word}),.l9_eo(candidate_l9_eo),.cws3_i({485'd0,word}),.cws3_o(candidate_cws3_o),.x_fw_ctl_p2_i({505'd0,word}),.x_fw_ctl_p2_o(candidate_x_fw_ctl_p2_o),.x_su_l0_ctl_i({425'd0,word}),.x_su_l0_ctl_o(candidate_x_su_l0_ctl_o),.x_su_l0_sc_i({7'd0,word}),.x_su_l0_sc_o(candidate_x_su_l0_sc_o),.fclk_out_cws3_o(candidate_fclk_out_cws3_o),.cland_fstart_out_cws3_o(candidate_cland_fstart_out_cws3_o),.fclk_out_x_fw_ctl_p2_o(candidate_fclk_out_x_fw_ctl_p2_o),.cland_fstart_out_x_fw_ctl_p2_o(candidate_cland_fstart_out_x_fw_ctl_p2_o),.fclk_out_x_su_l0_ctl_o(candidate_fclk_out_x_su_l0_ctl_o),.cland_fstart_out_x_su_l0_ctl_o(candidate_cland_fstart_out_x_su_l0_ctl_o),.fclk_in_cws3_i(fclk),.cland_fstart_in_cws3_i(fs_cws3_i),.strap_ca_k_cws3_i(6'd22),.fclk_in_x_st_a_i(fclk),.cland_fstart_in_x_st_a_i(fs_x_st_a_i),.strap_ca_k_x_st_a_i(6'd26),.fclk_in_x_st_b_i(fclk),.cland_fstart_in_x_st_b_i(fs_x_st_b_i),.strap_ca_k_x_st_b_i(6'd22),.fclk_in_x_su_l0_ctl_i(fclk),.cland_fstart_in_x_su_l0_ctl_i(fs_x_su_l0_ctl_i),.strap_ca_k_x_su_l0_ctl_i(6'd26),.fclk_in_x_su_l0_sc_i(fclk),.cland_fstart_in_x_su_l0_sc_i(fs_x_su_l0_sc_i),.strap_ca_k_x_su_l0_sc_i(6'd26),.cland_rstart_in(cland_rstart_in),.cland_up_ready(candidate_cland_up_ready),.cland_up_fault(candidate_cland_up_fault),.fclk_out_cland_up(candidate_fclk_out_cland_up));
reg ds_cws3_o=0;
always @(negedge clk) begin if(cycle==91 || cycle==691)ds_cws3_o<=1;if(cycle==400)ds_cws3_o<=0;end
wire [516:0] baseline_down_cws3_o;wire baseline_dr_cws3_o,baseline_df_cws3_o;
ot_dp_clk_landing_cas #(.W(517),.DEPTH(4)) baseline_downring_cws3_o(.fclk(clk),.t_rst_n(baseline_cland_fstart_out_cws3_o),.clk(clk),.rst_n(ds_cws3_o),.strap_k(6'd40),.d(baseline_cws3_o),.q(baseline_down_cws3_o),.ready(baseline_dr_cws3_o),.fault(baseline_df_cws3_o));
wire [516:0] candidate_down_cws3_o;wire candidate_dr_cws3_o,candidate_df_cws3_o;
ot_dp_clk_landing_cas #(.W(517),.DEPTH(4)) candidate_downring_cws3_o(.fclk(clk),.t_rst_n(candidate_cland_fstart_out_cws3_o),.clk(clk),.rst_n(ds_cws3_o),.strap_k(6'd43),.d(candidate_cws3_o),.q(candidate_down_cws3_o),.ready(candidate_dr_cws3_o),.fault(candidate_df_cws3_o));
reg ds_x_fw_ctl_p2_o=0;
always @(negedge clk) begin if(cycle==88 || cycle==688)ds_x_fw_ctl_p2_o<=1;if(cycle==400)ds_x_fw_ctl_p2_o<=0;end
wire [536:0] baseline_down_x_fw_ctl_p2_o;wire baseline_dr_x_fw_ctl_p2_o,baseline_df_x_fw_ctl_p2_o;
ot_dp_clk_landing_cas #(.W(537),.DEPTH(4)) baseline_downring_x_fw_ctl_p2_o(.fclk(clk),.t_rst_n(baseline_cland_fstart_out_x_fw_ctl_p2_o),.clk(clk),.rst_n(ds_x_fw_ctl_p2_o),.strap_k(6'd43),.d(baseline_x_fw_ctl_p2_o),.q(baseline_down_x_fw_ctl_p2_o),.ready(baseline_dr_x_fw_ctl_p2_o),.fault(baseline_df_x_fw_ctl_p2_o));
wire [536:0] candidate_down_x_fw_ctl_p2_o;wire candidate_dr_x_fw_ctl_p2_o,candidate_df_x_fw_ctl_p2_o;
ot_dp_clk_landing_cas #(.W(537),.DEPTH(4)) candidate_downring_x_fw_ctl_p2_o(.fclk(clk),.t_rst_n(candidate_cland_fstart_out_x_fw_ctl_p2_o),.clk(clk),.rst_n(ds_x_fw_ctl_p2_o),.strap_k(6'd46),.d(candidate_x_fw_ctl_p2_o),.q(candidate_down_x_fw_ctl_p2_o),.ready(candidate_dr_x_fw_ctl_p2_o),.fault(candidate_df_x_fw_ctl_p2_o));
reg ds_x_su_l0_ctl_o=0;
always @(negedge clk) begin if(cycle==88 || cycle==688)ds_x_su_l0_ctl_o<=1;if(cycle==400)ds_x_su_l0_ctl_o<=0;end
wire [456:0] baseline_down_x_su_l0_ctl_o;wire baseline_dr_x_su_l0_ctl_o,baseline_df_x_su_l0_ctl_o;
ot_dp_clk_landing_cas #(.W(457),.DEPTH(4)) baseline_downring_x_su_l0_ctl_o(.fclk(clk),.t_rst_n(baseline_cland_fstart_out_x_su_l0_ctl_o),.clk(clk),.rst_n(ds_x_su_l0_ctl_o),.strap_k(6'd43),.d(baseline_x_su_l0_ctl_o),.q(baseline_down_x_su_l0_ctl_o),.ready(baseline_dr_x_su_l0_ctl_o),.fault(baseline_df_x_su_l0_ctl_o));
wire [456:0] candidate_down_x_su_l0_ctl_o;wire candidate_dr_x_su_l0_ctl_o,candidate_df_x_su_l0_ctl_o;
ot_dp_clk_landing_cas #(.W(457),.DEPTH(4)) candidate_downring_x_su_l0_ctl_o(.fclk(clk),.t_rst_n(candidate_cland_fstart_out_x_su_l0_ctl_o),.clk(clk),.rst_n(ds_x_su_l0_ctl_o),.strap_k(6'd46),.d(candidate_x_su_l0_ctl_o),.q(candidate_down_x_su_l0_ctl_o),.ready(candidate_dr_x_su_l0_ctl_o),.fault(candidate_df_x_su_l0_ctl_o));
integer checks=0;integer first_base=-1,first_candidate=-1;
always @(negedge clk) begin
if(cycle==8)begin arst_n<=1;start_i<=1;end
if(cycle==64 || cycle==664)cland_rstart_in<=1;
if(cycle==400)begin arst_n<=0;start_i<=0;cland_rstart_in<=0;end
if(cycle==608)begin arst_n<=1;start_i<=1;end
if(cycle>12)begin
if(candidate.cland_raw_origin_0 !== candidate.rst_rl_0)$fatal(1,"RAW_EQUATION cland_raw_origin_0 cycle%0d",cycle);
if(candidate.cland_raw_origin_1 !== candidate.rst_rl_5)$fatal(1,"RAW_EQUATION cland_raw_origin_1 cycle%0d",cycle);
if(candidate.cland_raw_origin_2 !== candidate.rst_rl_6)$fatal(1,"RAW_EQUATION cland_raw_origin_2 cycle%0d",cycle);
if(candidate.cland_raw_origin_3 !== candidate.rst_rl_7)$fatal(1,"RAW_EQUATION cland_raw_origin_3 cycle%0d",cycle);
if(candidate.cland_raw_origin_4 !== candidate.cland_reset_cws3_i)$fatal(1,"RAW_EQUATION cland_raw_origin_4 cycle%0d",cycle);
if(candidate.cland_raw_reader_cws3_i_0 !== candidate.rst_rl_0)$fatal(1,"RAW_EQUATION cland_raw_reader_cws3_i_0 cycle%0d",cycle);
if(candidate.cland_raw_reader_cws3_i_1 !== candidate.rst_rl_5)$fatal(1,"RAW_EQUATION cland_raw_reader_cws3_i_1 cycle%0d",cycle);
if(candidate.cland_raw_reader_cws3_i_2 !== candidate.rst_rl_6)$fatal(1,"RAW_EQUATION cland_raw_reader_cws3_i_2 cycle%0d",cycle);
if(candidate.cland_raw_reader_cws3_i_3 !== candidate.rst_rl_7)$fatal(1,"RAW_EQUATION cland_raw_reader_cws3_i_3 cycle%0d",cycle);
if(candidate.cland_raw_reader_cws3_i_4 !== candidate.cland_reset_cws3_i)$fatal(1,"RAW_EQUATION cland_raw_reader_cws3_i_4 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_st_a_i_0 !== candidate.rst_rl_0)$fatal(1,"RAW_EQUATION cland_raw_reader_x_st_a_i_0 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_st_a_i_1 !== candidate.rst_rl_5)$fatal(1,"RAW_EQUATION cland_raw_reader_x_st_a_i_1 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_st_a_i_2 !== candidate.rst_rl_6)$fatal(1,"RAW_EQUATION cland_raw_reader_x_st_a_i_2 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_st_a_i_3 !== candidate.rst_rl_7)$fatal(1,"RAW_EQUATION cland_raw_reader_x_st_a_i_3 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_st_a_i_4 !== candidate.cland_reset_cws3_i)$fatal(1,"RAW_EQUATION cland_raw_reader_x_st_a_i_4 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_st_b_i_0 !== candidate.rst_rl_0)$fatal(1,"RAW_EQUATION cland_raw_reader_x_st_b_i_0 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_st_b_i_1 !== candidate.rst_rl_5)$fatal(1,"RAW_EQUATION cland_raw_reader_x_st_b_i_1 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_st_b_i_2 !== candidate.rst_rl_6)$fatal(1,"RAW_EQUATION cland_raw_reader_x_st_b_i_2 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_st_b_i_3 !== candidate.rst_rl_7)$fatal(1,"RAW_EQUATION cland_raw_reader_x_st_b_i_3 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_st_b_i_4 !== candidate.cland_reset_cws3_i)$fatal(1,"RAW_EQUATION cland_raw_reader_x_st_b_i_4 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_su_l0_ctl_i_0 !== candidate.rst_rl_0)$fatal(1,"RAW_EQUATION cland_raw_reader_x_su_l0_ctl_i_0 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_su_l0_ctl_i_1 !== candidate.rst_rl_5)$fatal(1,"RAW_EQUATION cland_raw_reader_x_su_l0_ctl_i_1 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_su_l0_ctl_i_2 !== candidate.rst_rl_6)$fatal(1,"RAW_EQUATION cland_raw_reader_x_su_l0_ctl_i_2 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_su_l0_ctl_i_3 !== candidate.rst_rl_7)$fatal(1,"RAW_EQUATION cland_raw_reader_x_su_l0_ctl_i_3 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_su_l0_ctl_i_4 !== candidate.cland_reset_cws3_i)$fatal(1,"RAW_EQUATION cland_raw_reader_x_su_l0_ctl_i_4 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_su_l0_sc_i_0 !== candidate.rst_rl_0)$fatal(1,"RAW_EQUATION cland_raw_reader_x_su_l0_sc_i_0 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_su_l0_sc_i_1 !== candidate.rst_rl_5)$fatal(1,"RAW_EQUATION cland_raw_reader_x_su_l0_sc_i_1 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_su_l0_sc_i_2 !== candidate.rst_rl_6)$fatal(1,"RAW_EQUATION cland_raw_reader_x_su_l0_sc_i_2 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_su_l0_sc_i_3 !== candidate.rst_rl_7)$fatal(1,"RAW_EQUATION cland_raw_reader_x_su_l0_sc_i_3 cycle%0d",cycle);
if(candidate.cland_raw_reader_x_su_l0_sc_i_4 !== candidate.cland_reset_cws3_i)$fatal(1,"RAW_EQUATION cland_raw_reader_x_su_l0_sc_i_4 cycle%0d",cycle);
if(candidate.cland_raw_writer_cws3_o_0_0 !== candidate.rst_rl_0)$fatal(1,"RAW_EQUATION cland_raw_writer_cws3_o_0_0 cycle%0d",cycle);
if(candidate.cland_raw_writer_cws3_o_0_1 !== candidate.rst_rl_5)$fatal(1,"RAW_EQUATION cland_raw_writer_cws3_o_0_1 cycle%0d",cycle);
if(candidate.cland_raw_writer_cws3_o_0_2 !== candidate.rst_rl_6)$fatal(1,"RAW_EQUATION cland_raw_writer_cws3_o_0_2 cycle%0d",cycle);
if(candidate.cland_raw_writer_cws3_o_0_3 !== candidate.rst_rl_7)$fatal(1,"RAW_EQUATION cland_raw_writer_cws3_o_0_3 cycle%0d",cycle);
if(candidate.cland_raw_writer_cws3_o_0_4 !== candidate.cland_reset_cws3_i)$fatal(1,"RAW_EQUATION cland_raw_writer_cws3_o_0_4 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_fw_ctl_p2_o_0_0 !== candidate.rst_rl_0)$fatal(1,"RAW_EQUATION cland_raw_writer_x_fw_ctl_p2_o_0_0 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_fw_ctl_p2_o_0_1 !== candidate.rst_rl_5)$fatal(1,"RAW_EQUATION cland_raw_writer_x_fw_ctl_p2_o_0_1 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_fw_ctl_p2_o_0_2 !== candidate.rst_rl_6)$fatal(1,"RAW_EQUATION cland_raw_writer_x_fw_ctl_p2_o_0_2 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_fw_ctl_p2_o_0_3 !== candidate.rst_rl_7)$fatal(1,"RAW_EQUATION cland_raw_writer_x_fw_ctl_p2_o_0_3 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_fw_ctl_p2_o_0_4 !== candidate.cland_reset_cws3_i)$fatal(1,"RAW_EQUATION cland_raw_writer_x_fw_ctl_p2_o_0_4 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_su_l0_ctl_o_0_0 !== candidate.rst_rl_0)$fatal(1,"RAW_EQUATION cland_raw_writer_x_su_l0_ctl_o_0_0 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_su_l0_ctl_o_0_1 !== candidate.rst_rl_5)$fatal(1,"RAW_EQUATION cland_raw_writer_x_su_l0_ctl_o_0_1 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_su_l0_ctl_o_0_2 !== candidate.rst_rl_6)$fatal(1,"RAW_EQUATION cland_raw_writer_x_su_l0_ctl_o_0_2 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_su_l0_ctl_o_0_3 !== candidate.rst_rl_7)$fatal(1,"RAW_EQUATION cland_raw_writer_x_su_l0_ctl_o_0_3 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_su_l0_ctl_o_0_4 !== candidate.cland_reset_cws3_i)$fatal(1,"RAW_EQUATION cland_raw_writer_x_su_l0_ctl_o_0_4 cycle%0d",cycle);
if(candidate.cland_raw_writer_cws3_o_1_0 !== candidate.rst_rl_0)$fatal(1,"RAW_EQUATION cland_raw_writer_cws3_o_1_0 cycle%0d",cycle);
if(candidate.cland_raw_writer_cws3_o_1_1 !== candidate.rst_rl_5)$fatal(1,"RAW_EQUATION cland_raw_writer_cws3_o_1_1 cycle%0d",cycle);
if(candidate.cland_raw_writer_cws3_o_1_2 !== candidate.rst_rl_6)$fatal(1,"RAW_EQUATION cland_raw_writer_cws3_o_1_2 cycle%0d",cycle);
if(candidate.cland_raw_writer_cws3_o_1_3 !== candidate.rst_rl_7)$fatal(1,"RAW_EQUATION cland_raw_writer_cws3_o_1_3 cycle%0d",cycle);
if(candidate.cland_raw_writer_cws3_o_1_4 !== candidate.cland_reset_cws3_i)$fatal(1,"RAW_EQUATION cland_raw_writer_cws3_o_1_4 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_fw_ctl_p2_o_1_0 !== candidate.rst_rl_0)$fatal(1,"RAW_EQUATION cland_raw_writer_x_fw_ctl_p2_o_1_0 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_fw_ctl_p2_o_1_1 !== candidate.rst_rl_5)$fatal(1,"RAW_EQUATION cland_raw_writer_x_fw_ctl_p2_o_1_1 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_fw_ctl_p2_o_1_2 !== candidate.rst_rl_6)$fatal(1,"RAW_EQUATION cland_raw_writer_x_fw_ctl_p2_o_1_2 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_fw_ctl_p2_o_1_3 !== candidate.rst_rl_7)$fatal(1,"RAW_EQUATION cland_raw_writer_x_fw_ctl_p2_o_1_3 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_fw_ctl_p2_o_1_4 !== candidate.cland_reset_cws3_i)$fatal(1,"RAW_EQUATION cland_raw_writer_x_fw_ctl_p2_o_1_4 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_su_l0_ctl_o_1_0 !== candidate.rst_rl_0)$fatal(1,"RAW_EQUATION cland_raw_writer_x_su_l0_ctl_o_1_0 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_su_l0_ctl_o_1_1 !== candidate.rst_rl_5)$fatal(1,"RAW_EQUATION cland_raw_writer_x_su_l0_ctl_o_1_1 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_su_l0_ctl_o_1_2 !== candidate.rst_rl_6)$fatal(1,"RAW_EQUATION cland_raw_writer_x_su_l0_ctl_o_1_2 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_su_l0_ctl_o_1_3 !== candidate.rst_rl_7)$fatal(1,"RAW_EQUATION cland_raw_writer_x_su_l0_ctl_o_1_3 cycle%0d",cycle);
if(candidate.cland_raw_writer_x_su_l0_ctl_o_1_4 !== candidate.cland_reset_cws3_i)$fatal(1,"RAW_EQUATION cland_raw_writer_x_su_l0_ctl_o_1_4 cycle%0d",cycle);
end
if(baseline_cland_up_ready && first_base<0)first_base=cycle;
if(candidate_cland_up_ready && first_candidate<0)first_candidate=cycle;
if(cycle>20 && (baseline.landing_ready_cws3_i !== candidate.landing_ready_cws3_i || baseline.landing_fault_cws3_i !== candidate.landing_fault_cws3_i))$fatal(1,"IN_ADMISSION cws3_i cycle%0d",cycle);
if(baseline.landing_ready_cws3_i && candidate.landing_ready_cws3_i)begin checks=checks+1;edge_cws3_i=edge_cws3_i+1;if(baseline.cland_cws3_i !== candidate.cland_cws3_i)$fatal(1,"IN_DATA cws3_i cycle%0d",cycle);end
if(cycle>20 && (baseline.landing_ready_x_st_a_i !== candidate.landing_ready_x_st_a_i || baseline.landing_fault_x_st_a_i !== candidate.landing_fault_x_st_a_i))$fatal(1,"IN_ADMISSION x_st_a_i cycle%0d",cycle);
if(baseline.landing_ready_x_st_a_i && candidate.landing_ready_x_st_a_i)begin checks=checks+1;edge_x_st_a_i=edge_x_st_a_i+1;if(baseline.cland_x_st_a_i !== candidate.cland_x_st_a_i)$fatal(1,"IN_DATA x_st_a_i cycle%0d",cycle);end
if(cycle>20 && (baseline.landing_ready_x_st_b_i !== candidate.landing_ready_x_st_b_i || baseline.landing_fault_x_st_b_i !== candidate.landing_fault_x_st_b_i))$fatal(1,"IN_ADMISSION x_st_b_i cycle%0d",cycle);
if(baseline.landing_ready_x_st_b_i && candidate.landing_ready_x_st_b_i)begin checks=checks+1;edge_x_st_b_i=edge_x_st_b_i+1;if(baseline.cland_x_st_b_i !== candidate.cland_x_st_b_i)$fatal(1,"IN_DATA x_st_b_i cycle%0d",cycle);end
if(cycle>20 && (baseline.landing_ready_x_su_l0_ctl_i !== candidate.landing_ready_x_su_l0_ctl_i || baseline.landing_fault_x_su_l0_ctl_i !== candidate.landing_fault_x_su_l0_ctl_i))$fatal(1,"IN_ADMISSION x_su_l0_ctl_i cycle%0d",cycle);
if(baseline.landing_ready_x_su_l0_ctl_i && candidate.landing_ready_x_su_l0_ctl_i)begin checks=checks+1;edge_x_su_l0_ctl_i=edge_x_su_l0_ctl_i+1;if(baseline.cland_x_su_l0_ctl_i !== candidate.cland_x_su_l0_ctl_i)$fatal(1,"IN_DATA x_su_l0_ctl_i cycle%0d",cycle);end
if(cycle>20 && (baseline.landing_ready_x_su_l0_sc_i !== candidate.landing_ready_x_su_l0_sc_i || baseline.landing_fault_x_su_l0_sc_i !== candidate.landing_fault_x_su_l0_sc_i))$fatal(1,"IN_ADMISSION x_su_l0_sc_i cycle%0d",cycle);
if(baseline.landing_ready_x_su_l0_sc_i && candidate.landing_ready_x_su_l0_sc_i)begin checks=checks+1;edge_x_su_l0_sc_i=edge_x_su_l0_sc_i+1;if(baseline.cland_x_su_l0_sc_i !== candidate.cland_x_su_l0_sc_i)$fatal(1,"IN_DATA x_su_l0_sc_i cycle%0d",cycle);end
if(cycle>20 && (baseline_dr_cws3_o !== candidate_dr_cws3_o || baseline_df_cws3_o !== candidate_df_cws3_o))$fatal(1,"OUT_ADMISSION cws3_o cycle%0d",cycle);
if(baseline_dr_cws3_o && candidate_dr_cws3_o)begin checks=checks+1;edge_cws3_o=edge_cws3_o+1;if(baseline_down_cws3_o !== candidate_down_cws3_o)$fatal(1,"OUT_DATA cws3_o cycle%0d",cycle);end
if(cycle>20 && (baseline_dr_x_fw_ctl_p2_o !== candidate_dr_x_fw_ctl_p2_o || baseline_df_x_fw_ctl_p2_o !== candidate_df_x_fw_ctl_p2_o))$fatal(1,"OUT_ADMISSION x_fw_ctl_p2_o cycle%0d",cycle);
if(baseline_dr_x_fw_ctl_p2_o && candidate_dr_x_fw_ctl_p2_o)begin checks=checks+1;edge_x_fw_ctl_p2_o=edge_x_fw_ctl_p2_o+1;if(baseline_down_x_fw_ctl_p2_o !== candidate_down_x_fw_ctl_p2_o)$fatal(1,"OUT_DATA x_fw_ctl_p2_o cycle%0d",cycle);end
if(cycle>20 && (baseline_dr_x_su_l0_ctl_o !== candidate_dr_x_su_l0_ctl_o || baseline_df_x_su_l0_ctl_o !== candidate_df_x_su_l0_ctl_o))$fatal(1,"OUT_ADMISSION x_su_l0_ctl_o cycle%0d",cycle);
if(baseline_dr_x_su_l0_ctl_o && candidate_dr_x_su_l0_ctl_o)begin checks=checks+1;edge_x_su_l0_ctl_o=edge_x_su_l0_ctl_o+1;if(baseline_down_x_su_l0_ctl_o !== candidate_down_x_su_l0_ctl_o)$fatal(1,"OUT_DATA x_su_l0_ctl_o cycle%0d",cycle);end
if(cycle==1099)begin
if(edge_cws3_i<200)$fatal(1,"VACUOUS_EDGE cws3_i checks%0d",edge_cws3_i);$display("EDGE cws3_i checks%0d",edge_cws3_i);
if(edge_x_st_a_i<200)$fatal(1,"VACUOUS_EDGE x_st_a_i checks%0d",edge_x_st_a_i);$display("EDGE x_st_a_i checks%0d",edge_x_st_a_i);
if(edge_x_st_b_i<200)$fatal(1,"VACUOUS_EDGE x_st_b_i checks%0d",edge_x_st_b_i);$display("EDGE x_st_b_i checks%0d",edge_x_st_b_i);
if(edge_x_su_l0_ctl_i<200)$fatal(1,"VACUOUS_EDGE x_su_l0_ctl_i checks%0d",edge_x_su_l0_ctl_i);$display("EDGE x_su_l0_ctl_i checks%0d",edge_x_su_l0_ctl_i);
if(edge_x_su_l0_sc_i<200)$fatal(1,"VACUOUS_EDGE x_su_l0_sc_i checks%0d",edge_x_su_l0_sc_i);$display("EDGE x_su_l0_sc_i checks%0d",edge_x_su_l0_sc_i);
if(edge_cws3_o<200)$fatal(1,"VACUOUS_EDGE cws3_o checks%0d",edge_cws3_o);$display("EDGE cws3_o checks%0d",edge_cws3_o);
if(edge_x_fw_ctl_p2_o<200)$fatal(1,"VACUOUS_EDGE x_fw_ctl_p2_o checks%0d",edge_x_fw_ctl_p2_o);$display("EDGE x_fw_ctl_p2_o checks%0d",edge_x_fw_ctl_p2_o);
if(edge_x_su_l0_ctl_o<200)$fatal(1,"VACUOUS_EDGE x_su_l0_ctl_o checks%0d",edge_x_su_l0_ctl_o);$display("EDGE x_su_l0_ctl_o checks%0d",edge_x_su_l0_ctl_o);
end
if(cycle==1100)begin if(checks<1000)$fatal(1,"VACUOUS checks%0d base%0d candidate%0d",checks,first_base,first_candidate);$display("PASS phase%0d checks%0d collector_first_base%0d collector_first_candidate%0d",phase_i,checks,first_base,first_candidate);$finish;end
end
endmodule
