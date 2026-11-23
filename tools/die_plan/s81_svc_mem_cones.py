"""S81 svc memory closure, per-helper STRUCTURAL steps (OPUS-FIX-S81-SVC-R9 11-22, COORD 18:0x ruling).

The class port in s81_svc_memory_closure.py re-targets the four T7 transforms (pmem, pvq, land, stage) through a
structural name map of the T7 bound.  It applies only to bounds of the T7 shape (all four native helpers, same att
variant).  The J7 monolithic hi rs t4/t5, lo rs t3/t6, pvso_entry t1 and J8 lo t4 bounds are another att variant
(narrow pvq helper 133b963e 8x1064 instead of 9c28 8x2120): measured on the real lo t3 bound, NO regenerated reference
(incl. the two with the same stage digest) maps their pmem or land cone, so the class port refuses them whatever
the helper gate says.

This module closes such a bound one helper at a time, each cone matched by exact structural witnesses whose net names
are derived from the bound (every pattern must match exactly once, cross references consistent; anything else raises):
  stage : the two stage2 ot_hdc_v41x_attn_staging #(.D(32),.NL(4),.SRAM_MACRO(0),.TROWS(640)) -> _staging_fit, SRAM 1
  pmem  : native PMEM 193c9 + its packed/payload/skid cone -> ot_t7_pmem_capture_v2 (4 x 256x256)
  land  : no structural cut yet (class port only); a present land helper stays native and is reported
  pvq   : narrow pvq stays native (8.5k bits); 9c28 pvq is class port only
The plan rows follow the steps: a capture/staging macro row is placed only when its step applied
(plan_row_group / ghost_rows), and plan_gate_pre MACROGHOST predicts the same from the bound before any kit.
"""
import re

HELPER = {'pmem': 'ot_bind_native_193c9bdc13b0c4251a5bbbc4', 'pvq': 'ot_bind_native_9c28130c03bbd6a26f6fd9a5',
          'land': 'ot_bind_native_4c805a5536bda0930879099e', 'stage': 'ot_hdc_v41x_attn_staging'}
PVQ_NARROW = 'ot_bind_native_133b963e2a98e3a3fc42b281'
STEPS = ('pmem', 'pvq', 'land', 'stage')
STRUCT_STEPS = ('pmem', 'stage')                 # steps with a structural (non class-port) form
# v2 children / macros per step (MACROS['v2'] of the closure, split by the step that instantiates them)
STEP_CHILD = {'pmem': 'ot_t7_pmem_capture_v2.sv', 'pvq': 'ot_t7_pvq_capture_v2.sv', 'land': 'ot_t7_land_capture_v2.sv',
              'stage': 'ot_hdc_v41x_attn_staging_fit.sv'}
STEP_MACROS = {'pmem': {'ot_sram_1r1w_256x256_m1_r0c0': 4}, 'pvq': {'ot_sram_1r1w_32x128_m1_r0c0': 17},
               'land': {'ot_sram_1r1w_160x256_m1_r0c0': 12}, 'stage': {'ot_sram_1r1w_160x265_m1_r0c0': 8}}
STAGE = "ot_hdc_v41x_attn_staging #(.D(32), .NL(4), .SRAM_MACRO(1'b0), .TROWS(640)) "
RE_ROW = re.compile(r'(?:^|\.)g_\w*?_(pmem|pvq|land)_capture\.|_g_stage2_u_stage[01]\.g_macro\.')


class ConeError(ValueError):
    pass


def helpers(bound_text):
    """{step: native instance count}, plus 'pvq_narrow'"""
    h = {k: len(re.findall(r'^\s*' + m + r'\b', bound_text, re.M)) for k, m in HELPER.items()}
    h['pvq_narrow'] = len(re.findall(r'^\s*' + PVQ_NARROW + r'\b', bound_text, re.M))
    return h


def class_shape(h):
    """the T7 shape the class port closes: every helper, one native memory each, two staging instances"""
    return h['pmem'] == 1 and h['pvq'] == 1 and h['land'] == 1 and h['stage'] == 2


def predict_steps(bound_text):
    """steps the closure applies to this bound: all four (class port) or the structural subset present"""
    h = helpers(bound_text)
    if class_shape(h):
        return set(STEPS)
    return {s for s in STRUCT_STEPS if h[s]}


def plan_row_group(inst):
    """capture/staging group a plan macro row belongs to (pmem / pvq / land / stage), else None"""
    m = RE_ROW.search(inst)
    if not m:
        return None
    return m.group(1) or 'stage'


def ghost_rows(rows, steps):
    """plan content rows (dicts with 'inst') of a closure group whose step does not apply"""
    return [r for r in rows if plan_row_group(r.get('inst', '')) not in (None, *steps)]


def one(rx, text, what):
    hits = re.findall(rx, text, re.M)
    if len(hits) != 1:
        raise ConeError(f'{what}: {len(hits)} matches')
    return hits[0]


def att_prefix(source):
    """generate prefix G of the attention unit (g_u_rsv_NN_u_u_att_, ..._u_a_, g_u_rsv_u_att_u_a_) from the single
    native PMEM instance"""
    return one(r'^\s*' + HELPER['pmem'] + r' (g_u_rsv\w*?_att_(?:u_a_)?)pmem \(', source, 'pmem instance')


def stage_prefix(source):
    """instance prefix of the two stage2 staging instances (u_<att unit>u_eng_)"""
    pre = one(r'^\s*' + re.escape(STAGE) + r'(u_\w+?_)g_stage2_u_stage0 \(', source, 'stage2 instance 0')
    return pre


def stage_struct(source):
    pre = stage_prefix(source)
    for i in range(2):
        row = STAGE + pre + 'g_stage2_u_stage%d (' % i
        if source.count(row) != 1:
            raise ConeError('stage2 instance %d: %d matches' % (i, source.count(row)))
        source = source.replace(row, row.replace('attn_staging', 'attn_staging_fit').replace("1'b0", "1'b1"), 1)
    if re.search(r'^\s*' + re.escape(STAGE), source, re.M):
        raise ConeError('a behavioural staging instance is left')
    return source


def pmem_struct(source):
    """native PMEM + payload / skid cone -> ot_t7_pmem_capture_v2 (witness of the hi4 t4_att fit, names derived)"""
    G = att_prefix(source)
    P, E = 'w_' + G[2:], 'w_' + G[2:] + 'u_eng_'
    PM = HELPER['pmem']
    pm = P + 'pmem_RD_DATA'
    lines = [x for x in source.splitlines() if x.lstrip().startswith(PM + ' ' + G + 'pmem (')]
    if len(lines) != 1:
        raise ConeError('pmem instance line: %d' % len(lines))
    line = lines[0]
    ports = dict(re.findall(r'\.(\w+)\((.*?)\)(?=,|\);)', line))
    if set(ports) != {'RD_ADDR', 'RD_DATA', 'WR_ADDR', 'WR_CLK', 'WR_DATA', 'WR_EN'}:
        raise ConeError('pmem ports %s' % sorted(ports))
    m = re.fullmatch(r'\{' + re.escape(P) + r'driver_pr_Q\[8:0\], (' + re.escape(P) + r'src_\w+_Y)\[8:0\]\}', ports['RD_ADDR'])
    pr = P + 'driver_pr_Q[8:0]'
    ok = (m and ports['RD_DATA'] == pm and ports['WR_ADDR'] == P + 'driver_pw_Q[8:0]' and ports['WR_CLK'] == 'clk'
          and re.fullmatch(r'w_u_rsv_\w*?src_\w+_Q\[511:0\]', ports['WR_DATA'])
          and re.fullmatch(re.escape(P) + r'src_\w+_Y\[511:0\]', ports['WR_EN']))
    if not ok:
        raise ConeError('pmem port map differs from the witness: %r' % ports)
    inc = m[1]
    if source.count(f"assign {inc} = {pr} + 9'b000000001;") != 1:
        raise ConeError('pmem read address increment')
    packed, owner, second = one(r'^\s*assign (' + re.escape(P) + r'src_\w+_Y) = (\S+)\[0\] \? \{(' + re.escape(P)
                                + r'src_\w+_Y)\[511:0\], ' + re.escape(pm) + r"\[1023:512\]\} : \{1024\{1'b0\}\};", source, 'packed')
    if len(re.findall(re.escape(pm) + r'\[1023:512\]', source)) != 1:
        raise ConeError('pmem upper half has another reader')
    phase2 = one(r'^\s*assign ' + re.escape(second) + r' = (' + re.escape(P) + r'src_\w+_Y)\[0\] \? ' + re.escape(pm)
                 + r"\[511:0\] : \{512\{1'b1\}\};", source, 'second')
    phase = one(r'^\s*assign ' + re.escape(phase2) + r" = (\S+_Y)\[1:0\] == 2'b10;", source, 'phase2') + '[1:0]'
    payload = one(r'^\s*assign (\S+_Y) = ' + re.escape(packed) + r'\[1023:0\];', source, 'payload')
    owner = owner + '[0]'
    wp = E + 'driver_g_pskid_wp_Q[0]'
    sk = [E + f'driver_g_pskid_sk{i}_Q' for i in range(2)]
    skreg = [G + f'u_eng_driver_g_pskid_sk{i}_q' for i in range(2)]
    mux = [one(r'^\s*always @\(posedge clk\) ' + re.escape(skreg[i]) + r' <= (\S+_Y)\[1023:0\];', source, f'skid{i} reg')
           for i in range(2)]
    sel = [one(r'^\s*assign ' + re.escape(mux[i]) + r' = (\S+_Y)\[0\] \? ' + re.escape(payload) + r'\[1023:0\] : '
               + re.escape(sk[i]) + r'\[1023:0\];', source, f'mux{i}') for i in range(2)]
    push = one(r'^\s*assign ' + re.escape(sel[1]) + r' = (\S+_Y\[0\]) && ' + re.escape(wp) + r';', source, 'select1')
    not_wptr = one(r'^\s*assign ' + re.escape(sel[0]) + r' = ' + re.escape(push) + r' && (\S+_Y)\[0\];', source, 'select0')
    if source.count(f'assign {not_wptr} = !{wp};') != 1:
        raise ConeError('select0 inverter')
    for i in range(2):                                   # each skid reg: its declaration, one always, one output assign
        got = {re.sub(r'\s*//.*$', '', l.strip()) for l in source.splitlines() if re.search(r'\b' + re.escape(skreg[i]) + r'\b', l)}
        n = sum(1 for l in source.splitlines() if re.search(r'\b' + re.escape(skreg[i]) + r'\b', l))
        want = {f'always @(posedge clk) {skreg[i]} <= {mux[i]}[1023:0];', f'assign {sk[i]} = {skreg[i]};',
                f'reg [1023:0] {skreg[i]};'}
        if n != 3 or got != want:
            raise ConeError(f'skid reg {skreg[i]} references differ: {sorted(got)}')
    cut = {pm, payload, packed, second, mux[0], mux[1], *skreg}
    remove = re.compile(r'(^\s*(?:wire|assign) (?:\[.*?\] )?(?:' + '|'.join(re.escape(x) for x in cut - set(skreg))
                        + r')\b)|\b(?:' + '|'.join(re.escape(x) for x in skreg) + r')\b', re.M)
    retained = '\n'.join(l for l in source.splitlines() if not remove.search(l))
    for n in cut - {pm}:
        if re.search(r'\b' + re.escape(n) + r'\b', retained):
            raise ConeError(f'{n} has a reader outside the pmem cone')
    child = '\n'.join([
        f'    ot_t7_pmem_capture_v2 {G}pmem_capture (',
        f"        .clk(clk), .pr({pr}), .wa({ports['WR_ADDR']}),",
        f'        .pstep({phase}), .owner({owner}), .push({push}), .wp({wp}),',
        f"        .wd({ports['WR_DATA']}), .wm({ports['WR_EN']}),",
        f'        .slot0({sk[0]}[1023:0]), .slot1({sk[1]}[1023:0]));',
    ])
    seed = retained.replace(line, child, 1) + '\n'
    if PM + ' ' + G in seed or pm in seed or len(re.findall(r'\bot_t7_pmem_capture_v2\b', seed)) != 1:
        raise ConeError('pmem cut left native state')
    return seed


def close_struct(bound_text):
    """(closed text, steps applied, report) for a non-class-shape bound; ConeError on any witness difference"""
    h = helpers(bound_text)
    steps, s = [], bound_text
    if h['stage']:
        s = stage_struct(s); steps.append('stage')
    if h['pmem']:
        s = pmem_struct(s); steps.append('pmem')
    if not steps:
        raise ConeError('no structural step applies')
    if bound_text.split(');', 1)[0] != s.split(');', 1)[0]:
        raise ConeError('module header changed')
    native = {k: v for k, v in h.items() if k not in steps and v}
    return s, steps, dict(helpers=h, steps=steps, left_native=native)


def derive_rows(plan_raw, rows_by_type):
    """drop the ghost capture/staging rows of each type given {type: steps}; returns {type: [dropped inst]}"""
    dropped = {}
    for tn, steps in rows_by_type.items():
        t = plan_raw['partition_types'][tn]
        ghosts = ghost_rows(t.get('contents', []), steps)
        ids = {id(r) for r in ghosts}
        t['contents'] = [r for r in t.get('contents', []) if id(r) not in ids]
        dropped[tn] = [r['inst'] for r in ghosts]
    return dropped


def main(argv=None):
    import argparse, json, sys
    from pathlib import Path
    ap = argparse.ArgumentParser(description='derive the svc capture/staging plan rows from the closure steps of each bound')
    ap.add_argument('--plan', required=True)
    ap.add_argument('--bound', nargs=2, action='append', metavar=('TYPE', 'BOUND_SV'), required=True)
    ap.add_argument('--out', help='plan with the ghost rows dropped (default: report only)')
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    want = {tn: predict_steps(Path(b).read_text()) for tn, b in a.bound}
    dropped = derive_rows(raw, want)
    for tn in want:
        print('S81_SVC_ROWS', tn, 'steps=' + ','.join(sorted(want[tn])), 'dropped=%d' % len(dropped[tn]))
    if a.out:
        if Path(a.out).exists(): sys.exit('refusing existing ' + a.out)
        Path(a.out).write_text(json.dumps(raw, separators=(',', ':')) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
