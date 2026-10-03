import copy,importlib.util,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('physical',ROOT/'tools/w2_full_controller_physical_context.py');G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G)
@pytest.fixture(scope='module')
def m():return G.model()
def test_full_source_census_and_dimensions(m):
 assert m['storage']['words']==219 and m['storage']['physical_bits']==15768
 assert m['storage']['primary_words']==182 and m['storage']['secondary_words']==37
 assert m['storage']['payload_bits']==7971 and m['storage']['static_seal_padding_bits']==7797
 assert m['replication']['bits_total']==20183040 and m['replication']['requested_controllers']==1280
 assert m['logic_inventory']['parallel_current_decoders']==219
 assert m['logic_inventory']['independent_write_encoders']==219
 assert m['logic_inventory']['journal_seats']==9 and m['logic_inventory']['corrector_engines']==8
 assert m['logic_inventory']['count_workers']==6
 assert m['ports']['input_bits']==2324 and m['ports']['output_bits']==2323
 assert m['ports']['book']['c_req_addr']['bits']==204
 assert m['ports']['book']['c_rsp_data']['bits']==1536
 assert m['ports']['book']['p_req_addr']['bits']==34
 assert m['parameters']['OPT_RESET_QUARANTINE']==1
 assert m['parameters']['OPT_EXACT']==1

def test_no_opaque_selector_or_replica_credit(m):
 assert m['logic_inventory']['raw_fixed_dynamic_bitmux_upper']==8*2*218*72
 assert m['logic_inventory']['peer_payload_dynamic_bitmux_upper']==8*2*3*218*44
 assert m['logic_inventory']['selector_NAND2_upper']==3*(251136+460416)
 assert m['area']['full_source_selector_exposed_budget_mm2_per_PC']>m['area']['retained_219_constructive_budget_mm2_per_PC']
 assert m['area']['actual_mux_simplification_credit']==0
 assert m['replication']['body_mm2_total']==1280*m['area']['full_source_selector_exposed_budget_mm2_per_PC']
 assert m['replication']['net_replacement_credit']==0

def test_actual_admission_absent_and_calendars_not_old(m):
 assert m['latency']['same_client_request_II_edges']==19
 assert m['latency']['different_client_prospective_II_edges']==10
 assert m['latency']['corrector_recurring_II']==9
 assert m['latency']['CAP']==4 and m['latency']['FIX']==4
 assert m['latency']['whole_token_delta'] is None
 assert m['area']['assigned_slot'] is None
 assert not any(m['actions'].values())
 assert m['decision'].startswith('BLOCKED')

def template(m):
 return dict(source_sha256=m['source_sha256'],parameters=m['parameters'],slot=dict(id='TEST_SCHEMA_ONLY_NOT_ACTUAL_SLOT',bbox_um=[0,0,1000,1000],placement_utilization=0.5,PG_OBS_excluded_um2=100000,owner_receipt_sha256='TEST_METADATA_NOT_AUTHORITY',PG_clock_reset_OBS_bound=True,neighbor_context='TEST_ONLY'),replica1280_source_map='TEST_ONLY',unified_token_composition_sha256='TEST_ONLY',period_ps=2500/3,setup_uncertainty_ps=60,hold_uncertainty_ps=25,SS_FF_PDK_lock_sha256='TEST_ONLY',CTS_reset_source_arcs='TEST_ONLY',legal_signal_track_map='TEST_ONLY',ports={n:dict(source_owner='TEST_ONLY',path_sha256='TEST_ONLY',driver_cell='TEST_ONLY',slew_min_ps=10,slew_max_ps=20,arrival_min_ps=0,arrival_max_ps=25,load_fF=1,capture_cell='TEST_ONLY') for n in m['ports']['book']})

@pytest.mark.parametrize('mutation,reason',[
 (lambda c:c['parameters'].update(NC=1),'parameters'),
 (lambda c:c['parameters'].update(MAX_OUT=2),'parameters'),
 (lambda c:c['parameters'].update(AW=32),'parameters'),
 (lambda c:c['parameters'].update(OPT_EXACT=True),'parameters'),
 (lambda c:c['ports']['c_req_addr'].update(slew_max_ps=float('nan')),'finite port'),
 (lambda c:c['ports']['c_rsp_data'].update(load_fF=float('inf')),'finite port'),
 (lambda c:c['source_sha256'].update({G.SOURCES[0]:'wrong'}),'source'),
 (lambda c:c['slot'].pop('id'),'slot'),
 (lambda c:c['slot'].update(bbox_um=[0,0,100,100]),'area deficit'),
 (lambda c:c['slot'].update(placement_utilization=.9),'density'),
 (lambda c:c['slot'].pop('PG_OBS_excluded_um2'),'exclusion'),
 (lambda c:c['ports']['c_req_addr'].update(slew_min_ps=0),'slew'),
 (lambda c:c['ports']['c_rsp_data'].update(load_fF=0),'load'),
 (lambda c:c['ports'].pop('reverse_fenced'),'unbound port'),
 (lambda c:c.update(period_ps=1000),'uncertainty'),
 (lambda c:c.update(setup_uncertainty_ps=0),'uncertainty'),
 (lambda c:c.update(hold_uncertainty_ps=0),'uncertainty'),
 (lambda c:c.pop('replica1280_source_map'),'replicas'),
 (lambda c:c.pop('legal_signal_track_map'),'routes'),
])
def test_bad_context_rejected_before_any_build(m,mutation,reason):
 c=copy.deepcopy(template(m));mutation(c)
 with pytest.raises(G.Refusal,match=reason):G.admit(c)

def test_schema_positive_is_explicitly_not_execution_admission(m):
 d=G.admit(template(m));assert d['metadata_schema_valid']
 assert d['actual_launch_requires_cold_context_artifact_review'] and not d['compiler_launched']
 assert 'ready' not in d

def test_width_parser_rejects_code():
 with pytest.raises(G.Refusal):G.width_expr('__import__("os").system("echo bad")',G.PARAMS)

def test_cold_record_generation(m):
 assert json.dumps(m,sort_keys=True,indent=2)+'\n'==(G.OUT/'model.json').read_text()
