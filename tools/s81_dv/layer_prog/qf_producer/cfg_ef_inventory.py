#!/usr/bin/env python3
"""Read-only real cfg7/EF/control cone inventory; no readiness surrogate."""
from pathlib import Path
import subprocess,json,re,hashlib
from head_local_contract import ROOT
ref='ceaed19c4';base=ROOT/'results/rtl/s81_qf_producer_1019/sid6_vehicle'
paths=['rtl/v41die/ot_s81_cfg7_seq.sv','rtl/v41rom/ot_v41_elem_pq_tags.sv','rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv','rtl/v41rom/ot_v41_rom_elem_qx_pq_w10.sv',
 'rtl/dsrom_sys/s81_dv/frame_l4/col_h9_l4.sv','rtl/dsrom_sys/s81_dv/frame_l4/col_h10_l4.sv']
ss={p:subprocess.check_output(['git','show',ref+':'+p]).decode() for p in paths}
def conns(line):return dict(re.findall(r'\.(\w+)\(([^()]*)\)',line))
norm=lambda s:re.sub(r'\s+','',s)
masters=[]
for master in ['col_h9_l4','col_h10_l4']:
 lines=ss['rtl/dsrom_sys/s81_dv/frame_l4/'+master+'.sv'].splitlines()
 qs=[l for l in lines if 'ot_v41_rom_elem_q_qxpq_w10 #' in l]
 cals=[l for l in lines if 'ot_s81_cfg7_seq #' in l];rec=[]
 for qline in qs:
  q=conns(qline);k=int(re.search(r'\) u_e(\d+) ',qline).group(1));ef=norm('{'+q['bank_free']+','+q['sh_free']+'}')
  matches=[l for l in cals if norm(conns(l)['ef'])==ef];assert len(matches)==1
  cal=conns(matches[0]);assert norm(q['go_tag'])==norm(cal['go_tag'])
  rec.append(dict(pair=k,cfg_instance=re.search(r'\) (u_\w+) ',matches[0]).group(1),ef=cal['ef'],
   element_bank_free=q['bank_free'],element_sh_free=q['sh_free'],real_go_tag=q['go_tag'],
   element_go=q['go'],cfg7_go=cal['go_e'],go_same_net=norm(q['go'])==norm(cal['go_e']),
   ef_direct_source_binding=True,go_tag_direct_source_binding=True))
 assert len(rec)==12
 masters.append(dict(master=master,q_pairs=rec))
qtext=ss['rtl/v41rom/ot_v41_rom_elem_qx_pq_w10.sv']
assert 'parameter integer DRAIN = 127' in qtext
wrapper=ss['rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv'];assert '.DRAIN(' not in wrapper
rec=dict(scope='Read-only actual source/control inventory; no cfg7 runtime coupon or fullsix frontend',source_ref=ref,
 files=[dict(path=p,sha256=hashlib.sha256(v.encode()).hexdigest(),bytes=len(v.encode())) for p,v in ss.items()],masters=masters,
 actual_six_q_cfg7_pairs=72,actual_six_q_weight_ROMs=288,actual_cfg_ROMs_for_q=504,
 tag_rule='cfg7 tag reset0, increments every GO broadcast before classgate, output pin go_tag; direct same tag nets into element',
 EF_rule='actual element registered bank_free/sh_free directly drive own cfg7 ef; never replace by always-free constants',
 bank_free_state='gcnt[nbank]==0; nbank reflects go swap; gcnt refreshed to actualDRAIN127 on go or walk_busy and counts down otherwise',
 shadow_state='sh_full set by final CFG word; clears on actualswap when !walking&&!go_e; settle and swap ownership remain live',
 walk_busy='w_run | n_run | bn_run | i1_v | i2_v | (BP!=0 && bp_hold!=0)',
 registered_export='st_bank_free additionally masks go_pin/go; registered st_sh_free/st_walking and optional QM>=6 walking second stage',
 actual_Q_DRAIN=127,BF_DRAIN200_is_different_profile=True,
 control_cone_inputs=['actual CFG image words/classes/address/bank/swap','actual GO/tag and original pin/register stages',
 'actual source xstream valid/block/index/half metadata and walking/need/issue machinery','real local reset and gate/pin/slot-clock ownership'],
 no_CAP_feedback_into_Q_EF=True,
 minimal_coupon_options=[dict(name='Independent control extraction',
  required='Exact backward cone through qx_pq walker/need/issue/bank/swap/tagger/registeredEF and CFG pins, with source correspondence proving arithmetic/ROMcode data independence',
  eliminated_claim='Cannot substitute assumed walking or tiedEF; source cone not yet extracted/proved',new_hardware=0,CPP_and_RSS=None),
  dict(name='Six real q-elements/control loops',q_elements=6,weight4096x274_ROMs=24,cfg4096x72_ROMs=42,
   required='Actual selected slot ingress+cfg7+real full q element, original weights/config/source and true EF, no syntheticready',
   scope='Only six chosen pair control coupons; cannot qualify all72pair skew/tagdelivery, fullsixnumeric, CAP orVPdrain',
   duplicate_build_cost='Likely separate compile before eventual fullsix; actual peak unknown',new_hardware=0),
  dict(name='Actual fullsix integrated frontend',q_elements=72,all_frame_ROMs=1012,
   required='Use existing selected source/images inventory, retain all actual EF/CFG/tag/return/CAP/VP loops and instrument sequentially',
   scope='Only route that directly measures all72 runtime tag/EF and512rowCAP/VPdrain together; requiresROOTselection/admission prerequisites',
   CPP_and_RSS=None,new_hardware=0)],
 unproved_by_control_coupon=['All72 physicalslot/go delivery','Actual fullframe emissions and6returnARR phases',
 'CAPpartial-store/decoder/CW/VPcommit and atomic per-epochRBASE install','Original tokendeadline and production/MU/nativephase'],
 native_phase=None,actual_CFG_rbase_dates=None,actual_CAP_VP_drain_dates=None,source_selected=False)
(base/'cfg_ef_control_inventory.json').write_text(json.dumps(rec,indent=2)+'\n')
print('CFG_EF_INVENTORY_ONLY actual72directEF/tagloops, DRAIN127; no syntheticreadiness/controlcoupon/fullsixbuild')
