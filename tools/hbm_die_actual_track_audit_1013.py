#!/usr/bin/env python3
"""Stream generated LEF macros and audit only actual placed orientation classes.

Usage: python3 tools/hbm_die_actual_track_audit_1013.py CASE OUT_JSON
Heavy full-die audit must run via ot-run --mem8 --threads1. This is pin-track
legality, not die timing, DRC, overlap or release qualification.
"""
import sys,json,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent)); import check_macro_track_alignment as C
D=Path(sys.argv[1]); masters={}; orient={}
for line in (D/'die.v').open():
 m=re.match(r'\s*(\w+)\s+([^\s(]+)\s*\(',line)
 if m: masters[m[2]]=m[1]
for line in (D/'place.tcl').open():
 q=line.split()
 if len(q)==5 and q[0]=='fplace' and q[1] in masters: orient.setdefault(masters[q[1]],set()).add(q[-1])
rows=[]; lines=None
for line in (D/'elements.lef').open():
 if line.startswith('MACRO '): lines=[line]
 elif lines is not None:
  lines.append(line)
  if line.startswith('END '):
   text=''.join(lines); lines=None
   name=text.splitlines()[0].split()[1]
   if name not in orient: continue
   m=C.parse_lef(text)[0]; r=C.audit_macro(m,C.ASAP7_TRACKS_NM,C.ASAP7_LAYERS)
   failures=[]
   for layer, cases in r['orientations'].items():
    for o in orient[name]:
     c=cases[o]; key='joint_with_row' if c['pref_axis']=='y' else 'joint_with_site'
     joint=c.get(key,{})
     if not joint.get('legal_origins_mod_joint_nm',[]): failures.append({'layer':layer,'orient':o,'residues':c['legal_origin_residues_mod_track_nm'],'joint':joint})
   if failures: rows.append({'master':name,'size_um':r['size_um'],'failures':failures})
Path(sys.argv[2]).write_text(json.dumps({'placed_masters':len(orient),'failures':rows},indent=2)+'\n')
print(json.dumps(rows))
