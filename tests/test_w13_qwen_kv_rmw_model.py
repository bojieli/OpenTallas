import importlib.util
import json,subprocess,sys,pytest
from pathlib import Path
s=importlib.util.spec_from_file_location('rmw',Path(__file__).resolve().parents[1]/'tools/w13_qwen_kv_rmw_model.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)


def test_packed512byte_K_requires_full_read_merge_write_and_ACK_budget():
    d=dict(id=0,layer=0,die=0,position=0,kinds=dict(K=dict(produced_payload_bytes=512,partial_sector_writes_by_stack=[64]*4,full_sector_writes_by_stack=[0]*4,distinct_byte_masks=[0x10001]),V=dict(produced_payload_bytes=512,partial_sector_writes_by_stack=[0]*4,full_sector_writes_by_stack=[0,0,16,0])))
    j=m.price([d]);r=j['rows'][0]
    assert r['port_payload_bytes']==16896 and sum(r['mixed_read_write_commands_by_stack'])==528
    assert r['minimum_shared_stack_command_cycles']==144 and r['write_visible_ACKs']==272
    assert r['merge_two_source_integer_warp_instructions']==768
    assert not j['physical_build_ready'] and j['speed_credit']==0


def test_write_visible_and_reverse_CDC_precede_lock_release_and_no_free_read():
    j=m.lock_calendar();e={x['phase']:x for x in j['events']}
    assert e['loaded_DRAM_read']['end_tick']<=e['merge_XOR_old_new']['start_tick']
    assert e['loaded_DRAM_write_visible']['end_tick']<=e['write_visible_ACK_fabric']['start_tick']
    assert e['reverse_ACK_CDC']['end_tick']<e['release_lock_after_visible_ACK']['end_tick']
    assert m.lock_calendar(write_visible_ns=1000)['total_ticks']>j['total_ticks']
    assert not j['hardware_qualified']


@pytest.fixture(scope='module')
def actual_pinned_manifest(tmp_path_factory):
    root=Path(__file__).resolve().parents[1]
    tree=tmp_path_factory.mktemp('qwen-pinned-KV-model')
    paths=['tools/qwen_hbm_complete_isa.py','tools/qwen_hbm_complete_program.py','compiler/models/qwen3-8b/config.json','compiler/models/qwen3-8b/checkpoint_source.json']
    for path in paths:
        data=subprocess.check_output(['git','show','8d68f3854:'+path],cwd=root)
        dest=tree/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    out=tree/'actual_manifest.json'
    subprocess.run([sys.executable,str(tree/'tools/qwen_hbm_complete_isa.py'),'--out',str(out)],cwd=tree,check=True)
    return json.loads(out.read_text())


@pytest.mark.parametrize('position,stack',[(0,2),(1,3)])
def test_all72_actual_pinned_writers_charge_skew_and_rotating_V_stack(actual_pinned_manifest,position,stack):
    demands=actual_pinned_manifest[f'KV_write_demand_instances_position{position}']
    assert len(demands)==72 and {(r['layer'],r['die']) for r in demands}=={(layer,die) for layer in range(36) for die in range(2)}
    j=m.price(demands)
    expected=[128]*4;expected[stack]=144
    for demand,row in zip(demands,j['rows']):
        V=[0]*4;V[stack]=16
        assert demand['kinds']['V']['full_sector_writes_by_stack']==V
        assert row['mixed_read_write_commands_by_stack']==expected
        assert row['minimum_shared_stack_command_cycles']==144
        assert row['port_payload_bytes']==16896 and row['write_visible_ACKs']==272
    assert j['per_writer_mixed_stack_command_patterns']==[expected]
    assert j['per_writer_stack_cycle_floor_range']==[144,144]
    assert j['total_mixed_commands']==38016 and j['total_port_payload_bytes']==1216512
    for die in ('0','1'):
        assert j['aggregate_mixed_commands_by_die_stack'][die]==[36*x for x in expected]
