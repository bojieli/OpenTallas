import hashlib,json,re
from pathlib import Path
B=Path('/srv/opentallas-scratch/claude/hd4g/gen2d')
C=B.parent/'gen2c/case_a'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
out={'status':'TERMINAL_FAILED_SNAPSHOTS_NOT_PERSISTED','variants':{},'inputs':{}}
for src,tags in [('15e069307',['ofly','ofly57']),('1e3fbe31b',['hhpref','hhfb'])]:
 for tag in tags:
  p=B/f'forest_{src}'/tag
  files=[q for q in p.rglob('*') if q.is_file() and not q.is_symlink() and '__pycache__' not in str(q)]
  wanted=['tools/hbm_die_v16/reset_forest_layer.py','tools/hbm_die_v16/reset_forest_geometry.py','tools/hbm_die_v16/reset_rows.py','tools/hbm_die_v15/die_clock_tree.py','rtl/hbm_accel/die_glue/hbfd_rrl.sv','rtl/lib/ot_rst_relay.sv']
  out['variants'][tag]={'source_label':src,'report':json.loads((p/'report.json').read_text()),'files_outside_src':[str(q.relative_to(p)) for q in files if not q.is_relative_to(p/'src')],'source_hashes':{x:digest(p/'src'/x) for x in wanted},'report_sha256':digest(p/'report.json'),'snapshot_present':False,'layer_present':(p/'layer.json').exists(),'loc_entries':list(map(str,(p/'loc').iterdir()))}
P=B/'forest_codex9d5a2c350'
for q in [P/'manifest.json',P/'contract_pre.json',C/'run.tcl',C/'die.v',P/'relay_views/hbfd_rrl_hop.lef',P/'relay_views/hbfd_rrl_sync.lef']:
 out['inputs'][str(q)]={'sha256':digest(q),'bytes':q.stat().st_size}
out['relay_lef']={}
for q in (P/'relay_views').glob('*.lef'):
 t=q.read_text();pins={}
 for m in re.finditer(r'\bPIN\s+(\S+)(.*?)\bEND\s+\1',t,re.S):
  pins[m[1]]={'rectangles':re.findall(r'\bRECT\s+([^;]+);',m[2]),'direction':re.findall(r'DIRECTION\s+(\w+)',m[2]),'use':re.findall(r'USE\s+(\w+)',m[2])}
 out['relay_lef'][q.name]={'pins':pins,'has_clock_out':any(x in pins for x in ['clock_out','clk_out','ck_out'])}
manifest=json.loads((P/'manifest.json').read_text());out['manifest_fields']=list(manifest)
out['clock_or_phase_metadata']={k:v for k,v in manifest.items() if any(s in k.lower() for s in ['clock','phase','reset'])}
out['native_clock_source_placement_lines']=[l for l in (C/'run.tcl').read_text().splitlines() if re.search(r'place_inst -name dkh_P2\b',l)]
out['endpoint_distance_um']=abs(18531-12761.158)+abs(30455-19794.988)
print(json.dumps(out,indent=2))
