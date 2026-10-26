`timescale 1ns/1ps
module pma_pair #(parameter WI=544,NI=16,WO=512,NO=17,REV=0,DMUT=0)(output reg complete=0);
 reg wclk=0,rclk=0,rst_n=0;
 generate if(!REV)begin always #8.5 wclk=~wclk;always #8 rclk=~rclk;end
 else begin always #8 wclk=~wclk;always #8.5 rclk=~rclk;end endgenerate
 wire[3:0]bank_clks={4{wclk}};
 reg w_start=0,r_start=0,observed_v=1;
 reg[WI-1:0]d=0;wire[WO-1:0]oq,nq;wire ov,nv,owf,nwf,orf,nrf;
 integer epoch=0,mode=0,wt=0,rt=0,sent=0,received=0,i,b,checks=0,words=0,resets=0;
 reg[WO-1:0]gold;reg active_read;
 ot_hbm_pma_block_gearbox #(.WI(WI),.NI(NI),.WO(WO),.NO(NO)) old_u(
 .wclk(wclk),.rclk(rclk),.rst_n(rst_n),.w_start(w_start),.r_start(r_start),.d(d),.observed_v(observed_v),.q(oq),.q_v(ov),.w_fault(owf),.r_fault(orf),.wclk_bank(bank_clks));
 ot_hbm_pma_block_gearbox_static_words #(.WI(WI),.NI(NI),.WO(WO),.NO(NO),.MUT(DMUT)) new_u(
 .wclk(wclk),.rclk(rclk),.rst_n(rst_n),.w_start(w_start),.r_start(r_start),.d(d),.observed_v(observed_v),.q(nq),.q_v(nv),.w_fault(nwf),.r_fault(nrf),.wclk_bank(bank_clks));
 function automatic pattern_bit(input integer e,input integer blockno,input integer bitno);
 reg[31:0]h;
 begin h=32'h9e3779b9*(bitno+1) ^ 32'h85ebca6b*(blockno+1) ^ 32'hc2b2ae35*(e+1);h=h^(h>>16);h=h*32'h27d4eb2d;h=h^(h>>15);pattern_bit=h[bitno%32];end
 endfunction
 always @(negedge wclk)begin
  if(!rst_n)begin w_start=0;observed_v=1;d=0;end
  else begin
   w_start=(wt==5)||(mode==1 && wt==80);
   observed_v=!(mode==1 && wt==30);
   for(i=0;i<WI;i=i+1)d[i]=pattern_bit(epoch,sent/NI,(sent%NI)*WI+i);
  end
 end
 always @(negedge rclk)begin
  if(!rst_n)r_start=0;
  else r_start=(rt==((mode==3)?8:30))||(mode==1 && rt==90);
 end
 always @(posedge wclk or negedge rst_n)
 if(!rst_n)begin wt<=0;sent<=0;end
 else begin
  wt<=wt+1;
  if(w_start||old_u.wa)sent<=sent+1;
 end
 always @(posedge rclk or negedge rst_n)
 if(!rst_n)begin rt<=0;received<=0;end
 else begin
  rt<=rt+1;
  if(r_start||old_u.ra)received<=received+1;
 end
 // Pre-edge expected stream; stimulus changes only on the preceding negative edge.
 always @(posedge rclk)begin
  active_read=rst_n&&(r_start||old_u.ra);
  for(integer j=0;j<WO;j=j+1)gold[j]=pattern_bit(epoch,received/NO,(received%NO)*WO+j);
  #0.001;
  if({nv,nrf,nq} !== {ov,orf,oq})$fatal(1,"OLD_NEW_READ rev=%0d mode=%0d received=%0d",REV,mode,received);
  if(rst_n && active_read && mode!=3)begin
   if(nq !== gold)$fatal(1,"GOLD_FULLWORD rev=%0d mode=%0d received=%0d got=%h expected=%h",REV,mode,received,nq,gold);
   words=words+1;
  end
  if({new_u.ra,new_u.rb,new_u.ri,new_u.consumed,new_u.done_s1,new_u.done_s2} !== {old_u.ra,old_u.rb,old_u.ri,old_u.consumed,old_u.done_s1,old_u.done_s2})$fatal(1,"READ_STATE rev=%0d",REV);
  checks=checks+1;
 end
 always @(posedge wclk)begin
  #0.001;
  if(nwf !== owf)$fatal(1,"WRITE_FAULT rev=%0d",REV);
  if({new_u.wa,new_u.wb,new_u.wi,new_u.done,new_u.cons_s1,new_u.cons_s2} !== {old_u.wa,old_u.wb,old_u.wi,old_u.done,old_u.cons_s1,old_u.cons_s2})$fatal(1,"WRITE_STATE rev=%0d",REV);
  for(integer k=0;k<4;k=k+1)if(new_u.bank[k] !== old_u.bank[k])$fatal(1,"WHOLE_BANK_STATE rev=%0d bank=%0d sent=%0d",REV,k,sent);
  checks=checks+1;
 end
 task automatic restart(input integer next_mode);
 begin
  @(negedge wclk);rst_n=0;mode=next_mode;epoch=epoch+1;resets=resets+1;
  repeat(4)@(negedge wclk);
  #0.002;rst_n=1;
 end endtask
 initial begin
  // Both directions wrap all four real banks repeatedly.
  restart(0);wait(wt==420);@(negedge wclk);
  if(nwf||nrf)$fatal(1,"NORMAL_FAULT rev=%0d",REV);
  restart(1);wait(wt==420);@(negedge wclk);
  if(!nwf||!nrf)$fatal(1,"DROP_RESTART_NOT_DETECTED rev=%0d",REV);
  restart(2);wait(wt==31);restart(0);wait(wt==420);@(negedge wclk);
  if(nwf||nrf)$fatal(1,"RESET_RECOVERY_FAULT rev=%0d",REV);
  restart(3);wait(wt==420);@(negedge wclk);
  if(!nrf)$fatal(1,"EARLY_ALIGNMENT_NOT_DETECTED rev=%0d",REV);
  $display("PAIR_PASS rev=%0d checks=%0d golden_fullwords=%0d resets=%0d",REV,checks,words,resets);complete=1;
 end
endmodule
module tb_pma_static_words;
 parameter DMUT=0;
 wire a,b;
 pma_pair #(.DMUT(DMUT)) ser(a);
 pma_pair #(.WI(512),.NI(17),.WO(544),.NO(16),.REV(1),.DMUT(DMUT)) deser(b);
 initial begin wait(a&&b);$display("PMA_STATIC_WORDS_PASS both16x544_to17x512_and_reverse");$finish;end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
