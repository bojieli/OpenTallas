#!/usr/bin/env python3
"""Prepare a source-pinned native FP candidate with explicit unchanged defaults."""
import argparse,copy,hashlib,json,re,sys
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('manifest',type=Path);p.add_argument('top',type=Path)
 p.add_argument('--source-base',type=Path,required=True)
 p.add_argument('--closure',type=Path,required=True)
 p.add_argument('--profile',choices=['minimal_4_4_0','candidate_5_4_1'],required=True)
 p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 sys.path.insert(0,str(a.source_base/'tools/hbm_b2'))
 from b2_top import Die
 if a.out.exists():p.error('use a fresh output directory')
 closure=json.loads(a.closure.read_text());profile=closure['profiles'][a.profile]
 paths=[]
 for item in closure['files']:
  path=a.source_base/item['path']
  if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
   raise ValueError('selected source closure mismatch: '+str(path))
  if not item['path'].endswith('/ot_hdc_fastfp_lat.sv'):paths.append(item['path'])
 source=a.top.read_text();die=Die(a.top,{})
 expected={f'su_{r}{g}' for r in ('NW','NE') for g in range(4)}
 got={n for n in die.insts if re.fullmatch(r'su_(NW|NE|SW|SE)[0-3]',n)}
 if got!=expected:raise ValueError('exact eight retained native slices required')
 rows=[]
 for name in sorted(expected):
  params={k:int(v) for k,v in re.findall(r'\.(\w+)\((\d+)\)',die.insts[name]['params'])}
  actual=dict(MLAT=params['MLAT'],ALAT=params['ALAT'],WCOPY=params.get('WCOPY',0))
  if actual!=dict(MLAT=4,ALAT=4,WCOPY=0) or params.get('LEAF')!=1:
   raise ValueError(name+': current 4/4/0 LEAF1 source profile differs')
  rows.append(dict(instance=name,actual=actual,full_side=params.get('FULL_SIDE',int(params['QID']==0))))
 if a.profile=='candidate_5_4_1':
  from su_build_profile import apply_profile
  source,caller=apply_profile(source,'m5a4w1')
 else:caller=dict(profile='m4a4w0',outer_caller_unchanged=True)
 a.out.mkdir(parents=True);top=a.out/'top.sv';top.write_text(source)
 manifest=copy.deepcopy(json.loads(a.manifest.read_text()));manifest['base']=str(a.source_base.resolve())
 manifest['netlist']=[str(top.resolve())]
 manifest['files']=list(dict.fromkeys(manifest.get('files',[])+paths))
 # bind_elab.pick deliberately gives the LAST explicit preference priority.
 manifest['prefer']=[s for s in manifest.get('prefer',[]) if s not in paths]+paths
 manifest['defines']=list(dict.fromkeys(manifest.get('defines',[])+profile['defines']))
 (a.out/'asbuilt.json').write_text(json.dumps(manifest,indent=1)+'\n')
 receipt=dict(schema='opentallas.hbm.native_fp_caller.v1',profile=a.profile,source_slices=rows,
              source_sha256=hashlib.sha256(a.top.read_bytes()).hexdigest(),candidate_sha256=hashlib.sha256(source.encode()).hexdigest(),
              source_closure=closure['files'],defines=profile['defines'],source_preference=paths,
              actual_caller=caller,added_cycles=profile['added_cycles'],
              guard='ADD4 applies only KEEP1/LAT4; legacy KEEP0 remains add_fast3, even for LAT4',
              status='CANDIDATE_ONLY_DEFAULTS_AND_PRODUCTION_ENABLE_UNCHANGED',
              obligations=['actual source hierarchy KEEP/LAT census','current native compiler token pass',
                           'native cut rebinding','physical review and TT/FF signoff'])
 (a.out/'caller.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print('native FP candidate',a.profile,profile['defines'],'source-pinned; production enable held')

if __name__=='__main__':main()
