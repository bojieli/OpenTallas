"""Explicit precise routed views preserve pin/PG/lower-OBS identity and staging names."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch
import pytest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
P=load('prov_detail_test',HERE/'prov_view.py')
A=load('abstract_detail_test',ROOT/'tools/die_plan/abstract_detail.py')

@pytest.fixture
def candidate(tmp_path):
 base=P.contract_lef('core',100,50,[dict(name='a',x=.1,y=5.,layer='M4')],{'a':'INPUT'},7)
 (tmp_path/'core.lef').write_text(base)
 lines=A.splice(base.splitlines(True),{'M6':['      RECT 20 20 30 20.1 ;\n'],'M7':['      RECT 50 0 50.2 50 ;\n']},['M6','M7'])
 (tmp_path/'detail_view.lef').write_text(''.join(lines))
 r=dict(base_sha256=P.sha256(tmp_path/'core.lef'),out_sha256=P.sha256(tmp_path/'detail_view.lef'),
        layers_detailed=['M6','M7'],check_ok=True,detail_pins_equal_base=True,bloat_factor=0)
 (tmp_path/'detail_receipt.json').write_text(json.dumps(r))
 return tmp_path,dict(detailed_lef='detail_view.lef',detailed_receipt='detail_receipt.json',detail_bloat_factor=0),r

def test_no_explicit_detail_preserves_original_selection(tmp_path):
 p,r=P.routed_detail(str(tmp_path),'core',{},None)
 assert p==str(tmp_path/'core.lef') and r is None

@pytest.mark.parametrize('bloat',[0,1])
def test_explicit_policy_and_only_upper_obs_replaced(candidate,bloat):
 d,m,r=candidate;m['detail_bloat_factor']=r['bloat_factor']=bloat
 (d/'detail_receipt.json').write_text(json.dumps(r))
 p,out=P.routed_detail(str(d),'core',m,str(ROOT))
 assert p==str(d/'detail_view.lef') and out['bloat_factor']==bloat
 assert A.check((d/'core.lef').read_text().splitlines(True),Path(p).read_text().splitlines(True),['M6','M7'])[0]

@pytest.mark.parametrize('change',['hash','pin','PG','lower','layers','unproved','bloat','missingpair','path','pin_clear'])
def test_reject_corrupt_geometry_and_receipts_even_with_updated_hash(candidate,change):
 d,m,r=candidate
 if change=='hash':r['out_sha256']='0'*64
 elif change in ('pin','PG','lower'):
  p=d/'detail_view.lef';s=p.read_text()
  if change=='pin':s=s.replace('PIN a\n','PIN bad_a\n')
  elif change=='PG':s=s.replace('PIN VSS\n','PIN bad_VSS\n')
  else:s=s.replace('LAYER M1 ;','LAYER M0 ;')
  p.write_text(s);r['out_sha256']=P.sha256(p)
 elif change=='layers':r['layers_detailed']=['M5','M6','M7']
 elif change=='unproved':r['detail_pins_equal_base']=False
 elif change=='bloat':m['detail_bloat_factor']=1
 elif change=='missingpair':del m['detailed_receipt']
 elif change=='pin_clear':r['pin_clear_um']=.048
 else:m['detailed_lef']='../detail_view.lef'
 (d/'detail_receipt.json').write_text(json.dumps(r))
 with pytest.raises(ValueError):P.routed_detail(str(d),'core',m,str(ROOT))

def test_stage_detail_named_like_base_does_not_overwrite_it(tmp_path):
 import sys
 sys.path.insert(0,str(HERE))
 import kit_wave as K
 c=dict(host='intel2',dir='/source/base',detailed_lef='/source/exact/core.lef',
        detailed_receipt='/source/exact/proof.json',detail_bloat_factor=0)
 sp=dict(gen_host='intel2',hub='intel2',work=str(tmp_path),item='t',plan='/p',src='/src',
         prov_views={'cands':{'core':[c]}})
 def run(stage,*args,**kwargs):
  return 0,('PROV_JSON '+json.dumps({'ok':True,'overlay_plan':'/overlay','children':{}}) if stage=='prov_views' else '')
 with patch.object(K.subprocess,'run') as called:
  out={};assert K.prov_stage(sp,run,lambda x:x,lambda *a:99,out)==('/overlay',0)
 calls=[x.args[0] for x in called.call_args_list]
 assert any(x[-2:]==['/source/exact/core.lef',str(tmp_path/'prov_relay/core/c0/detail_view.lef')] for x in calls)
 meta=json.loads((tmp_path/'prov_relay/core/c0/meta.json').read_text())
 assert meta['detailed_lef']=='detail_view.lef' and meta['source_detailed_lef']==c['detailed_lef']
 assert meta['detail_bloat_factor']==0


def test_pin_window_receipt_is_rechecked(tmp_path):
 """DIE-QC-97 11-10: a receipt with pin windows passes only when its windows sit on base signal pins"""
 base=P.contract_lef('core',100,50,[dict(name='a',x=.1,y=5.,layer='M4')],{'a':'INPUT'},7)
 (tmp_path/'core.lef').write_text(base)
 lines=A.splice(base.splitlines(True),{'M6':['      RECT 20 20 30 20.1 ;\n'],'M7':['      RECT 50 0 50.2 50 ;\n']},['M6','M7'])
 (tmp_path/'detail_view.lef').write_text(''.join(lines))
 win=dict(margin_um=1.0,top_layer='M7',clear_um=0.05,windows={})
 r=dict(base_sha256=P.sha256(tmp_path/'core.lef'),out_sha256=P.sha256(tmp_path/'detail_view.lef'),
        layers_detailed=['M6','M7'],check_ok=True,detail_pins_equal_base=True,bloat_factor=1,pin_window=win)
 (tmp_path/'detail_receipt.json').write_text(json.dumps(r))
 m=dict(detailed_lef='detail_view.lef',detailed_receipt='detail_receipt.json',detail_bloat_factor=1)
 p,out=P.routed_detail(str(tmp_path),'core',m,str(ROOT))
 assert p==str(tmp_path/'detail_view.lef') and out['pin_window']['pins']==[]
 win['windows']={'a':dict(layer='M4',rect=[40,40,42,42],layers=['M5'])}
 (tmp_path/'detail_receipt.json').write_text(json.dumps(r))
 with pytest.raises(ValueError):P.routed_detail(str(tmp_path),'core',m,str(ROOT))
