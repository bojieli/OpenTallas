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
