"""Preserving source faces adds zero wrappers and never invents peer context."""
import copy,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'physical/die_plan/hbm_arch_cores'))
import face_shell as F
PORTS=[('clk','input',1),('in_v','input',16),('in_ready','output',16),('data','output',32)]
def context():return dict(schema='opentallas.native_hard_child_seam.v1',module='native',scope_buses=['in_v','in_ready'],bus_widths=dict(in_v=16,in_ready=16),parent_contexts=[dict(parent='actual_parent')])
def test_source_owned_registers_are_not_rewrapped():
 r=F.preexisting_manifest('native',PORTS,context())
 assert r['files']==[] and r['face_flops']==0
 assert r['latency']['in_cycles']==r['latency']['out_cycles']==0
 assert r['native_endpoint_contract']['port_roles']==dict(in_v='input',in_ready='output')
 assert 'source-owned' in r['latency']['note']
@pytest.mark.parametrize('bad',['missing','master','width','parent','scope'])
def test_wrong_or_absent_peer_context_rejected(bad):
 c=context()
 if bad=='missing':c=None
 if bad=='master':c['module']='other'
 if bad=='width':c['bus_widths']['in_v']=17
 if bad=='parent':c['parent_contexts']=[]
 if bad=='scope':c['scope_buses'].append('absent')
 with pytest.raises(RuntimeError):F.preexisting_manifest('native',PORTS,c)
