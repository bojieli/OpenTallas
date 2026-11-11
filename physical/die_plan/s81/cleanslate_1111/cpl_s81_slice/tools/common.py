import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpl
FAM_BOUND = {'dsdv_slice_c1x_C__t3': 'dsdv_slice_c1x_C__t4', 'ot_s81sl_kv_leaf__t4': 'ot_s81sl_kv_leaf__t1',
             'ot_s81sl_kv_leaf__t5': 'ot_s81sl_kv_leaf__t3'}
def bound_for(n):
    for k in (n, FAM_BOUND.get(n)):
        if k and os.path.exists('bound/%s.sv' % k):
            return open('bound/%s.sv' % k).read(), k
    return None, None
def model(P, conns, n):
    b, src = bound_for(n)
    M = cpl.Model(P, n, conns, bound=b)
    M.bound_src = src
    return M
