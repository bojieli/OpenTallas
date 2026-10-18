"""Reviewed Gray-pointer FIFO CDC admission (gray_fifo_cdc_constraints.py): lint mutants and an actual OpenSTA run.

The fixture leaf has three asynchronous clock families (core | host | ingest) and the actual reviewed FIFO sources:
host -> core ot_link_afifo (combinational head, consumer gated by !rempty), core -> ingest ot_qwen_async_fifo_w
(RSEL2 0, consumer gated by rd_valid, reset conditioners fed by both families' resets) and ingest -> host
ot_qwen_async_fifo_w RSEL2 1 (the reviewed registered read stage; consumer reads it enable-free, as the W546 PIPE2
channel does). The generic Liberty is a timing-graph fixture only, never physical or metastability sign-off.
"""
import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import clock_entry_constraints as C
import gray_fifo_cdc_constraints as G
from test_async_gray_fifo_constraints import ROOT, STA, YOSYS

FIXTURE = r'''
module gf_fix #(parameter integer MUT = 0, parameter integer SYNC = 2) (
  input ck_core, input ck_host, input ck_ing,
  input rst_core_n, input rst_host_n, input rst_ing_n,
  input h_wr, input [3:0] h_wd, output h_full,
  output reg [3:0] c_q, output reg c_v,
  input c_wr, input [3:0] c_wd, output c_ready,
  output reg [3:0] i_q, output reg i_v,
  input i_wr, input [3:0] i_wd, output i_ready,
  output reg [3:0] h_q, output reg h_v, output reg s_out);
  // host -> core: combinational FWFT head, popped and captured while !rempty
  wire empty; wire [3:0] rdata;
  wire pop = !empty;
  ot_link_afifo #(.W(4), .AW(2), .SYNC(SYNC)) u_hc (
    .wclk(ck_host), .wrst_n(rst_host_n), .wr(h_wr), .wdata(h_wd), .wfull(h_full), .wfreed(), .ovf(),
    .rclk(ck_core), .rrst_n(rst_core_n), .rd(pop), .rempty(empty), .rdata(rdata), .rcount());
  always @(posedge ck_core or negedge rst_core_n) if (!rst_core_n) c_v <= 1'b0; else c_v <= pop ^ stray;
  // MUT 5: a host reset port drives a core register's asynchronous control
  reg stray;
  wire cap = (MUT == 4) ? c_v : pop;                        // MUT 4: gated by a registered copy, not the FIFO
  always @(posedge ck_core) if (cap || MUT == 3) c_q <= rdata;   // MUT 3: payload read not gated
  // core -> ingest: rd_valid-gated consumer
  wire iv; wire [3:0] id;
  ot_qwen_async_fifo_w #(.WIDTH(4), .DEPTH(4)) u_ci (
    .wr_clk(ck_core), .wr_rst_n(rst_core_n), .wr_valid(c_wr), .wr_ready(c_ready), .wr_data(c_wd), .wr_overflow(),
    .rd_clk(ck_ing), .rd_rst_n(rst_ing_n), .rd_valid(iv), .rd_ready(1'b1), .rd_data(id), .rd_underflow());
  always @(posedge ck_ing) if (iv) i_q <= id;
  always @(posedge ck_ing or negedge rst_ing_n) if (!rst_ing_n) i_v <= 1'b0; else i_v <= iv;
  // ingest -> host: reviewed registered read stage (RSEL2 1), consumer enable-free, valid re-timed one edge
  wire hv; wire [3:0] hd; reg hv_q;
  ot_qwen_async_fifo_w #(.WIDTH(4), .DEPTH(8), .RSEL2(1)) u_ih (
    .wr_clk(ck_ing), .wr_rst_n(rst_ing_n), .wr_valid(i_wr), .wr_ready(i_ready), .wr_data(i_wd), .wr_overflow(),
    .rd_clk(ck_host), .rd_rst_n(rst_host_n), .rd_valid(hv), .rd_ready(1'b1), .rd_data(hd), .rd_underflow());
  always @(posedge ck_host or negedge rst_host_n) if (!rst_host_n) begin hv_q <= 1'b0; h_v <= 1'b0; end
                                                 else begin hv_q <= hv; h_v <= hv_q; end
  always @(posedge ck_host) h_q <= hd;
  // MUT 2: an unsynchronised crossing (ingest flop samples a host register)
  reg hreg; always @(posedge ck_host) hreg <= h_wr;
  always @(posedge ck_ing) s_out <= (MUT == 2) ? hreg : i_v;

  wire stray_rst_n = (MUT == 5) ? rst_host_n : rst_core_n;
  always @(posedge ck_core or negedge stray_rst_n) if (!stray_rst_n) stray <= 1'b0; else stray <= c_wr;
endmodule
'''
REVIEWED = [r['path'] for r in G.REVIEWED.values() if 'async_fifo.sv' not in r['path']] + [G.RESET_SYNC[1]]
INS = dict(core=['rst_core_n', 'c_wr', 'c_wd'], host=['rst_host_n', 'h_wr', 'h_wd'], ingest=['rst_ing_n', 'i_wr', 'i_wd'])
OUTS = dict(core=['c_q', 'c_v', 'c_ready'], host=['h_full', 'h_q', 'h_v'], ingest=['i_q', 'i_v', 'i_ready', 's_out'])


def spec(mut=0, sync=2):
    ports = dict(core='ck_core', host='ck_host', ingest='ck_ing')
    return dict(name='gf_fix', top='gf_fix', kind='tile', sources=REVIEWED + ['gf_fix.sv'],
                params=dict(MUT=mut, SYNC=sync), clock='multiple_cts_roots', clock_port='ck_core',
                clock_ports=['ck_core', 'ck_host', 'ck_ing'], clock_data_paths='reviewed_gray_fifos',
                clock_relationship=dict(kind='independent_clock_families',
                                        periods_ps=dict(core=833.333, host=1000.0, ingest=1666.667)),
                clock_entry_domains={n: dict(ratio=G.family_ratio(n), ports=[ports[n]], inputs=INS[n], outputs=OUTS[n])
                                     for n in ('core', 'host', 'ingest')})


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for f in REVIEWED:
            (self.root / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / f, self.root / f)
        (self.root / 'gf_fix.sv').write_text(FIXTURE)

    def tearDown(self):
        self.tmp.cleanup()


@unittest.skipUnless(Path(YOSYS).exists(), 'Yosys 0.68 required')
class Lint(Fixture):
    def test_admitted_and_bounded_only(self):
        record = G.lint(spec(), self.root)
        fifos = {f['scope']: f for f in record['fifos'].values()}
        self.assertEqual({k: (f['writer'], f['reader']) for k, f in fifos.items()},
                         dict(u_hc=('host', 'core'), u_ci=('core', 'ingest'), u_ih=('ingest', 'host')))
        # pointer bound = faster family - 60; storage bound = reader family - 60
        self.assertEqual(fifos['u_hc']['pointer_max_delay_ps'], 773.333)
        self.assertEqual(fifos['u_hc']['storage_max_delay_ps'], 773.333)
        self.assertEqual(fifos['u_ci']['storage_max_delay_ps'], 1606.667)
        self.assertEqual(fifos['u_ih']['pointer_max_delay_ps'], 940.0)
        self.assertEqual(record['counts']['consumer'], 8)            # c_q and i_q
        self.assertEqual(record['counts']['rstage'], 8)              # u_ih rs_q (2 groups x 4 bits)
        self.assertEqual(record['counts']['rst'], 8)                 # four 2-stage conditioners
        self.assertEqual(record['roles']['c_q[2]'], ['consumer', next(k for k, f in record['fifos'].items()
                                                                      if f['scope'] == 'u_hc'), 'mem', 0])
        text = C.generate(spec(), self.root)
        self.assertIn('ot_gf_crossing $start $pin $source $cell $source_domain $expected', text)
        self.assertIn('{ot_gf_async $pin $cells $inputs; continue}', text)
        self.assertIn('ot_gf_complete $cells', text)
        self.assertIn('set ::ot_ce_related_data 0', text)
        for banned in ('set_false_path', 'set_clock_groups', 'set_multicycle_path', 'set_disable_timing'):
            self.assertNotIn(banned, text)
        clocks = C.clocks(spec(), 833.333)
        for name, period in (('core_clk', '833.333000000'), ('ot_io_host', '1000.000000000'),
                             ('ot_io_ingest', '1666.667000000')):
            self.assertIn(f'create_clock -name {name} -period {period}', clocks)

    def test_two_family_phy_leaf(self):
        s = spec()
        s['clock_entry_domains']['phy'] = s['clock_entry_domains'].pop('host')
        s['clock_entry_domains']['phy']['ratio'] = G.family_ratio('phy')
        s['clock_relationship']['periods_ps'] = dict(core=833.333, phy=1043.0, ingest=1666.667)
        record = G.lint(s, self.root)
        self.assertEqual(next(f for f in record['fifos'].values() if f['scope'] == 'u_hc')['writer'], 'phy')
        self.assertIn('ot_io_phy -period 1043.000000000', C.clocks(s, 833.333))

    def test_structural_mutants_refused(self):
        for kw, why in [(dict(sync=1), 'u_hc .*wptr synchroniser has 1 full-width stage'),
                        (dict(mut=2), 'unapproved crossing hreg \\(host\\) -> s_out \\(ingest\\)'),
                        (dict(mut=3), 'consumer c_q.* loads FIFO u_hc storage .* read-valid is false'),
                        (dict(mut=4), 'consumer c_q.* loads FIFO u_hc storage'),
                        (dict(mut=5), 'cross-family asynchronous control rst_host_n \\(host\\) -> stray \\(core\\)')]:
            with self.subTest(kw=kw), self.assertRaisesRegex(G.GrayFifoError, why):
                G.lint(spec(**kw), self.root)

    def test_reviewed_source_mutants_refused(self):
        path = self.root / 'rtl/link/ot_link_afifo.sv'
        original = path.read_text()
        for old, new in [('wgray_s[0] <= wgray_seam;', 'wgray_s[0] <= wbin;'),          # binary pointer published
                         ('wgray_s[i] <= wgray_s[i-1];', 'wgray_s[i] <= wgray_seam;')]:  # second stage bypassed
            with self.subTest(old=old):
                self.assertEqual(original.count(old), 1)
                path.write_text(original.replace(old, new))
                with self.assertRaisesRegex(G.GrayFifoError, 'reviewed source changed'):
                    G.lint(spec(), self.root)
        path.write_text(original)
        # a look-alike FIFO module from an unreviewed file cannot claim the reviewed identity
        (self.root / 'rogue.sv').write_text(original.replace('module ot_link_afifo', 'module ot_link_afifo'))
        s = spec()
        s['sources'] = [f for f in s['sources'] if f != 'rtl/link/ot_link_afifo.sv'] + ['rogue.sv']
        with self.assertRaisesRegex(G.GrayFifoError, 'does not bind its reviewed source'):
            G.lint(s, self.root)
        (self.root / 'meta.sv').write_text('(* module_src = "x" *) module meta; endmodule\n')
        s = spec()
        s['sources'].append('meta.sv')
        with self.assertRaisesRegex(G.GrayFifoError, 'reserved source/scope metadata'):
            G.lint(s, self.root)

    def test_schema_refused(self):
        for mutate, why in [
            (lambda s: s['clock_relationship']['periods_ps'].update(host=999.0), 'requires clock_relationship'),
            (lambda s: s['clock_entry_domains']['host'].update(ratio=[6, 5]), 'host ratio must be'),
            (lambda s: s['clock_entry_domains'].update(serial=s['clock_entry_domains'].pop('host')), 'clock families'),
            (lambda s: s.update(sdc_extra=['x.sdc']), 'custom timing hooks'),
            (lambda s: s.update(defines=['OT_S81_HOST_PHASESAFE']), 'build defines'),
            (lambda s: s.update(cdc_synchronizers=[]), 'cdc_synchronizers'),
            (lambda s: s.update(clock='hybrid_entries'), 'multiple_cts_roots'),
            (lambda s: s.update(route=dict(signoff_period_ps=900.0, period_ps=770)), '833.333'),
        ]:
            s = spec()
            mutate(s)
            with self.subTest(why=why), self.assertRaisesRegex(ValueError, why):
                C.generate(s, self.root)

    def test_actual_kv_cdc_channel(self):
        """The KV host-cluster channel ot_qwen_die_cdc_ch (phy -> core) at its real parameter shapes (W reduced)."""
        def channel(**params):
            doms = dict(phy=dict(ratio=G.family_ratio('phy'), ports=['wclk'], inputs=['wrst_n', 'i_v', 'i_d'],
                                 outputs=['i_cr', 'w_fault']),
                        core=dict(ratio=[1, 1], ports=['rclk'], inputs=['rrst_n', 'o_cr'], outputs=['o_v', 'o_d', 'r_fault']))
            return dict(top='ot_qwen_die_cdc_ch', kind='tile', clock='multiple_cts_roots', clock_port='rclk',
                        clock_ports=['wclk', 'rclk'], params=dict(W=16, **params), clock_data_paths='reviewed_gray_fifos',
                        sources=['rtl/lib/ot_reset_sync.sv', 'rtl/physical/ot_qwen_async_fifo_w.sv',
                                 'rtl/lib/ot_async_fifo.sv', 'rtl/physical/ot_qwen_die_cdc_ch.sv'],
                        clock_relationship=dict(kind='independent_clock_families', periods_ps=dict(phy=1043.0, core=833.333)),
                        clock_entry_domains=doms)
        pipe2 = G.lint(channel(PIPE=2), ROOT)               # KV host-cluster shape: RSEL2 registered read stage
        self.assertEqual(pipe2['counts']['rstage'], 32)
        self.assertEqual(next(iter(pipe2['fifos'].values()))['pointer_max_delay_ps'], 773.333)
        self.assertEqual(G.lint(channel(PIPE=0), ROOT)['counts']['consumer'], 16)          # send-gated od_q
        with self.assertRaisesRegex(G.GrayFifoError, 'consumer od_q.*read not gated by the FIFO'):
            G.lint(channel(PIPE=1), ROOT)                   # enable-free od_q on a combinational head: refused

    def test_existing_modes_unchanged(self):
        import test_async_gray_fifo_constraints as A
        self.assertNotIn('ot_gf_', C.generate(A.spec(), ROOT))


def fixture_lib(module):
    funcs = {'$_AND_': 'A & B', '$_OR_': 'A | B', '$_XOR_': 'A ^ B', '$_NOT_': '!A', '$_MUX_': '(A & !S) | (B & S)'}
    rows = ['library(probe) { delay_model : table_lookup; time_unit : "1ps"; capacitive_load_unit(1,ff); '
            'nom_voltage : 0.7; nom_temperature : 25; nom_process : 1;']
    arc = 'cell_rise(scalar){values("3");}cell_fall(scalar){values("3");}rise_transition(scalar){values("1");}fall_transition(scalar){values("1");}}'
    for typ in sorted({c['type'] for c in module['cells'].values()} - {'$scopeinfo'}):
        ff = typ.startswith('$_DFF')
        pins = next(c['port_directions'] for c in module['cells'].values() if c['type'] == typ)
        rows.append(f'cell("{typ}") {{area : 1;')
        if ff:
            assert typ in ('$_DFF_P_', '$_DFF_PN0_', '$_DFF_PN1_'), typ
            rows.append('ff(IQ,IQN){clocked_on : "C";next_state : "D";' + {'$_DFF_PN0_': 'clear : "!R";',
                        '$_DFF_PN1_': 'preset : "!R";'}.get(typ, '') + '}')
        for p, d in pins.items():
            rows.append(f'pin({p}){{direction : {d};')
            if d == 'input':
                rows.append('capacitance : 1;' + ('clock : true;' if p == 'C' else ''))
                if ff and p in ('D', 'R'):
                    for kind, val in ([('setup_rising', 2), ('hold_rising', 1)] if p == 'D'
                                      else [('recovery_rising', 2), ('removal_rising', 1)]):
                        rows.append('timing(){related_pin : "C";timing_type : ' + kind + ';rise_constraint(scalar){values("'
                                    + str(val) + '");}fall_constraint(scalar){values("' + str(val) + '");}}')
            else:
                rows.append('function : "' + ('IQ' if ff else funcs[typ]) + '";')
                if typ in ('$_DFF_PN0_', '$_DFF_PN1_'):
                    rows.append('timing(){related_pin : "R";timing_type : ' + ('clear' if typ == '$_DFF_PN0_' else 'preset')
                                + ';timing_sense : ' + ('positive_unate' if typ == '$_DFF_PN0_' else 'negative_unate') + ';' + arc)
                for inp in (['C'] if ff else [k for k, v in pins.items() if v == 'input']):
                    rows.append('timing(){related_pin : "' + inp + '";' + ('timing_type : rising_edge;timing_sense : positive_unate;'
                                if ff else 'timing_sense : non_unate;') + arc)
            rows.append('}')
        rows.append('}')
    return '\n'.join(rows + ['}'])


def sta_case(root, out, name, mut=0):
    paths = ' '.join(str(root / f) for f in spec()['sources'])
    synth = (f'read_verilog -sv -DSYNTHESIS {paths}; hierarchy -check -top gf_fix -chparam MUT {mut}; '
             f'synth -top gf_fix -flatten -noabc; dffunmap; abc -g simple; clean; write_json {out / "fix.json"}')
    p = subprocess.run([YOSYS, '-Q', '-T', '-p', synth], text=True, capture_output=True)
    if p.returncode:
        raise AssertionError(p.stdout + p.stderr)
    data = json.loads((out / 'fix.json').read_text())
    m = data['modules']['gf_fix']
    (out / 'probe.lib').write_text(fixture_lib(m))

    def flop(net, i):
        q = m['netnames'][net]['bits'][i]
        cells = [c for c in m['cells'].values() if c['type'].startswith('$_DFF') and c['connections']['Q'] == [q]]
        assert len(cells) == 1, (net, cells)
        return cells[0]
    if name == 'bypass_second_stage':      # reader takes the writer Gray pointer straight into stage 2
        flop('u_ci.wr_gray_r2', 0)['connections']['D'] = [m['netnames']['u_ci.wr_gray_pub']['bits'][0]]
    if name == 'binary_pointer':           # a binary pointer bit published into the synchroniser
        flop('u_ci.wr_gray_r1', 1)['connections']['D'] = [m['netnames']['u_ci.wr_bin']['bits'][0]]
    if name == 'payload_into_pointer':     # storage wired into a reader pointer register
        flop('u_ci.rd_bin', 0)['connections']['D'] = [m['netnames']['u_ci.mem[0]']['bits'][0]]
    jp, vp = out / f'{name}.json', out / f'{name}.v'
    jp.write_text(json.dumps(data))
    p = subprocess.run([YOSYS, '-Q', '-T', '-p', f'read_json {jp}; write_verilog -noattr -noexpr {vp}'],
                       capture_output=True, text=True)
    if p.returncode:
        raise AssertionError(p.stdout + p.stderr)
    generated = C.generate(spec(), root).rsplit('\not_ce_apply\n', 1)[0]
    ins, outs = [], []
    for domain, names in INS.items():
        for n in names:
            w = len(m['ports'][n]['bits'])
            ins += [f'{{{n}}} {domain}'] if w == 1 else [f'{{{n}[{i}]}} {domain}' for i in range(w)]
    for domain, names in OUTS.items():
        for n in names:
            w = len(m['ports'][n]['bits'])
            outs += [f'{{{n}}} {domain}'] if w == 1 else [f'{{{n}[{i}]}} {domain}' for i in range(w)]
    body = (f'read_liberty {{{out}/probe.lib}}\nread_verilog {{{vp}}}\nlink_design gf_fix\n'
            + C.clocks(spec(), 833.333) + generated
            + f'\nset ins [dict create {" ".join(ins)}]\nset outs [dict create {" ".join(outs)}]\n'
            + 'if {[catch {ot_ce_leaf_ownership $ins $outs} message]} {puts stderr $message; exit 1}\n'
            + 'puts ACTUAL_GF_GRAPH_PASS\nexit 0\n')
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
        self.assertIn('ACTUAL_GF_GRAPH_PASS', log)
        self.assertIn('OT_GF STRUCTURAL_PASS', log)
        record = G.lint(spec(), self.root)
        fid = {f['scope']: k for k, f in record['fifos'].items()}
        # every pointer bit of every chain crosses exactly once (3-bit link pointer, 3/4-bit qwen pointers, online bits)
        self.assertEqual(log.count(f'OT_GF BOUNDED {fid["u_hc"]} src wptr -> sync1'), 3, log)
        self.assertEqual(log.count(f'OT_GF BOUNDED {fid["u_ci"]} src rptr -> sync1'), 3, log)
        self.assertEqual(log.count(f'OT_GF BOUNDED {fid["u_ih"]} src wonl -> sync1'), 1, log)
        self.assertGreaterEqual(log.count(f'OT_GF BOUNDED {fid["u_hc"]} mem mem -> consumer'), 4, log)
        self.assertGreaterEqual(log.count(f'OT_GF BOUNDED {fid["u_ih"]} mem mem -> rstage'), 4, log)
        self.assertGreaterEqual(log.count('OT_GF BOUNDED reset'), 4, log)
        for name in ('bypass_second_stage', 'binary_pointer', 'payload_into_pointer'):
            with self.subTest(case=name):
                rc, log = sta_case(self.root, out, name)
                self.assertNotEqual(rc, 0, log)
                self.assertNotIn('ACTUAL_GF_GRAPH_PASS', log)
                self.assertIn('OT_GF:', log)


if __name__ == '__main__':
    unittest.main()
