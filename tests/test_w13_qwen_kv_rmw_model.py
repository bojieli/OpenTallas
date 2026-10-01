import importlib.util
from pathlib import Path
s=importlib.util.spec_from_file_location('rmw',Path(__file__).resolve().parents[1]/'tools/w13_qwen_kv_rmw_model.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)


def test_packed512byte_K_requires_full_read_merge_write_and_ACK_budget():
    d=dict(id=0,layer=0,die=0,position=0,kinds=dict(K=dict(produced_payload_bytes=512,partial_sector_writes_by_stack=[64]*4,full_sector_writes_by_stack=[0]*4,distinct_byte_masks=[0x10001]),V=dict(produced_payload_bytes=512,partial_sector_writes_by_stack=[0]*4,full_sector_writes_by_stack=[4]*4)))
    j=m.price([d]);r=j['rows'][0]
    assert r['port_payload_bytes']==16896 and sum(r['mixed_read_write_commands_by_stack'])==528
    assert r['minimum_shared_stack_command_cycles']==132 and r['write_visible_ACKs']==272
    assert r['merge_two_source_integer_warp_instructions']==768
    assert not j['physical_build_ready'] and j['speed_credit']==0


def test_write_visible_and_reverse_CDC_precede_lock_release_and_no_free_read():
    j=m.lock_calendar();e={x['phase']:x for x in j['events']}
    assert e['loaded_DRAM_read']['end_tick']<=e['merge_XOR_old_new']['start_tick']
    assert e['loaded_DRAM_write_visible']['end_tick']<=e['write_visible_ACK_fabric']['start_tick']
    assert e['reverse_ACK_CDC']['end_tick']<e['release_lock_after_visible_ACK']['end_tick']
    assert m.lock_calendar(write_visible_ns=1000)['total_ticks']>j['total_ticks']
    assert not j['hardware_qualified']
