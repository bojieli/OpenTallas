#!/usr/bin/env python3
"""CB16c-COLL 10-22: kit specs of the regional-split collective face sub-tiles.

  qfd_cb16c_es182 / qfd_cb16c_es199   edge register slices (one flop per bit, d W -> q E, ck N; hardened once, x6 each)
  qfd_cb16c_s0_body / qfd_cb16c_p_body the face bodies (12 roots, 6 SRAMs): the S0 / P regional7/5 kit geometry, with
                                        the body pins CLUSTERED in the window of the band that owns them (so every root's
                                        pin flops are local) and the E band moved in by the 43.2-um slice columns.
Writes physical/ref_tile/<kit>/spec.json (+ hand hooks); run tools/ref_tile/ref_tile.py gen on each afterwards.
"""
import copy, json, pathlib, sys
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
COUNTS = {}


def slice_spec(w):
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


def body_spec(prof):
    src = {'s0': 'qfd_coll_face_s0_regional7_main', 'p': 'qfd_coll_face_p_regional5_main'}[prof]
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
    s['fill_reason'] = {'regional_split': 'CB16c-COLL body of the split face: perimeter set by the face slot (907.2 square minus two '
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
    prof_args = {'s0': 's0', 'p': 'p'}[prof]
    s['job'] = dict(OWNER, tag=f'{prof}cxb', purpose=f'CB16c-COLL: {prof.upper()} face body of the regional split (ALT)',
                    benches=[lint(s['top'], s['sources'], '-DOT_COLL_BANK_LOCAL -DOT_COLL_REGIONAL'),
                             bench(prof_args, 0, 'pass', f'{WIT}/{prof}_m0.log')]
                    + [bench(prof_args, m, 'fail', f'{WIT}/{prof}_m{m}.log') for m in (1, 2, 3, 4)])
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


if __name__ == '__main__':
    for w in (182, 199):
        write(slice_spec(w))
    for prof in ('s0', 'p'):
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
        write(s, {'seq_landing.tcl': land, 'seq_release.tcl': rel})
