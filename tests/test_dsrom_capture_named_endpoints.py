import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_capture_named_endpoints as E

def test_all_static_rows_and_unique_physical_cells():
 rows={};n=0;names=set()
 for r in E.endpoints():
  n+=1;names.add(r['proposed_endpoint_identity']);rows.setdefault(r['source_row'],set()).add(r['opaque_raw_bit'])
  assert r['global_root']==(r['source_row']%256)//2
  assert r['physical_shard']==r['global_root']//64
  assert r['actual_placed_instance_name'] is None
  for p in r['pins'].values():
   x,y=p['point_DBU'];a,b,c,d=p['access_rect_DBU'];assert a<=x<=c and b<=y<=d
 assert n==len(names)==39744
 assert set(rows)==set(range(576))
 assert all(v==set(range(69)) for v in rows.values())

def test_read_restore_is_separate_from_storage_and_no_endpoint_invention():
 r=next(E.endpoints())
 assert r['pins']['restore.Y']['point_DBU']==[10980441.,15567255.]
 assert r['pins']['storage.QN']['point_DBU']==[10980279.,15567255.]
 c=E.contract()
 assert c['actual_local_controller_instance_ports'] is None
 assert c['CDC_endpoint']['selected_implementation'] is None
 assert not c['contextual_PR_admitted']
