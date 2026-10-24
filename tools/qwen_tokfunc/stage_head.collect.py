#!/usr/bin/env python3
"""TOK-FUNC-QW stage head collector: RUNROOT/head/runs/* -> RUNROOT/head/result.json.

    stage_head.collect.py RUNROOT GRADE IMGREL
LM-head span on RTL = from the stage-37 start edge e0 (the log's 'STAGE 37' line is e0 + 1, command_stage latched on the
start) to the head's END fixed issue (last ISSUE in stage 37) and to the LM-head ROM command go; compared with the
compiled image (lm_head.expected.me_issue / rom_go_at_tt_ctlm edges) and the ctlm head plan price (3,101 cycles)."""
import json
import re
import sys
from pathlib import Path

PRICED_HEAD_PLAN = 3101
rr, grade, imgrel = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
S = rr / 'head'
R = S / 'runs'
src_commit = (rr / 'src' / 'ASM_COMMIT').read_text().strip() if (rr / 'src' / 'ASM_COMMIT').exists() else '?'


def verdict(name):
    f = R / f'{name}.out'
    if not f.exists():
        return None, 'NOT_RUN'
    t = f.read_text()
    m = re.findall(r'CTLM_PROG .*?: (PASS|FAIL) (\d+)/(\d+)', t)
    lk = re.findall(r'LANDED_LOCKSTEP (?:PASS|FAIL) .*', t)
    if not m:
        return None, 'NO_RESULT (build/run error, see log)'
    v, ok, n = m[-1]
    return (v, int(ok), int(n), lk[-1] if lk else None), f'{v} {ok}/{n}'


res = {k: verdict(k) for k in ('h16y_img0', 'h16y_imgh', 'h16y_bmut3', 'src_landed')}
img = json.loads((S / 'tree' / imgrel / 'imgh' / 'ctlm_image.json').read_text())
HX = img['lm_head']['expected']
exp_end = HX['me_issue'][-1]['edge']
exp_rom = HX['rom_go_at_tt_ctlm'][-1]['edge']
cycles, notes = {}, []
lg = R / 'h16y_imgh' / 'log_m0_b0.txt'
if lg.exists():
    e0, issues, roms = None, [], []
    for line in open(lg):
        p = line.split()
        if len(p) < 2:
            continue
        cy, k = int(p[0]), p[1]
        if k == 'STAGE' and int(p[2]) == 37:
            e0 = cy - 1
        elif e0 is not None and k == 'ISSUE':
            issues.append((cy, int(p[2]), int(p[3])))
        elif e0 is not None and k == 'ROM':
            roms.append(cy)
    if e0 is not None and issues:
        cycles['lm_head_stage_start_to_END_issue'] = issues[-1][0] - e0
        cycles['lm_head_compiled_END_edge'] = exp_end
        cycles['lm_head_head_stop_cycle_compiled'] = img['lm_head']['stop_cycle']
        cycles['lm_head_priced_ctlm_plan'] = PRICED_HEAD_PLAN
        if roms:
            cycles['lm_head_stage_start_to_ROM_go'] = roms[0] - e0
            cycles['lm_head_ROM_go_to_END_issue'] = issues[-1][0] - roms[0]
        cycles['lm_head_compiled_ROM_go_edge'] = exp_rom
        notes.append(f'measured END edge {issues[-1][0] - e0} vs compiled {exp_end}; vs priced plan {PRICED_HEAD_PLAN} '
                     f'({issues[-1][0] - e0 - PRICED_HEAD_PLAN:+d})')
    else:
        notes.append('no stage-37 STAGE/ISSUE lines in the imgh log')
else:
    notes.append('imgh log missing')

ok = lambda k: res[k][0] is not None and res[k][0][0] == 'PASS'
fail = lambda k: res[k][0] is not None and res[k][0][0] == 'FAIL'
landed_ok = grade != 'RTL-functional (source assembly)' or (ok('src_landed') and res['src_landed'][0][3]
                                                            and res['src_landed'][0][3].startswith('PASS'))
timing_ok = 'lm_head_stage_start_to_END_issue' in cycles and cycles['lm_head_stage_start_to_END_issue'] == exp_end
v = 'PASS' if ok('h16y_img0') and ok('h16y_imgh') and fail('h16y_bmut3') and timing_ok else 'FAIL'
findings = []
if grade == 'RTL-functional (source assembly)' and not landed_ok:
    findings.append('src_landed: the landed ctlm cluster qfd_tt_ctlm_dv_lpf(_lp) diverges from qfd_tt_ctlm_dv in the LM-head stage '
                    '37 (stages 0..3 lockstep-clean): lpf instantiates ot_qfd_tt_ctlm_static_hr without .SEGCAL(1) and has no '
                    'segment-G XPF schedule (g_segx), i.e. it predates QW-SEGCAL ff9abcf4f. The hard head leaf (h16y/h16yb '
                    'netlist, chparam SEGCAL 1) is unaffected; the RTL source form of the landed parent runs the base-0 calendar '
                    'for the LM head. ' + str(res['src_landed'][0][3] if res['src_landed'][0] else res['src_landed'][1]))
out = {
    'stage': 'head',
    'grade': grade,
    'src_commit': src_commit,
    'verdict': v,
    'verdict_scope': ('h16y head leaf RTL (ot_qfd_tt_ctlm_static_hr_safe32 H16X=2 SEGCAL=1) in qfd_tt_ctlm_dv: img0/imgh PASS, bmut3 caught, LM-head span = compiled; src_landed is a finding, not in the verdict'
                      if grade == 'RTL-functional (source assembly)' else
                      'die-selected head leaf ot_qfd_tt_ctlm_static_hr_safe32_native32_1r (STAGE_ME 1, SEGCAL 1; ' + ('RTL h16za/native32_1r_param.v' if 'leaf' in grade else 'GEN carve') +
                      ') through the native32 vehicle in qfd_tt_ctlm_dv: img0/imgh PASS, bmut3 caught, LM-head span = compiled; src_landed not run (the abandoned generic LP is not the die parent)'),
    'findings': findings,
    'golden': ('compiled ctlm deployment images results/rtl/qlb_c4b_1018/lmh_cal/codex_r1 img0/imgh (ctlm_image.py '
               '--lm-head): every slice command word, LOCAL start, head fixed issue/END (pc,unit), ROM go, native go, XPF '
               'arm word and command_stage on its compiled edge (img0 123 checks, imgh 131 incl. the LM-head stage 37); '
               'ROM words decoded in the slice layout; src_landed = landed cluster qfd_tt_ctlm_dv_lpf_lp cycle-lockstep '
               'vs qfd_tt_ctlm_dv. NOT compared: LM-head logits/argmax vs the TP4 gold head -- this bench carries no '
               'datapath (the stg stage STG lm runs the LM-head matvec/AMAX/gather bit-exact)'),
    'runs': {k: res[k][1] + (f' | {res[k][0][3]}' if res[k][0] and res[k][0][3] else '') for k in res},
    'cycles': cycles,
    'mutants': {'h16y_bmut3 (LM-head segment-G first row one cycle late)':
                'FAIL as required' if fail('h16y_bmut3') else f'NOT CAUGHT ({res["h16y_bmut3"][1]})'},
    'stand_ins': ['slices / ROM tiles / native unit not simulated: their status (su_busy, su_prog, stn_busy, '
                  'native_idle) answers at the compiled image status cycles (tt_ctlm_prog_bench status_events)',
                  'kv_ok / kv_write_drained driven as levels (the T calendar LEVEL)',
                  'the LM-head span is the head control span (issue -> END on its fixed calendar); the matvec compute '
                  'duration inside it is the compiled wait, not a simulated ROM-tile run'],
    'notes': notes,
    'die_netlist_hook': '--die-netlist DIR: DIR/head_leaf.v (GEN carve of u_hr, $HEAD_NET_MODULE) replaces the h16y RTL '
                        'via the qfd_tt_head_static_h16y native vehicle',
    'logs': [str(p.relative_to(rr)) for p in sorted(R.glob('*.out'))] + ['head/runs/summary.txt'],
}
(S / 'result.json').write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps({k: out[k] for k in ('verdict', 'runs', 'cycles', 'mutants')}, indent=1))
