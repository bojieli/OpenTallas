`timescale 1ns/1ps
module tb_s81_boot_visibility;
 reg ck=0,rst_n=0; always #1 ck=~ck;
 reg iv=0,we=1; reg[31:0] a=0; reg[255:0] d=0; wire cr;
 wire[3:0] wv; reg[3:0] wr=15; wire[79:0] wa;wire[1023:0] wd;
 wire[1:0] present;wire ok,f;wire[3:0] fc;wire[31:0] sectors,markers;
 integer writes=0,err=0,phase=0;
 ot_s81_boot_seq #(.HAW(20),.MAX_POS(2),.NEED(1)) u(.ck(ck),.rst_n(rst_n),.i_v(iv),.i_we(we),.i_addr(a),.i_d(d),.i_cr(cr),
 .kv_v(),.kv_we(),.kv_a(),.kv_d(),.kv_rdy(1'b1),.plain_base(80'd0),.yarn_base(80'd0),.w_v(wv),.w_a(wa),.w_d(wd),.w_rdy(wr),
 .table_present(present),.boot_ok(ok),.fault(f),.fault_code(fc),.st_sectors(sectors),.st_markers(markers));
 always @(posedge ck) if(rst_n) for(integer s=0;s<4;s=s+1) if(wv[s]&&wr[s]) begin
   writes=writes+1;
   if(phase==0 && wd[256*s+:256] != 256'(8*(wa[20*s+:20]/2)+2*s+(wa[20*s+:20]%2)+1)) err=err+1;
 end
 task send(input bit iw,input[31:0] ia,input[255:0] id);
 begin @(negedge ck);iv=1;we=iw;a=ia;d=id;@(negedge ck);iv=0;end
 endtask
 task reset;
 begin @(negedge ck);rst_n=0;iv=0;repeat(3) @(negedge ck);rst_n=1;writes=0;end
 endtask
 initial begin
 reset();
 for(integer i=0;i<15;i=i+1) send(1,32'h80000000+i,256'(i+1));
 repeat(5) @(negedge ck);wr=7;
 send(1,32'h8000000f,256'd16);
 send(1,32'hffffffff,{192'd0,32'hd5596dd9,32'd16});
 repeat(12) @(negedge ck);
 if(ok||present!=0||markers!=0||writes!=15||wv!=8) err=err+1;
 wr=15;repeat(10) @(negedge ck);
 if(!ok||present!=1||f||markers!=1||writes!=16) err=err+1;
 phase=1;reset();send(0,32'h80000000,256'd1);repeat(8) @(negedge ck);
 if(!f||fc!=5||ok||writes!=0) err=err+1;
 reset();send(1,32'h80000001,256'd2);repeat(8) @(negedge ck);
 if(!f||fc!=1||ok||writes!=0) err=err+1;
 $display("TB_S81_BOOT_VISIBILITY held_last_write=checked static_read=checked out_of_order=checked errors=%0d %s",err,err==0?"PASS":"FAIL");
 if(err) $fatal(1,"boot visibility gate");$finish;
 end
endmodule
