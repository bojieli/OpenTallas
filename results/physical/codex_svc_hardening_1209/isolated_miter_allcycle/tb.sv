`timescale 1ns/1ps
module tb;
reg ck=0;always #0.5 ck=~ck;
reg rst=0,i_cv=0,i_sv=0,i_mv=0;reg[31:0]i_s=0;
wire sk_en=0;wire[6:0]i_nv=9;wire[31:0]i_scale=32'h3f800000,i_sink=0,i_nmb=32'hbf800000;
wire g_o_mxv;
wire [31:0] g_o_mx;
wire g_o_ev;
wire g_o_es;
wire g_o_el;
wire [31:0] g_o_e;
dsfd_su_t_sml  u_g(.ck(ck),.rst(rst),.sk_en(sk_en),.i_cv(i_cv),.i_nv(i_nv),.i_scale(i_scale),.i_sink(i_sink),.i_sv(i_sv),.i_s(i_s),.i_mv(i_mv),.i_nmb(i_nmb),.o_mxv(g_o_mxv),.o_mx(g_o_mx),.o_ev(g_o_ev),.o_es(g_o_es),.o_el(g_o_el),.o_e(g_o_e));
wire c_o_mxv;
wire [31:0] c_o_mx;
wire c_o_ev;
wire c_o_es;
wire c_o_el;
wire [31:0] c_o_e;
codex_svc_sml_native  u_c(.ck(ck),.rst(rst),.sk_en(sk_en),.i_cv(i_cv),.i_nv(i_nv),.i_scale(i_scale),.i_sink(i_sink),.i_sv(i_sv),.i_s(i_s),.i_mv(i_mv),.i_nmb(i_nmb),.o_mxv(c_o_mxv),.o_mx(c_o_mx),.o_ev(c_o_ev),.o_es(c_o_es),.o_el(c_o_el),.o_e(c_o_e));
wire m_o_mxv;
wire [31:0] m_o_mx;
wire m_o_ev;
wire m_o_es;
wire m_o_el;
wire [31:0] m_o_e;
codex_svc_sml_native #(.MUT(1)) u_m(.ck(ck),.rst(rst),.sk_en(sk_en),.i_cv(i_cv),.i_nv(i_nv),.i_scale(i_scale),.i_sink(i_sink),.i_sv(i_sv),.i_s(i_s),.i_mv(i_mv),.i_nmb(i_nmb),.o_mxv(m_o_mxv),.o_mx(m_o_mx),.o_ev(m_o_ev),.o_es(m_o_es),.o_el(m_o_el),.o_e(m_o_e));
integer seen=0,holdbad=0,checks=0,bad=0,mutdiff=0,validwords=0,lane,v;
always @(negedge ck) if(rst) begin
 checks=checks+1;
 if({g_o_mxv,g_o_ev,g_o_es,g_o_el} !== {c_o_mxv,c_o_ev,c_o_es,c_o_el})bad=bad+1;
 if(g_o_mxv && g_o_mx!==c_o_mx)bad=bad+1;
 if(g_o_mxv)seen=1;
 if(seen && g_o_mx!==c_o_mx)holdbad=holdbad+1;
 if(g_o_ev && g_o_e!==c_o_e)bad=bad+1;
 if(g_o_ev)validwords=validwords+1;
 if({g_o_mxv,g_o_ev,g_o_es,g_o_el} !== {m_o_mxv,m_o_ev,m_o_es,m_o_el})mutdiff=mutdiff+1;
end
initial begin
 repeat(8)@(negedge ck);rst=1;repeat(8)@(negedge ck);
 for(lane=0;lane<16;lane=lane+1)begin
  i_cv=1;@(negedge ck);i_cv=0;repeat(4)@(negedge ck);
  for(v=0;v<9;v=v+1)begin i_sv=1;i_s=(v==8&&lane>4)?32'hff800000:32'h3f800000+(lane<<10)+(v<<16);@(negedge ck);end
  i_sv=0;wait(g_o_mxv);@(negedge ck);i_mv=1;@(negedge ck);i_mv=0;repeat(130)@(negedge ck);
 end
 $display("SML_NATIVE_BOUNDARY checks=%0d validwords=%0d bad=%0d mutantdiff=%0d cycles_added=0",checks,validwords,bad,mutdiff);
 $display("SML_HOLD_ALLCYCLE holdbad=%0d",holdbad);
 if(holdbad || bad || validwords<144 || mutdiff==0)$fatal(1,"SML_NATIVE_BOUNDARY FAIL");
 $display("SML_NATIVE_BOUNDARY PASS");$finish;
end
initial begin #20000;$fatal(1,"protocol did not complete within native component schedule");end
endmodule
