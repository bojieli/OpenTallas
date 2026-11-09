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

def test_design_row_by_wave_key():
    did = 'hnx_vms_bank_q0_faces__vecd4ae#270x403.92/b95ff4f969a6c0ba'
    d = {'module': 'hnx_vms_bank_q0_faces__vecd4ae', 'wave_keys': ['hnx_vms_bank_q0_faces__vecd4ae__v39c3624d7cc9']}
    old = {'updated': '2026-11-08 10:00', 'status': 'FAIL'}; new = {'updated': '2026-11-09 10:00', 'status': 'RUNNING'}
    last = {('hbm', 'hnx_vms_bank_q0_faces__vecd4ae__v39c3624d7cc9'): new,
            ('hbm', 'hnx_vms_bank_q0_faces__vecd4ae__v32e0dfcad68a'): old}      # another design's key: never taken
    assert fb.design_row(last, 'hbm', did, d) is new
    assert fb.design_row(last, 'hbm', did, {'module': 'x'}) is None                # no wave key, no module row
    last[('hbm', 'hnx_vms_bank_q0_faces__vecd4ae')] = old
    assert fb.design_row(last, 'hbm', did, {'module': 'x'}) is old                 # module row still the fallback
    last[('hbm', did)] = new
    assert fb.design_row(last, 'hbm', did, {}) is new                              # own id first

if __name__ == '__main__':
    test_variant_rows_are_cores(); test_plain_core_and_types(); test_design_row_by_wave_key(); print('3 passed')
