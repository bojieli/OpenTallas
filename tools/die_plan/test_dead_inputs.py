import copy,json
from types import SimpleNamespace
from pathlib import Path
import pytest
from dead_inputs import dead_bits, ProvenDead,module_hash


def test_no_fanout_is_conservative():
 m=dict(ports={'a':dict(direction='input',bits=[2,3,4]),'y':dict(direction='output',bits=[4])},cells={'child':dict(connections={'A':[2],'Y':[5]},port_directions={'A':'input','Y':'output'})})
 assert dead_bits(m,'a')=={1}
 mutant=copy.deepcopy(m);mutant['cells']['child']['connections']['A'].append(3)
 assert dead_bits(mutant,'a')==set() # mutated live input must never be admitted


def test_exact_type_parameter_source_and_bit(tmp_path):
 src=tmp_path/'leaf.sv';src.write_text('module leaf #(parameter M=0)(input [1:0]a,output y);assign y=a[0];\nendmodule\n')
 row=dict(partition_type='tile',module='leaf',parameters={'M':'0'},source='leaf.sv',module_sha256=module_hash(src,'leaf'),method='yosys.proc.opt.no_fanout',remaining_loads=0,ports={'a':[[1,1]]})
 proof=tmp_path/'proof.json';proof.write_text(json.dumps(dict(schema='opentallas.dead_inputs.v1',verdict='PASS',declarations=[row])))
 d=ProvenDead({'dead_input_proofs':['proof.json'],'files':['leaf.sv']},tmp_path);cell=SimpleNamespace(module='leaf',params={'M':'0'})
 assert d.allows('tile',cell,'a',1)
 assert not d.allows('tile',cell,'a',0)
 assert not d.allows('other',cell,'a',1)
 cell.params={'M':'1'};assert not d.allows('tile',cell,'a',1)
 with pytest.raises(ValueError,match='defines'):
  ProvenDead({'dead_input_proofs':['proof.json'],'files':['leaf.sv'],'defines':['DIFFERENT_PROFILE']},tmp_path)
 dep=tmp_path/'child.sv';dep.write_text('module child(input a,output y);assign y=a;\nendmodule\n')
 data=json.loads(proof.read_text());data['dependency_modules']=[dict(module='child',source='child.sv',module_sha256=module_hash(dep,'child'))];proof.write_text(json.dumps(data))
 ProvenDead({'dead_input_proofs':['proof.json'],'files':['leaf.sv']},tmp_path)
 dep.write_text(dep.read_text().replace('assign y=a','assign y=~a'))
 with pytest.raises(ValueError,match='dependency'):
  ProvenDead({'dead_input_proofs':['proof.json'],'files':['leaf.sv']},tmp_path)
 data.pop('dependency_modules');proof.write_text(json.dumps(data))
 src.write_text(src.read_text().replace('a[0]','a[1]'))
 with pytest.raises(ValueError,match='stale'):ProvenDead({'dead_input_proofs':['proof.json'],'files':['leaf.sv']},tmp_path)


def test_no_unknown_direction_assumption():
 m=dict(ports={'a':dict(direction='input',bits=[2])},cells={'child':dict(connections={'unknown':[2]},port_directions={})})
 assert dead_bits(m,'a')==set()
