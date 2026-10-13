#!/usr/bin/env python3
"""Compare all source-elaborated default-shape port bits with inherited hard-view pins."""
import collections,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'results/arch/hbm_native_1013/sm'
m=json.load(open(OUT/'component.json')); rows={}
for c in m['children']:
 typ=c['logical_module']
 if typ in rows: continue
 expected=set(); expected_direction={}
 for port,p in c['boundary_ports'].items():
  bits=[port] if p['width']==1 else [f'{port}[{i}]' for i in range(p['width'])]; expected.update(bits)
  expected_direction.update({bit:p['direction'] for bit in bits})
 row={'logical_module':typ,'production_params':m['parameters'],'defines':m['defines'],'source_commit':m['source_commit'],'source_expected_bits':len(expected),'view_source_commit':c.get('view_source_commit'),'record_job':c.get('view_job'),'closed':False,'note':'Exact physical pin census is necessary; recorded default parameter/define/dependency provenance and production arithmetic remain separate gates.'}
 lef=c['view_lef']
 if not lef: row['status']='OPEN_NO_NATIVE_EXPORT'; rows[typ]=row; continue
 leftext=(ROOT/lef).read_text(); pins=set(re.findall(r'\bPIN\s+(\S+)',leftext))-{'VDD','VSS','VPWR','VGND'}
 directions={a:b.lower() for a,b in re.findall(r'\bPIN\s+(\S+)\s+.*?\bDIRECTION\s+(INPUT|OUTPUT|INOUT)\s*;',leftext,re.S)}
 mismatch={bit:{'source':direction,'view':directions.get(bit)} for bit,direction in expected_direction.items() if directions.get(bit)!=direction}
 row['lef']={'path':lef,'missing':sorted(expected-pins),'extra':sorted(pins-expected),'direction_mismatch':mismatch,'pass':expected==pins and not mismatch}; libs={}
 for corner,p in c['view_lib'].items():
  text=(ROOT/p).read_text(); pins=set(re.findall(r'(?<![\w])pin\s*\(\s*"?([^"\s\)]+)"?\s*\)',text)) - {'VDD','VSS','VPWR','VGND'}
  directions={a:b.lower() for a,b in re.findall(r'(?<![\w])pin\s*\(\s*"?([^"\s\)]+)"?\s*\)\s*\{.*?\bdirection\s*:\s*(input|output|inout)\s*;',text,re.S)}
  mismatch={bit:{'source':direction,'view':directions.get(bit)} for bit,direction in expected_direction.items() if directions.get(bit)!=direction}
  libs[corner]={'path':p,'missing':sorted(expected-pins),'extra':sorted(pins-expected),'direction_mismatch':mismatch,'pass':expected==pins and not mismatch}
 row['lib']=libs; row['status']='PORT_BITS_MATCH_NATIVE_DEFAULTS' if row['lef']['pass'] and all(v['pass'] for v in libs.values()) else 'OPEN_PORT_MISMATCH'; row['all_corners_present']=set(libs)=={'tt','ff','ss'}
 rows[typ]=row
(OUT/'port_audit.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps({k:{'status':r['status'],'all_corners':r.get('all_corners_present')} for k,r in rows.items()}))
