import importlib.util, os, sys
spec = importlib.util.spec_from_file_location('fb', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'failure_breakdown.py'))
fb = importlib.util.module_from_spec(spec); spec.loader.exec_module(fb)
CORES = {'ot_hbm_hc_bank128_pair_core', 'ot_hgi_coll_gq_land', 'ot_hbm_idx_tail_native', 'hnx_vms_bank_q0_faces__vecd4ae'}

def test_variant_rows_are_cores():
    for item, parent in [('ot_hbm_hc_bank128_pair_core__v7d149b37532c', 'ot_hbm_hc_bank128_pair_core'),
                         ('ot_hgi_coll_gq_land__vac72b8c34f86', 'ot_hgi_coll_gq_land'),
                         ('ot_hbm_idx_tail_native__v9496b22d4b49', 'ot_hbm_idx_tail_native'),
                         ('hnx_vms_bank_q0_faces__vecd4ae__v32e0dfcad68a', 'hnx_vms_bank_q0_faces__vecd4ae')]:
        assert fb.is_core_row(item, {'parent_item': parent}, CORES)
        assert fb.is_core_row(item, {'parent_item': ''}, CORES)  # suffix strip alone suffices

def test_plain_core_and_types():
    assert fb.is_core_row('ot_hbm_idx_tail_native#218.592x187.488/6b24', {}, CORES)
    for t in ('hbm_arch_q_b000', 'NE_io', 'col_h10_r2__t1__cl99efd374', 'kv3_hg_v1', 'hnx_vms_bank_q0_faces'):
        assert not fb.is_core_row(t, {'parent_item': ''}, CORES)

if __name__ == '__main__':
    test_variant_rows_are_cores(); test_plain_core_and_types(); print('2 passed')
