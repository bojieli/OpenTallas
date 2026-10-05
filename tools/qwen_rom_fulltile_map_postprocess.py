#!/usr/bin/env python3
"""Classify retained mapped bytes; original collector FAIL is immutable."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
from qwen_rom_hold_capture_loaded_map import block
from qwen_rom_fulltile_mapped_gate import check as survival_check
TOP='ot_qwen_rom_fulltile_tp4_context_top'
MACROS=('ot_rom_4096x266_m8','ot_sram_1r1w_128x256_m1_r2c2')
EXPECTED_MAP_SHA='92b6cf36af938f89468c6ce07d7bd5624239172eecd914de3eb750ff435802a0'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def classify_cell(kind,cell,library):
    if kind=='$scopeinfo':
        if cell.get('connections')!={} or cell.get('port_directions')!={}:
            raise ValueError('scopeinfo has ports/connections; not metadata-only')
        if cell.get('parameters',{}).get('TYPE') not in ('module','generate'):
            raise ValueError('unknown scopeinfo TYPE')
        if not isinstance(cell.get('attributes'),dict) or not cell['attributes']:
            raise ValueError('scopeinfo has no provenance attributes')
        return 'metadata'
    if kind not in library and kind not in MACROS:raise ValueError('unmapped logic cell '+kind)
    return 'hardware'

def run(work,source_root,out,gate_version="r1"):
    if out.exists():raise ValueError('refuse overwrite derived receipt')
    out.mkdir(parents=True)
    original=json.loads((work/'terminal.json').read_text())
    if original['status']!='FAIL_SOURCE_MAP_RETAINED' or original.get('error')!='unmapped cell $scopeinfo':
        raise ValueError('only exact retained scopeinfo collector failure is eligible')
    if digest(work/'mapped.json')!=EXPECTED_MAP_SHA:raise ValueError('different mapped bytes require separate review')
    pins=json.loads((work/'inputpins.json').read_text())
    portable=json.loads((work/'portable_inputs.json').read_text()) if (work/'portable_inputs.json').exists() else {}
    for name,expected in pins.items():
        if name in portable:path=work/portable[name]
        else:
            path=Path(name);path=path if path.is_absolute() else source_root/path
        if digest(path)!=expected:raise ValueError('input library/source pin mismatch '+name)
    netlist=json.loads((work/'mapped.json').read_text());net=netlist['modules'][TOP]
    text=(work/'ss_merged.lib').read_text()
    library={m[1].strip().strip('"'):block(text,m.start()) for m in re.finditer(r'\bcell\s*\(([^)]+)\)',text)}
    counts={};metadata=[];area=0
    for name,cell in net['cells'].items():
        kind=cell['type'];classification=classify_cell(kind,cell,library)
        if classification=='metadata':metadata.append(name);continue
        # Bind all hardware connections to the captured actual Liberty modules.
        if kind not in netlist['modules']:raise ValueError('missing cell definition '+kind)
        ports=netlist['modules'][kind]['ports']
        if set(cell['connections'])!=set(ports) or set(cell['port_directions'])!=set(ports):raise ValueError('missing/extra hardware pins '+name)
        for pin,definition in ports.items():
            if cell['port_directions'][pin]!=definition['direction'] or len(cell['connections'][pin])!=len(definition['bits']):raise ValueError('pin direction/width mismatch '+name+'/'+pin)
        counts[kind]=counts.get(kind,0)+1
        if kind in library:area+=float(re.search(r'\barea\s*:\s*([\d.]+)',library[kind])[1])
    if len(metadata)!=2319:raise ValueError('different metadata census')
    if any(counts.get(kind)!=expected for kind,expected in zip(MACROS,(10,2))):raise ValueError('incomplete macros')
    report=(work/'mapping.log').read_text()
    reported=float(re.search(r"Chip area for module '\\ot_qwen_rom_fulltile_tp4_context_top':\s*([\d.]+)",report)[1])
    if abs(area-reported)>1e-5:raise ValueError('area differs from actual Yosys stat')
    model=json.loads((work/'model.json').read_text())
    if area>model['slot']['complete_cell_area_ceiling_um2']:raise ValueError('complete area exceeds selected model')
    shutil.copyfile(work/'terminal.json',out/'original_terminal_FAIL.json')
    # Raw netlist bytes are retained, not rewritten to conceal metadata.
    for name in ('mapped.json','mapped.v','model.json','sourcepins.json','source_proc.json','ss_merged.lib'):(out/name).symlink_to((work/name).resolve())
    receipt={**{k:v for k,v in original.items() if k not in ('status','error')},'status':'PASS_COMPLETE_SOURCE_MAP_ONLY_CONTEXT_OPEN',
      'derived_postprocess_only':True,'original_terminal_FAIL_sha256':digest(work/'terminal.json'),
      'raw_mapped_json_sha256':digest(work/'mapped.json'),'scopeinfo_metadata_excluded':len(metadata),
      'metadata_has_no_ports_or_connections':True,'hardware_cell_counts':counts,
      'mapped_cell_area_um2':area,'macro_area_excluded_from_logic_cell_area':True,
      'new_hardware_or_synthesis_run':False,'contextual_SSFF':False,'tile_PR':False}
    (out/'terminal.json').write_text(json.dumps(receipt,indent=2)+'\n')
    try:
        if gate_version=="r2":
            from qwen_rom_fulltile_mapped_gate_r2 import check as selected_gate
        else:selected_gate=survival_check
        survival=selected_gate(out)
    except Exception as e:
        survival=dict(status='FAIL_COMPLETE_MAPPED_SURVIVAL_RETAINED',reason=str(e),contextual_SSFF=False,P_and_R_admitted=False)
    (out/'survival.json').write_text(json.dumps(survival,indent=2)+'\n')
    print(json.dumps(dict(classification=receipt['status'],area_um2=area,survival_status=survival['status'],survival_reason=survival.get('reason')),indent=2))
    return 0 if survival['status'].startswith('PASS') else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--gate-version',choices=('r1','r2'),default='r1');a=p.parse_args();raise SystemExit(run(a.work,a.source_root,a.out,a.gate_version))
