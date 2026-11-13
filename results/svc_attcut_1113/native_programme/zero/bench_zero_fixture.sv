`timescale 1ns/1ps
// Actual outer decoder/memories + actual native band/PAIR5 engine.
// Focused fixed-source programme/control/timing qualification, not whole-die G5.
module tb_svc_native_programme;
 reg clk=0;always #0.5 clk=~clk;reg rst_n=0,qv=0;reg[511:0]q=0;
 integer phase_case=0,mut=0,errors=0,cycle=0,origin=-1,gphase=-1;
 integer qc=0,kc=0,pc=0,lastq=-1,lastk=-1,lastp=-1,qerr=0,phaseerr=0;
 wire[31:0]fc;
 integer ns=0,np=0,firsts=-1,lasts=-1,firstv=-1,lastv=-1,drains=0,firstd=-1,lastd=-1,afseen=0,paccept=0;
 reg[1075:0]scores[0:7];reg[1063:0]pvsaved[0:7];
 wire af=u.u_eng.g_tr[0].g_xb.u_band.u_t.u_hc.u_expand.fault | u.u_eng.g_tr[1].g_xb.u_band.u_t.u_hc.u_expand.fault | u.u_eng.g_tr[2].g_xb.u_band.u_t.u_hc.u_expand.fault | u.u_eng.g_tr[3].g_xb.u_band.u_t.u_hc.u_expand.fault;
 dsdv_svc_att #(.H(8)) u(.clk(clk),.rst_n(rst_n),.sid(4'd3),.tile(4'd0),.gd(8'd0),.pvs(8'd0),.root(1'b0),
  .q_v(qv),.q_d(q),.hw_v(1'b0),.hw_d(291'd0),.qrq(),.qrk(2'd0),.qwd(2'd0),.qrv(2'd0),.qr_data(512'd0),.qr_tag(34'd0),.qr_beat(8'd0),
  .l_v(),.l_d(),.pv_ov(),.pv_od(),.sm_st(),.sm_kind(),.sm_jid(),.sm_rv(),.sm_rp(),.sm_rj(),.sm_rd(),
  .go_o(),.tjob_o(),.done(),.tagj(),.hcr(),.hack(),.fault(),.fault_code(fc),.pio_o(),.pvo_o(),.jc_o(),.st_o(),.hb_o());
 always @(posedge clk)if(rst_n)begin
  cycle++;
  if(af)afseen++;
  if(u.u_eng.p_go)begin paccept++;$display("P_ACCEPT case%0d relative%0d",phase_case,cycle-origin);end
  if(u.ekv_v&&u.kv_ready)$display("KV_ACCEPT case%0d relative%0d",phase_case,cycle-origin);
  if(u.sc_v)begin
   if(ns==0)firsts=cycle-origin;lasts=cycle-origin;
   if(phase_case==0)scores[ns]={u.sc_row,u.sc_m,u.sc_y,u.sc_f};
   else if(scores[ns]!=={u.sc_row,u.sc_m,u.sc_y,u.sc_f})qerr++;
   $display("SCORE case%0d relative%0d row%0d payload%h flags%h",phase_case,cycle-origin,u.sc_row,u.sc_y,u.sc_f);ns++;
  end
  if(u.pv_v)begin
   if(np==0)firstv=cycle-origin;lastv=cycle-origin;
   if(phase_case==0)pvsaved[np]={u.pv_c,u.pv_y,u.pv_f};
   else if(pvsaved[np]!=={u.pv_c,u.pv_y,u.pv_f})qerr++;
   $display("PV_RAW case%0d relative%0d c%0d payload%h flags%h",phase_case,cycle-origin,u.pv_c,u.pv_y,u.pv_f);np++;
  end
  if(u.pv_ov)begin if(drains==0)firstd=cycle-origin;lastd=cycle-origin;drains++;end
  if(u.go)begin origin=cycle;gphase=!u.native_load_slot;end
  if(u.eq_v&&u.eq_ready)begin
   if(lastq>=0&&cycle-lastq!=2)phaseerr++;
   if(!u.native_load_slot)phaseerr++;
   if(cycle-origin!=2+gphase+2*qc)phaseerr++;
   for(integer w=0;w<32;w++)if(u.eq_w[16*w+:16]!==16'(4096+32*qc+w))qerr++;
   $display("Q case%0d idx%0d cycle%0d relative%0d slot%0b",phase_case,qc,cycle,cycle-origin,u.native_load_slot);
   qc++;lastq=cycle;
  end
  if(u.ekv_v)begin if(lastk>=0&&cycle-lastk!=1)phaseerr++;kc++;lastk=cycle;end
  if(u.ep_v)begin
   if(lastp>=0&&cycle-lastp!=2)phaseerr++;
   if(u.native_load_slot)phaseerr++;
   if(cycle-origin!=64+(1^gphase)+2*pc)phaseerr++;
   for(integer w=0;w<64;w++)if(u.ep_w[16*w+:16]!==16'(8192+64*pc+w))qerr++;
   $display("P case%0d idx%0d cycle%0d relative%0d slot%0b",phase_case,pc,cycle,cycle-origin,u.native_load_slot);
   pc++;lastp=cycle;
  end
 end
 task automatic word(input[511:0]w);@(negedge clk);qv=1;q=w;endtask
 task automatic gap;@(negedge clk);qv=0;q=0;repeat(4)@(negedge clk);endtask
 function automatic[511:0]hdr(input integer typ,input integer len);reg[511:0]h;h=0;h[511:508]=4'(typ);h[503]=1;h[491:480]=12'(len);return h;endfunction
 initial begin
  reg[511:0]h;integer nominal_bad;integer seen[0:1];
  void'($value$plusargs("mut=%d",mut));
  for(integer p=0;p<2;p++)begin
   phase_case=p;rst_n=0;qv=0;repeat(64)@(negedge clk);rst_n=1;
   ns=0;np=0;drains=0;afseen=0;paccept=0;firsts=-1;lasts=-1;firstv=-1;lastv=-1;firstd=-1;lastd=-1;qc=0;kc=0;pc=0;lastq=-1;lastp=-1;lastk=-1;qerr=0;phaseerr=0;origin=-1;
   h=hdr(12,0);h[32]=1;word(h);gap();
   h=hdr(2,0);h[98:89]=32;word(h);gap();
   h=hdr(7,2);h[19:10]=32;word(h);
   for(integer j=0;j<2;j++)begin h=0;for(integer r=0;r<16;r++)h[32*r+:32]=32'(80+r+256*j);word(h);end gap();
   repeat(36)@(negedge clk);
   word(hdr(6,32));for(integer r=0;r<32;r++)begin h=0;h[9:0]=10'(r);h[30:10]=21'(80+(r%16)+256*(r/16));h[34+:128]=128'h010101;h[290+:16]=16'h3c00;word(h);end gap();
   word(hdr(1,128));for(integer j=0;j<128;j++)begin h=0;for(integer w=0;w<32;w++)h[16*w+:16]=16'(4096+32*(j/16)+w);word(h);end gap();
   word(hdr(5,8));for(integer j=0;j<8;j++)begin h=0;for(integer w=0;w<32;w++)h[16*w+:16]=16'(8192+32*j+w);word(h);end gap();
   repeat(p)@(negedge clk);
   h=hdr(13,0);h[15:0]=64;h[31:16]=200;word(h);gap();repeat(260)@(negedge clk);
   seen[p]=gphase;
   nominal_bad=(qc!=8||kc!=8||pc!=4||qerr!=0||phaseerr!=0||fc!=0||afseen!=0||ns!=8||np!=8||paccept!=4||drains!=40||!u.done);
   $display("NATIVE_PROGRAMME case%0d go_phase%0d Q%0d KV%0d Ppush%0d Paccept%0d scores%0d rawPV%0d drainedWords%0d payloadErrors%0d phaseErrors%0d fc%08x afSeen%0d scoreDates%0d:%0d rawPVDates%0d:%0d drainDates%0d:%0d done%0d",p,gphase,qc,kc,pc,paccept,ns,np,drains,qerr,phaseerr,fc,afseen,firsts,lasts,firstv,lastv,firstd,lastd,u.done);
   if(mut==0)begin if(nominal_bad)errors++;end
   else if(qc==8||qerr==0||!fc[12])errors++;
  end
  if(seen[0]==seen[1])begin $display("GO phase coverage FAILED");errors++;end
  if(errors==0)$display("NATIVE_PROGRAMME PASS mut=%0d",mut);else $fatal(1,"NATIVE_PROGRAMME FAIL mut=%0d errors=%0d",mut,errors);
  $finish;
 end
endmodule
