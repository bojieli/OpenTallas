#!/usr/bin/env python3
"""Candidate-only head HOST provider: explicit bootstrap/HBC dates and job-active wire.
Writes a copy; the die plan owner composes this with the controller and infra delta.
HBC1 admission defaults stay invalid until the compiler supplies real dates.
"""
import argparse,copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s81_head'))
# Keep this closure usable in a staged RTL-only vehicle; importing the plan
# composer would load die-plan tools even for source-list-only lint.
MESH_SOURCES=['rtl/link/ot_link_crc32.sv', 'rtl/lib/ot_rst_relay_tree3.sv', 'rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv', 'rtl/lib/ot_sram_oldread_b64.sv', 'rtl/lib/ot_sram_showahead_b64.sv', 'rtl/common/ot_link_credit_rx_b64.sv', 'rtl/common/ot_link_credit_tx_rc.sv', 'rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe4.sv', 'rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_safe3.sv', 'rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv', 'physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v', 'physical/asap7_memory_macros_v2/ot_sram_1r1w2c_256x64_m1/ot_sram_1r1w2c_256x64_m1.v', 'rtl/dsrom_sys/s81_head/ot_s81hd_util.sv', 'rtl/dsrom_sys/s81_head/ot_s81hd_lsc_parts.sv', 'rtl/dsrom_sys/s81_head/ot_s81hd_beat_link.sv', 'rtl/dsrom_sys/s81_head/ot_s81hd_best64.sv', 'rtl/dsrom_sys/s81_head/ot_s81hd_mesh_ep_core.sv']
HOSTB='rtl/dsrom_sys/s81_dv/hostb/'
HBC_FILES=['dsdv_hostb_hold.sv','dsdv_hostb_crc512.sv','dsdv_hostb_rx.sv','dsdv_hostb_tx.sv','dsdv_hostb_stage.sv','dsdv_hbc1_loader.sv','dsdv_hbc1_affine_book.sv','dsdv_hostb_stage_hbc.sv']
SOURCES=list(dict.fromkeys(MESH_SOURCES+['rtl/lib/ot_reset_sync.sv']+[HOSTB+p for p in HBC_FILES]+['rtl/dsrom_sys/s81_head/ot_s81hd_host276.sv','rtl/dsrom_sys/s81_head/ot_s81hd_host_ep_core.sv']))

def apply(base,params=None):
 p=copy.deepcopy(base)
 t=p['partition_types']['hd_host']
 if len(t['contents'])!=1 or t['contents'][0]['module'] not in ('ot_s81hd_host_ep','ot_s81hd_host_ep_core'):
  raise ValueError('HOST content changed; recompose explicitly')
 t['contents']=[dict(inst='u_core',module='ot_s81hd_host_ep_core',status='new',bind={'ck':'clk','rst_n':'rst_n','start_i':'start'},params=params or {},note='Two real safe8 lanes + HBC1 HOST_FRAMES authority loader/book + exact host276 codecs; S81 HBE consumer omitted. Compiled dates required; default not admitted.')]
 t['sources']=SOURCES
 t.setdefault('reset',{})['start_role']='bootstrap'
 p.setdefault('reset',{})['start']='broadcast'
 # h_tx[276] is the actual ctl job-active signal; every spine segment carries it.
 for tn,typ in p['partition_types'].items():
  for b in typ.get('buses',[]):
   if (tn=='hd_host' and b['name']=='h_tx_i') or (tn=='hd_ctl' and b['name']=='h_tx_o') or b['name'] in ('hd_i','hd_o'):
    if b['width'] not in (276,277):raise ValueError(f'{tn}.{b["name"]}: unexpected width')
    b['width']=277
  for ft in typ.get('ft_slots',[]):
   if ft['name']=='hd':
    if ft['width'] not in (276,277):raise ValueError('hd feedthrough width changed')
    ft['width']=277
 for lane in p['ports']:
  if lane['id'].startswith('host_tx__'):
   if lane['width'] not in (276,277):raise ValueError('host TX width changed')
   lane['width']=277
 return p

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('base',type=Path);ap.add_argument('--out',required=True,type=Path);ap.add_argument('--params',type=Path)
 a=ap.parse_args()
 if a.base.resolve()==a.out.resolve():raise SystemExit('refusing canonical overwrite')
 p=apply(json.loads(a.base.read_text()),json.loads(a.params.read_text()) if a.params else None)
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(p,indent=2)+'\n')
 print('HEAD_HOST_DELTA candidate only; compiled boot dates, clock/geometry, ctl and token gates remain')
if __name__=='__main__':main()
