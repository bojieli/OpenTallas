import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import uarch_model as U

def test_selected_ik128_reuses_body_costs_and_keeps_defaults():
    old=U.dsrom_s81_native_su_prefix();new=U.dsrom_s81_native_su_ik128()
    assert old['parameters']['KVT_SH']==9
    assert new['parameters']['KVT_SH']==11
    assert U.dsrom_s81_native_su_prefix()==old
    for key in ('ports','MACs_per_cycle_peak','operand_bytes_per_edge_peak','native_write_bytes_per_edge_peak',
                'state_bits_floor','staging_DFF_floor_mm2','replicas_per_rank','TP',
                'routing_tracks_data_bundle_floor','adapter_calendar'):
        assert new[key]==old[key]
    assert all(v==0 for v in new['selected_body_delta'].values())
    assert not new['all_KV_formats_qualified']
    assert not new['physical_dynamic_selection_qualified']
    assert not new['SS_FF_in_context']
    assert new['measured_rate_credit']==0

def test_actual_constant_stride_collision_and_selected_full_row_geometry():
    def address(row,dimension,shift):
        return ((row>>4)<<shift)+(dimension<<4)+(row&15)
    assert address(0,32,9)==address(16,0,9)==512
    assert address(0,32,11)!=address(16,0,11)
    # Two adjacent complete blocks have distinct native element addresses.
    selected={address(row,d,11) for row in range(32) for d in range(128)}
    assert selected==set(range(4096))
    new=U.dsrom_s81_native_su_ik128();row=new['target_DY4']
    assert row==1048575
    assert address(row,0,11)==new['target_dimension0_element_address']==134215695
    assert address(row,127,11)==new['target_dimension127_element_address']==134217727
    assert new['selected_address_extent_bytes']==536870912
    assert 'not physical' in new['address_extent_scope']
    assert new['target_dimension127_element_address']<1<<new['parameters']['AW']
    assert new['selected_block_stride_elements']==16*new['IK_dimensions']


def test_final_two_stride_policy_prices_mux_fanout_without_new_state():
    row=U.dsrom_s81_native_su_kvt_stride_policy()
    assert row['shifts']=={128:11,512:13}
    assert row['block_stride_elements']=={128:2048,512:8192}
    assert row['mux_bits_per_rank']==256*30
    assert row['equality_bits_per_rank']==256*24
    assert row['local_select_fanout_per_lane']==30
    assert abs(row['added_cell_proxy_mm2_per_rank']-0.0027648)<1e-12
    assert abs(row['added_cell_proxy_mm2_TP4']-0.0110592)<1e-12
    for key in ('new_ports','new_queues','new_engine_replicas','new_FF_bits','new_pipeline_cycles','added_latency_cycles'):
        assert row[key]==0
    assert row['loaded_path_delay_ps'] is None
    assert not row['loaded_path_SS_FF_closed']
    assert not row['all_KV_formats_qualified']
    assert row['fixed_IK_SH11_minimum_build_independent']
    assert U.dsrom_s81_native_su_prefix()['parameters']['KVT_SH']==9
