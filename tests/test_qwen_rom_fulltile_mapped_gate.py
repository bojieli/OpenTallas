import importlib.util
from pathlib import Path
import pytest
s=importlib.util.spec_from_file_location('gate',Path(__file__).resolve().parents[1]/'tools/qwen_rom_fulltile_mapped_gate.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
def net():
 return {'cells':{'ff0':{'type':'DFFHQNx1_ASAP7_75t_R','connections':{'QN':[10]}},'ff1':{'type':'DFFHQNx1_ASAP7_75t_R','connections':{'QN':[11]}},'inv':{'type':'INVx1_ASAP7_75t_R','connections':{'A':[10],'Y':[20]}},'buf':{'type':'BUFx4_ASAP7_75t_R','connections':{'A':[20],'Y':[30]}}}}
def test_actual_QN_inverse_and_buffer_owner():assert g.ff_endpoints(net(),[30,11])==['ff0','ff1']
def test_alias_replica_is_refused():
 with pytest.raises(ValueError,match='merged'):g.ff_endpoints(net(),[10,30])
def test_lost_endpoint_is_refused():
 with pytest.raises(ValueError,match='no actual mapped FF'):g.ff_endpoints(net(),[100])
