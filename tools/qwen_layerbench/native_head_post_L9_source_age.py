#!/usr/bin/env python3
"""Frozen W5->W4 real L9 word source-age evidence. No simulation or source mutation."""
import json,re,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent
W=json.loads((D/'wrappers.json').read_text());N=json.loads((D/'native_sources.json').read_text());S=json.loads((D/'sidecar_filtered.json').read_text());B=json.loads((D/'bus_groups_filtered.json').read_text());TOP=Path('/home/ubuntu/coord/tmp/codex-native-head-consumer-prep/qwen_compute_bound_top.sv');T=TOP.read_text()
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def lines(fn,needles):
 return [{'line':i,'source':l}for i,l in enumerate(W[fn].splitlines(),1)if any(n in l for n in needles)]
files=['slw_st_a_v2__clf4365a62.sv','qfd_qc_slw_fw.sv','qfd_qc_slw_stm.sv','qfd_qc_slw_sc__slw_sc_v3.sv','slw_fe_v2__clf110fab2.sv','slw_fw_v1__clf51c11d8__clc7ddab13.sv','slw_st_a_v1__clfc5867a6.sv']
# Physical ordinary register instances: parallel per-bit pads count once as a word age.
stages=[(files[0],'native_nb_publication_to_wrapper_output',1,['u_bout_x_fe_o']), (files[1],'W5_fw_FT',2,['u_ft_x_st_a_fe_o_']), (files[2],'W5_stm_FT',3,['u_ft_x_st_a_fe_o_']), (files[3],'W5_sc_FT',3,['u_ft_x_st_a_fe_o_']), (files[4],'W5_fe_input_boundary',1,['u_bin_x_st_a_i']), (files[4],'W5_fe_split_output_boundary',1,['u_bout_rd_eo','u_bout_rr_eo','u_bout_rv_eo']), (files[5],'W4_fw_split_input_boundary',1,['u_bin_rd_wi','u_bin_rr_wi','u_bin_rv_wi']), (files[5],'W4_fw_station_output_boundary',1,['u_bout_x_st_a_o']), (files[6],'W4_st_a_input_boundary',1,['u_bin_x_fw_i']), (files[6],'W4_st_a_nb_pad',10,['u_pd10_x_fw_i_0 ','u_pd10_x_fw_i_1 ','u_pd10_x_fw_i_2 '])]
r=[]
for fn,name,count,keys in stages:
 ls=lines(fn,keys);assert ls,(fn,name)
 if name.endswith('_FT'):assert len(ls)==count
 r.append({'wrapper':fn,'event':name,'ordinary_registered_stages':count,'actual_source':ls})
assert sum(x['ordinary_registered_stages']for x in r)==24
# Exact named parent clocks and literal straps for four count-aligned boundaries.
cas=[]
for inst,pin,portkey,kw in [('sl_W5_fw','x_st_a_fe_i','sl_W5_st_a__x_st_a_fe__0',20),('sl_W5_sc','x_st_a_fe_i','sl_W5_st_a__x_st_a_fe__2',10),('sl_W4_fw','rd_wi','sl_W5_fe__rd_eo_rd_wi__0',18),('sl_W4_st_a','x_fw_i','sl_W4_fw__x_fw_st_a__0',-17)]:
 tm=re.search(r'\n\s*(\w+)\s+'+inst+r'\s*\((.*?)\n\s*\);',T,re.S);assert tm
 body=tm[2];clk=re.search(r'\.clk\(([^)]+)\)',body)[1];sp=re.search(r'\.strap_ca_k_'+pin+r'\(6\x27b([01]+)\)',body)[1];assert int(sp,2)==kw%64
 ca=S['count_aligned_ports'][portkey];assert ca['K']==kw and ca['depth']==4
 fn=tm[1]+'.sv';m=re.search(r'^[ \t]*ot_dp_clk_landing_cas[ \t]*#\(([^\n]*)\)[ \t]+u_cland_'+pin+r'[ \t]*\((.*?)\);',W[fn],re.S|re.M);assert m
 cas.append({'parent_instance':inst,'wrapper':fn,'input_pin':pin,'literal_parent_clock':clk,'strap_bits':sp,'K_signed_sidecar':kw,'K_mod64':int(sp,2),'sidecar':ca,'actual_landing_source':m[0],'nominal_added_cycles':ca['sched_lat']})
# All five pieces of the native numerical L9 word share count/phase reference.
fwbody=re.search(r'\n\s*\w+\s+sl_W4_fw\s*\((.*?)\n\s*\);',T,re.S)[1]
for pin in ['rd_wi','re_wi','rl_wi','rr_wi','rv_wi']:
 assert f'.strap_ca_k_{pin}(6\'b010010)'in fwbody
 assert S['count_aligned_ports'][f'sl_W5_fe__{pin[:2]}_eo_{pin}__0']['K']==18
assert sum(x['nominal_added_cycles']for x in cas)==11
native_evidence={}
for fn,needles in [('rtl/qwen_dv/s5/s6/qfd_dv_s6_leaves.sv',['assign l9_o = l9_c;']),('rtl/qwen_dv/s5/s8/qfd_dv_s8_fdn_arf1.sv',['assign l9_c = l9_i[513:512];','assign l9_r0 = {l9_i[63:0]};'])]:
 s=N[fn]; assert all(q in s for q in needles)
 native_evidence[fn]={'sha256':sha(s),'combinational_no_extra_stage':[{'line':i,'source':l}for i,l in enumerate(s.splitlines(),1)if any(q in l for q in needles)]}
bus=[]
for obj in B['rows']:
 q=obj['row']
 if not isinstance(q,dict):continue
 ms=[m for m in q.get('members',[])if (q.get('sink')=='dvs_W5.u_core.u_sub.u_fup'and '.u_r0.nb_'in m.get('source',''))or(q.get('sink')=='dvs_W4.u_core.u_sub.u_fdn'and m.get('sink_port')=='l9_i')or(q.get('sink')=='dvs_W4.u_core.u_sub.u_r0'and m.get('sink_port','').startswith('nb_'))]
 if ms:bus.append({'sink':q['sink'],'src_part':q['src_part'],'members':ms})
result={'status':'SOURCE_ONLY_SELECTED_NEIGHBOR_WORD_AGE_CONTRACT','readset':{'selected_bound_top':{'path':str(TOP),'sha256':sha(T)},'wrappers':{f:sha(W[f])for f in files},'sidecar':{'path':S['path'],'sha256':S['sha256']},'bus_groups':{'path':B['path'],'sha256':B['sha256']},'native_sources':{f:sha(s)for f,s in N.items()}},'correction':'Native L9 numerical word uses rd/re/rl/rr/rv split bundles. l9_eo/l9_wi carries cmd/hr and must not stand in for the numerical neighbor word.','ordinary_register_events_to_receiver_pin':r,'ordinary_register_stage_count_to_receiver_pin':24,'count_aligned_boundaries':cas,'count_aligned_nominal_added_cycles':11,'nominal_schedule_contract':{'native_sender_nb_pin_publication_to_fup_l9_c':{'ordinary':10,'sidecar_CA_added':6,'total':16},'fup_l9_o_to_fdn_l9_i':{'ordinary':2,'sidecar_CA_added':3,'total':5},'fdn_l9_r0_c_to_receiver_nb_p':{'ordinary':12,'sidecar_CA_added':2,'total':14},'to_receiver_nb_p':35,'receiver_native_PIN_IN':1,'to_receiver_internal_nb_d_c':36,'qualification':'Nominal frozen sidecar schedule only, conditional on actual region count-origin/provider contract. Not measured source age or physical phase/CTS qualification.'},'bit_preserving_path_evidence':{'W5_fe_input_fup':lines(files[4],['.l9_c({x_st_a_i_q']), 'split_outputs':lines(files[4],['u_bout_rd_eo','u_bout_re_eo','u_bout_rl_eo','u_bout_rr_eo','u_bout_rv_eo']), 'W4_fdn_reassembly':lines(files[5],['.l9_i({rv_wi_q']), 'zero_stage_native_bodies':native_evidence,'r0_word_route':'sender nb_od[63:0] -> x_fe_o[65:2] -> fup l9_c/o[63:0] -> rd_eo[67:4] -> rd_wi_q[67:4] -> fdn l9_i/r0[63:0] -> x_st_a_o[65:2] -> receiver nb_d_p[63:0]','control_route':'sender nb_oc[0] -> fup l9_o[512] -> rr_eo[2] -> rr_wi_q[2] -> fdn l9_c[0]; nb_oc[1] -> l9_o513 -> rv_eo0 -> rv_wi_q0 -> fdn l9_c1'},'bus_group_selected_members':bus,'count_origin_contract':{'epoch':'Sender writer count n starts from t_rst_n forwarded with fclk; receiver m starts from local cland_start. All relevant CA macros DEPTH4, count width6, WFALL default0.','per_word_event_rule':'Let W(n) sample input d immediately before sender fclk rising edge n; let R(m) denote landing q immediately after receiver edge m. In the valid guarded epoch, q at R(m) is W(n) with n=(m-K) mod64. This is a count-label rule, not K elapsed cycles. Receiver following ot_dp_st captures prior q on its next local edge; that boundary register is already counted in ordinary stages.','no_double_count':'Do not add generic3 or K or a separate RDREG to the sidecar nominal ledger. CA q publication belongs to the count-aligned rule; the explicit succeeding boundary is listed once.','guards':'Lap/written/guard checks and ready/fault remain active. Source phase/count-origin qualification is required before converting this nominal ledger to production event times.'},'scope':'No RTL execution, no packet mutation, no aliasing regional clocks, no global source phase proof.','generator_sha256':sha(Path(__file__).read_text())}
(D/'selected_neighbor_source_age.json').write_text(json.dumps(result,indent=2)+'\n');print(D/'selected_neighbor_source_age.json',sha((D/'selected_neighbor_source_age.json').read_text()))
