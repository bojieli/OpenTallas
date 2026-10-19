#!/usr/bin/env python3
"""KVR-LANDLAG 10-19: unit tests of land_lag_sim.py -- the KV die kv-check (pass + mutants) and annotate on a KV slice;
the compute-die annotate path on a die_glue slice (unchanged behaviour)."""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import land_lag_sim as LLS  # noqa: E402

TOOL = HERE / 'land_lag_sim.py'


def planned_e(n):
    return max(2, math.ceil((n - 1) / 2) + 1)


def gen_landed(n, E):
    """kv_fwd_lanes.landed_cost (the KV GEN price)"""
    N = n - 1
    st = (1 + (N - 1) / 2) if N >= 1 else 0
    return st + 1 + E + 1


def kv_die(lanes, kfix=None, foreign_tie=None):
    """a KV die.v with forwarded lanes as kv_fwd_lanes renders them; lanes = [(name, S, n, K)]"""
    kfix = kfix or {}
    out = ['module qkd_kv_die ();', '  wire [35:0] n_x;']
    for nm, S, n, K in lanes:
        K = kfix.get(nm, K)
        ch = [f'rly_{nm}_{j}__s0' for j in range(n)]
        for j, c in enumerate(ch):
            a, b = f'n_{nm}__r{j}[{S - 1}:0]', f'n_{nm}__r{j + 1}[{S - 1}:0]'
            prev = ch[j - 1] if j else None
            if j < n - 1:
                if j == 0:
                    out.append(f'  qkd_rlysh0_{S} {c} (.ck(n_clk_core_c[0]), .en(n_rst_c[0]), .a({a}), .b({b}), '
                               f'.eb(n_{c}__eb[0]), .ck_o(n_{c}__cko[0]));')
                else:
                    out.append(f'  qkd_rlysh_{S} {c} (.ckf(n_{prev}__cko[0]), .ea(n_{prev}__eb[0]), .a({a}), .b({b}), '
                               f'.eb(n_{c}__eb[0]), .ck_o(n_{c}__cko[0]));')
            else:
                hi, lo = f'n_{c}__hi[0]', f'n_{c}__lo[0]'
                kb = [(K >> q) & 1 for q in range(3)]
                ks = ', '.join(f'.k{q}({hi if kb[q] else lo})' for q in range(3))
                if foreign_tie == nm:
                    ks = ks.replace(f'.k0({hi})', '.k0(n_other__hi[0])').replace(f'.k0({lo})', '.k0(n_other__lo[0])')
                tail = (f'.ck(n_clk_core_WS[0]), .rs(n_rst_ws[0]), {ks}, .tie_hi({hi}), .tie_lo({lo}), .b({b}), '
                        f'.fault(n_{c}__flt[0])')
                if n == 1:
                    out.append(f'  qkd_landsh0_{S} {c} (.ck_s(n_clk_core_c[0]), .en(n_rst_c[0]), .a({a}), {tail});')
                else:
                    out.append(f'  qkd_landsh_{S} {c} (.ckf(n_{prev}__cko[0]), .ea(n_{prev}__eb[0]), .a({a}), {tail});')
    out.append('  qkd_kvs_grp slg_WS_0 (.ck(n_clk_core_WS));')
    out.append('endmodule')
    return '\n'.join(out) + '\n'


def kv_lanes(lanes, landed_of):
    rows = []
    for nm, S, n, _ in lanes:
        E = planned_e(n)
        rows.append(dict(stations=[f'rly_{nm}_{j}__s0' for j in range(n)], S=S, n=n, src_tree='c', dst_tree='WS',
                         E_planned=E, K=E % 8 or 8, landed=landed_of(n, E)))
    return dict(schema='opentallas.qwen_kv_fwd_lanes.v1', lanes=rows)


def hw_landed(n, E):
    """the price that matches the hardware: L = E + 1 (o), + the block flop"""
    return E + 2


# straps as the hardware rule wants them: K = (E + h0(n)) mod 8 (G = R0)
GOOD = [('a', 36, 1, (planned_e(1) + 1) % 8), ('b', 36, 3, planned_e(3) % 8), ('c', 528, 15, planned_e(15) % 8),
        ('d', 1, 2, planned_e(2) % 8)]


class KvCheck(unittest.TestCase):
    def run_check(self, lanes, landed_of=hw_landed, **kw):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / 'die.v').write_text(kv_die(lanes, **{k: v for k, v in kw.items() if k in ('kfix', 'foreign_tie')}))
            fl = kv_lanes(lanes, landed_of)
            if kw.get('row_edit'):
                kw['row_edit'](fl)
            (d / 'fwd_lanes.json').write_text(json.dumps(fl))
            p = subprocess.run([sys.executable, str(TOOL), 'kv-check', '--die-v', str(d / 'die.v'), '--lanes',
                                str(d / 'fwd_lanes.json'), '--out', str(d / 'land_lag.json')], capture_output=True, text=True)
            return p.returncode, json.loads((d / 'land_lag.json').read_text()), p.stdout

    def test_pass(self):
        rc, r, out = self.run_check(GOOD)
        self.assertEqual(rc, 0, out)
        self.assertEqual(r['verdict'], 'PASS')
        self.assertEqual(r['crossings'], 4)
        self.assertEqual(r['other_landings']['slg_landing_groups'], 1)
        by = {x['landing']: x for x in r['crossings_detail']}
        self.assertEqual(by['rly_c_14__s0']['L_hw'], planned_e(15) + 1)       # E 8 strapped as K 0 -> E_hw 8
        self.assertEqual(by['rly_a_0__s0']['L_hw'], planned_e(1) + 1)
        self.assertIn('LAND_LAG_KV PASS crossings 4 failing 0', out)

    @staticmethod
    def canonical(fl):
        for r in fl['lanes']:
            r.update(E=r['E_planned'], cal=int(r['n']==1), h0=int(r['n']==1),
                     cal_basis='G-R0+h0', reset_cal=0,
                     age_contract='KVR-FWDAGE: G=R0; source-to-landing-output age E+1')

    def test_canonical_total_calendar_counts_hop0_once(self):
        rc,r,out=self.run_check(GOOD,row_edit=self.canonical)
        self.assertEqual(rc,0,out)
        self.assertEqual(r['crossings_detail'][0]['cal_total'],1)
        self.assertEqual(r['crossings_detail'][0]['L_hw'],3)

    def test_canonical_wrong_strap_still_fails(self):
        rc,r,_=self.run_check(GOOD,row_edit=self.canonical,kfix={'a':4})
        self.assertEqual(rc,1)
        self.assertEqual(r['fail_counts']['strap'],1)
        self.assertEqual(r['fail_counts']['latency'],1)

    def test_unknown_or_inconsistent_calendar_basis_fails_closed(self):
        for key,value in [('cal_basis','invented'),('reset_cal',1),('h0',0)]:
            def edit(fl):
                self.canonical(fl);fl['lanes'][0][key]=value
            rc,r,_=self.run_check(GOOD,row_edit=edit)
            self.assertEqual(rc,1,(key,r))
            self.assertGreater(r['fail_counts']['structure'],0)

    def test_mutant_one_landing_age_off_by_one(self):
        # one landing's K strap one edge late -> its age is off by one: strap + latency FAIL, only that crossing
        rc, r, out = self.run_check(GOOD, kfix={'b': (planned_e(3) + 1) % 8})
        self.assertEqual(rc, 1)
        self.assertEqual(r['verdict'], 'FAIL')
        self.assertEqual(r['failing_crossings'], 1)
        self.assertEqual(r['fail_counts']['strap'], 1)
        self.assertEqual(r['fail_counts']['latency'], 1)
        self.assertIn('rly_b_2__s0', r['fails']['strap'][0])

    def test_mutant_compiled_age_off_by_one(self):
        def edit(fl):
            fl['lanes'][2]['landed'] += 1
        rc, r, _ = self.run_check(GOOD, row_edit=edit)
        self.assertEqual(rc, 1)
        self.assertEqual(r['fail_counts'], dict(structure=0, strap=0, window=0, latency=1))

    def test_kv_gen_fixed_rule_passes(self):
        # KVR-FWDAGE 10-19: the KV GEN's own strap + price functions (kv_fwd_lanes.strap_k / landed_cost) pass kv-check
        sys.path.insert(0, str(HERE.parent / 'qwen_kv_die'))
        import kv_fwd_lanes as FL
        gen = [(nm, S, n, FL.strap_k(n, FL.planned_e(n)) % 8) for nm, S, n, _ in GOOD]
        self.assertEqual(gen, GOOD)
        rc, r, out = self.run_check(gen, landed_of=lambda n, E: FL.landed_cost(n, E)['landed'])
        self.assertEqual(rc, 0, out)
        self.assertEqual(r['fail_counts'], dict(structure=0, strap=0, window=0, latency=0))
        for n in range(1, 100):
            E = FL.planned_e(n)
            self.assertEqual(math.ceil(FL.landed_cost(n, E)['landed'] - 1), E + 1)

    def test_kv_gen_price_and_n1_strap(self):
        # mutant = the KV GEN before KVR-FWDAGE: K = E for n = 1 (no hop-0 en edge) and landed = st + E + 2
        gen = [(nm, S, n, planned_e(n) % 8) for nm, S, n, _ in GOOD]
        rc, r, _ = self.run_check(gen, landed_of=gen_landed)
        self.assertEqual(rc, 1)
        self.assertEqual(r['fail_counts']['strap'], 1)           # the n = 1 landing
        self.assertEqual(r['fail_counts']['window'], 1)          # E_hw 1 < the pilot minimum 2
        self.assertEqual(r['fail_counts']['latency'], 4)         # n = 1: 2 vs 3; n > 1: E + 1 vs ceil(st + E + 1)
        by = {x['landing']: x for x in r['crossings_detail']}
        self.assertEqual(by['rly_c_14__s0']['compiled_age'] - by['rly_c_14__s0']['L_hw'], math.ceil(1 + 13 / 2))

    def test_structure(self):
        def edit(fl):
            fl['lanes'][1]['stations'] = fl['lanes'][1]['stations'][1:]
            fl['lanes'][1]['n'] = 2
        rc, r, _ = self.run_check(GOOD, row_edit=edit)
        self.assertEqual(rc, 1)
        self.assertGreaterEqual(r['fail_counts']['structure'], 1)

    def test_foreign_tie(self):
        rc, r, _ = self.run_check(GOOD, foreign_tie='c')
        self.assertEqual(rc, 1)
        self.assertEqual(r['fail_counts']['strap'], 1)

    def test_missing_row(self):
        def edit(fl):
            fl['lanes'].pop(0)
        rc, r, _ = self.run_check(GOOD, row_edit=edit)
        self.assertEqual(rc, 1)
        self.assertEqual(r['fail_counts']['structure'], 1)


class Annotate(unittest.TestCase):
    def test_kv_slice(self):
        root = HERE.parents[1]
        with tempfile.TemporaryDirectory() as d:
            S = Path(d) / 'sl'
            S.mkdir()
            lanes = [('a', 36, 1, 3), ('b', 36, 3, 2)]
            (S / 'qwk_slice.sv').write_text(kv_die(lanes))
            fl = kv_lanes(lanes, hw_landed)
            fl['lanes'][1]['E_sta'] = 4                                   # a measured residual: LAG 2
            lp = Path(d) / 'fwd_lanes.json'
            lp.write_text(json.dumps(fl))
            wr = root / LLS.KV_LANE_RTL
            ln = root / 'rtl/qwen_split/qfd_fwd_lane.sv'
            (S / 'qwk_slice.f').write_text(f'{ln}\n{wr}\n{S / "qwk_slice.sv"}\n')
            r = LLS.annotate(S, lp)
            self.assertEqual(r['die'], 'qwen_kv')
            self.assertEqual(r['wrappers'], 8)                            # qkd_landsh_{1,36,296,528} + landsh0
            self.assertEqual({x['inst']: x['LAG'] for x in r['landings']}, {'rly_a_0__s0': 0, 'rly_b_2__s0': 2})
            t = (S / 'qwk_slice.sv').read_text()
            self.assertIn('qkd_landsh_36 #(.SIM_LAG(2)) rly_b_2__s0 (', t)
            self.assertIn('qkd_landsh0_36 #(.SIM_LAG(0)) rly_a_0__s0 (', t)
            g = (S / 'qkd_rlysh_lag.sv').read_text()
            self.assertIn('module qkd_landsh_36 #(parameter integer SIM_LAG = 0) (', g)
            self.assertIn('ot_qfd_land_lag #(.LAG(SIM_LAG), .W(36)', g)
            self.assertNotIn('ot_qfd_land #(', g)
            f = (S / 'qwk_slice.f').read_text().splitlines()
            self.assertEqual(f[1], str(ln.parent / 'ot_qfd_land_lag.sv'))
            self.assertEqual(f[2], str((S / 'qkd_rlysh_lag.sv').resolve()))

    def test_kv_slice_missing_row_fails_closed(self):
        root = HERE.parents[1]
        with tempfile.TemporaryDirectory() as d:
            S = Path(d) / 'sl'
            S.mkdir()
            (S / 'qwk_slice.sv').write_text(kv_die([('a', 36, 1, 3)]))
            lp = Path(d) / 'fwd_lanes.json'
            lp.write_text(json.dumps(dict(lanes=[])))
            (S / 'qwk_slice.f').write_text(f'{root / "rtl/qwen_split/qfd_fwd_lane.sv"}\n{root / LLS.KV_LANE_RTL}\n')
            with self.assertRaises(SystemExit):
                LLS.annotate(S, lp)

    def test_compute_slice_unchanged(self):
        # the compute die_glue path: wrappers in die_glue.sv, rows keyed by 'landing', LAG = E_sta - 2
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            S = d / 'sl'
            S.mkdir()
            (d / 'die_glue.sv').write_text('module qfd_landh_16_EW_65x30 (input wire ckf);\n'
                                           '    ot_qfd_land #(.W(16), .D(4), .FIRST(0)) u_land (.ckf(ckf));\nendmodule\n')
            (S / 'qwc.sv').write_text('module t;\n  qfd_landh_16_EW_65x30 rly_dvw_hr_wi_24 (.ckf(x));\nendmodule\n')
            (S / 'qwc.f').write_text(f'/src/rtl/qwen_split/qfd_fwd_lane.sv\n{d / "die_glue.sv"}\n{S / "qwc.sv"}\n')
            lp = d / 'fwd_lanes.json'
            lp.write_text(json.dumps(dict(lanes=[dict(bid='dvw_hr_wi', landing='rly_dvw_hr_wi_24', n=25, E=18, E_sta=7, K=2)])))
            r = LLS.annotate(S, lp)
            self.assertNotIn('die', r)
            self.assertEqual(r['landings'][0]['LAG'], 5)
            self.assertIn('qfd_landh_16_EW_65x30 #(.SIM_LAG(5)) rly_dvw_hr_wi_24 (', (S / 'qwc.sv').read_text())
            self.assertEqual((S / 'qwc.f').read_text().splitlines()[:2],
                             ['/src/rtl/qwen_split/qfd_fwd_lane.sv', '/src/rtl/qwen_split/ot_qfd_land_lag.sv'])
            self.assertTrue((S / 'die_glue_lag.sv').exists())


if __name__ == '__main__':
    unittest.main()
