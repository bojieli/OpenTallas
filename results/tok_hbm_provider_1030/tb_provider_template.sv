`timescale 1ns/1ps
`default_nettype none
module tb_provider;
 reg clk=0,rst_n=0;always begin #0.416 clk=1; #0.417 clk=0; end
 reg desc_v_i=0,step_i=0;reg[226:0]desc_i=0;
 reg window_buffer_i=0;reg[15:0]window_epoch_i=0;reg[14:0]window_row_i=@@ROW@@;reg[3:0]window_col_i=@@COL@@;
 reg begin_v=0,begin_bank=0;reg[15:0]begin_epoch=0;reg[14:0]begin_row=@@ROW@@;reg[3:0]begin_col=@@COL@@;
 reg[15:0]fill_v=0,fill_bank=0;reg[95:0]fill_slot=0;reg[255:0]fill_epoch=0;reg[4095:0]fill_data=0;
 reg release_v_i=0,release_buffer_i=0;reg[15:0]release_epoch_i=0;
 wire active_o,fault_o;wire[280:0]vm_dq;wire[15:0]block_ready;wire[7:0]leaf_fault;
 ot_hbm_static_load_provider_quad #(.SOURCE_QUAD(2)) dut(.*);
 reg[226:0]descs[0:@@ND@@-1];reg[31:0]steps[0:@@ND@@-1];reg[280:0]expected[0:@@NP@@-1];
 integer cyc=0,sent=0,got=0,latency=-1,phase,b,g,s,w,di,j,mut_epoch=0,mut_release=0;
 integer sent_cycle[0:@@NP@@-1];reg[15:0]epoch;reg ebank;
 function automatic[31:0]payload(input integer ph,l,grp,slotno,wordno);
 payload=32'h3e800000+32'(ph)*32'h01000000+32'(l)*32'h00010000+32'(grp)*32'h1000+32'(slotno)*8+32'(wordno);
 endfunction
 task tick;begin @(negedge clk);end endtask
 always @(posedge clk)begin
 cyc=cyc+1;#0.1;
 if(rst_n)begin
 if(fault_o||(|leaf_fault))$fatal(1,"PROVIDER_FAULT cycle=%0d phase=%0d fault=%b leaf=%h",cyc,phase,fault_o,leaf_fault);
 if(vm_dq[280])begin
 if(got>=sent||vm_dq!==expected[got])$fatal(1,"PROVIDER_DATA got=%0d sent=%0d actual=%h expected=%h",got,sent,vm_dq,expected[got]);
 if(latency<0)latency=cyc-sent_cycle[got];
 if(cyc-sent_cycle[got]!=latency)$fatal(1,"PROVIDER_DATE measured=%0d expect=%0d",cyc-sent_cycle[got],latency);
 got=got+1;
 end end end
 initial begin
 $readmemh("fixture_desc.mem",descs);$readmemh("fixture_steps.mem",steps);$readmemh("fixture_expected.mem",expected);
 if($value$plusargs("MUT_EPOCH=%d",mut_epoch))begin end
 if($value$plusargs("MUT_RELEASE=%d",mut_release))begin end
 repeat(32)tick();rst_n=1;repeat(16)tick();
 for(phase=0;phase<3;phase=phase+1)begin
 epoch=16'(7+phase);ebank=phase==2;
 begin_epoch=epoch;begin_bank=ebank;begin_v=1;tick();begin_v=0;repeat(16)tick();
 for(s=0;s<64;s=s+1)begin
 fill_v=16'hffff;
 for(b=0;b<8;b=b+1)for(g=0;g<2;g=g+1)begin
 fill_bank[(b*2+g)]=ebank;fill_slot[(b*2+g)*6+:6]=6'(s);fill_epoch[(b*2+g)*16+:16]=epoch;
 for(w=0;w<8;w=w+1)fill_data[(b*2+g)*256+w*32+:32]=payload(phase,b,g,s,w);
 end tick();end
 fill_v=0;repeat(16)tick();
 for(b=0;b<8;b=b+1)if(!block_ready[b*2+integer'(ebank)])$fatal(1,"PROVIDER_FILL_READY");
 window_buffer_i=ebank;window_epoch_i=epoch;
 if(mut_epoch!=0&&phase==0)window_epoch_i=epoch+1;
 for(di=0;di<@@ND@@;di=di+1)begin
 desc_i=descs[di];desc_v_i=1;tick();desc_v_i=0;
 for(j=0;j<steps[di];j=j+1)begin step_i=1;sent_cycle[sent]=cyc+1;sent=sent+1;tick();end
 step_i=0;
 end
 repeat(24)tick();if(got!=sent)$fatal(1,"PROVIDER_DRAIN got=%0d sent=%0d",got,sent);
 release_buffer_i=ebank;release_epoch_i=epoch;
 if(!(mut_release!=0&&phase==0))begin release_v_i=1;tick();release_v_i=0;end
 repeat(24)tick();
 end
 if(mut_epoch!=0||mut_release!=0)$fatal(1,"PROVIDER_MUTANT_ESCAPED");
 $display("PASS GENUINE_PROVIDER_QUAD descriptors=%0d packets=%0d words=%0d epochs=3 actual_latency=%0d sourcebundle990 allVMquads",3*@@ND@@,got,got*8,latency);$finish;
 end
endmodule
`default_nettype wire
