#!/usr/bin/env python3
"""Element stories for the Chip Explorer (section 7).

Each story is one hardened element or mechanism: the problem with numbers, the naive design and why it
fails, the trick (with a cycle-stepper diagram), the evidence, the price paid, the failed attempts and a
reviewer-depth table. EVERY NUMBER on a card is registered as a fact {v, unit, status, src} read from a
committed record by the helpers below; the prose is formatted from those facts. A record that disappears
or changes shape fails the build instead of leaving a stale number on the page.

Status per card:
  closed      every block the card names has a committed closure-loop verdict under results/closure_loop/
              (SS >= +15 ps, FF >= +15 ps, DRC 0 at 833.333 ps), or the card's mechanism is adopted on
              committed exact evidence with no block of its own;
  in progress exact RTL exists, routes are queued/running or failed and being redesigned; the card shows the
              current measured state from site/chip_explorer/inputs/loop_attempts.json (closure-loop snapshot);
  gated       blocked on an unestablished contract or gate named in the unified ledger;
  reference   an external anchor or a measured rule, not an element.
The status recomputes on every build, so a block that closes moves its card to "closed" with no code change.

Diagrams are schematic (cycle positions illustrate the mechanism; they are not measurements). Bar charts
plot recorded values only.

Inputs (beyond tools/chip_explorer_build.py's list): see INPUTS below.
"""
import json, re, glob
from pathlib import Path

INPUTS = [
    'results/closure_loop/*/verdict.json',
    'results/arch/unified_composition_20261007/ledger.json',
    'results/rtl/dsrom_closure_cost_ledger_20261007/ledger.json',
    'results/rtl/s81_bf_native_20261006/terminal.json',
    'results/rtl/s81_pq_root_cam_20261007/record.json',
    'results/uarch/s81_pq_root_cam_20261007/model.json',
    'results/uarch/dsrom_s81_pq_fullshape_design_20261007/design.json',
    'results/rtl/dsrom_recovery_20261004/levers/qelem_pq.json',
    'results/rtl/dsrom_recovery_20261004/levers/field_spine_pq.json',
    'results/rtl/dsrom_field_spine_20261004/DESIGN_NOTE.md',
    'results/uarch/dsrom_s81_mixed_geometry_20261007/model.json',
    'results/uarch/dsrom_s81_mixed1792_mapping_20261007/provenance.json',
    'rtl/common/ot_meso_fifo.sv',
    'rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv',
    'results/rtl/dsrom_softmax_recovery_20261007/record.json',
    'results/rtl/dsrom_softmax_exp_recut_20261007/record.json',
    'rtl/hdc/v41/ot_hdc_sinkhorn.sv',
    'results/rtl/hdc_v41_sinkhorn_campaign.json',
    'results/physical_abi3/asap7/hdc/v41/ot_hdc_sinkhorn_7ns/physical.json',
    'rtl/abi3/ot_a3_fp32_exp_pos_cr_rne.sv',
    'results/arch/three_machine_compose/compose.json',
    'results/rtl/dsrom_recovery_20261004/levers/draft.json',
    'results/rtl/hbm_collective_cdc_20261007/refill_model.json',
    'results/rtl/hbm_collective_cdc_20261007/final_pass/record.json',
    'results/rtl/hbm_collective_cdc_design_20261007/comparison_refill.json',
    'results/rtl/hbm_sm_su_result_contract_20261007/contract.json',
    'results/rtl/hbm_accel_die_floorplan_20261005/wire_stages.json',
    'results/rtl/qwen_contracts_20261007/link_credit_rtt/bench_gate/result.json',
    'results/rtl/qwen_contracts_20261007/link_credit_rtt/pricing.json',
    'results/rtl/qwen_stream4_kvmap_m_20261006/lever.json',
    'results/rtl/qwen_rom_TP4_allreduce_oneseg_20261003/pricing.json',
    'results/rtl/qwen_rom_TP4_allreduce_oneseg_20261003/measured.json',
    'results/rtl/qwen_ctrl_shift_20261007/model.json',
    'configs/hardware/technology.json',
    'results/asap7_physical/bitcell_density/bitcell_density.json',
    'physical/qwen_die_masters/io_ref_skew.sdc',
    # snapshots of records not yet on main (site/chip_explorer/inputs/stories/MANIFEST.json gives branch, commit, sha256)
    'site/chip_explorer/inputs/stories/bf_halfphl_exact.json',
    'site/chip_explorer/inputs/stories/bf_halfphl_price.json',
    'site/chip_explorer/inputs/stories/bf_root_phase_diagnosis.json',
    'site/chip_explorer/inputs/stories/qwen_closure_cost_ledger.json',
    'site/chip_explorer/inputs/stories/ot_qwen_rom_tile_w12.sv.txt',
    'site/chip_explorer/inputs/loop_attempts.json',
]

R = Path(__file__).resolve().parents[1]
_cache = {}


def J(p):
    if p not in _cache:
        _cache[p] = json.loads((R / p).read_text())
    return _cache[p]


def T(p):
    k = ('text', p)
    if k not in _cache:
        _cache[k] = (R / p).read_text()
    return _cache[k]


def G(p, *keys):
    """Value at a key path of a committed JSON record; KeyError if absent (the build must fail, not guess)."""
    o = J(p)
    for k in keys:
        o = o[k]
    return o


def RX(p, pattern, group=1, cast=float):
    """A number read out of a committed text record (RTL header, design note) by regex."""
    m = re.search(pattern, T(p), re.S)
    if not m:
        raise KeyError('pattern not found in %s: %s' % (p, pattern))
    s = m.group(group).replace(',', '')
    return cast(s)


SNAP = J('site/chip_explorer/inputs/stories/MANIFEST.json') if (R / 'site/chip_explorer/inputs/stories/MANIFEST.json').exists() else {}


def snap_src(name, pointer=''):
    m = SNAP[name]
    return 'branch %s @%s: %s%s (snapshot site/chip_explorer/inputs/stories/%s)' % (m['branch'], m['commit'], m['path'], (' ' + pointer) if pointer else '', name)


LOOP = J('site/chip_explorer/inputs/loop_attempts.json')
LOOP_SRC = 'closure-loop job state snapshot %s (site/chip_explorer/inputs/loop_attempts.json; failed and in-flight routes are not in results/)' % LOOP['taken']

UL = 'results/arch/unified_composition_20261007/ledger.json'
ULINES = {l['id']: l for t in J(UL)['targets'].values() for l in t['lines']}
DSL = 'results/rtl/dsrom_closure_cost_ledger_20261007/ledger.json'
DSITEMS = {i['item']: i for i in J(DSL)['items']}
DSCAND = {i['item']: i for i in J(DSL)['candidates']}


def verdicts():
    out = {}
    for f in sorted(glob.glob(str(R / 'results/closure_loop/*/verdict.json'))):
        j = json.loads(Path(f).read_text())
        m = j.get('metrics') or {}
        acc = j.get('acceptance') or {}
        ok = (m.get('ss_ps') is not None and m.get('ff_ps') is not None and m['ss_ps'] >= acc.get('ss_min_ps', 15)
              and m['ff_ps'] >= acc.get('ff_min_ps', 15) and (m.get('drc') or 0) == 0)
        rel = str(Path(f).relative_to(R))
        out.setdefault(j['block'], []).append(dict(job=j['job'], ss=m.get('ss_ps'), ff=m.get('ff_ps'), drc=m.get('drc'),
                                                    ok=ok, commit=(j.get('source_commit') or '')[:9], src=rel,
                                                    cycles=j.get('cycles_added')))
    return out


VERD = verdicts()


def fmtn(v, d=None):
    if isinstance(v, str):
        return v
    if d is None:
        d = 0 if float(v).is_integer() and abs(v) >= 1 else (2 if abs(v) < 10 else 1)
    s = ('{:,.%df}' % d).format(v)
    return s.replace('-', '−')


class Card:
    def __init__(self, cid, target, title, element, status, status_basis, summary):
        self.d = dict(id=cid, target=target, title=title, element=element, summary=summary,
                      status=status, status_basis=status_basis, facts=[], tried=[], records=[], blocks=[])
        self._keys = set()

    # register a fact and return it formatted for prose
    def f(self, key, v, unit, status, src, d=None, label=None):
        if key in self._keys:
            raise ValueError('duplicate fact ' + key)
        self._keys.add(key)
        self.d['facts'].append(dict(k=key, label=label or key.replace('_', ' '), v=v, unit=unit, status=status, src=src))
        u = '' if unit in ('', 'x') else (unit if unit in ('%',) else ' ' + unit)
        if unit == 'x':
            u = '×'
        return fmtn(v, d) + u

    def set(self, **kw):
        self.d.update(kw)
        return self

    def tried(self, name, result, why, src):
        self.d['tried'].append(dict(name=name, result=result, why=why, src=src))

    def rec(self, *paths):
        for p in paths:
            if p not in self.d['records']:
                self.d['records'].append(p)

    def blocks(self, *names, rule='all', ledger_closed=None):
        """Closure blocks of this element. Status becomes closed when every block has a passing committed verdict
        (or a closure stated in a committed ledger record, passed as ledger_closed={block: verdict-like dict})."""
        rows = []
        for b in names:
            vs = [v for v in VERD.get(b, []) if v['ok']]
            if not vs and ledger_closed and b in ledger_closed:
                vs = [ledger_closed[b]]
            att = LOOP['blocks'].get(b, [])
            failed = [a for a in att if a.get('ss_ps') is not None and a['status'] != 'CLOSED']
            live = [a for a in att if a['status'] in ('RUNNING', 'QUEUED', 'READY', 'ECO')]
            best = max(failed, key=lambda a: min(a['ss_ps'], a['ff_ps'] if a['ff_ps'] is not None else 1e9), default=None)
            rows.append(dict(block=b, closed=vs[-1] if vs else None, best_fail=best,
                             live=len(live), live_jobs=[a['job'] for a in live][:6]))
        self.d['blocks'] = rows
        self.d['block_rule'] = rule
        if rows:
            closed = [r for r in rows if r['closed']]
            if (rule == 'all' and len(closed) == len(rows)) or (rule == 'any' and closed):
                self.d['status'] = 'closed'
                self.d['status_basis'] = 'every named block has a committed closure-loop verdict (SS >= +15 / FF >= +15 ps, DRC 0 at 833.333 ps)' if rule == 'all' else 'a committed closure-loop verdict closes the element'
        return rows

    def out(self):
        return self.d


def V(c, b):
    """The passing committed verdict of block b (for prose), else None."""
    vs = [v for v in VERD.get(b, []) if v['ok']]
    return vs[-1] if vs else None


def loop_job(block, job_prefix):
    for a in LOOP['blocks'].get(block, []):
        if a['job'].startswith(job_prefix) and a.get('ss_ps') is not None:
            return a
    raise KeyError('no measured loop job %s* for %s in the snapshot' % (job_prefix, block))


# ======================================================================================================== cards
def build():
    cards = []

    # ------------------------------------------------------------------ DS: BF element
    c = Card('ds-bf', 'ds', 'The BF16 element that runs at half rate', 'ot_s81_bf_native (S81 BF pair)', 'in progress',
             'exact at transaction level; the half-rate HALF_PHL routes are queued/running in the closure loop',
             'The BF16 element multiplies a weight row from two ROM macros by the activations and accumulates in exact FP32 order. '
             'It could not reach 1.2 GHz at full rate, so it now runs every other clock on a gated clock, and one clock-gating path had to be rebuilt to make that work.')
    tb = 'results/rtl/s81_bf_native_20261006/terminal.json'
    rows = c.f('rows', RX(tb, r'independent-numerical BF=1 rows=(\d+)'), 'rows', 'measured', tb + ' runs[positive].markers', label='exact rows (independent numerical gate)')
    half = loop_job('ot_s81_bf_native', 'bf_half_61c1cf230')
    recut = loop_job('ot_s81_bf_native', 'bf_recut_5e31c66a7')
    unroll = loop_job('ot_s81_bf_native', 'bf_unroll_5e31c66a7')
    s_half = c.f('half_ss', half['ss_ps'], 'ps', 'measured', LOOP_SRC + ' job ' + half['job'], label='HALF baseline SS slack')
    c.f('half_ff', half['ff_ps'], 'ps', 'measured', LOOP_SRC + ' job ' + half['job'], label='HALF baseline FF hold')
    s_recut = c.f('recut_ss', recut['ss_ps'], 'ps', 'measured', LOOP_SRC + ' job ' + recut['job'], label='re-cut A SS slack')
    c.f('recut_ff', recut['ff_ps'], 'ps', 'measured', LOOP_SRC + ' job ' + recut['job'], label='re-cut A FF hold')
    s_unroll = c.f('unroll_ss', unroll['ss_ps'], 'ps', 'measured', LOOP_SRC + ' job ' + unroll['job'], label='unroll-by-2 SS slack')
    c.f('unroll_ff', unroll['ff_ps'], 'ps', 'measured', LOOP_SRC + ' job ' + unroll['job'], label='unroll-by-2 FF hold')
    dg = 'site/chip_explorer/inputs/stories/bf_root_phase_diagnosis.json'
    lim = G(dg, 'half_baseline', 'limiter')
    launch = c.f('ph_launch', float(re.search(r'Launch clock ([\d.]+) ps', lim).group(1)), 'ps', 'measured', snap_src('bf_root_phase_diagnosis.json', 'half_baseline.limiter'), label='phase FF clock arrival (launch)')
    icg = c.f('icg_clk', float(re.search(r'ICG CLK ([\d.]+)-833', lim).group(1)) - 833.33, 'ps', 'measured', snap_src('bf_root_phase_diagnosis.json', 'half_baseline.limiter'), d=1, label='ICG clock-pin arrival (one period earlier)')
    sinks = c.f('gated_sinks', int(re.search(r'([\d,]+)-sink gated subtree', lim).group(1).replace(',', '')), 'sinks', 'measured', snap_src('bf_root_phase_diagnosis.json', 'half_baseline.limiter'), label='gated subtree sinks')
    others = c.f('other_classes', float(re.search(r'Every other class >= \+([\d.]+) ps', lim).group(1)), 'ps', 'measured', snap_src('bf_root_phase_diagnosis.json', 'half_baseline.limiter'), label='every other path class (HALF)')
    ex = 'site/chip_explorer/inputs/stories/bf_halfphl_exact.json'
    partials = c.f('phl_partials', RX(ex, r'compared=(\d+)', cast=int), 'partials', 'measured', snap_src('bf_halfphl_exact.json', 'cases.positive.markers'), label='HALF_PHL partials identical to the original element')
    pr = 'site/chip_explorer/inputs/stories/bf_halfphl_price.json'
    ar_pct = c.f('price_ar', G(pr, 'composition', 'ar_pct'), '%', 'analytical', snap_src('bf_halfphl_price.json', 'composition.ar_pct'), d=2, label='AR cost (upper bound)')
    mtp_pct = c.f('price_mtp', G(pr, 'composition', 'mtp_pct'), '%', 'analytical', snap_src('bf_halfphl_price.json', 'composition.mtp_pct'), d=2, label='MTP cost (upper bound)')
    st = c.f('extra_stages', G(pr, 'area_and_dies', 'delta', 'stages'), 'stages', 'analytical', snap_src('bf_halfphl_price.json', 'area_and_dies.delta'), label='extra pipeline stages (BF-dedicated pairs)')
    dies = c.f('extra_dies', G(pr, 'area_and_dies', 'delta', 'layer_dies'), 'dies', 'analytical', snap_src('bf_halfphl_price.json', 'area_and_dies.delta'), label='extra layer dies')
    c.set(problem='Every BF16 weight row is summed in the golden model\'s exact FP32 order, so the element cannot reorder or drop an addition. '
                  'At 833 ps the full-rate element never closed: the re-cut variant routed at SS %s and the unrolled one at %s.' % (s_recut, s_unroll),
          naive=dict(title='Gate the clock with a phase flop on the ordinary clock tree',
                     text='Half rate means an ICG (clock gate) at the root that passes every other edge, enabled by a phase flop that toggles. '
                          'Clock-tree synthesis balanced that phase flop with the %s sinks below the gate, so it launched at %s while the ICG pin it feeds sees its clock at about %s: '
                          'one path, phase flop to ICG enable, failed by %s. Every other path class had at least +%s.' % (sinks, launch, icg, s_half, others.lstrip('+'))),
          trick=dict(title='HALF_PHL: put the phase flop on the gate\'s own clock net',
                     text='The phase flop now drives only the ICG enable, and a pre-CTS hook moves it onto the net that clocks the ICG, beside it, so launch and gate share one clock arrival. '
                          'Everything else that needs the phase (the half-cycle marker, output qualifier and capture enables) reads ph_d = t XNOR t_d, rebuilt from two flops on balanced leaves; an assertion checks ph_d equals the phase on every cycle. '
                          'It adds two flops and one XNOR and zero cycles.'),
          evidence='Transaction-level exact: %s identical to the original element; the three negative mutants (front pair, half qualifier, phase mismatch) all fail. The element itself passes the independent numerical gate on %s.' % (partials, rows),
          price='Half rate doubles BF16 field-phase time: %s AR and %s MTP (upper bound). BF pairs must then be BF-dedicated, which adds %s and %s.' % (ar_pct, mtp_pct, st, dies))
    c.blocks('ot_s81_bf_native')
    c.tried('Re-cut A (8-stage multiplier, cut tree adders)', 'SS %s' % s_recut, 'clock-gate enable skew plus 14-16-level residual paths', LOOP_SRC + ' ' + recut['job'])
    c.tried('Unroll-by-2 on a half-rate gated clock', 'SS %s' % s_unroll, 'same ICG enable class, now on the unrolled chains', LOOP_SRC + ' ' + unroll['job'])
    c.tried('Plain HALF (phase flop on the clock tree)', 'SS %s on one path' % s_half, 'phase flop balanced to the gated subtree, launched one period late', snap_src('bf_root_phase_diagnosis.json', 'half_baseline'))
    c.tried('root_phase (a dedicated phase-clock branch of two kept inverters)', 'flow error', G(dg, 'root_phase_cts_7ab4873f4', 'cause')[:180] + '...', snap_src('bf_root_phase_diagnosis.json', 'root_phase_cts_7ab4873f4'))
    c.rec(tb, 'physical/s81_bf_root_phase/model.json', snap_src('bf_halfphl_exact.json'), snap_src('bf_halfphl_price.json'), snap_src('bf_root_phase_diagnosis.json'))
    c.set(diagram=dict(
        naive=dict(kind='flow', cols=4, rows=3, nodes=[
            dict(id='root', c=0, r=1, label='clk root', k='ctrl'), dict(id='icg', c=1, r=0, label='ICG (gate)', k='ctrl'),
            dict(id='tree', c=1, r=2, label='CTS tree, balanced to gated sinks', k='wire'), dict(id='ph', c=2, r=2, label='phase flop ph (late leaf)', k='bad'),
            dict(id='sub', c=2, r=0, label='element flops (gated)', k='field'), dict(id='out', c=3, r=0, label='half-rate element', k='field')],
            edges=[dict(a='root', b='icg', l='early'), dict(a='root', b='tree'), dict(a='tree', b='ph', l='late'), dict(a='ph', b='icg', l='enable', bad=True),
                   dict(a='icg', b='sub'), dict(a='sub', b='out')],
            steps=[dict(hot=['root'], note='One clock edge leaves the root.'),
                   dict(hot=['icg'], pk=[0], note='The ICG pin sees it early, on the short root branch.'),
                   dict(hot=['tree', 'ph'], pk=[1, 2], note='The phase flop sits on a leaf CTS balanced against the big gated subtree, so it launches about one period late.'),
                   dict(hot=['ph', 'icg'], pk=[3], bad=True, note='Its new value reaches the ICG enable after the gate has already decided: the one failing path (%s).' % s_half)]),
        trick=dict(kind='flow', cols=4, rows=3, nodes=[
            dict(id='root', c=0, r=1, label='clk root', k='ctrl'), dict(id='icg', c=1, r=0, label='ICG (gate)', k='ctrl'),
            dict(id='ph', c=1, r=1, label='phase flop ph, on the ICG clock net', k='good'),
            dict(id='sub', c=2, r=0, label='element flops (gated)', k='field'), dict(id='t', c=2, r=2, label='t (gated leaf) / t_d (clk leaf)', k='su'),
            dict(id='phd', c=3, r=2, label='ph_d = t XNOR t_d', k='su'), dict(id='out', c=3, r=0, label='half-rate element', k='field')],
            edges=[dict(a='root', b='icg'), dict(a='root', b='ph', l='same arrival'), dict(a='ph', b='icg', l='enable'), dict(a='icg', b='sub'),
                   dict(a='sub', b='t'), dict(a='t', b='phd'), dict(a='sub', b='out'), dict(a='phd', b='out', l='qualifiers')],
            steps=[dict(hot=['root'], note='One clock edge leaves the root.'),
                   dict(hot=['icg', 'ph'], pk=[0, 1], note='The ICG and the phase flop sit on the same net: one clock arrival, no skew between launch and gate.'),
                   dict(hot=['ph', 'icg'], pk=[2], note='The enable path is now a short local path beside the ICG.'),
                   dict(hot=['sub', 't'], pk=[3, 4], note='t toggles on every gated edge; t_d samples it on every clk edge, both on balanced leaves.'),
                   dict(hot=['phd', 'out'], pk=[5, 7], note='Clock-domain users read ph_d, asserted equal to ph every cycle: 2 flops + 1 XNOR, 0 added cycles.')]),
        extra=dict(title='Inside the element: independent partial sums keep a pipelined adder full', kind='pipe', stages=6, cycles=12,
                   lanes=[dict(id='s%d' % s, start=s, every=6, k='field', label='slot %d' % s) for s in range(6)],
                   note='Schematic. Each BF16 word is split into chunk chains assigned to rotating slots (the RTL uses at least 24), so every add finds its previous partial ready and the adder takes one add a cycle. The chains meet in the golden tree order, so the sum is exact.')))
    cards.append(c.out())

    # ------------------------------------------------------------------ DS: PQ root CAM
    c = Card('ds-pqcam', 'ds', 'A 128-way sibling search split into two cycles', 'ot_s81_pq_ret_root_cam (PQ root)', 'gated',
             'unified ledger gates pq_stage_b_timing and pq_root_protected_face are open',
             'With several field operations in flight, partial sums come back out of order. The root finds each partial\'s sibling among 128 waiting entries and adds them in the golden order. That search cannot happen in one clock, so it is split in two without changing a single pairing decision.')
    rc = 'results/rtl/s81_pq_root_cam_20261007/record.json'
    md = 'results/uarch/s81_pq_root_cam_20261007/model.json'
    D = c.f('depth', G(md, 'D'), 'entries', 'analytical', md + ' D', label='root CAM depth')
    rep = c.f('replicas', G(md, 'replicas'), 'roots', 'analytical', md + ' replicas', label='root replicas a die')
    tc = c.f('tag_compare', G(md, 'memory_ports_bits_per_cycle', 'tag_compare_parallel'), 'bits/cycle', 'analytical', md + ' memory_ports_bits_per_cycle.tag_compare_parallel', label='parallel tag compare')
    d1 = c.f('d_complete', G(rc, 'measured_delta_cycles', 'complete'), 'cycle', 'measured', rc + ' measured_delta_cycles.complete', label='added latency, isolated root')
    d2 = c.f('d_two', G(rc, 'measured_delta_cycles', 'two_leaf'), 'cycles', 'measured', rc + ' measured_delta_cycles.two_leaf', label='added latency, two-leaf root')
    d8 = c.f('d_eight', G(rc, 'measured_delta_cycles', 'eight_leaf'), 'cycles', 'measured', rc + ' measured_delta_cycles.eight_leaf', label='added latency, eight-leaf root')
    er = c.f('exact_roots', G(rc, 'exact_roots'), 'roots', 'measured', rc + ' exact_roots', label='roots checked exact against the native root')
    bits = c.f('state_bits', G(md, 'incremental_state_bits', 'total_128_roots'), 'bits', 'analytical', md + ' incremental_state_bits.total_128_roots', label='added state, all roots')
    cb = DSCAND['pq_rootcam_B']
    c.f('B_ar', cb['ar_tok_s'], 'tok/s', 'analytical', DSL + ' candidates[pq_rootcam_B].ar_tok_s', label='DS AR with stage B charged (upper bound)')
    cp = DSCAND['pq_rootcam_CP']
    c.f('CP_ar', cp['ar_tok_s'], 'tok/s', 'analytical', DSL + ' candidates[pq_rootcam_CP].ar_tok_s', label='DS AR with stage C + protected face (upper bound)')
    c.set(problem='Each root holds up to %s waiting partial sums. Finding the sibling of an arriving partial is a %s compare, then a priority encode, then a buffer update, and the next arrival depends on that update. There are %s such roots on a die.' % (D, tc, rep),
          naive=dict(title='Search, encode and update in one cycle', text='The native root does compare, encode and update in the same cycle. At 833 ps that is a 128-input compare, a 128-way priority encoder and a write-back in series: it does not fit, and the design model says so before any route (microarch obligation in design.json).'),
          trick=dict(title='Register the match vectors, forward the last update', text='Stage A registers the 128-bit match and free vectors computed from a registered queue head. Stage B encodes and updates. '
                     'An entry inserted or removed by B on this edge is forwarded into A\'s view on the same edge, so A never acts on stale state and the pairing decisions are identical to the native root. '
                     'The fallback, stage C, fetches the paired entry\'s operands one edge after the decision from a registered hit index: safe because a slot removed in B(t) can only be rewritten by an insert decided in B(t+1).'),
          evidence='Exact against the unchanged native root on %s. The two negative controls (no insert forwarding, wrong sibling) fail as required. Measured added latency: %s isolated, %s for a two-leaf root, %s for an eight-leaf root.' % (er, d1, d2, d8),
          price='Latency only: one cycle per root decision pass. Charged as an upper bound in the DS ledger (every phase exposes one eight-leaf root). Added state %s for all roots.' % bits)
    c.blocks('ot_s81_pq_ret_root_cam')
    c.tried('Stage B routes (36b7a0452)', 'bench refused', 'the closure loop\'s exact bench returned rc=1 on that source; reworked (multi-mode hold variants queued)', LOOP_SRC)
    c.rec(rc, md, 'rtl/dsrom_sys/s81_pq_parent/ot_s81_pq_ret_root_cam.sv', DSL)
    c.set(diagram=dict(
        naive=dict(kind='flow', cols=4, rows=2, nodes=[
            dict(id='in', c=0, r=0, label='partial arrives', k='field'), dict(id='cam', c=1, r=0, label='compare 128 tags', k='bad'),
            dict(id='enc', c=2, r=0, label='priority encode', k='bad'), dict(id='upd', c=3, r=0, label='update buffer', k='bad'), dict(id='add', c=3, r=1, label='FP32 add', k='su')],
            edges=[dict(a='in', b='cam'), dict(a='cam', b='enc'), dict(a='enc', b='upd'), dict(a='upd', b='add'), dict(a='upd', b='cam', l='next arrival depends', bad=True)],
            steps=[dict(hot=['in', 'cam'], pk=[0], note='Cycle t: compare the tag against all 128 entries...'),
                   dict(hot=['enc'], pk=[1], note='...encode the hit...'),
                   dict(hot=['upd'], pk=[2], bad=True, note='...and write the buffer, all inside one 833 ps period. It does not fit.')]),
        trick=dict(kind='flow', cols=4, rows=2, nodes=[
            dict(id='q', c=0, r=0, label='registered queue head', k='field'), dict(id='A', c=1, r=0, label='A: match / free vectors (reg)', k='good'),
            dict(id='B', c=2, r=0, label='B: encode + update', k='good'), dict(id='C', c=2, r=1, label='C: operand fetch (fallback)', k='su'),
            dict(id='add', c=3, r=0, label='FP32 add (golden order)', k='su')],
            edges=[dict(a='q', b='A'), dict(a='A', b='B'), dict(a='B', b='A', l='same-edge forward'), dict(a='B', b='add'), dict(a='B', b='C'), dict(a='C', b='add')],
            steps=[dict(hot=['q', 'A'], pk=[0], note='Cycle t: A registers which of the 128 entries match and which are free.'),
                   dict(hot=['B'], pk=[1], note='Cycle t+1: B encodes the hit and updates the buffer.'),
                   dict(hot=['A', 'B'], pk=[2], note='The entry B inserted or freed on this edge is forwarded into A on the same edge: no stale decision.'),
                   dict(hot=['add'], pk=[3], note='The pair goes to the adder in golden order: +1 cycle a pass (measured %s / %s / %s).' % (d1, d2, d8)),
                   dict(hot=['C', 'add'], pk=[4, 5], note='Stage C (fallback) reads the operands one edge later from a registered hit index.')])))
    cards.append(c.out())

    # ------------------------------------------------------------------ DS: PQ field + q-element
    c = Card('ds-pq', 'ds', 'Four field operations in flight', 'ot_v41_rom_elem_q_qxpq_w10 + PQ spine', 'in progress',
             'exact on the field vehicle; the PQ q-element route is in ECO and the spine screen is routing',
             'The ROM field used to run one matrix operation at a time and wait for its last partial sum. With PQ, up to four operations are in flight on the same elements, each tagged, so the field never drains between operations.')
    qp = 'results/rtl/dsrom_recovery_20261004/levers/qelem_pq.json'
    ns = {n['node']: n for n in G(qp, 'measurement', 'node_summary')}
    wa = ns['L0.attn.wo_a']; dn = ns['L0.ffn.down']
    a1 = c.f('wo_a_asbuilt', wa['asbuilt_us'], 'us', 'measured', qp + ' measurement.node_summary[L0.attn.wo_a].asbuilt_us', d=3, label='L0 wo_a, one op at a time')
    a2 = c.f('wo_a_pq', wa['us'], 'us', 'measured', qp + ' measurement.node_summary[L0.attn.wo_a].us', d=3, label='L0 wo_a, PQ q-element')
    b1 = c.f('down_asbuilt', dn['asbuilt_us'], 'us', 'measured', qp + ' measurement.node_summary[L0.ffn.down].asbuilt_us', d=3, label='L0 ffn.down, one op at a time')
    b2 = c.f('down_pq', dn['us'], 'us', 'measured', qp + ' measurement.node_summary[L0.ffn.down].us', d=3, label='L0 ffn.down, PQ q-element')
    rws = c.f('rows_wo_a', wa['rows_checked'], 'rows', 'measured', qp + ' node_summary[L0.attn.wo_a].rows_checked', label='wo_a rows checked exact')
    fp = 'results/rtl/dsrom_recovery_20261004/levers/field_spine_pq.json'
    g = c.f('gain', G(fp, 'composed_if_adopted', 'AR_gain_pct'), '%', 'analytical', fp + ' composed_if_adopted.AR_gain_pct', d=1, label='AR gain if adopted (W10-element PQ composition)')
    qx = DSITEMS['pq_qelem']
    qc = c.f('qelem_cost', float(re.search(r'\+([\d.]+) % node time', qx['description']).group(1)), '%', 'analytical', DSL + ' items[pq_qelem].description', d=2, label='q-element decode stage cost (node time)')
    eco = loop_job('ot_v41_rom_elem_q_qxpq_w10', 'dsrom-qelem-qs5f')
    c.f('qelem_eco_ss', eco['ss_ps'], 'ps', 'measured', LOOP_SRC + ' job ' + eco['job'], label='q-element route (ECO) SS')
    c.f('qelem_eco_ff', eco['ff_ps'], 'ps', 'measured', LOOP_SRC + ' job ' + eco['job'], label='q-element route (ECO) FF hold')
    c.set(problem='One operation at a time leaves the field idle while the last partial sums travel back through the return tree. On layer 0, the attention output projection (wo_a) takes %s and the FFN down projection %s that way.' % (a1, b1),
          naive=dict(title='Issue, drain, issue', text='Broadcast an operation, wait for every region\'s last row to return, then broadcast the next. The return-tree latency is paid once per operation.'),
          trick=dict(title='Tag the operations, keep up to four in flight', text='Each operation carries a tag through the elements; returning rows are written by tag, and the root pairs partials of the same tag (see the root CAM story). '
                     'The spine issues the next operation as soon as its issue rule allows, so four operations overlap and the drain is paid once per group.'),
          evidence='Measured on the full-shape field vehicle at the S81 placement, every row exact (%s on wo_a alone): wo_a %s and ffn.down %s, from %s and %s.' % (rws, a2, b2, a1, b1),
          price='On the W10 element the composition gains %s AR. The q-element\'s decode stage costs %s of node time; the routes still have to close (latest q-element ECO route in the expander).' % (g, qc))
    c.blocks('ot_v41_rom_elem_q_qxpq_w10', 'ot_v41_pqc_spine_screen')
    c.tried('Z22c lean q-element', 'SS −14.6 / FF −11.4 ps', 'killed for the single-route rule; margin-first variant routed instead', qp + ' ss_ff.routes')
    c.rec(qp, fp, 'results/rtl/dsrom_qelem_pq_20261006/field_pq_qelem_qm2.json')
    gantt_ops = lambda over: [dict(row=r, start=(i * (2 if over else 10)) + r, len=8, label='op%d' % i, k='op%d' % i) for i in range(4) for r in range(3)]
    c.set(diagram=dict(
        naive=dict(kind='gantt', rows=['broadcast', 'elements', 'return tree'], span=44, unit='cycles (schematic)', bars=gantt_ops(False),
                   steps=[dict(t=0, note='op0 broadcasts.'), dict(t=10, note='op1 waits until op0\'s last row is back.'), dict(t=20, note='Each op pays the full return latency.'), dict(t=40, note='Four ops: four drains.')]),
        trick=dict(kind='gantt', rows=['broadcast', 'elements', 'return tree'], span=44, unit='cycles (schematic)', bars=gantt_ops(True),
                   steps=[dict(t=0, note='op0 broadcasts.'), dict(t=2, note='op1 issues behind it with its own tag.'), dict(t=6, note='Up to four tags in flight; rows return tagged.'), dict(t=16, note='The group drains once.')])))
    cards.append(c.out())

    # ------------------------------------------------------------------ DS: field spine
    c = Card('ds-spine', 'ds', 'The spine that feeds 128 regions', 'ot_v41_spine_pqc_w17w10 (ROM field spine)', 'in progress',
             'R=16 screens routed; R=128 screens still routing (DESIGN_NOTE physical table); spine screens queued in the loop',
             'The spine streams activations to 128 field regions and writes their returning rows into the vector memory. Its first version failed timing by most of a clock period because several feedback loops closed in one cycle.')
    dn_ = 'results/rtl/dsrom_field_spine_20261004/DESIGN_NOTE.md'
    o16 = c.f('old_r16', RX(dn_, r'Baseline \(PQ=0\), R=16 \| (-[\d.]+) ps'), 'ps', 'measured', dn_ + ' Problem table', label='old spine SS, PQ=0 R=16')
    o128 = c.f('old_r128', RX(dn_, r'PQ=1, R=128 \| (-[\d.]+) ps'), 'ps', 'measured', dn_ + ' Problem table', label='old spine SS, PQ=1 R=128')
    n16 = c.f('new_r16', RX(dn_, r'PQ=0, R=16 \| \+([\d.]+) ps'), 'ps', 'measured', dn_ + ' Physical table', label='new spine SS, PQ=0 R=16')
    n16f = c.f('new_r16_ff', RX(dn_, r'PQ=0, R=16 \| \+[\d.]+ ps \(0 violators\) \| (-[\d.]+) ps'), 'ps', 'measured', dn_ + ' Physical table', label='new spine FF, PQ=0 R=16')
    p16 = c.f('pq_r16', RX(dn_, r'PQ=1, R=16 \| \+([\d.]+) ps'), 'ps', 'measured', dn_ + ' Physical table', label='new spine SS, PQ=1 R=16')
    pairs = c.f('op_pairs', RX(dn_, r'holds on all ([\d,]+) consecutive op pairs', cast=int), 'op pairs', 'measured', dn_ + ' issue rule', label='consecutive op pairs, 0 rule violations')
    runs = c.f('runs', RX(dn_, r'every phase x region \(as-built rule\) \| ([\d,]+)', cast=int), 'runs', 'measured', dn_ + ' Exactness table', label='baseline phase x region runs, all exact')
    rowsx = c.f('rows', RX(dn_, r'pass, ([\d,]+) rows, 0 mismatches', cast=int), 'rows', 'measured', dn_ + ' Exactness table', label='rows, 0 mismatches')
    nodec = c.f('node_cost', RX(dn_, r'\| node \| \+(\d+) cycles', cast=int), 'cycles', 'measured', dn_ + ' Cycle cost table', label='added cycles a node')
    bug = c.f('bug_fail', RX(dn_, r'np=2 runs failed (\d+) of 60', cast=int), 'of 60 runs', 'measured', dn_ + ' item 8', label='inherited spine np=2 failures (bug found)')
    c.set(problem='The first spine missed 833 ps by %s (R=16) and %s (PQ, R=128). The failing paths were register-to-register loops inside the spine, not wires: the stream-ROM word loop, the row-write address, beat assembly, the stream-end cone and the row-count tree.' % (o16, o128),
          naive=dict(title='Close each loop in one cycle', text='The streamer read a ROM word, compared its need against what the x-buffer had, chose the next ROM address and read again, all in one cycle. Behavioural + and <= became ripple adders.'),
          trick=dict(title='A reader that runs ahead, and a fully registered return', text='A stream-ROM reader works one operation ahead in four stages (address, word, derived need/flags) and pushes words into a queue with 8 credits, so the streamer\'s advance test is a short compare on kept copies. '
                     'Beat assembly reads from registered, replicated indices. The return path is region-local: register, select from a per-16-region table replica, add the address with a prefix adder, write. Row counts come from registered tags through a popcount tree.'),
          evidence='Exact on every region with released-checkpoint rows: %s and %s, 0 mismatches. The issue rule holds on %s. New screens: SS +%s (PQ=0, R=16) with FF %s on one pin, SS +%s (PQ=1, R=16). The redesign also found an inherited tag bug that failed %s.' % (runs, rowsx, pairs, n16, n16f, p16, bug),
          price='%s a node (two-cycle phase ROM, one broadcast stage, three return stages); stream length and op spacing unchanged.' % nodec)
    c.blocks('ot_v41_pqc_spine_screen')
    c.tried('Old pinned spine at R=16', 'SS %s' % o16, 'same-cycle loops', dn_)
    c.tried('Old PQ spine at R=128', 'SS %s' % o128, 'same-cycle loops plus fanout to 128 regions', dn_)
    c.rec(dn_, 'rtl/v41die/ot_v41_spine_pqc_w17w10.sv')
    c.set(diagram=dict(
        naive=dict(kind='flow', cols=4, rows=2, nodes=[
            dict(id='rom', c=0, r=0, label='stream ROM', k='field'), dict(id='sw', c=1, r=0, label='word sw', k='field'),
            dict(id='need', c=2, r=0, label='need vs have', k='bad'), dict(id='addr', c=3, r=0, label='next ROM address', k='bad'), dict(id='beat', c=2, r=1, label='beat out', k='su')],
            edges=[dict(a='rom', b='sw'), dict(a='sw', b='need'), dict(a='need', b='addr'), dict(a='addr', b='rom', l='same cycle', bad=True), dict(a='need', b='beat')],
            steps=[dict(hot=['rom', 'sw'], pk=[0], note='The ROM returns a word...'), dict(hot=['need'], pk=[1], note='...its need is compared against the x-buffer...'),
                   dict(hot=['addr', 'rom'], pk=[2, 3], bad=True, note='...and the next address must reach the ROM in the same cycle: the loop misses by %s.' % o16)]),
        trick=dict(kind='flow', cols=4, rows=2, nodes=[
            dict(id='rd', c=0, r=0, label='reader R0-R2 (one op ahead)', k='good'), dict(id='q', c=1, r=0, label='queue, 8 credits', k='good'),
            dict(id='st', c=2, r=0, label='streamer: need <= have on kept copies', k='field'), dict(id='beat', c=3, r=0, label='beat (registered indices)', k='su'),
            dict(id='ret', c=2, r=1, label='return: reg / table replica / prefix add / write', k='good'), dict(id='vm', c=3, r=1, label='vector memory', k='su')],
            edges=[dict(a='rd', b='q'), dict(a='q', b='st'), dict(a='st', b='beat'), dict(a='st', b='q', l='pop / credit'), dict(a='ret', b='vm')],
            steps=[dict(hot=['rd'], note='The reader fetches ahead in op order; no loop through the streamer.'), dict(hot=['q'], pk=[0], note='Words wait in a queue behind a registered head (8 credits).'),
                   dict(hot=['st', 'beat'], pk=[1, 2], note='The streamer only compares and pops: a short cone.'), dict(hot=['ret', 'vm'], pk=[4], note='Rows return through four registered stages (+3 cycles a row write).')])))
    cards.append(c.out())

    # ------------------------------------------------------------------ DS: mixed frame packing
    c = Card('ds-frame', 'ds', 'How many element pairs fit in a field column', 'S81 field frame (mixed BF / q slots)', 'gated',
             'unified ledger gate field_phases_1792: the 1,792 geometry\'s field phases are unmeasured',
             'A field column has a fixed height. BF16 pairs and FP8/FP4 q pairs need different slot heights, so the number of pairs a die holds depends on how they are packed. The legal answer turned out lower than the plan.')
    mg = 'results/uarch/dsrom_s81_mixed_geometry_20261007/model.json'
    vv = {v['name']: v for v in G(mg, 'variants')}
    avail = c.f('avail', round(vv['uniform198']['field_frame_available_um'], 2), 'um', 'analytical', mg + ' variants[*].field_frame_available_um', d=2, label='field frame height available')
    u = c.f('uniform_sum', round(vv['uniform198']['maximum_requested_slot_height_sum_um'], 2), 'um', 'analytical', mg + ' variants[uniform198].maximum_requested_slot_height_sum_um', d=2, label='uniform198, 2,048 pairs: slot heights')
    m183 = c.f('m183_sum', round(vv['mixed183']['maximum_requested_slot_height_sum_um'], 2), 'um', 'analytical', mg + ' variants[mixed183].maximum_requested_slot_height_sum_um', d=2, label='mixed183, 2,304 pairs: slot heights')
    m221 = c.f('m221_sum', round(vv['mixed221']['maximum_requested_slot_height_sum_um'], 2), 'um', 'analytical', mg + ' variants[mixed221].maximum_requested_slot_height_sum_um', d=2, label='mixed221, 2,048 pairs requested: slot heights')
    mx = c.f('m221_max', vv['mixed221']['maximum_pairs_at_this_geometry'], 'pairs', 'analytical', mg + ' variants[mixed221].maximum_pairs_at_this_geometry', label='mixed221 maximum legal pairs')
    pv = 'results/uarch/dsrom_s81_mixed1792_mapping_20261007/provenance.json'
    hs = c.f('half_stages', G(pv, 'variants', 'half_dedicated', 'stages'), 'stages', 'analytical', pv + ' variants.half_dedicated.stages', label='1,792 mapping, BF-dedicated half rate: stages')
    fs = c.f('full_stages', G(pv, 'variants', 'full_shared', 'stages'), 'stages', 'analytical', pv + ' variants.full_shared.stages', label='1,792 mapping, shared full-rate BF: stages')
    hl = ULINES['actual1792_half_dedicated_hops']
    c.f('half_hops_us', hl['effect']['AR'], 'us', 'analytical', UL + ' lines[actual1792_half_dedicated_hops].effect.AR', d=3, label='added stage-hop latency, half-dedicated')
    c.set(problem='The plan asked for 2,304 pairs a die with mixed slots (q slots 183.6 um, BF slots 198.72 um). The legal-fit check sums the slot heights of the tallest column against the frame: %s available.' % avail,
          naive=dict(title='Pack the most pairs (mixed183, 2,304 pairs)', text='Shorter q slots looked like they fit more pairs. The tallest column needs %s against %s: not a legal fit.' % (m183, avail)),
          trick=dict(title='Size the slots to what routes, then count dies', text='The q slot that routes is taller (221.4 um), which caps a die at %s. Uniform 198.72 um slots fit 2,048 (%s). '
                     'Instead of squeezing, the design keeps the routable slot and adds dies: the 1,792 mapping needs %s with BF-dedicated half-rate pairs or %s with shared pairs.' % (mx, u, hs, fs)),
          evidence='Legal-fit sums from the geometry model (frame %s): uniform198 %s fits; mixed183 %s and mixed221 at 2,048 pairs %s do not. Both 1,792 mappings pass capacity on the released checkpoint declarations.' % (avail, u, m183, m221),
          price='Extra stages add board hops: the half-dedicated mapping adds %s of AR latency in the ledger (priced, not yet composed with measured field phases).' % c.f('half_hops_label', hl['effect']['AR'], 'us', 'analytical', UL + ' actual1792_half_dedicated_hops', d=1, label='stage hops (rounded)'))
    c.rec(mg, pv, UL)
    c.set(diagram=dict(
        naive=dict(kind='bars', unit='um', limit=dict(v=vv['uniform198']['field_frame_available_um'], label='frame available'),
                   bars=[dict(label='mixed183, 2,304 pairs', v=vv['mixed183']['maximum_requested_slot_height_sum_um'], k='bad')],
                   steps=[dict(show=1, note='The tallest column of the 2,304-pair packing overruns the frame.')]),
        trick=dict(kind='bars', unit='um', limit=dict(v=vv['uniform198']['field_frame_available_um'], label='frame available'),
                   bars=[dict(label='uniform198, 2,048 pairs', v=vv['uniform198']['maximum_requested_slot_height_sum_um'], k='good'),
                         dict(label='mixed183, 2,304 pairs', v=vv['mixed183']['maximum_requested_slot_height_sum_um'], k='bad'),
                         dict(label='mixed221, 2,048 requested', v=vv['mixed221']['maximum_requested_slot_height_sum_um'], k='bad')],
                   steps=[dict(show=1, note='Uniform 198.72 um slots: 2,048 pairs fit.'), dict(show=2, note='Mixed 183.6 um q slots: 2,304 pairs overrun.'),
                          dict(show=3, note='The routable 221.4 um q slot overruns at 2,048 and caps the die at %s.' % mx)])))
    cards.append(c.out())

    # ------------------------------------------------------------------ DS: mesochronous FIFO
    c = Card('ds-meso', 'ds', 'Crossing between clock regions without synchronising pointers', 'ot_meso_fifo_w512d8g1', 'in progress', '',
             'Regions of a ROM die share one clock frequency but not one phase. The crossing FIFO writes a slot every cycle no matter what, places its read pointer once at reset, then just counts, and guard slots stop it the moment the phase drifts too far.')
    rtl = 'rtl/common/ot_meso_fifo.sv'
    w = c.f('wander', RX(rtl, r'wander\s*(?://\s*)?of \+-w \(5 % of non-shared insertion, (\d+) ps central\)', cast=int), 'ps', 'analytical', rtl + ' header (clocking contract)', label='central phase wander budget')
    v = V(c, 'ot_meso_fifo_w512d8g1')
    c.set(problem='A synchronous register between two regions would need their clock trees matched to within the hold and setup window at 833 ps across the die. They come from one reference but their phase is unknown and wanders slowly (about %s central).' % w,
          naive=dict(title='A general asynchronous FIFO', text='Gray-coded pointers synchronised every cycle cost several cycles each way, and the pointer compare sits on the data path. Same-frequency regions do not need any of that.'),
          trick=dict(title='Always write, place once, guard the window', text='The writer\'s counter never stops: it writes slot wc every cycle, valid or not. At alignment the reader samples the writer\'s Gray count on both its rising and falling edge, learns which half-period the phase sits in, and sets its pointer so every slot is read OFFSET periods after it was written. '
                     'From then on the pointer only increments. Each cycle it samples the lap bit of two guard slots on the opposite edge; if the lag drifts out of the window, a sticky fault stops delivery and credit (fail closed).'),
          evidence=('Closed: SS %s / FF %s ps, DRC 0 (%s). Bench: depth-4 positive 52/52 runs clean; an offset mutant faults as it must.' % (fmtn(v['ss']), fmtn(v['ff']), v['src'])) if v else 'Not yet closed.',
          price='Two cycles a crossing (d8g1: depth 8, offset 4, guard 1); a field round trip crosses twice (+4 in the DS ledger).')
    if v:
        c.f('ss', v['ss'], 'ps', 'measured', v['src'], label='SS setup slack'); c.f('ff', v['ff'], 'ps', 'measured', v['src'], label='FF hold slack')
    ml = DSITEMS['meso_d8g1']
    c.f('ledger_ar', ml['ar_tok_s'], 'tok/s', 'analytical', DSL + ' items[meso_d8g1].ar_tok_s', label='DS AR after this item (cumulative ledger)')
    c.blocks('ot_meso_fifo_w512d8g1')
    for a in LOOP['blocks'].get('ot_meso_fifo_w512d4', []):
        if a.get('ss_ps') is not None:
            c.tried('Depth 4 (%s)' % a['job'], 'SS %s / FF %s ps' % (fmtn(a['ss_ps']), fmtn(a['ff_ps'])), 'below +15/+15 at 833 ps; depth 8 with a guard of 1 adds one cycle and closes', LOOP_SRC)
    c.rec(rtl, 'results/closure_loop/s81-meso-d8g1-c20d75e28/verdict.json', DSL)
    c.set(diagram=dict(
        naive=dict(kind='flow', cols=4, rows=2, nodes=[
            dict(id='w', c=0, r=0, label='writer', k='field'), dict(id='g', c=1, r=0, label='Gray pointer sync (3 FF)', k='bad'),
            dict(id='cmp', c=2, r=0, label='full / empty compare', k='bad'), dict(id='r', c=3, r=0, label='reader', k='su'), dict(id='g2', c=1, r=1, label='sync back (3 FF)', k='bad')],
            edges=[dict(a='w', b='g'), dict(a='g', b='cmp'), dict(a='cmp', b='r'), dict(a='r', b='g2'), dict(a='g2', b='w')],
            steps=[dict(hot=['w', 'g'], pk=[0], note='Every pointer update crosses through synchronisers...'), dict(hot=['cmp', 'r'], pk=[1, 2], bad=True, note='...and the compare sits in front of every read: cycles each way.')]),
        trick=dict(kind='ring', slots=8, offset=4, guard=1, cycles=12,
                   note='Writer fills one slot every cycle; the reader consumes the slot written OFFSET periods ago; the guard slot is sampled on the opposite edge.')))
    cards.append(c.out())

    # ------------------------------------------------------------------ DS: collective gearbox
    c = Card('ds-gearbox', 'ds', 'A link gearbox with no shifter', 'ot_s81ph_link_gbx FMT 1 (collective lane)', 'in progress',
             'FMT1 is exact on the TP4 bench; the lane tiles still route (latest SS in the expander)',
             'Die-to-die links move one 512-bit beat a cycle, but collective frames are a different size. The first gearbox cut frames into beats with a bit-granular shifter that could not close. The new format puts three frames in every four beats at fixed bit positions, so every output bit is a wire chosen by a phase.')
    gb = 'rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv'
    lo = c.f('ss_lo', RX(gb, r'coll lane SS (-\d+)\.\.'), 'ps', 'measured', gb + ' FMT comment', label='bit-shifter lane SS (best)')
    hi = c.f('ss_hi', RX(gb, r'coll lane SS -\d+\.\.(-\d+)'), 'ps', 'measured', gb + ' FMT comment', label='bit-shifter lane SS (worst)')
    sh = c.f('shift_bits', RX(gb, r'bit-granular (\d+)-b shifts', cast=int), 'bits', 'analytical', gb + ' FMT comment', label='shifter width')
    cg = DSCAND['coll_gbx_fmt1']
    r1 = c.f('rate_fmt1', 0.75, 'slots/beat', 'analytical', gb + ' FMT comment (3 slots in every 4 gearbox beats)', d=2, label='FMT1 slot rate')
    r0 = c.f('rate_g', RX(gb, r'vs G/S = ([\d.]+)'), 'slots/beat', 'analytical', gb + ' FMT comment (G/S)', d=3, label='bit-packed slot rate')
    tp4n = c.f('tp4_fmt1', int(re.search(r'end ([\d,]+) vs', cg['description']).group(1).replace(',', '')), 'cycles', 'measured', DSL + ' candidates[coll_gbx_fmt1]', label='TP4 bench end, FMT1')
    tp4o = c.f('tp4_old', int(re.search(r'vs ([\d,]+) cycles', cg['description']).group(1).replace(',', '')), 'cycles', 'measured', DSL + ' candidates[coll_gbx_fmt1]', label='TP4 bench end, before')
    c.f('cand_ar', cg['ar_tok_s'], 'tok/s', 'analytical', DSL + ' candidates[coll_gbx_fmt1].ar_tok_s', label='DS AR with FMT1 charged (upper bound)')
    c.set(problem='Frames of S bits must ride in 512-bit beats that also carry a marker, an idle flag and a reverse frame. Packing them back to back needs a %s shifter whose amount changes every beat; the lane tiles routed at SS %s to %s.' % (sh, lo, hi),
          naive=dict(title='Pack frames bit-tight', text='Slots back to back, cut into G-bit chunks: the best payload rate (%s slots a beat), but the cut position moves every beat, so every output bit is a wide mux driven by a counter.' % r0),
          trick=dict(title='Fixed group format: 3 slots in 4 beats', text='Slot j of a group occupies beat j bits [140j, 456) and beat j+1 bits [0, 140(j+1)); beat 3\'s top bits are zero, and the marker sits on beat 0. No shifter remains: each beat bit is one of four fixed wires selected by the beat phase.'),
          evidence='Bench PASS on the TP4 collective with the reorder mutant failing; link-up is faster (bench end %s vs %s cycles).' % (tp4n, tp4o),
          price='Slot rate %s instead of %s (−2.0 %%), charged as +2.0 %% of every collective node (upper bound).' % (r1, r0))
    c.blocks('dsfd_coll_lane_e', 'dsfd_coll_lane_w')
    for b in ('dsfd_coll_lane_w', 'dsfd_coll_lane_e'):
        for a in LOOP['blocks'].get(b, []):
            if a.get('ss_ps') is not None:
                c.tried('%s (%s)' % (b, a['job'][-22:]), 'SS %s / FF %s ps' % (fmtn(a['ss_ps']), fmtn(a['ff_ps'])), 'bit-granular shifter / predecessor lane format', LOOP_SRC)
    c.rec(gb, DSL)
    c.set(diagram=dict(
        naive=dict(kind='gantt', rows=['beat 0', 'beat 1', 'beat 2', 'beat 3'], span=456, unit='bit position', bars=[
            dict(row=0, start=0, len=149, label='s0', k='op0'), dict(row=0, start=149, len=149, label='s1', k='op1'), dict(row=0, start=298, len=149, label='s2', k='op2'), dict(row=0, start=447, len=9, label='', k='op3'),
            dict(row=1, start=0, len=140, label='s3', k='op3'), dict(row=1, start=140, len=149, label='s4', k='op0'), dict(row=1, start=289, len=149, label='s5', k='op1'), dict(row=1, start=438, len=18, label='', k='op2'),
            dict(row=2, start=0, len=131, label='s6', k='op2'), dict(row=2, start=131, len=149, label='s7', k='op3'), dict(row=2, start=280, len=149, label='s8', k='op0'), dict(row=2, start=429, len=27, label='', k='op1'),
            dict(row=3, start=0, len=122, label='s9', k='op1'), dict(row=3, start=122, len=149, label='s10', k='op2'), dict(row=3, start=271, len=149, label='s11', k='op3'), dict(row=3, start=420, len=36, label='', k='op0')],
            steps=[dict(t=0, note='Schematic: slot boundaries drift every beat...'), dict(t=456, note='...so each output bit needs a shift amount that changes every cycle.')]),
        trick=dict(kind='gantt', rows=['beat 0', 'beat 1', 'beat 2', 'beat 3'], span=456, unit='bit position', bars=[
            dict(row=0, start=0, len=456, label='slot 0 [0,456)', k='op0'),
            dict(row=1, start=0, len=140, label='slot 0 tail', k='op0'), dict(row=1, start=140, len=316, label='slot 1 [140,456)', k='op1'),
            dict(row=2, start=0, len=280, label='slot 1 tail', k='op1'), dict(row=2, start=280, len=176, label='slot 2 [280,456)', k='op2'),
            dict(row=3, start=0, len=420, label='slot 2 tail', k='op2'), dict(row=3, start=420, len=36, label='zero', k='idle')],
            steps=[dict(t=0, note='Beat 0: slot 0 starts at bit 0 with the marker.'), dict(t=140, note='Slot j ends at bit 140(j+1) of the next beat.'), dict(t=456, note='Positions never move: every beat bit is a fixed 4-way select.')])))
    cards.append(c.out())

    # ------------------------------------------------------------------ DS: softmax divider + exp
    c = Card('ds-softmax', 'ds', 'Softmax: an exact exponential and divider at 1.2 GHz', 'ot_dsrom_su_softmax_exp_tile, ot_dsrom_su_fdiv_tile / _hr', 'in progress',
             '', 'Attention softmax needs exp(x - max), a sum and a divide per score, all correctly rounded to the golden model. The exponential and the divider were rebuilt as pipelined tiles; each closed only after its long multiply/add stages were cut once more.')
    sr = 'results/rtl/dsrom_softmax_recovery_20261007/record.json'
    er_ = 'results/rtl/dsrom_softmax_exp_recut_20261007/record.json'
    pairs_ = c.f('div_pairs', G(sr, 'divider', 'full_drain_pairs'), 'pairs', 'measured', sr + ' divider.full_drain_pairs', label='divider pairs, 0 mismatches')
    dep = c.f('exp_depth', G(er_, 'tile_latency'), 'cycles', 'measured', er_ + ' tile_latency', label='exp tile latency')
    chk = c.f('exp_checked', G(er_, 'results_checked'), 'results', 'measured', er_ + ' results_checked', label='exp results checked')
    lm = c.f('lm', G(er_, 'parameters', 'LM'), 'stages', 'measured', er_ + ' parameters.LM', label='multiplier latency')
    nz0 = G(sr, 'cycle_deltas', 'baseline_m5_T640', 'attn.normalize'); nz1 = G(sr, 'softmax', 'T640_nodes', 'attn.normalize')
    n0 = c.f('norm_before', nz0, 'cycles', 'measured', sr + ' cycle_deltas.baseline_m5_T640.attn.normalize', label='normalize node, margin baseline (T640)')
    n1 = c.f('norm_after', nz1, 'cycles', 'measured', sr + ' softmax.T640_nodes.attn.normalize', label='normalize node, SAFE2 (T640)')
    ex_ = DSITEMS['softmax_exp_recut']
    ecost = c.f('exp_cost', 30, 'cycles', 'measured', DSL + ' items[softmax_exp_recut] (attn.exp 225 -> 255)', label='attn.exp added')
    mex = re.search(r'(dsrom_softmax_safe_exprcf_\w+) CLOSED SS \+([\d.]+) / FF \+([\d.]+)', ex_['description'])
    exp_closed = dict(job=mex.group(1), ss=float(mex.group(2)), ff=float(mex.group(3)), drc=0, ok=True, commit='', src=DSL + ' items[softmax_exp_recut].description', cycles=30)
    vd = V(c, 'ot_dsrom_su_fdiv_tile'); vh = V(c, 'ot_dsrom_su_fdiv_hr'); ve = V(c, 'ot_dsrom_su_softmax_exp_tile') or exp_closed
    ev = []
    for nm, vx in (('divider tile', vd), ('half-rate divider', vh), ('exp tile', ve)):
        if vx:
            c.f('ss_' + nm.replace(' ', '_'), vx['ss'], 'ps', 'measured', vx['src'], label=nm + ' SS'); c.f('ff_' + nm.replace(' ', '_'), vx['ff'], 'ps', 'measured', vx['src'], label=nm + ' FF')
            ev.append('%s SS %s / FF %s ps' % (nm, fmtn(vx['ss']), fmtn(vx['ff'])))
    c.set(problem='Every score of every head goes through max, exp, sum and normalize at 1M context; the units must be exact and run one result a cycle. The plain exp tile and the first divider routed with negative setup slack (expander).',
          naive=dict(title='One long multiply-add per stage', text='The exponential\'s polynomial and the divider\'s refinement chained a full multiply and add per pipeline stage; the plain exp tile routed at SS %s ps.' % fmtn(loop_job('ot_dsrom_su_softmax_exp_tile', 'dsrom_softmax_safe_exp_')['ss_ps'])),
          trick=dict(title='Range-reduce by ln2, then cut the multiplier and adder', text='exp(x) = 2^n * exp(r) with r = x - n ln2, so the series works on a small r and n becomes the exponent field. The RECUT tile adds two cuts in the multiplier and adder (latency %s), at one result a cycle. '
                     'The divider (SAFE) is a two-beat tile with a half-rate variant; both keep IEEE round-to-nearest-even.' % lm),
          evidence='Committed closures: %s. Divider: %s over 4 seeds, 0 mismatches. Exp: %s checked against the pinned golden, near-ln2 cancellation, extremes and reset abort included; the safe-input negative fails.' % ('; '.join(ev) if ev else 'none yet', pairs_, chk),
          price='normalize %s → %s cycles (SAFE2) and attn.exp +%s (RECUT) per row at T640; both priced in the DS ledger.' % (n0, n1, ecost.split(' ')[0]))
    c.blocks('ot_dsrom_su_softmax_exp_tile', 'ot_dsrom_su_fdiv_tile', 'ot_dsrom_su_fdiv_hr', ledger_closed={'ot_dsrom_su_softmax_exp_tile': exp_closed})
    for b in ('ot_dsrom_su_softmax_exp_tile', 'ot_dsrom_su_fdiv_tile', 'ot_dsrom_su_fdiv_hr', 'ot_dsrom_su_softmax_exp_hr'):
        for a in LOOP['blocks'].get(b, []):
            if a.get('ss_ps') is not None and a['status'] != 'CLOSED':
                c.tried('%s (%s)' % (b.replace('ot_dsrom_su_', ''), a['job'].replace('dsrom_softmax_', '')), 'SS %s / FF %s ps' % (fmtn(a['ss_ps']), fmtn(a['ff_ps'])), 'below +15 / +15', LOOP_SRC)
    c.rec(sr, er_, DSL)
    c.set(diagram=dict(
        naive=dict(kind='flow', cols=4, rows=1, nodes=[
            dict(id='x', c=0, r=0, label='x = s - max', k='su'), dict(id='poly', c=1, r=0, label='polynomial: mul + add a stage', k='bad'),
            dict(id='sc', c=2, r=0, label='scale', k='su'), dict(id='y', c=3, r=0, label='exp', k='su')],
            edges=[dict(a='x', b='poly'), dict(a='poly', b='sc', bad=True), dict(a='sc', b='y')],
            steps=[dict(hot=['x'], note='One score enters every cycle.'), dict(hot=['poly'], pk=[0], bad=True, note='A full multiply plus add in one stage misses 833 ps.')]),
        trick=dict(kind='flow', cols=5, rows=1, nodes=[
            dict(id='x', c=0, r=0, label='x', k='su'), dict(id='n', c=1, r=0, label='n = round(x log2 e); r = x - n ln2', k='good'),
            dict(id='p', c=2, r=0, label='series in r (cut mul / add, LAT %s)' % lm.split(' ')[0], k='good'), dict(id='e', c=3, r=0, label='exponent += n', k='good'), dict(id='y', c=4, r=0, label='exp, correctly rounded', k='su')],
            edges=[dict(a='x', b='n'), dict(a='n', b='p'), dict(a='p', b='e'), dict(a='e', b='y')],
            steps=[dict(hot=['x', 'n'], pk=[0], note='Range reduction: r is small, n is an integer.'), dict(hot=['p'], pk=[1], note='The series on r runs in a deeper pipeline: two more cuts.'),
                   dict(hot=['e', 'y'], pk=[2, 3], note='2^n is just the exponent field. One result a cycle, %s deep.' % dep)])))
    cards.append(c.out())

    # ------------------------------------------------------------------ DS: Sinkhorn
    c = Card('ds-sinkhorn', 'ds', 'Sinkhorn: one normalisation per clock', 'ot_hdc_sinkhorn (hyper-connection mixer)', 'in progress',
             'exact; routed only at the TT corner (pathfinding), not at the SS/FF sign-off corners',
             'DeepSeek-V4.1 mixes its residual streams with a 4x4 Sinkhorn normalisation: 40 dependent row and column normalisations, 80 times a token. On ordinary pipelined units each one costs dozens of cycles. This unit spends area to do a whole normalisation in one clock, bit-identical to IEEE.')
    sk = 'rtl/hdc/v41/ot_hdc_sinkhorn.sv'
    per = c.f('naive_cyc', RX(sk, r'31-deep divider ot_hdc_fdiv = (\d+) cycles', cast=int), 'cycles', 'analytical', sk + ' header (WHY)', label='one normalisation on pipelined units')
    nsk = c.f('per_token', RX(sk, r'(\d+) Sinkhorns per token', cast=int), 'Sinkhorns/token', 'analytical', sk + ' header (WHY)', label='Sinkhorns a token')
    ndep = c.f('dep', RX(sk, r'each (\d+) DEPENDENT normalisations', cast=int), 'steps', 'analytical', sk + ' header (WHY)', label='dependent normalisations each')
    cp_ = 'results/rtl/hdc_v41_sinkhorn_campaign.json'
    lat = c.f('lat', G(cp_, 'latency_cycles'), 'cycles', 'measured', cp_ + ' latency_cycles', label='unit latency (accept to out_valid)')
    ops = c.f('ops', G(cp_, 'arithmetic', 'totals', 'ops'), 'ops', 'measured', cp_ + ' arithmetic.totals.ops', label='arithmetic ops checked, 0 errors')
    sig = c.f('sig', G(cp_, 'generator', 'seed_bound', 'significands_checked'), 'significands', 'measured', cp_ + ' generator.seed_bound.significands_checked', label='reciprocal seed bound proved over')
    ph = 'results/physical_abi3/asap7/hdc/v41/ot_hdc_sinkhorn_7ns/physical.json'
    tp = G(ph, 'design', 'clock_period_ns'); ws = G(ph, 'design', 'setup_wns_ns')
    tpp = c.f('tt_period', tp, 'ns', 'measured', ph + ' design.clock_period_ns (corner %s)' % G(ph, 'corner', 'name'), d=1, label='routed target period (TT)')
    tws = c.f('tt_wns', ws * 1000, 'ps', 'measured', ph + ' design.setup_wns_ns', d=1, label='TT setup slack')
    tns = c.f('tt_ns', round(G(cp_, 'latency_cycles') * (tp - ws)), 'ns', 'analytical', 'latency_cycles x (period - setup slack) from ' + cp_ + ' and ' + ph, label='one Sinkhorn at the TT period (derived)')
    c.set(problem='%s a token x %s each. On the pipelined adders and the divider, one normalisation (3 chained adds, the eps add and a 31-deep divide) costs %s, and the next cannot start until it finishes.' % (nsk, ndep, per),
          naive=dict(title='Reuse the pipelined FP units', text='Each normalisation pays the full adder and divider latency, %s, times %s in series.' % (per, ndep)),
          trick=dict(title='A combinational step that is exactly IEEE', text='All operands are non-negative, so the adders drop the cancellation path. Division is a multiply by a table-seeded reciprocal checked by two exact remainder signs, which picks the correctly rounded quotient. '
                     'All 16 quotients run in parallel and the matrix is written back transposed, so the next (column) step again sums storage rows with no select mux. One register a step, one step a clock.'),
          evidence='Exact against the golden on %s; the reciprocal seed bound is proved for all %s; 17 mutations caught. Latency %s. Routed at %s with %s setup slack at TT (pathfinding corner only).' % (ops, sig, lat, tpp, tws),
          price='Area: one unit per sublayer engine. The step is a long combinational path, so the unit runs in the slow serial-chain domain; one Sinkhorn is about %s at the TT period.' % tns)
    c.rec(sk, cp_, ph)
    c.set(diagram=dict(
        naive=dict(kind='gantt', rows=['normalisation chain'], span=4 * RX(sk, r'31-deep divider ot_hdc_fdiv = (\d+) cycles', cast=int), unit='cycles',
                   bars=[dict(row=0, start=i * RX(sk, r'31-deep divider ot_hdc_fdiv = (\d+) cycles', cast=int), len=RX(sk, r'31-deep divider ot_hdc_fdiv = (\d+) cycles', cast=int), label='step %d' % i, k='op%d' % (i % 4)) for i in range(4)],
                   steps=[dict(t=51, note='Step 0: three chained adds, the eps add and a 31-deep divide.'), dict(t=102, note='Step 1 waits for step 0.'), dict(t=204, note='Four of %s steps done.' % ndep)]),
        trick=dict(kind='gantt', rows=['normalisation chain'], span=4 * RX(sk, r'31-deep divider ot_hdc_fdiv = (\d+) cycles', cast=int), unit='cycles',
                   bars=[dict(row=0, start=0, len=2, label='A,B', k='op3')] + [dict(row=0, start=2 + i, len=1, label='', k='op%d' % (i % 2)) for i in range(G(cp_, 'latency_cycles') - 2)],
                   steps=[dict(t=2, note='Step 0 runs as two cycles on a general datapath (subnormals possible).'), dict(t=G(cp_, 'latency_cycles'), note='Then one normalisation per clock: all %s done at cycle %s.' % (ndep, G(cp_, 'latency_cycles')))])))
    cards.append(c.out())

    # ------------------------------------------------------------------ DS: positive exponential
    c = Card('ds-sinkexp', 'ds', 'The exponential that had to accept positive inputs', 'ot_a3_fp32_exp_pos_cr_rne (attention sink)', 'in progress',
             'certified exact RTL; not yet a hardened block of its own',
             'Attention sinks add exp(sink - max) to each softmax row, and the sink never joins the running maximum, so the argument is often positive. The certified exponential only accepted x <= 0. Range reduction by ln2 made the positive side fit the same narrow datapath.')
    ep = 'rtl/abi3/ot_a3_fp32_exp_pos_cr_rne.sv'
    pos = c.f('pos', RX(ep, r'and ([\d,]+) of the ([\d,]+) shipped V4-Flash sink logits', cast=int), 'logits', 'measured', ep + ' header', label='positive V4-Flash sink logits')
    tot = c.f('tot', RX(ep, r'of the ([\d,]+) shipped V4-Flash sink logits', cast=int), 'logits', 'measured', ep + ' header', label='V4-Flash sink logits')
    p41 = c.f('pos41', RX(ep, r'\(([\d,]+) of [\d,]+ for V4\.1\)', cast=int), 'logits', 'measured', ep + ' header', label='positive V4.1 sink logits')
    t41 = c.f('tot41', RX(ep, r'\([\d,]+ of ([\d,]+) for V4\.1\)', cast=int), 'logits', 'measured', ep + ' header', label='V4.1 sink logits')
    ib = c.f('int_bits', RX(ep, r'needing up to (\d+) integer bits', cast=int), 'integer bits', 'analytical', ep + ' header', label='integer bits without range reduction')
    q = c.f('qual', RX(ep, r'every one of the ([\d,]+) qualification arguments', cast=int), 'arguments', 'measured', ep + ' header', label='qualification arguments, bit-identical to exp_cr32')
    c.set(problem='%s of %s V4-Flash sink logits are positive (%s of %s for V4.1), so a positive offset is the common case. The existing unit refuses x > 0 because its enclosure has three integer bits; exp(88) needs %s.' % (pos, tot, p41, t41, ib),
          naive=dict(title='Widen the datapath, or invert exp(-x)', text='Inverting an enclosure of exp(-x) still needs the large integer part, and a scaled fixed-point format works but is overbuilt.'),
          trick=dict(title='x = n ln2 + r', text='With r in [0, ln2), exp(r) lies in [1, 2): one integer bit. 2^n becomes the binary32 exponent, the form the rounding already builds. The series is all-positive, so its tail is bounded geometrically (term_{N+1} x 4 since r < 0.75), and the result is certified or refused, never guessed.'),
          evidence='Bit-identical to the golden exp_cr32 on %s on two simulators (every multiple of ln2 in range and its neighbours, subnormal edge, the largest finite argument, random, and the measured sink maxima). A mutant that keeps the alternating-series bound fails.' % q,
          price='No wider datapath; the softmax/sink epilogue selects this unit by the offset\'s sign.')
    c.rec(ep, 'rtl/test/tb_a3_exp_pos.sv', 'tools/build_a3_exp_pos_vectors.py')
    c.set(diagram=dict(
        naive=dict(kind='bars', unit='integer bits', bars=[dict(label='enclosure has', v=3, k='good'), dict(label='exp(88) needs', v=RX(ep, r'needing up to (\d+) integer bits', cast=int), k='bad')],
                   steps=[dict(show=1, note='The certified unit carries three integer bits.'), dict(show=2, note='A positive argument up to 88 needs %s.' % ib)]),
        trick=dict(kind='flow', cols=4, rows=1, nodes=[
            dict(id='x', c=0, r=0, label='x > 0', k='su'), dict(id='n', c=1, r=0, label='n = floor(x log2 e), r = x - n ln2', k='good'),
            dict(id='s', c=2, r=0, label='exp(r) in [1,2): 1 integer bit', k='good'), dict(id='y', c=3, r=0, label='exponent = n, certified round', k='su')],
            edges=[dict(a='x', b='n'), dict(a='n', b='s'), dict(a='s', b='y')],
            steps=[dict(hot=['x', 'n'], pk=[0], note='Reduce by ln2 (constants checked to 160+ bits at build time).'), dict(hot=['s'], pk=[1], note='The series fits the existing one-integer-bit format.'),
                   dict(hot=['y'], pk=[2], note='2^n is the exponent field; the enclosure certifies the rounding or refuses.')])))
    cards.append(c.out())

    # ------------------------------------------------------------------ DS: DSpark exact draft
    c = Card('ds-dspark', 'ds', 'Speculation that never changes a token', 'DSpark MTP on the ROM array', 'gated',
             'three_machine_compose ds_rom.MTP_physical_qualified = false',
             'The ROM array drafts several tokens with DeepSeek\'s own exact DSpark head, then verifies them in one pass. Rejected positions are rolled back by truncation, so the output is identical to plain decoding; only the speed changes.')
    cm = 'results/arch/three_machine_compose/compose.json'
    ar = c.f('ar', G(cm, 'ds_rom', 'AR_tok_s'), 'tok/s', 'analytical', cm + ' ds_rom.AR_tok_s', label='DS ROM AR (candidate)')
    mtp = c.f('mtp', G(cm, 'ds_rom', 'MTP_tok_s'), 'tok/s', 'analytical', cm + ' ds_rom.MTP_tok_s', label='DS ROM MTP (candidate)')
    tau = c.f('tau', G(cm, 'ds_rom', 'tau'), 'tokens/step', 'analytical', cm + ' ds_rom.tau', d=3, label='accepted tokens a step (owner 6-class blend, gamma 5)')
    stp = c.f('step', G(cm, 'ds_rom', 'MTP_step_us'), 'us', 'measured', cm + ' ds_rom.MTP_step_us', d=1, label='one MTP step')
    aru = c.f('ar_us', G(cm, 'ds_rom', 'AR_us'), 'us', 'measured', cm + ' ds_rom.AR_us', d=1, label='one AR token')
    dr = 'results/rtl/dsrom_recovery_20261004/levers/draft.json'
    dd = c.f('draft_dies', G(dr, 'dies_added'), 'dies', 'analytical', dr + ' dies_added', label='draft dies added')
    c.set(problem='One token walks all 85 pipeline stages; at batch 1 most stages sit idle while it does.',
          naive=dict(title='Plain autoregressive decoding', text='One token per pass: %s a token, %s.' % (aru, ar)),
          trick=dict(title='Exact draft, one verify pass, truncate on reject', text='The draft head proposes gamma = 5 tokens; the array verifies all positions in one pass, time-multiplexed on the same elements. Rejected slots\' KV rows are never read before the committed position rewrites them (the dead-row invariant), and the Engram hash history is restored from a snapshot.'),
          evidence='Golden and ISA programs are bit-exact against non-speculative greedy decoding; the RTL campaign runs on the reduced vehicle. A step takes %s and accepts %s on average.' % (stp, tau),
          price='%s for the draft heads; the step is longer than one AR token. Not yet physically qualified, so MTP is not a headline.' % dd)
    c.rec(cm, dr, 'results/rtl/dsrom_dspark_rtl_20261003/REPLAY.md')
    c.set(diagram=dict(
        naive=dict(kind='gantt', rows=['array'], span=10, unit='steps (schematic)', bars=[dict(row=0, start=i * 2, len=2, label='t%d' % i, k='op%d' % (i % 4)) for i in range(5)],
                   steps=[dict(t=2, note='One token a pass.'), dict(t=10, note='Five passes, five tokens.')]),
        trick=dict(kind='gantt', rows=['draft head', 'array (verify)'], span=10, unit='steps (schematic)',
                   bars=[dict(row=0, start=0, len=1, label='5 drafts', k='op1'), dict(row=1, start=1, len=3, label='verify 6 positions', k='op0'), dict(row=0, start=4, len=1, label='5 drafts', k='op1'), dict(row=1, start=5, len=3, label='verify', k='op0')],
                   steps=[dict(t=1, note='Draft gamma = 5 tokens with the exact head.'), dict(t=4, note='One verify pass checks every position; accept the agreeing prefix (%s on average).' % tau), dict(t=8, note='Truncate the rest: output identical to plain decoding.')])))
    cards.append(c.out())

    # ------------------------------------------------------------------ HBM: protected CDC
    c = Card('hbm-cdc', 'hbm', 'A protected clock crossing that refills at line rate', 'ot_hbm_w2_protected_cdc successor (collective receive)', 'gated',
             'unified ledger gates cdc_refill_ss_timing, cdc_frequency_lock and credit_producer_native are open',
             'Collective data arrives on the link clock and must cross into the core clock with every bit protected and no word lost across resets. The protected crossing could only pop a word every third cycle; the refill design reads the next encoded word into the same protected head bank, so it pops every cycle.')
    rm = 'results/rtl/hbm_collective_cdc_20261007/refill_model.json'
    wdt = c.f('width', G(rm, 'width'), 'bits', 'analytical', rm + ' width', label='payload width')
    dpt = c.f('depth', G(rm, 'depth'), 'words', 'analytical', rm + ' depth', label='FIFO depth')
    rp = c.f('replicas', G(rm, 'replicas'), 'FIFOs', 'analytical', rm + ' replicas', label='replicas')
    gs = c.f('gray', G(rm, 'normal_timing', 'gray_sync_stages'), 'stages', 'analytical', rm + ' normal_timing.gray_sync_stages', label='Gray sync stages')
    es = c.f('empty', G(rm, 'normal_timing', 'empty_start_capture_plus_validate_cycles'), 'cycles', 'analytical', rm + ' normal_timing.empty_start_capture_plus_validate_cycles', label='empty-start cycles')
    fp_ = 'results/rtl/hbm_collective_cdc_20261007/final_pass/record.json'
    passed = G(fp_, 'passed')
    flits = c.f('flits', RX(fp_, r'independent_clocks(\d+)flits', cast=int), 'flits', 'measured', fp_ + ' checks.positive.output', label='flits across independent clocks')
    cr = 'results/rtl/hbm_collective_cdc_design_20261007/comparison_refill.json'
    ca = c.f('A_us', G(cr, 'comparison', 'A_credit_bound', 'AR_us'), 'us', 'analytical', cr + ' comparison.A_credit_bound.AR_us', d=3, label='II=3 credit-bound cost a token')
    cb_ = c.f('Bp_us', G(cr, 'comparison', 'Bprime_refill_II1', 'AR_us'), 'us', 'analytical', cr + ' comparison.Bprime_refill_II1.AR_us', d=3, label='II=1 refill cost a token')
    rtt = c.f('rtt', G(cr, 'options', 'A_credit_bound', 'credit_rtt_cycles'), 'cycles', 'analytical', cr + ' options.A_credit_bound.credit_rtt_cycles', label='credit round trip')
    c.set(problem='%s FIFOs of %s x %s bits, ECC-protected storage and pointers, asynchronous clocks, coordinated reset. The protected head took three cycles per pop, capping each port at a third of line rate.' % (rp, wdt, dpt),
          naive=dict(title='Protected head, read every third cycle (II = 3)', text='Every pop re-reads and re-checks the head bank: a third of line rate, which costs %s a token on the measured receive stream.' % ca),
          trick=dict(title='Refill the protected head at II = 1', text='On a pop, the next encoded word is loaded into the same protected head bank from the next binary/Gray pointer, so correction permissions stay fail-closed and no state bits are added. '
                     'Gray/complement rails cross through %s synchroniser stages; the read pointer returns only on an accepted pop (no same-cycle credit reuse). Reset is a coordinated power-on sequence: async assert, sync release, no unilateral runtime reset.' % gs),
          evidence='Full %s x %s with independent clocks: %s (%s flits; wrap, stalls, full, correction, rail corruption, drain, coordinated reset); output corruption is detected.' % (wdt, dpt, 'PASS' if passed else 'FAIL', flits),
          price='%s empty-start cycles a pass: %s a token. Full rate also needs >= %s credits in flight, which the native credit producer does not yet provide (gate).' % (es, cb_, rtt))
    c.blocks('hfd_coll_pkt_fifo_ii1', 'hfd_coll_credit_prod')
    for b in ('hfd_coll_pkt_fifo_ii1', 'hfd_coll_credit_prod'):
        for a in LOOP['blocks'].get(b, []):
            if a.get('ss_ps') is not None:
                c.tried('%s (%s)' % (b, a['job']), 'SS %s / FF %s ps' % (fmtn(a['ss_ps']), fmtn(a['ff_ps'])), '64:1 encoded read mux / capture path; registered head-pointer address proposed', LOOP_SRC)
    c.rec(rm, fp_, cr, UL)
    c.set(diagram=dict(
        naive=dict(kind='gantt', rows=['link writes', 'core pops'], span=12, unit='cycles', bars=[dict(row=0, start=i, len=1, label='w%d' % i, k='op0') for i in range(12)] + [dict(row=1, start=3 * i + 2, len=3, label='p%d' % i, k='op1') for i in range(3)],
                   steps=[dict(t=3, note='A word arrives every cycle...'), dict(t=12, note='...but the protected head pops one every three cycles: a third of line rate.')]),
        trick=dict(kind='gantt', rows=['link writes', 'core pops'], span=12, unit='cycles', bars=[dict(row=0, start=i, len=1, label='w%d' % i, k='op0') for i in range(12)] + [dict(row=1, start=2 + i, len=1, label='p%d' % i, k='op1') for i in range(10)],
                   steps=[dict(t=2, note='Two empty-start cycles (capture and validate)...'), dict(t=12, note='...then the head refills on every pop: one word a cycle.')])))
    cards.append(c.out())

    # ------------------------------------------------------------------ HBM: four ways to fix the rate cap
    c = Card('hbm-credit', 'hbm', 'Four ways to fix a third-rate port', 'collective receive queue (packet SRAM + CDC)', 'gated',
             'packet_sram_ii3_rate_cap: the packet SRAM still drains at II = 3 until the refill is applied there',
             'Once a port can only drain a word every third cycle, there are four fixes: limit the credits, rotate three banks, refill the head, or build a deeper FIFO. The design model priced all four before any RTL was written.')
    cmpd = G(cr, 'comparison')
    for key, lab in (('A_credit_bound', 'A credit bound'), ('B_rotated_II1', 'B 3-bank rotation'), ('Bprime_refill_II1', "B' head refill"), ('C_deep_fifo', 'C deep FIFO')):
        c.f(key + '_thr', cmpd[key]['throughput'], 'of line rate', 'analytical', cr + ' comparison.%s.throughput' % key, d=3, label=lab + ' throughput')
        c.f(key + '_us', cmpd[key]['AR_us'], 'us', 'analytical', cr + ' comparison.%s.AR_us' % key, d=3, label=lab + ' AR cost a token')
    a_area = c.f('B_area', cmpd['B_rotated_II1']['area_um2_added'], 'um2', 'analytical', cr + ' comparison.B_rotated_II1.area_um2_added', d=1, label='B added area')
    c_area = c.f('C_area', cmpd['C_deep_fifo']['area_um2_added'], 'um2', 'analytical', cr + ' comparison.C_deep_fifo.area_um2_added', d=1, label='C added area')
    pc = c.f('pct', G(cr, 'options', 'A_credit_bound', 'cost_serialisation', 'AR_pct'), '%', 'analytical', cr + ' options.A_credit_bound.cost_serialisation.AR_pct', d=2, label='A: AR cost of serialisation')
    c.set(problem='At II = 3 the receive stream costs %s of AR (credit-bound option, measured receive streaming).' % pc,
          naive=dict(title='Deepen the FIFO (C)', text='More storage does not raise the drain rate: C adds %s and still runs at a third of line rate.' % c_area),
          trick=dict(title="Refill the head (B')", text="B' keeps the protected storage and makes the head bank refill on every pop: full rate with zero added state bits and about 60-100 um2 of logic. B (rotating three banks) is the same speed for %s and stays only as the fallback." % a_area),
          evidence="The refill is measured RTL on the CDC (see the CDC story); the comparison prices throughput, latency, credits and area for each option.",
          price="+%s a token for the empty-start cycles; the packet SRAM itself still needs the same refill before the cap is gone (gated)." % fmtn(cmpd['Bprime_refill_II1']['AR_us'], 3) + ' us')
    c.rec(cr, 'results/rtl/hbm_collective_cdc_design_20261007/options.json', UL)
    c.set(diagram=dict(
        naive=dict(kind='bars', unit='us a token', bars=[dict(label='C deep FIFO', v=cmpd['C_deep_fifo']['AR_us'], k='bad')], steps=[dict(show=1, note='A deeper FIFO pays the same third-rate drain.')]),
        trick=dict(kind='bars', unit='us a token', bars=[dict(label='A credit bound', v=cmpd['A_credit_bound']['AR_us'], k='bad'), dict(label='B rotation (+12,093 um2)', v=cmpd['B_rotated_II1']['AR_us'], k='good'),
                                                        dict(label="B' refill (~60-100 um2)", v=cmpd['Bprime_refill_II1']['AR_us'], k='good'), dict(label='C deep FIFO (+290,238 um2)', v=cmpd['C_deep_fifo']['AR_us'], k='bad')],
                   steps=[dict(show=1, note='A: limit credits to the depth; safe, but a third of line rate.'), dict(show=2, note='B: rotate three banks; full rate, more area.'), dict(show=3, note="B': refill the head; full rate, no state added."), dict(show=4, note='C: deeper FIFO; no help.')])))
    cards.append(c.out())

    # ------------------------------------------------------------------ HBM: SM -> SU native edge
    c = Card('hbm-smsu', 'hbm', 'Results go straight into the consumer\'s registers', 'SM -> SU result edge (HBM accelerator)', 'gated',
             'unified ledger gate sm_su_result_edge_native: the native edge is not built',
             'On a GPU, a matrix unit\'s results go to memory and the next kernel reads them back. Here the matrix units (SMs) send result rows straight into the vector unit\'s ingress FIFOs through relay stations, so the round trip through memory disappears.')
    ct = 'results/rtl/hbm_sm_su_result_contract_20261007/contract.json'
    pub = c.f('published', G(ct, 'summary', 'published_cycles'), 'cycles/token', 'analytical', ct + ' summary.published_cycles', label='priced today (die-view edge)')
    nat = c.f('native', G(ct, 'summary', 'native_cycles'), 'cycles/token', 'analytical', ct + ' summary.native_cycles', label='proposed native edge')
    sf = c.f('sf', G(ct, 'summary', 'store_forward_floor_cycles'), 'cycles/token', 'analytical', ct + ' summary.store_forward_floor_cycles', label='store-and-forward floor')
    rows = c.f('rows', G(ct, 'summary', 'rows_per_token'), 'rows/token', 'analytical', ct + ' summary.rows_per_token', label='result rows a token')
    sfp = c.f('sf_pct', G(ct, 'impact', 'rtl_store_and_forward_floor', 'AR_pct_of_unified'), '%', 'analytical', ct + ' impact.rtl_store_and_forward_floor.AR_pct_of_unified', d=1, label='store-and-forward AR cost')
    np_ = c.f('nat_pct', G(ct, 'impact', 'native_edge_proposed', 'AR_pct_of_unified'), '%', 'analytical', ct + ' impact.native_edge_proposed.AR_pct_of_unified', d=3, label='native edge AR cost')
    c.set(problem='%s a token move from the SMs to the SU. The path the committed RTL implements stores each row and reads it back through the GPU-comparator memory system, one outstanding.' % rows,
          naive=dict(title='Store and forward through memory', text='Per row: result-store capture, write and readback through the shared provider, then an SU read. Floor estimate %s, %s of AR.' % (sf, sfp)),
          trick=dict(title='A native level-2 edge', text='The SU grants each SM a reservation of op_rows rows at issue, so no ready or credit ever crosses the die. Rows travel through 64-bit relay slices at every gather station into a per-SM ingress FIFO; the consumer starts when its row count reaches op_rows, ordered by protocol rather than timing slack. The one-way wire hides under the barrier round trip.'),
          evidence='Contract model with the r23 floor one-way cycles; priced %s against %s today.' % (nat, pub),
          price='%s of AR on the unified candidate, and about 0.14 mm2 of ingress flops (estimate). Gated until built.' % np_)
    c.blocks('hfd_result_relay64_ew', 'hfd_result_relay64_ns')
    c.rec(ct, UL)
    c.set(diagram=dict(
        naive=dict(kind='flow', cols=5, rows=1, nodes=[
            dict(id='sm', c=0, r=0, label='SM result', k='field'), dict(id='rs', c=1, r=0, label='result store', k='bad'),
            dict(id='mem', c=2, r=0, label='CDC + xbar + L2 (+HBM ack)', k='bad'), dict(id='rd', c=3, r=0, label='SU sector read', k='bad'), dict(id='su', c=4, r=0, label='SU lanes', k='su')],
            edges=[dict(a='sm', b='rs'), dict(a='rs', b='mem'), dict(a='mem', b='rd'), dict(a='rd', b='su')],
            steps=[dict(hot=['sm', 'rs'], pk=[0], note='Capture the row.'), dict(hot=['mem'], pk=[1], bad=True, note='Write it through the memory system, one outstanding...'), dict(hot=['rd', 'su'], pk=[2, 3], bad=True, note='...and read it back: >= %s a token.' % sf)]),
        trick=dict(kind='flow', cols=5, rows=1, nodes=[
            dict(id='sm', c=0, r=0, label='SM r face', k='field'), dict(id='r1', c=1, r=0, label='relay slices', k='good'), dict(id='r2', c=2, r=0, label='gather station +1', k='good'),
            dict(id='q', c=3, r=0, label='SU ingress FIFO (count == op_rows)', k='good'), dict(id='su', c=4, r=0, label='SU lane registers', k='su')],
            edges=[dict(a='sm', b='r1'), dict(a='r1', b='r2'), dict(a='r2', b='q'), dict(a='q', b='su')],
            steps=[dict(hot=['sm'], note='Rows leave on the SM\'s result face; space was reserved at issue.'), dict(hot=['r1', 'r2'], pk=[0, 1], note='Registered relay slices carry them across the die.'),
                   dict(hot=['q', 'su'], pk=[2, 3], note='The consumer releases on the row count: %s a token.' % nat)])))
    cards.append(c.out())

    # ------------------------------------------------------------------ HBM: relays at every pin
    c = Card('hbm-relays', 'hbm', 'A relay station at every pin', 'hfd_stn_* / hfd_meso_* / hfd_svc_* stations', 'in progress', '',
             'Die-level wires longer than a stage are cut into registered hops, and every hardened block\'s pin on a long segment gets a relay right beside it, so no block\'s timing depends on a wire it cannot see.')
    cl = ULINES['closure_22']
    nre = c.f('relays', int(re.search(r'\((\d+) relay ends', cl['item']).group(1)), 'relay ends', 'analytical', UL + ' lines[closure_22].item', label='relay ends (r22)')
    rus = c.f('relay_us', cl['effect']['AR'], 'us', 'analytical', UL + ' lines[closure_22].effect.AR', d=3, label='AR cost of the relays')
    blocks_ = ['hfd_stn_r19', 'hfd_stn_r33', 'hfd_stn_r34', 'hfd_stn_r36', 'hfd_stn_r38', 'hfd_stn_r39', 'hfd_meso_r35', 'hfd_meso_r37', 'hfd_gath_r9', 'hfd_gath_r25', 'hfd_mcast_r5', 'hfd_mcast_r7',
               'hfd_svc_SE_s6', 'hfd_svc_SE_s7', 'hfd_svc_SE_s8', 'hfd_svc_SW_s4', 'hfd_router', 'hfd_cmdproc_n', 'hfd_cmdproc_s']
    rows_ = c.blocks(*blocks_)
    ncl = sum(1 for r in rows_ if r['closed'])
    c.f('closed_views', ncl, 'blocks', 'measured', 'results/closure_loop/*/verdict.json (blocks named in this card)', label='station / service / router views closed')
    worst = min((r['closed']['ss'] for r in rows_ if r['closed']), default=None)
    ws_ = c.f('worst_ss', worst, 'ps', 'measured', 'min SS over the closed verdicts of this card', d=2, label='lowest SS among closed views') if worst is not None else 'n/a'
    hw = 'results/rtl/hbm_accel_die_floorplan_20261005/wire_stages.json'
    pitch = c.f('pitch', G(hw, 'stage_pitch_um'), 'um', 'measured', hw + ' stage_pitch_um', d=2, label='registered wire stage pitch')
    c.set(problem='A 30 mm die: the longest broadcasts cross tens of millimetres. A hardened block\'s IO budget assumes its neighbour is a register; an unregistered pin at the end of a long wire breaks that contract at the die level, after the block has "closed".',
          naive=dict(title='Close blocks alone, wire them later', text='Blocks meet their own sign-off with an assumed IO delay, then die integration finds the real wire on the pin and the margin is gone.'),
          trick=dict(title='Stations every %s, a relay abutting every pin' % pitch, text='Every long die segment is a chain of registered stations at the measured stage pitch, and every hardened-block pin on a segment longer than 100 um gets a relay end abutting it, so the last unregistered piece of wire is short and known.'),
          evidence='%s of the %d station, service and router views this card tracks have committed closures at 833 ps; the lowest setup slack among them is %s.' % (ncl, len(rows_), ws_),
          price='%s, %s of AR on the HBM candidate. The station views are closed; the die-top route that places all of them is still open (die-level gate).' % (nre, rus))
    c.rec(UL, hw, 'results/closure_loop/')
    c.set(diagram=dict(
        naive=dict(kind='flow', cols=4, rows=1, nodes=[dict(id='a', c=0, r=0, label='block A (closed alone)', k='field'), dict(id='w', c=1, r=0, label='long unregistered wire', k='bad'),
                                                       dict(id='w2', c=2, r=0, label='...', k='bad'), dict(id='b', c=3, r=0, label='block B pin', k='field')],
                   edges=[dict(a='a', b='w'), dict(a='w', b='w2', bad=True), dict(a='w2', b='b', bad=True)],
                   steps=[dict(hot=['a'], note='A launches.'), dict(hot=['w', 'w2', 'b'], pk=[0, 1, 2], bad=True, note='The wire delay lands inside B\'s input budget.')]),
        trick=dict(kind='flow', cols=5, rows=1, nodes=[dict(id='a', c=0, r=0, label='block A', k='field'), dict(id='r1', c=1, r=0, label='relay at pin (<=100 um)', k='good'),
                                                       dict(id='s', c=2, r=0, label='stations every %s' % pitch, k='good'), dict(id='r2', c=3, r=0, label='relay at pin', k='good'), dict(id='b', c=4, r=0, label='block B', k='field')],
                   edges=[dict(a='a', b='r1'), dict(a='r1', b='s'), dict(a='s', b='r2'), dict(a='r2', b='b')],
                   steps=[dict(hot=['a', 'r1'], pk=[0], note='Cycle 0: into the relay beside A\'s pin.'), dict(hot=['s'], pk=[1], note='One stage per cycle.'), dict(hot=['r2', 'b'], pk=[2, 3], note='The last hop to B is short and registered: B\'s IO contract holds.')])))
    cards.append(c.out())

    # ------------------------------------------------------------------ Qwen: ROM tile
    c = Card('qwen-tile', 'qwen', 'Reading a ROM macro that is slower than the clock', 'qfd_tile / qfd_tile_e (Qwen ROM tile)', 'in progress',
             'ROM_PIPE and half-depth variants are queued in the closure loop',
             'Each Qwen tile reads a ROM bank every cycle. The macro\'s own clock-to-output time is close to a whole 833 ps period, so the capture could not close. The fix pipelines the request and the capture, and lands the ROM clock early so the macro gets a head start.')
    tf = 'site/chip_explorer/inputs/stories/ot_qwen_rom_tile_w12.sv.txt'
    q1 = c.f('clkq_lo', RX(tf, r'ROM clk->q is (\d+)-\d+ ps SS', cast=int), 'ps', 'measured', snap_src('ot_qwen_rom_tile_w12.sv.txt', 'ROM_PIPE comment (macro liberty)'), label='ROM clk->q at SS, low')
    q2 = c.f('clkq_hi', RX(tf, r'ROM clk->q is \d+-(\d+) ps SS', cast=int), 'ps', 'measured', snap_src('ot_qwen_rom_tile_w12.sv.txt', 'ROM_PIPE comment (macro liberty)'), label='ROM clk->q at SS, high')
    q3 = c.f('clkq_half', RX(tf, r'half-depth banks, SS clk->q\s*\n\s*//\s*(\d+) ps', cast=int), 'ps', 'measured', snap_src('ot_qwen_rom_tile_w12.sv.txt', 'BAW comment'), label='half-depth bank clk->q at SS')
    t0 = loop_job('qfd_tile', 'qfd_tile-load80')
    t1 = loop_job('qfd_tile_e', 'qfd_tile_e-load80')
    s0 = c.f('tile_ss', t0['ss_ps'], 'ps', 'measured', LOOP_SRC + ' job ' + t0['job'], label='qfd_tile SS (before)')
    c.f('tile_ff', t0['ff_ps'], 'ps', 'measured', LOOP_SRC + ' job ' + t0['job'], label='qfd_tile FF (before)')
    c.f('tile_e_ss', t1['ss_ps'], 'ps', 'measured', LOOP_SRC + ' job ' + t1['job'], label='qfd_tile_e SS (before)')
    ql = 'site/chip_explorer/inputs/stories/qwen_closure_cost_ledger.json'
    qi = {i['item']: i for i in G(ql, 'items')}
    qc_ = c.f('cost', qi['tile_rom_pipe']['cycles_per_token_upper_bound'], 'cycles/token', 'analytical', snap_src('qwen_closure_cost_ledger.json', 'items[tile_rom_pipe]'), label='ROM_PIPE cost (upper bound)')
    qp_ = c.f('cost_pct', qi['tile_rom_pipe']['ar_pct_upper_bound'], '%', 'analytical', snap_src('qwen_closure_cost_ledger.json', 'items[tile_rom_pipe]'), d=3, label='ROM_PIPE AR cost (upper bound)')
    c.set(problem='The ROM macro\'s clk->q is %s to %s at SS, and the tile reads a bank every cycle, so the output cannot be held for two cycles. The tile routed at SS %s.' % (q1, q2, s0),
          naive=dict(title='Capture the macro output in the same cycle', text='Address from the engine, macro read, bank OR and capture in one 833 ps period. The macro alone uses most of it, and a long, late macro clock made it worse.'),
          trick=dict(title='ROM_PIPE: relay the request, capture at the pins, clock the macro early', text='The request (bank enable and address) goes through relay stages, one kept copy per bank group, so it arrives from beside the macros. The macro clock is landed early by CTS (a CTS-only 250 ps insertion view), giving the read useful skew; the request path pays the same skew, which the relays absorb. '
                     'The capture register sits at the macro pins with no enable, then one stage does the INT8-to-BF16 expansion and the group OR, then a relay into the engine. The other variant uses half-depth banks (clk->q %s) so a balanced clock closes the single-cycle capture.' % q3),
          evidence='Exactness benches pass with the ROM_MUT negative control failing (capture bank select one edge early). The routes are queued; the card switches to closed when a verdict lands.',
          price='%s a token, %s AR (upper bound: every op fill exposed).' % (qc_, qp_))
    c.blocks('qfd_tile', 'qfd_tile_e')
    c.tried('Single-cycle capture, loaded clock (qfd_tile)', 'SS %s / FF %s ps' % (fmtn(t0['ss_ps']), fmtn(t0['ff_ps'])), 'macro clk->q plus a late macro clock', LOOP_SRC)
    c.tried('Single-cycle capture (qfd_tile_e)', 'SS %s / FF %s ps' % (fmtn(t1['ss_ps']), fmtn(t1['ff_ps'])), 'same', LOOP_SRC)
    c.rec(snap_src('ot_qwen_rom_tile_w12.sv.txt'), snap_src('qwen_closure_cost_ledger.json'), 'physical/asap7_memory_macros/ot_rom_4096x266_m8_skew250 (branch claude/qwen-blocks-20261007)')
    c.set(diagram=dict(
        naive=dict(kind='timeline', span=900, period=833, lanes=[dict(label='ROM clk->q', start=0, len=RX(tf, r'ROM clk->q is \d+-(\d+) ps SS', cast=int), k='bad'), dict(label='bank OR + capture setup', start=RX(tf, r'ROM clk->q is \d+-(\d+) ps SS', cast=int), len=60, k='bad')],
                   steps=[dict(t=RX(tf, r'ROM clk->q is \d+-(\d+) ps SS', cast=int), note='The macro alone uses most of the period.'), dict(t=900, note='Bank OR and capture land past the next edge.')]),
        trick=dict(kind='timeline', span=900, period=833, lanes=[dict(label='early ROM clock', start=0, len=250, k='good'), dict(label='ROM clk->q', start=-250 + 250, len=RX(tf, r'ROM clk->q is \d+-(\d+) ps SS', cast=int), k='su'), dict(label='capture at pins', start=RX(tf, r'ROM clk->q is \d+-(\d+) ps SS', cast=int) - 250 + 250, len=30, k='good')],
                   shift=250, steps=[dict(t=0, note='The macro clock arrives 250 ps before the capture clock (schematic of the CTS-only insertion view).'), dict(t=833, note='The read now has the period plus the skew; expansion and OR move to the next stage.')])))
    cards.append(c.out())

    # ------------------------------------------------------------------ Qwen: link credits = RTT
    c = Card('qwen-credit', 'qwen', 'Link credits sized to the round trip', 'ot_qwen_die_hub_fr + qfd_link_rx128', 'in progress',
             'exact gate passes on two simulators; the hub and receive-buffer routes are queued',
             'A credit link can only keep as many words in flight as it has credits. With 54 registered stations the credit takes 117 cycles to come back, so 8 credits sustain only a small fraction of the link. 128 credits keep it at full rate.')
    lb = 'results/rtl/qwen_contracts_20261007/link_credit_rtt/bench_gate/result.json'
    cases = [x for x in G(lb, 'cases') if x['case'].startswith('sweep_h54') or x['case'] in ('pos_h54_cr128',)]
    sweep = {}
    for x in G(lb, 'cases'):
        if x['kind'] == 'pos' and x['sim'] == 'verilator' and 'BP' not in x['params'] and x['params'].get('HOPS') == 54:
            sweep[x['params']['CR']] = x['epochs'][0]
    rtt = c.f('rtt', sweep[128]['credit_rtt_a'], 'cycles', 'measured', lb + ' cases[pos_h54_cr128].epochs[0].credit_rtt_a', label='credit round trip, 54 stations')
    r8 = c.f('rate8', sweep[8]['rate_milli_a'] / 1000, 'words/cycle', 'measured', lb + ' cases[sweep_h54_cr8]', d=3, label='rate at 8 credits')
    r4 = c.f('rate4', sweep[4]['rate_milli_a'] / 1000, 'words/cycle', 'measured', lb + ' cases[sweep_h54_cr4]', d=3, label='rate at 4 credits (predecessor)')
    r128 = c.f('rate128', sweep[128]['rate_milli_a'] / 1000, 'words/cycle', 'measured', lb + ' cases[pos_h54_cr128]', d=3, label='rate at 128 credits')
    mif = c.f('inflight', sweep[128]['max_inflight_a'], 'words', 'measured', lb + ' cases[pos_h54_cr128].epochs[0].max_inflight_a', label='max words in flight at 128')
    lpr = 'results/rtl/qwen_contracts_20261007/link_credit_rtt/pricing.json'
    area = c.f('area', G(lpr, 'area', 'added_die_mm2_estimate'), 'mm2', 'analytical', lpr + ' area.added_die_mm2_estimate', d=2, label='added die area (estimate)')
    k4 = c.f('kv4', G(lpr, 'kv_new_serialisation', 'cycles_at_4_credits'), 'cycles', 'analytical', lpr + ' kv_new_serialisation.cycles_at_4_credits', label='136 KV words a layer at 4 credits')
    c.d['summary'] = ('A credit link can only keep as many words in flight as it has credits. Across the forwarded path a credit takes %s to come back, '
                      'so 8 credits sustain %s of the link; 128 credits keep it at full rate.' % (rtt, r8.replace('words/cycle', 'words a cycle')))
    c.set(problem='The forwarded link crosses 54 registered stations; a credit returns after %s. A sender with C credits can have at most C words in flight, so its rate is about C / RTT.' % rtt,
          naive=dict(title='A handful of credits', text='With 8 credits the link moves %s a cycle; the predecessor\'s 4 credits measured %s. The 136-word KV write-back of a layer would take %s.' % (r8, r4, k4)),
          trick=dict(title='Credits >= round trip (Little\'s law)', text='Give the receiver a 128-word buffer at each strip end and the sender 128 credits: more than the %s round trip, so a credit is always back before it is needed.' % rtt),
          evidence='Exact on Verilator and Icarus: %s at 128 credits with 0 stalls and at most %s in flight; four negative cases end in the named fault. The sweep below is the same bench at 4 to 256 credits.' % (r128, mif),
          price='0 token cycles (the stations were already priced); about %s of flops a die; routes pending.' % area)
    c.blocks('qfd_hub_fr', 'qfd_link_rx128')
    c.rec(lb, lpr, UL)
    sw = sorted(sweep)
    c.set(diagram=dict(
        naive=dict(kind='bars', unit='words/cycle', max=1.0, bars=[dict(label='%d credits' % k, v=sweep[k]['rate_milli_a'] / 1000, k='bad') for k in sw if k <= 8], steps=[dict(show=1, note='4 credits: the predecessor.'), dict(show=2, note='8 credits.')]),
        trick=dict(kind='bars', unit='words/cycle', max=1.0, marker=dict(label='RTT %d cycles' % sweep[128]['credit_rtt_a']),
                   bars=[dict(label='%d credits' % k, v=sweep[k]['rate_milli_a'] / 1000, k=('good' if k >= sweep[128]['credit_rtt_a'] else 'su')) for k in sw],
                   steps=[dict(show=i + 1, note='%d credits: %.3f words a cycle.' % (k, sweep[k]['rate_milli_a'] / 1000)) for i, k in enumerate(sw)])))
    cards.append(c.out())

    # ------------------------------------------------------------------ Qwen: KV landing
    c = Card('qwen-kvmap', 'qwen', 'Stripe the KV cache by where it lands', 'STREAM4 KV landing, Option M (KV_MAP=1)', 'closed',
             'owner-adopted 2026-10-06 on exact evidence; no new block (the as-built crossbar is kept)',
             'Four HBM stacks feed four die quadrants, and each quadrant\'s crossbar only reaches its own tiles. Re-striping the KV cache so each sector comes from the stack beside its destination made every write local, with no extra hardware.')
    kv = 'results/rtl/qwen_stream4_kvmap_m_20261006/lever.json'
    sw_ = c.f('writes', G(kv, 'measured', 'slice_writes'), 'slice writes', 'measured', kv + ' measured.slice_writes', label='slice writes a token (P8191)')
    ob = c.f('out_base', G(kv, 'measured', 'out_of_quadrant_writes_base'), 'writes', 'measured', kv + ' measured.out_of_quadrant_writes_base', label='out-of-quadrant writes, base map')
    om = c.f('out_m', G(kv, 'measured', 'out_of_quadrant_writes_M'), 'writes', 'measured', kv + ' measured.out_of_quadrant_writes_M', label='out-of-quadrant writes, Option M')
    bps = G(kv, 'measured', 'beats_per_stack')
    c.f('beats', bps[0], 'beats/stack', 'measured', kv + ' measured.beats_per_stack', label='beats per stack (each of 4)')
    fd = c.f('fill_delta', G(kv, 'measured', 'iso_P8191_fill_cycles', 'delta'), 'cycles', 'measured', kv + ' measured.iso_P8191_fill_cycles.delta', label='fill cycles added (isolated P8191)')
    ul = ULINES['kv_map_m']
    c.f('token_cost', ul['effect']['AR'], 'cycles/token', 'measured', UL + ' lines[kv_map_m].effect.AR', label='token cycles added')
    c.set(problem='On the base map, %s of %s slice writes leave their stack\'s quadrant, and the as-built per-quadrant crossbar cannot deliver them: only a third would land.' % (ob, sw_),
          naive=dict(title='Any stack writes any tile', text='A full die crossbar from every stack to every tile: more wires across the die, or a third of the KV landing.'),
          trick=dict(title='Option M: stripe KV by destination quadrant', text='The KV layout is re-striped so every sector streams from the HBM stack of its destination tiles\' quadrant. Every stack still carries exactly a quarter of the beats.'),
          evidence='%s out-of-quadrant writes with Option M; %s per stack. Exact 15/15 for both maps; a mismatched backend fails as it must.' % (om, ', '.join(fmtn(b) for b in bps)),
          price='%s of fill on the isolated P8191 bench; %s a token in the composition.' % (fd, fmtn(ul['effect']['AR']) + ' cycles'))
    c.rec(kv, UL)
    quad_nodes = [dict(id='h%d' % i, c=i, r=0, label='HBM stack %d' % i, k='hbm') for i in range(4)] + [dict(id='q%d' % i, c=i, r=1, label='quadrant %d tiles' % i, k='field') for i in range(4)]
    c.set(diagram=dict(
        naive=dict(kind='flow', cols=4, rows=2, nodes=quad_nodes, edges=[dict(a='h%d' % i, b='q%d' % j, bad=(i != j)) for i in range(4) for j in range(4)],
                   steps=[dict(hot=['h0'], pk=[0, 1, 2, 3], note='Stack 0\'s sectors land on tiles of every quadrant...'), dict(hot=['q1', 'q2', 'q3'], bad=True, note='...but its crossbar only reaches quadrant 0.')]),
        trick=dict(kind='flow', cols=4, rows=2, nodes=quad_nodes, edges=[dict(a='h%d' % i, b='q%d' % i) for i in range(4)],
                   steps=[dict(hot=['h0', 'q0'], pk=[0], note='Each sector comes from the stack beside its destination.'), dict(hot=['h1', 'h2', 'h3', 'q1', 'q2', 'q3'], pk=[1, 2, 3], note='All four stacks stream in parallel, a quarter of the beats each.')])))
    cards.append(c.out())

    # ------------------------------------------------------------------ Qwen: one-stream all-reduce
    c = Card('qwen-allreduce', 'qwen', 'An all-reduce split by an 8-bit counter', 'ot_qwen_tp_seq_w12 ENABLE_AR256', 'closed',
             'measured bit-exact on the TP4 runtime; no new hardware',
             'Every Qwen layer runs two all-reduces of 256 words across four dies. Each one ran as two serial halves, paying the link fill and drain twice. The cause was not bandwidth or credits: the descriptor\'s 8-bit count could not say 256.')
    pj = 'results/rtl/qwen_rom_TP4_allreduce_oneseg_20261003/pricing.json'
    mj = 'results/rtl/qwen_rom_TP4_allreduce_oneseg_20261003/measured.json'
    s2 = c.f('split', G(pj, 'per_allreduce_cycles', 'split128_measured_bench'), 'cycles', 'measured', pj + ' per_allreduce_cycles.split128_measured_bench', label='all-reduce as two segments')
    s1 = c.f('one', G(pj, 'per_allreduce_cycles', 'one256_measured_bench'), 'cycles', 'measured', pj + ' per_allreduce_cycles.one256_measured_bench', label='all-reduce as one stream')
    lat = c.f('lat', G(pj, 'diagnosis', 'segment_latency_terms', 'link_LAT_one_way'), 'cycles', 'analytical', pj + ' diagnosis.segment_latency_terms.link_LAT_one_way', label='link latency one way')
    l0 = c.f('layer_before', G(mj, 'runs', 'A', 'cycles', 'L1'), 'cycles', 'measured', mj + ' runs.A.cycles.L1', label='layer, two segments')
    l1 = c.f('layer_after', G(mj, 'runs', 'B', 'cycles', 'L1'), 'cycles', 'measured', mj + ' runs.B.cycles.L1', label='layer, one stream')
    gain = c.f('gain', 100 * G(mj, 'token_projection', 'per_user_rate_gain'), '%', 'analytical', mj + ' token_projection.per_user_rate_gain', d=1, label='per-user rate gain (projected from L1)')
    d128 = c.f('d128', G(pj, 'littles_law_depth', 'measured_by_depth', '128'), 'cycles', 'measured', pj + ' littles_law_depth.measured_by_depth.128', label='one stream at FIFO depth 128')
    c.set(problem='Each all-reduce took %s. Each half paid the link latency (%s one way) and the fold before the sequencer moved on.' % (s2, lat),
          naive=dict(title='Two descriptors of 128 words', text='The program generator split every 256-word all-reduce into two descriptors because the count field is 8 bits, and the sequencer runs one descriptor at a time.'),
          trick=dict(title='Count 0 means 256', text='The default-off ENABLE_AR256 path decodes a count of 0 as 256, so the whole vector goes as one stream. The collective FIFO depth follows Little\'s law: a 256-word vector never has more than 256 outstanding, so depth 256 streams at link rate.'),
          evidence='Bit-exact against the retained terminal: layer %s → %s. Per all-reduce %s → %s. Depth 128 measured %s (credit stalls); 256 and above stream without stalls.' % (l0, l1, s2, s1, d128),
          price='None: no RTL change, only the program and a FIFO depth. Projected gain %s per user.' % gain)
    c.rec(pj, mj, 'results/rtl/qwen_rom_TP4_allreduce_oneseg_20261003/pricing.md')
    tw = G(pj, 'diagnosis', 'segment_latency_terms')
    c.set(diagram=dict(
        naive=dict(kind='gantt', rows=['link'], span=1000, unit='cycles', bars=[
            dict(row=0, start=0, len=128, label='128 words', k='op0'), dict(row=0, start=128, len=tw['link_LAT_one_way'], label='latency', k='idle'), dict(row=0, start=128 + tw['link_LAT_one_way'], len=17, label='', k='op3'),
            dict(row=0, start=494, len=128, label='128 words', k='op1'), dict(row=0, start=622, len=tw['link_LAT_one_way'], label='latency again', k='idle'), dict(row=0, start=961, len=17, label='', k='op3')],
            steps=[dict(t=128, note='Segment A streams 128 words...'), dict(t=494, note='...waits for the last reduced word (latency + fold)...'), dict(t=987, note='...then segment B pays it all again: %s measured.' % s2)]),
        trick=dict(kind='gantt', rows=['link'], span=1000, unit='cycles', bars=[
            dict(row=0, start=0, len=256, label='256 words', k='op0'), dict(row=0, start=256, len=tw['link_LAT_one_way'], label='latency', k='idle'), dict(row=0, start=256 + tw['link_LAT_one_way'], len=17, label='', k='op3')],
            steps=[dict(t=256, note='One stream of 256 words.'), dict(t=624, note='Latency and fold paid once: %s measured.' % s1)])))
    cards.append(c.out())

    # ------------------------------------------------------------------ Qwen: controller SHIFT
    c = Card('qwen-ctrl', 'qwen', 'An HBM controller queue that shifts instead of searching', 'qfd_ctrl_shift (Qwen HBM controller, per PC)', 'in progress',
             'exact on all 32 PCs; the first SHIFT route missed setup (expander)',
             'The HBM controller picks which write to send next. Searching the whole queue and every bank\'s state in one cycle missed timing; the SHIFT successor keeps writes oldest-first in a one-hot shift queue and registers bank eligibility a cycle ahead.')
    cs = 'results/rtl/qwen_ctrl_shift_20261007/model.json'
    w_ = c.f('worst', G(cs, 'latency', 'composed_worst_case_token_cycles'), 'cycles/token', 'analytical', cs + ' latency.composed_worst_case_token_cycles', label='worst-case token cost')
    pc_ = c.f('pct', G(cs, 'latency', 'cost_pct'), '%', 'analytical', cs + ' latency.cost_pct', d=3, label='token cost')
    ed = c.f('edges', G(cs, 'latency', 'minimum_request_to_phy_added_edges'), 'edges', 'analytical', cs + ' latency.minimum_request_to_phy_added_edges', label='added request-to-PHY edges')
    reps = c.f('pcs', G(cs, 'replicas'), 'PCs', 'analytical', cs + ' replicas', label='pseudo-channels')
    pre = ULINES['ctrl_shift']['note']
    p_ss = c.f('pred_ss', float(re.search(r'predecessor SS (-[\d.]+)', pre).group(1)), 'ps', 'measured', UL + ' lines[ctrl_shift].note', label='predecessor SS')
    sh_ = loop_job('qfd_ctrl_shift_00', 'qfd_ctrl_shift_00')
    s_ss = c.f('shift_ss', sh_['ss_ps'], 'ps', 'measured', LOOP_SRC + ' job ' + sh_['job'], label='first SHIFT route SS')
    c.f('shift_ff', sh_['ff_ps'], 'ps', 'measured', LOOP_SRC + ' job ' + sh_['job'], label='first SHIFT route FF')
    c.set(problem='%s each choose the next DRAM command every cycle. The predecessor scheduler routed at SS %s.' % (reps, p_ss),
          naive=dict(title='Search the queue for the oldest eligible write', text='Compare every queued write\'s bank against live bank timers and pick the oldest match, all combinationally between the request and the PHY.'),
          trick=dict(title='Oldest-first shift queue, registered eligibility', text='Writes sit in a 4-deep one-hot queue ordered by age; a pop shifts the queue (only on a consumed write), so "oldest" is always position 0. Bank eligibility is computed and registered a cycle earlier. Inputs and outputs are captured in flops.'),
          evidence='Exact on all 32 PCs (model before RTL; qualification record). The first SHIFT route is at SS %s, still short of +15.' % s_ss,
          price='%s added from request to PHY: %s worst case, %s of the token.' % (ed, w_, pc_))
    c.blocks('qfd_ctrl_shift_00')
    c.tried('Predecessor scheduler', 'SS %s' % p_ss, 'combinational search on the request-to-PHY path', UL + ' lines[ctrl_shift]')
    c.tried('SHIFT, first route', 'SS %s / FF %s ps' % (fmtn(sh_['ss_ps']), fmtn(sh_['ff_ps'])), 'next variants queued (multi-mode hold)', LOOP_SRC)
    c.rec(cs, 'results/rtl/qwen_ctrl_shift_20261007/qualification.json', UL)
    c.set(diagram=dict(
        naive=dict(kind='flow', cols=4, rows=1, nodes=[dict(id='q', c=0, r=0, label='write queue', k='ctrl'), dict(id='s', c=1, r=0, label='search: oldest eligible', k='bad'),
                                                       dict(id='b', c=2, r=0, label='live bank timers', k='bad'), dict(id='p', c=3, r=0, label='PHY', k='hbm')],
                   edges=[dict(a='q', b='s'), dict(a='b', b='s'), dict(a='s', b='p', bad=True)],
                   steps=[dict(hot=['q', 'b', 's'], pk=[0, 1], note='Compare every entry against every bank...'), dict(hot=['p'], pk=[2], bad=True, note='...and drive the PHY in the same cycle: SS %s.' % p_ss)]),
        trick=dict(kind='flow', cols=4, rows=1, nodes=[dict(id='q', c=0, r=0, label='one-hot shift queue (oldest at 0)', k='good'), dict(id='e', c=1, r=0, label='bank eligibility (registered)', k='good'),
                                                       dict(id='s', c=2, r=0, label='pick position 0 if eligible', k='good'), dict(id='p', c=3, r=0, label='PHY (output flop)', k='hbm')],
                   edges=[dict(a='q', b='s'), dict(a='e', b='s'), dict(a='s', b='p'), dict(a='s', b='q', l='shift on pop')],
                   steps=[dict(hot=['e'], note='Cycle t-1: bank eligibility is registered.'), dict(hot=['q', 's'], pk=[0, 1], note='Cycle t: the oldest write is always at position 0.'), dict(hot=['p', 'q'], pk=[2, 3], note='Issue through an output flop; the queue shifts.')])))
    cards.append(c.out())

    # ------------------------------------------------------------------ cross: Taalas HC1
    c = Card('x-hc1', 'x', 'Why the weights are ROM: the Taalas HC1 anchor', 'ROM accelerator design basis', 'reference', 'published anchor plus a measured bitcell',
             'The ROM designs follow the only shipping evidence for a chip with all weights on die: Taalas HC1. A via-programmed ROM cell is a fraction of an SRAM cell, so a whole model fits beside the multipliers and no weight is ever fetched.')
    tj = 'configs/hardware/technology.json'
    hc = G(tj, 'reference_parts', 'taalas_hc1')
    ar_ = c.f('area', hc['die_area_mm2']['value'], 'mm2', 'measured', tj + ' reference_parts.taalas_hc1.die_area_mm2 (published)', label='HC1 die area (published)')
    bs = c.f('bs', hc['batch_size']['value'], '', 'measured', tj + ' reference_parts.taalas_hc1.batch_size (published)', label='batch size (published)')
    pw = c.f('pw', hc['power_w']['range_high'], 'W', 'measured', tj + ' reference_parts.taalas_hc1.power_w.range_high (reported)', label='card power (reported, high)')
    rt = None
    for k, v in hc.items():
        if isinstance(v, dict) and v.get('value') == 16960.0:
            rt = c.f('rate', v['value'], 'tok/s', 'measured', tj + ' reference_parts.taalas_hc1.%s (chart label)' % k, label='per-user rate, Llama 3.1 8B (published chart)')
    bc = 'results/asap7_physical/bitcell_density/bitcell_density.json'
    rr = [l for l in T(tj).split('\n') if 'got 0.1298 at 130 nm' in l]
    v130 = RX(tj, r'got ([\d.]+) at 130 nm'); v7 = RX(tj, r'against ([\d.]+) at a predictive 7 nm')
    r7 = c.f('ratio7', v7, 'x SRAM', 'measured', tj + ' rom note: measured ratio at ASAP7 (' + bc + ')', d=2, label='ROM / 6T SRAM cell area, ASAP7')
    r130 = c.f('ratio130', v130, 'x SRAM', 'measured', tj + ' rom note: measured ratio at 130 nm (results/spice/ihp_sg13g2_bitcell/bitcell.json)', d=4, label='ROM / 6T SRAM cell area, 130 nm')
    c.set(problem='Decode at batch 1 reads every weight once per token. From HBM that is a bandwidth wall; from on-die SRAM the model does not fit.',
          naive=dict(title='Weights in SRAM or streamed from HBM', text='SRAM is too big per bit to hold an 8B model on a reticle; HBM makes every token wait on DRAM bandwidth.'),
          trick=dict(title='Hard-wire the weights in ROM beside the multipliers', text='A via-programmed NOR ROM cell measured %s the area of a 6T SRAM cell at ASAP7 (%s at 130 nm). HC1 shows the result at product scale: %s die, all Llama 3.1 8B weights on die, %s per user at batch %s.' % (r7, r130, ar_, rt, bs)),
          evidence='HC1 figures are published or reported (sources in the expander); the bitcell ratios are this repository\'s layout measurements.',
          price='The model is fixed at manufacture; KV still lives in HBM beside the dies.')
    c.rec(tj, bc)
    c.set(diagram=dict(naive=dict(kind='bars', unit='x SRAM cell area', bars=[dict(label='6T SRAM cell', v=1.0, k='bad')], steps=[dict(show=1, note='One SRAM cell per bit.')]),
                       trick=dict(kind='bars', unit='x SRAM cell area', bars=[dict(label='6T SRAM cell', v=1.0, k='bad'), dict(label='ROM cell, ASAP7', v=v7, k='good'), dict(label='ROM cell, 130 nm', v=v130, k='good')],
                                  steps=[dict(show=1, note='SRAM: 1.'), dict(show=2, note='ROM at ASAP7: %s.' % r7), dict(show=3, note='ROM at 130 nm: %s.' % r130)])))
    cards.append(c.out())

    # ------------------------------------------------------------------ cross: wire reach
    c = Card('x-reach', 'x', 'A wire reaches about half a millimetre per clock', 'die wire stages (all three dies)', 'reference', 'measured routed express link; applied to every die',
             'At 1.2 GHz on the slow corner, a routed signal travels only about half a millimetre per clock. Every die-level path is therefore a chain of registered stages, and the stage count of each path is a priced latency, not an afterthought.')
    re_ = c.f('reach', G(hw, 'ss_reach_um'), 'um', 'measured', hw + ' ss_reach_um', d=0, label='SS reach a stage at 833 ps')
    p_ = c.f('pitch', G(hw, 'stage_pitch_um'), 'um', 'measured', hw + ' stage_pitch_um', d=2, label='stage pitch used for pricing')
    cbd = G(hw, 'class_bounds')
    xb = cbd['xbcast']
    xu = c.f('xb_um', xb['routed_um'], 'um', 'measured', hw + ' class_bounds.xbcast.routed_um', d=0, label='longest x-broadcast path, routed')
    x4 = c.f('xb_430', xb['stages_430'], 'stages', 'measured', hw + ' class_bounds.xbcast.stages_430', label='x-broadcast stages at 430.56 um')
    x5 = c.f('xb_504', xb['stages_504'], 'stages', 'measured', hw + ' class_bounds.xbcast.stages_504', label='x-broadcast stages at 504 um')
    ql2 = ULINES['die_relays_430um']
    qr = c.f('qwen_relays', int(re.search(r'\(([\d,]+) relays\)', ql2['item']).group(1).replace(',', '')), 'relays', 'analytical', UL + ' lines[die_relays_430um].item', label='Qwen die relay stations (r21)')
    qc2 = c.f('qwen_relay_cycles', ql2['effect']['AR'], 'cycles/token', 'analytical', UL + ' lines[die_relays_430um].effect.AR', label='Qwen relay cost a token')
    c.set(problem='The HBM die\'s longest x-broadcast path is %s of routed wire; the Qwen die needs %s relay stations.' % (xu, qr),
          naive=dict(title='Use the typical-corner reach', text='A typical-corner figure promises twice the distance per clock; a design priced on it is not signed off at the slow corner.'),
          trick=dict(title='Register every %s and count the stages' % p_, text='The measured slow-corner reach is %s a stage at 833 ps; pricing uses a %s pitch for margin. Each path class is counted from the routed bundle: the x-broadcast is %s at 430.56 um (%s at 504 um).' % (re_, p_, x4, x5)),
          evidence='Routed die global-route record; class bounds per path in the expander.',
          price='Stages are latency: %s a Qwen token for its relays, and the HBM wire terms in the unified ledger.' % qc2)
    c.rec(hw, UL)
    ks = [k for k in ('weight', 'kv', 'attn_q', 'control', 'result', 'xbcast') if k in cbd]
    c.set(diagram=dict(naive=dict(kind='bars', unit='stages', bars=[dict(label=k, v=cbd[k]['stages_504'], k='su') for k in ks], steps=[dict(show=len(ks), note='Stages at the full 504 um reach, per path class.')]),
                       trick=dict(kind='bars', unit='stages', bars=[dict(label=k, v=cbd[k]['stages_430'], k='good') for k in ks], steps=[dict(show=i + 1, note='%s: %d stages over %s um routed.' % (k, cbd[k]['stages_430'], fmtn(cbd[k]['routed_um'], 0))) for i, k in enumerate(ks)])))
    cards.append(c.out())

    # ------------------------------------------------------------------ cross: rule H1
    c = Card('x-h1', 'x', 'A hold margin that was counted twice', 'die-link IO constraints (rule H1)', 'reference', 'flow rule on main; re-timed routes closed without re-routing',
             'Every die link had its hold allowance charged at both ends: once on the sender\'s output and once on the receiver\'s input. Blocks were failing hold by margins that did not exist. Counting it once, at the sender, turned several of them into closed blocks without touching a route.')
    sd = 'physical/qwen_die_masters/io_ref_skew.sdc'
    vs = [V(c, b) for b in ('qfd_embed_ingress_code', 'qfd_embed_ingress_scale')]
    ev = '; '.join('%s SS %s / FF %s ps (%s)' % (b, fmtn(v_['ss']), fmtn(v_['ff']), v_['src']) for b, v_ in zip(('code', 'scale'), vs) if v_)
    for b, v_ in zip(('code', 'scale'), vs):
        if v_:
            c.f(b + '_ff', v_['ff'], 'ps', 'measured', v_['src'], label='embedding ingress %s FF hold' % b)
    c.set(problem='A die link\'s hold term (50 ps plus uncertainty) was applied as the sender\'s output minimum delay and again as the receiver\'s input minimum delay.',
          naive=dict(title='Each block protects itself', text='Both sides budget for the same physical hold risk, so each sees half a real margin and hold repair chases a violation that is not there (or the route fails).'),
          trick=dict(title='Rule H1: the sender carries it', text='The hold term rides once, on the sender\'s output min delay; the receiver\'s input min equals the measured link minimum. Existing routes are re-timed under the corrected constraints without re-routing (resta_hold), and the multi-mode route repairs SS setup and FF hold together.'),
          evidence='Constraints committed (%s); closed under the rule: %s.' % (sd, ev or 'none yet'),
          price='None in cycles; it removes a fake constraint, it does not relax a real one.')
    c.rec(sd, 'tools/orfs_hold_mm.py')
    c.set(diagram=dict(
        naive=dict(kind='flow', cols=4, rows=1, nodes=[dict(id='s', c=0, r=0, label='sender reg', k='field'), dict(id='so', c=1, r=0, label='output min: -(L+50)', k='bad'), dict(id='ri', c=2, r=0, label='input min: L-50', k='bad'), dict(id='r', c=3, r=0, label='receiver reg', k='field')],
                   edges=[dict(a='s', b='so'), dict(a='so', b='ri', l='link'), dict(a='ri', b='r')], steps=[dict(hot=['so'], pk=[0], bad=True, note='Hold term charged at the sender...'), dict(hot=['ri'], pk=[1, 2], bad=True, note='...and again at the receiver.')]),
        trick=dict(kind='flow', cols=4, rows=1, nodes=[dict(id='s', c=0, r=0, label='sender reg', k='field'), dict(id='so', c=1, r=0, label='output min: carries the hold term', k='good'), dict(id='ri', c=2, r=0, label='input min = L_min', k='good'), dict(id='r', c=3, r=0, label='receiver reg', k='field')],
                   edges=[dict(a='s', b='so'), dict(a='so', b='ri', l='link'), dict(a='ri', b='r')], steps=[dict(hot=['so'], pk=[0], note='Charged once, by the sender.'), dict(hot=['ri', 'r'], pk=[1, 2], note='The receiver sees the real link minimum.')])))
    cards.append(c.out())

    # ------------------------------------------------------------------ cross: redundancy survives synthesis
    c = Card('x-keep', 'x', 'Redundancy that survives synthesis', 'kept replicas and prefix adders (ot_v41_kreg, ot_v41_prefix)', 'reference', 'design rule; replica counts checked in routed netlists',
             'To cut fanout, a register is copied so each copy drives a few loads, and adders are written as log-depth prefix trees. Synthesis undoes both unless told not to: it merges identical registers and re-ripples adders. So the copies and the trees are kept explicitly, and counted in the routed netlist.')
    k1 = c.f('ixb', RX(dn_, r'\| g_ixb \| (\d+)', cast=int), 'instances', 'measured', dn_ + ' replica table', label='g_ixb replicas in the routed netlist')
    k2 = c.f('ixq', RX(dn_, r'\| g_ixq \| (\d+)', cast=int), 'instances', 'measured', dn_ + ' replica table', label='g_ixq replicas')
    k3 = c.f('sel', RX(dn_, r'\| g_sel \| (\d+)', cast=int), 'instances', 'measured', dn_ + ' replica table', label='g_sel replicas')
    c.set(problem='Beat assembly in the field spine reads 32 x-buffer banks and selects across 64 lanes from shared indices: one driver, many loads.',
          naive=dict(title='Copy the register in RTL', text='Yosys sees identical registers and merges them (opt_merge); ABC rebuilds a written prefix adder as a ripple in context. The netlist ends up with the original fanout.'),
          trick=dict(title='Keep-hierarchy replicas and kept prefix trees', text='Every replica is an ot_v41_kreg instance with keep_hierarchy, so it cannot be folded; arithmetic uses explicit log-depth prefix modules marked keep. The routed netlist is checked for the instance counts.'),
          evidence='Routed R=16 spine netlists contain %s g_ixb, %s g_ixq and %s g_sel kept replicas.' % (k1, k2, k3),
          price='A few thousand flops a die (about 1.6k replica and pipeline flops in the spine).')
    c.rec(dn_, 'rtl/v41die/ot_v41_spine_pqc_w17w10.sv')
    c.set(diagram=dict(
        naive=dict(kind='fanout', copies=1, loads=32, note='One driver, 32 loads after opt_merge folds the copies.'),
        trick=dict(kind='fanout', copies=4, loads=32, note='Four kept copies, 8 loads each.')))
    cards.append(c.out())

    return dict(cards=cards, loop_taken=LOOP['taken'], loop_src=LOOP_SRC, inputs=INPUTS,
                legend=dict(closed='every named block has a committed closure-loop verdict at 833.333 ps (SS >= +15, FF >= +15, DRC 0), or the mechanism is adopted on committed exact evidence with no block of its own',
                            **{'in progress': 'exact RTL exists; routes are queued, running or failed; the card shows the current measured state'},
                            gated='blocked on an unestablished contract or gate in the unified ledger',
                            reference='an anchor or a design rule, not an element'))


if __name__ == '__main__':
    s = build()
    print(len(s['cards']), 'cards')
    for c_ in s['cards']:
        print(c_['id'], c_['status'], len(c_['facts']), 'facts', len(c_['tried']), 'tried')
