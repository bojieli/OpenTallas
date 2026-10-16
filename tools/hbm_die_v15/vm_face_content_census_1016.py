#!/usr/bin/env python3
"""Count actual hierarchical VM bank replicas and candidate content area."""
import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    path=Path('/home/ubuntu/wt/hnl-0030/results/arch/hbm_die_v16/source_compact_0253/contract.json');raw=path.read_bytes();c=json.loads(raw)
    source='rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_static.sv';slice_source='rtl/hbm_accel/generic/vm/static/ot_vms_slice_static.sv'
    get=lambda p:subprocess.check_output(['git','-C',str(ROOT),'show','a89a10d1f:'+p]);wrapper=get(source);sl=get(slice_source)
    assert b'for(b=0;b<8;b=b+1)begin:g_bank' in sl and b'end else begin:g_historical_bank' in sl
    grant=json.loads((ROOT/'results/arch/hbm_die_v15/vm_native_face_grants_1016.json').read_text());rows=[]
    for qi,q in enumerate(['SW','SE','NW','NE']):
        inst='hb_vms_'+q;i=c['instances'][inst];assert i['source']==source and i.get('params',{}).get('STRAP_BANKS',0)==0
        for b in range(8):rows.append(dict(quadrant=q,bank=b,current_parent_instance=inst,current_hierarchical_path=f'{inst}.u_slice.g_bank[{b}].g_historical_bank.u_bank',current_master='ot_vms_bank_static',candidate_source=grant['slots'][qi]['source'],candidate_source_sha256=grant['slots'][qi]['source_sha256'],candidate_master=grant['slots'][qi]['cell'],candidate_outline_um=[270,313.2],prior_nine_root_outline_um=[270,270],area_delta_mm2=.011664))
    homes=[]
    for plan in ['core4_sfu2','core4_sfu2_wide']:
        p=json.loads((ROOT/'results/arch/hbm_die_v15'/plan/'compact.P.json').read_text())
        for r in rows:
            slot='vmb_'+r['quadrant']+str(r['bank']);b=p[slot];ox=round((b['w']-270)/2/2.16)*2.16;oy=round((b['h']-313.2)/2/2.16)*2.16
            assert ox>=0 and oy>=0 and ox+270<=b['w'] and oy+313.2<=b['h']
            homes.append(dict(plan=plan,planning_slot=slot,hierarchical_path=r['current_hierarchical_path'],candidate_local_offset_um=[ox,oy],candidate_rect_um=[b['x']+ox,b['y']+oy,270,313.2],parent_slot_outline_um=[b['w'],b['h']],scope='containment proposal only; current source does not instantiate face master or these homes'))
    out=dict(schema='opentallas.hbm.vm_face_content_census.v1',qualification='CONTENT_AREA_AND_CONTAINMENT_ONLY_NO_PARENT_ADOPTION',contract_sha256=hashlib.sha256(raw).hexdigest(),source_ref='a89a10d1f',source_hashes={source:hashlib.sha256(wrapper).hexdigest(),slice_source:hashlib.sha256(sl).hexdigest()},logical_bank_count=len(rows),candidate_clock_entries=15*len(rows),candidate_soft_clock_entries=12*len(rows),candidate_raw_macro_clock_entries=3*len(rows),prior_nine_root_clock_entries=9*len(rows),extra_entries_vs_nine_root=6*len(rows),current_bank_clock_sources=[r for r in c['clock_resets'] if r['instance'].startswith('hb_vms_') and r['port']=='clk_bank'],current_sram_macro_count=3*len(rows),prior_content_area_mm2=len(rows)*270*270/1e6,new_content_area_mm2=len(rows)*270*313.2/1e6,content_delta_mm2=len(rows)*.011664,banks=rows,planning_containment_homes=homes,open=['actual parent source dispatch to new face masters','NE source unification to actual q2 master if sharing measured q2 view','native face-clock TT/FF/DRC and clock delivery','parent pin/wire/PG/root topology and complete cuts','actual whole-die area packing; no area credit claimed'])
    outpath=ROOT/'results/arch/hbm_die_v15/vm_face_content_census_1016.json';outpath.write_text(json.dumps(out,indent=1)+'\n');print({k:v for k,v in out.items() if k not in ['source_hashes','banks','planning_containment_homes','open']})
if __name__=='__main__':main()
