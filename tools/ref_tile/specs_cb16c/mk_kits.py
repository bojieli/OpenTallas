#!/usr/bin/env python3
"""CB16c-COLL 10-22: kit specs of the regional-split collective face sub-tiles.

  qfd_cb16c_es182 / qfd_cb16c_es199   edge register slices (one flop per bit, d W -> q E, ck N; hardened once, x6 each)
  qfd_cb16c_s0_body / qfd_cb16c_p_body the face bodies (12 roots, 6 SRAMs): the S0 / P regional7/5 kit geometry, with
                                        the body pins CLUSTERED in the window of the band that owns them (so every root's
                                        pin flops are local) and the E band moved in by the 43.2-um slice columns.
Writes physical/ref_tile/<kit>/spec.json (+ hand hooks); run tools/ref_tile/ref_tile.py gen on each afterwards.
"""
import copy, json, pathlib, re, sys
WT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
RT = WT / 'physical/ref_tile'
CX = 'rtl/physical/qwen_coll_cb16c_1022/qfd_coll_face_cx.sv'
BODY = 'rtl/physical/qwen_coll_cb16c_1022/qfd_coll_face_cx_body.sv'
OWNER = {'owner': 'Claude:CB16c-COLL', 'branch': 'claude/cb16c-coll-1022'}
V5 = '/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator'
W_BODY, H = 864.0, 907.2          # face 907.2 square = 21.6 slice column + 864 body + 21.6 slice column (slices abut the body)


def bench(prof, mut, expect, wit):
    b = {'name': f'cb16c_lockstep_{prof}_m{mut}', 'expect': expect, 'threads': 8, 'peak_ram_gb': 32, 'needs': ['verilator'],
         'cmd': f'VERILATOR={V5} bash rtl/test/run_cb16c_coll_face_cx.sh {{RUN}}/{prof}_m{mut} {prof} {mut}'}
    if expect == 'pass':
        b.update(pass_regex=f'^CB16C_COLL_BENCH PASS MUT=0 PROFILE={prof}$', pass_witness=wit)
    else:
        b.update(fail_regex=f'^CB16C_COLL_BENCH FAIL MUT={mut} PROFILE={prof}$', fail_witness=wit)
    return b


def lint(top, srcs, defs=''):
    return {'name': 'lint', 'expect': 'pass', 'threads': 1, 'peak_ram_gb': 4, 'needs': ['verilator'],
            'cmd': ("mkdir -p {RUN} && printf '%s\\n' 'module ot_lint_top; " + top + " u_top (); endmodule' > {RUN}/ot_lint_top.sv && "
                    "verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-MODMISSING -DSYNTHESIS "
                    + defs + " --top-module ot_lint_top {RUN}/ot_lint_top.sv " + ' '.join(srcs) + ' && echo lint-ok')}


WIT = 'results/rtl/cb16c_coll_1022'
# measured per-band source-owned sequential counts of each body netlist (None = the S0 face's counts, first gate reports)
COUNTS = {'s0': {'codec': 3920, 'phy': 1426, 'cal': 715, 'lcal': 720, 'tx': 1565, 'rx': 1018},
          'p': {'codec': 3920, 'phy': 1426, 'cal': 166, 'lcal': 167, 'tx': 1565, 'rx': 1018},
          # CB16c-COLL2-SR: R body (FW 514) measured by its first gate (75579d191, ot-pve1); bank3 holds the top 514-b bits
          's1': {'codec': 3920, 'phy': 1426, 'cal': 715, 'lcal': 695, 'tx': 1565, 'rx': 1018},   # first gate 75579d191
          's2': {'codec': 3920, 'phy': 1426, 'cal': 696, 'lcal': 709, 'tx': 1565, 'rx': 1018},   # first gate 75579d191
          'r': {'codec': 3715, 'phy': 1349, 'cal': 166, 'lcal': 167, 'tx': 1501, 'rx': 986, 'bank3': 454}}


# CB16c-COLL2-SR: R-face masters (514 = 2 x 257 W, 565 = 5 x 113 E): outline height / pin span per width, bench profile
SLICE_H = {257: (145.8, [2.16, 143.64], 'r'), 113: (86.4, [2.16, 84.24], 'r')}


def slice_spec(w):
    if w in SLICE_H:
        s = slice_spec(182)
        h, pr, prof = SLICE_H[w]
        top = f'qfd_coll_eslice{w}'
        s = json.loads(json.dumps(s).replace('qfd_coll_eslice182', top).replace('qfd_cb16c_es182', f'qfd_cb16c_es{w}'))
        s['outline'] = {'w': 21.6, 'h': h}
        s['pin_ranges'] = {'d': pr, 'q': pr}
        s['structural_change'] = (f'CB16c-COLL2-SR 10-22: collective face edge register slice {top} ({w} b, one stage d->q, ck N) '
                                  'for the R face (FW 514 / PW 565) of qfd_coll_face_r_cx: W tx_data / rx_data 2 x 257 b on '
                                  'cal_ck_t0..1 / rx_rck_r0..1; E phy_tx / phy_rx 5 x 113 b on codec0p_t0..4 / codec0p_r0..4; hardened '
                                  f'once. Outline 21.6 x {h} ({pr[1]-pr[0]:.2f} um of pins, <= 146 um of bus); recipe 4 flop-first, '
                                  'hold_budget die; same recipe as es182/es199.')
        s['job'] = dict(OWNER, branch='claude/cb16c-sr-1022', tag=f'es{w}',
                        purpose=f'CB16c-COLL2-SR: R-face edge slice {top} (ALT regional split of the COLLIO faces)',
                        benches=[lint(top, [CX]), bench(prof, 0, 'pass', f'{WIT}/{prof}_m0.log')])
        return s
    name = f'qfd_cb16c_es{w}'
    top = f'qfd_coll_eslice{w}'
    return {
        'name': name, 'top': top, 'kind': 'tile', 'sources': [CX], 'params': {}, 'clock_port': 'ck', 'reset_ports': [],
        'macros': [], 'outline': {'w': 21.6, 'h': 145.8}, 'pins': {'N': ['ck'], 'W': ['d'], 'E': ['q']},
        'pin_ranges': {'d': [2.16, 143.64], 'q': [2.16, 143.64]},
        'recipe': 4, 'hold_budget': 'die', 'inhold': False, 'outhold': False,
        'io_flop_at_pins': {'cols': 4, 'allow_none': True}, 'keep_pin_regs': True,
        'pin_regs': {'enable': False, 'reason': 'CB16c-COLL: this slice IS one flip-flop per bit between its d and q pins (the face pin '
                     'register moved out of the body); a flow pin register would add a second stage the face calendar does not price'},
        'route': {'pd': 0.45, 'threads': 4, 'peak_ram_gb': 8, 'pin_h': 'M4', 'pin_v': 'M3 M5', 'm5_pg_pitch': 2.7,
                  'hold_margin_ns': 0.03, 'io_hold_margin_ns': 0.0, 'macro_halo_um': 5.4, 'pin_balance': {'group_max': 1}},
        'structural_change': (f'CB16c-COLL 10-22: collective face edge register slice {top} ({w} b, one stage d->q, ck N), the regional '
                              'sub-tile of qfd_coll_face_cx: 6 instances per face on their own clock entries (W tx_data / rx_data: '
                              '182 b on cal_ck_t* / rx_rck_r*; E phy_tx / phy_rx: 199 b on codec0p_t* / codec0p_r*), hardened once. '
                              'Outline = one third of the face bus (145.8 um of pins at the face pin pitch); recipe 4 flop-first, '
                              'hold_budget die.'),
        'job': dict(OWNER, tag=f'es{w}', purpose=f'CB16c-COLL: collective face edge slice {top} (ALT regional split of the COLLIO faces)',
                    benches=[lint(top, [CX]), bench('s0', 0, 'pass', f'{WIT}/s0_m0.log')]),
    }


# COLLIO-SR2 10-23: SEAM landing sub-bands. Every body gate (S0/P/S1/S2/R @cfc200bfb/9bf8ffebe) failed cross_clock SETUP on
# the same class: inter-entry flop->flop crossings across the 864 x 907 body (210-ps distinct-entry reserve) between bands
# 600-1200 um apart (tx o_data W-top -> bank2 din_q E-bottom -181 ps; codec codec_data E-centre -> rx wd W-bottom -69 ps;
# c_abort -> bank we_q -100 ps; tx o_valid -> codec cmd_ov -26 ps).  RTL unchanged (0 cycles): the CAPTURE ranks of those
# crossings move out of their root's band into small seam sub-bands of the SAME root at the body centre-left, so each
# path is one <= ~650-um crossing hop plus one intra-root hop (60-ps uncertainty):
#   bank b landing (din_q/wa_q/we_q of g_bank[b].g_local.u_store, root codec(b+1)) -> seam SB_b next to the lcal band
#   codec_data (codec0, the pure-copy rx_flit rank of rf) -> crx between the codec band and the rx band
#   codec_valid (codec0) -> cval; tx o_valid (u_ctl.wr_observed_v, tx_rck) -> txov
# Counts are the measured 9bf8ffebe/cfc200bfb netlists (P / R gate odbs): din_q 137 (bank3 135, R 103) + wa_q 6 + we_q 1.
SEAM = {
    'main': {'bank0': (340.2, 442.8, 378.0, 496.8), 'bank2': (383.4, 442.8, 421.2, 496.8),
             'bank1': (340.2, 518.4, 378.0, 572.4), 'bank3': (383.4, 518.4, 421.2, 572.4),
             'crx': (340.2, 302.4, 421.2, 399.6), 'cval': (480.6, 394.2, 518.4, 410.4), 'txov': (340.2, 588.6, 378.0, 604.8)},
    # ALT (parallel fallback): seams 59.4 um further east (shorter c_abort/codec hops, longer tx hop), cval nearer the codec
    'alt': {'bank0': (399.6, 442.8, 437.4, 496.8), 'bank2': (442.8, 442.8, 480.6, 496.8),
            'bank1': (399.6, 518.4, 437.4, 572.4), 'bank3': (442.8, 518.4, 480.6, 572.4),
            'crx': (340.2, 302.4, 421.2, 399.6), 'cval': (448.2, 394.2, 486.0, 410.4), 'txov': (399.6, 588.6, 437.4, 604.8)},
}


def seam_land(land, prof, variant):
    """Split the seam ranks out of their roots' bands (exact counts) and lay them out in the SEAM boxes."""
    fw = 514 if prof == 'r' else 546
    b3 = fw - 3 * 137
    n = {'bank0': 144, 'bank1': 144, 'bank2': 144, 'bank3': b3 + 7, 'crx': fw, 'cval': 1, 'txov': 1}
    parent = {'bank0': 'bank0', 'bank1': 'bank1', 'bank2': 'bank2', 'bank3': 'bank3', 'crx': 'codec', 'cval': 'codec', 'txov': 'tx'}
    rx = {f'bank{b}': r'g_bank\[%d\]\.g_local\.u_store\.(din_q|wa_q|we_q)(\[|\$)' % b for b in range(4)}
    rx.update(crx=r'u_body\.codec_data\[', cval=r'u_body\.codec_valid\$', txov=r'u_ctl\.wr_observed_v\$')
    box = SEAM[variant]
    for s, par in parent.items():
        m = re.search(r'\n (%s \{[^}]*\} \{[^}]*\}) (\d+)\n' % par, land)
        assert m, par
        land = land.replace(m.group(0), '\n %s %d\n' % (m.group(1), int(m.group(2)) - n[s]), 1)
    sub = 'set ot_cl_sub {\n' + ''.join(' seam_%s %s {%s} {%s} %d\n' % (s, parent[s], rx[s], ' '.join('%.6f' % v for v in box[s]), n[s])
                                      for s in parent) + '}\n'
    a = '\nsource /src/physical/common_flow/anchor_row_packing.tcl'
    assert land.count(a) == 1
    land = land.replace(a, '\n' + sub.rstrip('\n') + a, 1)
    a = ' set members [lsort -dictionary $members]\n'
    assert land.count(a) == 1
    land = land.replace(a, a + (' set ot_cl_groups [list $name $members $box $expected]\n'
        ' foreach {sn sp sre sbox sexp} $ot_cl_sub {\n'
        '  if {$sp ne $name} continue\n'
        '  set sm {};set rest {}\n'
        '  foreach n [lindex $ot_cl_groups 1] {if {[regexp $sre [string map {\\\\ {}} $n]]} {lappend sm $n} else {lappend rest $n}}\n'
        '  lset ot_cl_groups 1 $rest;lappend ot_cl_groups $sn $sm $sbox $sexp\n'
        ' }\n'
        ' foreach {name members box expected} $ot_cl_groups {\n'), 1)
    a = ' puts "OT_COLL_LAND planned $name roots={$ports} cells=[llength $members] columns=$cols rows=$nr box=$box"\n}\n'
    assert land.count(a) == 1
    land = land.replace(a, a[:-2] + '\n }\n}\n', 1)
    a = 'ten landing bands, twelve roots'
    assert land.count(a) == 1
    land = land.replace(a, 'ten landing bands + seven seam sub-bands (COLLIO-SR2 %s), twelve roots' % variant)
    return '# COLLIO-SR2 10-23 seam sub-bands (%s): bank landings / codec_data / codec_valid / tx o_valid moved to centre-left seams\n' % variant + land


def body_spec(prof):
    src = {'s0': 'qfd_coll_face_s0_regional7_main', 'p': 'qfd_coll_face_p_regional5_main',
           # CB16c-COLL2-SR: S1 / S2 / R on the S0 regional7 frame (same 907.2 frame, 6 macros at the same sites, 12 roots)
           's1': 'qfd_coll_face_s0_regional7_main', 's2': 'qfd_coll_face_s0_regional7_main',
           'r': 'qfd_coll_face_s0_regional7_main'}[prof]
    name = f'qfd_cb16c_{prof}_body'
    s = json.loads((RT / src / 'spec.json').read_text().replace(f'physical/ref_tile/{src}/', f'physical/ref_tile/{name}/'))
    s['name'] = name
    s['top'] = f'qfd_coll_face_{prof}_cxb'
    s['sources'] = [CX, BODY] + [x for x in s['sources'] if not x.endswith(f'qfd_coll_face_{prof}_pl.sv')]
    s['params'] = {}
    s['outline'] = {'w': W_BODY, 'h': H}
    # pins: every bus clustered in the window of its owning band (the band boxes of seq_landing.tcl)
    s['pins'] = {'W': ['rx_data', 'rx_valid', 'rx_rck', 'rx_wck', 'cal_ck', 'cal_lck', 'rst_n', 'tx_slot', 'peer_slot', 'tx_valid',
                       'cdc_fault', 'tx_data', 'tx_wck', 'tx_rck', 'codec2'],
                 'E': ['phy_rx', 'phy_rx_valid', 'phy_up', 'codec0p', 'epoch_abort', 'fault_cause', 'phy_tx_valid', 'phy_tx',
                       'phy_tx_slot', 'phy_rx_slot', 'codec3', 'codec4'],
                 'N': [], 'S': ['codec1', 'codec0']}
    s['pin_ranges'] = {
        # W: rx band y 54.0-334.8 / cal band 388.8-496.8 / tx band 615.6-853.2
        'rx_data': [97.2, 280.8], 'rx_valid': [282.96, 286.2], 'rx_rck': [288.36, 291.6], 'rx_wck': [293.76, 297.0],
        'cal_ck': [437.4, 440.64], 'cal_lck': [442.8, 446.04], 'rst_n': [448.2, 451.44], 'tx_slot': [453.6, 456.84],
        'peer_slot': [459.0, 462.24], 'tx_valid': [464.4, 467.64], 'cdc_fault': [469.8, 480.6],
        'tx_data': [637.2, 820.8], 'tx_wck': [823.0, 826.2], 'tx_rck': [828.4, 831.6], 'codec2': [842.4, 845.64],
        # E: phy band y 345.6-604.8 (the codec0p root); lcal-owned slots at its lower end
        'phy_rx': [345.6, 432.0], 'phy_rx_valid': [434.16, 437.4], 'phy_up': [439.56, 442.8], 'codec0p': [469.8, 473.04],
        'epoch_abort': [475.2, 478.44], 'fault_cause': [480.6, 491.4], 'phy_tx_valid': [509.76, 513.0],
        'phy_tx': [518.4, 604.8], 'phy_tx_slot': [448.2, 451.44], 'phy_rx_slot': [453.6, 456.84],
        'codec3': [216.0, 219.24], 'codec4': [691.2, 694.44]}
    s['fill_reason'] = {'pin_bound': 'CB16c-COLL body of the split face: perimeter set by the face slot (907.2 square minus two '
                        '21.6-um slice columns), six fixed SRAM macros; std cells banded beside their roots.'}
    s.pop('std_area_um2', None)
    s['structural_change'] = (
        f'CB16c-COLL 10-22 (ALT, STEWARD-QKc/SQC-CB16c): body of the regionally split {prof.upper()} collective face qfd_coll_face_cx '
        f'(RTL qfd_coll_static_face_x, generated by exact substitution from the face RTL at 2919e5896). The four pin-bound ranks moved '
        f'to hardened edge slices with their own clock entries (tx_data td_q, rx CDC o_data: 0 cycles; phy_tx / phy_rx: +1 each, '
        f'consumed by the calendar, face L+2). Geometry = {src} (6 macros, 12 roots, ten landing bands) on an 864.0 x 907.2 outline '
        f'(E band moved in 43.2 um), with every bus pin CLUSTERED in the window of its owning band, so each root\'s pin flops are '
        f'within one ~250-um band (was: tx_data / rx_data / phy pins spread over the whole 907-um edge on one root).')
    s['slot_change_request'] = 'body 864.0 x 907.2 inside the 907.2-square face slot of the Codex regional kits (unchanged slot)'
    prof_args = {'s0': 's0', 'p': 'p', 's1': 's1', 's2': 's2', 'r': 'r'}[prof]
    if prof in ('s1', 's2', 'r'):
        s['job'] = dict(OWNER, branch='claude/cb16c-sr-1022')
        s['structural_change'] = s['structural_change'].replace('CB16c-COLL 10-22', 'CB16c-COLL2-SR 10-22', 1) + (
            ' R: FW 514 / PW 565 (slices es257 x2 W, es113 x5 E in qfd_coll_face_r_cx).' if prof == 'r' else '')
    s['job'] = dict(s.get('job') if prof in ('s1', 's2', 'r') else OWNER, tag=f'{prof}cxb', purpose=f'CB16c-COLL: {prof.upper()} face body of the regional split (ALT)',
                    benches=[lint(s['top'], s['sources'], '-DOT_COLL_BANK_LOCAL -DOT_COLL_REGIONAL'),
                             bench(prof_args, 0, 'pass', f'{WIT}/{prof}_m0.log')]
                    + [bench(prof_args, m, 'fail', f'{WIT}/{prof}_m{m}.log') for m in (1, 2, 3, 4)])
    # tx_data is now captured by the TX CDC write rank wd (tx_wck): the td_q cal_ck rank is the face slice
    d = s['clock_entry_domains']
    d['core']['inputs'] = [x for x in d['core']['inputs'] if x != 'tx_data']
    d['txw']['inputs'] = ['tx_data']
    s['pin_hook_after_flops'] = [f'physical/ref_tile/{name}/seq_landing.tcl']
    s['pre_dpl_extra'] = [f'physical/ref_tile/{name}/seq_release.tcl']
    return s, src


def write(spec, hand=None):
    d = RT / spec['name']
    d.mkdir(parents=True, exist_ok=True)
    (d / 'spec.json').write_text(json.dumps(spec, indent=1) + '\n')
    for f, t in (hand or {}).items():
        (d / f).write_text(t)
    print('wrote', d / 'spec.json')


# ---------------------------------------------------------------------------------------------- face cluster parent
# CB16c-COLL2 10-22: wires-only parent qfd_coll_face_cx = body + 12 edge slices, every child clock pin on its own face
# entry (clock "entries"): the body's 12 roots + 12 regional slice entries (cal_ck_t* / rx_rck_r* / codec0p_t* / codec0p_r*,
# fed by the die from the same face_ck bits as cal_ck / rx_rck / codec0p).  Slice columns 21.6 um W and E, 4.32-um channels
# to the body, 8.64-um core margin; slices stacked at a 151.2 pitch (5.4-um channel above each slice carries its ck entry).
# W column: rx slices (MY: d faces the body) at the bottom under the body rx band, tx slices on top under the tx band;
# E column: phy_rx slices (MY) at the bottom beside the phy_rx window, phy_tx slices on top.  Parent signals M2-M7.
CX_PROF = {'s0': dict(HARD=1, PHY=350, L=383, R=0, PEER_R=5), 'p': dict(HARD=2, PHY=20, L=58, R=5, PEER_R=5),
           'r': dict(HARD=1, PHY=20, L=58, R=5, PEER_R=5)}   # COLLIO-SR2: R face (FW 514), bench profile r L0 56 + 2
CX_M, CX_CH, CX_SW, CX_SH, CX_PITCH = 8.64, 4.32, 21.6, 146.88, 151.2   # slice view 21.6 x 146.88


def cx_spec(prof):
    body = json.loads((RT / f'qfd_cb16c_{prof}_body' / 'spec.json').read_text())
    xw, xb = CX_M, CX_M + CX_SW + CX_CH
    xe = xb + W_BODY + CX_CH
    W, Hh = round(xe + CX_SW + CX_M, 2), round(H + 2 * CX_M, 2)
    ys = [round(CX_M + i * CX_PITCH, 2) for i in range(6)]
    v = lambda kit, top: f'physical/ref_tile/{kit}/views/{top}'
    ch = [{'view': v(f'qfd_cb16c_{prof}_body', f'qfd_coll_face_{prof}_cxb'), 'count': 1, 'inst': '*u_core', 'at': [xb, CX_M]}]
    for i in range(3):
        ch.append({'view': v('qfd_cb16c_es182', 'qfd_coll_eslice182'), 'count': 1, 'inst': f'*u_rxs{i}', 'at': [xw, ys[i]], 'orient': 'MY'})
        ch.append({'view': v('qfd_cb16c_es182', 'qfd_coll_eslice182'), 'count': 1, 'inst': f'*u_txs{i}', 'at': [xw, ys[3 + i]]})
        ch.append({'view': v('qfd_cb16c_es199', 'qfd_coll_eslice199'), 'count': 1, 'inst': f'*u_prs{i}', 'at': [xe, ys[i]], 'orient': 'MY'})
        ch.append({'view': v('qfd_cb16c_es199', 'qfd_coll_eslice199'), 'count': 1, 'inst': f'*u_pts{i}', 'at': [xe, ys[3 + i]]})
    ent = {}
    for i in range(3):
        g_lo, g_hi = ys[i] + CX_SH, ys[i] + CX_PITCH          # the channel above slice i / 3+i: its ck pin (N face) sits there
        G_lo, G_hi = ys[3 + i] + CX_SH, ys[3 + i] + CX_PITCH
        c = lambda a, b: [round((a + b) / 2 - 0.144, 3), round((a + b) / 2 + 0.144, 3)]
        ent[f'rx_rck_r{i}'] = ('W', c(g_lo, g_hi))
        ent[f'codec0p_r{i}'] = ('E', c(g_lo, g_hi))
        ent[f'cal_ck_t{i}'] = ('W', c(G_lo, min(G_hi, Hh - CX_M / 2)))
        ent[f'codec0p_t{i}'] = ('E', c(G_lo, min(G_hi, Hh - CX_M / 2)))
    pins = {f: list(body['pins'].get(f, [])) for f in ('N', 'S', 'W', 'E')}
    rng = {k: [round(a + CX_M, 2), round(b + CX_M, 2)] for k, (a, b) in body['pin_ranges'].items()}
    rng['rx_data'] = [round(ys[0] + 2.16, 2), round(ys[2] + CX_SH - 2.16, 2)]
    rng['tx_data'] = [round(ys[3] + 2.16, 2), round(ys[5] + CX_SH - 2.16, 2)]
    rng['phy_rx'] = list(rng['rx_data'])
    rng['phy_tx'] = list(rng['tx_data'])
    for k, (f, r) in ent.items():
        pins[f].append(k)
        rng[k] = r
    body_ck = list(body['clock_ports'])
    ports = body_ck + [f'cal_ck_t{i}' for i in range(3)] + [f'rx_rck_r{i}' for i in range(3)] + \
        [f'codec0p_t{i}' for i in range(3)] + [f'codec0p_r{i}' for i in range(3)]
    name = f'qfd_cb16c_{prof}_cx'
    return {
        'name': name, 'top': 'qfd_coll_face_cx', 'kind': 'cluster', 'sources': [CX, BODY] + [x for x in body['sources'] if x not in (CX, BODY)],
        'defines': list(body.get('defines', [])), 'params': CX_PROF[prof],
        'clock': 'entries', 'clock_port': ports[0], 'clock_ports': ports, 'reset_ports': [],
        'outline': {'w': W, 'h': Hh}, 'child_lattice_um': 2.16, 'children': ch, 'pins': pins, 'pin_ranges': rng,
        'route': {'pd': 0.3, 'threads': 8, 'peak_ram_gb': 32, 'pin_h': 'M4'},
        'child_clock_ref': 'boundary',
        'structural_change': (f'CB16c-COLL2 10-22: wires-only face cluster of the regionally split {prof.upper()} collective face: '
                              'hard body (12 local roots) + 12 hardened edge register slices (es182 x6 W, es199 x6 E), every child '
                              'clock pin on its own face entry (24 entries; the 12 slice entries are new regional ports beside the '
                              'slices); no parent tree, no parent logic; parent signals M2-M7 over the M5 children.'),
        'why_floorplan': 'wires-only parent: body 864 x 907.2 + two 21.6-um slice columns, 4.32-um channels, 8.64-um margin',
        'slot_change_request': f'face slot 907.2 square -> {W} x {Hh} (the two slice columns + channels around the 864-um body)',
        'job': dict(OWNER, owner='Claude:CB16c-COLL2', tag=f'{prof}cx', purpose=f'CB16c-COLL2: {prof.upper()} face cluster parent (regional split)',
                    extra_paths=['physical/common_flow/clock_entries.tcl'],
                    views_to=f'physical/ref_tile/{name}/views', record_to=f'results/rtl/ref_tile/{name}',
                    benches=[bench(prof, 0, 'pass', f'{WIT}/{prof}_m0.log')] + [bench(prof, m, 'fail', f'{WIT}/{prof}_m{m}.log') for m in (1, 2, 3, 4)]),
    }

# COLLIO-SR2 10-23: R face cluster parent qfd_coll_face_r_cx (FW 514): body + 14 hardened edge slices on their own entries
# (W: es257 x2 rx (MY, bottom, under the body rx band) + x2 tx (top, under the tx band), view 21.6 x 146.88 at the S0
# 151.2 pitch; E: es113 x5 phy_rx (MY, bottom) + x5 phy_tx (top), view 21.6 x 86.4 at a 91.2 pitch, the 4.8-um channel
# above each slice carrying its ck entry).  26 clock entries = 12 body roots + cal_ck_t0..1 / rx_rck_r0..1 /
# codec0p_t0..4 / codec0p_r0..4.  Same frame as S0/P (933.12 x 924.48); kit gen once the R body view exists.
CX_SH13, CX_P13 = 86.4, 91.2


def cx_spec_r():
    prof = 'r'
    body = json.loads((RT / f'qfd_cb16c_{prof}_body' / 'spec.json').read_text())
    xw, xb = CX_M, CX_M + CX_SW + CX_CH
    xe = xb + W_BODY + CX_CH
    W, Hh = round(xe + CX_SW + CX_M, 2), round(H + 2 * CX_M, 2)
    yw = [round(CX_M + i * CX_PITCH, 2) for i in (0, 1, 4, 5)]          # rx0 rx1 | tx0 tx1
    ye = [round(CX_M + i * CX_P13, 2) for i in range(10)]               # prx0..4 | ptx0..4
    assert ye[9] + CX_SH13 <= Hh - CX_M + 1e-6
    v = lambda kit, top: f'physical/ref_tile/{kit}/views/{top}'
    ch = [{'view': v('qfd_cb16c_r_body', 'qfd_coll_face_r_cxb'), 'count': 1, 'inst': '*u_core', 'at': [xb, CX_M]}]
    for i in range(2):
        ch.append({'view': v('qfd_cb16c_es257', 'qfd_coll_eslice257'), 'count': 1, 'inst': f'*u_rxs{i}', 'at': [xw, yw[i]], 'orient': 'MY'})
        ch.append({'view': v('qfd_cb16c_es257', 'qfd_coll_eslice257'), 'count': 1, 'inst': f'*u_txs{i}', 'at': [xw, yw[2 + i]]})
    for i in range(5):
        ch.append({'view': v('qfd_cb16c_es113', 'qfd_coll_eslice113'), 'count': 1, 'inst': f'*u_prs{i}', 'at': [xe, ye[i]], 'orient': 'MY'})
        ch.append({'view': v('qfd_cb16c_es113', 'qfd_coll_eslice113'), 'count': 1, 'inst': f'*u_pts{i}', 'at': [xe, ye[5 + i]]})
    c = lambda a, b: [round((a + b) / 2 - 0.144, 3), round((a + b) / 2 + 0.144, 3)]
    ent = {}
    for i in range(2):
        ent[f'rx_rck_r{i}'] = ('W', c(yw[i] + CX_SH, yw[i] + CX_PITCH))
        ent[f'cal_ck_t{i}'] = ('W', c(yw[2 + i] + CX_SH, min(yw[2 + i] + CX_PITCH, Hh - CX_M / 2)))
    for i in range(5):
        ent[f'codec0p_r{i}'] = ('E', c(ye[i] + CX_SH13, ye[i] + CX_P13))
        ent[f'codec0p_t{i}'] = ('E', c(ye[5 + i] + CX_SH13, min(ye[5 + i] + CX_P13, Hh - CX_M / 2)))
    pins = {f: list(body['pins'].get(f, [])) for f in ('N', 'S', 'W', 'E')}
    rng = {k: [round(a + CX_M, 2), round(b + CX_M, 2)] for k, (a, b) in body['pin_ranges'].items()}
    rng['rx_data'] = [round(yw[0] + 2.16, 2), round(yw[1] + CX_SH - 2.16, 2)]
    rng['tx_data'] = [round(yw[2] + 2.16, 2), round(yw[3] + CX_SH - 2.16, 2)]
    rng['phy_rx'] = [round(ye[0] + 2.16, 2), round(ye[4] + CX_SH13 - 2.16, 2)]
    rng['phy_tx'] = [round(ye[5] + 2.16, 2), round(ye[9] + CX_SH13 - 2.16, 2)]
    for k, (f, r) in ent.items():
        pins[f].append(k)
        rng[k] = r
    ports = list(body['clock_ports']) + [f'cal_ck_t{i}' for i in range(2)] + [f'rx_rck_r{i}' for i in range(2)] + \
        [f'codec0p_t{i}' for i in range(5)] + [f'codec0p_r{i}' for i in range(5)]
    assert len(ports) == 26
    name = 'qfd_cb16c_r_cx'
    return {
        'name': name, 'top': 'qfd_coll_face_r_cx', 'kind': 'cluster', 'sources': [CX, BODY] + [x for x in body['sources'] if x not in (CX, BODY)],
        'defines': ['OT_COLL_BANK_LOCAL', 'OT_COLL_REGIONAL'], 'params': CX_PROF[prof],
        'clock': 'entries', 'clock_port': ports[0], 'clock_ports': ports, 'reset_ports': [],
        'outline': {'w': W, 'h': Hh}, 'child_lattice_um': 2.16, 'children': ch, 'pins': pins, 'pin_ranges': rng,
        'route': {'pd': 0.3, 'threads': 8, 'peak_ram_gb': 32, 'pin_h': 'M4'},
        'child_clock_ref': 'boundary',
        'structural_change': ('COLLIO-SR2 10-23: wires-only face cluster of the regionally split R collective face (FW 514): hard '
                              'body (12 local roots) + 14 hardened edge register slices (es257 x4 W, es113 x10 E), every child '
                              'clock pin on its own face entry (26 entries; the 14 slice entries are new regional ports beside the '
                              'slices); no parent tree, no parent logic; parent signals M2-M7 over the M5 children.'),
        'why_floorplan': 'wires-only parent: body 864 x 907.2 + two 21.6-um slice columns, 4.32-um channels, 8.64-um margin',
        'slot_change_request': f'face slot 907.2 square -> {W} x {Hh} (the two slice columns + channels around the 864-um body)',
        'job': dict(OWNER, owner='Claude:COLLIO-SR2', branch='claude/cb16c-sr-1022', tag='rcx',
                    purpose='COLLIO-SR2: R face cluster parent (regional split)',
                    extra_paths=['physical/common_flow/clock_entries.tcl'],
                    views_to=f'physical/ref_tile/{name}/views', record_to=f'results/rtl/ref_tile/{name}',
                    benches=[bench(prof, 0, 'pass', f'{WIT}/{prof}_m0.log')] + [bench(prof, m, 'fail', f'{WIT}/{prof}_m{m}.log') for m in (1, 2, 3, 4)]),
    }


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == 'cx':
        for prof in sys.argv[3:] or ('s0', 'p'):
            write(cx_spec_r() if prof == 'r' else cx_spec(prof))
        sys.exit(0)
    for w in (182, 199, 257, 113):
        write(slice_spec(w))
    for prof in ('s0', 'p', 's1', 's2', 'r'):
        s, src = body_spec(prof)
        land = (RT / 'qfd_coll_face_s0_regional7_main' / 'seq_landing.tcl').read_text()   # P: same geometry, S0's band method
        old = (' phy {codec0p} {864.000000 345.600000 896.400000 604.800000}',
               ' codec {codec0} {604.800000 388.800000 820.800000 561.600000}')
        new = (' phy {codec0p} {810.000000 345.600000 842.400000 604.800000}',
               ' codec {codec0} {604.800000 388.800000 799.200000 561.600000}')
        for a, b in zip(old, new):
            assert land.count(a) == 1, a
            land = land.replace(a, b)
        a = ' if {[llength $members]!=$expected} {error "OT_COLL_LAND $name actual [llength $members] differs from measured source count $expected"}'
        assert land.count(a) == 1
        land = land.replace(a, ' if {[llength $members]!=$expected} {lappend ot_cl_miss "$name actual [llength $members] expected $expected"}')
        a = 'set ot_cl_owned {};set ot_cl_by {};set ot_cl_boxes {};set ot_cl_seen_cells {}'
        assert land.count(a) == 1
        land = land.replace(a, a + ';set ot_cl_miss {}')
        a = 'ot_anchor_pack::repair $ot_cl_b $ot_cl_owned'
        assert land.count(a) == 1
        land = land.replace(a, 'if {[llength $ot_cl_miss]} {error "OT_COLL_LAND counts differ from the measured source counts: [join $ot_cl_miss {; }]"}\n' + a)
        cnt = COUNTS.get(prof)
        if cnt:
            for band, n in cnt.items():
                import re as _re
                land, k = _re.subn(r'(\n %s \{[^}]*\} \{[^}]*\}) \d+\n' % band, r'\g<1> %d\n' % n, land)
                assert k == 1, band
        land = '# CB16c-COLL body: E bands moved in by the 43.2-um slice columns; counts = the measured body netlist (all bands\n# reported at once on a mismatch)\n' + land
        rel = (RT / 'qfd_coll_face_s0_regional7_main' / 'seq_release.tcl').read_text()
        s['structural_change'] += (' COLLIO-SR2 10-23: SEAM landing sub-bands (RTL and cycles unchanged): bank landing din_q/wa_q/we_q, '
                                   'codec_data/codec_valid and tx o_valid placed in centre-left seams of their own roots, so no '
                                   'inter-entry hop exceeds ~650 um (all 5 body gates failed cross_clock on 600-1200-um crossings).')
        write(s, {'seq_landing.tcl': seam_land(land, prof, 'main'), 'seq_release.tcl': rel})
        # ALT (parallel fallback route): same body, seams 59.4 um further east
        a = json.loads(json.dumps(s).replace(f'physical/ref_tile/{s["name"]}/', f'physical/ref_tile/{s["name"]}x/'))
        a['name'] = s['name'] + 'x'
        a['job'] = dict(a['job'], tag=a['job']['tag'] + 'x', purpose=a['job']['purpose'] + ' -- ALT seam geometry (COLLIO-SR2)')
        a['structural_change'] = a['structural_change'].replace('centre-left seams', 'centre seams (ALT, +59.4 um east)')
        write(a, {'seq_landing.tcl': seam_land(land, prof, 'alt'), 'seq_release.tcl': rel})
