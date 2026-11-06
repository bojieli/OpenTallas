#!/usr/bin/env python3
"""Install exact measured native dataflow groups, default off.

Placement only: caller supplies source-mapped member/master lists, held controls,
and the ordinary region_guide spec. The canonical soft guides release before DPL.
Source RTL, clocks, resets, ports and latency are unchanged. This does not qualify
an old source kit for current adoption: it produces a provisional physical trial.
"""
import argparse, hashlib, json, pathlib, shutil, sys
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))

def digest(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
 return h.hexdigest()

def install(kit,regions,members,held):
 import region_guide
 kit=pathlib.Path(kit);spec=json.loads(pathlib.Path(regions).read_text())
 rows=[line.split('\t') for line in pathlib.Path(members).read_text().splitlines() if line]
 holds=[line.split('\t') for line in pathlib.Path(held).read_text().splitlines() if line]
 if not rows or any(len(x)!=4 for x in rows) or any(len(x)!=2 for x in holds):raise ValueError('native tile manifest rows')
 names=[x[0] for x in rows];fixed=[x[0] for x in holds]
 if len(names)!=len(set(names)) or len(fixed)!=len(set(fixed)) or set(names)&set(fixed):raise ValueError('duplicate/held native tile members')
 guided=[n for r in spec['regions'] for n in r['insts']]
 if len(guided)!=len(set(guided)) or set(guided)!=set(names):raise ValueError('region members differ from exact native manifest')
 assignment={n:r['name'] for r in spec['regions'] for n in r['insts']}
 if any(assignment[n]!=f'ot_rg_native_{bus}_{tile}' for n,m,bus,tile in rows):raise ValueError('native tile assignment mismatch')
 for f in ('face_flops.tcl','face_flops_release.tcl'):
  if not (kit/f).is_file():raise ValueError('native tiles require existing placement hook pair')
 if (kit/'landing_native_tiles.tcl').exists():raise ValueError('native tiles already installed; use fresh scope')
 shutil.copyfile(HERE/'landing_native_tiles.tcl',kit/'landing_native_tiles.tcl')
 shutil.copyfile(members,kit/'native_tiles_manifest.tsv');shutil.copyfile(held,kit/'native_tiles_held.tsv')
 with (kit/'face_flops.tcl').open('a') as f:f.write('\n# Explicit exact native dataflow membership, zero cycles.\nsource /work/landing_native_tiles.tcl\n')
 outline=json.loads((kit/'freeze.json').read_text())['outline_um']
 rec=region_guide.install(kit,spec,outline=outline,src={'file':str(regions),'sha256':digest(regions)})
 # Generic soft guides permit missing/fixed skips. This exact opt-in refuses them.
 with (kit/'face_flops.tcl').open('a') as f:f.write(f'if {{$::rg_cells != {len(names)} || $::rg_n != {len(spec["regions"])}}} {{error "NATIVE_TILES incomplete actual region membership"}}\n')
 receipt=dict(schema='opentallas.native_dataflow_tiles.v1',provisional_physical_only=True,zero_added_cycles=True,members=len(names),held=len(fixed),regions=rec,inputs={str(p):digest(p) for p in (regions,members,held)})
 (kit/'native_tiles_install.json').write_text(json.dumps(receipt,indent=1)+'\n');return receipt

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('kit');p.add_argument('--regions',required=True);p.add_argument('--members',required=True);p.add_argument('--held',required=True);a=p.parse_args();print(json.dumps(install(a.kit,a.regions,a.members,a.held),indent=1))
