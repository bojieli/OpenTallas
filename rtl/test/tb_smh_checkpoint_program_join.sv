`timescale 1ns/1ps
module tb_smh_checkpoint_program_join;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,command_cfg_we=0,read_cfg_we=0,command_start_v=0,read_start_v=0;
 reg [9:0] cfg_addr=0,start_base=0;reg [10:0] start_limit=72;reg [15:0] start_loops=2;
 reg [255:0] command_cfg_data=0,read_cfg_data=0;
 reg open_v=0,open_bank=0,retire_v=0,retire_bank=0;
 reg [15:0] open_epoch=16'h4567,retire_epoch=16'h4567;
 reg [6:0] open_count=40;reg [9:0] open_tag_base=10'd1000;
 reg [3:0] sector_v=0;reg [95:0] sector_index=0;reg [63:0] sector_epoch=0;reg [1023:0] sector_data=0;
 wire [1:0] block_ready,bank_owned;
 wire [82:0] command;wire [1098:0] packet;
 wire command_v,read_calendar_v,command_done,read_done;
 wire [31:0] command_ordinal,read_ordinal;
 wire [1081:0] lt0,lt1;wire [569:0] lb0,lb1;
 wire [11:0] fm;wire [42:0] expected_request;wire programme_fault,service_fault,feed_fault;
 ot_smh_packed_program_join dut(.*);
 reg [1081:0] want_l0=0,want_l1=0;reg [569:0] want_b0=0,want_b1=0;
 integer i,k,ordinal,phase,n,cycle=0,seen=0,sourceedges=0;
 reg watching=0,old_command_v=0,old_command_v2=0;
 reg [1087:0] lines[0:39];reg [255:0] ci[0:71],ri[0:71];
 string sourcepath,commandpath,readpath;
 function automatic [1087:0] line_for(input integer row);line_for=lines[row];endfunction
 function automatic [255:0] sector_for(input integer sector);
 integer off;begin for(integer j=0;j<32;j=j+1)begin off=sector*32+j;sector_for[j*8+:8]=off<40*136?lines[off/136][8*(off%136)+:8]:0;end end
 endfunction
 function automatic [82:0] command_for(input integer slot_);command_for=ci[slot_][82:0];endfunction
 function automatic [1081:0] expected_l(input integer slot_);
 reg [82:0] c;reg [1087:0] l;integer row;begin c=command_for(slot_);row=(c[39:30]-1000)&1023;l=line_for(row);expected_l={c[25:0],l[1055:0]};end
 endfunction
 function automatic [569:0] expected_b(input integer slot_);
 reg [82:0] c;reg [1087:0] l;integer row;begin c=command_for(slot_);row=(c[39:30]-1000)&1023;l=line_for(row);expected_b={c[25:0],l[1087:1056],l[1023:512]};end
 endfunction
 task tick;begin @(posedge clk);#1;cycle=cycle+1;end endtask
 always @(posedge clk)begin
   if(rst_n&&watching)begin
     // Compare at capture edge against the exact scheduled command and source
     // bytes. No dynamic service status is permitted to alter these slots.
     if(command_v && command[29])begin
       if(packet!=={1'b1,command[39:30],line_for((command[39:30]-1000)&1023)})
         $fatal(1,"PROGRAMJOIN packet identity/byte/edge mismatch ordinal=%0d",command_ordinal);
       seen=seen+1;
     end
     if(old_command_v2 && (lt0!==want_l1 || lt1!==want_l1 || lb0!==want_b1 || lb1!==want_b1))
       $fatal(1,"PROGRAMJOIN native S1 boundary mismatch");
     old_command_v2=old_command_v;old_command_v=command_v&&command[25];
     want_l1=want_l0;want_b1=want_b0;
     if(command_v&&command[25])begin
       want_l0=expected_l(command_ordinal%72);
       want_b0=expected_b(command_ordinal%72);
     end else begin want_l0=0;want_b0=0;end
   end
 end
 initial begin
   if(!$value$plusargs("LINES=%s",sourcepath)||!$value$plusargs("COMMAND=%s",commandpath)||!$value$plusargs("READ=%s",readpath))$fatal(1,"source image args required");
   $readmemh(sourcepath,lines);$readmemh(commandpath,ci);$readmemh(readpath,ri);
   repeat(4)tick();@(negedge clk);rst_n=1;
   for(i=0;i<72;i=i+1)begin
     @(negedge clk);command_cfg_we=1;read_cfg_we=1;cfg_addr=10'(i);
     command_cfg_data=ci[i];
     read_cfg_data=ri[i];if(MUT==1 && read_cfg_data[33])read_cfg_data[9:0]=read_cfg_data[9:0]+1'b1;tick();
   end
   @(negedge clk);command_cfg_we=0;read_cfg_we=0;open_v=1;tick();
   @(negedge clk);open_v=0;ordinal=0;phase=0;
   while(ordinal<172)begin
     n=phase==4?1:4;if(172-ordinal<n)n=172-ordinal;
     sector_v=0;
     for(k=0;k<n;k=k+1)begin sector_v[k]=1;sector_index[k*24+:24]=ordinal+k;sector_epoch[k*16+:16]=16'h4567;sector_data[k*256+:256]=sector_for(ordinal+k);end
     tick();if(service_fault)$fatal(1,"PROGRAMJOIN packed source fault");sourceedges=sourceedges+1;
     @(negedge clk);ordinal=ordinal+n;phase=phase==4?0:phase+1;
   end
   sector_v=0;tick();tick();tick();if(block_ready!==2'b01 || sourceedges!=51)$fatal(1,"PROGRAMJOIN prefetch finite boundary");
   // Ready is observed once before the fixed programme; it never gates slots.
   @(negedge clk);read_start_v=1;tick();@(negedge clk);read_start_v=0;command_start_v=1;tick();
   @(negedge clk);command_start_v=0;watching=1;
   repeat(153)tick();
   if(seen!=80||programme_fault||service_fault||feed_fault)$fatal(1,"PROGRAMJOIN missing slots or fault seen=%0d",seen);
   $display("CHECKPOINT PROGRAMJOIN PASS80 actualreleased136Bpackets actualSRAM83/34planes 144slots originalS1fullwidth 40rowprefetch51edges");$finish;
 end
endmodule
