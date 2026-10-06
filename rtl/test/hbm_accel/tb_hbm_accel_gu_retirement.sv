`timescale 1ns/1ps
// Actual selected-SIMT LDG -> CVTBF16 -> retirement -> acknowledged STG.
// Stimulus is the retained native GU cold FP32 output; expected is comparator
// only. This exporter gate does not claim a live TC->GU->SwiGLU chain.
module tb_hbm_accel_gu_retirement #(parameter integer EXPORT=1, METADATA_ONLY=0);
 localparam integer SPANS=METADATA_ONLY?1:768;
 reg clk=0,rst_n=0; always #0.4165 clk=~clk;
 reg im_we=0,launch_v=0; reg [12:0] im_addr=0; reg [63:0] im_data=0;
 reg [7:0] sid=0,did=0; reg [8:0] expert=41; reg matrix=0;
 reg [11:0] row_base=0; reg [31:0] convert_pc=3,convert_src=1;
 localparam [72:0] FRAME={20'hfffff,17'h1a321,4'h9,32'h9234abcd};
 reg [72:0] frame=FRAME; reg owner_valid=1,accept=0,warm_req=0;
 wire warm_ack,retained,ce,due;
 wire done,fault,busy,req_v,req_we,rsp_rdy,gv,terminal;
 wire [31:0] req_addr,req_strb; wire [255:0] req_data; wire [15:0] req_tag;
 reg rsp_v=0,rsp_we=0; reg [15:0] rsp_tag=0; reg [255:0] rsp_data=0;
 wire [2047:0] bf16; wire [8:0] oe,oc; wire om;
 wire [11:0] obr; wire [7:0] ofirst,os,od; wire [72:0] oframe; wire [31:0] oop;
 ot_hbm_accel_simt_sm #(.ENABLE(1),.GU_JOIN(EXPORT),.NL(128),.NV(256),.SMEM_WORDS(64),
  .TC_SUB(1),.TC_LS(1),.TC_XDEPTH(8),.TC_RMAX(16),.TC_LEV(1),.BC_DEPTH(8)) dut(
  .clk(clk),.rst_n(rst_n),.sm_id(sid),.die_id(did),.im_we(im_we),.im_addr(im_addr),.im_data(im_data),
  .launch_v(launch_v),.launch_pc(32'd0),.launch_token(16'ha321),.launch_pos(16'hffff),
  .sm_done(done),.sm_fault(fault),.busy(busy),.res_v(),.res_data(),.bar_arrive(),.bar_release(1'b0),
  .lreq_v(req_v),.lreq_rdy(1'b1),.lreq_we(req_we),.lreq_addr(req_addr),.lreq_wdata(req_data),.lreq_wstrb(req_strb),.lreq_tag(req_tag),
  .lrsp_v(rsp_v),.lrsp_rdy(rsp_rdy),.lrsp_we(rsp_we),.lrsp_tag(rsp_tag),.lrsp_data(rsp_data),
  .treq_v(),.treq_rdy(1'b0),.treq_addr(),.treq_tag(),.trsp_v(1'b0),.trsp_rdy(),.trsp_tag(16'd0),.trsp_data(256'd0),
  .coll_req_v(),.coll_req_rdy(1'b0),.coll_mode(),.coll_count(),.coll_data(),.coll_rsp_v(1'b0),.coll_rsp_rdy(),.coll_rsp_data(4096'd0),
  .coll_x(),.coll_off(),.coll_nown(),.coll_fuse(),.coll_resid(),.coll_rsp_ss(32'd0),.coll_rsp_err(1'b0),
  .gu_join_launch(1'b1),.gu_join_owner_valid(owner_valid),.gu_join_pc(convert_pc),.gu_join_src(convert_src[7:0]),
  .gu_join_expert(expert),.gu_join_matrix(matrix),.gu_join_row_base(row_base),.gu_join_lane_first(8'd0),.gu_join_count(9'd12),
  .gu_join_frame(frame),.gu_join_op(expert==41?32'd0:32'd1),.gu_join_v(gv),.gu_join_accept(accept),.gu_join_bf16(bf16),
  .gu_join_out_expert(oe),.gu_join_out_matrix(om),.gu_join_out_row_base(obr),.gu_join_out_lane_first(ofirst),.gu_join_out_count(oc),
  .gu_join_out_frame(oframe),.gu_join_out_op(oop),.gu_join_out_sm(os),.gu_join_out_die(od),.gu_join_terminal(terminal),
  .gu_join_warm_reset_req(warm_req),.gu_join_warm_reset_ack(warm_ack),.gu_join_retained(retained),.gu_join_ce(ce),.gu_join_due(due),
  .st_instr(),.st_cycles(),.st_stall_mem(),.st_tc_rows());
 reg [31:0] actual[0:9215],expected[0:9215],meta[0:3839];
 integer span=0,rows=0,stores=0,acks=0,exports=0,total_hold=0;
 reg accepted=0;
 // Two response seats suffice for this 12-row actual LSU load/store. Neither
 // response data nor instructions use expected[]; it is read only in checks.
 always @(posedge clk) begin : memory_port
  integer base,r,b;
  rsp_v<=0;
  if(rst_n && req_v) begin
   if(req_addr!=0 && req_addr!=32 && req_addr!=64 && req_addr!=96) $fatal(1,"unexpected LSU address");
   rsp_v<=1; rsp_we<=req_we; rsp_tag<=req_tag; rsp_data<=0;
   for(b=0;b<8;b=b+1) begin
    base=int'(req_addr)/4+b;
    if(!req_we && base<12) rsp_data[b*32+:32]<=actual[span*12+base];
    if(req_we && req_strb[b*4+:4]!=0) begin
     r=base-16;
     if(r<0 || r>=12 || req_strb[b*4+:4]!=4'hf) $fatal(1,"store mask/range");
     if(EXPORT && !accepted) $fatal(1,"store before export acceptance");
     if(req_data[b*32+:32]!==expected[span*12+r]) $fatal(1,"rounded store mismatch span=%0d row=%0d actual=%h expected=%h",span,r,req_data[b*32+:32],expected[span*12+r]);
     stores=stores+1;
    end
   end
  end
  if(rst_n && rsp_v && rsp_we) acks=acks+1;
  if(!EXPORT && (gv || terminal || bf16!=0 || oframe!=0 || oc!=0)) $fatal(1,"default-off export visible");
 end
 function automatic [63:0] ins(input [7:0] op,d,a,b,input [31:0] imm);ins={op,d,a,b,imm};endfunction
 task automatic word(input integer addr,input [63:0] data);
  @(negedge clk); im_we=1;im_addr=13'(addr);im_data=data;
  @(negedge clk); im_we=0;
 endtask
 task automatic reset_sm;
  @(negedge clk);rst_n=0;launch_v=0;accept=0;frame=FRAME;owner_valid=1;accepted=0;warm_req=0;
  repeat(3) @(negedge clk);rst_n=1;
 endtask
 task automatic launch;
  @(negedge clk);launch_v=1;@(negedge clk);launch_v=0;
 endtask
 reg [2047:0] held;
 reg [71:0] clean_code[0:2];
 integer ce_trials=0,due_trials=0;
 initial begin
  $readmemh("actual.hex",actual);$readmemh("expected.hex",expected);$readmemh("descriptors.hex",meta);
  reset_sm();
  word(0,ins(8'h28,4,0,0,0)); // U4=0
  word(1,ins(8'h38,1,4,11,0)); // actual retained FP32 GU, 12 lanes
  word(2,ins(8'h0e,3,1,0,0)); // generic CVT: must never export
  word(3,ins(8'h0e,2,1,0,0)); // caller-bound real conversion
  word(4,ins(8'h39,2,4,11,64)); // real acknowledged rounded store
  word(5,ins(8'h32,0,0,0,0));
  for(span=0;span<SPANS;span=span+1) begin
   @(negedge clk);
   expert=9'(meta[span*5]);matrix=1'(meta[span*5+1]);row_base=12'(meta[span*5+2]);
   sid=8'(meta[span*5+3]);did=8'(meta[span*5+4]);accepted=0;accept=0;
   launch();
   if(EXPORT) begin
    wait(gv||fault); if(fault) $fatal(1,"unexpected exporter fault span=%0d",span);
    @(negedge clk);held=bf16;
    repeat(1+span%17) begin
     if(!gv || bf16!==held || oe!==expert || om!==matrix || obr!==row_base || ofirst!=0 || oc!=12 ||
        oframe!==FRAME || oop!==(expert==41?32'd0:32'd1) || os!==sid || od!==did || done || terminal)
       $fatal(1,"held descriptor/payload/drain mismatch span=%0d",span);
     total_hold++; @(negedge clk);
    end
    for(integer r=0;r<12;r++) begin
     if(bf16[r*16+:16]!==expected[span*12+r][31:16]) $fatal(1,"BF16 export mismatch span=%0d row=%0d",span,r);
     rows++;
    end
    accept=1;accepted=1;exports++;
    @(negedge clk);accept=0;
   end
   wait(done||fault);@(negedge clk);if(fault || (EXPORT && !terminal)) $fatal(1,"terminal fault/missing GU completion span=%0d done=%b fault=%b enrolled=%b seen=%b terminal=%b",span,done,fault,dut.g_on.gu_en,dut.g_on.gu_seen,terminal);
   @(negedge clk);
  end
  if(stores!=12*SPANS || acks!=2*SPANS || (EXPORT && (rows!=12*SPANS || exports!=SPANS))) $fatal(1,"row/ack totals");
  $display("PASS_GU_RETIREMENT_EXPORT enabled=%0d experts=41,65 matrices=G,U rows=%0d stores=%0d acks=%0d spans=%0d held_cycles=%0d retained_FP32_input=1 live_full_chain=0",EXPORT,rows,stores,acks,exports,total_hold);
  if(EXPORT) begin
   `ifdef GU_METADATA_FAULTS
   // Inject every bit of THREE actual W6 words; accept HIGH during CE.
   span=0;expert=41;matrix=0;row_base=0;sid=0;did=0;
   for(integer k=0;k<3;k++)for(integer b=0;b<72;b++)begin
    reset_sm();launch();wait(gv);@(negedge clk);held=bf16;
    for(integer j=0;j<3;j++)clean_code[j]=dut.g_on.g_gu_coded.u_meta.code[j];
    dut.g_on.g_gu_coded.u_meta.code[k]=clean_code[k]^(72'b1<<b);
    accept=1;#0.001;
    if(!ce||due||gv||terminal||warm_ack||!retained||dut.g_on.gu_phase!=2)
      $fatal(1,"CE permissions/debt k=%0d b=%0d",k,b);
    @(negedge clk);accept=0;
    if(ce||due||fault||!gv||bf16!==held||dut.g_on.gu_phase!=2)
      $fatal(1,"CE scrub/recheck/debt k=%0d b=%0d",k,b);
    for(integer j=0;j<3;j++)if(dut.g_on.g_gu_coded.u_meta.code[j]!==clean_code[j])$fatal(1,"CE wrong scrub row");
    // Raw original ALU dest/valid no longer authorise GU retirement.
    dut.g_on.alu_wd=8'd15;dut.g_on.alu_wv=0;
    accept=1;accepted=1;@(negedge clk);accept=0;
    wait(done||fault);@(negedge clk);
    if(fault||!terminal||dut.g_on.vr[2][31:0]!==expected[0])$fatal(1,"CE accepted destination/terminal");
    ce_trials++;
   end
   $display("PASS_CODED_METADATA_CE_ALL_BITS cases=%0d words=3 bits=216 no_early_accept=1 destination_protected=1",ce_trials);
   // DUE freezes code/payload and cannot acknowledge warm reset.
   for(integer k=0;k<3;k++)for(integer pair_case=0;pair_case<2;pair_case++)begin
    reset_sm();launch();wait(gv);@(negedge clk);held=bf16;
    clean_code[k]=dut.g_on.g_gu_coded.u_meta.code[k]^(72'd3<<(pair_case?69:0));
    dut.g_on.g_gu_coded.u_meta.code[k]=clean_code[k];accept=1;warm_req=1;#0.001;
    if(!due||gv||warm_ack||!retained||!fault)$fatal(1,"DUE immediate permission");
    repeat(4)begin
     @(negedge clk);
     if(!due||gv||terminal||warm_ack||!retained||bf16!==held||dut.g_on.g_gu_coded.u_meta.code[k]!==clean_code[k])
       $fatal(1,"DUE lost evidence/debt k=%0d",k);
    end
    due_trials++;
   end
   $display("PASS_CODED_METADATA_DUE cases=%0d fail_hold=1 root_POR_only=1",due_trials);
   reset_sm();launch();wait(gv);@(negedge clk);warm_req=1;held=bf16;
   repeat(4)begin @(negedge clk);if(warm_ack||!retained||!gv||bf16!==held||done)$fatal(1,"warm erased held span");end
   accept=1;accepted=1;@(negedge clk);accept=0;
   wait(done||fault);@(negedge clk);if(fault||!warm_ack||retained||!terminal)$fatal(1,"warm acknowledgement before/after real drain");
   launch();if(busy||!warm_ack)$fatal(1,"launch bypassed warm quarantine");
   warm_req=0;
   // CE after sm_done cannot erase coded terminal visibility.
   @(negedge clk);dut.g_on.g_gu_coded.u_meta.code[2]=dut.g_on.g_gu_coded.u_meta.code[2]^72'd1;#0.001;
   if(!ce||terminal||warm_ack||!retained)$fatal(1,"completed CE permissions");
   @(negedge clk);if(ce||!terminal||fault)$fatal(1,"completed CE lost coded terminal debt");
   $display("PASS_WARM_QUARANTINE_AND_CODED_COMPLETION active_debt_preserved=1 launch_blocked=1 late_CE_terminal_recovers=1");
   `endif
   span=0;expert=41;matrix=0;row_base=0;sid=0;did=0;
   reset_sm();convert_src=2;launch();wait(fault);if(gv||terminal)$fatal(1,"wrong source exported");
   $display("PASS_REJECT_WRONG_BOUND_SOURCE");
   reset_sm();convert_src=1;convert_pc=6;word(3,ins(8'h32,0,0,0,0));launch();wait(fault);if(gv||terminal)$fatal(1,"missing conversion accepted");
   $display("PASS_REJECT_MISSING_CONVERSION");
   reset_sm();convert_pc=3;word(3,ins(8'h0e,2,1,0,0));launch();wait(gv);@(negedge clk);held=bf16;frame=FRAME^73'd1;
   wait(fault);if(gv||terminal||bf16!==held)$fatal(1,"owner change consumed/changed payload");
   $display("PASS_REJECT_CHANGED_OWNER_FRAME");
   reset_sm();frame=FRAME^73'h1000000000;launch();wait(fault);if(gv||terminal)$fatal(1,"launch identity accepted");
   $display("PASS_REJECT_LAUNCH_IDENTITY");
  end
  $finish;
 end
endmodule
