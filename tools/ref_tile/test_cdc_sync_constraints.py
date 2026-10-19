"""Reviewed CDC-exception mode (cdc_sync_constraints.py): structural lint mutants and an actual OpenSTA graph run.

The fixture is a small two-clock Gray-event synchroniser (same structure as the col_su XSER=1 collar). The generic
Liberty from test_async_gray_fifo_constraints is a timing-graph fixture only, never physical or metastability sign-off.
"""
import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import cdc_sync_constraints as S
import clock_entry_constraints as C
from test_async_gray_fifo_constraints import STA, YOSYS, fixture_lib

FIXTURE = r'''
module cdc_fix #(parameter integer MUT = 0) (
  input ck_a, input ck_b, input rst_n, input ev_in, input [3:0] d_in,
  output reg [3:0] d_out, output reg v_out, output reg s_out);
  reg [1:0] rc, ra;
  always @(posedge ck_b) rc <= {rc[0], rst_n};
  always @(posedge ck_a) ra <= {ra[0], rc[1]};
  wire rb_n = rc[1], ra_n = ra[1];
  reg [1:0] seq; reg [3:0] h, pd; reg pv;
  always @(posedge ck_a) pd <= d_in;
  always @(posedge ck_a or negedge ra_n)
    if (!ra_n) begin pv <= 0; seq <= 0; end
    else begin pv <= ev_in; if (pv) seq <= (MUT == 1) ? seq + 1'b1 : {seq[0], ~seq[1]}; end
  always @(posedge ck_a) if (pv || MUT == 4) h <= pd;
  reg [1:0] x1, x2, x3;
  wire ck_x = (MUT == 7) ? ck_a : ck_b;
  always @(posedge ck_x or negedge rb_n)
    if (!rb_n) begin x1 <= 0; x2 <= 0; x3 <= 0; end else begin x1 <= seq; x2 <= x1; x3 <= x2; end
  wire ev = x2 != x3;
  wire cap = (MUT == 3) ? (x1 != x2) : ev;
  always @(posedge ck_b) if (cap || MUT == 5) d_out <= h;
  always @(posedge ck_b or negedge rb_n) if (!rb_n) v_out <= 0; else v_out <= ev;
  always @(posedge ck_b) s_out <= (MUT == 6) ? pd[0] : ~rc[0];
endmodule
'''


def spec(mut=0):
    return dict(name='cdc_fix', top='cdc_fix', kind='tile', sources=['cdc_fix.sv'], params=dict(MUT=mut),
                clock='multiple_cts_roots', clock_port='ck_a', clock_ports=['ck_a', 'ck_b'],
                clock_data_paths='related_pll_ratio',
                clock_relationship=dict(kind='same_pll_fixed_phase', ratio=[4, 3], phase_ps=0),
                clock_entry_domains=dict(
                    core=dict(ratio=[1, 1], ports=['ck_a'], inputs=['ev_in', 'd_in'], outputs=[]),
                    serial=dict(ratio=[4, 3], ports=['ck_b'], inputs=['rst_n'], outputs=['d_out', 'v_out', 's_out'])),
                cdc_synchronizers=[
                    dict(name='event', src_domain='core', dst_domain='serial', source='seq', chain=['x1', 'x2', 'x3'],
                         payload=['h'], sync_max_delay_ps=250, payload_max_delay_ps=833),
                    dict(name='reset', src_domain='serial', dst_domain='core', source='rc[1]',
                         chain=['ra[0]', 'ra[1]'], sync_max_delay_ps=250)])


def async_spec(mut=0):
    """Same fixture on the asynchronous stream833.333 / HBM1024 pair (cdc_synchronizers_async)."""
    s = spec(mut)
    s['clock_data_paths'] = S.ASYNC_POLICY
    s['clock_relationship'] = dict(S.ASYNC_RELATIONSHIP)
    s['clock_entry_domains']['hbm'] = s['clock_entry_domains'].pop('serial')
    s['clock_entry_domains']['hbm']['ratio'] = list(S.ASYNC_RATIO)
    for g in s['cdc_synchronizers']:
        for k in ('src_domain', 'dst_domain'):
            g[k] = 'hbm' if g[k] == 'serial' else g[k]
    return s


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'cdc_fix.sv').write_text(FIXTURE)

    def tearDown(self):
        self.tmp.cleanup()


HIER = r'''
module cdc_hier_stage (input ck, input d, output reg q);
  always @(posedge ck) q <= d;
endmodule
module cdc_hier (input ck_a, input ck_b, input rst_n, input d_in, output reg q_out);
  reg rc; reg [1:0] rs;
  always @(posedge ck_b) rc <= rst_n;
  always @(posedge ck_a) rs <= {rs[0], rc};
  wire pd;
  cdc_hier_stage u_s (.ck(ck_a), .d(d_in), .q(pd));   // a submodule: flatten leaves a $scopeinfo cell
  always @(posedge ck_a or negedge rs[1]) if (!rs[1]) q_out <= 0; else q_out <= pd;
endmodule
'''


class Hierarchy(unittest.TestCase):
    def test_flattened_submodule_admitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'cdc_hier.sv').write_text(HIER)
            s = dict(name='cdc_hier', top='cdc_hier', kind='tile', sources=['cdc_hier.sv'], params={},
                     clock='multiple_cts_roots', clock_port='ck_a', clock_ports=['ck_a', 'ck_b'],
                     clock_data_paths='related_pll_ratio',
                     clock_relationship=dict(kind='same_pll_fixed_phase', ratio=[4, 3], phase_ps=0),
                     clock_entry_domains=dict(
                         core=dict(ratio=[1, 1], ports=['ck_a'], inputs=['d_in'], outputs=['q_out']),
                         serial=dict(ratio=[4, 3], ports=['ck_b'], inputs=['rst_n'], outputs=[])),
                     cdc_synchronizers=[dict(name='reset', src_domain='serial', dst_domain='core', source='rc',
                                             chain=['rs[0]', 'rs[1]'], sync_max_delay_ps=250)])
            record = S.lint(s, root)
            self.assertEqual(record['counts'], dict(source=1, sync1=1, payload=0, capture=0))


class Lint(Fixture):
    def test_admitted_and_bounded_only(self):
        record = S.lint(spec(), self.root)
        self.assertEqual(record['counts'], dict(source=3, sync1=3, payload=4, capture=4))
        self.assertEqual(record['roles']['x1[1]'], ['event', 'sync1', 1])
        self.assertEqual(record['roles']['d_out[2]'], ['event', 'capture', 0])
        text = C.generate(spec(), self.root)
        self.assertIn('ot_cdc_crossing $start $pin $source $cell $source_domain $expected', text)
        self.assertIn('set_max_delay -ignore_clock_latency $bound -from $launch -to $target', text)
        self.assertIn('set_min_delay -ignore_clock_latency 0.0', text)
        self.assertIn('ot_cdc_complete $cells', text)
        for banned in ('set_false_path', 'set_clock_groups', 'set_multicycle_path', 'set_disable_timing'):
            self.assertNotIn(banned, text)

    def test_structural_mutants_refused(self):
        for mut, why in [(1, 'not a Gray counter'), (3, 'stage-1 flop .* drives more than stage 2'),
                         (4, 'changes while the Gray count holds'), (5, 'not gated by the synchronised count'),
                         (6, 'undeclared crossing pd\\[0\\]'), (7, 'not on the destination clock')]:
            with self.subTest(mut=mut), self.assertRaisesRegex(S.CdcError, why):
                S.lint(spec(mut), self.root)

    def test_exception_on_same_domain_path_refused(self):
        s = spec()
        s['cdc_synchronizers'][0]['dst_domain'] = 'core'
        with self.assertRaisesRegex(ValueError, 'same-domain path'):
            C.generate(s, self.root)
        # declared domains differ but the actual chain sits on the source clock (MUT 7): refused on the netlist
        with self.assertRaisesRegex(S.CdcError, 'not on the destination clock'):
            S.lint(spec(7), self.root)

    def test_schema_and_bounds_refused(self):
        for mutate, why in [
            (lambda s: s['cdc_synchronizers'][0].update(false_path=True), 'unsupported keys'),
            (lambda s: s['cdc_synchronizers'][0].update(chain=['x1']), '>= 2 destination-clock stages'),
            (lambda s: s['cdc_synchronizers'][0].update(sync_max_delay_ps=800), 'sync_max_delay_ps must be in'),
            (lambda s: s['cdc_synchronizers'][0].update(payload_max_delay_ps=1100), 'payload_max_delay_ps must be in'),
            (lambda s: s['cdc_synchronizers'][1].update(payload_max_delay_ps=100), 'without payload'),
            (lambda s: s['cdc_synchronizers'][1].update(source='seq'), 'named twice'),
            (lambda s: s.update(sdc_extra=['x.sdc']), 'custom timing hooks'),
            (lambda s: s.update(clock_data_paths='async_gray_fifo'), 'async_gray_fifo'),
            (lambda s: s['cdc_synchronizers'][0].update(source='nope'), 'not found'),
        ]:
            s = spec()
            mutate(s)
            with self.subTest(why=why), self.assertRaisesRegex(ValueError, why):
                S.lint(s, self.root)

    def test_missing_group_for_actual_crossing_refused(self):
        s = spec()
        del s['cdc_synchronizers'][1]
        with self.assertRaisesRegex(S.CdcError, 'undeclared crossing (.*/)?rc\\[1\\]'):
            S.lint(s, self.root)


class AsyncPair(Fixture):
    def test_async_pair_admitted_through_synchronizers(self):
        record = S.lint(async_spec(), self.root)
        self.assertEqual(record['counts'], dict(source=3, sync1=3, payload=4, capture=4))
        self.assertEqual(record['groups']['event']['dst_domain'], 'hbm')
        self.assertFalse(C.related_data(async_spec()))
        self.assertAlmostEqual(S.periods(async_spec())['hbm'], 1024.0, places=3)
        text = C.generate(async_spec(), self.root)
        self.assertIn('set ::ot_ce_related_data 0', text)
        self.assertIn('ot_cdc_crossing $start $pin $source $cell $source_domain $expected', text)
        for banned in ('set_false_path', 'set_clock_groups', 'set_multicycle_path', 'set_disable_timing'):
            self.assertNotIn(banned, text)

    def test_async_structural_mutants_refused(self):
        for mut, why in [(1, 'not a Gray counter'), (4, 'changes while the Gray count holds'),
                         (5, 'not gated by the synchronised count'), (6, 'undeclared crossing pd\\[0\\]'),
                         (7, 'not on the destination clock')]:
            with self.subTest(mut=mut), self.assertRaisesRegex(S.CdcError, why):
                S.lint(async_spec(mut), self.root)

    def test_async_pair_needs_the_declared_structure(self):
        for mutate, why in [
            (lambda s: s.pop('cdc_synchronizers'), 'requires cdc_synchronizers'),
            (lambda s: s.update(clock_relationship=dict(kind='hbm_phy_async_gray_fifo', stream_period_ps=833.333,
                                                         hbm_period_ps=1024.0)), 'requires clock_relationship'),
            (lambda s: s['clock_entry_domains']['hbm'].update(ratio=[4, 3]), 'ratio must be'),
            (lambda s: s['clock_entry_domains']['hbm'].update(ports=['ck_b', 'ck_a']), 'exactly one actual root'),
            (lambda s: s.setdefault('route', {}).update(signoff_period_ps=1000.0), 'stream833.333 primary period'),
            (lambda s: s.update(sdc_extra=['x.sdc']), 'custom timing hooks'),
        ]:
            s = async_spec()
            mutate(s)
            with self.subTest(why=why), self.assertRaisesRegex(ValueError, why):
                C.generate(s, self.root)

    def test_hbm_ratio_still_refused_on_related_profiles(self):
        s = spec()
        s['clock_entry_domains']['serial']['ratio'] = list(S.ASYNC_RATIO)
        with self.assertRaisesRegex(ValueError, 'multiple_cts_roots requires one actual related phase0 root|only related'):
            C.generate(s, self.root)


def sta_case(root, out, name, make_spec=None):
    make_spec = make_spec or spec
    dst = 'hbm' if make_spec is async_spec else 'serial'
    synth = (f'read_verilog -sv -DSYNTHESIS {root / "cdc_fix.sv"}; hierarchy -top cdc_fix; '
             f'synth -top cdc_fix -flatten -noabc; dffunmap; abc -g simple; clean; write_json {out / "fix.json"}')
    p = subprocess.run([YOSYS, '-Q', '-T', '-p', synth], text=True, capture_output=True)
    if p.returncode:
        raise AssertionError(p.stdout + p.stderr)
    data = json.loads((out / 'fix.json').read_text())
    m = data['modules']['cdc_fix']
    (out / 'probe.lib').write_text(fixture_lib(m))
    if name == 'stage1_on_source_clock':     # x1 re-clocked by ck_a: its tag now sits on a same-domain path
        q = m['netnames']['x1']['bits'][0]
        cell = next(c for c in m['cells'].values() if c['type'].startswith('$_DFF') and c['connections']['Q'] == [q])
        cell['connections']['C'] = m['ports']['ck_a']['bits']
    if name == 'payload_into_stage1':        # payload bit wired straight into synchroniser stage 1
        q = m['netnames']['x1']['bits'][0]
        cell = next(c for c in m['cells'].values() if c['type'].startswith('$_DFF') and c['connections']['Q'] == [q])
        cell['connections']['D'] = [m['netnames']['h']['bits'][0]]
    jp, vp = out / f'{name}.json', out / f'{name}.v'
    jp.write_text(json.dumps(data))
    p = subprocess.run([YOSYS, '-Q', '-T', '-p', f'read_json {jp}; write_verilog -noattr -noexpr {vp}'],
                       capture_output=True, text=True)
    if p.returncode:
        raise AssertionError(p.stdout + p.stderr)
    generated = C.generate(make_spec(), root).rsplit('\not_ce_apply\n', 1)[0]
    body = (f'read_liberty {{{out}/probe.lib}}\nread_verilog {{{vp}}}\nlink_design cdc_fix\n'
            + C.clocks(make_spec(), 833.333) + generated
            + f'\nset ins [dict create ev_in core {{d_in[0]}} core {{d_in[1]}} core {{d_in[2]}} core {{d_in[3]}} core rst_n {dst}]\n'
            + f'set outs [dict create {{d_out[0]}} {dst} {{d_out[1]}} {dst} {{d_out[2]}} {dst} {{d_out[3]}} {dst} '
            + f'v_out {dst} s_out {dst}]\n'
            + 'if {[catch {ot_ce_leaf_ownership $ins $outs} message]} {puts stderr $message; exit 1}\n'
            + 'puts ACTUAL_CDC_GRAPH_PASS\nexit 0\n')
    tp = out / f'{name}.tcl'
    tp.write_text(body)
    p = subprocess.run([STA, '-exit', str(tp)], text=True, capture_output=True)
    return p.returncode, p.stdout + p.stderr


@unittest.skipUnless(Path(YOSYS).exists() and Path(STA).exists(), 'Yosys 0.68 and OpenSTA fixture tools required')
class ActualGraph(Fixture):
    def test_actual_graph_normal_and_mutants(self):
        out = self.root / 'sta'
        out.mkdir()
        rc, log = sta_case(self.root, out, 'normal')
        self.assertEqual(rc, 0, log)
        self.assertIn('ACTUAL_CDC_GRAPH_PASS', log)
        self.assertIn('OT_CDC STRUCTURAL_PASS', log)
        self.assertEqual(log.count('OT_CDC BOUNDED event source -> sync1'), 2, log)
        self.assertEqual(log.count('OT_CDC BOUNDED reset source -> sync1'), 1, log)
        self.assertGreaterEqual(log.count('OT_CDC BOUNDED event payload -> capture'), 4, log)
        for name in ('stage1_on_source_clock', 'payload_into_stage1'):
            with self.subTest(case=name):
                rc, log = sta_case(self.root, out, name)
                self.assertNotEqual(rc, 0, log)
                self.assertNotIn('ACTUAL_CDC_GRAPH_PASS', log)
                self.assertIn('OT_CDC:', log)

    def test_actual_graph_async_pair(self):
        out = self.root / 'sta_async'
        out.mkdir()
        rc, log = sta_case(self.root, out, 'normal', async_spec)
        self.assertEqual(rc, 0, log)
        self.assertIn('ACTUAL_CDC_GRAPH_PASS', log)
        self.assertIn('OT_CDC STRUCTURAL_PASS', log)
        self.assertEqual(log.count('OT_CDC BOUNDED event source -> sync1'), 2, log)
        self.assertGreaterEqual(log.count('OT_CDC BOUNDED event payload -> capture'), 4, log)
        for name in ('stage1_on_source_clock', 'payload_into_stage1'):
            with self.subTest(case=name):
                rc, log = sta_case(self.root, out, name, async_spec)
                self.assertNotEqual(rc, 0, log)
                self.assertNotIn('ACTUAL_CDC_GRAPH_PASS', log)
                self.assertIn('OT_CDC:', log)


if __name__ == '__main__':
    unittest.main()
