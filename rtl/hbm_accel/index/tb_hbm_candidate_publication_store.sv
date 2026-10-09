`timescale 1ps/1fs
module tb_hbm_candidate_publication_store;
 reg clk=0;always #416.5 clk=~clk;
 reg por_n=0,start=0,owner_valid=1,retire=0,consumer_retained=0;
 reg[73:0] frame={1'b1,73'h2f123456789abcde};
 wire start_r,flit_r,empty_r,pub,retained,fault,read_r,rsp_v;
 reg flit_v=0,empty_v=0,read_v=0,rsp_r=0;
 reg[544:0] flit=0;reg[6:0] empty_rank=0,read_rank=0;reg[16:0] read_ordinal=0;
 wire[73:0] rsp_frame;wire[6:0] rsp_rank;wire[16:0] rsp_ordinal;wire[33:0] rsp_tuple;wire rsp_last,rsp_empty,rsp_ce;
 ot_hbm_candidate_publication_store #(.ENABLE(1),.OWNER_W(74)) dut(
 .clk(clk),.por_n(por_n),.start(start),.start_frame(frame),.start_r(start_r),.owner_valid(owner_valid),.owner_frame(frame),
 .retire(retire),.consumer_retained(consumer_retained),.flit_v(flit_v),.flit_r(flit_r),.flit(flit),.flit_owner(frame),
 .expected_kind(1'b1),.expected_dst(8'd3),.empty_v(empty_v),.empty_r(empty_r),.empty_rank(empty_rank),.empty_frame(frame),
 .publication_complete(pub),.retained(retained),.fault(fault),.read_v(read_v),.read_r(read_r),.read_frame(frame),
 .read_rank(read_rank),.read_ordinal(read_ordinal),.rsp_v(rsp_v),.rsp_r(rsp_r),.rsp_frame(rsp_frame),.rsp_rank(rsp_rank),
 .rsp_ordinal(rsp_ordinal),.rsp_tuple(rsp_tuple),.rsp_last(rsp_last),.rsp_empty(rsp_empty),.rsp_ce(rsp_ce));
 function automatic[33:0] value(input integer rank,ordinal);
 value={17'(rank*1380+ordinal),16'(ordinal^16'hbaba),1'(ordinal%3!=0)};
 endfunction
 integer mode=0,cycles=0,writes=0,reads=0;
 always @(posedge clk)begin cycles<=cycles+1;if(cycles>3000000)$fatal(1,"deadlock watchdog mechanism bound");end
 task tick;begin @(negedge clk);end endtask
 task reset;begin por_n=0;tick;tick;por_n=1;tick;start=1;tick;start=0;end endtask
 task send(input integer rank,q,b,fin);
 begin
 while(!flit_r&&!fault)tick;
 if(fault)$fatal(1,"unexpected fault before flit");
 flit=0;flit[544]=1;flit[543:536]=3;flit[535:528]=8'(rank);flit[527:526]=2'(q);flit[525:512]=14'(b);flit[511]=fin;
 for(integer k=0;k<15;k++)flit[34*k+:34]=value(rank,q*345+b*15+k);
 flit_v=1;tick;flit_v=0;
 while(!flit_r&&!pub&&!fault)tick;
 writes++;
 end endtask
 task readone(input integer r,o);
 begin
 while(!read_r&&!fault)tick;
 read_rank=7'(r);read_ordinal=17'(o);read_v=1;tick;read_v=0;
 while(!rsp_v&&!fault)tick;
 if(fault)$fatal(1,"unexpected provider fault rank%0d ord%0d",r,o);
 if(rsp_frame!==frame||rsp_rank!==r||rsp_ordinal!==o||rsp_tuple!==value(r,o)||rsp_empty||rsp_last!==(o==1379))$fatal(1,"provider mismatch rank%0d ord%0d",r,o);
 repeat(2)begin tick;if(!rsp_v||rsp_tuple!==value(r,o))$fatal(1,"unstable backpressure");end
 rsp_r=1;tick;rsp_r=0;reads++;
 end endtask
 initial begin
 if(!$value$plusargs("mode=%d",mode))mode=0;
 reset;
 if(mode==1)begin send(0,1,0,1);if(!fault)$fatal(1,"wrong quarter accepted");$display("CANDIDATE_PASS rejected_wrong_quarter");$finish;end
 if(mode==2)begin send(0,0,0,1);consumer_retained=1;retire=1;tick;if(!fault)$fatal(1,"early retirement accepted");$display("CANDIDATE_PASS rejected_retirement");$finish;end
 for(integer r=0;r<96;r++)for(integer q=0;q<4;q++)for(integer b=0;b<23;b++)send(r,q,b,b==22);
 if(!pub||writes!=8832)$fatal(1,"premature/missing publication");
 if(mode==3||mode==4)begin
 dut.g_bank[0].bank.g_macro[0].u_sram.arr[0][2]=~dut.g_bank[0].bank.g_macro[0].u_sram.arr[0][2];
 if(mode==4)dut.g_bank[0].bank.g_macro[0].u_sram.arr[0][4]=~dut.g_bank[0].bank.g_macro[0].u_sram.arr[0][4];
 if(mode==4)begin read_rank=0;read_ordinal=0;read_v=1;tick;read_v=0;while(!fault)tick;if(rsp_v)$fatal(1,"UE exposed data");$display("CANDIDATE_PASS UE quarantined");$finish;end
 readone(0,0);if(!rsp_ce)$fatal(1,"CE not corrected");$display("CANDIDATE_PASS CE corrected");$finish;
 end
 for(integer r=0;r<96;r++)for(integer o=0;o<1380;o++)readone(r,o);
 retire=1;tick;retire=0;if(retained||fault)$fatal(1,"clean retirement failed");
 reset;for(integer r=0;r<96;r++)begin while(!empty_r)tick;empty_rank=7'(r);empty_v=1;tick;empty_v=0;end
 if(!pub)$fatal(1,"explicit empty receipt missing");
 read_rank=95;read_ordinal=0;read_v=1;tick;read_v=0;while(!rsp_v)tick;
 if(!rsp_empty||!rsp_last)$fatal(1,"empty reply bad");
 $display("CANDIDATE_PASS full_flits=%0d literal_reads=%0d cycles=%0d owner74=1",writes,reads,cycles);$finish;
 end
endmodule
