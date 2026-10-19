`timescale 1ns/1ps
// Component path cut: actual accepted RX/observer -> actual LP primitives -> actual GI.
// Uses exact D4/K2 input and output landings from current generated CTLM LP.
// Head/ME/arithmetic are outside this probe; no full-token or physical-clock claim.
module sf_native_probe_land #(parameter W=1,K=2)(input ck,rsi_w,rsi_r,input[W-1:0]i,output[W-1:0]o);
 wire[4*W-1:0]bank;wire[11:0]epo;wire[3:0]vld;
 ot_pl_land_w #(.W(W),.D(4)) w(.ck(ck),.rsi(rsi_w),.i(i),.bank(bank),.epo(epo),.vld(vld));
 ot_pl_land_r #(.W(W),.D(4),.K(K)) r(.ck(ck),.rsi(rsi_r),.bank(bank),.epo(epo),.vld(vld),.o(o));
endmodule
module tb_sysface_lp_bank_native_join #(parameter MUT=0);
 reg ck=0;always #5 ck=~ck;reg rst_n=0;wire clk=ck;
 reg[17:0]ETOK=65536;reg[511:0]row[0:63];reg[15:0]ESCALE=0;string vectors;
 integer reads=0,outputs=0,scale_reads=0,validations=0;
 wire rr,rhr,rcore,rgi;
 ot_pl_pad #(.W(1),.N(1)) root(.ck(ck),.d(rst_n),.q(rr));
 ot_pl_pad #(.W(1),.N(2)) hr(.ck(ck),.d(rr),.q(rhr));
 ot_pl_pad #(.W(1),.N(2)) core(.ck(ck),.d(rr),.q(rcore));
 ot_pl_pad #(.W(1),.N(3)) gi_reset(.ck(ck),.d(rcore),.q(rgi));
 reg[186:0]dh=0;reg init_u0=0;wire[186:0]dh_l;wire init_l;
 sf_native_probe_land #(.W(187)) ld(.ck(ck),.rsi_w(rhr),.rsi_r(rcore),.i(dh),.o(dh_l));
 sf_native_probe_land li(.ck(ck),.rsi_w(rhr),.rsi_r(rcore),.i(init_u0),.o(init_l));
 reg offer=0,role=0;reg[1:0]role_user=0;reg[547:0]record=0;
 wire av,hv,rxf,obf,mv;wire[15:0]he,me;wire[58:0]ht;wire[1:0]hg,mu,mg;wire[17:0]mt;wire[128:0]ctx,ctx_l;
 qfd_host_native_context_rx rx(.ck(ck),.rst_n(rst_n),.receive_slot(offer),.rx_v(offer),.rx_record(record),.program_begin_v(1'b0),.program_ready(1'b1),.installed_fusedcap(1'b1),.program_epoch(16'hbeef),.program_digest(64'h123456789abcdef0),.head_context_v(1'b0),.head_stage(6'd0),.head_token(18'd0),.head_position(18'd0),.native_active(1'b0),.accepted_v(av),.host_epoch_valid(hv),.host_epoch(he),.host_tag(ht),.host_gen(hg),.host_fusedcap(),.host_image_epoch(),.host_image_digest(),.fault(rxf));
 qfd_sys_face_accepted_mu_identity #(.EPOCH_EXPORT(1)) obs(.ck(ck),.rst_n(rst_n),.offer_slot(offer),.offer_v(offer),.offer_record(record),.host_accept_v(av),.host_epoch_valid(hv),.host_epoch(he),.host_tag(ht),.host_gen(hg),.program_ready(1'b1),.program_cap(1'b1),.program_fault(rxf),.program_epoch(16'hbeef),.program_digest(64'h123456789abcdef0),.epoch_slot(role),.epoch_user(role_user),.accepted_epoch_v(mv),.accepted_epoch_user(mu),.accepted_epoch(me),.accepted_token(mt),.accepted_generation(mg),.ctx_x(ctx),.fault(obf));
 sf_native_probe_land #(.W(129)) lc(.ck(ck),.rsi_w(rhr),.rsi_r(rcore),.i(ctx),.o(ctx_l));
 wire es_raw;wire[17:0]et_raw;wire[1:0]eu_raw;wire[61:0]dcs;
 qfd_tt_ctlm_dv_gi #(.NU(4),.STAGE_ME(1),.OPSEG(1),.OPSEG_EXPANDED(1),.OPSEG_PINREG(1),.CTX_SRC(1),.FCTX(1),.EMB_ID(1),.INIT_U0(1),.INIT_FIRST(52),.INIT_CNT(3)) dut(.ck(ck),.rst_n(rgi),.dh(dh_l),.dh_user(2'd0),.init_u0((MUT==3)?init_u0:init_l),.ctx_x((MUT==1)?ctx:ctx_l),.mu_fault(1'b0),.ss5(107'd0),.ag5(10'd0),.fab(1'b0),.cmd(),.dcs(dcs),.emb_start(es_raw),.emb_token(et_raw),.emb_user(eu_raw),.s_start(),.s_stage(),.st(),.tl(),.cal_program_obs(),.cal_descriptor_obs(),.cal_image_ready(),.fctx(),.hu(),.su_obs_o(),.su_acc_o(),.x_oprog(),.x_orows(),.x_oidle(),.rom_ret_v());
 wire es;wire[17:0]et;wire[1:0]eu;
 sf_native_probe_land #(.K(MUT==2?1:2)) los(.ck(ck),.rsi_w(rcore),.rsi_r(rhr),.i(es_raw),.o(es));
 sf_native_probe_land #(.W(18)) lot(.ck(ck),.rsi_w(rcore),.rsi_r(rhr),.i(et_raw),.o(et));
 sf_native_probe_land #(.W(2)) lou(.ck(ck),.rsi_w(rcore),.rsi_r(rhr),.i(eu_raw),.o(eu));
 wire actual_init=dut.init_u0_q&&dut.d_start&&dut.d_stage==0&&dut.s_user==0;
 wire pub=(MUT==9&&cyc==1600)||actual_init||(dut.ctx_ld&&dut.ctx_mask!=0);
 wire[3:0]pubmask=(MUT==4)?4'd0:(MUT==9&&cyc==1600)?4'd1:((actual_init?4'b0001:0)|{dut.ctx_mask,1'b0});
 reg fetch=0,release_row=0;wire[15:0]fe,re,ce;wire ef;
 qfd_mu_embedding_cold_epoch_model #(.ENABLE(1),.NU(4),.COLD_PENDING(1)) ledger(.ck(ck),.rst_n(rst_n),.epoch_abort(1'b0),.new_epoch(1'b0),.accepted_v(mv),.accepted_user(mu),.accepted_epoch(me),.accepted_cold_role(mu==0),.accepted_token(mt),.accepted_generation(mg),.publish_slot(pub),.publish_mask(pubmask),.init_publication(actual_init),.init_token(dut.s_tok),.init_generation(MUT==8?2'd3:2'd2),.fetch_slot(fetch),.fetch_pending(1'b1),.fetch_user(2'd0),.fetch_token(ETOK),.fetch_generation(2'd2),.consume_slot(es),.consume_user(eu),.consume_token(et),.release_slot(release_row),.retire_slot(1'b0),.retire_mask(4'd0),.fetch_epoch(fe),.expected_epoch(re),.core_epoch(ce),.fault(ef));

 wire context_v=0;wire[5:0]stage=0;wire[17:0]token=et,position=5;
 wire[547:0]dd=0,rxdata=0;wire kvslot=0,xslot=0,qslot=0,txslot=0,rxv=0,rxslot=0,visibility_slot=0,complete_slot=0;
 wire[1:0]kvindex=0;wire[4:0]qb=0,tb=0,rb=0;wire[3:0]tk=0,rk=0;
 wire[379:0]cmd=es?{4'hE,(et+((MUT==7)?18'd1:18'd0)),357'd0,1'b0}:380'd0;
 wire pw_v=(cyc>=1402&&cyc<1467)&&!(MUT==6&&cyc==1466);
 wire pw_scale=cyc==1402;wire[5:0]pw_idx=pw_scale?0:6'(cyc-1403);
 wire[511:0]pw_data=pw_scale?{496'd0,ESCALE}:row[pw_idx];
 wire[519:0]dr;wire n_tv,n_done,n_fault;wire[58:0]n_xid;wire[1:0]n_xg;wire[523:0]n_x3;wire[547:0]n_td;wire[94:0]n_ret;
 wire e_cre,e_sre;wire[23:0]e_caddr;wire[17:0]e_saddr;wire[511:0]e_cq;wire[15:0]e_sq;wire p_fault;
 qfd_native59_dv_service #(.MUT(0),.NU(4),.MCTX(1),.SAFE(2))native_engine(
 .ck(clk),.ck_fmt(clk),.ck_qbuf(clk),.rst_n(rst_n),
 .host_epoch_valid(hv),.host_fused_capability(1'b1),.host_epoch(he),.host_tag(ht),.host_generation(hg),
 .layer_context_v(context_v),.command_stage(stage),.native_token(token),.native_position(position),.native_cmd(cmd),
 .dd_i(dd),.kv_word_slot(kvslot),.kv_word_index(kvindex),.kv_x3_slot(xslot),
 .x3(n_x3),.x3_identity(n_xid),.x3_generation(n_xg),
 .q_slot(qslot),.q_slot_beat(qb),.tx_slot(txslot),.tx_slot_kind(tk),.tx_slot_beat(tb),.native_tx_v(n_tv),.native_tx_payload(n_td),
 .native_rx_v(rxv),.native_rx_payload(rxdata),.rx_slot(rxslot),.rx_slot_kind(rk),.rx_slot_beat(rb),.dr_o(dr),
 .emb_code_re(e_cre),.emb_code_addr(e_caddr),.emb_scale_re(e_sre),.emb_scale_addr(e_saddr),.emb_code_q(e_cq),.emb_scale_q(e_sq),
 .visibility_slot(visibility_slot),.complete_slot(complete_slot),.completed(n_done),.native_ret(n_ret),.fault(n_fault));

 reg[15:0]face_epoch=0;
 always @(posedge ck)if(!rst_n)face_epoch<=0;else if(es&&MUT!=5)face_epoch<=ce;
 wire validation_start,arm_fault;wire[17:0]validation_token;wire[15:0]validation_epoch;
 qfd_embedding_validation_arm #(.ENABLE(1)) arm(.ck(ck),.rst_n(rst_n),.core_start(es),.core_user(eu),.core_token(et),.registered_epoch(face_epoch),.native_read(e_cre||e_sre),.release_slot(release_row),.validation_start(validation_start),.validation_token(validation_token),.validation_epoch(validation_epoch),.fault(arm_fault));
 qfd_embedding_word_provider prov(.ck(ck),.rst_n(rst_n),.word_v(pw_v),.word_data(pw_data),.word_token(ETOK),.word_index(pw_idx),.word_scale(pw_scale),.word_epoch(re),.expected_word_slot(cyc>=1402&&cyc<1467),.expected_token(ledger.resident_token),.expected_word(pw_idx),.expected_scale(pw_scale),.expected_epoch(re),.fill_begin(fetch),.fill_token(mt),.fill_epoch(fe),.core_start(validation_start),.core_token(validation_token),.core_epoch(validation_epoch),.embed_code_re(e_cre),.embed_code_addr(e_caddr),.embed_code_q(e_cq),.embed_scale_re(e_sre),.embed_scale_addr(e_saddr),.embed_scale_q(e_sq),.fault(p_fault));
 function automatic[547:0]rec(input integer user,input integer tok,input integer gen);
 reg[547:0]v;reg[58:0]tag;begin tag={14'h123,2'(user),6'd0,18'(tok),13'd7,6'd0};if(user==0&&tok==ETOK)tag[18:6]=13'd5;v=0;v[542:539]=12;v[538:533]=63;v[532:517]=tag[58:43];v[141:78]=64'h123456789abcdef0;v[77:62]=16'hbeef;v[61]=1;v[60:59]=2'(gen);v[58:0]=tag;return v;end endfunction
 integer cyc,checks=0,ctx_edges=0,init_edges=0,raw_edges=0,out_edges=0,consume_edges=0;
 reg[63:0]pw[0:1023],dw[0:7];string packet;
 task check(input bit good,input string why);begin checks++;if(!good)$fatal(1,"LP_NATIVE_FAIL MUT%0d cycle%0d %s",MUT,cyc,why);end endtask
 initial begin
 if(!$value$plusargs("PACKET=%s",packet)||!$value$plusargs("VECTORS=%s",vectors))$fatal(1,"PACKET/VECTORS required");
 begin integer ignored;reg[15:0]sc[0:0];ignored=$value$plusargs("TOKEN=%d",ETOK);$readmemh({vectors,"/codes.hex"},row);$readmemh({vectors,"/scale.hex"},sc);ESCALE=sc[0];end
 $readmemh({packet,"/pw.hex"},pw);$readmemh({packet,"/dw.hex"},dw);
 repeat(3)@(negedge ck);rst_n=1;repeat(20)@(negedge ck); // component reset initialization, not runtime gating
 for(cyc=0;cyc<1900;cyc++)begin
 @(negedge ck);dh=0;offer=0;record=0;role=0;init_u0=0;fetch=0;release_row=0;
 if(cyc>=2&&cyc<1026)begin dh[118]=1;dh[117:108]=10'(cyc-2);dh[107:44]=pw[cyc-2];end
 if(cyc>=1026&&cyc<1034)begin dh[186]=1;dh[185:183]=3'(cyc-1026);dh[182:119]=dw[cyc-1026];end
 if(cyc==1200)begin offer=1;record=rec(1,1001,2);role=1;role_user=1;end
 if(cyc==1201||cyc==1301)begin offer=1;record=rec(0,888,1);end
 if(cyc==1300)begin offer=1;record=rec(0,ETOK,2);role=1;role_user=0;end
 if(cyc==1400)fetch=1;
 if(cyc==1740)begin offer=1;record=rec(0,(ETOK==151935)?0:ETOK+1,3);record[58:43]=16'h490;record[532:517]=16'h490;role=1;role_user=0;end
 if(cyc==1666)begin dh[43:0]=(44'd1<<42)|(44'(ETOK)<<18)|5;init_u0=1;end
 if(cyc==1850)release_row=1; // diagnostic hold only; actual native last-read join is separate
 @(posedge ck);
 if(dut.ctx_ld&&dut.ctx_mask!=0)begin ctx_edges++;check(cyc==1206,"offer-to-actualbank sample must be6");$display("LP_CTX offer1200 bank_sample%0d age%0d",cyc,cyc-1200);end
 if(actual_init)begin init_edges++;check(cyc==1670,"external INIT sample-to-actual bank sample must be4");$display("LP_INIT input_sample1666 bank_sample%0d age%0d",cyc,cyc-1666);end
 if(es)begin consume_edges++;check(cyc==1736&&et==ETOK&&eu==0,"external emb command sample must be70 with aligned token/user");check(re==16'h48c&&ce==16'h48c,"selected cold pending promoted before actual command sample");$display("LP_COMMAND sample%0d input_to_command%0d epoch%h token%0d user%0d",cyc,cyc-1666,ce,et,eu);end
 if(validation_start)begin validations++;check(cyc==1737&&validation_token==ETOK&&validation_epoch==16'h48c,"actual provider validation at command+1");$display("LP_NATIVE_VALIDATION sample%0d",cyc);end
 if(e_cre)begin check(e_caddr=={ETOK,6'(reads)}&&cyc==1739+reads,"native code read age/address unchanged");if(reads==0)$display("LP_NATIVE_FIRST_CODE sample%0d",cyc);reads++;end
 if(e_sre)begin scale_reads++;check(cyc==1803,"actual scale read at command+67");$display("LP_NATIVE_SCALE_READ sample%0d",cyc);end
 if(dr[519]&&dr[518])begin
  check(cyc==1742+outputs,"native external output age unchanged");
  if(outputs<64)check(dr[511:0]===row[outputs]&&dr[517:512]==6'(outputs),"native code payload/index");else check(dr[511:0]==={496'd0,ESCALE},"native scale payload");
  if(outputs==64)$display("LP_NATIVE_LAST_OUTPUT sample%0d",cyc);outputs++;
 end
 check(!p_fault&&!arm_fault&&!n_fault,"actual provider/arm/native fault-free");
 #0.1;
 if(es_raw)begin raw_edges++;check(cyc==1732&&et_raw==ETOK&&eu_raw==0,"raw GI EMB publication age66");$display("LP_GI_EMB publication%0d age%0d",cyc,cyc-1666);end
 if(es)begin out_edges++;check(cyc==1735&&et==ETOK&&eu==0,"output LP EMB publication age69");$display("LP_EXTERNAL_EMB publication%0d age%0d",cyc,cyc-1666);end
 check(!rxf&&!obf&&!ef&&dcs[2:1]==0,$sformatf("receiver/observer/ledger/GI flags %0d/%0d/%0d/%0d",rxf,obf,ef,dcs[2:1]));
 end
 check(reads==64&&scale_reads==1&&outputs==65&&validations==1,"actual native/provider fullrow coverage");
 check(ctx_edges==1&&init_edges==1&&raw_edges==1&&out_edges==1&&consume_edges==1,"all actual boundary observations covered");
 $display("LP_NATIVE_PASS checks%0d CTX6 INITbank4 rawEMB66 outEMB69 command70 validate71 firstcode73 scale137 lastoutput140 functionalclocks_tied productionphase_unbound",checks);$finish;
 end
endmodule
