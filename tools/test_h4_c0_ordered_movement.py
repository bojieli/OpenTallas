"""Finite lowering and strict native-reference negative gates; no payload run."""
import copy, hashlib, json, unittest
from h4_c0_ordered_movement import strict_api, emit_template, CapacityGate

class MovementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.api=strict_api()
    def fixture(self,n=5000):
        nodes=[dict(op='LOAD',dst='a',src=[],shape=[n],attrs={'dtype':'F32','name':'a'}),
               dict(op='LOAD',dst='b',src=[],shape=[n],attrs={'dtype':'F32','name':'b'}),
               dict(op='FADD',dst='c',src=['a','b'],shape=[n],attrs={})]
        p={'templates':{'t':{'code':nodes,'outputs':{'out':'c'}}}}
        t=dict(execution_path='source_order_live_range_stages',executed_primitive_scalar_projection={'LOAD':2*n,'FADD':n},
            plan={'workspace_upper_bytes':100000},reference_scalar_fallback_admitted=False,no_recomputed_dependency_scalars=True,
            provider_transfer_projection={'read_512B_fragments_upper':2,'write_512B_fragments_upper':1})
        d=dict(schema='H3_DS_FORWARD_BOUNDED_POLYNOMIAL_DISPATCH_V2',automatic_scalar_fallback_templates=0,
            workspace={'rank_cap_bytes':33554432,'base':None},templates={'t':t},source_program_sha256='a'*64,
            PC_dispatch=[dict(pc=0,family='vec',dependencies=[],calls=[{'rank':0,'template':'t','SM_partition':'block256%32'}],
                projected_executed_primitive_scalars=t['executed_primitive_scalar_projection'],
                provider_transfer_projection=t['provider_transfer_projection'])])
        b=dict(schema='H4_DS_NATIVE_SHARED_MOVEMENT_BRIDGE_V1',source_program_sha256=d['source_program_sha256'],
            source_dispatch_sha256=hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            bridge_source_sha256='b'*64,scratch_beat_bytes=64,scratch_capacity_bytes=65536,
            templates={'t':emit_template(p,'t',t,self.api)})
        return p,d,b
    def join(self,p,d,b):return self.api.compose_ds_full_program_services(d,bridge=b,native_program=p)
    def test_source_order_reads_follow_visible_writes_and_reverse(self):
        p,d,b=self.fixture();j=self.join(p,d,b)
        self.assertEqual(j['unknown_shared_template_calls'],0)
        self.assertEqual(j['bound_scratch64_read_subtotal'],626)
        self.assertEqual(j['bound_scratch64_write_ACK_subtotal'],939)
        self.assertLessEqual(b['templates']['t']['finite_occupancy_peak']['scratch_bytes'],65536)
        self.assertFalse(j['hardware_full_native_claim'])
    def test_exact_shape_and_opcode_refs(self):
        p,d,b=self.fixture();b['templates']['t']['ordered_movements'][1]['native_instruction_ref']['result_shape']=[4999]
        with self.assertRaisesRegex(ValueError,'attrs shape mismatch'):self.join(p,d,b)
    def test_missing_operand_never_becomes_zero(self):
        p,d,b=self.fixture();ev=b['templates']['t']['ordered_movements'];ev[:]=[m for m in ev if m['event']!='read64']
        with self.assertRaisesRegex(ValueError,'operand coverage'):self.join(p,d,b)
    def test_read_before_write_rejected(self):
        p,d,b=self.fixture();ev=b['templates']['t']['ordered_movements'];ev[:]=[m for m in ev if not (m['event']=='write64_ACK' and m['source_step']==0)]
        with self.assertRaisesRegex(ValueError,'before source write visibility'):self.join(p,d,b)
    def test_alias_rejected(self):
        p,d,b=self.fixture();ev=b['templates']['t']['ordered_movements'];acq=[m for m in ev if m['event']=='acquire'];acq[1]['base']=0
        with self.assertRaisesRegex(ValueError,'shared live alias'):self.join(p,d,b)
    def test_RF_only_has_complete_exact_operand_routes(self):
        p,d,b=self.fixture(128);j=self.join(p,d,b)
        self.assertEqual(j['bound_scratch64_read_subtotal'],0)
        self.assertEqual(j['unknown_shared_template_calls'],0)
        b['templates']['t']['RF_operand_routes'].pop()
        with self.assertRaisesRegex(ValueError,'operand coverage'):self.join(p,d,b)
    def test_capacity_overflow_is_explicit_gate(self):
        with self.assertRaisesRegex(CapacityGate,'FINITE_SCRATCH_CAPACITY'):self.fixture(10000)
    def test_forward_leaf_never_relabelled_source_order(self):
        p,d,b=self.fixture();t=copy.deepcopy(d['templates']['t']);t['execution_path']='forward_streaming_Q8_matvec'
        with self.assertRaisesRegex(CapacityGate,'FORWARD_LEAF_CONTINUATION'):emit_template(p,'t',t,self.api)

if __name__=='__main__':unittest.main()
