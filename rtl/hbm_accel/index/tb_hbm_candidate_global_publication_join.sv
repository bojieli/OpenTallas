`timescale 1ps/1fs
module tb_hbm_candidate_global_publication_join #(parameter integer MUT_SLOT=0);
 reg clk=0;always #416.5 clk=~clk;
 reg por_n=0,ps=0,owner_valid=1,flit_v=0,empty_v=0,cs=0,out_r=0,retire=0,downstream_drained=0;
 reg[73:0]frame={1'b0,20'hfffff,17'h12345,4'h3,32'h99112233};
 reg[544:0]flit=0;reg[6:0]empty_rank=95;
 wire psr,fr,er,pub,csr,ov,retained,done,fault;
 wire[33:0]tuple;wire[73:0]oframe;wire[6:0]rank;
 ot_hbm_candidate_global_publication_join #(.ENABLE(1),.OWNER_W(74),.MUT_SLOT(MUT_SLOT)) dut(
 .clk(clk),.por_n(por_n),.publication_start(ps),.publication_frame(frame),.publication_start_r(psr),
 .owner_valid(owner_valid),.owner_frame(frame),.flit_v(flit_v),.flit_r(fr),.flit(flit),.flit_owner(frame),
 .expected_kind(1'b1),.expected_dst(8'd3),.empty_v(empty_v),.empty_r(er),.empty_rank(empty_rank),.empty_frame(frame),
 .publication_complete(pub),.consumer_start(cs),.consumer_start_r(csr),.out_v(ov),.out_r(out_r),.out_tuple(tuple),.out_frame(oframe),.out_rank(rank),
 .retire(retire),.downstream_drained(downstream_drained),.retained(retained),.done(done),.fault(fault));
 integer mode=0,cycles=0,writes=0,emitted=0,nextid=0,ce_responses=0;reg prior_stall=0;reg[33:0]prior_tuple;reg[73:0]prior_frame;reg[6:0]prior_rank;
 always @(negedge clk)begin if(cs||dut.consumer_retained)out_r<=cycles%7>=2;end
 always @(posedge clk)begin
 cycles<=cycles+1;
 if(dut.sv&&dut.sr&&dut.ce)ce_responses++;
 if(mode!=0&&mode!=2&&ov&&out_r)emitted++;
 if(cycles>200000)$fatal(1,"JOIN deadlock beyond finite96x60slot inventory");
 if(mode==0||mode==2)begin
 if(prior_stall&&(!ov||tuple!==prior_tuple||oframe!==prior_frame||rank!==prior_rank))$fatal(1,"JOIN_MISMATCH unstable output");
 prior_stall<=ov&&!out_r;prior_tuple<=tuple;prior_frame<=oframe;prior_rank<=rank;
 if(ov&&out_r)begin
 while(nextid%96==95||(nextid/96)%3==1)nextid++;
 if(tuple!=={17'(nextid),16'h3f80,1'b1}||rank!==7'(nextid%96)||oframe!==frame)$fatal(1,"JOIN_MISMATCH expected_id=%0d actual_id=%0d",nextid,tuple[33:17]);
 nextid++;emitted++;
 end
 end
 end
 task tick;begin @(negedge clk);end endtask
 task send(input integer r,q);
 begin
 while(!fr&&!fault)tick;
 flit=0;flit[544]=1;flit[543:536]=3;flit[535:528]=8'(r);flit[527:526]=2'(q);flit[511]=1;
 for(integer k=0;k<15;k++)begin
 flit[k*34+:34]={17'(r+96*(q*15+k)),16'h3f80,1'(q==0&&k%3!=1)};
 if(mode==1&&r==0&&q==0&&k==0)flit[k*34+17+:17]=17'd1;
 end
 flit_v=1;tick;flit_v=0;
 while(!fr&&!pub&&!fault)tick;
 if(fault)$fatal(1,"JOIN_MISMATCH premature fault during publication");
 writes++;
 end endtask
 initial begin
 if(!$value$plusargs("mode=%d",mode))mode=0;
 repeat(3)tick;por_n=1;tick;
 if(mode==4)frame[73]=1;
 ps=1;tick;ps=0;
 if(mode==4)begin if(!fault||pub||ov||retained)$fatal(1,"JOIN_MISMATCH owner74 truncated into73 consumer");$display("JOIN_PASS owner74_high_rejected_no_truncation");$finish;end
 for(integer r=0;r<95;r++)for(integer q=0;q<4;q++)send(r,q);
 while(!er)tick;empty_v=1;tick;empty_v=0;
 if(!pub||writes!=380)$fatal(1,"JOIN_MISMATCH incomplete real publication");
 if(mode==2)begin
 dut.store.g_bank[0].bank.g_macro[0].u_sram.arr[0][2]=~dut.store.g_bank[0].bank.g_macro[0].u_sram.arr[0][2];
 end
 if(mode==3)begin
 dut.store.g_bank[0].bank.g_macro[0].u_sram.arr[0][2]=~dut.store.g_bank[0].bank.g_macro[0].u_sram.arr[0][2];
 dut.store.g_bank[0].bank.g_macro[0].u_sram.arr[0][4]=~dut.store.g_bank[0].bank.g_macro[0].u_sram.arr[0][4];
 end
 if(mode==5)begin retire=1;tick;if(!fault)$fatal(1,"JOIN_MISMATCH early retirement accepted");$display("JOIN_PASS early_retirement_rejected");$finish;end
 while(!csr)tick;cs=1;tick;cs=0;
 if(mode==1||mode==3)begin
 while(!fault&&!done)tick;
 if(!fault||emitted!=0)$fatal(1,"JOIN_MISMATCH malformed source orUE not quarantined");
 $display("JOIN_PASS rejected_fault mode=%0d",mode);$finish;
 end
 while(!done&&!fault)tick;
 if(fault)$fatal(1,"JOIN_MISMATCH unexpected consumer fault");
 if(mode==2)begin if(emitted!=950||ce_responses!=15)$fatal(1,"JOIN_MISMATCH CE outputs=%0d responses=%0d",emitted,ce_responses);$display("JOIN_PASS real_macro_CE outputs=950 repeated_flit_reads=15");$finish;end
 if(emitted!=950)$fatal(1,"JOIN_MISMATCH output count=%0d",emitted);
 downstream_drained=1;tick;retire=1;tick;retire=0;
 if(retained||fault)$fatal(1,"JOIN_MISMATCH final retirement");
 $display("JOIN_PASS ranks=96 native_flits=380 literal_extent=5700 outputs=950 cycles=%0d",cycles);$finish;
 end
endmodule
