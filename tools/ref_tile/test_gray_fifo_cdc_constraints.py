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
    def test_launch_aliases_carry_launch_roles_only(self):
        record = G.lint(spec(), self.root)
        aliases = record.get('launch_aliases', {})
        for k, owner in aliases.items():
            self.assertIn(record['roles'][k][0], ('src', 'esrc', 'lsrc'))
            self.assertEqual(record['roles'][k], record['roles'][owner.split('/')[0]])
        print('LAUNCH_ALIASES', sorted(aliases))

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


# ---------------------------------------------------------------------------------------------------------------------
# Extension mode (reviewed_gray_fifo_extensions, ROOT-0330-CDC 2026-10-18): core (two bus-bit roots) | hbm, two reviewed
# ot_hbm_accel_cdc_fifo core -> hbm, one hard macro on core root 1 feeding FIFO 1, an hbm consumer mixing both FIFO
# heads (each head read only while its own FIFO is non-empty), a pointer register (u_f1 rgray) and a level-sync source
# (h_st) that are also gated storage consumers, a declared hbm -> core level synchroniser and a die-constant strap.
EXT_FIXTURE = r"""
module gx_fix #(parameter integer MUT = 0, parameter integer NOMAC = 0) (
  input [1:0] ck_cr, input ck_hbm, input rst_c_n, input rst_h_n, input quad,
  input c_wr, input [3:0] c_wd, output c_full,
  output reg [3:0] h_q, output reg h_v, output reg qh,
  output reg c_fault, output reg qc, output reg c_x);
  wire both = rst_c_n & rst_h_n;
  wire r0, r1, rh;
  ot_reset_sync u_r0(.clk(ck_cr[0]), .async_rst_n(both), .sync_rst_n(r0));
  ot_reset_sync u_r1(.clk(ck_cr[1]), .async_rst_n(both), .sync_rst_n(r1));
  ot_reset_sync u_rh(.clk(ck_hbm), .async_rst_n(both), .sync_rst_n(rh));
  reg [1:0] wa; always @(posedge ck_cr[1]) wa <= wa + 1'b1;
  wire [3:0] rd;
  wire [3:0] madd = (MUT == 1) ? h_q : c_wd;          // MUT 1: macro input from an hbm register (straddles families)
  generate if (NOMAC) begin : g_nm
    assign rd = c_wd ^ {2'b0, wa};
  end else begin : g_m
    fx_ram u_ram(.clk((MUT == 6) ? ck_hbm : ck_cr[1]), .ce(c_wr), .a(wa), .wd(madd), .rd(rd));   // MUT 6: hbm clock
  end endgenerate
  wire e0, e1, f1; wire [3:0] d0, d1;
  wire pop0 = !e0;
  wire pop1 = !e1 && (e0 || d0[3]);                    // u_f1 rgray reads u_f0 storage only while u_f0 is non-empty
  ot_hbm_accel_cdc_fifo #(.W(4), .AW(2)) u_f0(.wclk(ck_cr[0]), .wrst_n(r0), .we(c_wr), .wdata(c_wd), .full(c_full),
    .rd_freed(), .rclk(ck_hbm), .rrst_n(rh), .re(pop0), .rdata(d0), .empty(e0));
  ot_hbm_accel_cdc_fifo #(.W(4), .AW(2)) u_f1(.wclk(ck_cr[1]), .wrst_n(r1), .we(c_wr), .wdata(rd), .full(f1),
    .rd_freed(), .rclk(ck_hbm), .rrst_n(rh), .re(pop1), .rdata(d1), .empty(e1));
  always @(posedge ck_hbm)
    if (MUT == 2) h_q <= d1;                           // MUT 2: u_f1 head read ungated
    else if (!e0 || !e1) h_q <= !e0 ? d0 : d1;
  reg h_st;
  always @(posedge ck_hbm or negedge rh) if (!rh) begin h_v <= 0; h_st <= 0; end
    else begin h_v <= !e0 || !e1; if (!e0 && ^d0) h_st <= 1; end
  (* async_reg = "true" *) reg s1, s2;
  always @(posedge ck_cr[0] or negedge r0) if (!r0) begin s1 <= 0; s2 <= 0; c_fault <= 0; end
    else begin
      s1 <= (MUT == 3) ? (h_st & c_wr) : h_st;         // MUT 3: logic in the synchroniser
      s2 <= s1;
      c_fault <= (MUT == 4) ? (s2 | s1) : s2;          // MUT 4: the metastable stage 1 is consumed
    end
  always @(posedge ck_cr[0]) qc <= quad;
  always @(posedge ck_hbm) qh <= quad;
  always @(posedge ck_cr[0]) c_x <= (MUT == 5) ? h_v : c_wr;   // MUT 5: undeclared hbm -> core crossing
endmodule
"""
FX_BB = '(* blackbox *)\nmodule fx_ram (input clk, input ce, input [1:0] a, input [3:0] wd, output [3:0] rd);\nendmodule\n'
FX_LIB = """library(fx_ram_{c}) {{
  cell(fx_ram) {{
    memory () {{ type : ram; address_width : 2; word_width : 4; }}
    pin(clk) {{ direction : input; clock : true; }}
    pin({ck2}) {{ direction : input; {extra} timing() {{ related_pin : "clk"; timing_type : setup_rising; }} }}
    bus(a) {{ direction : input; timing() {{ related_pin : "clk"; timing_type : setup_rising; }} }}
    bus(wd) {{ direction : input; timing() {{ related_pin : "clk"; timing_type : setup_rising; }} }}
    bus(rd) {{ direction : output; timing() {{ related_pin : "clk"; timing_type : rising_edge; }} }}
  }}
}}
"""
EXT_SOURCES = [G.RESET_SYNC[1], G.REVIEWED['ot_hbm_accel_cdc_fifo']['path']]
EXT_INS = dict(core=['rst_c_n', 'c_wr', 'c_wd', 'quad'], hbm=['rst_h_n'])
EXT_OUTS = dict(core=['c_full', 'c_fault', 'qc', 'c_x'], hbm=['h_q', 'h_v', 'qh'])


def ext_spec(mut=0, nomac=0, straps=('quad',), levels=None):
    view = 'physical/fx/fx_ram'
    s = dict(name='gx_fix', top='gx_fix', kind='tile', params=dict(MUT=mut, NOMAC=nomac),
             sources=EXT_SOURCES + ([] if nomac else [f'{view}/fx_ram_bb.v']) + ['gx_fix.sv'],
             clock='multiple_cts_roots', clock_port='ck_cr[0]', clock_ports=['ck_cr[0]', 'ck_cr[1]', 'ck_hbm'],
             clock_data_paths='reviewed_gray_fifos',
             clock_relationship=dict(kind='independent_clock_families', periods_ps=dict(core=833.333, hbm=1024.0)),
             clock_entry_domains=dict(
                 core=dict(ratio=[1, 1], ports=['ck_cr[0]', 'ck_cr[1]'], inputs=EXT_INS['core'], outputs=EXT_OUTS['core']),
                 hbm=dict(ratio=G.family_ratio('hbm'), ports=['ck_hbm'], inputs=EXT_INS['hbm'], outputs=EXT_OUTS['hbm'])),
             reviewed_gray_fifo_extensions=dict(
                 level_synchronizers=[dict(name='hbm_fault', source='h_st', chain=['s1', 's2'])] if levels is None else levels,
                 die_constant_inputs=list(straps)))
    if not nomac:
        s['macros'] = [dict(view=view, count=1, inst='g_m.u_ram')]
    return s


class ExtFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for f in EXT_SOURCES:
            (self.root / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / f, self.root / f)
        (self.root / 'gx_fix.sv').write_text(EXT_FIXTURE)
        self.view = self.root / 'physical/fx/fx_ram'
        self.view.mkdir(parents=True)
        (self.view / 'fx_ram_bb.v').write_text(FX_BB)
        for c in ('tt', 'ff', 'ss'):
            (self.view / f'fx_ram_{c}.lib').write_text(FX_LIB.format(c=c, ck2='ce', extra=''))

    def tearDown(self):
        self.tmp.cleanup()


@unittest.skipUnless(Path(YOSYS).exists() and Path(YOSYS).with_name('yosys-abc').exists(), 'Yosys 0.68 + yosys-abc required')
class ExtLint(ExtFixture):
    def test_admitted_fifo_macro_level_strap(self):
        record = G.lint(ext_spec(), self.root)
        fifos = {f['scope']: (fid, f) for fid, f in record['fifos'].items()}
        self.assertEqual({k: (f['module'], f['writer'], f['reader']) for k, (_, f) in fifos.items()},
                         dict(u_f0=('ot_hbm_accel_cdc_fifo', 'core', 'hbm'), u_f1=('ot_hbm_accel_cdc_fifo', 'core', 'hbm')))
        f0, f1 = fifos['u_f0'][0], fifos['u_f1'][0]
        self.assertEqual(fifos['u_f0'][1]['pointer_max_delay_ps'], 773.333)     # faster family (core) - 60
        self.assertEqual(fifos['u_f0'][1]['storage_max_delay_ps'], 964.0)       # reader hbm 1024 - 60
        self.assertEqual(list(record['macros'].values()), ['core'])
        self.assertTrue(next(iter(record['macros'])).endswith('u_ram'))
        self.assertEqual(record['levels']['l0'], dict(name='hbm_fault', src='hbm', dst='core', stages=2,
                                                       max_delay_ps=773.333))
        self.assertEqual(record['roles']['s1'], ['lsync1', 'l0', 'lvl', 0])
        self.assertEqual(record['roles']['h_st'], ['lsrc', 'l0', 'lvl', 0])
        self.assertEqual(record['gated']['h_q[0]'], sorted([f0, f1]))           # mixes both FIFO heads
        self.assertEqual(record['gated']['h_st'], [f0])                          # level source AND gated consumer
        self.assertEqual(record['gated']['u_f1.rgray[0]'], [f0])                 # pointer register AND gated consumer
        self.assertEqual(record['strap_crossings'], ['quad->hbm'])
        text = C.generate(ext_spec(), self.root)
        for needle in ('proc ot_gf_ext_crossing', 'ot_gf_strap $start $pin $name $expected $inputs',
                       'set ::ot_gf_levels [dict create {l0} {src hbm dst core bound 773.333}]',
                       '{ot_gf_async $pin $cells $inputs; continue}'):
            self.assertIn(needle, text)
        for banned in ('set_false_path', 'set_clock_groups', 'set_multicycle_path', 'set_disable_timing'):
            self.assertNotIn(banned, text)
        clocks = C.clocks(ext_spec(), 833.333)
        self.assertIn('create_clock -name ot_io_hbm -period 1024.000000000', clocks)
        self.assertIn('[get_ports {ck_cr[1]}]', clocks)

    def test_structural_mutants_refused(self):
        for kw, why in [
                (dict(mut=1), 'macro .*u_ram \\(core\\) input wd reads h_q.* \\(hbm\\); a macro must sit in one clock family'),
                (dict(mut=6), 'macro .*u_ram \\(hbm\\) input .* \\(core\\); a macro must sit in one clock family'),
                (dict(mut=2), 'consumer h_q.* loads FIFO u_f1 storage while the FIFO read-valid is false'),
                (dict(mut=3), 'level synchroniser hbm_fault stage 1 s1 is not a direct flop'),
                (dict(mut=4), 'level synchroniser hbm_fault stage 1 s1 drives more than stage 2'),
                (dict(mut=5), 'unapproved crossing h_v \\(hbm\\) -> c_x \\(core\\)'),
                (dict(straps=()), 'input quad \\(core\\) drives qh \\(hbm\\)'),
                (dict(levels=[]), 'unapproved crossing h_st \\(hbm\\) -> s1 \\(core\\)'),
                (dict(levels=[dict(name='x', source='h_st', chain=['s1'])]), 'needs >= 2 destination stages')]:
            with self.subTest(kw=kw), self.assertRaisesRegex(G.GrayFifoError, why):
                G.lint(ext_spec(**kw), self.root)

    def test_macro_and_schema_refused(self):
        (self.view / 'fx_ram_ff.lib').write_text(FX_LIB.format(c='ff', ck2='ce', extra='clock : true;'))
        with self.assertRaisesRegex(G.GrayFifoError, 'exactly one Liberty clock pin'):
            G.lint(ext_spec(), self.root)
        (self.view / 'fx_ram_ff.lib').write_text(FX_LIB.format(c='ff', ck2='ce', extra=''))
        s = ext_spec()
        s['macros'][0]['count'] = 2
        with self.assertRaisesRegex(G.GrayFifoError, 'differ from the declared macros'):
            G.lint(s, self.root)
        s = ext_spec()
        del s['reviewed_gray_fifo_extensions']
        with self.assertRaisesRegex(ValueError, 'no hard children/macros'):
            C.generate(s, self.root)
        s = ext_spec(nomac=1)
        del s['reviewed_gray_fifo_extensions']
        with self.assertRaisesRegex(G.GrayFifoError, 'clock port ck_cr\\[0\\] is not one actual scalar input'):
            G.lint(s, self.root)                        # bus-bit roots stay refused outside the extension mode
        s = ext_spec()
        s['reviewed_gray_fifo_extensions']['false_paths'] = ['x']
        with self.assertRaisesRegex(ValueError, 'no false paths'):
            C.generate(s, self.root)

    def test_reviewed_fifo_source_pinned(self):
        path = self.root / G.REVIEWED['ot_hbm_accel_cdc_fifo']['path']
        text = path.read_text()
        old = 'wg_r1 <= wgray; wg_r2 <= wg_r1;'
        self.assertEqual(text.count(old), 1)
        path.write_text(text.replace(old, 'wg_r1 <= wgray; wg_r2 <= wgray;'))
        with self.assertRaisesRegex(G.GrayFifoError, 'reviewed source changed'):
            G.lint(ext_spec(), self.root)


def ext_sta_case(root, out, name, mut=0):
    """The extension TCL on the actual OpenSTA graph of the macro-free fixture (NOMAC 1)."""
    sp = ext_spec(mut=mut, nomac=1)
    paths = ' '.join(str(root / f) for f in sp['sources'])
    synth = (f'read_verilog -sv -DSYNTHESIS {paths}; hierarchy -check -top gx_fix -chparam MUT {mut} -chparam NOMAC 1; '
             f'synth -top gx_fix -flatten -noabc; dffunmap; abc -g simple; clean; write_json {out / "fix.json"}')
    p = subprocess.run([YOSYS, '-Q', '-T', '-p', synth], text=True, capture_output=True)
    if p.returncode:
        raise AssertionError(p.stdout + p.stderr)
    data = json.loads((out / 'fix.json').read_text())
    m = data['modules']['gx_fix']
    (out / 'probe.lib').write_text(fixture_lib(m))
    if name == 'level_bypass':             # stage 2 of the level synchroniser fed straight from the hbm source
        q = m['netnames']['s2']['bits'][0]
        cell = next(c for c in m['cells'].values() if c['type'].startswith('$_DFF') and c['connections']['Q'] == [q])
        cell['connections']['D'] = [m['netnames']['h_st']['bits'][0]]
    jp, vp = out / f'{name}.json', out / f'{name}.v'
    jp.write_text(json.dumps(data))
    p = subprocess.run([YOSYS, '-Q', '-T', '-p', f'read_json {jp}; write_verilog -noattr -noexpr {vp}'],
                       capture_output=True, text=True)
    if p.returncode:
        raise AssertionError(p.stdout + p.stderr)
    generated = C.generate(sp, root).rsplit('\not_ce_apply\n', 1)[0]
    ins, outs = [], []
    for table, acc in ((EXT_INS, ins), (EXT_OUTS, outs)):
        for domain, names in table.items():
            for n in names:
                w = len(m['ports'][n]['bits'])
                acc += [f'{{{n}}} {domain}'] if w == 1 else [f'{{{n}[{i}]}} {domain}' for i in range(w)]
    body = (f'read_liberty {{{out}/probe.lib}}\nread_verilog {{{vp}}}\nlink_design gx_fix\n'
            + C.clocks(sp, 833.333) + generated
            + f'\nset ins [dict create {" ".join(ins)}]\nset outs [dict create {" ".join(outs)}]\n'
            + 'if {[catch {ot_ce_leaf_ownership $ins $outs} message]} {puts stderr $::errorInfo; exit 1}\n'
            + 'puts ACTUAL_GX_GRAPH_PASS\nexit 0\n')
    tp = out / f'{name}.tcl'
    tp.write_text(body)
    p = subprocess.run([STA, '-exit', str(tp)], text=True, capture_output=True)
    return p.returncode, p.stdout + p.stderr


@unittest.skipUnless(Path(YOSYS).exists() and Path(STA).exists() and Path(YOSYS).with_name('yosys-abc').exists(),
                     'Yosys 0.68, yosys-abc and OpenSTA fixture tools required')
class ExtActualGraph(ExtFixture):
    def test_actual_graph_normal_and_mutants(self):
        out = self.root / 'sta'
        out.mkdir()
        rc, log = ext_sta_case(self.root, out, 'normal')
        self.assertEqual(rc, 0, log)
        self.assertIn('ACTUAL_GX_GRAPH_PASS', log)
        self.assertIn('OT_GF STRUCTURAL_PASS', log)
        self.assertEqual(log.count('OT_GF BOUNDED level l0'), 1, log)
        self.assertEqual(log.count('OT_GF BOUNDED strap quad'), 1, log)
        self.assertGreaterEqual(log.count('mem mem -> gated'), 4, log)
        self.assertGreaterEqual(log.count('src wptr -> sync1'), 6, log)       # 3-bit Gray pointer of both FIFOs
        rc, log = ext_sta_case(self.root, out, 'level_bypass')
        self.assertNotEqual(rc, 0, log)
        self.assertIn('OT_GF:', log)

# KV-HOSTCL-CDC2 design, ported onto main by KV-HROOT-CDC 2026-10-18: (d) event synchronisers (toggle/ack handshake with
# held payload, as qkd_host_visibility_fence) in a reviewed_gray_fifos leaf, alone and with an extension-mode SRAM macro.
EV_FIXTURE = r"""
module ev_fix #(parameter integer MUT = 0, parameter integer MAC = 1) (
  input ck_core, input ck_host, input rst_core_n, input rst_host_n,
  input [7:0] c_inc, input c_go, output reg c_busy,
  output reg [7:0] h_landed, output reg h_fault,
  input h_wr, input [3:0] h_wd, output h_full, output reg [3:0] c_q,
  input [4:0] h_addr, input h_we, input [127:0] h_wd2, output reg [127:0] h_rd, output reg [127:0] c_rd);
  // core: commit counter, held snapshot published with a toggle request, acknowledge synchronised back
  reg [7:0] commits, snapshot; reg req, ac1, ac2, fc;
  reg rc1, rc2, ack_host, fc1, fc2;
  always @(posedge ck_core or negedge rst_core_n)
    if (!rst_core_n) begin commits <= 0; snapshot <= 0; req <= 0; ac1 <= 0; ac2 <= 0; fc <= 0; c_busy <= 0; end
    else begin
      ac1 <= ack_host; ac2 <= ac1; commits <= commits + c_inc; c_busy <= req ^ ac2;
      if (c_go) fc <= 1'b1;
      if (req == ac2 && commits != snapshot) begin snapshot <= commits; req <= ~req; end
    end
  // host: MUT 1 cuts the request chain to one stage (rc1 consumed); MUT 2 also loads the payload with no event in
  // flight; MUT 6 captures it with no gating at all
  wire rq = (MUT == 1) ? rc1 : rc2;
  always @(posedge ck_host or negedge rst_host_n)
    if (!rst_host_n) begin rc1 <= 0; rc2 <= 0; ack_host <= 0; fc1 <= 0; fc2 <= 0; h_landed <= 0; h_fault <= 0; end
    else begin
      rc1 <= req; rc2 <= rc1; fc1 <= fc; fc2 <= fc1; h_fault <= fc2 | (MUT == 1 && rc2);
      if (rq != ack_host || MUT == 6) begin h_landed <= snapshot; ack_host <= rq; end
      else if (MUT == 2) h_landed <= snapshot ^ 8'h01;
    end
  // host -> core reviewed FIFO
  wire empty; wire [3:0] rdata; wire pop = !empty;
  ot_link_afifo #(.W(4), .AW(2), .SYNC(2)) u_hc (
    .wclk(ck_host), .wrst_n(rst_host_n), .wr(h_wr), .wdata(h_wd), .wfull(h_full), .wfreed(), .ovf(),
    .rclk(ck_core), .rrst_n(rst_core_n), .rd(pop), .rempty(empty), .rdata(rdata), .rcount());
  always @(posedge ck_core) if (pop) c_q <= rdata;
  // host SRAM: MUT 3 clocks it from core (host data pins then cross), MUT 4 from a gated host clock,
  // MUT 5 lets a core register read its output
  reg [4:0] a_q; reg we_q; reg [127:0] wd_q;
  always @(posedge ck_host) begin a_q <= h_addr; we_q <= h_we; wd_q <= h_wd2; end
  wire mclk = (MUT == 3) ? ck_core : (MUT == 4) ? (ck_host & h_we) : ck_host;
  wire [127:0] rd;
  generate if (MAC) begin : g_m
    ot_sram_1r1w_32x128_m1 u_m (.clk(mclk), .r_ce_in(1'b1), .r_addr_in(a_q), .rd_out(rd), .w_ce_in(we_q),
      .w_addr_in(a_q), .wd_in(wd_q), .w_mask_in({128{1'b1}}));
  end else begin : g_nm
    assign rd = wd_q;
  end endgenerate
  always @(posedge ck_host) h_rd <= rd;
  always @(posedge ck_core) c_rd <= (MUT == 5) ? rd : {32{c_q}};
endmodule
"""
EV_MACRO = 'physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1'
EV_INS = dict(core=['rst_core_n', 'c_inc', 'c_go'], host=['rst_host_n', 'h_wr', 'h_wd', 'h_addr', 'h_we', 'h_wd2'])
EV_OUTS = dict(core=['c_busy', 'c_q', 'c_rd'], host=['h_landed', 'h_fault', 'h_full', 'h_rd'])
LINK = 'rtl/link/ot_link_afifo.sv'


def ev_spec(mut=0, chain=('rc1', 'rc2'), seen='ack_host', macros=0, groups=True):
    g = [dict(name='req', src_domain='core', dst_domain='host', source='req', chain=list(chain), payload=['snapshot'],
              sync_max_delay_ps=773.333, payload_max_delay_ps=940.0),
         dict(name='ack', src_domain='host', dst_domain='core', source='ack_host', chain=['ac1', 'ac2'],
              sync_max_delay_ps=773.333),
         dict(name='fault', src_domain='core', dst_domain='host', source='fc', chain=['fc1', 'fc2'],
              sync_max_delay_ps=773.333)]
    if seen:
        g[0]['seen'] = seen
    ports = dict(core='ck_core', host='ck_host')
    s = dict(name='ev_fix', top='ev_fix', kind='tile', params=dict(MUT=mut, MAC=int(bool(macros))),
             sources=[LINK] + ([f'{EV_MACRO}/ot_sram_1r1w_32x128_m1_bb.v'] if macros else []) + ['ev_fix.sv'],
             clock='multiple_cts_roots', clock_port='ck_core', clock_ports=['ck_core', 'ck_host'],
             clock_data_paths='reviewed_gray_fifos',
             clock_relationship=dict(kind='independent_clock_families', periods_ps=dict(core=833.333, host=1000.0)),
             clock_entry_domains={n: dict(ratio=G.family_ratio(n), ports=[ports[n]], inputs=EV_INS[n],
                                          outputs=EV_OUTS[n]) for n in ('core', 'host')})
    if groups:
        s['cdc_synchronizers'] = g
    if macros:
        s['macros'] = [dict(view=EV_MACRO, count=macros, inst='g_m.u_m')]
        s['reviewed_gray_fifo_extensions'] = dict(why='host SRAM (extension mode macros)')
    return s


class EvFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for f in [LINK] + [str(x.relative_to(ROOT)) for x in (ROOT / EV_MACRO).glob('*') if x.suffix in ('.v', '.lib')]:
            (self.root / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / f, self.root / f)
        (self.root / 'ev_fix.sv').write_text(EV_FIXTURE)
        (self.root / 'dd_fix.sv').write_text(DEAD_FIXTURE)

    def tearDown(self):
        self.tmp.cleanup()


# A FIFO whose write side a parameter ties off (as qkd_host_native_qm_debt RMW_EN 0): no synchroniser flop survives.
DEAD_FIXTURE = r"""
module dd_fix (input ck_core, input ck_host, input rst_core_n, input rst_host_n,
  input h_wr, input [3:0] h_wd, output h_full, output reg [3:0] c_q, input c_go, output reg h_f);
  wire empty; wire [3:0] rdata; wire pop = !empty;
  ot_link_afifo #(.W(4), .AW(2), .SYNC(2)) u_hc (
    .wclk(ck_host), .wrst_n(rst_host_n), .wr(h_wr), .wdata(h_wd), .wfull(h_full), .wfreed(), .ovf(),
    .rclk(ck_core), .rrst_n(rst_core_n), .rd(pop), .rempty(empty), .rdata(rdata), .rcount());
  always @(posedge ck_core) if (pop) c_q <= rdata;
  ot_link_afifo #(.W(4), .AW(2), .SYNC(2)) u_dead (
    .wclk(ck_host), .wrst_n(rst_host_n), .wr(1'b0), .wdata(4'd0), .wfull(), .wfreed(), .ovf(),
    .rclk(ck_core), .rrst_n(rst_core_n), .rd(1'b0), .rempty(), .rdata(), .rcount());
  reg fc, f1, f2;
  always @(posedge ck_core or negedge rst_core_n) if (!rst_core_n) fc <= 1'b0; else if (c_go) fc <= 1'b1;
  always @(posedge ck_host or negedge rst_host_n) if (!rst_host_n) begin f1 <= 0; f2 <= 0; h_f <= 0; end
                                                 else begin f1 <= fc; f2 <= f1; h_f <= f2; end
endmodule
"""


def dd_spec(groups=True):
    ports = dict(core='ck_core', host='ck_host')
    ins = dict(core=['rst_core_n', 'c_go'], host=['rst_host_n', 'h_wr', 'h_wd'])
    outs = dict(core=['c_q'], host=['h_full', 'h_f'])
    s = dict(name='dd_fix', top='dd_fix', kind='tile', sources=[LINK, 'dd_fix.sv'],
             clock='multiple_cts_roots', clock_port='ck_core', clock_ports=['ck_core', 'ck_host'],
             clock_data_paths='reviewed_gray_fifos',
             clock_relationship=dict(kind='independent_clock_families', periods_ps=dict(core=833.333, host=1000.0)),
             clock_entry_domains={n: dict(ratio=G.family_ratio(n), ports=[ports[n]], inputs=ins[n], outputs=outs[n])
                                  for n in ('core', 'host')})
    if groups:
        s['cdc_synchronizers'] = [dict(name='fault', src_domain='core', dst_domain='host', source='fc',
                                       chain=['f1', 'f2'], sync_max_delay_ps=773.333)]
    return s


@unittest.skipUnless(Path(YOSYS).exists() and Path(YOSYS).with_name('yosys-abc').exists(), 'Yosys 0.68 + yosys-abc required')
class EventLint(EvFixture):
    def test_admitted(self):
        for macros in (0, 1):
            with self.subTest(macros=macros):
                record = G.lint(ev_spec(macros=macros), self.root)
                self.assertEqual(record['events']['req'], dict(
                    src_domain='core', dst_domain='host', width=1, payload_bits=8, seen=1, sync_max_delay_ps=773.333,
                    payload_max_delay_ps=940.0))
                self.assertEqual(record['counts']['ecap'], 8)               # h_landed, gated by rc2 != ack_host
                self.assertEqual(record['roles']['ack_host'], ['esrc', 'ack', 'ev', 0])   # seen of req, source of ack
                if macros:
                    self.assertEqual(record['macros'], {'g_m.u_m': 'host'})
                text = C.generate(ev_spec(macros=macros), self.root)
                self.assertIn('ot_gf_event_crossing $start $pin', text)
                self.assertIn('set ::ot_gf_events [dict create {ack} {src host dst core width 1 payload 0 sync 773.333',
                              text)
                for banned in ('set_false_path', 'set_clock_groups', 'set_multicycle_path', 'set_disable_timing'):
                    self.assertNotIn(banned, text)

    def test_mutants_refused(self):
        for kw, why in [
            (dict(mut=1), 'req: stage-1 flop rc1.* drives more than stage 2'),            # fence chain cut to 1 stage
            (dict(mut=1, chain=('rc1',)), 'chain needs >= 2 destination-clock stages'),
            (dict(mut=2), 'req: capture h_landed.* loads payload snapshot.* no event'),   # payload captured ungated
            (dict(mut=6), 'req: capture h_landed.* not gated by the synchronised count'),
            (dict(seen=None), 'req: capture h_landed.* loads payload snapshot.* no event'),  # no seen: rc2 alone ungated
            (dict(seen='rc1'), 'seen rc1 is not on|named twice|already|seen rc1'),
            (dict(groups=False), 'unapproved crossing snapshot.* -> h_landed'),                                   # main without (d)
            (dict(mut=5, macros=1), 'macro output g_m.u_m \\(host\\) drives c_rd.* leaf of its own clock family'),
            (dict(mut=3, macros=1), 'macro g_m.u_m \\(core\\) input .* reads .* \\(host\\); a macro must sit in one clock family'),
            (dict(macros=2), 'elaborated macros .* differ from the declared macros'),
        ]:
            with self.subTest(kw=kw), self.assertRaisesRegex(G.GrayFifoError, why):
                G.lint(ev_spec(**kw), self.root)

    def test_event_schema_refused(self):
        for mutate, why in [
            (lambda s: s['cdc_synchronizers'][0].update(sync_max_delay_ps=800.0), 'sync_max_delay_ps must be in'),
            (lambda s: s['cdc_synchronizers'][0].update(payload_max_delay_ps=950.0), 'payload_max_delay_ps must be in'),
            (lambda s: s['cdc_synchronizers'][0].update(dst_domain='core'), 'same-family'),
            (lambda s: s['cdc_synchronizers'][0].update(false_path=1), 'keys'),
        ]:
            s = ev_spec()
            mutate(s)
            with self.subTest(why=why), self.assertRaisesRegex(ValueError, why):
                C.generate(s, self.root)

    def test_constant_chains_only_with_events(self):
        record = G.lint(dd_spec(), self.root)
        self.assertEqual(record['constant_chains'], ['u_dead.wptr', 'u_dead.rptr'])
        self.assertNotIn('u_dead', {f['scope'] for f in record['fifos'].values()})
        with self.assertRaisesRegex(G.GrayFifoError, 'u_dead'):                          # main's FIFO-only mode
            G.lint(dd_spec(groups=False), self.root)

    def test_without_events_sdc_unchanged(self):
        text = C.generate(spec(), FixtureRoot.root(self))
        for proc in ('ot_gf_event_crossing', 'ot_gf_events', 'ot_gf_event_complete'):
            self.assertNotIn(proc, text)


class FixtureRoot:
    @staticmethod
    def root(case):
        for f in REVIEWED:
            (case.root / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / f, case.root / f)
        (case.root / 'gf_fix.sv').write_text(FIXTURE)
        return case.root


def ev_sta_case(root, out, name, s):
    top = s['top']
    paths = ' '.join(str(root / f) for f in s['sources'])
    params = ''.join(f' -chparam {k} {v}' for k, v in sorted(s.get('params', {}).items()))
    synth = (f'read_verilog -sv -DSYNTHESIS {paths}; hierarchy -check -top {top}{params}; '
             f'synth -top {top} -flatten -noabc; dffunmap; abc -g simple; clean; write_json {out / "fix.json"}')
    p = subprocess.run([YOSYS, '-Q', '-T', '-p', synth], text=True, capture_output=True)
    if p.returncode:
        raise AssertionError(p.stdout + p.stderr)
    data = json.loads((out / 'fix.json').read_text())
    m = data['modules'][top]
    (out / 'probe.lib').write_text(fixture_lib(m))

    def flop(net, i):
        q = m['netnames'][net]['bits'][i]
        cells = [c for c in m['cells'].values() if c['type'].startswith('$_DFF') and c['connections']['Q'] == [q]]
        assert len(cells) == 1, (net, cells)
        return cells[0]
    if name == 'event_bypass':             # host takes the core toggle straight into stage 2
        flop('rc2', 0)['connections']['D'] = [m['netnames']['req']['bits'][0]]
    if name == 'event_payload_into_sync':  # a payload bit wired into the request synchroniser
        flop('rc1', 0)['connections']['D'] = [m['netnames']['snapshot']['bits'][3]]
    jp, vp = out / f'{name}.json', out / f'{name}.v'
    jp.write_text(json.dumps(data))
    p = subprocess.run([YOSYS, '-Q', '-T', '-p', f'read_json {jp}; write_verilog -noattr -noexpr {vp}'],
                       capture_output=True, text=True)
    if p.returncode:
        raise AssertionError(p.stdout + p.stderr)
    generated = C.generate(s, root).rsplit('\not_ce_apply\n', 1)[0]
    ins, outs = [], []
    for d, key in ((ins, 'inputs'), (outs, 'outputs')):
        for domain, e in s['clock_entry_domains'].items():
            for n in e[key]:
                w = len(m['ports'][n]['bits'])
                d += [f'{{{n}}} {domain}'] if w == 1 else [f'{{{n}[{i}]}} {domain}' for i in range(w)]
    body = (f'read_liberty {{{out}/probe.lib}}\nread_verilog {{{vp}}}\nlink_design {top}\n'
            + C.clocks(s, 833.333) + generated
            + f'\nset ins [dict create {" ".join(ins)}]\nset outs [dict create {" ".join(outs)}]\n'
            + 'if {[catch {ot_ce_leaf_ownership $ins $outs} message]} {puts stderr $message; exit 1}\n'
            + 'puts ACTUAL_GF_GRAPH_PASS\nexit 0\n')
    tp = out / f'{name}.tcl'
    tp.write_text(body)
    p = subprocess.run([STA, '-exit', str(tp)], text=True, capture_output=True)
    return p.returncode, p.stdout + p.stderr


@unittest.skipUnless(Path(YOSYS).exists() and Path(STA).exists(), 'Yosys 0.68 and OpenSTA fixture tools required')
class EventActualGraph(EvFixture):
    def test_actual_graph_events(self):
        out = self.root / 'sta'
        out.mkdir()
        s = ev_spec()
        rc, log = ev_sta_case(self.root, out, 'normal', s)
        self.assertEqual(rc, 0, log)
        self.assertIn('ACTUAL_GF_GRAPH_PASS', log)
        self.assertIn('OT_GF STRUCTURAL_PASS', log)
        for g in ('req', 'ack', 'fault'):
            self.assertEqual(log.count(f'OT_GF BOUNDED {g} esrc ev -> esync1'), 1, log)
        self.assertGreaterEqual(log.count('OT_GF BOUNDED req epay ev -> ecap'), 8, log)
        for name in ('event_bypass', 'event_payload_into_sync'):
            with self.subTest(case=name):
                rc, log = ev_sta_case(self.root, out, name, s)
                self.assertNotEqual(rc, 0, log)
                self.assertNotIn('ACTUAL_GF_GRAPH_PASS', log)
                self.assertIn('OT_GF:', log)


class PinRegWrapperNames(unittest.TestCase):
    """HKV-HROOT 10-18: recipe-3 pin registers wrap the top as u_ot_pr_core; tagged roles must still resolve."""

    def test_wrapped_name_resolves_and_plain_name_unchanged(self):
        proc = G.TCL[G.TCL.index('proc ot_gf_names'):G.TCL.index('proc ot_gf_role')]
        script = proc + (
            'puts [join [ot_gf_names {u_ot_pr_core.u_a.g_afw.u_af.mem[0][0]}] |]\n'
            'puts [join [ot_gf_names {u_a.mem}] |]\n'
            'puts [join [ot_gf_names {x_u_ot_pr_core.u_a}] |]\n')
        out = subprocess.run(['tclsh'], input=script, text=True, capture_output=True, check=True).stdout.splitlines()
        self.assertEqual(out[0], 'u_ot_pr_core.u_a.g_afw.u_af.mem[0][0]|u_a.g_afw.u_af.mem[0][0]')
        self.assertEqual(out[1], 'u_a.mem')
        self.assertEqual(out[2], 'x_u_ot_pr_core.u_a')


if __name__ == '__main__':
    unittest.main()


# ---------------------------------------------------------------------------------------------------------------------
# Merged online chains (HKV-HRADM3 10-19, qkd_hr_cdc_host/pc r5 'missing actual synchronised pointer crossing f1 ronl'):
# a core -> host and a host -> core ot_qwen_async_fifo_w on the same two clocks and resets.  u_ch's wr_online chain
# (core launch, host stages) and u_hc's rd_online chain are bit-identical; synthesis' opt_merge keeps one of them.
MERGE_FIXTURE = r'''
module gm_fix (input ck_core, input ck_host, input rst_core_n, input rst_host_n,
  input c_wr, input [3:0] c_wd, output c_ready, output reg [3:0] h_q, output reg h_v,
  input h_wr, input [3:0] h_wd, output h_ready, output reg [3:0] c_q, output reg c_v);
  wire hv, cv; wire [3:0] hd, cd;
  ot_qwen_async_fifo_w #(.WIDTH(4), .DEPTH(4)) u_ch (
    .wr_clk(ck_core), .wr_rst_n(rst_core_n), .wr_valid(c_wr), .wr_ready(c_ready), .wr_data(c_wd), .wr_overflow(),
    .rd_clk(ck_host), .rd_rst_n(rst_host_n), .rd_valid(hv), .rd_ready(1'b1), .rd_data(hd), .rd_underflow());
  ot_qwen_async_fifo_w #(.WIDTH(4), .DEPTH(4)) u_hc (
    .wr_clk(ck_host), .wr_rst_n(rst_host_n), .wr_valid(h_wr), .wr_ready(h_ready), .wr_data(h_wd), .wr_overflow(),
    .rd_clk(ck_core), .rd_rst_n(rst_core_n), .rd_valid(cv), .rd_ready(1'b1), .rd_data(cd), .rd_underflow());
  always @(posedge ck_host) if (hv) h_q <= hd;
  always @(posedge ck_host or negedge rst_host_n) if (!rst_host_n) h_v <= 1'b0; else h_v <= hv;
  always @(posedge ck_core) if (cv) c_q <= cd;
  always @(posedge ck_core or negedge rst_core_n) if (!rst_core_n) c_v <= 1'b0; else c_v <= cv;
endmodule
'''
M_INS = dict(core=['rst_core_n', 'c_wr', 'c_wd'], host=['rst_host_n', 'h_wr', 'h_wd'])
M_OUTS = dict(core=['c_ready', 'c_q', 'c_v'], host=['h_ready', 'h_q', 'h_v'])


def merge_spec():
    ports = dict(core='ck_core', host='ck_host')
    return dict(name='gm_fix', top='gm_fix', kind='tile', sources=REVIEWED + ['gm_fix.sv'], params={},
                clock='multiple_cts_roots', clock_port='ck_core', clock_ports=['ck_core', 'ck_host'],
                clock_data_paths='reviewed_gray_fifos',
                clock_relationship=dict(kind='independent_clock_families', periods_ps=dict(core=833.333, host=1000.0)),
                clock_entry_domains={n: dict(ratio=G.family_ratio(n), ports=[ports[n]], inputs=M_INS[n],
                                             outputs=M_OUTS[n]) for n in ('core', 'host')})


def merge_sta_case(root, out, name):
    paths = ' '.join(str(root / f) for f in merge_spec()['sources'])
    synth = (f'read_verilog -sv -DSYNTHESIS {paths}; hierarchy -check -top gm_fix; '
             f'synth -top gm_fix -flatten -noabc; dffunmap; abc -g simple; clean; write_json {out / "fix.json"}')
    p = subprocess.run([YOSYS, '-Q', '-T', '-p', synth], text=True, capture_output=True)
    if p.returncode:
        raise AssertionError(p.stdout + p.stderr)
    data = json.loads((out / 'fix.json').read_text())
    m = data['modules']['gm_fix']
    (out / 'probe.lib').write_text(fixture_lib(m))
    online = sorted(n for n in m['netnames'] if 'online' in n and not m['netnames'][n].get('hide_name'))
    q_of = {n: m['netnames'][n]['bits'][0] for n in online}
    flops = {c['connections']['Q'][0]: c for c in m['cells'].values() if c['type'].startswith('$_DFF')}
    if name == 'merged_partner_broken':
        # the surviving shared chain's stage 1 samples a host register instead of the core online flag
        src = [n for n in online if n.endswith('wr_online') or n.endswith('rd_online')]
        stage1 = [n for n in online if n.endswith('_r1') or n.endswith('_w1')]
        mutated = []
        for s1 in stage1:
            f = flops.get(q_of[s1])
            if f is None:
                continue
            for s in src:
                if f['connections']['D'] == [q_of[s]] and any(x['connections']['Q'] == [q_of[s]] for x in flops.values()):
                    f['connections']['D'] = [m['netnames']['h_v']['bits'][0]]
                    mutated.append(s1)
        assert mutated, online
    jp, vp = out / f'{name}.json', out / f'{name}.v'
    jp.write_text(json.dumps(data))
    p = subprocess.run([YOSYS, '-Q', '-T', '-p', f'read_json {jp}; write_verilog -noattr -noexpr {vp}'],
                       capture_output=True, text=True)
    if p.returncode:
        raise AssertionError(p.stdout + p.stderr)
    s = merge_spec()
    generated = C.generate(s, root).rsplit('\not_ce_apply\n', 1)[0]
    ins, outs = [], []
    for table, acc in ((M_INS, ins), (M_OUTS, outs)):
        for domain, names in table.items():
            for n in names:
                w = len(m['ports'][n]['bits'])
                acc += [f'{{{n}}} {domain}'] if w == 1 else [f'{{{n}[{i}]}} {domain}' for i in range(w)]
    body = (f'read_liberty {{{out}/probe.lib}}\nread_verilog {{{vp}}}\nlink_design gm_fix\n'
            + C.clocks(s, 833.333) + generated
            + f'\nset ins [dict create {" ".join(ins)}]\nset outs [dict create {" ".join(outs)}]\n'
            + 'if {[catch {ot_ce_leaf_ownership $ins $outs} message]} {puts stderr $message; exit 1}\n'
            + 'puts ACTUAL_GF_GRAPH_PASS\nexit 0\n')
    tp = out / f'{name}.tcl'
    tp.write_text(body)
    p = subprocess.run([STA, '-exit', str(tp)], text=True, capture_output=True)
    return p.returncode, p.stdout + p.stderr, online


@unittest.skipUnless(Path(YOSYS).exists() and Path(STA).exists(), 'Yosys 0.68 and OpenSTA fixture tools required')
class MergedOnline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for f in REVIEWED:
            (self.root / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / f, self.root / f)
        (self.root / 'gm_fix.sv').write_text(MERGE_FIXTURE)

    def tearDown(self):
        self.tmp.cleanup()

    def test_merged_online_chain_admitted_once(self):
        out = self.root / 'sta'
        out.mkdir()
        rc, log, online = merge_sta_case(self.root, out, 'normal')
        self.assertEqual(rc, 0, log)
        self.assertIn('ACTUAL_GF_GRAPH_PASS', log)
        self.assertIn('OT_GF STRUCTURAL_PASS', log)
        # synthesis merged the two same-direction online chains (the fixture is the qkd_hr_cdc_host shape) ...
        self.assertEqual(log.count('OT_GF MERGED_ONLINE'), 2, log)
        # ... and every surviving online chain is bounded; pointers are never admitted by the merge rule
        self.assertEqual(log.count('src wonl -> sync1') + log.count('src ronl -> sync1'), 2, log)
        self.assertEqual(log.count('src wptr -> sync1'), 6, log)
        self.assertEqual(log.count('src rptr -> sync1'), 6, log)

    def test_broken_partner_refused(self):
        out = self.root / 'sta'
        out.mkdir()
        rc, log, _ = merge_sta_case(self.root, out, 'merged_partner_broken')
        self.assertNotEqual(rc, 0, log)
        self.assertNotIn('ACTUAL_GF_GRAPH_PASS', log)
        self.assertIn('OT_GF:', log)
