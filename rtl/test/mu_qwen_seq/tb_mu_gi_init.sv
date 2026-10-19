`timescale 1ns/1ps
// Real GI/calendar/three-bank expanded leaf and actual F16 PW/DW. Root arithmetic
// is deliberately scripted from observed AMemit: this proves the bank/status
// contract, not arithmetic, full-token correctness, or an absolute D2D epoch.
module tb_mu_gi_init;
 parameter integer BAD_COUNT=0;
 reg ck=0,rst_n=0; always #0.5 ck=~ck;
 reg [186:0] dh=0; reg init_u0=0; wire [128:0] ctx_x; reg offer_v=0; reg[547:0] record=0;
 wire accept_v,host_valid,rx_fault,observer_fault;wire[15:0] he;wire[58:0] ht;wire[1:0] hg;
 qfd_host_native_context_rx receiver(.ck(ck),.rst_n(rst_n),.receive_slot(offer_v),.rx_v(offer_v),.rx_record(record),
 .program_begin_v(1'b0),.program_ready(1'b1),.installed_fusedcap(1'b1),.program_epoch(16'hbeef),.program_digest(64'h123456789abcdef0),
 .head_context_v(1'b0),.head_stage(6'd0),.head_token(18'd0),.head_position(18'd0),.native_active(1'b0),
 .accepted_v(accept_v),.host_epoch_valid(host_valid),.host_epoch(he),.host_tag(ht),.host_gen(hg),.host_fusedcap(),.host_image_epoch(),.host_image_digest(),.fault(rx_fault));
 qfd_sys_face_accepted_mu_ctx observer(.ck(ck),.rst_n(rst_n),.offer_slot(offer_v),.offer_v(offer_v),.offer_record(record),
 .host_accept_v(accept_v),.host_epoch_valid(host_valid),.host_epoch(he),.host_tag(ht),.host_gen(hg),
 .program_ready(1'b1),.program_cap(1'b1),.program_fault(rx_fault),.program_epoch(16'hbeef),.program_digest(64'h123456789abcdef0),.ctx_x(ctx_x),.fault(observer_fault));
 reg [106:0] ss5=0;
 wire [115:0] cmd; wire [61:0] dcs; wire emb_start,s_start; wire [17:0] emb_token; wire [5:0] s_stage; wire [48:0] st;
 qfd_tt_ctlm_dv_gi #(.NU(4),.STAGE_ME(1),.OPSEG(1),.OPSEG_EXPANDED(1),.OPSEG_PINREG(1),.CTX_SRC(1),.FCTX(1),
 .INIT_U0(1),.INIT_FIRST(BAD_COUNT?0:52),.INIT_CNT(BAD_COUNT?1024:3)) dut
 (.ck(ck),.rst_n(rst_n),.dh(dh),.dh_user(2'd0),.init_u0(init_u0),.ctx_x(ctx_x),.mu_fault(rx_fault|observer_fault),.ss5(ss5),.ag5(10'd0),.fab(1'b0),
 .cmd(cmd),.dcs(dcs),.emb_start(emb_start),.emb_token(emb_token),.s_start(s_start),.s_stage(s_stage),.st(st),
 .tl(),.cal_program_obs(),.cal_descriptor_obs(),.cal_image_ready(),.fctx(),.hu(),.su_obs_o(),.su_acc_o(),.x_oprog(),.x_orows(),.x_oidle(),.rom_ret_v());
 reg [63:0] pw[0:1023],dw[0:7];
 integer et[0:4095],ek[0:4095]; reg[128:0] ev[0:4095];
 integer rt[0:255],ru[0:255],rv[0:255]; integer qh=0,qt=0;
 integer tok[0:3],fresh[0:3],loads[0:3],firstemb[0:3],emits[0:3],results[0:3],embs[0:3];
 integer cyc,i,j,n=0,fd,r,idx=0,nend,mut=0,prefixheads=0,u,expected,seenemb=0,headstarts=0,me=0;
 integer offer_at[0:3],measured_loads=0;reg[58:0] tag;
 reg checkemb; string packet,events,limits;
 task fail(input string why); $display("TB_MU_GI_INIT FAIL mut=%0d cyc=%0d %s cal=%0d/%0d op=%0d",mut,cyc,why,dut.c_fault,dut.c_fcode,dut.op_fault); $finish; endtask
 initial begin
 if(!$value$plusargs("PACKET=%s",packet)||!$value$plusargs("EVENTS=%s",events)||!$value$plusargs("LIMITS=%s",limits)) $fatal(1,"paths required");
 r=$value$plusargs("MUT=%d",mut);
 $readmemh({packet,"/pw.hex"},pw);$readmemh({packet,"/dw.hex"},dw);
 // Mutation restores the forbidden AMemit into the actual appended INIT entry.
 if(mut==2) begin pw[64+2*52]=pw[64+2*40];pw[65+2*52]=pw[65+2*40];end
 fd=$fopen(events,"r");while(!$feof(fd)) begin r=$fscanf(fd,"%d %d %h\n",et[n],ek[n],ev[n]);if(r==3)n++;end $fclose(fd);
 fd=$fopen(limits,"r");r=$fscanf(fd,"%d",nend);$fclose(fd);
 for(i=0;i<4;i++)begin tok[i]=0;fresh[i]=0;loads[i]=0;firstemb[i]=0;emits[i]=0;results[i]=0;embs[i]=0;end
 repeat(3)@(negedge ck);rst_n=1;
 for(cyc=0;cyc<nend;cyc++)begin
 @(negedge ck);dh=0;offer_v=0;record=0;ss5=0;init_u0=0;
 if(cyc>=2&&cyc<1026)begin dh[118]=1;dh[117:108]=10'(cyc-2);dh[107:44]=pw[cyc-2];end
 if(cyc>=1026&&cyc<1034)begin dh[186]=1;dh[185:183]=3'(cyc-1026);dh[182:119]=dw[cyc-1026];end
 if(idx<n&&et[idx]==cyc)begin
  if(ek[idx]==2||ek[idx]==3)begin
  u=0;tag=0;
  if(ek[idx]==2)for(j=1;j<4;j++)if(ev[idx][108+j-1])begin u=j;tag[36:19]=ev[idx][36*(j-1)+18+:18];tag[18:6]=13'(ev[idx][36*(j-1)+:18]);end
  tag[58:43]={14'h123,2'(u)}; record[542:539]=12;record[538:533]=63;record[532:517]=tag[58:43];
  record[141:78]=64'h123456789abcdef0;record[77:62]=16'hbeef;record[61]=1;record[60:59]=2;record[58:0]=tag;offer_v=1;offer_at[u]=cyc;
 end else begin dh[43:0]=ev[idx][43:0];init_u0=(ek[idx]==0);if(mut==1&&cyc==2000)init_u0=1;end
  idx++;
 end
 if(qh<qt&&rt[qh%256]==cyc)begin ss5[24]=1;ss5[27:26]=2'(ru[qh%256]);ss5[17:0]=18'(rv[qh%256]);qh++;end
 // Invalid write while first context is pending must fault, without stalls.
 if(mut==3&&cyc==253430)begin ss5[24]=1;ss5[27:26]=1;ss5[17:0]=888;end
 @(posedge ck);
 // These are the GI's actual synchronous acceptance/consumption edges.
 if(dut.ctx_ld)for(j=1;j<4;j++)if(dut.ctx_mask[j-1])begin if(cyc-offer_at[j]!=3)fail($sformatf("bank load age=%0d expected3",cyc-offer_at[j]));
 measured_loads++;$display("GI_CONTEXT_EDGE user=%0d offer=%0d bankload=%0d age=%0d",j,offer_at[j],cyc,cyc-offer_at[j]);tok[j]=dut.c_ctx[36*(j-1)+18+:18];fresh[j]=1;loads[j]++;end
 if(dut.d_start)begin tok[0]=dut.s_tok;if(dut.u0_init_start)begin
  if(dut.u_cal.start_first!=52||dut.u_cal.start_cnt!=3||!dut.u_cal.start_rng)fail("wrong explicit INIT range");
  prefixheads++;$display("GI_INIT_EDGE dh_pin=1666 cal_accept=%0d stage0_head=%0d",cyc,s_start);if(dut.s_me)fail("INIT launched ME");end end
 if(s_start)headstarts++;
 if(dut.r_fill)begin tok[dut.r_wr]=dut.ss_tok[17:0];results[dut.r_wr]++;end
 if(dcs[60])begin if(dcs[59:42]!=777+emits[0])fail("user0 result lost");results[0]++;end
 checkemb=dut.c_emb;u=dut.c_user;expected=tok[u];
 if(dut.c_emb)begin if(u==0&&cyc<2000)$display("GI_INIT_EDGE local_emb_consume=%0d token=%0d",cyc,expected);embs[u]++;if(fresh[u])begin fresh[u]=0;firstemb[u]++;end end
 else if(dut.c_seg)fresh[u]=0;
 #0.1;
 if(dcs[2:1]!=0)fail("sticky controller/calendar fault");
 if(checkemb&&u==0&&cyc<2000)$display("GI_INIT_EDGE emb_start_pin=%0d token=%0d",cyc,emb_token);
 if(checkemb&&(!emb_start||emb_token!=expected))fail($sformatf("EMB u%0d got%0d expected%0d",u,emb_token,expected));
 if(cmd[0]&&cmd[3:1]==6&&cmd[5])begin
  u=cmd[9:8];if(cyc<2000)fail("cold INIT emitted argmax");
  if(fresh[u])fail("INIT emitted before consuming context");
  emits[u]++;rt[qt%256]=cyc+52;ru[qt%256]=u;rv[qt%256]=777+emits[u]+10000*u;qt++;
  if(qt-qh>=256)fail("result queue overflow");
 end
 end
 for(j=1;j<4;j++)if(loads[j]!=2||firstemb[j]!=2||emits[j]<2||results[j]<2)fail($sformatf("coverage u%0d loads%0d firstemb%0d emits%0d results%0d",j,loads[j],firstemb[j],emits[j],results[j]));
 if(prefixheads!=1||results[0]<2)fail("cold-prefix/user0 result coverage");
 $display("TB_MU_GI_INIT PASS edges=%0d prefix=%0d headstarts=%0d ctxloads=%0d/%0d/%0d firstemb=%0d/%0d/%0d emits=%0d/%0d/%0d/%0d results=%0d/%0d/%0d/%0d accepted_receiver_bank_age=3 arithmetic=scripted absolute_epoch=unbound",cyc,prefixheads,headstarts,loads[1],loads[2],loads[3],firstemb[1],firstemb[2],firstemb[3],emits[0],emits[1],emits[2],emits[3],results[0],results[1],results[2],results[3]);$finish;
 end
endmodule
