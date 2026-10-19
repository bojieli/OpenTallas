import hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strip_clock as sc
import view_targets as vt


def _ins(ss, ff, tt=None, pins=None):
    b = lambda v: {'boundary': {'n': 4, 'mean': v}}
    j = {'ss': b(ss), 'ff': b(ff), 'tt': b(tt) if tt is not None else None}
    if pins:
        j['clock_measurements'] = {p: {'ss': b(v[0]), 'ff': b(v[1]), 'tt': b(v[2])} for p, v in pins.items()}
    return j


def test_convert_real_synth_and_lef_match(tmp_path):
    ref = tmp_path / 'ref_tile'
    for job, lef, val in (('a_old', 'LEF-OLD', 100.0), ('a_new', 'LEF-NEW', 200.0)):
        d = ref / job / 'views' / 'mA'
        d.mkdir(parents=True)
        (d / 'mA.lef').write_text(lef)
        (d / 'insertion.json').write_text(json.dumps(_ins(val, val / 2, pins={'clk_cap': [9.0, 5.0, 7.0]})))
    d = ref / 'b' / 'views' / 'mB'
    d.mkdir(parents=True)
    (d / 'insertion.json').write_text(json.dumps(_ins(80.0, 40.0)))
    case = {'views': {'mA': 'ROUTED_UNBOUND', 'mB': 'ROUTED_UNBOUND', 'mC': 'SYNTH (grant slot outline)',
                      'mD': 'ROUTED_UNBOUND'},
            'consumed_view_sha256': {'mA.lef': hashlib.sha256(b'LEF-NEW').hexdigest()}}
    r = vt.convert(case, str(ref))['masters']
    assert r['mA']['insertion_in_arcs_ps'] == [200.0, 100.0, 150.0]          # tt missing -> (ss + ff) / 2
    assert r['mA']['insertion_per_clock_pin_ps'] == {'clk_cap': [9.0, 5.0, 7.0]}
    assert 'lef_sha_match' in r['mA']['source']
    assert r['mB']['insertion_in_arcs_ps'] == [80.0, 40.0, 60.0]
    assert r['mC'] == {'view': 'SYNTH', 'insertion_in_arcs_ps': [0.0, 0.0, 0.0], 'source': 'SYNTH_IDEAL_R0'}
    assert r['mD']['source'] == 'REAL_NO_INSERTION_JSON' and r['mD']['insertion_in_arcs_ps'] == [0.0, 0.0, 0.0]


# strip_clock.walk on a minimal ODB-like graph: root -> dk buffer -> dk buffer -> two sinks; a sink on the root net too
class _T:
    def __init__(self, inst, name, io, net=None):
        self.inst, self.name, self.io, self.net = inst, name, io, net
        if net:
            net.its.append(self)

    def getIoType(self): return self.io
    def getInst(self): return self.inst
    def getNet(self): return self.net
    def getMTerm(self): return type('M', (), {'getName': lambda s: self.name})()


class _N:
    def __init__(self, n): self.n, self.its = n, []
    def getName(self): return self.n
    def getITerms(self): return self.its


class _I:
    def __init__(self, n): self.n, self.its = n, []
    def getName(self): return self.n
    def getITerms(self): return self.its


def _buf(name, a, y):
    i = _I(name)
    i.its = [_T(i, 'A', 'INPUT', a), _T(i, 'Y', 'OUTPUT', y)]
    return i


def test_strip_walk_collects_sinks_through_clock_cells():
    root, n1, n2 = _N('ckg_pll_x'), _N('n_dkx_1'), _N('n_dkx_2')
    _buf('dkx_g_1', root, n1)
    _buf('dkx_y_2', n1, n2)
    s1, s2, s0 = _I('blk1'), _I('blk2'), _I('blk0')
    _T(s1, 'clk', 'INPUT', n2); _T(s2, 'ck', 'INPUT', n2); _T(s0, 'clk', 'INPUT', root)
    _T(_I('ckgen'), 'pll_x', 'OUTPUT', root)
    sinks, insts = sc.walk(root, lambda n: n.startswith('dkx_'))
    assert sorted(f'{s.getInst().getName()}/{s.name}' for s in sinks) == ['blk0/clk', 'blk1/clk', 'blk2/ck']
    assert sorted(i.getName() for i in insts) == ['dkx_g_1', 'dkx_y_2']
