"""Necessary finite source gates before any V1 engine RTL build."""
import hashlib
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import h4_v1_g0_model as M
import h3_qwen_bounded_native as N


@pytest.fixture(scope='module')
def model():return M.build()


def test_all_models_and_audit_opcodes_source_bound(model):
    assert model['coverage']['V1_opcodes']==22
    assert (model['models']['Qwen']['PCs'],model['models']['DeepSeek']['PCs'])==(1737,2213)
    assert (model['models']['Qwen']['families'],model['models']['DeepSeek']['families'])==(21,30)
    assert set(model['opcode_contracts'])==M.V1
    assert all(p['sha256']==hashlib.sha256(M.pinned(p['commit'],p['path'])).hexdigest()for p in model['source_pins'])
    assert not model['actual_H1_binding']['V1_opcode_endpoint'] and not model['engine_RTL_written']


def test_SELECT_third_operand_and_I64_are_not_free():
    a=M.command_cost('SELECT',[32,32,32],32)
    b=M.command_cost('SELECT',[32,64,64],64)
    assert (a['RF_read_vectors'],a['RF_read_pair_transactions'])==(3,2)
    assert (b['RF_read_vectors'],b['RF_read_pair_transactions'],b['RF_write_vectors'])==(5,3,2)
    assert b['third_operand_extra_read_pairs']==2
    assert b['RF_write_physical_mirror_bytes']==2048
    assert b['serialized_service_ticks']>a['serialized_service_ticks']
    assert not b['RMW_codec_cost_recharged']


def test_actual_RF_no_stall_edge_and_positive_ack_cost(model):
    r=model['resource_contract']
    assert r['source_derived_no_stall_RF_read_edges']==3 and r['source_derived_no_stall_RF_write_ACK_edges']==2
    cmd=M.command_cost('IADD64',[64,64],64)
    assert cmd['components']['RF_read']==6 and cmd['components']['RF_write_visible']==4
    assert cmd['native_only_replacement_ticks']<cmd['serialized_service_ticks']
    assert 'never blindly add' in model['cost_interface']['RF']


@pytest.mark.parametrize('change',[{'mirror_ACK':0},{'modulo_latency':float('inf')},{'accept':-1}])
def test_unknown_cost_never_zero_or_invalid(change):
    costs=dict(M.DEFAULT);costs.update(change)
    with pytest.raises(ValueError):M.command_cost('AND',[32,32],32,costs=costs)


@pytest.mark.parametrize('args',[('UNKNOWN',[32],32,128),('F2I',[32],32,128),('AND',[32,32],32,129),('SELECT',[64,64,64],64,128)])
def test_bad_opcode_type_or_unbounded_shape_rejects(args):
    with pytest.raises(ValueError):M.command_cost(*args)


def test_lease_keeps_low_high_ACK_generation_and_reverse():
    c=M.command_cost('SELECT',[32,64,64],64);lease=M.CommandLease();identity=(1,31,7,2**40)
    lease.accept(identity,c)
    with pytest.raises(ValueError):lease.accept(identity,c)
    with pytest.raises(ValueError):lease.compute_complete(identity)
    with pytest.raises(ValueError):lease.read_return((1,31,7,0))
    for _ in range(3):lease.read_return(identity)
    lease.compute_complete(identity)
    with pytest.raises(ValueError):lease.write_ACK(identity,1)
    lease.write_ACK(identity,3)
    with pytest.raises(ValueError):lease.retire(identity,True,True)
    lease.write_ACK(identity,3)
    with pytest.raises(ValueError):lease.retire(identity,True,False)
    lease.retire(identity,True,True);assert lease.live is None


def test_dependency_cost_and_replication_without_clock_claim(model):
    for name,ranks in [('Qwen',2),('DeepSeek',96)]:
        m=model['models'][name]
        assert m['replicas']==32*ranks
        assert m['critical_path']['serialized_single_worker_ticks_upper']>=m['critical_path']['dependency_path_ticks_upper']>0
        assert m['critical_path']['hardware_token_rate'] is None
        assert m['incremental_footprint_mm2_range'][1]>m['incremental_footprint_mm2_range'][0]>0
    assert not model['routing']['single_channel_fits']
    assert model['area']['slot_fit'].startswith('UNKNOWN')
    assert not model['area']['existing_RF_and_C0_area_recharged']


def test_existing_primitive_source_not_replaced():
    source=M.pinned(M.NATIVE,'tools/h3_qwen_bounded_native.py')
    assert Path(N.__file__).read_bytes()==source
    vm=N.NativePrimitiveVM()
    a=vm.primitive('IADD',[np.array([2**63-1],np.int64),np.array([1],np.int64)],{'dtype':'I64'})
    assert a.tolist()==[-2**63]
    assert vm.primitive('SHR',[np.int64(-2),np.int64(1)],{'dtype':'I64'})==np.int64(-1)
    assert vm.primitive('SHR',[np.uint32(0xfffffffe),np.uint32(1)],{'dtype':'U32'})==np.uint32(0x7fffffff)
    with pytest.raises(ValueError):vm.primitive('IMOD',[np.int64(1),np.int64(0)],{'dtype':'I64'})
    with pytest.raises(ValueError):vm.primitive('SHL',[np.int64(1),np.int64(64)],{'dtype':'I64'})
    x=vm.primitive('I2F',[np.array([2**24+1,2**24+3],np.int64)])
    np.testing.assert_array_equal(x.view(np.uint32),np.array([0x4b800000,0x4b800002],np.uint32))
    assert vm.primitive('F2I',[np.float32(-1.75)])==np.int64(-1)
    for value in [np.float32(float('nan')),np.float32(float('inf')),np.float32(2**63)]:
        with pytest.raises(ValueError):vm.primitive('F2I',[value])
    # Integer predicates preserve low-bit differences beyond F32 exactness.
    assert vm.primitive('FCMP_LT',[np.int64(2**60),np.int64(2**60+1)])==1
    nan=np.array(0x7fc12345,np.uint32).view(np.float32)
    assert vm.primitive('FCMP_EQ',[nan,nan])==0 and vm.primitive('FCMP_NE',[nan,nan])==1
    assert vm.primitive('BITCAST_U',[nan])==np.uint32(0x7fc12345)
    assert vm.primitive('FP8_UNPACK',[np.uint8(128)]).view(np.uint32)==0
    with pytest.raises(ValueError):vm.primitive('FP8_UNPACK',[np.uint8(127)])


def test_Dewey_cost_reconciliation_preserves_highword_RMW_and_C0(model):
    command=M.command_cost('SELECT',[32,64,64],64)
    ledger=dict(RF_read_pair_transactions=2,RF_write_vectors=2,native_ticks_per_command=32,
                I64_RMW_already_charged=True,C0_already_charged=True)
    joined=M.reconcile_cost(command,ledger)
    assert joined['additional_RF_read_pairs']==1 and joined['additional_RF_write_vectors']==0
    assert joined['additional_I64_RMW_charge']==0 and joined['additional_C0_charge']==0
    ledger['RF_write_vectors']=3
    with pytest.raises(ValueError,match='scope mismatch'):M.reconcile_cost(command,ledger)
    summary=M.additive_summary(model)
    assert not summary['hardware_admitted'] and set(summary['model_contributions'])=={'Qwen','DeepSeek'}
    assert model['unified_model_join']['read_only']


def test_folded_iterative_modulo_and_FP8_table_are_finite(model):
    mod=M.command_cost('IMOD',[64,64],64,lanes=32)
    assert mod['folded_lane_groups']==4 and mod['native_only_replacement_ticks']==256
    assert mod['lane_group_II_provisional']==64
    r=model['resource_contract']
    assert r['FP8_table_replicas']==32 and r['FP8_table_read_ports_each']==1
    assert r['FP8_table_bits']==127*32*32
    assert r['lane_pipeline_bits']>0 and r['iterative_state_bits']>0
    assert model['area']['FP8_table_constant_mux_bit_equivalents']>0


@pytest.mark.parametrize('op,a,b,expected',[
 ('AND',0x1234,0x00ff,0x34),('OR',0x1200,0x34,0x1234),('XOR',0x1234,0x00ff,0x12cb),
 ('ISUB',-2**63,1,2**63-1),('IMUL',2**62,4,0),('IMOD',-5,3,1),('SHL',1,63,-2**63),
 ('FCMP_EQ',2**60,2**60,1),('FCMP_NE',2**60,2**60+1,1),
 ('FCMP_GT',2**60+1,2**60,1),('FCMP_LT',-2**60,-2**60+1,1),
])
def test_native_integer_bits_and_predicate_source_corners(op,a,b,expected):
    got=N.NativePrimitiveVM().primitive(op,[np.int64(a),np.int64(b)],{'dtype':'I64'})
    assert int(got)==expected


def test_native_SELECT_IOTA_FMAX_FMIN_LDEXP_FP8_and_I8():
    vm=N.NativePrimitiveVM()
    assert vm.primitive('SELECT',[np.uint32(1),np.int64(2**60+1),np.int64(0)],{'dtype':'I64'})==2**60+1
    np.testing.assert_array_equal(vm.primitive('IOTA',[],shape=[8]),np.arange(8,dtype=np.int64))
    pos=np.array(0,np.uint32).view(np.float32);neg=np.array(0x80000000,np.uint32).view(np.float32)
    assert vm.primitive('FMAX',[pos,neg]).view(np.uint32)==0x80000000
    assert vm.primitive('FMIN',[neg,pos]).view(np.uint32)==0
    assert vm.primitive('LDEXP',[np.float32(1),np.int64(2)]).view(np.uint32)==0x40800000
    vm.primitive('LDEXP',[np.float32(1),np.int64(1024)]);assert vm.fault
    with pytest.raises(ValueError):vm.primitive('PACKET_COMMIT',[np.float32(1)])
    vm=N.NativePrimitiveVM()
    np.testing.assert_array_equal(vm.primitive('FP8_PACK',[np.array([0.,-0.,1.,-1.],np.float32)]),[0,0,56,184])
    assert vm.primitive('FP8_UNPACK',[np.uint8(126)]).view(np.uint32)==0x43e00000
    with pytest.raises(ValueError):vm.primitive('FP8_PACK',[np.float32(float('nan'))])
    np.testing.assert_array_equal(vm.primitive('I2F',[np.array([-128,127],np.int8)]).view(np.uint32),[0xc3000000,0x42fe0000])
