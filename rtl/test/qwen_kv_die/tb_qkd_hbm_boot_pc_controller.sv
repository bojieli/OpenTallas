`timescale 1ns/1ps
module tb_qkd_hbm_boot_pc_controller;
 parameter MUT=0;
 reg ck=0,hclk=0;always #0.416667 ck=~ck;always #0.512 hclk=~hclk;
 reg rn=0,start=0,corrupt=0;wire[287:0]es;wire[260:0]er;
 reg[287:0]normal_es=0;wire[260:0]normal_er;wire busy,done,ok;wire[3:0]cause;wire[327:0]po;reg[288:0]pi=0;wire fo;
 qkd_hbm_boot_static #(.TIMEOUT(20000),.MUT(MUT))boot(.ck(ck),.ck_test(ck),.rst_n(rn),.boot_go(start),.normal_es(normal_es),.normal_er(normal_er),.ctrl_es(es),.ctrl_er(er),.boot_done(done),.boot_ok(ok),.boot_cause(cause),.fault());
 qkd_ctrl_pc ctl(.pll_hbm(hclk),.hrst(rn),.ck(ck),.rsi(rn),.pc(5'd13),.ci(319'd0),.co(),.es(es),.er(er),.po(po),.pi(pi),.ki(33'd0),.ko(),.fi(1'b0),.fo(fo));
 `include "qkd_strip_map.vh"
    function automatic [71:0] enc64(input [63:0] data);
        reg [71:0] c; integer p, k, j;
        begin
            c = '0; j = 0;
            for (p = 1; p <= 71; p = p + 1) if ((p & (p - 1)) != 0) begin c[p-1] = data[j]; j = j + 1; end
            for (k = 0; k < 7; k = k + 1)
                for (p = 1; p <= 71; p = p + 1)
                    if ((p & (1 << k)) != 0 && p != (1 << k)) c[(1<<k)-1] = c[(1<<k)-1] ^ c[p-1];
            c[71] = ^c[70:0]; enc64 = c;
        end
    endfunction
    function automatic [287:0] enc256(input [255:0] d);
        enc256 = {enc64(d[255:192]), enc64(d[191:128]), enc64(d[127:64]), enc64(d[63:0])};
    endfunction

 reg[287:0]mem=0;integer cyc=0,nwr=0,nrd=0;
 longint wr_due[$],rd_due[$];reg[287:0]rd_word[$];
 always @(posedge hclk)begin
  cyc++;pi<=0;
  if(wr_due.size()!=0&&wr_due[0]<=cyc)begin mem=po[O_po_wd+:288];nwr++;void'(wr_due.pop_front());end
  if(rd_due.size()!=0&&rd_due[0]<=cyc)begin pi<={rd_word[0],1'b1};void'(rd_due.pop_front());void'(rd_word.pop_front());end
  if(rn&&po[O_po_col_v])begin
   if(po[O_po_col_bank+:5]!=3||po[O_po_col_col+:5]!=2)$fatal(1,"wrong column");
   if(po[O_po_col_we])wr_due.push_back(cyc+5);
   else begin nrd++;rd_due.push_back(cyc+14);rd_word.push_back(corrupt?(mem^288'h7):mem);end
  end
 end
 task kick;
  @(negedge ck);start=1;@(negedge ck);start=0;
  wait(done);@(negedge ck);
 endtask
 initial begin
  repeat(8)@(negedge ck);rn=1;repeat(300)@(negedge ck);
  kick();if(!ok||nwr!=2||nrd!=2||fo)$fatal(1,"controller good check rejected writes%0d reads%0d fault%0d",nwr,nrd,fo);
  repeat(4)@(negedge ck);
  normal_es={1'b1,1'b1,5'd3,5'd2,19'd0,256'h1234,1'b1};
  @(negedge ck);normal_es=0;wait(normal_er[259]);
  @(negedge ck);normal_es={1'b0,1'b0,5'd3,5'd2,19'd0,256'b0,1'b1};
  @(negedge ck);normal_es=0;wait(normal_er[0]);
  if(normal_er[256:1]!=256'h1234||normal_er[258])$fatal(1,"normal path after boot differs");
  @(negedge ck);rn=0;repeat(8)@(negedge ck);rn=1;repeat(300)@(negedge ck);corrupt=1;kick();if(ok||cause!=3)$fatal(1,"controller corrupted data accepted");
  $display("PASS real qkd_ctrl_pc boot roundtrip good/corrupt: writes%0d reads%0d",nwr,nrd);$finish;
 end
 initial begin #200000;$fatal(1,"controller watchdog");end
endmodule
