#!/usr/bin/env python3
"""Promote literal WAKE intent on completed mapped cells; no synthesis or RTL edits."""
import argparse, copy, gzip, hashlib, json, subprocess
from pathlib import Path
from dsrom_noECC_wake_retained_map import wake_cells
from dsrom_noECC_mapped_element_join import buffer_tree
ROOT=Path(__file__).resolve().parents[1]
CONTAINER='dsrom-wake-retention-a910'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def semantic(n):
    x=copy.deepcopy(n)
    for m in x['modules'].values():
        for c in m.get('cells',{}).values():c.pop('attributes',None)
    return x

def annotation_only(original,after):
    if semantic(original)!=semantic(after):return False
    changed=[]
    for name,m in original['modules'].items():
        for k,c in m.get('cells',{}).items():
            a=c.get('attributes',{});b=after['modules'][name]['cells'][k].get('attributes',{})
            if a==b:continue
            if name!='ot_v41_rom_elem_w10' or not c['type'].startswith('DFF') or 'ot_v41_rom_elem_w10.sv:191.' not in a.get('src',''):return False
            if {k:v for k,v in b.items() if k not in ('keep','dont_touch')}!={k:v for k,v in a.items() if k not in ('keep','dont_touch')}:return False
            if not all(int(b.get(k,'0'),2)==1 for k in ('keep','dont_touch')):return False
            changed.append(k)
    return len(changed)==8

def restore_signed_labels(original,after):
    count=0
    for name,m in original['modules'].items():
        for k,v in m.get('netnames',{}).items():
            b=after['modules'][name]['netnames'][k]
            if v==b:continue
            if 'signed' not in v or 'signed' in b or k in m.get('ports',{}):raise ValueError('unexpected net/port serialization change')
            if {k:x for k,x in v.items() if k!='signed'}!=b:raise ValueError('net bits/attributes changed')
            b['signed']=v['signed'];count+=1
    return count

def run(work,out):
    prior=json.loads((work/'record.json').read_text())
    if prior['status']=='RUNNING':raise ValueError('do not consume a live producer')
    if len(prior['runs'])!=2 or any(r.get('returncode')!=0 for r in prior['runs']):raise ValueError('complete actual q/BF maps required')
    if out.exists():raise ValueError('immutable attempt output already exists')
    image=subprocess.check_output(['docker','inspect',CONTAINER,'--format','{{.Image}}'],text=True).strip()
    if image!=prior['container_image']:raise ValueError('tool image pin mismatch')
    out.mkdir();subprocess.run(['docker','exec',CONTAINER,'mkdir',str(out)],check=True)
    source=ROOT/'results/uarch/dsrom_noECC_complete_element_20261002/model.json'
    reserve=json.loads(source.read_text());oldbase=ROOT/'results/uarch/dsrom_noECC_complete_element_mapping_20261002/terminal_pair'
    prices=json.loads((oldbase/'inputs/clock_cell_prices.json').read_text())
    record={'source_mapping_record_sha256':digest(work/'record.json'),'source_mapping_commit':prior['source_commit'],'container_image':image,'cold_synthesis_runs':0,'engine_RTL_changes':0,'status':'PREPARING','cases':{}}
    write(out/'record.json',record)
    for r in prior['runs']:
        case=r['case'];d=out/case;d.mkdir();src=work/case/'mapped.json'
        if digest(src)!=r['mapped_json_sha256']:raise ValueError('mapped source hash changed')
        script='read_json '+str(src)+'\n'
        script+='select -set local_wake ot_v41_rom_elem_w10/a:src=*ot_v41_rom_elem_w10.sv:191.* ot_v41_rom_elem_w10/t:DFF* %i\n'
        script+='select -assert-count 8 @local_wake\nsetattr -set keep 1 -set dont_touch 1 @local_wake\nselect -clear\n'
        script+='write_json '+str(d/'mapped.json')+'\nwrite_verilog '+str(d/'mapped.v')+'\n'
        (d/'retention.ys').write_text(script);subprocess.run(['docker','cp',str(d),CONTAINER+':'+str(out)],check=True)
        with (d/'retention.log').open('w') as f:subprocess.run(['docker','exec',CONTAINER,'yosys','-Q','-T','-s',str(d/'retention.ys')],stdout=f,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['docker','cp',CONTAINER+':'+str(d)+'/.',str(d)],check=True)
        original=json.loads(src.read_text());after=json.loads((d/'mapped.json').read_text())
        labels=restore_signed_labels(original,after)
        write(d/'mapped.json',after)
        if not annotation_only(original,after):raise ValueError('Only keep/dont_touch on exactly8 source-owned real FF cells may change')
        actual=wake_cells(d/'mapped.json')
        if not actual['passed']:raise ValueError('eight actual retained FFcells and outputs required')
        e=copy.deepcopy(reserve['elements']['q_pair' if case=='q' else 'BF16_column_pair'])
        if case=='q':
            e['outline_DBU'][3]=151200;e['compute_control_clock_region_DBU'][3]=151200
        n=after['modules']['ot_v41_rom_elem_w10']
        profiles={}
        for corner,inv in r['inventory'].items():
            profiles[corner]={k:{**v,'BUF4_capacitance_only':buffer_tree(v['pin_cap_fF'],prices[corner])} for k,v in inv['clock_nets'].items()}
        cap={k:c for k,c in n['cells'].items() if c['type'].startswith('DFF') and 'ot_v41_rom_elem_w10.sv:746.' in c['attributes'].get('src','')}
        icg={k:c for k,c in n['cells'].items() if c['type'].startswith('ICG')}
        macros={k:c for k,c in n['cells'].items() if c['type']=='ot_rom_4096x274_m8'}
        if len(macros)!=4 or len(icg)!=8 or len(cap)!=1088:raise ValueError('full geometry/capture/clock instance census changed')
        record['cases'][case]={'unchanged_hardware_graph':True,'restored_original_internal_signed_labels':labels,'raw_mapping_sha256':digest(src),'retained_mapping_sha256':digest(d/'mapped.json'),'actual_WAKEDFF':actual,'actual_top_ports':n['ports'],'actual_macro_cells':macros,'actual_ICG_cells':icg,'actual_capture_FF_cells':cap,'SS_FF_pin_loads':profiles,'mapped_area_um2':r['inventory']['ss']['stdcell_area_um2'],'physical_geometry_contract':e,'capture_constraints':reserve['capture_constraints'],'parent_IO_requirements':reserve['boundary_constraints_source'],'physical_G0_admitted':False,'remaining_context':{'actual_CTS_clock_skew_and_minpulse':'Not installed; all root/leaf gating checks required','actual_PG_vias_and_pin_escape':'Source translated pin/OBS/halo and PDN template retained; actual installed union/spacing required','real_parent_IO_cells_arrival_slew_load':'Parent CFG/VM/root driving and receiving endpoints required; no zero IO','Maxwell_counts':'Replace q outline once +3310.2432um2/pair using actual complete-element count; BF fixed157.68um'}}
        write(out/'record.json',record)
    record.update(status='EIGHT_ACTUAL_WAKE_CELLS_RETAINED_CONTEXT_OPEN',physical_PnR_admitted=False,candidate=reserve['candidate'],geometry_source_sha256=digest(source),fixed_period_ps=833.3333333333334,SS_setup_ps=60,FF_hold_ps=25,added_cycles=0,ROM_macro_width=274,old_negative_evidence_unchanged=True)
    write(out/'record.json',record)
    return record
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.work,a.out)
