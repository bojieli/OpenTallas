"""Exact opt-in per-clock sites; legacy placement remains unchanged."""
import ast,gzip,hashlib,json,math,re
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py'
def function():
    text=SRC.read_text();start=text.index('def plan_clock_entries(');end=text.index('\ndef io_tcl(',start);tree=ast.parse(text[start:end]);f=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='plan_clock_entries')
    ns=dict(Path=Path,json=json,math=math,re=re,PIN_LEN_UM=.48,sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest())
    exec(compile(ast.Module(body=[f],type_ignores=[]),str(SRC),'exec'),ns)
    return ns['plan_clock_entries']
def entry(sites=None):
    d=dict(module='tkm',xy_um=[159.84,172.8],port=None,merged_clock_ports=['buffer_clk','clk'])
    if sites is not None:d['clock_pin_sites_um']=sites
    return d
def call(tmp_path,d):
    p=tmp_path/'clock_entries.json';p.write_text(json.dumps(d))
    return function()(p,'tkm',['clk','buffer_clk'],319.68,389.664,(.024,.048))
def test_legacy_same(tmp_path):
    p,r=call(tmp_path,{'root':{'u':entry()}})
    assert p=={'buffer_clk':(159.864,172.8),'clk':(159.96,172.8)}
    assert 'clock_pin_sites_um' not in r
    assert call(tmp_path,{'root':{}})==({},None)
def test_exact_reviewed_sites(tmp_path):
    sites={'clk':[159.96,172.8],'buffer_clk':[160.344,172.8]};p,r=call(tmp_path,{'root':{'u':entry(sites)}})
    assert p=={n:tuple(xy) for n,xy in sites.items()};assert r['clock_pin_sites_um']==sites
    assert r['ports']==['buffer_clk','clk']
@pytest.mark.parametrize('sites',[{'clk':[159.96,172.8]}, {'clk':[159.96,172.8],'wrong':[160.344,172.8]}, {'clk':[159.96,172.8],'buffer_clk':[160.32,172.8]}, {'clk':[159.96,172.8],'buffer_clk':[160.344,400]}, {'clk':[159.96,172.8],'buffer_clk':[159.96,172.8]}, {'clk':[159.96,172.8],'buffer_clk':[160.344]}])
def test_bad_sites_refused(tmp_path,sites):
    with pytest.raises(SystemExit,match='CLOCK_ENTRY_SITES'):call(tmp_path,{'root':{'u':entry(sites)}})
def test_conflicting_instances_refused(tmp_path):
    e=entry({'clk':[159.96,172.8],'buffer_clk':[160.344,172.8]})
    with pytest.raises(SystemExit,match='CLOCK_ENTRY_CONFLICT'):call(tmp_path,{'root':{'a':e,'b':entry()}})
def test_real_tkm_metadata(tmp_path):
    p=ROOT/'physical/die_plan/hbm/plan_of_record/d44v/clock_entries.json.gz';d=json.loads(gzip.decompress(p.read_bytes()));e=d['root']['u_tkm_SW_root'];e=dict(e,module='tkm');sites=e['clock_pin_sites_um'];out,r=call(tmp_path,{'root':{'u':e}})
    assert out['clk']==(159.96,172.8);assert out['buffer_clk']==(160.344,172.8)
    assert e['merged_clock_ports']==['buffer_clk','clk'];assert r['clock_pin_sites_um']==sites
