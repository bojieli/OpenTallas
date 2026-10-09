`timescale 1ns/1ps
module tb_hgi_mtp_die_facade;
 reg clk=0; always #0.4166665 clk=~clk;
 reg rst=1; reg [130:0] f_cmdproc=0; reg [522:0] f_su_red=0; reg [58:0] f_router=0; reg f_coll=1;
 wire[505:0] t_cmdproc,ref_t_cmdproc; wire[57:0] t_router,ref_t_router;wire[18:0] t_coll,ref_t_coll;
 reg[1:0] reset_reference=3; always @(posedge clk) reset_reference<={reset_reference[0],rst};
 wire ref_rst_n=~reset_reference[1];
 hfd_mtp_generic18 #(.ENABLE(1)) dut(.ck(clk),.rst(rst),.f_cmdproc(f_cmdproc),.t_cmdproc(t_cmdproc),.f_su_red(f_su_red),.f_router(f_router),.t_router(t_router),.t_coll(t_coll),.f_coll(f_coll));
 ot_hgi_mtp_core18 #(.GENERIC18(1),.TW(18),.SPECF(0)) refcore(

 .clk(clk), .rst_n(ref_rst_n),
 .start(f_cmdproc[0 +: 1]),
 .cfg_gamma(f_cmdproc[1 +: 4]),
 .cfg_force(f_cmdproc[5 +: 1]),
 .cfg_ngen(f_cmdproc[6 +: 16]),
 .cfg_plen(f_cmdproc[22 +: 16]),
 .p_tok(f_cmdproc[38 +: 18]),
 .f_tok(f_cmdproc[56 +: 18]),
 .cmd_ready(f_cmdproc[74 +: 1]),
 .eng_done(f_cmdproc[75 +: 1]),
 .sr_v(f_cmdproc[76 +: 1]),
 .sr_kind(f_cmdproc[77 +: 4]),
 .sr_idx(f_cmdproc[81 +: 16]),
 .sr_pos(f_cmdproc[97 +: 32]),
 .u_clr(f_cmdproc[129 +: 1]),
 .u_flush(f_cmdproc[130 +: 1]),
 .p_addr(ref_t_cmdproc[0 +: 16]),
 .f_addr(ref_t_cmdproc[16 +: 16]),
 .e_v(ref_t_cmdproc[32 +: 1]),
 .e_tok(ref_t_cmdproc[33 +: 18]),
 .e_idx(ref_t_cmdproc[51 +: 16]),
 .done(ref_t_cmdproc[67 +: 1]),
 .cmd_v(ref_t_cmdproc[68 +: 1]),
 .cmd_op(ref_t_cmdproc[69 +: 4]),
 .cmd_idx(ref_t_cmdproc[73 +: 8]),
 .cmd_ncol(ref_t_cmdproc[81 +: 4]),
 .cmd_pos(ref_t_cmdproc[85 +: 32]),
 .cmd_tok1(ref_t_cmdproc[117 +: 18]),
 .cmd_toks(ref_t_cmdproc[135 +: 144]),
 .am_v(ref_t_cmdproc[279 +: 1]),
 .am_idx(ref_t_cmdproc[280 +: 18]),
 .am_fault(ref_t_cmdproc[298 +: 1]),
 .sr_ready(ref_t_cmdproc[299 +: 1]),
 .sa_v(ref_t_cmdproc[300 +: 1]),
 .sa_addr(ref_t_cmdproc[301 +: 32]),
 .sa_tok(ref_t_cmdproc[333 +: 18]),
 .sa_pad(ref_t_cmdproc[351 +: 1]),
 .sa_last(ref_t_cmdproc[352 +: 1]),
 .sa_err(ref_t_cmdproc[353 +: 1]),
 .n_committed(ref_t_cmdproc[354 +: 32]),
 .step_v(ref_t_cmdproc[386 +: 1]),
 .step_a(ref_t_cmdproc[387 +: 3]),
 .step_g(ref_t_cmdproc[390 +: 4]),
 .steps(ref_t_cmdproc[394 +: 16]),
 .cyc_total(ref_t_cmdproc[410 +: 32]),
 .cyc_engine(ref_t_cmdproc[442 +: 32]),
 .cyc_markov(ref_t_cmdproc[474 +: 32]),
 .lg_v(f_su_red[0 +: 1]),
 .lg_last(f_su_red[1 +: 1]),
 .lg_bias_en(f_su_red[2 +: 1]),
 .lg_mask(f_su_red[3 +: 8]),
 .lg_vals(f_su_red[11 +: 256]),
 .lg_bias(f_su_red[267 +: 256]),
 .x_v(f_router[0 +: 1]),
 .x_draft(f_router[1 +: 1]),
 .x_ids(f_router[2 +: 54]),
 .x_col(f_router[56 +: 3]),
 .t_v(ref_t_router[0 +: 1]),
 .t_ids(ref_t_router[1 +: 54]),
 .t_col(ref_t_router[55 +: 3]),
 .u_v(ref_t_coll[0 +: 1]),
 .u_id(ref_t_coll[1 +: 9]),
 .u_mask(ref_t_coll[10 +: 8]),
 .u_last(ref_t_coll[18 +: 1]),
 .u_ready(f_coll[0 +: 1])
 );
 integer cycle,seen=0;
 initial begin
  for(cycle=0;cycle<220;cycle=cycle+1) begin
   @(negedge clk);
   if(cycle>=2 && dut.rst_n!==ref_rst_n) $fatal(1,"FACADE_RESET_MISMATCH cycle%0d",cycle);
   if(cycle>=8 && {t_cmdproc,t_router,t_coll}!=={ref_t_cmdproc,ref_t_router,ref_t_coll}) $fatal(1,"FACADE_PORT_MISMATCH cycle%0d",cycle);
   if(cycle==4 || cycle==104) rst=0;
   if(cycle==100) rst=1;
   f_cmdproc=0;f_cmdproc[1+:4]=1;f_cmdproc[5]=1;f_cmdproc[6+:16]=1;f_cmdproc[22+:16]=1;
   f_cmdproc[38+:18]=18'h20001+cycle;f_cmdproc[56+:18]=18'h20007+cycle;f_cmdproc[74]=1;f_cmdproc[75]=1;
   f_cmdproc[0]=(cycle==12 ||cycle==112);
   f_su_red=0;f_su_red[3+:8]=8'hff;
   if(t_cmdproc[68])seen=seen+1;
  end
  if(seen==0)$fatal(1,"FACADE_NO_COMMAND_OBSERVED");
  $display("HGI_FACADE18 PASS cycles220 commands%0d resetrelease2 nativecoreactualshape384/max1m",seen);$finish;
 end
endmodule
