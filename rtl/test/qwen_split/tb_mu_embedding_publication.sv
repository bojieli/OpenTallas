`timescale 1ns/1ps
// Minimum real native59 embedding reader + production word provider. No row readiness wait.
module tb_mu_embedding_publication;
 reg clk=0; always #0.416667 clk=~clk;
 integer cyc=0,mut=0,count=0,reads=0; always @(posedge clk)cyc<=cyc+1;
 wire rst_n=cyc>=4;
 reg [17:0] ETOK=123457; wire [15:0] EEP=16'(round);
 reg [15:0] ESCALE=16'h3e80;
 reg [511:0] row[0:63]; string vectors;
 initial begin
  void'($value$plusargs("MUT=%d",mut)); void'($value$plusargs("TOKEN=%d",ETOK));
  if(!$value$plusargs("VECTORS=%s",vectors))$fatal(1,"VECTORS required");
  $readmemh({vectors,"/codes.hex"},row);
  begin reg[15:0] sc[0:0]; $readmemh({vectors,"/scale.hex"},sc); ESCALE=sc[0]; end
 end
 wire context_v=0; wire[5:0]stage=0; wire[17:0]token=ETOK,position=0;
 wire[547:0]dd=0,rxdata=0;wire kvslot=0,xslot=0,qslot=0,txslot=0,rxv=0,rxslot=0,visibility_slot=0,complete_slot=0;
 wire[1:0]kvindex=0;wire[4:0]qb=0,tb=0,rb=0;wire[3:0]tk=0,rk=0;
 reg[379:0]cmd; reg pw_v,pw_scale,fill_begin,core_start;reg[5:0]pw_idx;reg[511:0]pw_data;
 integer round=0;
 wire [1:0] user_id=2'(round%4);
 wire [31:0] base=32'(round*200);
 wire [31:0] FILL=base+20,CORE=base+90,EMB=base+92;
 wire av=(cyc==base+10)||(cyc==base+91&&user_id==0);
 wire [17:0] atok=(cyc==base+91)?((ETOK==151935)?18'd0:ETOK+18'd1):ETOK;
 wire fetch_slot=(cyc==FILL&&mut!=9&&mut!=11)||(mut==10&&cyc==CORE+10)||(mut==11&&cyc==CORE);
 wire ep_fault;wire [15:0] ep_fetch,ep_expected,ep_core;
 wire ep_accept=(round<4&&cyc==base+10)||(cyc==base+15);
 wire ep_publish=(round<4&&cyc==base+12)||(round<7&&cyc==base+175)||(mut==15&&cyc==base+40);
 qfd_mu_embedding_epoch_publication #(.ENABLE(1)) epoch_ledger(.ck(clk),.rst_n(rst_n),
 .accepted_v(ep_accept),.accepted_user(user_id),.accepted_epoch(EEP+((cyc==base+15)?16'd4:16'd0)),
 .publish_slot(ep_publish),.publish_mask(4'b1<<user_id),.fetch_slot(fetch_slot),.fetch_user(user_id),
 .consume_slot(core_start),.consume_user(user_id),.release_slot(cyc==base+170),
 .retire_slot((round==7&&cyc==base+171)||(mut==16&&cyc==base+40)),.retire_mask(4'b1<<user_id),
 .fetch_epoch(ep_fetch),.expected_epoch(ep_expected),.core_epoch(ep_core),.fault(ep_fault));
 wire ledger_fill;wire [17:0] ledger_token,expected_token;wire [15:0] ledger_epoch,expected_epoch;wire ledger_fault;
 qfd_mu_embedding_ledger #(.ENABLE(1)) ledger(.ck(clk),.rst_n(rst_n),
 .accept_v(av),.accept_user(user_id),.accept_token(atok),.accept_epoch(EEP),
 .fetch_slot(fetch_slot),.fetch_user(user_id),.consume_slot(core_start),
 .consume_user(user_id+((mut==12)?2'd1:2'd0)),.consume_token(ETOK),
 .consume_epoch(EEP-((mut==13&&round==4)?16'd4:16'd0)),.release_slot(cyc==base+170),
 .fill_begin(ledger_fill),.fill_token(ledger_token),.fill_epoch(ledger_epoch),
 .expected_token(expected_token),.expected_epoch(expected_epoch),.fault(ledger_fault));
 always @*begin
  cmd=0;pw_v=0;pw_scale=0;fill_begin=ledger_fill;core_start=(cyc==CORE);pw_idx=0;pw_data=0;
  if(cyc==FILL+2)begin pw_v=1;pw_scale=1;pw_data={496'd0,ESCALE};end
  if(cyc>=FILL+3&&cyc<FILL+67)begin pw_v=1;pw_idx=6'(cyc-FILL-3);pw_data=row[pw_idx];end
  if(mut==4&&cyc==FILL+66)pw_v=0;
  if(mut==5)core_start=(cyc==FILL+66);
  if(cyc==EMB)cmd={4'hE,(ETOK+((mut==7)?18'd1:18'd0)),357'd0,1'b0};
 end
 wire[519:0]dr;wire n_tv,n_done,n_fault;wire[58:0]n_xid;wire[1:0]n_xg;wire[523:0]n_x3;wire[547:0]n_td;wire[94:0]n_ret;
 wire e_cre,e_sre;wire[23:0]e_caddr;wire[17:0]e_saddr;wire[511:0]e_cq;wire[15:0]e_sq;wire p_fault;
 qfd_native59_dv_service #(.MUT(0))dut(
 .ck(clk),.rst_n(rst_n),
 .host_epoch_valid(1'b1),.host_fused_capability(1'b1),.host_epoch(16'd9),.host_tag({16'd9,6'd0,18'd50994,13'd255,6'd0}),.host_generation(2'd1),
 .layer_context_v(context_v),.command_stage(stage),.native_token(token),.native_position(position),.native_cmd(cmd),
 .dd_i(dd),.kv_word_slot(kvslot),.kv_word_index(kvindex),.kv_x3_slot(xslot),
 .x3(n_x3),.x3_identity(n_xid),.x3_generation(n_xg),
 .q_slot(qslot),.q_slot_beat(qb),.tx_slot(txslot),.tx_slot_kind(tk),.tx_slot_beat(tb),.native_tx_v(n_tv),.native_tx_payload(n_td),
 .native_rx_v(rxv),.native_rx_payload(rxdata),.rx_slot(rxslot),.rx_slot_kind(rk),.rx_slot_beat(rb),.dr_o(dr),
 .emb_code_re(e_cre),.emb_code_addr(e_caddr),.emb_scale_re(e_sre),.emb_scale_addr(e_saddr),.emb_code_q(e_cq),.emb_scale_q(e_sq),
 .visibility_slot(visibility_slot),.complete_slot(complete_slot),.completed(n_done),.native_ret(n_ret),.fault(n_fault));
 qfd_embedding_word_provider prov(.ck(clk),.rst_n(rst_n),.word_v(pw_v),.word_data(pw_data),.word_token(ETOK+((mut==1)?18'd1:18'd0)),.word_index(pw_idx),
 .word_scale(pw_scale),.word_epoch(EEP+((mut==2)?16'd1:16'd0)),.expected_word_slot(cyc>=FILL+2&&cyc<FILL+67),.expected_token(expected_token),.expected_word(pw_idx),.expected_scale(pw_scale),
 .expected_epoch(ep_expected),.fill_begin(fill_begin),.fill_token(ledger_token),.fill_epoch(ep_fetch),.core_start(core_start),.core_token(ETOK+((mut==3)?18'd1:18'd0)),.core_epoch(ep_core+((mut==6)?16'd1:(mut==8||mut==14)?16'd4:16'd0)),
 .embed_code_re(e_cre),.embed_code_addr(e_caddr),.embed_code_q(e_cq),.embed_scale_re(e_sre),.embed_scale_addr(e_saddr),.embed_scale_q(e_sq),
 .fault(p_fault));

 always @(posedge clk)if(rst_n)begin
  if(e_cre)begin
   if(e_caddr!={ETOK,6'(reads)})$fatal(1,"JOIN_FAIL read token/index cycle=%0d",cyc);
   if(reads==0)$display("FIRST_CODE_RE cycle=%0d token=%0d epoch=%0d resident=%0d/%0d complete=%0d",cyc,ETOK,EEP,prov.store.resident_token,prov.store.resident_epoch,prov.store.complete);
   reads=reads+1;
  end
  if(dr[519]&&dr[518])begin
   if(cyc!=EMB+6+count)$fatal(1,"JOIN_FAIL output age cycle=%0d count=%0d",cyc,count);
   if(count<64)begin if(dr[511:0]!==row[count]||dr[517:512]!=6'(count))$fatal(1,"JOIN_FAIL payload");end
   else if(dr[511:0]!=={496'd0,ESCALE})$fatal(1,"JOIN_FAIL scale");
   count=count+1;
  end
  if(cyc==base+180)begin
   if(p_fault||n_fault||ledger_fault||ep_fault)$fatal(1,"JOIN_FAIL identity/residency provider=%0d native=%0d ledger=%0d epoch_publication=%0d",p_fault,n_fault,ledger_fault,ep_fault);
   if(count!=65||reads!=64)$fatal(1,"JOIN_FAIL fullshape counts");
   $display("ROUND_PASS user=%0d token=%0d epoch=%0d reads=%0d output=%0d",user_id,ETOK,EEP,reads,count);
   if(round==7)begin $display("JOIN_PASS pending_vs_active recurring4 reload native59 provider token=%0d rounds=8",ETOK);$finish;end
   round=round+1;reads=0;count=0;
  end
 end
endmodule
