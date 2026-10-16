#!/usr/bin/env python3
"""S81 die-context STA kit (CLAUDE S81-RERUN 2026-10-07, coordinator audit: no S81 die had post-route die STA).

From a die variant (tools/dsrom_s81_fulldie.py options) writes, for SS and FF:
  * the liberty set: every CLOSED view lib in the tree (station / cfifo / ROM / ... *_ss.lib / *_ff.lib whose cell name
    is a die master), and an INTERIM pin-registered lib for every other master (generator glue, slabs, real macros
    without a lib): each data input a setup / hold arc to the master's clock pin, each output a clk->q arc; areas from
    the floorplan.  Interim constants (SS / FF): clk->q 90 / 32, setup 30 / 10, hold 15 / 15 ps (budget sheet).
  * sta_<corner>.tcl: read libs + die.v (+ SPEF when given), ideal clocks on the die clock sources (collective PLL
    pins, column roots), signoff uncertainty + the inter-region die budget (setup 60 + 150, hold 25 + 50), and report
    the worst paths per (start master, end master) class.  Forwarded-clock lanes have no clock in this model (station
    views carry them: unconstrained here, reported as such).
  die_sta.py kit --s81-opts "<opts>" --die layer --out DIR
"""
import argparse, hashlib, json, math, re, shlex, sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
# --gen-root: import the die generator from another checkout (the source the die case / GRT SPEF was built from), so a
# kit refreshed with newer views keeps the netlist of the routed case
_g = next((sys.argv[i + 1] for i, x in enumerate(sys.argv[:-1]) if x == '--gen-root'), None)
sys.path.insert(0, str(Path(_g) / 'tools' if _g else ROOT / 'tools'))
import dsrom_s81_fulldie as S  # noqa: E402

CLK_NAMES = ('ck', 'clk', 'sk', 'cks', 'ckh', 'cw', 'wclk', 'fi0', 'fi', 'xf', 'ck_in')
# s81-die 2026-10-13 (c6p STA by path class, results/physical/die_iter_1012/s81/c6p_sta_classes_1013): FF cq 32 ps against
# hold 15 + die hold uncertainty 50 made EVERY short placeholder hop a hold violation (1,010,469 endpoints at >= -33.3 ps).
# A pin-registered tile owes the contract minimum clk -> pin of 65 ps at FF (the relay kits build it: outhold
# BUF-HB4-BUF); the placeholder carries that minimum, so a hop between placeholders is neutral (0 at zero wire) and a
# placeholder launching into a REAL pin is judged against the real pin's hold with the contract launch.
K = dict(ss=dict(cq=90.0, su=30.0, ho=15.0), tt=dict(cq=55.0, su=18.0, ho=15.0), ff=dict(cq=65.0, su=10.0, ho=15.0))
# s81-die-iter 2026-10-12 (FF hold, r4f SPEF: hco_SW -> xsco_SW -103.7, hr_W<n> -> f_hr_W<n>_o_1 -77.9, hl_W<n> ->
# g_hl_W<n>_o_sp_collective_0 -77.6 ps): a closed end block (m2l / r2l / l2r, kind 'hend') is balanced on its MEAN clock
# insertion, but its boundary output flops ride a shorter branch (~80 vs 152 ps), so its outputs launch ~70 ps early
# into the glue stage placed beside it (a few um of wire, no wire delay to absorb it).  Receiver hold pad (the Qwen
# 'relay-input pads' pattern, tools/hbm_die_relay_sta.py): every interim glue stage whose data input is driven by a
# closed hend within PAD_NEAR_UM carries a delay chain between that input pin and its capture register, sized at FF
# (HOLD_PAD_FF) and costing PAD_SCALE x at TT / SS (ASAP7 BUF chains).  The padded instances bind a '<master>__hp' cell
# (same ports; the pad lives inside the stage).  REL_CLK: a multi-clock glue master's data input timed against the
# clock that captures it (the SEL_XSTG input register `ir` is clocked by cw, the end block's side -- not ck).
PAD_SCALE = dict(ff=1.0, tt=1.4, ss=1.9)
HOLD_PAD_FF = 120.0
PAD_NEAR_UM = 100.0
PAD_SUFFIX = '__hp'
REL_CLK = {'dsfd_xstg': {'i': 'cw'}}
# s81-die 2026-10-13: the --cfifo-colck column FIFO is a TWO-domain master (lane write side on xf, column side on cr = its
# column tree's return; ck only passes to co).  The single-clock placeholder timed its column side on the trunk ck and
# the clock return cr as data: all of c6p's TT -1,426.8 ps (co -> cr 111 ep, relay -> st / ri 8,960 ep) and the 72,192 FF
# endpoints at -519..-577 ps (xa / xb / cc launched 548 ps before the column relays' clock).  Inputs AND outputs of a
# multi-clock glue master are related to the clock that captures / launches them (REL_CLK_COLCK applies with --cfifo-colck).
REL_CLK_COLCK = {'dsfd_cfifo': dict(xd='xf', st='cr', ri='cr', xa='cr', xb='cr', cc='cr', rs='cr', rd='cr', rf='cr')}


def hold_pad_sites(m):
    """{load inst: set(data ports)} of the interim glue inputs a closed end block drives from <= PAD_NEAR_UM away"""
    by = {it.name: it for it in m['insts']}
    gap = lambda p, q: max(0.0, max(p.x, q.x) - min(p.x + p.w, q.x + q.w)) + max(0.0, max(p.y, q.y) - min(p.y + p.h, q.y + q.h))
    out = defaultdict(set)
    for bid, cls, bits, eps in m['buses']:
        d = by.get(eps[0][0]) if eps else None
        if d is None or d.kind != 'hend':
            continue
        for inst, port in eps[1:]:
            l_ = by.get(inst)
            if l_ is not None and l_.kind != 'hend' and S.is_glue(l_.master) and gap(d, l_) <= PAD_NEAR_UM:
                out[inst].add(port)
    return out
# owner option B (2026-10-07): die setup at TT, hold at FF, SS as sensitivity.  TT planned clock arrival = mean of the
# CTS-validated SS and FF insertions (the plan's CTS ran SS / FF libraries only): an estimate, marked in kit.json


# S81-PH partitions (tools/budgets/tiles.py): a die slab master hardened as tiles.  A slab with every tile closed has an
# assembled view (physical/s81_ph_views/assembled/<slab>, tools/s81/assemble_views.py: tile ETM arcs on the slab die
# ports + the inter-tile glue check); the others stay one interim master and the index reports their closed tiles.
PARTS = dict(dsfd_bk_selector=('dsfd_selt_q', 'dsfd_selt_c'), dsfd_bk_collector=('dsfd_colt_lane', 'dsfd_colt_mrg'),
             dsfd_sp_capture=('dsfd_capt_x', 'dsfd_capt_g2', 'dsfd_capt_ctl'),
             dsfd_sp_collective=('dsfd_coll_lane_w', 'dsfd_coll_core', 'dsfd_coll_ck'),
             dsfd_ctrl=('dsfd_ctrl_pc', 'dsfd_ctrl_ctr'),
             dsfd_svc=('dsfd_svc_pc', 'dsfd_svc_stn', 'dsfd_svcio_ad', 'dsfd_svcio_od', 'dsfd_svcio_q', 'dsfd_svcio_x'),
             dsfd_sp_vm=('dsfd_vm_bg',), dsfd_sp_gather=('ot_s81ph_root_tile', 'ot_s81ph_root_blk'),
             # layer1e Engram service (s81-gen 2026-10-09): lookup + sink hardened separately (prefetch SRAM macros)
             dsfd_engram=('dsfd_engram_lkp', 'dsfd_engram_sink'),
             # --wfc-hard slab (s81-gen 2026-10-09): SOURCE HARD ot_dsrom_wfc_tokpipe_src CLOSED (910e67c7b; record has no
             # exported LEF / Liberty yet -> counted open by the lib index), HARD tok, link (lnk_b record, cell dsfd_wfc_lnk)
             dsfd_wfc=('ot_dsrom_wfc_tokpipe_src', 'dsfd_wfc_tok_hard', 'dsfd_wfc_lnk'))


def _rank(p, root, label):
    """lib preference when several files define one cell: this die variant's closed records, then S81-PH closed tiles,
    then other S81 die view records, then anything else (newest first within a rank)"""
    r = str(p.relative_to(root))
    k = (0 if r.startswith(f'physical/s81_die_views/views/{label}/') else 1 if r.startswith(('physical/s81_ph_views/closed/',
                                                                                        'physical/s81_ph_views/assembled/'))
         else 2 if r.startswith('physical/s81_die_views/views/') else 3)
    return (k, -p.stat().st_mtime)


def closed_libs(corner, root=ROOT, label='m221pq'):
    """cell -> (lib path, kind): kind 'closed' when the lib sits in a closure-loop record dir (corner_sta.json beside it),
    'assembled' for an S81-PH slab assembled from its closed tile ETMs (tools/s81/assemble_views.py, assembled.json beside
    it), else 'macro' (memory / PHY / hard IP liberty)"""
    out = {}
    for p in sorted((root / 'physical').rglob(f'*_{corner}.lib'), key=lambda q: _rank(q, root, label)):
        t = p.read_text(errors='ignore')[:200000]
        for c in re.findall(r'^\s*cell\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)', t, re.M):
            out.setdefault(c, (p, 'assembled' if (p.parent / 'assembled.json').exists() else
                               'closed' if (p.parent / 'corner_sta.json').exists() else 'macro'))
    return out



COLL_CR_PARTS = ('dsfd_coll_lane_w', 'dsfd_coll_cb', 'dsfd_coll_ce', 'dsfd_coll_ct')


def collective_credit_binding(root):
    """Select source-pinned credit masters; same-named legacy libraries cannot satisfy this variant."""
    root = Path(root)
    manifest_path = root / 'physical/s81_ph_views/collective/composition_split3cr.json'
    manifest = json.loads(manifest_path.read_text())
    bindings, problems = {}, []
    receipts = sorted((root / 'results/closure_loop').glob('*/verdict.json'))
    overrides = manifest.get('per_master_source_commits', {})
    invalid_mapping = False
    if not isinstance(overrides, dict) or set(overrides) - set(COLL_CR_PARTS):
        overrides = {}
        invalid_mapping = True
        problems.append('collective: invalid per-master source mapping')
    for master in COLL_CR_PARTS:
        expected = overrides.get(master, manifest['source_commits']['lane' if master == 'dsfd_coll_lane_w' else 'core'])
        if invalid_mapping or not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{9,40}', expected):
            problems.append(f'{master}: invalid source pin')
            continue
        params = manifest['required_parameters'][master]
        for vp in receipts:
            v = json.loads(vp.read_text())
            if v.get('block') != master or not str(v.get('source_commit', '')).startswith(expected):
                continue
            metrics, benches = v.get('metrics', {}), v.get('benches', {})
            def nonnegative(value):
                return type(value) in (int, float) and math.isfinite(value) and value >= 0
            if (v.get('status') != 'CLOSED' or not nonnegative(metrics.get('ss_ps'))
                    or not nonnegative(metrics.get('ff_ps')) or metrics.get('drc') != 0
                    or metrics.get('drc_skipped') or not benches
                    or not all(b.get('ok') is True for b in benches.values())
                    or not any(b.get('expect') == 'pass' for b in benches.values())
                    or sum(b.get('expect') == 'fail' for b in benches.values()) < 2):
                continue
            route = v.get('job_spec', {}).get('stages', {}).get('route', {}).get('cmd', '')
            if not all(re.search(r'--param\s+' + re.escape(k) + r'=' + str(val) + r'(?:\s|$)', route)
                       for k, val in params.items() if k != 'LR' or val != 0):
                continue
            if re.search(r'--param\s+LR=(?!0(?:\s|$))', route):
                continue
            for record in v.get('job_spec', {}).get('record', []):
                directory = root / record['to']
                libs = {c: directory / f'{master}_{c}.lib' for c in ('ss', 'tt', 'ff')}
                if not all(lp.is_file() for lp in libs.values()):
                    continue
                check = directory / 'check.json'
                if not check.is_file() or json.loads(check.read_text()).get('verdict') != 'MATCH':
                    continue
                bindings[master] = dict(verdict=str(vp.relative_to(root)), source_commit=v['source_commit'],
                                        libs={c: str(lp.relative_to(root)) for c, lp in libs.items()})
                break
            if master in bindings:
                break
        if master not in bindings:
            problems.append(f'{master}: missing CLOSED source-pinned CR/LCR routed views and exact/negative gates')
    clock = root / 'physical/s81_ph_views/closed/dsfd_coll_ck'
    cv = clock / 'verdict.json'
    clock_binding = None
    if cv.is_file():
        v = json.loads(cv.read_text())
        libs = {c: clock / f'dsfd_coll_ck_{c}.lib' for c in ('ss', 'tt', 'ff')}
        if (str(v.get('verdict', '')).startswith('CLOSED')
                and v.get('commit') == '752a48488384dbe9c95a72c084bc24e0ac800a17'
                and type(v.get('ss_ps')) in (int, float) and v['ss_ps'] >= 0
                and type(v.get('ff_ps')) in (int, float) and v['ff_ps'] >= 0
                and v.get('drc') == 0 and all(lp.is_file() for lp in libs.values())):
            clock_binding = dict(verdict=str(cv.relative_to(root)), source_commit=v['commit'],
                                 libs={c: str(lp.relative_to(root)) for c, lp in libs.items()})
    if clock_binding is None:
        problems.append('dsfd_coll_ck: missing source-pinned retained clock/reset tile')
    return dict(variant='split3cr', tiles=list(COLL_CR_PARTS) + ['dsfd_coll_ck'], tile_bindings=bindings, clock_binding=clock_binding,
                qualified=False, qualification='UNQUALIFIED: assembled slab and inter-tile glue gate required',
                problems=problems, assembly_by_corner={})



def credit_qualification_valid(root, qualification, binding):
    """Measured qualification must exist and match the exact source-pinned assembly, not just a PASS label."""
    try:
        path = Path(root) / qualification['evidence']
        data = path.read_bytes()
        if qualification.get('status') != 'PASS' or hashlib.sha256(data).hexdigest() != qualification.get('sha256'):
            return False
        q = json.loads(data)
        manifest = json.loads((Path(root) / 'physical/s81_ph_views/collective/composition_split3cr.json').read_text())
        if (q.get('status') != 'PASS' or q.get('variant') != 'split3cr'
                or q.get('tile_bindings') != binding['tile_bindings'] or q.get('clock_binding') != binding['clock_binding']
                or q.get('clock_period_ps') != 833.333 or q.get('setup_uncertainty_ps') != 60
                or q.get('hold_uncertainty_ps') != 25 or q.get('drc') != 0
                or q.get('clock_sinks') != [r['inst'] + '/ck' for r in manifest['instances']]
                or not all(type(q.get(k)) in (int, float) and math.isfinite(q[k]) and q[k] >= 0
                           for k in ('tt_setup_ps', 'ff_hold_ps'))):
            return False
        sinks = [r['inst'] for r in manifest['instances']]
        taps = q.get('clock_taps', {})
        clock_root = q.get('clock_root', {})
        if (q.get('source_latency_policy') != 'option1' or set(taps) != set(sinks)
                or clock_root.get('instance') != 'u_ck'
                or not all(type(clock_root.get(k)) in (int, float) and math.isfinite(clock_root[k]) for k in ('x_um', 'y_um'))
                or not all(type(taps[n].get(k)) in (int, float) and math.isfinite(taps[n][k]) and taps[n][k] >= 0
                           for n in sinks for k in ('tt_source_latency_ps', 'ff_source_latency_ps'))):
            return False
        corner = json.loads((Path(root) / q['corner_sta']).read_text())
        for key, metric in (('setup_tt', 'tt_setup_ps'), ('hold_ff', 'ff_hold_ps')):
            r = corner[key]
            if r.get('errors') or r.get('worst_slack_ps') != q[metric]:
                return False
            if not all(re.fullmatch('[0-9a-f]{64}', str(r.get(k, ''))) for k in
                       ('odb_sha256', 'spef_sha256', 'sdc_sha256')):
                return False
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False

def credit_assembled_views(root, binding, candidates):
    """Accept only a CR assembly explicitly bound to the selected four committed closure receipts."""
    if binding['problems']:
        return
    assemblies = sorted((Path(root) / 'physical').rglob('assembled.json'))
    for corner, index in candidates.items():
        rejected = []
        for path in assemblies:
            assembly = json.loads(path.read_text())
            if assembly.get('slab') != 'dsfd_sp_collective':
                continue
            if assembly.get('variant') != 'split3cr' or assembly.get('tile_bindings') != binding['tile_bindings'] or assembly.get('clock_binding') != binding['clock_binding']:
                rejected.append(f'rejected legacy or mismatched assembly {path}')
                continue
            glue = assembly.get('glue_worst_ps', {})
            if not all(type(glue.get(k)) in (int, float) and math.isfinite(glue[k]) and glue[k] >= 0
                       for k in ('tt_setup_bal', 'ff_hold_bal')):
                rejected.append(f'unqualified inter-tile glue {path}')
                continue
            qualification = assembly.get('physical_qualification', {})
            if not credit_qualification_valid(root, qualification, binding):
                rejected.append(f'missing measured glue/clock qualification {path}')
                continue
            used = assembly.get('corners', {}).get(corner, {}).get('libs', {})
            expected = {m: r['libs'][corner] for m, r in binding['tile_bindings'].items()}
            expected['dsfd_coll_ck'] = binding['clock_binding']['libs'][corner]
            lp = path.parent / f'dsfd_sp_collective_{corner}.lib'
            if used != expected or not lp.is_file():
                rejected.append(f'missing or mismatched tile library provenance {path}')
                continue
            binding['assembly_by_corner'][corner] = str(lp.relative_to(root))
            index['dsfd_sp_collective'] = (lp, 'assembled')
            break
        else:
            binding['problems'].append(f'{corner}: missing qualified split3cr assembled slab; ' + '; '.join(rejected))
    binding['qualified'] = not binding['problems'] and len(binding['assembly_by_corner']) == 3
    if binding['qualified']:
        binding['qualification'] = 'source-pinned split3cr assembled timing and glue; die context still required'


def measured_insertion(path):
    """block -> {ss, ff, tt} routed clock insertion (ps) from the closure loop's measured_insertion.json; a corner whose
    routed measurement is on another clock than the block's falls back to the calibrate CTS-only value; tt missing ->
    mean(ss, ff)"""
    if not path or not Path(path).exists():
        return {}
    out = {}
    for b, r in json.loads(Path(path).read_text())['blocks'].items():
        v = {}
        for c in ('ss', 'ff', 'tt'):
            x = r.get(c)
            if x and x.get('clock', r.get('clock')) == r.get('clock') and 'mean' in x:
                v[c] = float(x['mean'])
            elif (r.get('calibrate') or {}).get(c):
                v[c] = float(r['calibrate'][c]['mean'])
        if 'ss' in v and 'ff' in v:
            v.setdefault('tt', (v['ss'] + v['ff']) / 2)
            out[b] = v
    return out


def arcs_insertion(mst, view, mi, libpath=None, parts=None):
    """[ss, ff, tt] clock insertion carried INSIDE a view's arcs (closed: its routed measurement, else the calib.json
    boundary mean beside the lib; assembled: mean over its tiles); interim / partitioned / macro carry none"""
    if view == 'closed':
        # DIE CLOCK DELIVERY RULE (owner 2026-10-13, el1013-pinreg-audit.log): R = the routed view's insertion.json
        # <corner>.boundary.mean = the sign-off reference (io_ref_routed.sdc); it outranks measured_insertion.json (keyed
        # by block name, may be another route of the block) and the calibrate value.
        ij = libpath and Path(libpath).parent / 'insertion.json'
        if ij and ij.exists():
            j = json.loads(ij.read_text())
            if all((j.get(c) or {}).get('boundary', {}).get('n') for c in ('ss', 'ff')):
                ss, ff = j['ss']['boundary']['mean'], j['ff']['boundary']['mean']
                tt = j['tt']['boundary']['mean'] if (j.get('tt') or {}).get('boundary', {}).get('n') else (ss + ff) / 2
                return [ss, ff, tt]
        cj = libpath and Path(libpath).parent / 'calib.json'
        # ds-1010 2026-10-10: an ALTERNATE view of the block (e.g. views_colck/dsfd_cfifo, bound by --cfifo-colck) carries
        # its own route's insertion, not the default view's routed measurement in measured_insertion.json (keyed by block
        # name).  r4f FF: the colck cfifo was balanced with the plain cfifo's 263 ps while its cr arcs carry ~206 ps, so its
        # read side launched ~57 ps early into the first column relays (cf<c> cr -> y_xa_<c>_0_0, -107 ps).
        alt = libpath and Path(libpath).parent.parent.name != 'views'
        if mst in mi and not (alt and cj and cj.exists()):
            return [mi[mst][c] for c in ('ss', 'ff', 'tt')]
        if cj and cj.exists():
            j = json.loads(cj.read_text())
            ss, ff = j['ss']['boundary']['mean'], j['ff']['boundary']['mean']
            return [ss, ff, (ss + ff) / 2]
    if view == 'assembled':
        src = [x for x in (parts or PARTS).get(mst, ()) if x in mi]
        if src:
            return [sum(mi[x][c] for x in src) / len(src) for c in ('ss', 'ff', 'tt')]
    return [0.0, 0.0, 0.0]


BF_COMPOSE = ROOT / 'results/rtl/s81_bf_arch_20261009/compose/compose.json'


def bf_front_tap(masters, lat, by, root=ROOT, compose=None):
    """ds-1010 2026-10-10 (owner: hierarchical full-rate BF adopted): the BF front's balanced clock tap.  The routed
    front (ot_s81_bf_front) has a shallower tree than its two routed columns (ot_v41_bf_col): mean insertion TT 275.2 vs
    642.7, FF 221.0 vs 513.0 ps (compose.json, from the closed ETMs), so the die tree taps the front LATER than the
    columns by the deficit (TT 367.5 / FF 292.0 = set_clock_latency -source on the front tap, the interior insertion the
    columns spend; design standard for edge / face taps).  Flop arrivals of front and columns are then equal, which is
    what the kit's balanced model already gives: an interim (pin = flop) view keeps planned + D on every pin, a closed
    view gets planned + D - its in-arc insertion (balance_latency), i.e. the front pin lands the deficit after the
    column pins by construction.  Recorded here as the die clock plan's tap target per front clock pin."""
    fronts = sorted(k_ for k_ in lat if by[k_.split('/')[0]].master == 'dsfd_bf_front')
    if not fronts:
        return None
    cp = Path(compose) if compose else root / BF_COMPOSE.relative_to(ROOT)
    if not cp.exists():
        raise FileNotFoundError(f'--bf-hier die without the composed BF record {cp}')
    cj = json.loads(cp.read_text())
    tap = {c: round(cj['corners'][c]['bal_latency']['u_front'], 1) for c in ('tt', 'ff')}
    ins = {c: {b: round((v['min'] + v['max']) / 2, 1) for b, v in cj['corners'][c]['insertion'].items() if b in ('u_front', 'u_col0')}
           for c in ('tt', 'ff')}
    views = {m_: masters.get(m_, {}).get('view', 'interim') for m_ in ('dsfd_bf_front', 'dsfd_bf_col')}
    rec = dict(front_clock_pins=len(fronts), tap_source_latency_ps=tap, block_mean_insertion_ps=ins,
               ss='no SS ETM of the routed BF blocks: the SS tap scales with the column tree (not measured)',
               views=views, record=str(cp),
               basis=('compact die (--bf-hier-compact) timed with the col600 composed tap until the compact blocks close '
                      'and their compose record is passed (--bf-compose)' if getattr(S, 'BF_HIER', None) == 450.144 and not compose
                      else 'composed record of the bound BF blocks'),
               model=('interim BF views (pin = flop): front and column flops already arrive together; the physical tap '
                      'target is the column pin latency + tap_source_latency_ps' if 'interim' in views.values() else
                      'closed BF views: balance_latency delivers the front pin tap_source_latency_ps after its columns'))
    if all(v == 'closed' for v in views.values()):
        col = sorted(k_ for k_ in lat if by[k_.split('/')[0]].master == 'dsfd_bf_col')
        f0 = next(iter(fronts)); c0 = next(k_ for k_ in col if k_.split('/')[0] == f0.split('/')[0] + 'w')
        d = [lat[f0][i] - lat[c0][i] for i in (2, 1)]
        rec['closed_check_ps'] = dict(tt=round(d[0], 1), ff=round(d[1], 1))
    return rec


LEVEL_R_PS = 300.0       # tiles with R <= 300 ps (TT) share one clock level (the owner clock rule's insertion cap)
SKEW_SAME, SKEW_DEEP = 90.0, 150.0
MAX_SPREAD_PS = 80.0


def clock_delivery(lat, pin_master, masters, libs, by, vroot):
    """DIE CLOCK DELIVERY RULE record + the deep-tile uncertainty lines (owner 2026-10-13 09:25; el1013-pinreg-audit.log;
    tools/hier_contract/pinreg_audit.py v2).

      entry   the die delivers the clock at tile X's clock pin at phi - R_X (balance_latency already does this: pin
              latency = planned + D - in-arc insertion); R = insertion.json boundary mean of the BOUND view, else the
              ETM min/max_clock_tree_path midrange (ESTIMATED), else 0 for an interim pin-registered master
      levels  R_tt <= 300: the common level.  R_tt > 300: its own trunk tap, R - 300 earlier; every hop that touches it
              is budgeted at SKEW 150 instead of 90 (OCV 2 x 5 % x R on the non-shared insertion)
      spread  boundary max - min > 80 ps is a TILE defect (inside o + s, not compensatable): listed, never padded

    Returns (record, {corner: tcl}) -- the tcl raises the setup uncertainty by SKEW_DEEP - SKEW_SAME on the clock pins of
    the deep instances (their capture side; the launch side of a deep tile is judged per pair by pinreg_audit --case)."""
    tiles, deep_pins = {}, []
    for pin in sorted(lat):
        mst = pin_master[pin]
        t = tiles.get(mst)
        if t is None:
            r = masters.get(mst, {})
            view = r.get('view', 'interim')
            lp = libs['tt'].get(mst, libs['ss'].get(mst, (None,)))[0] if view != 'interim' else None
            ij = lp and Path(lp).parent / 'insertion.json'
            t = dict(view=view, instances=0, clock_pins=set())
            if ij and ij.exists():
                j = json.loads(ij.read_text())
                b = {c: (j.get(c) or {}).get('boundary') or {} for c in ('ss', 'ff', 'tt')}
                if b['tt'].get('n') or (b['ss'].get('n') and b['ff'].get('n')):
                    tt = b['tt'] if b['tt'].get('n') else dict(mean=(b['ss']['mean'] + b['ff']['mean']) / 2,
                                                              min=(b['ss']['min'] + b['ff']['min']) / 2,
                                                              max=(b['ss']['max'] + b['ff']['max']) / 2)
                    t.update(R_ps={c: round(b[c]['mean'], 1) for c in b if b[c].get('n')}, R_tt_ps=round(tt['mean'], 1),
                             spread_tt_ps=round(tt['max'] - tt['min'], 1), source='insertion.json boundary mean',
                             file=str(ij.relative_to(vroot)) if ij.is_relative_to(vroot) else str(ij))
            if 'R_tt_ps' not in t and view != 'interim':
                pn = pin.split('/')[1]
                v = pin_insertion(mst, pn, libs)
                if v:
                    t.update(R_tt_ps=round(v[2], 1), source='ESTIMATED: ETM min/max_clock_tree_path midrange over all sinks '
                             '(no insertion.json: boundary spread unmeasured; run ck_insertion.py on the view)')
                elif r.get('insertion_in_arcs_ps'):
                    t.update(R_tt_ps=round(r['insertion_in_arcs_ps'][2], 1), source='ESTIMATED: measured_insertion.json / '
                             'calib.json block mean (no insertion.json beside the bound lib)')
            if 'R_tt_ps' not in t and view == 'macro':
                # r5 2026-10-14: a hard memory macro (cfg ROM ot_rom_4096x72_m8) has no clock tree inside its view: every
                # liberty arc (clk -> rd_out, addr/ce setup / hold) is referenced to its clk pin, so R = 0 by construction
                t.update(R_tt_ps=0.0, source='hard macro: liberty arcs referenced to the clock pin (no internal tree), R = 0')
            if 'R_tt_ps' not in t and view == 'partitioned' and lp is None:
                # r5 2026-10-14: a partitioned master without an assembled lib is timed by its interim pin-registered
                # model (pin = flop) like any interim master: R = 0 is exact for that model (not an estimate of a view)
                t.update(R_tt_ps=0.0, source='interim pin-registered model (partitioned, children not assembled): no internal insertion')
            if 'R_tt_ps' not in t:
                t.update(R_tt_ps=0.0, source='interim pin-registered model (pin = flop): no internal insertion' if view == 'interim'
                         else 'UNMEASURED: routed view without insertion.json and without a clock_tree_path on this pin '
                              '(taken as 0: run ck_insertion.py on the view)')
            R = t['R_tt_ps']
            t['level'] = 'common' if R <= LEVEL_R_PS else 'early_tap'
            t['entry_offset_tt_ps'] = round(-R, 1)                       # required clock arrival at the pin relative to phi
            t['tap_before_common_level_ps'] = round(max(0.0, R - LEVEL_R_PS), 1)
            t['hop_skew_ps'] = SKEW_SAME if R <= LEVEL_R_PS else SKEW_DEEP
            t['ocv_on_insertion_ps'] = round(2 * 0.05 * R, 1)
            if t.get('spread_tt_ps', 0.0) > MAX_SPREAD_PS:
                t['defect'] = f"boundary spread {t['spread_tt_ps']} ps > {MAX_SPREAD_PS:.0f} (tile defect, not compensatable)"
            tiles[mst] = t
        t['instances'] += 1
        t['clock_pins'].add(pin.split('/')[1])
        if t['level'] == 'early_tap':
            deep_pins.append(pin)
    for t in tiles.values():
        t['clock_pins'] = sorted(t['clock_pins'])
        t['instances'] = t['instances'] // max(1, len(t['clock_pins']))
    deep = {m_: t for m_, t in tiles.items() if t['level'] == 'early_tap'}
    rec = dict(rule='die clock delivery (owner 2026-10-13): clock at each tile clock pin at phi - R (insertion-compensated '
                    'entry), never a common phase at the pins; R <= 300 ps one level, R > 300 an earlier trunk tap and SKEW '
                    '150 on its hops; hop: o_A + 0.76 ps/um x L + s_B <= 833.3 - 60 - SKEW',
               level_r_ps=LEVEL_R_PS, skew_ps=dict(same_level=SKEW_SAME, deep=SKEW_DEEP),
               hop_budget_ps=dict(same_level=round(833.333 - 60 - SKEW_SAME, 1), deep=round(833.333 - 60 - SKEW_DEEP, 1)),
               masters_common=sum(1 for t in tiles.values() if t['level'] == 'common'), masters_early_tap=len(deep),
               early_tap={m_: dict(R_tt_ps=t['R_tt_ps'], tap_before_common_level_ps=t['tap_before_common_level_ps'],
                                   instances=t['instances'], source=t['source']) for m_, t in sorted(deep.items())},
               estimated_R=sorted(m_ for m_, t in tiles.items() if t['source'].startswith(('ESTIMATED', 'UNMEASURED'))),
               spread_defects={m_: t['defect'] for m_, t in sorted(tiles.items()) if 'defect' in t},
               deep_clock_pins=len(deep_pins), tiles=dict(sorted(tiles.items())),
               sta='setup uncertainty + %.0f ps on the clock pins of the early-tap instances (capture side); launch side '
                   'of a deep tile: pinreg_audit.py --case pair equation at SKEW 150' % (SKEW_DEEP - SKEW_SAME))
    return rec, deep_pins


def co_delay(lib):
    """the cfifo's ck -> co clock pass (rising, smallest load) from its view lib: the column clock root arrives that
    much after the cfifo ck pin (0 when the lib has no co arc, e.g. an interim cfifo)"""
    t = Path(lib).read_text(errors='ignore') if lib and Path(lib).exists() else ''
    m = re.search(r'pin\("?co\[0\]"?\)\s*\{.*?cell_rise\([^)]*\)\s*\{[^}]*?values\("\s*([\d.]+)', t, re.S)
    return float(m.group(1)) if m else 0.0


_TREE_INS = {}


def pin_tree_insertion(lib, pin):
    """{(pin, 'min'|'max'): rise value} from a view lib's min/max_clock_tree_path arcs on clock pin `pin` (the ETM's
    own per-clock-pin insertion), {} when the lib carries none for that pin"""
    key = (str(lib), pin)
    if key not in _TREE_INS:
        t = Path(lib).read_text(errors='ignore') if lib and Path(lib).exists() else ''
        out = {}
        names = [pin] if '[' in pin else [pin,pin+'[0]']
        if pin.endswith('[0]'):
            names.append(pin[:-3])
        body = ''
        for name in names:
            pm = re.search(r'\bpin\s*\(\s*"?%s"?\s*\)\s*\{' % re.escape(name),t)
            if not pm:
                continue
            start,depth = pm.end(),1
            quoted,escaped = False,False
            for end in range(start,len(t)):
                ch=t[end]
                if escaped:
                    escaped=False
                elif ch=='\\' and quoted:
                    escaped=True
                elif ch=='"':
                    quoted=not quoted
                elif not quoted:
                    depth += (ch=='{')-(ch=='}')
                    if depth==0:
                        body=t[start:end]
                        break
            break
        for tm in re.finditer(r'timing_type\s*:\s*(min|max)_clock_tree_path\s*;.*?cell_rise\s*\([^)]*\)\s*\{[^}]*?values\(\s*"\s*([\d.]+)',
                              body, re.S):
            out[tm.group(1)] = float(tm.group(2))
        _TREE_INS[key] = out
    return _TREE_INS[key]


def pin_insertion(mst, pin, libs):
    """s81-die-iter 2026-10-12 (die relay hold FF -107.3, r4f: cf<c> cr -> y_xa_<c>_0_0): a MULTI-CLOCK block (the
    colck cfifo: ck = stream trunk + co pass, cr = its column-side sink of the column tree, xf = the lane write clock)
    has a different insertion behind each clock pin; one master scalar (its routed / calib boundary mean, the ck side:
    206.5 ps FF) put the column relays ~40-80 ps behind the cr-side launch flops.  Balance each such pin with the ETM's
    own min/max_clock_tree_path on that pin: SS (setup corner) max, FF (hold corner) min, TT their mean.  [ss, ff, tt]
    or None (the lib carries no tree path on the pin -> the master scalar, as before)"""
    if not libs:
        return None
    v = []
    for c in ('ss', 'ff', 'tt'):
        lp = libs.get(c, {}).get(mst, (None,))[0]
        d = pin_tree_insertion(lp, pin) if lp else {}
        if not d:
            return None
        v.append(d.get('max', d.get('min')) if c == 'ss' else d.get('min', d.get('max')) if c == 'ff' else
                 (d.get('min', 0.0) + d.get('max', d.get('min', 0.0))) / (2 if 'max' in d and 'min' in d else 1))
    return v


def sta_latency_lines(lat, pin_master, libs, corner, ci):
    """Translate physical clock-pin targets to OpenSTA's ETM-normalized clock reference.

    OpenSTA subtracts min/max_clock_tree_path from ETM I/O timing tables. The physical balance already
    subtracts that insertion from the pin target, so using that target unchanged subtracts it twice.
    Compensate only explicit ETM tree paths, separately for early/late; preserve physical targets in the record.
    """
    lines, correction = [], {}
    for pin, v in sorted(lat.items()):
        mst, port = pin_master[pin], pin.split('/')[1]
        lp = libs[corner].get(mst, (None,))[0]
        tree = pin_tree_insertion(lp, port) if lp else {}
        pins = f'[get_pins -quiet {{{pin} {pin}[0]}}]'
        if tree:
            early = tree.get('min', tree.get('max', 0.0))
            late = tree.get('max', tree.get('min', 0.0))
            lines.extend([f'set_clock_latency -min {v[ci] + early:.6f} {pins}\n',
                          f'set_clock_latency -max {v[ci] + late:.6f} {pins}\n'])
            correction[pin] = dict(physical_pin_ps=v[ci], early_etm_ps=early, late_etm_ps=late)
        else:
            lines.append(f'set_clock_latency {v[ci]:.6f} {pins}\n')
    return ''.join(lines), correction


def balance_latency(lat, pin_master, masters, mi, libs=None, group=None, parts=None):
    """in place: lat[pin] = planned [ss, ff, tt] arrival -> pin latency so that every flop arrives at plan + D
    (D = the deepest in-arc insertion per corner within the pin's clock tree: the trunk, or one column tree, which
    hangs off its cfifo `co` and can only pad below it; group: pin -> tree key, default one tree).  Returns the record."""
    ins = {}
    for k_ in lat:
        mst = pin_master[k_]
        if mst not in ins:
            r = masters.get(mst, {})
            lp = libs and libs['ss'].get(mst, (None,))[0]
            ins[mst] = arcs_insertion(mst, r.get('view', 'interim'), mi, lp, parts)
            if any(ins[mst]):
                r['insertion_in_arcs_ps'] = [round(x, 1) for x in ins[mst]]
            r.pop('insertion_added_ps', None)
    grp = (lambda k_: group.get(k_, 'trunk')) if group else (lambda k_: 'trunk')
    # per-clock-pin insertion: the ETM's own clock_tree_path on that pin (pin_insertion: SS max, FF min, TT mean), else
    # the master scalar.  s81-die-iter 2026-10-12: SINGLE-clock closed views too -- r4f FF, dsfd_m2l_vr_512x1__hco_SW
    # was balanced on its routed boundary MEAN (152 ps FF) while its ETM's min tree path is 123.0, so its launch flops
    # arrived ~29 ps before the plan into the interim xsco_SW relay 2.8 um away (-103.7 ps); multi-clock masters
    # (the colck cfifo) were already balanced per pin.
    pin_ins, per_pin = {}, {}
    for k_ in lat:
        mst, pn = pin_master[k_], k_.split('/')[1]
        if masters.get(mst, {}).get('view', 'interim') != 'interim':
            if (mst, pn) not in per_pin:
                per_pin[(mst, pn)] = pin_insertion(mst, pn, libs)
            if per_pin[(mst, pn)]:
                pin_ins[k_] = per_pin[(mst, pn)]
    vin = lambda k_: pin_ins.get(k_) or ins[pin_master[k_]]
    for (mst, pn), v in sorted(per_pin.items()):
        if v:
            masters.get(mst, {}).setdefault('insertion_per_clock_pin_ps', {})[pn] = [round(x, 1) for x in v]
    D = defaultdict(lambda: [0.0, 0.0, 0.0])
    for k_ in lat:
        g, v = grp(k_), vin(k_)
        D[g] = [max(D[g][i], v[i]) for i in range(3)]
    for k_ in lat:
        v, d = vin(k_), D[grp(k_)]
        lat[k_] = [lat[k_][i] + d[i] - v[i] for i in range(3)]
    return dict(model='balanced: flop arrival = planned sink arrival + D (per clock tree); pin latency = that - in-arc '
                      'insertion; a column clock source = its cfifo ck pin latency',
                pad_ps={g: [round(x, 1) for x in d] for g, d in sorted(D.items()) if any(d)},
                masters_offset=sorted(m for m, v in ins.items() if any(v)), pins=len(lat),
                per_clock_pin={f'{m_}/{p_}': [round(x, 1) for x in v] for (m_, p_), v in sorted(per_pin.items()) if v})


def interim_lib(cells, corner, pads=None):
    pads = pads or {}
    k = K[corner]
    L = [f'library (s81_interim_{corner}) {{', ' delay_model : table_lookup;', ' time_unit : "1ps";',
         ' voltage_unit : "1V";', ' current_unit : "1mA";', ' pulling_resistance_unit : "1kohm";',
         ' leakage_power_unit : "1nW";', ' capacitive_load_unit (1, ff);', ' nom_voltage : 0.7;', ' nom_temperature : 25;',
         ' nom_process : 1;']
    # every port a bus (width 1 too): the die SPEF / odb netlist name 1-bit macro pins 'ck[0]' (LEF bit pins)
    widths = sorted({w for _, _, ports in cells for _, (d, w) in ports.items()})
    for w in widths:
        L.append(f' type (b{w}) {{ base_type : array; data_type : bit; bit_width : {w}; bit_from : {w - 1}; bit_to : 0; '
                 'downto : true; }')
    for name, area, ports in cells:
        assigned = S._assigned_record(name) if hasattr(S, '_assigned_record') else None
        clock_bits = (assigned or {}).get('data_clock_bits', {})
        assigned_clocks = {p.split('[')[0] for pins in (assigned or {}).get('clock_entries', {}).values() for p in pins}
        ck = next((c for c in CLK_NAMES if c in ports and ports[c][0] == 'input'), None)
        rel = dict(next((v_ for m_, v_ in REL_CLK.items() if name.startswith(m_)), {}))
        if getattr(S, 'CFIFO_COLCK', False):
            rel.update(next((v_ for m_, v_ in REL_CLK_COLCK.items() if name.startswith(m_)), {}))
        rel = {p_: c_ for p_, c_ in rel.items() if c_ in ports and ports[c_][0] == 'input'}
        L.append(f' cell ({name}) {{ area : {area:.3f};')
        for p, (d, w) in sorted(ports.items()):
            head = f'  bus ({p}) {{ bus_type : b{w};'
            body = [head, f'   direction : {"input" if d == "input" else "output" if d == "output" else "inout"};']
            if d == 'input':
                body.append('   capacitance : 1.0;')
            if p == ck or (d == 'input' and (p in CLK_NAMES or p in rel.values() or p in assigned_clocks)):
                body.append('   clock : true;')
            elif p in clock_bits:
                assert len(clock_bits[p]) == w, (name, p, 'clock attribution width')
                for bit, rck in enumerate(clock_bits[p]):
                    assert rck.split('[')[0] in assigned_clocks, (name, p, bit, rck)
                    body.append(f'   pin ("{p}[{bit}]") {{')
                    if d == 'input':
                        for tt, v in (('setup_rising', k['su']), ('hold_rising', k['ho'])):
                            body.append(f'    timing () {{ related_pin : "{rck}"; timing_type : {tt}; '
                                        f'rise_constraint (scalar) {{ values ("{v}"); }} fall_constraint (scalar) {{ values ("{v}"); }} }}')
                    elif d == 'output':
                        body.append(f'    timing () {{ related_pin : "{rck}"; timing_type : rising_edge; '
                                    f'cell_rise (scalar) {{ values ("{k["cq"]}"); }} cell_fall (scalar) {{ values ("{k["cq"]}"); }} '
                                    'rise_transition (scalar) { values ("20"); } fall_transition (scalar) { values ("20"); } }')
                    body.append('   }')
            elif ck and d == 'input':
                rck = rel.get(p, ck)
                pps = HOLD_PAD_FF if p in pads.get(name, ()) else 0.0
                for tt, v in (('setup_rising', k['su'] + pps * PAD_SCALE[corner]), ('hold_rising', k['ho'] - pps)):
                    body.append(f'   timing () {{ related_pin : "{rck}"; timing_type : {tt}; '
                                f'rise_constraint (scalar) {{ values ("{v}"); }} fall_constraint (scalar) {{ values ("{v}"); }} }}')
            elif ck and d == 'output':
                body.append(f'   timing () {{ related_pin : "{rel.get(p, ck)}"; timing_type : rising_edge; '
                            f'cell_rise (scalar) {{ values ("{k["cq"]}"); }} cell_fall (scalar) {{ values ("{k["cq"]}"); }} '
                            'rise_transition (scalar) { values ("20"); } fall_transition (scalar) { values ("20"); } }')
            body.append('  }')
            L += body
        L.append(' }')
    L.append('}')
    return '\n'.join(L) + '\n'



def real_view_gate(required_masters, corner_views):
    """Refuse planning cells and cross-corner substitutions for a real-view kit.

    Call after the normal source-qualified binding filter and collective overrides.
    The gate covers the libraries only; physical clocks and complete hardware
    composition remain separate obligations.
    """
    missing = {}
    for master in sorted(required_masters):
        for corner in ('ss', 'tt', 'ff'):
            source = corner_views.get(corner, {}).get(master)
            if source is None:
                missing.setdefault(master, {})[corner] = 'missing_real_corner_view'
            elif source[1] not in ('closed', 'assembled', 'macro'):
                missing.setdefault(master, {})[corner] = 'planning_view_' + str(source[1])
            elif not Path(source[0]).is_file():
                missing.setdefault(master, {})[corner] = 'missing_library_file'
    return dict(schema='opentallas.s81.real_view_gate.v1',
                verdict='FAIL' if missing else 'PASS',
                required_masters=len(set(required_masters)), missing=missing,
                scope='Source-filtered three-corner libraries only; not native die qualification',
                tt_fallback_to_ss=False, interim_libraries_allowed=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['kit'])
    ap.add_argument('--s81-opts', required=True)
    ap.add_argument('--die', default='layer')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--clock-plan', type=Path, help='results/rtl/budgets_20261006/clock_plan/<die>.json.gz: per-sink '
                    'planned SS / FF insertion (sinks not in the plan take the nearest planned sink of the same clock)')
    ap.add_argument('--gen-root', type=Path, help='checkout whose tools/dsrom_s81_fulldie.py builds the die (default: this one)')
    ap.add_argument('--views-root', type=Path, default=ROOT, help='checkout whose physical/ supplies the view libs')
    ap.add_argument('--label', default='m221pq', help='die variant label of physical/s81_die_views/views/<label>/')
    ap.add_argument('--measured', type=Path, default=ROOT / 'results/rtl/budgets_20261006/measured_insertion.json',
                    help='closure-loop routed block clock insertion: the in-arc insertion of closed / assembled views, '
                         'subtracted from their planned pin latency (balanced die tree, balance_latency)')
    ap.add_argument('--require-qualified-collective', action='store_true', help='reject an unqualified opt-in split3CR collective instead of writing an interim planning kit')
    ap.add_argument('--require-real-views', action='store_true',
                    help='refuse missing real SS/TT/FF views before writing timing libraries; no interim cells or SS-as-TT substitution')
    ap.add_argument('--require-view-identity', action='store_true',
                    help='separately require actual source/parameter/hierarchy identity against every bound closing job; not physical qualification')
    ap.add_argument('--variant-recipes', type=Path,
                    help='JSON mapping die master to Git-pinned source recipe; actual die parameters/defines always override this file')
    ap.add_argument('--jobs-root', type=Path, default=Path.home() / '.local/state/closure_loop/jobs')
    ap.add_argument('--identity-yosys', default='yosys')
    ap.add_argument('--planning-hold-pads', action='store_true',
                    help='planning sensitivity only: model unbuilt 120 ps FF receiver delay chains; '
                         'the default kit uses unpadded timing and never treats these chains as physical evidence')
    ap.add_argument('--bf-compose', type=Path, help='composed BF pair record (bf_hier_compose_sta.py compose.json) of the '
                    'die\'s BF blocks: the front clock tap; default the col600 record')
    ap.add_argument('--index-out', type=Path, help='also write the master -> view index (JSON) here')
    ap.add_argument('--legacy-unqualified-libs', action='store_true',
                    help='S81 DIE 2026-10-13: keep the tree-scan binding of routed-view ETMs (closed / assembled) of masters '
                         'that are NOT in the view-binding table (not QUALIFIED by tools/s81/native_view_qualify.py). '
                         'Default: such a master is timed with the interim pin-registered lib and listed under '
                         'unqualified_views_not_bound; only for re-running a kit of an earlier case')
    a = ap.parse_args()
    if a.require_real_views and (a.legacy_unqualified_libs or a.planning_hold_pads):
        ap.error('--require-real-views is incompatible with legacy unqualified libraries or planning hold pads')
    S.apply_options(S.die_options(argparse.ArgumentParser()).parse_args(shlex.split(a.s81_opts) + ['--die', a.die]))
    m = S.build()
    pdir = S.finalize_r8(m)
    a.out.mkdir(parents=True, exist_ok=True)
    first = {}
    for it in m['insts']:
        first.setdefault(it.master, it)
    rp = S.real_ports_r8()
    S.write_netlist(m, 1, a.out / 'die.v')
    rec = dict(masters={}, clocks=[])
    vroot = a.views_root.resolve()
    cls_ = {c: closed_libs(c, vroot, a.label) for c in ('ss', 'tt', 'ff')}
    # S81 DIE 2026-10-13 binding rule: a die master takes a routed-view ETM ONLY through the view-binding table (the
    # generator's --view-binding / OT_S81_VIEW_BINDING, built from qualification.json by tools/s81/view_binding.py); the
    # bound master's three corner libs are the table's (same export as the LEF the die places).  The constant-bound hard
    # macros (S.REAL_FILES: cfg ROM, PHY, SerDes, UCIe, q element -- real LEF by generator constant) are outside the
    # native qualification and keep their liberty by cell name; every master with a GENERATED outline needs the table.
    bound = S.bound_views(vroot) if hasattr(S, 'bound_views') else {}     # --gen-root of an earlier generator: no table
    # OT_S81_VIEW_BINDING_SKIP_MISFIT (S-DIE 10-16): a table master the generator did not bind (misfit) keeps its
    # generated outline, so it must not take the table's liberty either
    bound = {k_: v_ for k_, v_ in bound.items() if k_ not in (m.get('view_binding_misfits') or {})}
    not_bound = {}

    def qualified_only():
        for c_ in ('ss', 'tt', 'ff'):
            for mst in first:
                if mst in bound:
                    cls_[c_][mst] = (S._view_path(bound[mst][c_], vroot), 'closed')
                elif not a.legacy_unqualified_libs and mst in cls_[c_] and mst not in S.REAL_FILES:
                    not_bound.setdefault(mst, {})[c_] = str(cls_[c_].pop(mst)[0].relative_to(vroot))
    S._init_real()
    qualified_only()
    psites = hold_pad_sites(m)
    by_ = {it.name: it for it in m['insts']}
    # a pad lives inside an INTERIM stage: a master with a routed view in any corner carries its own (real) timing
    psites = {i: v for i, v in psites.items() if not any(by_[i].master in cls_[c] for c in cls_)}
    # A Liberty hold offset is not an implemented delay chain. Keep the required sites as a contract request,
    # and change the timing model only when the caller explicitly requests a planning sensitivity.
    required_pad_sites = {i: sorted(p) for i, p in sorted(psites.items())}
    pads = defaultdict(set)                  # padded cell -> padded data ports
    if not a.planning_hold_pads:
        psites = {}
    for inst, ps_ in psites.items():
        pads[by_[inst].master + PAD_SUFFIX] |= ps_
    if psites:
        txt = (a.out / 'die.v').read_text()
        for inst in psites:
            mst = by_[inst].master
            txt, k_ = re.subn(rf'^(\s*){re.escape(mst)} {re.escape(inst)} \(', rf'\g<1>{mst}{PAD_SUFFIX} {inst} (', txt,
                              count=1, flags=re.M)
            assert k_ == 1, ('hold pad: instance not in die.v', inst, mst)
        (a.out / 'die.v').write_text(txt)
    rec['hold_pads'] = dict(ff_ps=HOLD_PAD_FF, scale=PAD_SCALE, near_um=PAD_NEAR_UM, instances=len(psites),
                            planning_only=bool(a.planning_hold_pads), physically_implemented=False,
                            required_sites=required_pad_sites,
                            cells={c: sorted(v) for c, v in sorted(pads.items())},
                            rule='unverified receiver-delay target for interim glue driven by a closed hend within near_um')
    if getattr(S, 'CFIFO_COLCK', False):
        # ds-1010 2026-10-10: --cfifo-colck binds the colck cfifo view (its column side clocked from cr); the kit itself
        # selects it (chains used to sed the lib paths AFTER the kit had balanced the column tree with the plain view)
        for c_ in ('ss', 'tt', 'ff'):
            lp = vroot / f'physical/s81_die_views/views_colck/dsfd_cfifo/dsfd_cfifo_{c_}.lib'
            if lp.exists():
                cls_[c_]['dsfd_cfifo'] = (lp, 'closed')
    parts = dict(PARTS)
    if getattr(S, 'COLL_SPLIT3_CR', False):
        parts['dsfd_sp_collective'] = COLL_CR_PARTS + ('dsfd_coll_ck',)
        binding = collective_credit_binding(vroot)
        credit_assembled_views(vroot, binding, cls_)
        rec['collective_binding'] = binding
        if not binding['qualified']:
            for index in cls_.values():
                index.pop('dsfd_sp_collective', None)
            if a.require_qualified_collective:
                raise ValueError('UNQUALIFIED split3cr collective: ' + '; '.join(binding['problems']))
    qualified_only()                         # the colck / collective overrides above obey the same rule
    rec['view_binding'] = dict(table=getattr(S, 'VIEW_BINDING', None), bound_masters=sorted(m_ for m_ in bound if m_ in first),
                               legacy_unqualified_libs=bool(a.legacy_unqualified_libs),
                               unqualified_views_not_bound=dict(sorted(not_bound.items())))
    if a.require_real_views:
        gate = real_view_gate(first, cls_)
        (a.out / 'real_view_gate.json').write_text(json.dumps(gate, indent=1) + '\n')
        if gate['verdict'] != 'PASS':
            raise ValueError('REAL_VIEW_GATE FAIL: missing source-qualified three-corner views; see real_view_gate.json')
        rec['real_view_gate'] = gate
    if a.require_view_identity:
        from s81 import view_identity as VI
        source_root = Path(S.ROOT).resolve()
        manifest = source_root / 'physical/s81_die_rtl/layer1.f'
        selected, defines, libdirs = [], [], []
        for line in manifest.read_text().splitlines():
            line = line.strip()
            if line.startswith('+define+'):
                defines.extend(d for d in line[len('+define+'):].split('+') if d)
            elif line.startswith('+libdir+'):
                libdirs.append(line[len('+libdir+'):])
            elif line and not line.startswith(('#', '//', '+', '-')):
                selected.append(source_root / line)
        recipes = json.loads(a.variant_recipes.read_text()) if a.variant_recipes else {}
        identity = VI.attest(first, recipes, bound, S.die_master_params(m),
                             source_root=source_root, manifest_sources=selected,
                             manifest_defines=defines, manifest_libdirs=libdirs, jobs_root=a.jobs_root,
                             yosys=a.identity_yosys)
        (a.out / 'view_identity_gate.json').write_text(json.dumps(identity, indent=1) + '\n')
        if identity['verdict'] != 'PASS':
            raise ValueError('VIEW_IDENTITY FAIL: see view_identity_gate.json; library presence is a separate gate')
        rec['view_identity_gate'] = identity
    for corner in ('ss', 'tt', 'ff'):
        cl = cls_[corner]
        cells, libs = [], set()
        for mst, it in sorted(first.items()):
            src = cl.get(mst)
            if not src and corner == 'tt' and mst in cls_['ss']:
                src = cls_['ss'][mst]        # routed view without a TT extraction: its SS liberty (pessimistic, marked)
            if src:
                libs.add(str(src[0]))
                r_ = rec['masters'].setdefault(mst, dict(view=src[1], libs={}))
                if src[1] == 'assembled' and 'glue_worst_ps' not in r_:
                    aj = json.loads((src[0].parent / 'assembled.json').read_text())
                    r_.update(tiles=list(parts.get(mst, ())), glue_worst_ps=aj['glue_worst_ps'],
                              tiles_ss_as_tt=aj['corners']['tt']['tiles_ss_as_tt'])
                r_['libs'][corner] = (str(src[0].relative_to(vroot)) if src[0].is_relative_to(vroot) else str(src[0])) + (' (SS as TT)' if src is not cl.get(mst) else '')
                continue
            if mst in rp:      # real macro without a lib: its die ports, bit names from the real port map
                ports = {}
                for p_, names in rp[mst].items():
                    for n_ in names:
                        mm = re.match(r'^(.*)\[(\d+)\]$', n_)
                        b, i = (mm.group(1), int(mm.group(2)) + 1) if mm else (n_, 1)
                        ports[b] = ('input', max(i, ports.get(b, ('input', 0))[1]))
                d_ = defaultdict(int)
                for bid, cls, bits, eps in m['buses']:
                    if eps[0][0] == it.name:
                        for n_ in rp[mst].get(S.pslice(eps[0][1])[0], []):
                            d_[re.sub(r'\[\d+\]$', '', n_)] = 1
                ports = {b: ('output' if d_.get(b) else 'input', w) for b, (_, w) in ports.items()}
            else:
                ports = dict(pdir.get(mst, {}))
            cells.append((mst, (it.w + S.SHAVE) * (it.h + S.SHAVE), ports))
            if mst + PAD_SUFFIX in pads:
                cells.append((mst + PAD_SUFFIX, (it.w + S.SHAVE) * (it.h + S.SHAVE), ports))
            r_ = dict(view='interim', ports=len(ports))
            if mst in parts:
                if mst == 'dsfd_sp_collective' and 'collective_binding' in rec:
                    done = sorted(rec['collective_binding']['tile_bindings'])
                    if rec['collective_binding']['clock_binding']:
                        done.append('dsfd_coll_ck')
                    r_['qualification'] = rec['collective_binding']['qualification']
                    r_['binding_problems'] = rec['collective_binding']['problems']
                else:
                    done = sorted(x for x in parts[mst] if x in cls_['ss'] and cls_['ss'][x][1] == 'closed')
                r_.update(view='partitioned', tiles=list(parts[mst]), tiles_closed=done)
            rec['masters'][mst] = r_
        (a.out / f'interim_{corner}.lib').write_text(interim_lib(cells, corner, pads))
        (a.out / f'libs_{corner}.txt').write_text('\n'.join(sorted(libs) + [f'/kit/interim_{corner}.lib']) + '\n')
    # clocks: die domain sources (collective PLL pins) and the column roots (cfifo co)
    srcs = []
    for bid, cls, bits, eps in m['buses']:
        if cls == 'clock':
            srcs.append((bid, f'{eps[0][0]}/{eps[0][1]}', dict(clk_stream=833.333, clk_serial=1111.111,
                                                                clk_hbm=1023.96).get(bid, 833.333)))
        elif cls == 'col_clock':
            srcs.append((bid, f'{eps[0][0]}/{eps[0][1]}', 833.333))
    rec['clocks'] = srcs
    lat = {}
    if a.clock_plan:
        import gzip, math
        cp = json.load(gzip.open(a.clock_plan))
        si = cp['sink_insertion']
        by = {it.name: it for it in m['insts']}
        cen = lambda n: (by[n].x + by[n].w / 2, by[n].y + by[n].h / 2)
        known = defaultdict(list)          # clock bus -> [(x, y, ss, ff)]
        sinks = []
        for bid, cls, bits, eps in m['buses']:
            if cls not in ('clock', 'col_clock'):
                continue
            for inst, p_ in eps[1:]:
                if inst not in by:
                    continue
                k_ = f'{inst}/{p_}'
                sinks.append((bid, inst, p_))
                if k_ in si:
                    known[bid].append(cen(inst) + tuple(si[k_]))
        for bid, inst, p_ in sinks:
            k_ = f'{inst}/{p_}'
            pk = f'{inst}/' + rp.get(by[inst].master, {}).get(p_, [p_])[0]   # real macros: the pin of the die port
            if k_ in si:
                lat[pk] = si[k_]
            elif known[bid]:
                x, y = cen(inst)
                nb = min(known[bid], key=lambda q: abs(q[0] - x) + abs(q[1] - y))
                lat[pk] = [nb[2], nb[3]]
        for k_ in list(lat):
            lat[k_] = [lat[k_][0], lat[k_][1], (lat[k_][0] + lat[k_][1]) / 2.0]
        # balanced die tree (s81-die-timing 2026-10-08): every block flop arrives at the PLANNED sink arrival.  The
        #   block sign-off (flow-ioref, io_ref_routed.sdc) references its IO to its OWN mean boundary-register arrival,
        #   so the die tree must deliver each partition clock pin early by the block's internal insertion (CTS macro
        #   pin insertion offsets).  sta_v2/v3 instead ADDED the routed insertion to 24 interim masters only (the q
        #   element +373 ps FF against its abutting interim bank): one-sided skew -> FF -823.8 on 3.0M endpoints.
        mi = measured_insertion(a.measured)
        grp = {}
        for bid, inst, p_ in sinks:
            pk = f'{inst}/' + rp.get(by[inst].master, {}).get(p_, [p_])[0]
            grp[pk] = bid if bid.startswith('ck_col_') else 'trunk'
        bal = balance_latency(lat, {k_: by[k_.split('/')[0]].master for k_ in lat}, rec['masters'], mi, cls_, grp, parts)
        rec['routed_insertion'] = dict(file=str(a.measured), **bal)
        pin_master = {k_: by[k_.split('/')[0]].master for k_ in lat}
        for ci, corner in ((0, 'ss'), (1, 'ff'), (2, 'tt')):
            text, correction = sta_latency_lines(lat, pin_master, cls_, corner, ci)
            (a.out / f'latency_{corner}.tcl').write_text(text)
            rec.setdefault('sta_etm_reference_compensation', {})[corner] = correction
        rec['tt_latency'] = 'estimate: mean of the CTS-validated SS and FF sink insertion'
        rec['clock_delivery'], deep_pins = clock_delivery(lat, pin_master, rec['masters'], cls_, by, vroot)
        (a.out / 'clock_delivery.json').write_text(json.dumps(rec['clock_delivery'], indent=1) + '\n')
        (a.out / 'deep_uncertainty.tcl').write_text(''.join(
            'set_clock_uncertainty -setup %.1f [get_pins -quiet {%s %s[0]}]\n' % (85.0 + SKEW_DEEP - SKEW_SAME, p_, p_)
            for p_ in deep_pins))
        tap = bf_front_tap(rec['masters'], lat, by, a.views_root.resolve(), a.bf_compose)
        if tap:
            rec['bf_front_tap'] = tap
        rec['clock_plan'] = dict(file=str(a.clock_plan), sinks=len(sinks), planned=sum(1 for s in sinks if f'{s[1]}/{s[2]}' in si),
                                 nearest=len(lat) - sum(1 for s in sinks if f'{s[1]}/{s[2]}' in si))
    # with the CTS plan: setup 60 + 25 plan tolerance, hold 25 + 25 plan tolerance (rule H1: the die-link hold term
    # (+50) is not counted at the die, the receiver block signs off its input min at L; was 75)
    for corner, (us, uh) in ((('ss', (85.0, 50.0)), ('tt', (85.0, 50.0)), ('ff', (85.0, 50.0))) if lat else
                             (('ss', (210.0, 75.0)), ('tt', (210.0, 75.0)), ('ff', (210.0, 75.0)))):
        T = ['set libs [split [string trim [read [open /kit/libs_%s.txt]]] "\\n"]' % corner,
             'foreach l $libs { read_liberty $l }', 'read_verilog /kit/die.v', 'link_design dsfd_die',
             'if {[file exists /kit/die.spef]} { read_spef /kit/die.spef; puts OT_SPEF }']
        for n_, pin, per in srcs:
            T.append(f'create_clock -name {n_} -period {per} [get_pins -quiet {{{pin} {pin}[0]}}]')
        if lat:   # planned per-sink insertion (the die tree's skew); uncertainty = signoff 60 + 25 plan tolerance
            T.append(f'source /kit/latency_{corner}.tcl')
            # a column clock is the stream trunk passed through its cfifo root: source latency = the trunk insertion
            # at that cfifo's ck pin (the plan's column-sink values are relative to the column root)
            ci = dict(ss=0, ff=1, tt=2)[corner]
            for n_, pin, per in srcs:
                if n_.startswith('ck_col_'):
                    root = pin.split('/')[0] + '/ck[0]' if pin.split('/')[0] + '/ck[0]' in lat else pin.split('/')[0] + '/ck'
                    if root in lat:      # balanced cfifo pin latency + its ck -> co pass (the column tree hangs off co)
                        cf_ = by[pin.split('/')[0]].master
                        cod = co_delay(cls_[corner][cf_][0] if cf_ in cls_[corner] else None)
                        rec.setdefault('column_root_co_ps', {})[corner] = round(cod, 1)
                        T.append(f'set_clock_latency -source {lat[root][ci] + cod:.1f} [get_clocks {n_}]')
        T += [f'set_clock_uncertainty -setup {us} [all_clocks]', f'set_clock_uncertainty -hold {uh} [all_clocks]',
              'if {[file exists /kit/deep_uncertainty.tcl]} { source /kit/deep_uncertainty.tcl }' if lat else '',
              'set_clock_groups -asynchronous -group {clk_serial} -group {clk_hbm} -group [get_clocks -quiet {clk_stream ck_col_*}]',
              'set_false_path -through [get_nets -quiet {n_rst_* n_rs_col_* por_n}]',
              f'report_checks -path_delay {"min" if corner == "ff" else "max"} -group_path_count 200 -endpoint_path_count 1 '
              f'-fields {{fanout}} -digits 1 > /kit/paths_{corner}.rpt',
              f'report_checks -path_delay {"min" if corner == "ff" else "max"} -group_path_count 100000 '
              f'-endpoint_path_count 1 -format end -digits 1 > /kit/end_{corner}.rpt',
              f'report_worst_slack -{"min" if corner == "ff" else "max"} -digits 1',
              f'report_tns -{"min" if corner == "ff" else "max"} -digits 1',
              f'report_check_types -violators -max_slew -max_capacitance > /kit/drv_{corner}.rpt']
        (a.out / f'sta_{corner}.tcl').write_text('\n'.join(t for t in T if t) + '\n')
    n = defaultdict(int)
    for v in rec['masters'].values():
        n[v['view']] += 1
    rec['counts'] = dict(n)
    rec['views_root'] = str(vroot)
    (a.out / 'kit.json').write_text(json.dumps(rec, indent=1) + '\n')
    if a.index_out:
        cnt = defaultdict(int)
        for it in m['insts']:
            cnt[it.master] += 1
        idx = dict(schema='opentallas.s81.die_view_index.v1', die=a.die, label=a.label, s81_opts=a.s81_opts,
                   counts=dict(n), instances={k: sum(cnt[m_] for m_, v in rec['masters'].items() if v['view'] == k) for k in n},
                   masters={k: dict(v, instances=cnt[k]) for k, v in sorted(rec['masters'].items())},
                   routed_insertion=rec.get('routed_insertion'), collective_binding=rec.get('collective_binding'),
                   view_binding=rec.get('view_binding'))
        a.index_out.parent.mkdir(parents=True, exist_ok=True)
        a.index_out.write_text(json.dumps(idx, indent=1) + '\n')
    print(json.dumps(dict(n), indent=0), len(srcs), 'clock sources')


if __name__ == '__main__':
    main()
