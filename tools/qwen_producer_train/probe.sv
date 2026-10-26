module probe(input wire ck,rst_n,go,train_start,output wire ov,output wire fault,output wire candidate_fault,output wire rbv,output wire[19:0]row,output wire[15:0]omask);
wire pv,we;wire[112:0]pf;wire[23:0]addr;wire[15:0]mask;wire[550:0]rb;
ot_qwen_me_spctl_w12 #(.W(16),.IL(8),.NW(18),.GT(3072),.SMIN(7),.SMAX(11),.TCUT(7),.XD(105),.XVM(15),.ORD(7),.ACC_LAT(7),.TREE_LAT(7),.MUL_LAT(6),.SCALE_LAT(8),.FAST_ISSUE(1),.KV_PREP(3),.BANDF(1),.SPRE(2),.XADDR(0),.PQ(1)) ctl(
.clk(ck),.rst_n(rst_n),.go(go),.land_cnt(16'd0),
.i_nout(18'd768),.i_tiles(18'd1),.i_k(18'd8),.i_wsrc(1'b0),.i_wbase(24'd0),.i_ts(24'd64),.i_ks(24'd8),.i_js(24'd1),.i_xbase(24'd4096),.i_xks(24'd1),.i_xjs(24'd0),.i_xcs(24'd8),.i_jsh(3'd0),.i_split(4'd9),.i_wcs(24'd0),.i_round(1'b1),.i_obase(24'd768),.i_ots(24'd8),.i_ojs(24'd1),.i_mmode(1'b0),.i_oen(1'b1),.i_amax(1'b0),.i_rmax(1'b0),.i_mbase(24'd0),.x_q('0),.tr_fault('0),.p_am('0),.p_fault('0),.fab_fault(1'b0),.p_v_e2(pv),.p_f_e2(pf));
ot_qwen_me_spport_w12 #(.W(16),.IL(8),.AW(24),.NW(18),.GT(3072),.SMIN(7),.PQ(1),.TREE_LAT(7),.SCALE_LAT(8),.BANDF(1),.TCUT(7),.HARD_MUL(0)) port0(
.clk(ck),.ck_mul('0),.rst_n(rst_n),.pt_id(16'd0),.lv_in({16{32'h3f800000}}),.a_v_e2(pv),.a_f_e2(pf),.scale_q({8{32'h3f800000}}),.o_we(we),.o_addr(addr),.o_mask(mask),.o_ov(ov));
wire[4424:0]rq={ov,7'd0,we,3864'd0,addr,mask,512'd0};
qfd_res_ser_static #(.BAND(0),.NB(3),.D(2)) ser(.ck(ck),.rst_n(rst_n),.me_en(1'b1),.rq(rq),.rb(rb),.fault(fault));

wire[550:0]candidate_rb;
qfd_res_train_static #(.BAND(0))candidate(.ck(ck),.ck_bank({24{ck}}),.rst_n(rst_n),.train_start(train_start),.train_count(4'd1),.capture_stride(32'd64),.payload_write(1'b1),.rq(rq),.rb(candidate_rb),.fault(candidate_fault));
assign rbv=candidate_rb[550];assign row=candidate_rb[547:528];assign omask=candidate_rb[527:512];
endmodule
