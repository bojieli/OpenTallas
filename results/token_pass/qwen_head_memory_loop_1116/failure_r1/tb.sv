`timescale 1ns/1ps
module tb;
reg ck=0; always #0.5 ck=~ck;
reg rst_n=0,emit=0,last=0; reg[17:0]idx=0; reg[23:0]ra=0,wa=128;
wire hrst;wire h_va_re,h_vm_we,h_retire,h_l_fault;wire[23:0]h_va_addr,h_vm_waddr;wire[31:0]h_vm_wdata,cva;
qfd_dv_lane_h_su_mem9 #(.MEMORY_ALIGNMENT(3),.MEMORY_READ_EXTRA(9),.KV_WR_PIPE(1)) head(.clk(ck),.rst_n(hrst),.emit0(emit),.live(1'b1),.i(idx),.fin_th(19'd127),.i_last_r(last),.cura0(ra),.asi(24'd1),.asrc('0),.ma('0),.ad('0),.imm1('0),.cls('0),.accept(emit),.i_sfu('0),.va_re(h_va_re),.va_addr(h_va_addr),.va_q(cva),.vb_re(),.vb_addr(),.vb_q('0),.vc_re(),.vc_addr(),.vc_q('0),.wrom_re(),.wrom_addr(),.wrom_q('0),.crom_re(),.crom_addr(),.crom_q('0),.vm_we(h_vm_we),.vm_waddr(h_vm_waddr),.vm_wdata(h_vm_wdata),.kv_we(),.kv_waddr(),.kv_wdata(),.l_ov(),.l_out(),.l_red(),.l_redsq(),.l_raddr(),.l_last(),.retire(h_retire),.l_fault(h_l_fault),.sx_exp_v(),.sx_exp_x(),.sy_exp_y('0),.sy_exp_vo('0),.sy_exp_f('0),.sx_rcp_v(),.sx_rcp_x(),.sy_rcp_y('0),.sy_rcp_f('0),.sx_rsq_v(),.sx_rsq_x(),.sy_rsq_y('0),.sy_rsq_f('0));
wire req;wire[23:0]addr;wire[31:0]back;
qfd_dv_s5_lrly relay(.ck(ck),.rst_n(rst_n),.gb('0),.gv('0),.lv1(1'b0),.pd1('0),
 .va_q(back),.vb_q('0),.vc_q('0),.cr_q('0),.h_rst_n(hrst),.c_va(cva),
 .h_va_re(h_va_re),.h_va_addr(h_va_addr),.h_vb_re(1'b0),.h_vc_re(1'b0),.h_wrom_re(1'b0),.h_crom_re(1'b0),
 .h_vm_we(h_vm_we),.h_kv_we(1'b0),.h_l_ov(1'b0),.h_l_redsq(1'b0),.h_l_last(1'b0),.h_retire(h_retire),.h_l_fault(h_l_fault),
 .h_vb_addr('0),.h_vc_addr('0),.h_wrom_addr('0),.h_crom_addr('0),.h_vm_waddr(h_vm_waddr),.h_kv_waddr('0),.h_l_raddr('0),
 .h_vm_wdata(h_vm_wdata),.h_kv_wdata('0),.h_l_out('0),.h_l_red('0),.va_re(req),.va_addr(addr));
integer rqdelay=4,rpdelay=4;
reg[199:0]rq[0:21];reg[255:0]rp[0:20];integer z;
wire[199:0]rqsrc={7'b0,req,168'b0,addr};
always @(posedge ck) begin
 rq[0]<=rqsrc;for(integer a=1;a<22;a=a+1)rq[a]<=rq[a-1];
 rp[0]<=aq;for(integer a=1;a<21;a=a+1)rp[a]<=rp[a-1];
end
wire[199:0]rd;wire[255:0]q,aq; wire vr;
qfd_dv_s8_vm8q_rp1_rst rs(.ck(ck),.d(rst_n),.q(vr));
qfd_dv_s8_vm8q_rp1_vrd rda(.ck(ck),.d(rq[rqdelay-1]),.q(rd));
reg w1=0;reg[23:0]waddr=0;reg[31:0]wdata=0;wire[1049:0]vw;
qfd_dv_s8_vm8q_rp1_vwr vwa(.ck(ck),.d({7'b0,h_vm_we,168'b0,h_vm_waddr,224'b0,h_vm_wdata,1'b0,24'b0,512'b0,w1,waddr,wdata}),.q(vw));
wire fault;
qfd_dv_s8x_vmr #(.MIF(1)) vm(.ck(ck),.rst_n(vr),.re(rd[199:192]),.addr(rd[191:0]),.q(q),
 .vm_we(vw[1049:1042]),.vm_waddr(vw[1041:850]),.vm_wdata(vw[849:594]),.w16_we(vw[593]),.w16_addr(vw[592:569]),.w16_data(vw[568:57]),
 .w1_we(vw[56]),.w1_addr(vw[55:32]),.w1_data(vw[31:0]),.fault(fault));
qfd_dv_s5_vm8out #(.W(256)) oa(.ck(ck),.d(q),.q(aq));
assign back=rp[rpdelay-1][31:0];
function automatic[31:0]datum(input integer n);datum=32'h3f800000+n*32'h1000;endfunction
integer cy=0,active=0,nwrite=0,nret=0,bad=0,first_req=-1,first_bound=-1,first_reply=-1,first_operand=-1,first_write=-1,first_ret=-1,origin=0;
always @(posedge ck) begin
 cy=cy+1;
 if(active!=0)begin
 if(req&&first_req<0)first_req=cy;
 if(rq[rqdelay-1][192]&&first_bound<0)first_bound=cy;
 if(aq[31:0]==datum(0)&&first_reply<0)first_reply=cy;
 if(head.u_h.u_lane.s1_v&&first_operand<0)first_operand=cy;
 if(h_retire)begin nret=nret+1;if(first_ret<0)first_ret=cy;end
 if(h_vm_we)begin
 if(first_write<0)first_write=cy;
 if(h_vm_waddr<128||h_vm_waddr>255||h_vm_wdata!==datum(h_vm_waddr-128))begin
 bad=bad+1;if(bad<=4)$display("WRONG case=%0d cycle=%0d addr=%0d got=%08x expected=%08x",active,cy,h_vm_waddr,h_vm_wdata,datum(h_vm_waddr-128));end
 nwrite=nwrite+1;
 end
 end
end
integer k,c,fail=0;
initial begin
 for(c=1;c<=3;c=c+1)begin
 @(negedge ck);rst_n=0;emit=0;w1=0;active=0;
 rqdelay=(c==1)?4:22;rpdelay=(c==1)?4:((c==2)?21:20);
 repeat(100)@(negedge ck);rst_n=1;repeat(100)@(negedge ck);
 for(k=0;k<128;k=k+1)begin w1=1;waddr=k;wdata=datum(k);@(negedge ck);end
 w1=0;repeat(100)@(negedge ck);
 nwrite=0;nret=0;bad=0;first_req=-1;first_bound=-1;first_reply=-1;first_operand=-1;first_write=-1;first_ret=-1;active=c;origin=cy+1;
 for(k=0;k<128;k=k+1)begin emit=1;idx=k;ra=k;wa=128+k;last=(k==127);@(negedge ck);end
 emit=0;last=0;repeat(300)@(negedge ck);
 $display("CASE case=%0d reqdelay=%0d replydelay=%0d writes=%0d retire=%0d bad=%0d req=%0d bound=%0d first_VMout=%0d operand=%0d write=%0d retire_first=%0d",c,rqdelay,rpdelay,nwrite,nret,bad,first_req-origin,first_bound-origin,first_reply-origin,first_operand-origin,first_write-origin,first_ret-origin);
 if(nwrite!=128||nret!=128||(c==1&&bad!=0)||(c>1&&bad==0))fail=fail+1;
 active=0;
 end
 if(fail)$fatal(1,"LOOP_WITNESS_FAIL cases=%0d",fail);
 $display("LOOP_WITNESS_PASS expected_failures=2 control_pass=1");$finish;
end
endmodule
