`timescale 1ps/1fs
`default_nettype none
// Component stimulus only: scratch input is initialized explicitly through native DQ.
module tb_source_write_causal_1101 #(parameter integer STK=3, PHY_QUAD=0, WB_MUT=0);
 initial if(STK!=3)$fatal(1,"DBK source SID is STK; only SID3 scratch staged in this fixture");
 reg clk=0,rst_n=0; always #416.5 clk=~clk;
 reg cfg_v=0;reg[7:0]cfg_target=0;reg[11:0]cfg_addr=0;reg[255:0]cfg_data=0;
 reg write_desc_v=0,write_launch=0,calendar_v=0,load_desc_v=0,load_step=0,release_v=0;
 reg[88:0]calendar_payload=0;reg[226:0]load_desc=0;reg[15:0]epoch=7;
 reg[280:0]staged_dq=0;reg[135:0]readback_rq=0;wire[2055:0]readback_rr;
 wire[7:0]VM_done;wire[15:0]block_ready;wire store_src,store_done,store_busy,store_quiet,load_active,fault;wire[11:0]true_ACKs;
 wire[31:0]physical_write_count,physical_read_count,physical_completion_count;
 reg[280:0]stage[0:63];reg[31:0]expected[0:511];reg[226:0]wm[0:0],rm[0:0];reg[255:0]bootlo[0:0],boothi[0:0];
 integer sectors=39,words=312,row=16384,col=6,cyc=0,done_seen=0,native_done=0,read_got=0,read_sent=0,check_mode=0;
 integer write_base=0,completion_base=0,read_base=0,mut_stale=0;reg[255:0]read_expect[0:127];
 source_write_vehicle_1101 #(.STK(STK),.PHY_QUAD(PHY_QUAD),.WB_MUT(WB_MUT))dut(
 .clk(clk),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .refresh_lo_tgt(8'd127),.refresh_hi_tgt(8'd126),.write_tgt(8'd104),.write_desc_v(write_desc_v),.write_limit(13'd1),.write_launch(write_launch),
 .calendar_v(calendar_v),.calendar_payload(calendar_payload),.load_desc_v(load_desc_v),.load_desc(load_desc),.load_step(load_step),
 .window_buffer(1'b0),.window_epoch(epoch),.window_row(15'(row)),.window_col(4'(col)),.release_v(release_v),.release_epoch(epoch),
 .staged_dq(staged_dq),.readback_rq(readback_rq),.readback_rr(readback_rr),.VM_done(VM_done),.block_ready(block_ready),
 .store_src(store_src),.store_done(store_done),.store_busy(store_busy),.store_quiet(store_quiet),.load_active(load_active),.true_ACKs(true_ACKs),.fault(fault),
 .physical_write_count(physical_write_count),.physical_read_count(physical_read_count),.physical_completion_count(physical_completion_count));
 always @(posedge clk)begin
 cyc=cyc+1;
 if(rst_n)begin
 #0.001;
 if(fault)$fatal(1,"CAUSAL_FAULT cycle%0d cp%b back%b wb%b source%b pc%h vmks%h provider%b vm%h",cyc,dut.cp_fault,dut.store_fault,dut.wb_fault,dut.source_fault,dut.pc_fault,dut.vmks_fault,dut.provider_fault,dut.vm_fault);
 native_done=native_done+$countones(VM_done);
 if(store_done)begin
 done_seen=done_seen+1;
 if(physical_completion_count-completion_base!=sectors)$fatal(1,"CAUSAL_EARLY_ACK completed%0d expected%0d",physical_completion_count-completion_base,sectors);
 if(physical_write_count-write_base!=sectors)$fatal(1,"CAUSAL_WRITE_COUNT");
 end
 for(integer b=0;b<8;b=b+1)if(readback_rr[b*257+256])begin
 if(read_got>=read_sent)$fatal(1,"CAUSAL_UNSOLICITED_READ");
 if(readback_rr[b*257+:256]!==read_expect[read_got])$fatal(1,"CAUSAL_READBACK phase%0d sector%0d got%h expected%h",check_mode,read_got,readback_rr[b*257+:256],read_expect[read_got]);
 read_got=read_got+1;
 end
 end end
 task tick;@(negedge clk);endtask
 task config_word(input[11:0]a,input[255:0]d);begin cfg_addr=a;cfg_data=d;cfg_v=1;tick();cfg_v=0;repeat(3)tick();end endtask
 task cache_fill;begin
 calendar_payload=0;calendar_payload[0]=1;calendar_payload[17:2]=epoch;calendar_payload[84:70]=15'(row);calendar_payload[88:85]=4'(col);calendar_v=1;tick();calendar_v=0;
 repeat(15)tick();calendar_payload=0;calendar_payload[52]=1;calendar_payload[69:54]=epoch;calendar_payload[84:70]=15'(row);calendar_payload[88:85]=4'(col);calendar_v=1;tick();calendar_v=0;
 while((block_ready&16'h5555)!=16'h5555)tick();
 $display("CAUSAL_FILL epoch%0d cycle%0d reads%0d",epoch,cyc,physical_read_count);
 end endtask
 task copy_to_vm;begin
 load_desc=rm[0];load_desc_v=1;tick();load_desc_v=0;load_step=1;repeat(sectors)tick();load_step=0;repeat(30)tick();
 if(load_active)$fatal(1,"CAUSAL_COPY_NOT_DRAINED");
 end endtask
 task read_vm(input integer base_word,input integer kind);reg[255:0]exp;integer bank,sec;begin
 read_sent=0;read_got=0;check_mode=kind;
 for(integer s=0;s<sectors;s=s+1)begin
 sec=(base_word>>3)+s;bank=sec&7;exp=0;
 for(integer w=0;w<8;w=w+1)begin
 if(kind==0)exp[w*32+:32]=32'h3e000000^((32'(rm[0][44:5]>>5)*8+32'(s*8+w))&32'h00ffffff);
 else exp[w*32+:32]=expected[s*8+w];
 end
 read_expect[read_sent]=exp;read_sent=read_sent+1;readback_rq=0;readback_rq[bank*17+:17]={1'b1,16'(sec)};tick();
 end
 readback_rq=0;repeat(20)tick();if(read_got!=sectors)$fatal(1,"CAUSAL_READ_DRAIN");
 end endtask
 reg[339:0]entry;string casedir;
 initial begin
 void'($value$plusargs("CASE=%s",casedir));void'($value$plusargs("SECTORS=%d",sectors));void'($value$plusargs("ROW=%d",row));void'($value$plusargs("COL=%d",col));void'($value$plusargs("MUT_STALE=%d",mut_stale));words=sectors*8;
 $readmemh({casedir,"/staged_native_DQ.mem"},stage,0,sectors-1);$readmemh({casedir,"/expected_new_words.mem"},expected,0,words-1);
 $readmemh({casedir,"/write_move227.mem"},wm);$readmemh({casedir,"/read_move227.mem"},rm);$readmemh("boot_0.mem",bootlo);$readmemh("boot_1.mem",boothi);
 repeat(32)tick();rst_n=1;repeat(32)tick();cfg_target=127;config_word(12'h800,bootlo[0]);cfg_target=126;config_word(12'h800,boothi[0]);
 while(dut.refresh_ready!=2'b11)tick();
 cache_fill();copy_to_vm();read_vm(261632,0);
 for(integer s=0;s<sectors;s=s+1)begin staged_dq=stage[s];tick();end staged_dq=0;repeat(20)tick();read_vm(261120,1);
 cfg_target=104;entry=0;entry[31:0]=32'd24;entry[63:32]=32'd64;entry[95:64]=32'd80;entry[322:96]=wm[0];entry[323]=0;entry[339:324]=16'd9;
 config_word(12'h800,entry[255:0]);config_word(12'h801,{172'd0,entry[339:256]});
 repeat(16)tick();write_desc_v=1;tick();write_desc_v=0;repeat(16)tick();
 if(!dut.cp_configured)$fatal(1,"CAUSAL_CP_CONFIG");
 write_base=physical_write_count;completion_base=physical_completion_count;write_launch=1;tick();write_launch=0;
 while(done_seen==0)tick();repeat(16)tick();
 if(!store_quiet||store_busy)$fatal(1,"CAUSAL_STORE_NOT_QUIET");
 if(mut_stale==0)begin release_v=1;tick();release_v=0;repeat(24)tick();epoch=8;cache_fill();end
 copy_to_vm();read_vm(261632,1);
 if(mut_stale!=0)$fatal(1,"CAUSAL_STALE_MUTANT_ESCAPED");
 $display("CAUSAL_WRITE_REFILL PASS stack%0d q%0d words%0d sectors%0d writes%0d completed%0d reads%0d nativeACK%0d cycle%0d",STK,PHY_QUAD,words,sectors,physical_write_count-write_base,physical_completion_count-completion_base,physical_read_count,native_done,cyc);$finish;
 end
endmodule
`default_nettype wire
