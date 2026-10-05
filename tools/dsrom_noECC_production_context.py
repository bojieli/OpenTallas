#!/usr/bin/env python3
"""Bind complete existing maps to real physical masters and implementation names."""
import fnmatch,gzip,hashlib,json,re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_noECC_production_context_20261002'
PRIOR=ROOT/'results/uarch/dsrom_noECC_WAKE_cell_retention_20261002/terminal'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return gzip.decompress(p.read_bytes()).decode() if p.suffix=='.gz' else p.read_text()
def cells(text):
    pattern=r'(?P<attrs>(?:  \(\*[^\n]*\*\)\n)*)  (?P<master>\w+) (?P<name>\S+) +\(\n(?P<ports>.*?)^  \);'
    return [m.groupdict() for m in re.finditer(pattern,text,re.M|re.S)]
def actual_wake(cs):
    w=[c for c in cs if c['master'].startswith('DFF') and 'ot_v41_rom_elem_w10.sv:191.' in c['attrs']]
    if len(w)!=8 or len({c['name'] for c in w})!=8:raise ValueError('exact8 actual Verilog WAKE instances required')
    if not all('keep = ' in c['attrs'] and 'dont_touch = ' in c['attrs'] for c in w):raise ValueError('cell attributes required')
    return w
def lef_masters(text):
    out={}
    for m in re.finditer(r'^MACRO (\S+)\n(.*?)^END \1$',text,re.M|re.S):
        name,b=m.groups();size=re.search(r'SIZE ([\d.]+) BY ([\d.]+)',b)
        pins=[]
        for pm in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$',b,re.M|re.S):
            pn,pb=pm.groups();layer=None;rect=[]
            for line in pb.splitlines():
                lm=re.search(r'LAYER (\S+) ;',line)
                if lm:layer=lm[1]
                rm=re.search(r'RECT (.*?) ;',line)
                if rm:rect.append({'layer':layer,'bbox_DBU':[round(float(z)*1000) for z in rm[1].split()]})
            pins.append({'name':pn,'rectangles':rect,'use':re.search(r'USE (\w+)',pb)[1]})
        obs=[];layer=None
        if '  OBS\n' in b:
            for line in b.split('  OBS\n')[1].split('  END')[0].splitlines():
                lm=re.search(r'LAYER (\S+) ;',line)
                if lm:layer=lm[1]
                rm=re.search(r'RECT (.*?) ;',line)
                if rm:obs.append({'layer':layer,'bbox_DBU':[round(float(z)*1000) for z in rm[1].split()]})
        out[name]={'pins':pins,'OBS':obs,'size_DBU':[round(float(v)*1000) for v in size.groups()], 'area_um2':float(size[1])*float(size[2]), 'site':re.search(r'SITE (\S+) ;',b)[1], 'LEF_body':b}
    return out
def protection_tcl(names):
    if len(names)!=8 or len(set(names))!=8:raise ValueError('exact8 implementation instances required')
    lines=['# Eight source-owned cells in emitted Verilog; preserve through physical optimization.']
    for i,n in enumerate(names):
        n=n.removeprefix('\\')
        lines += [f'set w{i} [get_cells -hierarchical -regexp {{{"^"+re.escape(n)+"$"}}}]',f'if {{[llength $w{i}] != 1}} {{error "Missing unique mapped WAKE cell {i}"}}',f'set_dont_touch $w{i}']
    return '\n'.join(lines)+'\n'
def build():
    for r in json.loads((BASE/'inputs/receipts.json').read_text()):
        if sha(BASE/'inputs'/r['copy'])!=r['copy_sha256']:raise ValueError('physical source changed')
    policy=read(BASE/'inputs/platform.mk')
    patterns=[]
    for m in re.finditer(r'^export DONT_USE_CELLS\s*(?:\+=|=)\s*(.*)$',policy,re.M):patterns+=m[1].split()
    lef=lef_masters(read(BASE/'inputs/cells.lef.gz'))
    mapped=json.loads((PRIOR/'mapping_terminal.json').read_text());context=json.loads((PRIOR/'context_terminal.json').read_text());join=json.loads((PRIOR/'model.json').read_text());out={}
    for r in mapped['runs']:
        k=r['case'];cs=cells(read(PRIOR/k/'retained_mapped.v.gz'));counts=Counter(c['master'] for c in cs)
        if dict(counts)!=r['inventory']['ss']['master_counts']:raise ValueError('Verilog/JSON hardware census mismatch')
        w=actual_wake(cs);cap=[c for c in cs if c['master'].startswith('DFF') and 'ot_v41_rom_elem_w10.sv:746.' in c['attrs']]
        gates=[c for c in cs if c['master'].startswith('ICG')];rom=[c for c in cs if c['master']=='ot_rom_4096x274_m8']
        if (len(cap),len(gates),len(rom))!=(1088,8,4):raise ValueError('complete source scope required')
        used={n:v for n,v in counts.items() if n!='ot_rom_4096x274_m8'}
        if set(used)-set(lef):raise ValueError('mapped physical master unavailable')
        area=sum(lef[n]['area_um2']*v for n,v in used.items());a=r['inventory']['ss']['stdcell_area_um2']
        if abs(area-a)>1e-5:raise ValueError('physical LEF/Liberty area mismatch')
        widths={n:v for n,v in used.items() if lef[n]['size_DBU'][0]%54 or lef[n]['size_DBU'][1]!=270}
        if widths:raise ValueError('nonmatching literal site/row geometry')
        named={n:{'count':v,**{p:lef[n][p] for p in ('size_DBU','site','area_um2','pins','OBS')}} for n,v in used.items()}
        blocked={n:v for n,v in used.items() if any(fnmatch.fnmatchcase(n,p) for p in patterns)}
        geo=join['cases'][k]
        out[k]={'actual_Verilog_WAKEDFF':w,'actual_Verilog_captureDFF':cap,'actual_Verilog_ICG':gates,'actual_Verilog_ROM':rom,'named_physical_master_inventory':named,'physical_LEF_cell_union_area_um2':area,'Liberty_area_match':True,'site_width_DBU':54,'row_height_DBU':270,'default_dont_use_matches_existing_cells':blocked,'existing_instances_are_not_library_invalid':True,'production_entry':'Read committed retained_mapped.v, skip synthesis. Assert actual8 sourceWAKE names and set_dont_touch. Keep platformdontuse for NEW optimization choices; do not silently substitute/remove existing cells.','actual_top_ports':context['cases'][k]['actual_top_ports'],'clock_pin_loads_and_geometry_source':'../dsrom_noECC_WAKE_cell_retention_20261002/terminal/context_terminal.json','geometry_source_sha256':sha(PRIOR/'context_terminal.json'),'outline_DBU':geo['outline_DBU'],'PG_expansion_strip_DBU':geo['PG_template_growth_required_strip_DBU'],'PG_clock_IO_installed':False,'parent_IO_source_owned_required':geo['parent_IO_requirements'],'protection_Tcl':protection_tcl([c['name'] for c in w])}
    return {'schema':'opentallas.dsrom.production-context-source-binding.v1','candidate':join['candidate'],'current_main_checkpoint_read':'c1f8fbd75','source_mapping_commit':mapped['source_commit'],'retained_evidence_commit':'3a6b71c33cf1cc976858aa856a661100aefa8b91','retained_model_sha256':sha(PRIOR/'model.json'),'physical_policy_patterns':patterns,'production_track_source_sha256':sha(BASE/'inputs/make_tracks.tcl'),'RC_source_sha256':sha(BASE/'inputs/setRC.tcl'),'RC_scope':'Actual source retained; no unverified RC-unit conversion or modeled wire delay promoted to measurement','cases':out,'no_engine_RTL_or_cold_mapping':True,'SS_setup_ps':60,'FF_hold_ps':25,'period_ps':833.3333333333334,'G0_physical_implementation_admitted':False,'installed_CTS_PDN_not_a_prebuild_requirement':True,'prebuild_model_gaps':['sourcePDNextension/via/exclusion construction','priced branchplacement/cuts/slew constraints','actualsourceparentIO endpoint constraints'],'installed_PG_CTS_and_extracted_SSFF_are_build_validation':True,'old_negative_records_unchanged':True}
if __name__=='__main__':
    x=build();(BASE/'model.json').write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
    for k,c in x['cases'].items():(BASE/(k+'_protect_WAKE.tcl')).write_text(c['protection_Tcl'])
    print(sha(BASE/'model.json'))
