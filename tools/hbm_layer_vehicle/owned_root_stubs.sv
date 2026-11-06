// Deliberate wrapper-only abstraction. These are NOT arithmetic or protocol proofs.
module ot_static_program_target #(parameter PCW=10,TGT_PIN=1)(
 input clk,rst_n,input[7:0]tgt,input cfg_v,input[7:0]cfg_target,input[11:0]cfg_addr,
 input[255:0]cfg_data,input desc_v,input[11:0]desc_base,input[12:0]desc_limit,input[15:0]desc_loops,
 input launch_v,program_active,output program_cfg_we,output[PCW-1:0]program_cfg_addr,
 output[255:0]program_cfg_data,output program_start_v,output[PCW-1:0]program_start_base,
 output[PCW:0]program_start_limit,output[15:0]program_start_loops,output configured,fault);
 assign program_cfg_we=cfg_v&&cfg_target==tgt;assign program_cfg_addr=cfg_addr[PCW-1:0];
 assign program_cfg_data=cfg_data;assign program_start_v=0;assign program_start_base=0;
 assign program_start_limit=0;assign program_start_loops=0;assign configured=1;assign fault=0;
endmodule
module ot_hbm_hc_eng_seq_static #(parameter W=124)(input clk,rst_n,cfg_we,input[9:0]cfg_addr,
 input[255:0]cfg_data,input start_v,input[9:0]start_base,input[10:0]start_limit,input[15:0]start_loops,
 output[W-1:0]event_word,output event_v,output[19:0]t,output active,done,fault);
 assign event_word=cfg_data[W-1:0];assign event_v=cfg_we;assign t=0;
 assign active=cfg_we;assign done=0;assign fault=0;
endmodule
module ot_hdc_v41x_hcp_sys1_static #(parameter W=256,TL=4,PMAX=8,OMAX=32,AW=10,CW=16,ML=2,DF=32,
 STATIC_CALENDAR=1,SYS=1,SYS_LAT=1,TPRE=7)(input clk,reduction_clk,scalar_clk,rst_n,calendar_pop,
 input cmd_valid,output cmd_ready,input[3:0]cmd_npos,input[5:0]cmd_nout,input[CW-1:0]cmd_nchunk,
 input cmd_scale,input[31:0]cmd_nf,cmd_eps,input[AW-1:0]cmd_wbase,cmd_xbase,
 output[7:0]w_re,x_re,output[8*AW-1:0]w_addr,x_addr,input[8*W*32-1:0]w_data,input[8*W*16-1:0]x_data,
 output reg o_valid, input o_ready,output reg[2:0]o_pos,output reg[4:0]o_idx,
 output reg[31:0]o_data,output o_last,fault,idle,
 output sd_v,sd_ss,output[$clog2(W):0]sd_nv,output[AW-1:0]sd_wa,sd_xa,
 input[W*32/(1<<TPRE)-1:0]sys_sum,input sys_fault);
 assign cmd_ready=1;assign w_re=0;assign x_re=0;assign w_addr=0;assign x_addr=0;
 assign o_last=0;assign fault=0;assign idle=1;assign sd_v=0;assign sd_ss=0;
 assign sd_nv=0;assign sd_wa=0;assign sd_xa=0;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin o_valid<=0;o_pos<=0;o_idx<=0;o_data<=0;end
  else begin o_valid<=cmd_valid;if(cmd_valid)begin
    o_pos<=3'(cmd_npos-1);o_idx<=5'(cmd_eps[4:0]%cmd_nout);o_data<=cmd_eps^32'(cmd_wbase);
  end end
 end
endmodule
module ot_sram_1r1w_1024x256_m2_r2c2(input clk,r_ce_in,input[9:0]r_addr_in,output[255:0]rd_out,
 input w_ce_in,input[9:0]w_addr_in,input[255:0]wd_in,w_mask_in,input[1:0]rr_en,input[17:0]rr_addr,
 input[1:0]cr_en,input[15:0]cr_sel);assign rd_out=0;endmodule
module ot_hbm_hc_tail_unit_static #(parameter MUT_PRE=0)(input clk,rst_n,launch,
 input[767:0]mixes,bases,input[95:0]scales,output result_v,output[767:0]result,output fault);
 assign result_v=0;assign result=0;assign fault=0;
endmodule
