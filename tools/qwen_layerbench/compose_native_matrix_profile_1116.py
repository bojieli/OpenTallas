#!/usr/bin/env python3
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();P=args.out.parent;P.mkdir(parents=True,exist_ok=True)
paths={'tile':'results/rtl/qc_tile_age_1116/qualification.json','stn':'results/rtl/qc_stn55_1116/qualification.json','round':'results/rtl/qc_round96_1116/qualification.json','cb':'results/rtl/qc_mat_native_1116/cb_graph/source_graph_diagnostic.json','xhead':'results/rtl/qc_xhead_native_1116/xhead_ages.json'}
r={k:json.loads((ROOT/v).read_text()) for k,v in paths.items()}
assert r['tile']['status']=='PASS_TIMING_COMPONENT' and r['tile']['GO_to_first_valid_receiver']==51
assert r['stn']['status']=='PASS_COMPONENT_CANDIDATE' and r['round']['status']=='PASS_COMPONENT_CANDIDATE'
assert r['round']['head']['PH_IK_RSEL_sequences_equal'] and all(v['sequence_equal'] for v in r['round']['tile'].values())
assert r['round']['station']['late_pin_lead']==6 and r['round']['station']['flat_command_to_pin']==3
assert r['cb']['root']==165 and r['cb']['rs_feedthrough']==29 and r['cb']['bco']==[26]*4 and all(n['aligned'] for n in r['cb']['nodes'])
assert r['xhead']['d_head']==21
c=r['stn']['cases'];l8=c['o']['first_receiver_edge']-c['o']['far_final_first_receiver_edge'];l7=c['gu']['first_receiver_edge']-c['gu']['far_final_first_receiver_edge'];l9=c['qkv']['first_receiver_edge']-c['qkv']['NB_first_receiver_edge']+r['round']['station']['sender_neighbor_valid_age']
assert (l7,l8,l9)==(20,27,36)

q=dict(schema='opentallas.qwen.native-matrix-ages.v1',status='PASS_COMPONENT_COMPOSED',native_component_profile=True,slice_rtl='s8',source_scope='native_zero_parent_transport',memory_profile={'sram_if_mif':1,'relative_memory_alignment':3},
 l8_ar=30,ar_hop=2,xc_cc=3,command_to_stn_cfg=3,
 result_age={'vm':{'7':27,'9':43},'ar':{'8':30}},station_r_v={'7':20,'8':27,'9':36},
 stn_pin_lead={'qkv':61,'o':6,'gu':61,'down':6},stn_lead={'qkv':64,'o':9,'gu':64,'down':9},native_ar_hgd_base=2,
 tile=dict(d_clu=220,rs_age=0,round_period={'qkv':64,'o':96,'gu':256,'down':96},raw_prefix={'qkv':56,'o':8,'gu':248,'down':40},native_near=165,native_far=220,source_receipt='results/rtl/qc_tile_age_1116/qualification.json',stn_receipt='results/rtl/qc_stn55_1116/qualification.json'),
 tile_meas={},ledger={'native_tile':51,'CB_near':165,'CB_far':220,'near_far_skew':55,'frs_fn':0,'L8_station_result':27,'station_to_AR':3,'L7_station_first_result':20,'station_to_VM_MIF1':7,'L9_sender_to_neighbor_receiver':16,'neighbor_forwarding_native':0,'L9_neighbor_input_to_result':20,'XC_flat_command_to_output':3,'STN_flat_command_to_cfg_pin':3,'source_command_origin':'slice flat cmd_i receiver, D.Chain.cmd_arrival[0]=0','receiver_convention':'True posedge receiver-to-receiver edges; no producer-NBA ambiguity.'},
 required_source_selection=['STN cb55 explicit binder','OT_QC_AR_ROUND96 selected head and REGROOT3 tile','AR phase cache with HGD2+5s under native1-edge HR hops'],
 release_qualified=False,physical_qualified=False,installed=False,bound_parent_transport_included=False,
 limits=['Native architectural profile only; actual private N43 SU/MEM44 and bound transport compose separately.','LM/amax ages deliberately absent; require separate native profile.','AR phase cache qualification/selected source event is a separate dependency.'])
near_go = r['xhead']['d_head'] + r['cb']['root']
for n,pre,last,far in [('qkv',56,63,55),('o',8,207,55),('gu',248,255,55),('down',40,239,55)]:q['tile_meas'][n]=dict(first_rs=near_go,first_final=near_go+pre,last_final=near_go+last,far=far)
q['input_sha256']={k:hashlib.sha256((ROOT/v).read_bytes()).hexdigest() for k,v in paths.items()}
q['result_age']={'vm':{'7':l7+7,'9':l9+7},'ar':{'8':l8+3}}
args.out.write_text(json.dumps(q,indent=2)+'\n')
