`timescale 1ns/1ps
// S81-RCK-8 SML form C miter: production dsfd_su_t_sml (golden) vs codex_svc_sml_native form C,
// cold reset (64 low, stimulus at the first edge after release) + two warm resets (64 low) mid-stream,
// all-cycle compare of every output. Mutants: MUT=1 (score valid dropped), RMUT=1 (valid-line reset copy
// never resets) must both differ.
module tb;
reg ck=0;always #0.5 ck=~ck;
reg rst=0,i_cv=0,i_sv=0,i_mv=0;reg[31:0]i_s=0;
wire sk_en=0;wire[6:0]i_nv=9;wire[31:0]i_scale=32'h3f800000,i_sink=0,i_nmb=32'hbf800000;
`define SML_PORTS(p) .ck(ck),.rst(rst),.sk_en(sk_en),.i_cv(i_cv),.i_nv(i_nv),.i_scale(i_scale),.i_sink(i_sink),.i_sv(i_sv),.i_s(i_s),.i_mv(i_mv),.i_nmb(i_nmb),.o_mxv(p``_o_mxv),.o_mx(p``_o_mx),.o_ev(p``_o_ev),.o_es(p``_o_es),.o_el(p``_o_el),.o_e(p``_o_e)
`define SML_WIRES(p) wire p``_o_mxv,p``_o_ev,p``_o_es,p``_o_el; wire [31:0] p``_o_mx,p``_o_e;
`SML_WIRES(g) `SML_WIRES(c) `SML_WIRES(m) `SML_WIRES(r)
dsfd_su_t_sml u_g(`SML_PORTS(g));
codex_svc_sml_native u_c(`SML_PORTS(c));
codex_svc_sml_native #(.MUT(1)) u_m(`SML_PORTS(m));
codex_svc_sml_native #(.RMUT(1)) u_r(`SML_PORTS(r));
integer seen=0,checks=0,bad=0,ctlbad=0,mxbad=0,ebad=0,mutdiff=0,rmutdiff=0,validwords=0,mxwords=0,lane,v,warm=0;
wire [97:0] g_all={g_o_mxv,g_o_ev,g_o_es,g_o_el,g_o_mx,g_o_e};
wire [97:0] c_all={c_o_mxv,c_o_ev,c_o_es,c_o_el,c_o_mx,c_o_e};
wire [97:0] m_all={m_o_mxv,m_o_ev,m_o_es,m_o_el,m_o_mx,m_o_e};
wire [97:0] r_all={r_o_mxv,r_o_ev,r_o_es,r_o_el,r_o_mx,r_o_e};
always @(negedge ck) begin
 checks=checks+1;
 // control outputs are reset: compare on every cycle, including while rst is low
 if({g_o_mxv,g_o_ev,g_o_es,g_o_el} !== {c_o_mxv,c_o_ev,c_o_es,c_o_el}) begin bad=bad+1; ctlbad=ctlbad+1; end
 if(g_o_mxv) begin seen=1; mxwords=mxwords+1; end
 // o_mx has no reset: compare every cycle once the golden produced its first defined value
 if(seen && g_o_mx!==c_o_mx) begin bad=bad+1; mxbad=mxbad+1; end
 if(g_o_ev) validwords=validwords+1;
 if(g_o_ev && g_o_e!==c_o_e) begin bad=bad+1; ebad=ebad+1; end
 if(seen && (g_all !== m_all)) mutdiff=mutdiff+1;
 if({g_o_mxv,g_o_ev,g_o_es,g_o_el} !== {r_o_mxv,r_o_ev,r_o_es,r_o_el}) rmutdiff=rmutdiff+1;
end
task automatic one_lane(input integer l);
 begin
  i_cv=1;repeat(4)@(negedge ck);i_cv=0;repeat(4)@(negedge ck);   // cv held 4 edges: covers the 2-edge release
  for(v=0;v<9;v=v+1)begin i_sv=1;i_s=(v==8&&l>4)?32'hff800000:32'h3f800000+(l<<10)+(v<<16);@(negedge ck);end
  i_sv=0;
 end
endtask
task automatic warm_reset;
 begin rst=0;i_cv=0;i_sv=0;i_mv=0;repeat(64)@(negedge ck);rst=1;warm=warm+1; end
endtask
initial begin
 repeat(64)@(negedge ck);rst=1;               // cold: 64 low, stimulus right after release
 for(lane=0;lane<16;lane=lane+1)begin
  one_lane(lane);
  wait(g_o_mxv);@(negedge ck);i_mv=1;@(negedge ck);i_mv=0;
  if(lane==5) begin repeat(30)@(negedge ck); warm_reset; end         // warm reset with the exp pipeline busy
  else if(lane==11) begin repeat(3)@(negedge ck); warm_reset; end    // warm reset right after the re-read starts
  else repeat(130)@(negedge ck);
 end
 repeat(130)@(negedge ck);
 $display("SML_C_MITER checks=%0d validwords=%0d mxwords=%0d bad=%0d ctl=%0d mx=%0d e=%0d warm=%0d mutantdiff=%0d rmutantdiff=%0d added_data_cycles=0 added_reset_cycles=0",
          checks,validwords,mxwords,bad,ctlbad,mxbad,ebad,warm,mutdiff,rmutdiff);
 if(bad || validwords<100 || mutdiff==0 || rmutdiff==0 || warm!=2)$fatal(1,"SML_C_MITER FAIL");
 $display("SML_C_MITER PASS");$finish;
end
initial begin #40000;$fatal(1,"SML_C_MITER TIMEOUT");end
endmodule
