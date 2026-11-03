from pathlib import Path
import hashlib,json,sys
r=Path(sys.argv[1]);mode=sys.argv[2];d=json.loads((r/'PLACE_EXPECTED.json').read_text());k=r/'kit'
for name,h in d['expected'].items():assert hashlib.sha256((k/name).read_bytes()).hexdigest()==h,name
m=json.loads((r/'CANARY_INPUTS.json').read_text())
for name,h in m['expected'].items():assert hashlib.sha256((r/name).read_bytes()).hexdigest()==h,name
base=k/'run/results/asap7/hc_ot_qkh_recip_leaf__216x216/base'
assert not any(p.name.startswith(('4_','5_','6_')) for p in base.iterdir())
if mode!='run':assert not any(p.name.startswith('3_') for p in base.iterdir())
else:
 assert all((base/n).is_file() for n in ['3_1_place_gp_skip_io.odb','3_2_place_iop.odb','3_3_place_gp.odb','3_4_place_resized.odb','3_5_place_dp.odb','3_place.odb','3_place.sdc'])
 for stage in ['global_place_skip_io','io_placement','global_place','resize','detail_place']:
  log=k/('PG_PLACE_CANARY_'+stage+'.jsonl')
  assert log.is_file() and log.stat().st_size>0,stage
print('PASS_PRIVATE_CANARY_INPUTS',mode,'original94+instrumentation pinned; no stage4+')
