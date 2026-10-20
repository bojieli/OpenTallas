#!/usr/bin/env python3
"""Prepare an observational full-six coupon; never compile or run it here."""
from pathlib import Path
import json, re, hashlib
from head_local_contract import ROOT

b=ROOT/'results/rtl/s81_qf_producer_1019/sid6_vehicle'
out=b/'fullsix_launch_packet'
original=(b/'input_source_ledger_result/pins04/tb_input_source_ledger.sv').read_text()
t=original[:original.index('\n\nwire[6605:0]input_words;')]
t=t.replace('module tb_input_source_ledger;', 'module tb_fullsix_trace;')
t=t.replace('wire is_v;wire', 'wire cap_cfg_v;wire[159:0]cap_cfg_d;\nwire is_v;wire')
t=t.replace('.is_v(is_v),.is_d(is_d),.fault(fx)', '.is_v(is_v),.is_d(is_d),.cfg_v(cap_cfg_v),.cfg_d(cap_cfg_d),.fault(fx)')
t=t.replace('wire c_v,sw_v;', 'wire[9:0]cw_v;wire[119:0]cw_a;wire[319:0]cw_d;\nwire[1:0]cw2_v;wire[23:0]cw2_a;wire[63:0]cw2_d;\nwire c_v,sw_v;')
t=t.replace('#(.W(436),.D(4)) dn', '#(.W(526),.D(4)) dn')
t=t.replace('.d({cv[2],cd,swv[2]', '.d({cw_v[4+:2],cw_a[48+:24],cw_d[128+:64],cv[2],cd,swv[2]')
t=t.replace('.q({c_v,c_d,sw_v', '.q({cw2_v,cw2_a,cw2_d,c_v,c_d,sw_v')
t=t.replace('.cw_v(2\'b00), .cw_a(24\'d0), .cw_d(64\'d0)', '.cw_v(cw2_v), .cw_a(cw2_a), .cw_d(cw2_d)')
t=t.replace('if(u_p.wv[0]||u_p.wv[1])begin nw++;', 'if((u_p.wv[0]||u_p.wv[1]) && n<ORIGIN+1300)begin nw++;')
t=t.replace('  probe_finish();\n  if(err)$fatal(1,"INPUT_SOURCE_LEDGER_FAIL errors=%0d",err);\n  $display("INPUT_SOURCE_LEDGER_SOURCE_PASS raw1280 codes1280 scales40 sourcewrites320 gathers20 actualepochs15");$finish;',
'''  $display("FULLSIX_SOURCE_CHECK errors=%0d rawwrites=%0d gathers=%0d epochs=%0d",err,nw,nq,gos);
  $display("FULLSIX_PREPARATORY_TRACE_END CAPfault=%b landfaults=%b otherVPfaults=%b no_numeric_PASS nativephase_NULL",cap_fault,return_landing_fault,other_vp_fault);
  if(err)$fatal(1,"FULLSIX_RAW_SOURCE_FAIL errors=%0d",err);
  $finish;''')
t+='''
// First trace retains the actual CAP reset state. No host-selected tag/rbase.
// CFG and drain faults are recorded and remain failures; no numeric qualification.
wire[559:0]frame_return,cap_return;wire[3:0]return_landing_fault;
wire cap_fault;wire[4:0]other_vp_fault;
selected_fullsix_cone fullcone(.clk(clk),.rst_n(rst_n),.source_word(actual_source_word),.rt(frame_return),.return_landing_fault(return_landing_fault));
ot_s81sl_rly #(.W(560),.D(6)) dr(.clk(clk),.d(frame_return),.q(cap_return));
ot_s81sl_cap cap(.clk(clk),.rst_n(rst_n),.rt_w(cap_return[279:0]),.rt_e(cap_return[559:280]),
 .cfg_v(cap_cfg_v),.cfg_d(cap_cfg_d),.cw_s_v(cw_v[5:0]),.cw_s_a(cw_a[71:0]),.cw_s_d(cw_d[191:0]),
 .cw_n_v(cw_v[9:6]),.cw_n_a(cw_a[119:72]),.cw_n_d(cw_d[319:192]),.fault(cap_fault));
assign other_vp_fault[2]=fp;
'''
vp_monitor=[]
for k in range(5):
 if k==2:
  vp='u_p'
 else:
  vp=f'leaf{k}.u_p'
  t+=f'''if (1) begin:leaf{k}
 wire cvk,swvk;wire[159:0]cdk;wire[9:0]swak;wire[7:0]swmk;wire[255:0]swdk;
 wire[1:0]cwvk;wire[23:0]cwak;wire[63:0]cwdk;
 ot_s81sl_rly #(.W(526),.D(4)) dl(.clk(clk),
 .d({{cw_v[{2*k}+:2],cw_a[{24*k}+:24],cw_d[{64*k}+:64],cv[{k}],cd,swv[{k}],swa[{10*k}+:10],swm[{8*k}+:8],swd[{256*k}+:256]}}),
 .q({{cwvk,cwak,cwdk,cvk,cdk,swvk,swak,swmk,swdk}}));
 ot_s81sl_vp u_p(.clk(clk),.rst_n(rst_n),.c_v(cvk),.c_d(cdk),.sw_v(swvk),.sw_a(swak),.sw_m(swmk),.sw_d(swdk),
 .cw_v(cwvk),.cw_a(cwak),.cw_d(cwdk),.lo_v(),.lo_d(),.s_v(),.s_d(),.x_rv(1'b0),.x_ra(10'd0),.x_qv(),.x_qd(),
 .x_wv(1'b0),.x_wa(10'd0),.x_wm(8'd0),.x_wd(256'd0),.hw_v(),.hw_j(),.hw_hf(),.hw_d(),.hr_v(),.hr_j(),.hr_hf(),
 .hq_v(1'b0),.hq_d(256'd0),.n_go(),.n_pre(),.m_v(),.m_q(),.m_b(),.m_i(),.wl_v(),.wl_i(),.wl_d(),.fault(other_vp_fault[{k}]));
 end
'''
 t+=f'''always @(posedge clk)if(rst_n && ({vp}.cwv_c!=0||{vp}.cv_c||{vp}.re_e||{vp}.re_o||{vp}.fault))
 $display("VP_DRAIN t=%0d leaf={k} cw=%b cwa=%h cmd=%b srun=%b reads=%b%b raddr=%0d,%0d fault=%b",($time/834)-ORIGIN,{vp}.cwv_c,{vp}.cwa_c,{vp}.cv_c,{vp}.srun,{vp}.re_o,{vp}.re_e,{vp}.ra_e,{vp}.ra_o,{vp}.fault);
'''
 for bank in range(2):
  t+=f'''always @(posedge clk)if(rst_n && {vp}.wv[{bank}])begin
 $display("VP_ACTUAL_COMMIT t=%0d leaf={k} bank={bank} row=%0d mask=%h data=%h cwv=%b collision=%b",($time/834)-ORIGIN,{vp}.wa[{bank}],{vp}.wm[{bank}],{vp}.wd[{bank}],{vp}.cwv_c,{vp}.wcol);
end
'''
t+='''reg[31:0]cap_prev=0;
always @(posedge clk)begin
 if(rst_n)begin
  if(cap_cfg_v)$display("ACTUAL_CAP_CFG t=%0d body=%h",($time/834)-ORIGIN,cap_cfg_d);
  for(integer l=0;l<6;l++)begin
   if(frame_return[70*l+1])$display("FRAME_RETURN t=%0d lane=%0d word=%h",($time/834)-ORIGIN,l,frame_return[70*l+:70]);
   if(cap_return[70*l+1])$display("CAP_ARR t=%0d lane=%0d word=%h",($time/834)-ORIGIN,l,cap_return[70*l+:70]);
  end
  if(cap.g_hard.u_rt.fa_v||cap.g_hard.u_rt.fb_v||cap.g_hard.u_rt.any_open||cap_prev!={cap.g_hard.u_rt.fcause,cap.g_hard.u_rt.any_open,15'd0})begin
   $display("CAP_LIFETIME t=%0d fa=%b/%h fb=%b/%h open=%b f5=%b f6=%b f7=%b f8=%b f9=%b f11=%b causes=%h rbase=%h rcnt=%0d",($time/834)-ORIGIN,
   cap.g_hard.u_rt.fa_v,cap.g_hard.u_rt.fa_t,cap.g_hard.u_rt.fb_v,cap.g_hard.u_rt.fb_t,cap.g_hard.u_rt.any_open,
   cap.g_hard.u_rt.f5,cap.g_hard.u_rt.f6,cap.g_hard.u_rt.f7,cap.g_hard.u_rt.f8,cap.g_hard.u_rt.f9,cap.g_hard.u_rt.f11,cap.g_hard.u_rt.fcause,cap.g_hard.u_rt.c_rbase,cap.g_hard.u_rt.c_rcnt);
  end
  cap_prev={cap.g_hard.u_rt.fcause,cap.g_hard.u_rt.any_open,15'd0};
  if(|cw_v)$display("ACTUAL_CW t=%0d valid=%h addr=%h data=%h",($time/834)-ORIGIN,cw_v,cw_a,cw_d);
 end
end
'''
frames=json.loads((b/'selected_vehicle_image_manifest.json').read_text())['frames']
mon=[]
for f in frames:
 name=f['frame'];h='fullcone.'+name+('.u_f' if '_MX' in f['master'] else '')
 for k in f['physical_q']:
  c=f'{h}.u_s{k}';e=f'{h}.u_e{k}';q=e+'.u_e';p=q+'.u_pq'
  assert k in f['physical_q']
  mid=f'{name}_q{k}';mon.append(dict(id=mid,cfg7=c,wrapper=e,backend=q,tagger=p))
  t+=f'''if (1) begin:observe_{mid}
 reg[15:0]prevstate=0;reg oldbank;reg oldgo;reg[1:0]oldtag;
 always @(posedge clk)begin
  oldbank={p}.wbank;oldgo={q}.go_e;oldtag={q}.go_tag_e;
  if(rst_n)begin
   if({c}.lc[0]||{c}.go_x||{c}.go_e||{c}.cfg[0]||{c}.st!=0)
    $display("CFG7_TRACE t=%0d id={mid} lc=%h go_x=%b counter=%0d go_e=%b outtag=%0d ef=%b st=%b",($time/834)-ORIGIN,{c}.lc,{c}.go_x,{c}.tag,{c}.go_e,{c}.go_tag,{c}.ef,{c}.st);
   if({e}.go||oldgo||{e}.cfg_v||prevstate!={{{e}.bank_free,{e}.sh_free,{q}.walk_busy,{p}.walking,{p}.sh_full,{p}.settle,{p}.wbank,({p}.gcnt[0]==0),({p}.gcnt[1]==0),{p}.fault,4'd0}})
    $display("Q_LIFETIME t=%0d id={mid} go_pin=%b pin_tag=%0d go_e=%b tag_e=%0d wbank=%b otags=%0d,%0d bankfree=%b shfree=%b walk=%b/%b shadow=%b settle=%0d gcnt=%0d,%0d cfg=%b a=%0d data=%h swap=%b fault=%b",($time/834)-ORIGIN,
    {e}.go,{e}.go_tag,oldgo,oldtag,oldbank,{p}.otag[0],{p}.otag[1],{e}.bank_free,{e}.sh_free,{q}.walk_busy,{p}.walking,{p}.sh_full,{p}.settle,{p}.gcnt[0],{p}.gcnt[1],{e}.cfg_v,{e}.cfg_a,{e}.cfg_d,{p}.swap,{e}.fault);
   prevstate={{{e}.bank_free,{e}.sh_free,{q}.walk_busy,{p}.walking,{p}.sh_full,{p}.settle,{p}.wbank,({p}.gcnt[0]==0),({p}.gcnt[1]==0),{p}.fault,4'd0}};
   if(|{e}.pv)$display("ACTUAL_PAIR_PV t=%0d id={mid} valid=%b rows=%h vals=%h seg=%h nseg=%h err=%b pos=%h",($time/834)-ORIGIN,{e}.pv,{e}.prow,{e}.pval,{e}.pseg,{e}.pnseg,{e}.perr,{e}.ppos);
  end
  #2;
  if(rst_n && oldgo)$display("ACTUAL_TAG_CAPTURE t=%0d id={mid} bank=%b sampled=%0d captured=%0d",($time/834)-ORIGIN,oldbank,oldtag,{p}.otag[oldbank]);
 end
end
'''
t+='endmodule\n'
assert 'probe_finish' not in t and 'selected_input_cone' not in t
(out/'tb_fullsix_trace.sv').write_text(t)
(out/'trace_points.json').write_text(json.dumps(dict(scope='Observations only, no counters drive design tags/EF/CFG; first trace no numericPASS',actual_q_pairs=mon,actual_pairs=len(mon),CAP_unconfigured_reset_state=True,all15_original_reader_epochs=True,unconnected_extensions='Leaves0/1/3/4 VS/VN seams inactive because original private CTL only targets leaf2; no fabricated readiness or returns'),indent=2)+'\n')
assert len(mon)==72
print('PREPARED fullsix trace source, actual72 cfg7/Q/tagger monitors; no build')
