#!/usr/bin/env python3
"""Read-only diagnostic replay: snapshot exact row constraints and pre-place occupancy.
No acceptance, placement, source or geometry logic changes. Preserve original failure.
"""
import collections, hashlib, json, os, runpy, sys
from pathlib import Path
import numpy as np
ROOT=Path(os.environ['FROZEN_SRC']); OUT=Path(os.environ['MODEL_OUT'])
OUT.mkdir(parents=True,exist_ok=True)
os.chdir(ROOT)
sys.path.insert(0,str(ROOT/'tools/hbm_die_v15'));sys.path.insert(0,str(ROOT/'tools'))
import lane_rows_reach as L
original=L.LanePlacer.place
wanted={'rf0019_k02_00','rf0025_k00_00'}
records=[]
def capture(self,rid):
    if rid not in wanted:return original(self,rid)
    stats=self.stats.copy();terms=self.terms(rid);self.stats=stats
    g=self.row_geom[rid]
    neighbors={}
    for _,_,_,_,label in terms:
        n=label.split(' -> ')[1].rsplit('.',1)[0]
        neighbors[n]=dict(master=self.I[n]['master'],placement=self.pl.get(n),planned_ll=self.plan_ll.get(n),
                          cell=self.cell_of[n],size=self.size[self.cell_of[n]],view_kind=self.kinds.get(self.cell_of[n]))
    np.savez_compressed(OUT/(rid+'_occupancy.npz'),grid=self.occ.g)
    rec=dict(row=rid,geometry=g,terms=terms,neighbors=neighbors,cell_um=self.CELL,die_um=[self.W,self.H],
             reach_um=self.R,margin_um=self.margin,grid_shape=list(self.occ.g.shape),
             own_views={n:dict(master=self.I[n]['master'],cell=self.cell_of[n],size=self.size[self.cell_of[n]],
                pins=(self.lef_xy_fn(self.lef_path_of(self.cell_of[n])) if self.lef_path_of(self.cell_of[n]) else None)) for n,*_ in g['tiles']})
    before=len(self.fails);result=original(self,rid)
    rec['original_result']=result;rec['original_failure']=self.fails[before:]
    (OUT/(rid+'.json')).write_text(json.dumps(rec,indent=2));records.append(rid)
    return result
L.LanePlacer.place=capture
args=json.loads(Path(os.environ['MODEL_ARGS']).read_text())
sys.argv=[str(ROOT/'tools/hbm_die_v15/die_case_v16.py')]+args
try:runpy.run_path(sys.argv[0],run_name='__main__')
except SystemExit as e:
    (OUT/'diagnostic_receipt.json').write_text(json.dumps(dict(original_exit=str(e),captured_rows=records,
      qualification=False,scope='Unmodified failed GEN replay; exact pre-place occupancy and centroid-lower-bound terms only',
      source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [ROOT/'tools/hbm_die_v15/die_case_v16.py',ROOT/'tools/hbm_die_v15/lane_rows_reach.py']}),indent=2))
    if len(records)!=len(wanted):raise
