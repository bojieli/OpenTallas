`timescale 1ns/1ps
// Three actual mapped-context states; reference retains the identical boundary
// registers, loader, AO protection and RD64 capture. No field/UPF power claim.
module tb_w5_context_activity(input wire clk);
 reg por_n=0,cfg_go=0,go=0,xs_v=0,pg_en=1,sched_v=0;
 reg [23:0] gap=0; reg [7:0] xp=0;reg [2:0] xb=0,pos=0;
 reg [255:0] q0=0,q1=0;reg [3:0] ack=0;
 wire [10:0] ma,ra;wire [3:0] sw,rsw;
 wire ready,late,pgf,fault,busy,ov,oe,rr,rl,rpf,rf,rb,rv,re;
 wire [31:0] ot,od,rt,rd;
 function automatic [47:0] config_word(input [10:0] addr);
 integer a,c;reg [47:0] d;
 begin
 a=addr%25;c=(a<8)?a:((a<16)?a-8:a-17);d=0;
 if(a<8)d=48'(c+1)|(48'd1<<21)|(48'd1<<27)|(48'd1<<28);
 else if(a<16)d=48'(c!=7)|(48'(32*c)<<1)|(48'(c!=7)<<9)|(48'(c)<<16)|(48'(c)<<19);
 else if(a==16)d=0;else d=48'(c+101);
 config_word=d;
 end
 endfunction
 wire [47:0] cm=config_word(ma),rcm=config_word(ra);
 ot_w5_context #(.ENABLE(1),.HARD_CFG(1)) dut(.clk(clk),.por_n(por_n),.cfg_go(cfg_go),.cfg_ph(6'd0),.cfg_np(3'd0),
 .cm_q(cm),.go(go),.xs_v(xs_v),.xs_p(xp),.xs_b(xb),.xs_sv(2'b11),.xs_q0(q0),.xs_q1(q1),
 .xs_e0(10'd127),.xs_e1(10'd126),.xs_pos(pos),.pg_en(pg_en),.sched_v(sched_v),.sched_gap(gap),
 .pg_lead(24'd400),.pg_bet(24'd64),.pg_idle(8'd160),.pg_rst(8'd4),.pg_step(16'd16),.pg_ack_to(16'd200),
 .sw_ack(ack),.cm_a(ma),.sw_en(sw),.ready(ready),.late(late),.pg_fault(pgf),.fault(fault),.busy(busy),
 .o_v(ov),.o_t(ot),.o_d(od),.o_e(oe));
 ot_w5_context_ref #(.ENABLE(1)) ref_e(.clk(clk),.por_n(por_n),.cfg_go(cfg_go),.cfg_ph(6'd0),.cfg_np(3'd0),
 .cm_q(rcm),.go(go),.xs_v(xs_v),.xs_p(xp),.xs_b(xb),.xs_sv(2'b11),.xs_q0(q0),.xs_q1(q1),
 .xs_e0(10'd127),.xs_e1(10'd126),.xs_pos(pos),.pg_en(pg_en),.sched_v(sched_v),.sched_gap(gap),
 .pg_lead(24'd400),.pg_bet(24'd64),.pg_idle(8'd160),.pg_rst(8'd4),.pg_step(16'd16),.pg_ack_to(16'd200),
 .sw_ack(ack),.cm_a(ra),.sw_en(rsw),.ready(rr),.late(rl),.pg_fault(rpf),.fault(rf),.busy(rb),
 .o_v(rv),.o_t(rt),.o_d(rd),.o_e(re));
 genvar j;generate for(j=0;j<4;j=j+1)begin:g_ack
 integer n=0;
 always @(posedge clk)if(sw[j]!=ack[j])begin n=n+1;if(n>=(sw[j]?8:2))begin ack[j]<=sw[j];n=0;end end else n=0;
 end endgenerate
 integer cyc=0,rows=0,nonzero=0,beats=0,cfg_captures=0;
 always @(posedge ref_e.u_stage.u_ao.quarantine) if(cyc>2980)
 $display("QUARANTINE cyc=%0d clk=%b copy_bad=%b external=%b sticky=%b native=%b ctl=%b late=%b diff=%h",cyc,clk,
 ref_e.u_stage.u_ao.bad,ref_e.context_fault,ref_e.u_stage.u_ao.sticky,ref_e.u_stage.e_fault,
 ref_e.u_stage.u_ao.u_p.ctl_fault,ref_e.u_stage.u_ao.u_p.late,
 ref_e.u_stage.u_ao.snap_p^ref_e.u_stage.u_ao.snap_r);
 always @(negedge clk)begin
 cyc=cyc+1;
 if(por_n)begin
 if({dut.u_ld.c_v,dut.u_ld.c_a}!=={ref_e.u_ld.c_v,ref_e.u_ld.c_a})
   $fatal(1,"real cfg timing mismatch cyc=%0d",cyc);
 if(dut.u_ld.c_v)begin
   cfg_captures=cfg_captures+1;
   if(dut.u_ld.c_d!==ref_e.u_ld.c_d)$fatal(1,"real cfg payload mismatch cyc=%0d",cyc);
 end
 if({ma,sw,ready,late,pgf,fault,busy,ov}!=={ra,rsw,rr,rl,rpf,rf,rb,rv})
 $fatal(1,"context control mismatch cyc=%0d",cyc);
 if(fault||late||pgf)$fatal(1,"context real fault cyc=%0d late=%b pgf=%b fault=%b source=%b/%b/%b native=%b return=%b",cyc,late,pgf,fault,ref_e.settings_bad,ref_e.go_bad,ref_e.ld_fault,ref_e.u_stage.e_fault,ref_e.rf);
 if(ov)begin
 if({ot,od,oe}!=={rt,rd,re})$fatal(1,"actual return mismatch cyc=%0d",cyc);
 rows=rows+1;if(od!=0)nonzero=nonzero+1;
 end
 if(cyc>=5000&&cyc<6000&&(ready||(|sw)||busy))$fatal(1,"PG idle window not actually off");
 if(cyc>=21000&&cyc<22000&&(!ready||sw!=4'hf||busy))$fatal(1,"CG idle window not actually powered/idle");
 end
 end
 function automatic [273:0] romword(input [11:0] a);
 reg [127:0] w0,w1;reg [31:0] h;
 begin h={20'd0,a}*32'h9E3779B1+32'h7F4A7C15;w0={4{h^32'h5bd1e995}}&{16{8'h77}};
 h=h*32'h85EBCA6B+1;w1={4{h}}&{16{8'h77}};
 romword={2'b0,8'd120+8'(a[2:0]),w1,8'd123+8'(a[4:3]),w0};end
 endfunction
 function automatic [255:0] xword(input integer b,input integer s);
 reg [31:0] h;reg [255:0] w;
 begin h=b*32'h27D4EB2F+s;for(integer i=0;i<8;i=i+1)begin h=h*32'h165667B1+7;w[i*32+:32]=h;end
 xword=w&{32{8'h77}};end
 endfunction
 task automatic wait_until(input integer t);while(cyc<t)@(negedge clk);endtask
 task automatic token(input integer t,input integer nextgap);
 integer sent;
 begin wait_until(t-1);@(negedge clk);go=1;
 $display("MARK go %0d ready=%0d",cyc,ready);
 @(negedge clk);go=0;sched_v=0;repeat(8)@(negedge clk);sent=0;
 // Announce the following arrival after this GO has crossed its real D3
 // source pipeline. Deadline is at the actual stage launch, three edges later.
 if(nextgap>0)begin sched_v=1;gap=24'(t+nextgap+3-cyc-1);@(negedge clk);sched_v=0;end
 while(ref_e.u_stage.g_el[0].u_elem.n_run&&sent<1000)begin
 xp=ref_e.u_stage.g_el[0].u_elem.n_pair;xb=ref_e.u_stage.g_el[0].u_elem.n_b;
 pos=ref_e.u_stage.g_el[0].u_elem.n_pos;q0=xword(beats,1);q1=xword(beats,2);beats=beats+1;xs_v=1;
 @(negedge clk);xs_v=0;repeat(15)@(negedge clk);sent=sent+1;
 end
 while(rb||rv||busy||ov)@(negedge clk);
 repeat(100)@(negedge clk);$display("MARK end %0d rows=%0d",cyc,rows);
 end
 endtask
 initial begin
 repeat(4)@(negedge clk);por_n=1;
 @(negedge clk);cfg_go=1;@(negedge clk);cfg_go=0;
 repeat(40)@(negedge clk);
 sched_v=1;gap=24'(3000+3-cyc-1);@(negedge clk);sched_v=0;
 token(3000,16000);token(19000,0);
 @(negedge clk);pg_en=0;while(!ready)@(negedge clk);
 token(35000,0);repeat(200)@(negedge clk);
 if(cfg_captures!=25)$fatal(1,"full25 config capture coverage got%0d",cfg_captures);
 if(rows<20||nonzero<10)$fatal(1,"actual capture coverage rows=%0d nonzero=%0d",rows,nonzero);
 $display("PASS actual W5 context rows=%0d nonzero=%0d beats=%0d cycles=%0d",rows,nonzero,beats,cyc);$finish;
 end
endmodule
module ot_rom_4096x274_m8(input wire clk,ce_in,input wire [11:0] addr_in,output reg [273:0] rd_out);
 always @(posedge clk)if(ce_in)rd_out<=tb_w5_context_activity.romword(addr_in);
endmodule

// Real synchronous CFG macro behavioral view; ROM faults are not protected by
// mandatory ECC. cfg_bad is solely a meaningful golden-comparison control.
module ot_rom_4096x72_m8(input wire clk,ce_in,input wire [11:0] addr_in,output reg [71:0] rd_out);
 always @(posedge clk)if(ce_in)
 rd_out <= {24'd0,tb_w5_context_activity.config_word(addr_in[10:0])}
           ^ ($test$plusargs("cfg_bad") ? 72'h4000 : 72'd0);
endmodule
