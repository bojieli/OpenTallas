from pathlib import Path
import sys,re
w=Path('/srv/opentallas-scratch3/claude/wt/codex-lec-transfer-1106');p=Path(__file__).parent;base=p.parent/'am_proof'
sys.path.insert(0,str(w/'tools/s81_link'));from s81_rck_am import TRANSPORT_DECL,add_face3_option,add_transport4_option
for name in ['old_literal.sv','reset_literal.sv','face_literal.sv','good.sv']:(p/name).write_text((base/name).read_text())
tb=(base/'tb.sv').read_text();a=tb.index('`ifdef WRONG_VALID');b=tb.index('`endif',a)+len('`endif')
new='''am_new u_new(.clk(clk),.rst_n(rck_reset_calendar),.p_v(rck_p_v),.p_d(rck_p_d),.am_face3(rck_am_parts),.state(b),.lock(bl),.n_relock(bn));'''
tb=tb[:a]+new+tb[b:]
anchor='wire [8:0] parts;ot_s81_kp4_am_face3 u_parts(.clk(clk),.p_d(raw),.parts(parts));'
assert anchor in tb
extra='''
wire ck_syn=clk;
wire [8:0] face_am_parts=parts;wire face_p_v=face_v;wire [543:0] face_p_d=face;
'''+TRANSPORT_DECL+'''
reg [1716:0] history [0:3];integer h;
always @(posedge clk) begin history[0]<=a;for(h=1;h<4;h=h+1)history[h]<=history[h-1];end
wire [1716:0] expected=history[3];
'''
tb=tb.replace(anchor,anchor+extra).replace('cycle>8 && a!==b','cycle>24 && expected!==b').replace('literal payload/valid/reset/FSM calendar mismatch','literal relay4 cohort/reset/calendar mismatch').replace('added_ff=9 added_full_cycles=0','added_ff=2229 added_full_cycles=4')
for kind in ['good','short_cohort','short_reset','counts_bypass','valid_bypass','data_bypass','reset_bypass']:
 s=tb
 if kind=='short_cohort':s=s.replace('.N(4)) u_rck_transport4','.N(3)) u_rck_transport4')
 if kind=='short_reset':s=s.replace('.N(4)) u_rck_reset4','.N(3)) u_rck_reset4')
 if kind=='counts_bypass':s=s.replace('.am_face3(rck_am_parts)','.am_face3(parts)')
 if kind=='valid_bypass':s=s.replace('.p_v(rck_p_v)','.p_v(face_v)')
 if kind=='data_bypass':s=s.replace('.p_d(rck_p_d)','.p_d(face)')
 if kind=='reset_bypass':s=s.replace('.rst_n(rck_reset_calendar)','.rst_n(rst_n)')
 (p/(kind+'_tb.sv')).write_text(s)
# Verify literal production bindings and exact idempotent generator replay.
lp=(w/'rtl/dsrom_sys/s81_link/lp/ot_s81_kp4_dec_native_flat_lp.sv').read_text()
assert add_transport4_option(lp)==lp
assert '.N(554)' not in lp
print('NATIVE_RELAY4_COHORT width554 depth4 +RESET4 production bindings verified')
