`timescale 1ns/1ps
module tb_calendar_edges;
 reg ck=0; always #5 ck=~ck;
 localparam [31:0] WORD=(32'd7<<18)|(32'd1<<17)|(32'd2<<14)|(32'd3<<10);
 localparam [1023:0] IMAGE={32{WORD}};
 reg rst_n=1,cfg_we=0,cfg_valid=1,start_valid=1,pair_ready=1,pair_poison=0,reload=0;
 reg[15:0] cfg_epoch=16'h1234,start_epoch=16'h1234;
 reg[5:0] cfg_addr=0; reg[63:0] cfg_data_c={WORD,WORD}; reg[4:0] cfg_base_c=3;
 reg[3:0] start_c=0,seg_c=15,halt_c=0;
 wire receipt_ready; wire[31:0]seen; wire base_seen,epoch_valid,settled,poisoned,first_consumed,running,fault,ev_v;
 wire[15:0] receipt_epoch;wire[2:0]ev_port;wire[3:0]ev_kind;wire[4:0]ev_beat;
 ot_qwen_d2d_cal_sf_fe #(.ENABLE_FIRST_EPOCH_GUARD(1),.EXPECTED_IMAGE(IMAGE),.EXPECTED_BOOT_BASE(3),.EXPECTED_TOKEN_BASE(5)) d(.*);
 integer checks=0,sc=0,i,j;reg[31:0] saved_cur,saved_pc;reg[13:0]saved_cnt;
 task tick;begin @(posedge ck);#1;@(negedge ck);end endtask
 task chk(input c,input string name);begin checks++;if(c!==1'b1)begin $display("ASSERT_FAIL %s scenario=%0d time=%0t seen=%h base=%b ready=%b poison=%b run=%b cnt=%h pc=%h cur=%h",name,sc,$time,seen,base_seen,receipt_ready,poisoned,running,d.cnt,d.pc0,d.cur);$fatal(1,"calendar guard violation");end end endtask
 task reset_all;begin
 cfg_we=0;start_c=0;reload=0;pair_poison=0;cfg_valid=1;start_valid=1;cfg_epoch='h1234;start_epoch='h1234;cfg_data_c={WORD,WORD};cfg_base_c=3;cfg_addr=0;halt_c=0;seg_c=15;
 rst_n=0;#1;chk(seen===0 && !base_seen && !epoch_valid && !first_consumed,"RESET_INVALIDATES");tick;rst_n=1;
 end endtask
 task wr(input integer a);begin cfg_addr=a;cfg_we=1;tick;cfg_we=0;end endtask
 task upload(input integer omit);begin for(j=0;j<32;j++)if(j!=omit)wr(j);if(omit!=32)wr(32);end endtask
 task hold_state;begin saved_cur=d.cur;saved_pc=d.pc0;saved_cnt=d.cnt;end endtask
 task veto_check(input string tag);begin
 chk(!running && !first_consumed,tag);chk(d.cur===saved_cur && d.pc0===saved_pc && d.cnt===saved_cnt,"INTERNAL_START_VETO");chk(poisoned,"STICKY_POISON");start_c=0;end endtask
 initial begin
 @(negedge ck);
 // Before any reset, unreset table/base state must remain arbitrary/X.
 chk($isunknown(d.g_e[0].e) && $isunknown(d.sel1_c0),"ARBITRARY_OLD_Q");
 // W: start alongside final base; W+1: start while cfg_recent still true.
 for(i=0;i<2;i++)begin sc=200+i;reset_all;for(j=0;j<32;j++)wr(j);cfg_addr=32;cfg_we=1;
 if(i==0)begin hold_state;start_c=15;tick;cfg_we=0;veto_check("W_START_FORBIDDEN");end
 else begin tick;cfg_we=0;hold_state;start_c=15;tick;veto_check("W_PLUS_1_FORBIDDEN");end end
 sc=1;reset_all;
 // Earliest physically accepted post-reset upload edge; no readiness delay.
 wr(0);chk(seen[0] && epoch_valid && d.g_e[0].e===WORD,"FIRST_POST_RESET_ACCEPTED");
 for(i=1;i<32;i++)wr(i);wr(32);chk(!settled && !receipt_ready,"LAST_W_NOT_SETTLED");
 tick;chk(receipt_ready,"W_PLUS_1_RECEIPT"); // start at W+2 (next edge)
 start_c=15;tick;chk(running && first_consumed && d.cur===WORD && d.cnt==7 && d.pc0==16,"HEALTHY_W_PLUS_2_STATE");start_c=0;
 repeat(7)tick;chk(ev_v && ev_port==2 && ev_kind==3,"HEALTHY_EVENT_EXACT_EDGE");
 // A visible data/valid cohort without cfg_we is not an accepted table write.
 sc=50;reset_all;upload(9);repeat(2)tick;cfg_addr=9;cfg_data_c={WORD^32'd1,WORD^32'd1};cfg_we=0;cfg_valid=1;tick;
 chk(!seen[9] && !receipt_ready && d.g_e[9].e===WORD,"EMITTED_VALID_NO_ACCEPTED_CREDIT");
 hold_state;start_c=15;tick;veto_check("EMITTED_VALID_START_VETO");
 // Every actual accepted entry, and the base, is necessary.
 for(i=0;i<33;i++)begin sc=100+i;reset_all;upload(i);repeat(2)tick;chk(!receipt_ready,"OMISSION_RECEIPT");hold_state;start_c=15;tick;veto_check("OMISSION_START_VETO");end
 // Wrong consumed low/high data; unused copy does not affect receipt.
 for(i=0;i<9;i++)begin sc=300+i;reset_all;upload(-1);repeat(2)tick;
 cfg_addr= i==1 ? 20 : 2;cfg_data_c={WORD,WORD};cfg_base_c=3;
 case(i)
 0:cfg_data_c[31:0]=WORD^1;
 1:cfg_data_c[63:32]=WORD^1;
 2:begin cfg_addr=32;cfg_base_c=4;end
 3:begin cfg_addr=33;end
 4:cfg_epoch='h1235;
 5:cfg_valid=0;
 6:cfg_valid=1'bx;
 7:cfg_data_c[31:0]='x;
 8:begin cfg_addr=32;cfg_base_c='x;end
 endcase
 hold_state;cfg_we=1;start_c=15;tick;cfg_we=0;veto_check("MALFORMED_SAME_EDGE_VETO");end
 // Independent malformed-upload witness: no simultaneous start can mask a missing comparison.
 for(i=0;i<9;i++)begin sc=350+i;reset_all;upload(-1);repeat(2)tick;
 cfg_addr=i==1 ? 20 : 2;cfg_data_c={WORD,WORD};cfg_base_c=3;
 case(i)
 0:cfg_data_c[31:0]=WORD^1;
 1:cfg_data_c[63:32]=WORD^1;
 2:begin cfg_addr=32;cfg_base_c=4;end
 3:cfg_addr=33;
 4:cfg_epoch='h1235;
 5:cfg_valid=0;
 6:cfg_valid=1'bx;
 7:cfg_data_c[31:0]='x;
 8:begin cfg_addr=32;cfg_base_c='x;end
 endcase
 cfg_we=1;tick;cfg_we=0;chk(poisoned,"MALFORMED_UPLOAD_POISONS_WITHOUT_START");end
 sc=400;reset_all;upload(-1);repeat(2)tick;cfg_addr=2;cfg_data_c[63:32]='x;wr(2);repeat(2)tick;chk(receipt_ready && !poisoned,"UNCONSUMED_HIGH_COPY_X");
 sc=401;reset_all;upload(-1);repeat(2)tick;cfg_addr=20;cfg_data_c[31:0]='x;wr(20);repeat(2)tick;chk(receipt_ready && !poisoned,"UNCONSUMED_LOW_COPY_X");
 // Already running writes are emitted but never accepted by original storage.
 sc=500;reset_all;upload(-1);repeat(2)tick;start_c=15;tick;start_c=0;
 // Verification fault injection only: deposit a missing receipt bit. This is not a legal producer trace.
 d.seen[9]=0;cfg_addr=9;cfg_data_c={WORD^32'd1,WORD^32'd1};cfg_we=1;tick;cfg_we=0;
 chk(!seen[9] && d.g_e[9].e===WORD && poisoned,"REJECTED_RUNNING_WRITE_NO_CREDIT");
 sc=600;reset_all;upload(-1);repeat(2)tick;chk(receipt_ready,"PRE_RELOAD_READY");reload=1;tick;reload=0;chk(!receipt_ready && seen==0 && !base_seen,"RELOAD_INVALIDATES");
 sc=601;reset_all;start_c=15;hold_state;tick;veto_check("EARLY_START_VETO");wr(0);chk(poisoned,"UPLOAD_MUST_NOT_CLEAR_POISON");upload(-1);repeat(3)tick;chk(poisoned && !receipt_ready && !running && !first_consumed,"LATE_UPLOAD_NO_RETRY");
 reload=1;tick;reload=0;upload(-1);repeat(3)tick;chk(poisoned && !receipt_ready && !running,"RELOAD_CANNOT_CLEAR_POISON");
 sc=602;reset_all;upload(-1);repeat(2)tick;start_epoch='hx;hold_state;start_c=15;tick;veto_check("UNKNOWN_START_ID_VETO");
 sc=603;reset_all;upload(-1);repeat(2)tick;start_c=4'bx111;hold_state;tick;veto_check("UNKNOWN_START_COPY_VETO");
 sc=604;reset_all;upload(-1);repeat(2)tick;pair_poison=1;hold_state;start_c=15;tick;veto_check("SAME_EDGE_PAIR_FAULT_VETO");
 $display("CALENDAR_EDGES_PASS checks=%0d",checks);$finish;
 end
endmodule
