#!/usr/bin/env python3
"""Prepare the owned UNAPPLIED T7 LAND data cut from an exact approved preimage (original, PMEM, PVQ-only, PMEM+PVQ).

Removes the native 640x256 land helper instance (4c805) and the 1060-bit ekv_w capture register (src_2be8), zeroes the
now-unobserved fields of the 2158-bit struct wire 711_Y (only [3:0] -> ekv_m capture and [1067:1064] -> rel_bad are
read), deletes the resulting dead wire/assign/combinational-cell cone, and instantiates ot_t7_land_capture_candidate
driving the unchanged src_2be8 Q wire.  Every other line is byte-identical and in order.
"""
from pathlib import Path
import re, json, hashlib, argparse, difflib, shutil
ALLOWED = {
    '61c902f184b49e231c34de041d0f1832a4117749592f81fa3bf42d6ff4df504a': 'original_T7',
    '04a554300de8e3c87737a889aa4462dece93e4f5221c77ce98b04913cea94544': 'PMEM_data_cut',
    'a288687b6953a879105bcfb4fe9011fc099707e28cfa4d3559f7069c11b9e28b': 'PVQ_only_data_cut',
    '00bd1321a8290e742fd010b2f45cccab86b3ea94fdfeebf5c8c135d60d00f3a2': 'PMEM_PVQ_joint_data_cut',
}
P = 'w_u_rsv_14_u_u_att_'
LAND = 'ot_bind_native_4c805a5536bda0930879099e g_u_rsv_14_u_u_att_land ('
G = 'g_u_rsv_14_u_u_att_src_2be8fdcd9643c0eb235e_q'
Q = P + 'src_2be8fdcd9643c0eb235e_Q'
S = P + '711_Y'
# per-lane facts in the parent (lane j = row 4*(rc-1)+j): valid row<tjob, win row<wcount, need, scale byte
VALID = ['558', '597', '636', '675']; WIN = ['580', '619', '658', '697']
NEED = ['567', '606', '645', '684'];  SCALE = ['583', '622', '661', '700']
LANE_WORD = ['procmux_69594', 'procmux_69568', 'procmux_69538', 'procmux_69508']
KC_M = ['procmux_69597', 'procmux_69572', 'procmux_69542', 'procmux_69512']
REL = ['procmux_69591', 'procmux_69564', 'procmux_69534', 'procmux_69504']


def sha(s): return hashlib.sha256(s.encode()).hexdigest()
def header(s): return s[s.index('module '):s.index(');', s.index('module ')) + 2]
def w(n): return P + n + '_Y'


def struct_fields():
    hi = [P + 'procmux_69496_Y[0]', P + 'procmux_69500_Y[0]', P + '674_Y[31:0]', "32'b" + format(4, '032b'),
          P + 'land_RD_DATA[255:0]', P + 'land_RD_DATA[511:256]', P + 'land_RD_DATA[767:512]', P + 'land_RD_DATA[1023:768]']
    rel = [w(n) + '[0]' for n in REL[::-1]]
    kcw = [w(n) + '[264:0]' for n in reversed(LANE_WORD)]
    kcm = [w(n) + '[0]' for n in KC_M[::-1]]
    return hi, rel, kcw, kcm


def transform(s):
    h = sha(s)
    if h not in ALLOWED: raise ValueError('unapproved preimage hash')
    lines = s.splitlines()
    inst = [l for l in lines if LAND in l]
    if len(inst) != 1: raise ValueError('land instance count')
    ports = dict(re.findall(r'\.(\w+)\((.*?)\)(?=, \.|\);)', inst[0]))
    want_ra = '{' + ', '.join(w(n) + '[31:0]' for n in ['552', '547', '542', '537']) + '}'
    if ports.get('RD_ADDR') != want_ra or ports.get('RD_DATA') != P + 'land_RD_DATA' or \
       ports.get('WR_CLK') != '{' + ', '.join(['clk'] * 7) + '}' or set(ports) != {'RD_ADDR', 'RD_DATA', 'WR_ADDR', 'WR_CLK', 'WR_DATA', 'WR_EN'}:
        raise ValueError('land port identity')
    for n, k in ((537, 0), (542, 1), (547, 2), (552, 3)):
        pass  # address wires are checked structurally by the native gate's 4*(rc-1)+j form; they die with the instance
    cap = [l for l in lines if re.search(r'\b' + G + r'\b', l)]
    if len(cap) != 3 or not any('always @(posedge clk)' in l and '<= ' + S + '[1063:4];' in l for l in cap):
        raise ValueError('capture identity')
    # struct wire: exact field list, exactly three readers ([3:0], [1063:4], [1067:1064])
    sl = [l for l in lines if l.lstrip().startswith('assign ' + S + ' = ')]
    if len(sl) != 1: raise ValueError('struct assign count')
    hi, rel, kcw, kcm = struct_fields()
    body = sl[0].split(' = ', 1)[1].split(';', 1)[0]
    if body != '{' + ', '.join(hi + rel + kcw + kcm) + '}': raise ValueError('struct field identity')
    readers = [l for l in lines if re.search(r'\b' + S + r'\b', l) and l is not sl[0] and l.strip() != 'wire [2157:0] ' + S + ';']
    rd = sorted(re.findall(re.escape(S) + r'\[(\d+:\d+)\]', '\n'.join(readers)))
    if rd != ['1063:4', '1067:1064', '3:0']: raise ValueError('struct readers %r' % rd)
    # lane word / fact wire identities (lane j reads RD_DATA[256j+255:256j], scale from wsc shifter)
    A = {}
    for l in lines:
        m = re.match(r'\s*assign (\w+) = (.*);', l)
        if m: A[m[1]] = m[2]
    # exact native-composition identity per lane: the original lane word is the rowword/kc_w form the native gate
    # models, read at RD_ADDR lane j = 4*(rc-1)+j, with valid/win taken on that same row
    def row_of(n):
        m = re.fullmatch(r'(\w+)\[31:0\] \+ (?:\{32\{1\'b0\}\}|32\'b([01]{32}))', A.get(n, ''))
        if not m: return None
        k = int(m[2], 2) if m[2] else 0
        m2 = re.fullmatch(r"32'b0{29}100 \* (\w+)\[31:0\]", A.get(m[1], ''))
        if not m2 or A.get(m2[1]) != "{{22{1'b0}}, " + P + "driver_rc_Q[9:0]} - 32'b" + '0' * 31 + '1': return None
        return k
    RD = P + 'land_RD_DATA'
    z120 = '0' * 120; z264 = '0' * 264
    for j, ra in enumerate(['537', '542', '547', '552']):
        if row_of(w(ra)) != j: raise ValueError('RD_ADDR lane %d' % j)
        lw = A.get(w(LANE_WORD[j]), '')
        m = re.fullmatch(re.escape(w(VALID[j])) + r"\[0\] \? (\w+)\[264:0\] : \{265\{1'b0\}\}", lw)
        if not m: raise ValueError('lane word %d' % j)
        m = re.fullmatch(re.escape(w(VALID[j])) + r"\[0\] \? (\w+)\[264:0\] : \{265\{1'bx\}\}", A.get(m[1], ''))
        if not m: raise ValueError('lane valid mux %d' % j)
        m = re.fullmatch(re.escape(w(WIN[j])) + r"\[0\] \? \{1'b0, " + re.escape(w(SCALE[j])) + r"\[7:0\], " + re.escape(RD) +
                         r"\[%d:%d\]\} : (\w+)\[264:0\]" % (256 * j + 255, 256 * j), A.get(m[1], ''))
        if not m: raise ValueError('lane rowword %d' % j)
        if A.get(m[1]) != w(NEED[j]) + "[0] ? {121'b1" + z120 + ', ' + RD + '[%d:%d]} : 265\'b1' % (256 * j + 143, 256 * j) + z264:
            raise ValueError('lane compressed %d' % j)
        mv = re.fullmatch(r"(\w+)\[31:0\] < \{\{22\{1'b0\}\}, " + re.escape(P) + r"60_Y\[9:0\]\}", A.get(w(VALID[j]), ''))
        mw = re.fullmatch(r"(\w+)\[31:0\] < \{\{24\{1'b0\}\}, " + re.escape(P) + r"driver_wcount_Q\[7:0\]\}", A.get(w(WIN[j]), ''))
        if not mv or not mw or mv[1] != mw[1] or row_of(mv[1]) != j: raise ValueError('lane facts row %d' % j)
    for j in range(4):
        m = re.search(r'\? \{1\'b0, ' + re.escape(w(SCALE[j])) + r'\[7:0\], ' + re.escape(P) + r'land_RD_DATA\[(\d+):(\d+)\]\} : ', '\n'.join(A.values()))
        if not m or (int(m[1]), int(m[2])) != (256 * j + 255, 256 * j): raise ValueError('lane %d scale/data identity' % j)
        if not A.get(w(WIN[j]), '').endswith("< {{24{1'b0}}, " + P + 'driver_wcount_Q[7:0]}'): raise ValueError('win %d' % j)
        if not A.get(w(VALID[j]), '').endswith("< {{22{1'b0}}, " + P + '60_Y[9:0]}'): raise ValueError('valid %d' % j)
        if not A.get(w(NEED[j]), '').endswith(' || ' + P + 'src_a5fb9f49b45eea02433e_Q[0]'): raise ValueError('need %d' % j)
    new_struct = sl[0].replace(body, '{' + "{1090{1'b0}}, " + ', '.join(rel) + ", {1060{1'b0}}, " + ', '.join(kcm) + '}')
    new_struct = new_struct.replace('assign ', 'assign /* LAND-cut: unobserved fields zeroed */ ', 1)
    # dead-cone deletion over declared wires driven by one assign or one single-output combinational native cell
    drv = {}; decl = {}
    for l in lines:
        m = re.match(r'\s*assign (\w+) = ', l)
        if m and m[1] != S: drv.setdefault(m[1], []).append(l)
        m = re.match(r'\s*ot_bind_native_\w+ g_\w+ \((?:\.[ABS]\([^()]*(?:\([^()]*\))?[^()]*\), )+\.Y\((\w+)\)\);\s*$', l)
        if m: drv.setdefault(m[1], []).append(l)
        m = re.match(r'\s*wire (?:\[[^]]+\] )?(\w+);\s*$', l)
        if m: decl[m[1]] = l
    wr = lambda n: w(n) + '[0]'
    child = ['    // UNAPPLIED LAND data-cut (TOK-DS-3): queue/control/ekv_m/rel_bad/reset lines retained.',
             '    ot_t7_land_capture_candidate g_u_rsv_14_u_u_att_land_capture (',
             '        .clk(clk), .WR_ADDR(' + ports['WR_ADDR'] + '),',
             '        .WR_DATA(' + ports['WR_DATA'] + '),',
             '        .WR_EN(' + ports['WR_EN'] + '),',
             '        .rc(' + P + 'driver_rc_Q[9:0]),',
             '        .valid({' + ', '.join(wr(n) for n in VALID[::-1]) + '}),',
             '        .win({' + ', '.join(wr(n) for n in WIN[::-1]) + '}),',
             '        .need({' + ', '.join(wr(n) for n in NEED[::-1]) + '}),',
             '        .scale({' + ', '.join(w(n) + '[7:0]' for n in SCALE[::-1]) + '}),',
             '        .q(' + Q + '[1059:0]));']
    remove = set(cap + inst); mod = {sl[0]: new_struct}
    def text_without(rm):
        return '\n'.join(mod.get(l, l) for l in lines if l not in rm) + '\n' + '\n'.join(child)
    # restrict deletion to the backward cone of what the cut stops reading: the land instance inputs and the
    # zeroed struct fields (pre-existing dead logic elsewhere stays byte-identical)
    roots = set(re.findall(r'\bw_\w+\b', inst[0])) | set(re.findall(r'\bw_\w+\b', ', '.join(hi + kcw)))
    cone = set(); stack = list(roots)
    while stack:
        n = stack.pop()
        if n in cone: continue
        cone.add(n)
        for x in drv.get(n, []): stack.extend(t for t in re.findall(r'\bw_\w+\b', x) if t != n)
    cur = text_without(remove)
    while True:
        progress = False
        toks = {}
        for t in re.findall(r'\bw_\w+\b', cur): toks[t] = toks.get(t, 0) + 1
        for n, d in decl.items():
            if d in remove or n == Q or n not in cone or len(drv.get(n, [])) > 1: continue
            own = [d] + [x for x in drv.get(n, []) if x not in remove]
            if n not in drv and n != P + 'land_RD_DATA': continue   # only the removed instance's output may be driverless
            cnt = sum(len(re.findall(r'\b' + n + r'\b', mod.get(x, x))) for x in own)
            if toks.get(n, 0) == cnt:
                remove.update(own); progress = True
        if not progress: break
        cur = text_without(remove)
    out = []
    for l in lines:
        if l == inst[0]: out.extend(child)
        elif l not in remove: out.append(mod.get(l, l))
    new = '\n'.join(out) + '\n'
    assert header(new) == header(s)
    assert G not in new and 'ot_bind_native_4c805a5536bda0930879099e' not in new and P + 'land_RD_DATA' not in new
    for n in VALID + WIN + NEED + SCALE + KC_M + REL: assert re.search(r'\bwire (\[[^]]+\] )?' + w(n) + ';', new), n
    for n in LANE_WORD: assert w(n) not in new, n
    assert all(l in new for l in lines if l not in remove and l not in mod)
    return new, [l for l in lines if l in remove], h


def prepare(parent, out):
    if out.exists(): raise FileExistsError('fresh owned output required')
    s = parent.read_text(); new, removed, h = transform(s); out.mkdir(parents=True)
    name = 's81p_svc_lo_dsdv_svc_rs__t7_bound.sv'
    (out / name).write_text(new)
    shutil.copyfile(Path(__file__).parent / 'ot_t7_land_capture_candidate.sv', out / 'ot_t7_land_capture_candidate.sv')
    (out / 'bound_cut.patch').write_text(''.join(difflib.unified_diff(s.splitlines(True), new.splitlines(True), fromfile='before/' + name, tofile='UNAPPLIED/' + name)))
    nff = sum(1 for l in removed if 'always @(posedge' in l)
    r = dict(status='UNAPPLIED_OWN_SOURCE', preimage=ALLOWED[h], before_sha256=h, after_sha256=sha(new),
             removed_line_count=len(removed), removed_capture_always=nff, modified_lines=1,
             removed_lines=removed, original_capture_FF_removed=1060, new_LVT_FF=1280, new_metadata_FF=40,
             external_FF_delta=260, macro_clock_delta=12, reset_load_delta=0, cycle_delta=0,
             top_header_identical=True, all_other_original_lines_identical_in_order=True,
             native_component_gate='results/rtl/s81_T7_LAND_native_candidate_1102')
    (out / 'transform.json').write_text(json.dumps(r, indent=2) + '\n'); return r


if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('--parent', type=Path, required=True); a.add_argument('--out', type=Path, required=True)
    x = a.parse_args(); r = prepare(x.parent, x.out); r.pop('removed_lines'); print(json.dumps(r, indent=2))
