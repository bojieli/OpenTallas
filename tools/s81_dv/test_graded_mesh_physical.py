import json
from types import SimpleNamespace
import pytest
import graded_mesh_physical as G

def test_bank_rows_snap_once_and_never_collapse_at_half_row_coordinates():
 c={str(i):v for i,v in enumerate(G.cluster(13753.8,17571.195,24,4))}
 assert len({(v['x'],v['y']) for v in c.values()})==24
 assert not G.D.placement_overlaps(c)

def test_physical_rails_respect_maxwidth_minstep_and_pg_spacing():
 for x in range(0,5001,13):
  w,_=G.width_at(x,10000,0,0)
  assert .04<=w<1.805 and w<=2.0
  assert abs(w/.08-round(w/.08))<1e-6
 for v in [256.544,459.32,12184.415,24744.96]:
  q=G.axis(v)
  assert abs(q-round(q/8.64)*8.64)+.88+.24+1<=4.32+1e-6

def test_legacy_uniform_combo_cannot_route_a_graded_candidate(tmp_path):
 (tmp_path/'mesh.json').write_text(json.dumps({'meta':{'graded_physical':{'rail_count':3}}}))
 with pytest.raises(SystemExit,match='actual segmented-rail encoder'):
  G.D.cmd_combo(SimpleNamespace(dir=str(tmp_path),kit=str(tmp_path/'absent')))
