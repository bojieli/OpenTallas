"""Actual elaborated RTL fixture joined through hashed physical/die receipts.

Deleted lifecycle nodes, oracle output and stale routed sources must each fail
an otherwise passing complete chain. Artifact hashes are checked on every edge.
"""
import copy
import importlib.util
import json
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import native_provenance as NP
spec = importlib.util.spec_from_file_location('actual_native_fixture', HERE.parent/'tests/test_native_operation_coverage.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class Reader:
    def __init__(self):
        self.data = {}

    def add(self, path, obj, raw=False):
        data = obj if raw else json.dumps(obj, sort_keys=True).encode()
        ref = dict(commit='a'*40, path=path, sha256=NP.digest(data))
        self.data[path] = data
        return ref

    def read(self, ref):
        data = self.data[ref['path']]
        if NP.digest(data) != ref['sha256']:
            raise ValueError('ARTIFACT_HASH_MISMATCH:'+ref['path'])
        return data


class ProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.CoverageTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixture.CoverageTests.tearDownClass()

    def setUp(self):
        f = fixture.CoverageTests
        self.reader = r = Reader()
        self.binding = copy.deepcopy(f.manifest)
        pr = r.add('program.json', f.program.read_bytes(), raw=True)
        r.add('real_native.sv', (f.root/'real_native.sv').read_bytes(), raw=True)
        r.add('target.json', (f.root/'target.json').read_bytes(), raw=True)
        mr = r.add('bindings.json', self.binding)
        gate = r.add('gate.py', (HERE.parent/'native_operation_coverage.py').read_bytes(), raw=True)
        self.token = dict(nodes=[dict(id='L0.add')], edges=[])
        token = r.add('token.json', self.token)
        files = {name:r.add(name, ('actual '+name).encode(), raw=True) for name in ('lef','tt_lib','ff_lib')}
        hashes = {name:ref['sha256'] for name,ref in files.items()}
        module = json.loads((f.root/'target.json').read_text())['modules']['top']
        self.route = dict(master='engine_leaf', status='CLOSED', tt_setup_ps=10, ff_hold_ps=4, drc=0,
                          rtl_sha256=f.manifest['elaboration']['source_sha256'],
                          elaborated_module_sha256=NP.digest(json.dumps(module,sort_keys=True,separators=(',',':')).encode()),
                          native_boundary=dict(reference='phi_minus_R',launch_ps=200,capture_ps=180,spread_ps=40), artifact_sha256=hashes)
        route = r.add('route.json', self.route)
        contract = r.add('contract.json',dict(slots={'leaf0':dict(master='engine_leaf',artifact_sha256=hashes)}))
        die = r.add('die.v', b'module die; engine_leaf leaf0(); endmodule', raw=True)
        db = r.add('die_bind.json',dict(verdict='PASS',masters={'engine_leaf':dict(verdict='PASS',instances=1)},die_netlist_sha256=die['sha256'],contract_sha256=contract['sha256']))
        grt = r.add('grt.json',dict(overflow=0,die_netlist_sha256=die['sha256'],contract_sha256=contract['sha256'],view_sha256_by_master={'engine_leaf':hashes}))
        sta = r.add('sta.json',dict(tt_setup_ps=5,ff_hold_ps=1,die_netlist_sha256=die['sha256'],grt_sha256=grt['sha256']))
        schedule = r.add('schedule.json',dict(program_sha256={'layer0':pr['sha256']},unplanned_stalls=0,exact_timeline=True,all_native_producers=True,runtime_backpressure=False))
        self.spec = dict(design='fixture',programs=[dict(id='layer0',program=pr,bindings=mr)],operation_gate=gate,
                         program_inventory=r.add('program_inventory.json',dict(programs=[dict(id='layer0',sha256=pr['sha256'])])),
                         token_graph=token,node_operations={'L0.add':['layer0:add']},schedule=schedule,
                         physical_bindings={'top/e':dict(master='engine_leaf',slot='leaf0',leaf_instance='top',target_commit='a'*40,route=route,files=files,contract=contract,die_bind=db,die_netlist=die,grt=grt,die_sta=sta)})
        self.spec['physical_bindings']['top/m']=copy.deepcopy(self.spec['physical_bindings']['top/e'])
        self.spec['physical_bindings']['top']=copy.deepcopy(self.spec['physical_bindings']['top/e'])

    def run_gate(self):
        return NP.qualify(self.reader,self.spec,self.token)

    def test_full_source_and_physical_join_passes(self):
        x=self.run_gate();self.assertTrue(x['native_qualified'],x)

    def test_deleted_token_node_fails(self):
        self.token['nodes'].clear()
        x=self.run_gate();self.assertFalse(x['native_qualified'])
        self.assertIn('TOKEN_NODE_DANGLING',str(x))
        self.assertIn('TOKEN_GRAPH_DIFFERS_FROM_PINNED_LIFECYCLE',str(x))

    def test_deleted_current_program_fails(self):
        self.spec['programs'].clear()
        x=self.run_gate();self.assertFalse(x['native_qualified'])
        self.assertIn('EMITTED_PROGRAM_INVENTORY_DIFFERS',str(x))

    def test_reference_producer_fails(self):
        self.binding['operations']['add']['output_provider']='oracle'
        self.spec['programs'][0]['bindings']=self.reader.add('bindings.json',self.binding)
        x=self.run_gate();self.assertFalse(x['native_qualified'])
        self.assertIn('REFERENCE_OR_BEHAVIORAL_COMPUTE_OUTPUT',str(x))

    def test_stale_routed_source_fails(self):
        self.route['rtl_sha256']={'real_native.sv':'0'*64}
        self.spec['physical_bindings']['top/e']['route']=self.reader.add('route.json',self.route)
        x=self.run_gate();self.assertFalse(x['native_qualified'])
        self.assertIn('ROUTE_RTL_SOURCE_STALE_OR_UNPROVEN',str(x))

    def test_missing_routed_file_fails(self):
        del self.reader.data['lef']
        self.assertFalse(self.run_gate()['native_qualified'])

    def test_current_component_category_does_not_override_missing_chain(self):
        self.spec['physical_bindings'].clear()
        self.spec['category']='closed (TT era)'
        self.assertIn('INSTANCE_HAS_NO_PHYSICAL_BINDING',str(self.run_gate()))

    def test_missing_memory_physical_binding_fails(self):
        self.spec['physical_bindings'].pop('top/m')
        x=self.run_gate();self.assertFalse(x['native_qualified'])
        self.assertIn('TARGET_COMPONENT_HAS_NO_PHYSICAL_BINDING',str(x))
        self.assertFalse(x['nodes']['L0.add']['native_qualified'])

    def test_stale_die_netlist_receipt_fails(self):
        self.reader.data['die.v']=b'module wrong;endmodule'
        self.assertFalse(self.run_gate()['native_qualified'])

    def test_unrecorded_external_exception_fails(self):
        self.binding['components']['wire']=dict(implementation='model',role='off_chip_signal')
        self.spec['programs'][0]['bindings']=self.reader.add('bindings.json',self.binding)
        self.assertIn('EXTERNAL_MODEL_EXCEPTION_UNPROVEN',str(self.run_gate()))

    def test_explicit_external_wire_model_is_permitted(self):
        self.binding['components']['wire']=dict(implementation='model',role='off_chip_signal')
        self.spec['programs'][0]['bindings']=self.reader.add('bindings.json',self.binding)
        self.spec['external_models']={'wire':dict(boundary_kind='network_wire',boundary_ports=['tx','rx'],scope='between dies only',supplies_internal_compute=False)}
        self.assertTrue(self.run_gate()['native_qualified'])


if __name__=='__main__':unittest.main()
