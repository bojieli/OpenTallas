import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('source',ROOT/'tools/dsrom_c_w6_source.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def test_actual_source_selected_events_default_off():
 raw=(ROOT/'rtl/test/dsrom_sys/tb_dsrom_system.sv').read_text(); out=m.instrument(raw)
 assert 'parameter integer W6_TRACE = 0' in out
 for e in ['STAGE_ISSUE','STAGE_DONE','HOP_ACCEPT','HOP_SEND','HBM_ACCEPT','HBM_VISIBLE']:
  assert f'W6_{e}' in out
 assert 'if (h_v[w6_port] && h_rdy[w6_port])' in out
 assert 'if (|h_wr_done)' in out
 # ACK has no fabricated user/position attribution; caller acceptance differs.
 line=next(x for x in out.splitlines() if '$display("W6_HBM_VISIBLE' in x)
 assert 'user=' not in line and 'pos=' not in line
 assert '.core_start(c_start)' in out and '.core_done(c_done)' in out
 assert out.count('W6_TRACE')==3
 with pytest.raises(AssertionError):m.instrument(out)

def test_actual_campaign_source_selection_is_optin_and_preserves_parameters(monkeypatch):
 import types
 spec=importlib.util.spec_from_file_location('campaign',ROOT/'tools/dsrom_w6_system_campaign.py')
 c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
 p=types.SimpleNamespace(TB=Path('original.sv'))
 monkeypatch.setenv('OT_SYS_GPARAMS','LINK_RT=1')
 c.select(p,False);assert p.TB==Path('original.sv')
 c.select(p,True);assert p.TB==ROOT/'rtl/test/dsrom_sys/w6/tb_dsrom_system.sv'
 assert c.os.environ['OT_SYS_GPARAMS']=='LINK_RT=1 W6_TRACE=1'
 with pytest.raises(ValueError):c.select(p,True)
