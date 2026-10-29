`timescale 1ps/1ps
module tb_qctl_native;
 reg clk=0;always begin #416 clk=1;#417 clk=0;end
 reg rst_n=0,pw=0,start=0;reg[7:0]pa=0;reg[255:0]pd=0;reg[31:0]prog[0:2047];
 wire[1:0]lws,lqs,lqe,lks,lfs,lf;wire[6:0]lqi[0:1];wire[4:0]lqh[0:1];wire[7:0]lki[0:1];wire[11:0]lnq[0:1];
 ot_hbm_idx_qctl_static legacy(.clk_program(clk),.clk_program_mem(clk),.rst_n(rst_n),.slot(1'b0),.program_we(pw),.program_addr(pa),.program_data(pd),.start(start),.length(12'd1568),.nkeys(14'd4096),.weight_slot(lws[0]),.query_slot(lqs[0]),.query_index(lqi[0]),.query_emit(lqe[0]),.query_emit_head(lqh[0]),.key_slot(lks[0]),.key_index(lki[0]),.nq(lnq[0]),.frame_start(lfs[0]),.vf(1'b0),.qf(1'b0),.scf(1'b0),.fault(lf[0]));
 ot_hbm_idx_qctl_static_r2048 preserve(.clk_program(clk),.clk_program_mem(clk),.rst_n(rst_n),.slot(1'b0),.program_we(pw),.program_addr(pa),.program_data(pd),.start(start),.length(12'd1568),.nkeys(14'd4096),.n_rows(5'd1),.row_pitch(12'd0),.weight_slot(lws[1]),.query_slot(lqs[1]),.query_index(lqi[1]),.query_emit(lqe[1]),.query_emit_head(lqh[1]),.key_slot(lks[1]),.key_index(lki[1]),.nq(lnq[1]),.frame_start(lfs[1]),.vf(1'b0),.qf(1'b0),.scf(1'b0),.kbf(1'b0),.fault(lf[1]),.key_v(),.key_row(),.pre_v(),.pre_index(),.key_replay(),.row_start());
 wire[1:0]ws,qs,qe,ks,kv,pv,fs,rs,cf;wire[6:0]qi[0:1];wire[4:0]qh[0:1],kr[0:1];wire[7:0]ki[0:1],pi[0:1];wire[11:0]nq[0:1];wire replay;
 ot_hbm_idx_qctl_static_r2048 #(.NATIVE_IDXN(1),.ROOT_NATIVE_PROFILE(1),.PREFILLED_KEYS(1)) native_ctl(.clk_program(clk),.clk_program_mem(clk),.rst_n(rst_n),.slot(1'b0),.program_we(pw),.program_addr(pa),.program_data(pd),.start(start),.length(12'd1568),.nkeys(14'd4096),.n_rows(5'd6),.row_pitch(12'd328),.weight_slot(ws[0]),.query_slot(qs[0]),.query_index(qi[0]),.query_emit(qe[0]),.query_emit_head(qh[0]),.key_slot(ks[0]),.key_v(kv[0]),.key_index(ki[0]),.key_row(kr[0]),.pre_v(pv[0]),.pre_index(pi[0]),.key_replay(replay),.nq(nq[0]),.frame_start(fs[0]),.row_start(rs[0]),.vf(1'b0),.qf(1'b0),.scf(1'b0),.kbf(1'b0),.fault(cf[0]));
 ot_hnx_idxq_qctl #(.ROW_CLEAR_DELAY(171)) reference(.clk_program(clk),.clk_program_mem(clk),.rst_n(rst_n),.slot(1'b0),.program_we(pw),.program_addr(pa),.program_data(pd),.start(start),.length(12'd1568),.nkeys(14'd4096),.n_rows(5'd6),.row_pitch(12'd328),.weight_slot(ws[1]),.query_slot(qs[1]),.query_index(qi[1]),.query_emit(qe[1]),.query_emit_head(qh[1]),.key_slot(ks[1]),.key_v(kv[1]),.key_index(ki[1]),.key_row(kr[1]),.pre_v(pv[1]),.pre_index(pi[1]),.nq(nq[1]),.frame_start(fs[1]),.row_start(rs[1]),.vf(1'b0),.qf(1'b0),.scf(1'b0),.kbf(1'b0),.fault(cf[1]));
 wire blocked_fs,blocked_fault;
 ot_hbm_idx_qctl_static_r2048 #(.NATIVE_IDXN(1),.ROOT_NATIVE_PROFILE(0)) blocked(.clk_program(clk),.clk_program_mem(clk),.rst_n(rst_n),.slot(1'b0),.program_we(pw),.program_addr(pa),.program_data(pd),.start(start),.length(12'd1568),.nkeys(14'd4096),.n_rows(5'd6),.row_pitch(12'd328),.weight_slot(),.query_slot(),.query_index(),.query_emit(),.query_emit_head(),.key_slot(),.key_v(),.key_index(),.key_row(),.pre_v(),.pre_index(),.key_replay(),.nq(),.frame_start(blocked_fs),.row_start(),.vf(1'b0),.qf(1'b0),.scf(1'b0),.kbf(1'b0),.fault(blocked_fault));
 reg prefill_clear=0;wire clear,live,pre,rv;wire[7:0]preidx,replayidx;
 integer drop_pre,bypass_guard,wrong_clear;
 initial begin drop_pre=$test$plusargs("DROP_PRE");bypass_guard=$test$plusargs("BYPASS_GUARD");wrong_clear=$test$plusargs("WRONG_CLEAR");end
 ot_hnx_idxn_kb_ctl_prefilled control(.prefill_clear(prefill_clear||(wrong_clear!=0&&fs[0])),.key_v(kv[0]),.key_index(ki[0]),.pre_v_in(pv[0]&&drop_pre==0),.pre_index_in(pi[0]),.clear(clear),.live_v(live),.live_index(),.pre_v(pre),.pre_index(preidx),.replay_v(rv),.replay_index(replayidx));
 reg prev_pre=0;reg[7:0]prev_index=0;integer edges=0,keys=0,pre0=0,pre1=0,clears=0,frames=0,querys=0,heads=0,blocked_seen=0;
 always @(posedge clk)begin
  #10;
  if(rst_n)begin
   edges++;
   if({lws[0],lqs[0],lqi[0],lqe[0],lqh[0],lks[0],lki[0],lnq[0],lfs[0],lf[0]}!=={lws[1],lqs[1],lqi[1],lqe[1],lqh[1],lks[1],lki[1],lnq[1],lfs[1],lf[1]})$fatal(1,"QCTL_FAIL legacy identity edge%0d",edges);
   if({ws[0],qs[0],qi[0],qe[0],qh[0],kv[0],ki[0],kr[0],nq[0],fs[0],rs[0],cf[0]}!=={ws[1],qs[1],qi[1],qe[1],qh[1],kv[1],ki[1],kr[1],nq[1],fs[1],rs[1],cf[1]})$fatal(1,"QCTL_FAIL native common edge%0d",edges);
   if(cf[0]||lf[0]||ks[0]||live)$fatal(1,"QCTL_FAIL unexpected fault/live");
   if(clear&&!prefill_clear)$fatal(1,"QCTL_FAIL record start erased prefill");
   if((bypass_guard!=0?fs[0]:blocked_fs))$fatal(1,"QCTL_FAIL incoherent root profile launched");
   if(start)begin if(!blocked_fault)$fatal(1,"QCTL_FAIL missing guard");blocked_seen++;end
   if(rv)begin if(!prev_pre||prev_index!=replayidx)$fatal(1,"QCTL_FAIL replay without PRE row%0d index%0d",kr[0],ki[0]);keys++;end
   if(rv!==replay)$fatal(1,"QCTL_FAIL replay wire");
   if(pre)pre0++;if(pv[1])pre1++;if(rs[0])clears++;if(fs[0])frames++;if(qs[0])querys++;if(qe[0])heads++;
   prev_pre=pre;prev_index=preidx;
  end
 end
 initial begin
  $readmemh("prog173.hex",prog);repeat(8)@(negedge clk);rst_n=1;repeat(40)@(negedge clk);
  prefill_clear=1;@(negedge clk);prefill_clear=0;
  for(integer row=0;row<196;row++)begin pa=8'(row);for(integer j=0;j<8;j++)pd[j*32+:32]=prog[row*8+j];pw=1;@(negedge clk);pw=0;repeat(2)@(negedge clk);end
  start=1;@(negedge clk);start=0;repeat(3500)@(negedge clk);
  if(keys!=1026||pre0!=1026||pre1!=855||clears!=6||frames!=1||querys!=768||heads!=192||blocked_seen!=1)$fatal(1,"QCTL_FAIL counts keys%0d pre%0d/%0d clears%0d frames%0d queries%0d heads%0d",keys,pre0,pre1,clears,frames,querys,heads);
  $display("QCTL_PASS edges%0d legacy_identity native_common prefillkeys%0d row0extraPRE%0d clears%0d",edges,keys,pre0-pre1,clears);$finish;
 end
endmodule
