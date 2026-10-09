`timescale 1ns/1ps
// Minimum actual CP -> installed native record -> serial owner -> real SMH.
// Released43x256 matvec only. No stored-logit/argmax or whole-token credit.
module tb_dshbm_markov_record_join;
 reg clk=0,sclk=0,rst_n=0;always #0.416667 clk=~clk;always #0.555556 sclk=~sclk;
 reg [1023:0] dir;
 reg [31:0] seq[0:9];reg [1087:0] weights[0:343];
 reg [25215:0] xs[0:7];reg [31:0] gold[0:42],dlog[0:42],combined[0:42],expected_winner[0:0];
 integer cyc=0,rows_seen=0,line_requests=0,xbeats=0,word_reads=0,mismatches=0;
 always @(posedge clk)cyc<=cyc+1;
 reg cmd_we=0,cmd_addr=0,db_v=0,install_v=0;reg [63:0] cmd_data=0;
 wire db_ready,cp_cpl;wire [3:0] cp_status;wire launch,cp_done,cp_fault;
 wire [16:0] cp_token;wire cp_result_v;wire [31:0] cp_result_data;
 wire [31:0] cp_job;wire [3:0] cp_generation;wire [19:0] cp_position;
 wire [31:0] launch_pc;wire [16:0] launch_token;wire [19:0] launch_pos;
 ot_ds_hbm_cmdproc20 #(.ENABLE(1),.NSM(1),.NCMD(2)) cp(
  .clk(clk),.rst_n(rst_n),.cmd_we(cmd_we),.cmd_addr(cmd_addr),.cmd_wdata(cmd_data),
  .db_v(db_v),.db_rdy(db_ready),.db_token(17'd21946),.db_pos(20'd524288),
  .db_job(32'h5171),.db_generation(4'd3),.launch_v(launch),.launch_pc(launch_pc),
  .launch_token(launch_token),.launch_pos(launch_pos),.sm_done(cp_done),.sm_fault(cp_fault),
  .res_v(cp_result_v),.res_data(cp_result_data),.cpl_v(cp_cpl),.cpl_rdy(1'b1),.cpl_status(cp_status),.cpl_token(cp_token),
  .cpl_job(cp_job),.cpl_generation(cp_generation),.cpl_position(cp_position));
 wire run,run_ready,owner_done,owner_done_ready,owner_fault;
 wire [31:0] program_base;wire [32:0] program_limit;wire [15:0] records;
 wire [72:0] launch_owner={launch_pos,launch_token,4'd3,32'h5171};wire [72:0] retained_owner;
 ot_hbm_native_mtp_smh_pc_dispatch_mx1 #(.ENABLE(1)) dispatch(
  .clk(clk),.rst_n(rst_n),.install_v(install_v),.install_pc(32'd0),
  .install_program_base(32'd0),.install_program_limit(33'd40),.install_record_count(16'd1),
  .install_payload_error(1'b0),.launch_v(launch),.launch_pc(launch_pc),
  .launch_token(launch_token),.launch_position(launch_pos),.launch_owner(launch_owner),
  .run_v(run),.run_ready(run_ready),.program_base(program_base),.program_limit(program_limit),
  .record_count(records),.operand_owner(retained_owner),.operand_token(),.operand_position(),
  .owner_done(owner_done),.owner_fault(owner_fault),.owner_done_ready(owner_done_ready),
  .sm_done(cp_done),.sm_fault(cp_fault),.drained_ready());
 wire mr_v,mr_r;wire [31:0] mr_addr;reg rsp_v=0;reg [31:0] rsp_addr,rsp_data;
 wire alloc_v,alloc_rsp_r;wire [15:0] alloc_record;wire [23:0] alloc_lines;
 reg alloc_rsp_v=0;
 wire xr_v,x_ready;wire [15:0] xr_record;wire [6:0] xr_base;wire [7:0] xr_extent;
 reg x_active=0;reg [6:0] ordinal=0;reg [3:0] group=0;
 wire [27263:0] padded_x={2048'b0,xs[ordinal]};
 wire xw_en;wire [6:0] xw_addr,xw_grp;wire [2047:0] xw_data;
 wire start,start_ready;wire [12:0] op_rows;wire [15:0] op_c;wire [7:0] op_g;
 wire op_gs;wire [1:0] op_fmt;wire [6:0] op_xb;
 wire d_v,d_ready;wire [31:0] d_base;wire [23:0] d_lines;
 wire arrive,native_fault,pub_r;wire pub_v;
 ot_hbm_sm_serial_owner #(.ENABLE(1)) owner(
  .clk(clk),.rst_n(rst_n),.run_valid(run),.run_ready(run_ready),
  .program_base(program_base),.program_limit(program_limit),.record_count(records),
  .mem_req_valid(mr_v),.mem_req_ready(1'b1),.mem_req_addr(mr_addr),
  .mem_rsp_valid(rsp_v),.mem_rsp_ready(mr_r),.mem_rsp_addr(rsp_addr),.mem_rsp_data(rsp_data),.mem_rsp_error(1'b0),
  .alloc_valid(alloc_v),.alloc_ready(1'b1),.alloc_record(alloc_record),.alloc_lines(alloc_lines),
  .alloc_rsp_valid(alloc_rsp_v),.alloc_rsp_ready(alloc_rsp_r),.alloc_rsp_record(16'd0),.alloc_rsp_base(32'd0),.alloc_rsp_error(1'b0),
  .x_req_valid(xr_v),.x_req_ready(1'b1),.x_req_record(xr_record),.x_req_base(xr_base),.x_req_extent(xr_extent),
  .x_valid(x_active),.x_ready(x_ready),.x_record(16'd0),.x_ordinal(ordinal),.x_group(group),
  .x_data(padded_x[group*2048+:2048]),.x_error(1'b0),
  .xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),
  .d_valid(d_v),.d_ready(d_ready),.d_base(d_base),.d_lines(d_lines),
  .start(start),.start_ready(start_ready),.op_rows(op_rows),.op_c(op_c),.op_g(op_g),
  .op_gs(op_gs),.op_fmt(op_fmt),.op_xb(op_xb),.arrive(arrive),.sm_fault(native_fault),
  .publication_valid(pub_v),.publication_ready(pub_r),.publication_record(16'd0),
  .done(owner_done),.done_ready(owner_done_ready),.fault(owner_fault));
 wire req_v;wire [31:0] req_addr;wire [9:0] req_tag;
 reg w_v=0;reg [9:0] w_tag;reg [1087:0] w_data;
 wire rv;wire [7:0] rrow;wire [255:0] rdata;
 reg release_in=0;
 ot_hbm_accel_smh #(.NC(8),.RMAX(256),.XD(128),.REQCR(0)) smh(
  .clk(clk),.rst_n(rst_n),.start(start),.start_ready(start_ready),.op_rows(op_rows),
  .op_c(op_c),.op_g(op_g),.op_gs(op_gs),.op_fmt(op_fmt),.op_xb(op_xb),.busy(),
  .d_valid(d_v),.d_ready(d_ready),.d_base(d_base),.d_lines(d_lines),
  .req_v(req_v),.req_ready(1'b1),.req_addr(req_addr),.req_tag(req_tag),
  .rsp_v(w_v),.rsp_tag(w_tag),.rsp_data(w_data),
  .xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),
  .rv(rv),.rrow(rrow),.rdata(rdata),.fault(native_fault),.arrive(arrive),
  .release_in(release_in),.released());
 reg [42:0] seen=0;
 // One full43-row job fits the two finite64-entry CDC queues even if the
 // serial provider stalls completely. Caller cannot relaunch until publication.
 wire serial_v,serial_ready,score_accept,score_cdc_fault;wire [121:0] serial_data;
 ot_s81_pulse_cdc #(.W(122),.QD(64)) score_cdc(
  .s_clk(clk),.s_rst_n(rst_n),.i_v(rv),.i_d({retained_owner,9'b0,rrow,rdata[31:0]}),
  .i_accept(score_accept),.fault(score_cdc_fault),
  .d_clk(sclk),.d_rst_n(rst_n),.o_v(serial_v),.o_r(serial_ready),.o_d(serial_data));
 wire lg_req,lg_rsp_r;wire [72:0] lg_owner;wire [16:0] lg_token;
 reg lg_rsp=0;reg [72:0] lg_ret_owner;reg [16:0] lg_ret_token;reg [31:0] lg_data;
 wire score_v,score_r,score_fault;wire [72:0] score_owner;wire [16:0] score_token;wire [31:0] score_value;
 ot_hbm_native_mtp_score_join_mx1 #(.ENABLE(1)) add_join(
  .clk(sclk),.rst_n(rst_n),.i_v(serial_v),.i_ready(serial_ready),
  .i_owner(serial_data[121:49]),.i_token(serial_data[48:32]),.i_score(serial_data[31:0]),
  .lg_req_v(lg_req),.lg_req_ready(1'b1),.lg_req_owner(lg_owner),.lg_req_token(lg_token),
  .lg_rsp_v(lg_rsp),.lg_rsp_ready(lg_rsp_r),.lg_rsp_owner(lg_ret_owner),
  .lg_rsp_token(lg_ret_token),.lg_rsp_score(lg_data),.lg_rsp_error(1'b0),
  .o_v(score_v),.o_ready(score_r),.o_owner(score_owner),.o_token(score_token),.o_score(score_value),
  .fault(score_fault),.drained_ready());
 reg rank_start=0;wire rank_ready,rank_v,rank_r,rank_fault;
 wire [72:0] rank_owner;wire [16:0] rank_token;wire [31:0] rank_score;
 ot_hbm_native_mtp_rank_argmax_mx1 #(.ENABLE(1),.MAX_RANKS(43)) rank_merge(
  .clk(sclk),.rst_n(rst_n),.start_v(rank_start),.start_ready(rank_ready),
  .start_owner({20'd524288,17'd21946,4'd3,32'h5171}),.nranks(12'd43),
  .i_v(score_v),.i_ready(score_r),.i_owner(score_owner),.i_rank(score_token[11:0]),
  .i_present(1'b1),.i_token(score_token),.i_score(score_value),
  .o_v(rank_v),.o_ready(rank_r),.o_owner(rank_owner),.o_token(rank_token),.o_score(rank_score),
  .fault(rank_fault),.drained_ready());
 wire return_v,return_fault;wire [89:0] returned;
 ot_s81_pulse_cdc #(.W(90),.QD(8)) result_cdc(
  .s_clk(sclk),.s_rst_n(rst_n),.i_v(rank_v&&rank_r),.i_d({rank_owner,rank_token}),
  .i_accept(rank_r),.fault(return_fault),
  .d_clk(clk),.d_rst_n(rst_n),.o_v(return_v),.o_r(pub_r),.o_d(returned));
 assign pub_v=return_v;
 assign cp_result_v=return_v&&pub_r;
 assign cp_result_data={15'b0,returned[16:0]};
 integer combined_rows=0,combined_mismatches=0;
 always @(posedge sclk)if(rst_n)begin
  if(lg_rsp && lg_rsp_r)lg_rsp<=0;
  if(lg_req)begin
   if(lg_token>=43)$fatal(1,"actual stored-logit source bounds");
   lg_rsp<=1;lg_ret_owner<=lg_owner;lg_ret_token<=lg_token;lg_data<=dlog[lg_token];
  end
  if(score_v && score_r)begin
   combined_rows<=combined_rows+1;
   if(score_value!==combined[score_token])begin combined_mismatches<=combined_mismatches+1;
    $display("MISMATCH combined row=%0d got=%h gold=%h",score_token,score_value,combined[score_token]);end
  end
 end
 always @(posedge clk)if(rst_n)begin
  rsp_v<=mr_v;if(mr_v)begin
   if(mr_addr>=40 || mr_addr[1:0]!=0)$fatal(1,"native program address bounds");
   rsp_addr<=mr_addr;rsp_data<=seq[mr_addr/4];word_reads<=word_reads+1;
  end
  alloc_rsp_v<=alloc_v;
  if(alloc_v && (alloc_record!=0 || alloc_lines!=344))$fatal(1,"real allocation request mismatch");
  if(xr_v)begin
   if(xr_record!=0 || xr_base!=0 || xr_extent!=8)$fatal(1,"real X context mismatch");
   x_active<=1;ordinal<=0;group<=0;
  end
  if(x_active && x_ready)begin
   xbeats<=xbeats+1;
   if(group==12)begin group<=0;if(ordinal==7)x_active<=0;else ordinal<=ordinal+1;end
   else group<=group+1;
  end
  w_v<=req_v;
  if(req_v)begin
   if(req_addr>=344)$fatal(1,"native weight address bounds");
   w_tag<=req_tag;w_data<=weights[req_addr];line_requests<=line_requests+1;
`ifdef MUTATE_WEIGHT
   w_data<=weights[req_addr]^1088'h8000;
`endif
  end
  release_in<=arrive;
  if(cp_result_v && returned[89:17]!==retained_owner)$fatal(1,"actual returned winner ownership at acceptance");
  if(rv)begin
   if(!score_accept)$fatal(1,"native pulse score capacity exhausted");
   if(rrow>=43 || seen[rrow])$fatal(1,"native duplicate/out-of-bounds result");
   seen[rrow]<=1;rows_seen<=rows_seen+1;
   if(rdata[31:0]!==gold[rrow] || rdata[255:32]!==224'b0)begin
    mismatches<=mismatches+1;$display("MISMATCH row=%0d got=%h gold=%h",rrow,rdata[31:0],gold[rrow]);
   end
  end
  if(cp_cpl)begin
   if(cp_status!=0 || cp_token!==expected_winner[0][16:0] || rows_seen!=43 || combined_rows!=43 ||
      combined_mismatches!=0 || line_requests!=344 || word_reads!=10 || xbeats!=104 || mismatches!=0 ||
      native_fault || owner_fault || cp_fault || score_cdc_fault || score_fault || rank_fault || return_fault)
    $fatal(1,"actual CP/record/SMH numerical gate failed status=%0d rows=%0d mismatches=%0d",cp_status,rows_seen,mismatches);
   if(cp_job!=32'h5171 || cp_generation!=3 || cp_position!=524288)$fatal(1,"actual CP completion ownership");
   $display("PASS actual CP record SMH released Markov rows43 K256 NC8 storedDLOG LAT3 serial0.9GHz localargmax winner=%0d cycles=%0d",cp_token,cyc);$finish;
  end
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR required");
  $readmemh({dir,"/seq.hex"},seq);$readmemh({dir,"/lines.hex"},weights);
  $readmemh({dir,"/x.hex"},xs);$readmemh({dir,"/gold.hex"},gold);
  $readmemh({dir,"/dlog.hex"},dlog);$readmemh({dir,"/combined.hex"},combined);$readmemh({dir,"/winner.hex"},expected_winner);
  repeat(4)@(negedge clk);rst_n=1;
  @(negedge clk);install_v=1;cmd_we=1;cmd_addr=0;cmd_data=64'h1000100000000000;
  @(negedge clk);install_v=0;cmd_addr=1;cmd_data=64'h2000000000000000;
  @(negedge clk);cmd_we=0;
  @(negedge sclk);rank_start=1;
  while(!rank_ready)@(negedge sclk);
  @(negedge sclk);rank_start=0;
  while(!db_ready)@(negedge clk);
  db_v=1;@(negedge clk);db_v=0;
 end
endmodule
