`timescale 1ns/1ps
// Real sys_face ROM read -> real HOST AUTH receiver -> real NU4/OPSEG1 controller stores.
// This bounded initialisation probe never claims a filler schedule or full-token execution.
module tb_gc3_cfg_load;
 parameter integer BAD_BASE=0;
 reg ck=0; always #0.4165 ck=~ck;
 reg rst_n=0; integer cyc=0; always @(posedge ck)cyc<=cyc+1;
 `include "program_metadata.svh"
 reg [63:0] expected[0:1031];
 string image_dir;
 initial begin if(!$value$plusargs("OT_ROM_DIR=%s",image_dir))$fatal(1,"OT_ROM_DIR required");
 $readmemh({image_dir,"/program.memh"},expected);end
 wire [74:0] pw;wire[186:0]dh;wire[75:0]po,co;wire[68:0]dbo;
 wire csr,cir,lcv;wire[17:0]nt,np;wire[5:0]cs;wire[55:0]dc;wire[379:0]nc;wire[452:0]hr;wire[115:0]cmd;wire cf;
 wire kok,kwd,fab;
 qfd_tt_ctlm_dv #(.XPF_TRANSPORT_EDGES(21),.STAGE_ME(1),.HARD_HR(1),.NU(4),.OPSEG(1),.CTX_SRC(1),.FCTX(1)) ctl(
 .ck(ck),.rst_n(rst_n),.pw(pw),.dh(dh),.dh_user(2'd0),.ctx_x(129'd0),.kok(kok),.kwd(kwd),.fab(fab),
 .program_obs(po),.control_stores_ready(csr),.layer_context_v(lcv),.native_tok(nt),.native_pos(np),.command_stage(cs),
 .cal_program_obs(co),.cal_descriptor_obs(dbo),.cal_image_ready(cir),.dc(dc),.native_cmd(nc),.native_ret(95'd3),.hr(hr),
 .cmd(cmd),.ss5(107'd0),.ag5(10'd0),.emb_start(),.emb_token(),.cf(cf));
 reg begin_v=0,auth_v=0,send_v=0;reg[1:0]send_type=0;wire tv,ov,af;wire[547:0]rec;
 qkd_program_auth_tx auth(.ck(ck),.rst_n(rst_n),.send_slot(send_v),.send_type(send_type),.begin_v(begin_v),
 .begin_epoch(16'hb0b),.expected_pw(11'd1024),.expected_dw(4'd8),.auth_v(auth_v),.auth_epoch(16'hb0b),
 .auth_digest(DIGEST),.tx_v(tv),.tx_observed_v(ov),.tx_record(rec),.fault(af));
 wire ff;
 qfd_sys_face #(.MU(1),.MU_HEAD(1)) face(.ck(ck),.rst_n(rst_n),
 .cfg_tx_we(),.cfg_rx_we(),.cfg_addr(),.cfg_data(),.cal_start(),.cal_seg(),.fwd_epoch(1'b0),
 .rx_payload(rec),.prog_rx_v(ov),.prog_witness_slot(1'b0),.prog_auth_slot(tv),.prog_context_slot(1'b0),
 .prog_tx_observed_v(),.prog_tx_record(),.emb_rx_v(1'b0),.emb_rx_slot(1'b0),.d2d_fault(1'b0),.d2d_epoch_abort(1'b0),
 .status_epoch16(),.vm_drained(),.collective_drained(),.collective_busy(),.crom_fault(),.execution_active(),.admit_ready(),
 .result_v(),.result_done(),.result_fault(),.result_cause(),.result_tag(),.result_gen(),.result_token(),.result_value(),.result_cycles(),
 .seq_dc(dc),.seq_program_obs(co),.seq_descriptor_obs(dbo),.seq_cfg_image_ready(cir),.seq_dh(dh),
 .tt_program_obs(po),.tt_control_stores_ready(csr),.tt_layer_context_v(lcv),.tt_command_stage(cs),.tt_native_tok(nt),.tt_native_pos(np),
 .tt_pw(pw),.tt_kok(kok),.tt_kwd(kwd),.tt_fab(fab),.host_epoch_valid(),.host_fused_capability(),.host_epoch(),.host_tag(),.host_generation(),
 .q_slot(),.q_slot_beat(),.kv_word_slot(),.kv_word_index(),.visibility_slot(),.complete_slot(),.native_fault(1'b0),
 .emb_word_v(),.emb_word_data(),.emb_word_token(),.emb_word_index(),.emb_word_scale(),.emb_word_epoch(),
 .emb_expected_slot(),.emb_expected_token(),.emb_expected_word(),.emb_expected_scale(),.emb_expected_epoch(),
 .emb_fill_begin(),.emb_fill_token(),.emb_fill_epoch(),.emb_core_epoch(),.emb_prov_fault(1'b0),
 .io_cmd_free(1'b1),.io_fault(1'b0),.io_shared_fault(1'b0),.fault(ff));
 integer nw=0,nd=0,errors=0;
 always @(posedge ck) if(rst_n)begin
 if(pw[74])begin
 if(pw[73:64]!==10'(nw)||pw[63:0]!==expected[nw])errors=errors+1;
 nw=nw+1;end
 if(dh[186])begin
 if(dh[185:183]!==3'(nd)||dh[182:119]!==expected[1024+nd])errors=errors+1;
 nd=nd+1;end
 end
 initial begin
 repeat(8)@(negedge ck);rst_n=1;
 repeat(300)@(negedge ck);
 if(!face.boot_done)$fatal(1,"boot notcomplete");
 begin_v=1;@(negedge ck);begin_v=0;auth_v=1;@(negedge ck);auth_v=0;
 send_type=1;send_v=1;@(negedge ck);send_v=0;repeat(3)@(negedge ck);
 send_type=2;send_v=1;@(negedge ck);send_v=0;
 repeat(1200)@(negedge ck);
 $display("GC3_LOAD words=%0d descriptors=%0d mismatch=%0d CSR=%b CAL_READY=%b CTX_BAD=%b OPSEG_FAULT=%b CF=%b FACE_FAULT=%b AUTH_FAULT=%b READY=%b",nw,nd,errors,csr,cir,ctl.ctx_bad,ctl.l_fault,cf,ff,af,face.rp_program_ready);
 if(nw!=1024||nd!=8||errors!=0||af)$fatal(1,"cfgROM replay failed");
 if(BAD_BASE==0 && (!csr||!cir||ctl.ctx_bad))$fatal(1,"real controller stores did notseal");
 if(BAD_BASE!=0 && csr)$fatal(1,"missingcalendarbase escaped");
 if(BAD_BASE==0)$display("GC3_CFG_REPLAY_PASS actualNU4OPSEG1 storessealed; fullmaster held because OPSEGmask unbound");
 else $display("GC3_MISSING_BASE_CAUGHT actualcalendarconsumer refusedimage");
 $finish;
 end
endmodule
