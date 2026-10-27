#!/usr/bin/env python3
"""Candidate current HEAD control/LEP source delta; canonical plan never mutated.

Makes the head-only no-index contract real (the old idx wrapper default is1,
contrary to the historical lane note), and exposes actual MU landing accepted
beats on a live11-bit notification bus. Requires source geometry/infra re-plan.
"""
import argparse,copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/die_plan'));sys.path.insert(0,str(ROOT/'tools/s81_head'))
from gen import latency_table
from schema import Plan
import head_rtl_plan_delta as prior
T='rtl/dsrom_sys/s81_head/'
CTL_SOURCES=list(dict.fromkeys(prior.MESH_SOURCES+[
 T+'ot_s81hd_ctl_core.sv',T+'ot_s81hd_ctl_hsf0_static.sv',T+'ot_s81hd_static_issue.sv',T+'ot_s81hd_host276.sv',
 'rtl/dsrom_sys/mtp/dsfd_mtp_tops.sv','rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv','rtl/dsrom_sys/mtp/ot_dsrom_mtp_seq.sv',
 'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v']))

def apply(base,closure):
 p=prior.apply(copy.deepcopy(base),closure)
 ctl=p['partition_types']['hd_ctl'];lep=p['partition_types']['hd_lep0N']
 ctl['contents']=[dict(inst='u_core',module='ot_s81hd_ctl_core',status='new',bind={'ck':'clk','rst_n':'rst_n','start_i':'start'},
  note='HSF0 exact rank/result/MTP, START-date authority, HOST276/mesh64 codecs; MTP DHRES provider still required')]
 ctl['sources']=CTL_SOURCES
 lep['contents'][0]['module']='ot_s81hd_lep0N_noidx_core'
 lep['contents'][0]['note']='Head-specific IDX_EN0; omitted H4 inputs structurally unread; actual MU landing notification lw_o'
 for ty,dead in ((ctl,{'tl_o','ca_i','cb_i'}),(lep,{'tl_i','ca_o','cb_o'})):
  ty['buses']=[b for b in ty['buses'] if b['name'] not in dead]
 drop={'h4_tl__0','h4_ca__0','h4_cb__0'}
 p['ports']=[x for x in p['ports'] if x['id'] not in drop]
 for lane in p['lanes']:lane['ports']=[n for n in lane['ports'] if n not in drop]
 p['lanes']=[l for l in p['lanes'] if l['ports']]
 for ty,name,direction,face in ((lep,'lw_o','out','E'),(ctl,'lw_i','in','W')):
  if not any(b['name']==name for b in ty['buses']):
   ty['buses'].append(dict(name=name,dir=direction,width=11,kind='ctl',leaf='u_core.'+name,face=face,
    window_um=[1104.624,1124.736],layers=['M4','M6'],order='lsb_low'))
 if not any(x['id']=='head_lep_landing__0' for x in p['ports']):
  p['ports'].append(dict(id='head_lep_landing__0',src=dict(part='lep0N',bus='lw_o'),dst=dict(part='ctl',bus='lw_i'),width=11,kind='ctl'))
  p['lanes'].append(dict(id='head_lep_landing',ports=['head_lep_landing__0']))
 p['reset']['start']='broadcast';ctl.setdefault('reset',{})['start_role']='bootstrap'
 for tn,bn in (('hd_ctl','h_tx_o'),('hd_host','h_tx_i')):
  bus=next(b for b in p['partition_types'][tn]['buses'] if b['name']==bn)
  if bus['width'] not in (276,277):raise ValueError('unexpected host lane width')
  bus['width']=277
 for port in p['ports']:
  if port['id'].startswith('host_tx__'):port['width']=277
 for slot in p['partition_types']['hd_spn'].get('ft_slots',[]):
  if slot['name']=='hd':slot['width']=277
 p['latency']=dict(lanes=latency_table(Plan(p)))
 return p

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base',type=Path,required=True);ap.add_argument('--closure',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 if a.base.resolve()==a.out.resolve():raise SystemExit('refusing canonical in-place mutation')
 p=apply(json.loads(a.base.read_text()),json.loads(a.closure.read_text()));a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(p,indent=2)+'\n')
 print('HEAD_CONTROL_DELTA candidate only; clock/geometry/bind/token gates remain open')
