"""Component ABI/state and physical-authority refusal gates (not runtime credit)."""
from pathlib import Path
import pytest
from tools.gpu_sys.canonical_qwen_range_owner_rtl import BITS,OFF,ROW,FIELDS,declarations
from tools.gpu_sys.canonical_qwen_range_owner_bindings import RangeOwnerPort
from tools.gpu_sys.canonical_qwen_transport import TransportError
ROOT=Path(__file__).resolve().parents[1]
T=ROOT/'tools/gpu_sys/canonical_qwen_range_owner_template.sv'

class ObservedPort:
 def __init__(self):self.ticks=0;self.values={};self.sets=[]
 def parameter(self,n):return {'ENABLE':1,'SM_INDEX':0}[n]
 def get(self,n):return self.values.get(n,0)
 def set(self,n,v):self.values[n]=v;self.sets.append((n,v))
 def settle(self):pass
 def tick(self):self.ticks+=1


def test_actual_holders_are_full_identity_and_separately_coded():
 assert ROW['producer_tuple']==239 and ROW['consumer_tuple']==239
 assert ROW['ACK_bitmap']==32 and ROW['owner55']==55
 assert sum(((b+43)//44)*72*(7 if k=='r' else 1) for k,b in BITS.items())==8136
 for k,d in FIELDS.items():
  assert len({o for o,w in OFF[k].values()})==len(d)
  assert sum(d.values())==BITS[k]
 assert 'R_PRODUCER_FRAME_RETIRED' in declarations()


def test_constructor_observes_installed_pins_without_factory_edges():
 p=ObservedPort();RangeOwnerPort(p,0)
 assert p.ticks==0 and p.sets==[]


def test_wrong_instance_or_disabled_refuses():
 p=ObservedPort()
 with pytest.raises(TransportError):RangeOwnerPort(p,1)
 p.parameter=lambda n:0
 with pytest.raises(TransportError):RangeOwnerPort(p,0)


def test_hardware_issue_required_not_output_version_inference():
 p=ObservedPort();q=RangeOwnerPort(p,0)
 with pytest.raises(TransportError):q.current_issue(13)
 p.values.update(issued_input_live=1,issued_input_started=1,inputs_bound_tuple=(1<<175)|(13<<164))
 assert q.current_issue(13)==p.values['inputs_bound_tuple']
 with pytest.raises(TransportError):q.current_issue(14)
 p.values['fault']=1
 with pytest.raises(TransportError):q.current_issue(13)


def test_post_page_release_requires_actual_held_query():
 p=ObservedPort();q=RangeOwnerPort(p,0)
 with pytest.raises(TransportError):q.complete_page(123,7,11)
 assert p.ticks==0
 p.values.update(query_result_valid=1,source_owner_retained=1,query_result_tuple=123,query_result_slot=7,query_result_owner=11)
 with pytest.raises(TransportError):q.complete_page(124,7,11)
 assert p.ticks==0
 assert q.complete_page(123,7,11)
 assert p.ticks==1 and p.sets==[('query_result_ready',1),('query_result_ready',0)]


def test_frame_vs_lease_and_whole_input_ABI_are_distinct():
 s=T.read_text();frame=s.split('if(frame_retire_valid&&frame_retire_ready)begin')[1].split('if(source_native_retire_valid')[0]
 assert 'rn[retire_row]=0' not in frame
 assert 'R_PRODUCER_FRAME_RETIRED' in frame and 'R_CONSUMER_ORDINAL' in frame
 assert 'if(source_native_retire_valid&&source_native_retire_ready)rn[release_row]=0' in s
 assert 'input_terminal_mask==b[B_MASK +:7]' in s
 assert 'input_reverse_mask==b[B_MASK +:7]' in s
 assert 'expected_consumer(r[i][R_SOURCE_VERSION' in s
 assert 'local_tuple(bind_tuple)&&bind_output_row<0' in s # remote input bank allowed


def test_no_clean_or_mutable_state_shortcut():
 s=T.read_text()
 assert '.release_clean(ok[w])' in s
 assert 'else if(ce[w]&&!due[w])' in s
 assert 'else if(write_enable&&clean)' in s
 assert 'if(warm_reset)gn[G_QUARANTINE]=1' in s
 assert 'wire active=base_active&&!unexpected;' in s
 assert 'go_match=barrier_ok&&next_source_PC==go_tuple[174:164]' in s


def test_predicted_calendar_is_positive_and_no_physical_claim():
 import json
 m=json.loads((ROOT/'results/uarch/canonical_qwen_range_owner_20261003/model.json').read_text())
 assert m['protected_bits_all_SM']==64*8136
 assert m['prospective_calendar']['query_service_edges']==5
 assert m['repair_holders_per_SM']==0
 assert m['codec_replication']['parallel_scrub_ports']==113
 assert m['SS_FF_loaded_timing'] is None and m['track_and_slot_fit'] is None
 assert m['functional_component_enrollment_only'] and not m['RTL_build_admitted']


def test_fixture_port_parser_carries_width_without_parsing_keywords_as_names():
 from tools.gpu_sys.canonical_qwen_range_owner_gate import parse_ports
 x=parse_ports('input wire clk,por_n, input wire [238:0] tuple, output wire v,ready')
 assert x=={'clk':('input',''),'por_n':('input',''),'tuple':('input','238:0'),'v':('output',''),'ready':('output','')}
 for text in ('input wire clk,input','input wire clk,clk','input wire [0:0] v, output'):
  with pytest.raises(ValueError):parse_ports(text)


def test_source_ABI_has_no_declared_keyword_or_duplicate_port():
 from tools.gpu_sys.canonical_qwen_range_owner_gate import parse_ports
 header=T.read_text().split(')(\n',1)[1].split(');',1)[0]
 x=parse_ports(header)
 assert x['input_terminal_tuple']==('input','238:0')
 assert x['inputs_bound_tuple']==('output','238:0')
 assert x['inputs_bound_mask']==('output','6:0')
 assert x['query_result_owner']==('output','45:0')
 assert len(x)>75
