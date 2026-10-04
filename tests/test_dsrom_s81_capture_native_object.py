import copy,gzip,importlib.util,json
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[1]/'tools/dsrom_s81_capture_native_object.py'
s=importlib.util.spec_from_file_location('obj',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
@pytest.fixture(scope='module')
def source():
 n=json.loads(gzip.decompress((m.BASE/'mapped.json.gz').read_bytes()))['modules']['ot_dsrom_rd64_vm_capture']
 return n,json.loads((m.BASE/'terminal.json').read_text()),json.loads((m.BASE/'library_cell_areas.json').read_text())
def test_actual_complete_native_capture(source):
 n,t,a=source;r=m.summarize(n,t,a)
 assert r['cells']==352899 and r['FF_cells']==16271
 assert r['actual_cell_area_um2']==pytest.approx(29917.08108)
 assert r['source_clock']['native_CLK_sinks']==16271
 assert r['source_cold_reset']['native_async_sinks']==7567
 assert sum(r['source_cold_reset']['native_sink_pin_counts'].values())==7567
 assert r['required_constant_supply']['native_constant_one_sinks']==7567
 assert not r['source_clock']['physical_buffers_or_CTS_included']
@pytest.mark.parametrize('kind',['clock','reset'])
def test_wrong_clock_reset_rejected(source,kind):
 n,t,a=source;n=dict(n);n['cells']=dict(n['cells'])
 key=next(k for k,c in n['cells'].items() if c['type'].startswith('DFFASR'))
 c=copy.deepcopy(n['cells'][key]);n['cells'][key]=c
 if kind=='clock':c['connections']['CLK']=[987654321]
 else:c['connections']['RESETN']=['1'];c['connections']['SETN']=['1']
 with pytest.raises(ValueError,match='source'):m.summarize(n,t,a)
def test_wrong_terminal_count_rejected(source):
 n,t,a=source;t=copy.deepcopy(t);t['actual_cell_census']['NAND2x1_ASAP7_75t_R']-=1
 with pytest.raises(ValueError,match='census'):m.summarize(n,t,a)
def test_unsupported_cell_refused(source):
 n,t,a=source;n=dict(n);n['cells']=dict(n['cells']);n['cells']['unbound']={'type':'$unmapped'}
 with pytest.raises(ValueError,match='unknown'):m.summarize(n,t,a)
def test_typed_reset_set_constants(source):
 n,t,a=source;r=m.summarize(n,t,a)
 assert set(r['source_cold_reset']['native_sink_pin_counts'])=={'RESETN','SETN'}
 assert r['required_constant_supply']['physical_TIEHI_cells_present']==0
