#!/usr/bin/env python3
"""HARD-IP types (COORD DECIDES 2026-11-10): a type whose only contents are a reused PHY macro with nothing to place or
route leaves both the type numerator and denominator.  Run: python3 -m pytest -q test_release_tree_hard_ip.py"""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import release_tree_plan as R

LIB = 'physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_tt.lib'


def phy(**kw):
    t = dict(module='ot_qkvd_ucie_x64_phy', hard=True, ft_slots=[], buses=[1],
             contents=[dict(inst='u', module='ot_qkvd_ucie_x64_phy', status='reuse', lib=LIB)])
    t.update(kw)
    return t


def test_qc_like_phy_types_are_hard_ip():
    T = {'phy_ucie_kv': phy(), 'phy_serdes': phy(module='ot_qfd_serdes_112g_x12_phy_s597'),
         'coll_ucie': dict(module='p', cells=66574, contents=[dict(module='ot_qfd_ucie_x64_phy', status='reuse', lib=LIB)])}
    h = R.hard_ip_types(T)
    assert sorted(h) == ['phy_serdes', 'phy_ucie_kv'] and h['phy_ucie_kv']['lib'] == [LIB]


def test_s81_k_only_macro_reports_physical_master():
    T = {'phy__t1': phy(contents=[dict(module='ot_hbm3e_phy_v41x_aw30_e8p5', physical_master='ot_hbm3e_phy_v41x_aw30_e8p5_k',
                                      status='reuse', lib='x_tt.lib', lef='x.lef')])}
    assert R.hard_ip_types(T)['phy__t1'] == dict(macros=['ot_hbm3e_phy_v41x_aw30_e8p5_k'], lef=['x.lef'], lib=['x_tt.lib'])


def test_anything_to_place_or_route_stays_a_type():
    rework = [dict(module='qkd_hbm3e_phy_pc', status='rework', lib=LIB)]
    T = {'kv3_phy': phy(contents=rework),                                         # modeled / reworked PHY
         'kv3_phy_v1': phy(ft_slots=[dict(name='ft0')]),                          # feedthrough to route
         'PHY_NC': phy(cells=1000, contents=[dict(module='m', status='new')]),    # new, cells, no lib
         'wrap': phy(hard_cores=[dict(module='c')]),                              # hard core to place
         'nolib': phy(contents=[dict(module='m', status='reuse')]),               # no committed lib
         'soft': phy(hard=False), 'empty': phy(contents=[])}
    assert R.hard_ip_types(T) == {}
