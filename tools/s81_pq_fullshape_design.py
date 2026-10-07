#!/usr/bin/env python3
"""S81 production PQ full-shape partition: executable sizing and contracts (Claude design, 2026-10-07).

Design (README beside the results): the native R128 PQ parent is NOT one block. It splits into
  * 128 ot_v41_ret_root (ROOTD = QD = 128) placed one per region in the frame's empty q position, in the column clock;
  * 12 return write-back slices (RWB, one per tier-half: 10/11 regions) at the return end blocks, i.e. the stream-domain
    sp_gather slab directly south of the VM;
  * one PQ core (issuer, ROM adapters, loader + actquant, x-buffers in 36 1R1W SRAM macros, reader / streamer, lane
    encoder) at the VM north face;
  * a union x lane (q beat and BF beat overlaid: never valid together) instead of the native 1,633-bit packed bus.
Everything below is derived from the pinned RTL text, the Codex inventory snapshot, the macro index and the die generator
geometry extract; quantities that are estimates say so (ESTIMATES) and are never used as closure evidence.

Asserted invariants (fail closed): native field widths from the spine RTL; union / serial lane layouts carry every native
field of the valid family once and untruncated; the return lane carries the root's rounded word unchanged; root and PQ
storage bits equal the inventories; the SRAM maps of bb / qb are bijective and conflict-free for every read group and
write block at KMAX 6144; per-block pin counts sum to the native port total plus explicit new interfaces.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/uarch/dsrom_s81_pq_fullshape_design_20261007'
# Portable pinned copies of Codex's read-only snapshot pq_snapshot_1117 (uncommitted upstream until the owner's gate);
# inputs/SHA256SUMS covers them, inputs/REPO_INPUTS.SHA256SUMS every repo file this tool reads. Both fail closed.
SNAP = OUT / 'inputs'
SNAP_SHA = {'pq_parent_binding.py': 'b2d619a4008cd00cea21a85cbf89749fc3c952f4d5b503fcc6359f6062a2f7a4',
            'dsrom_s81_pq_parent_20261007/full_inventory.json':
                '614fcd263803be179b263d17cb77f061b711db60140c5407b0827a8ce7d87874',
            'dsrom_s81_pq_parent_20261007/half_inventory.json':
                '4b38ddb16ea9e633a8306d2bcc28320e214788f63419ee7425f0307d69ca2248'}
SPINE = ROOT / 'rtl/v41die/ot_v41_spine_pqc_w17w10.sv'
RET = ROOT / 'rtl/v41rom/ot_v41_ret.sv'
MACROS = ROOT / 'physical/asap7_memory_macros_v2/index.json'
GEOM = OUT / 'geometry_extract.json'
GEN = OUT / 'inputs/pinned/tools/dsrom_s81_fulldie.py'   # exact generator of GEOM (main's copy drifts)
REPO_SUMS = OUT / 'inputs/REPO_INPUTS.SHA256SUMS'
SENS = ROOT / 'results/uarch/dsrom_spine_return_station_20261007/sensitivity.json'
RSTORE = ROOT / 'results/uarch/dsrom_return_storage_hbm_20261003/model.json'
MAP = ROOT / 'results/uarch/dsrom_s81_mixed1792_mapping_20261007'

R, ROOTD, QD = 128, 128, 128
CLK_PS = 1e6 / 1200.0
CC_REACH_UM = 215.0            # r9 common-clock hop cap (geometry options --cc-reach-um 215)
PIN_DENSITY = 564 / 172.8      # pins per um of face: the r8 slot station carries the 564-b stream on a 172.8 um face
FINAL_SEG_UM = 100.0           # owner directive 9: final die-wire segment to a block pin
UTIL = 0.575                   # owner directive 11: 55-60 % placement utilisation
ESTIMATES = {   # NOT evidence: replaced by synthesis / route reports when the blocks are screened
    'root_logic_cell_um2': (3500.0, 'CAM 128x27b compare + 2 priority encoders + queue head + bd[hit] 128:1 muxes + '
                                    'ot_fp32_add_rne_pipe + norm/parent/RNE; mux2 ~0.1 um2 per input'),
    'core_logic_cell_um2': (60000.0, 'issuer/accept, ROM adapters, loader + 2 ot_hdc_actquant + BF16 rounders, reader '
                                     'FIFO, streamer, beat assembly; Codex R128 screen 148,012 um2 total minus screen '
                                     'state and its return side; REQUEST hierarchical cell area of that screen'),
    'rwb_logic_cell_um2_per_region': (380.0, 'q1..q3 base+row, pos*stride select, format select, KS adders (3 x 19 b)'),
    'vm_cdc_latency_cycles': (4, 'serial_0p9 <-> stream_1p2 ot_ratio_cdc_fifo synchroniser + output register; the CDC '
                                 'owner supplies the measured value'),
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------ sources
def verify_repo_inputs():
    for line in REPO_SUMS.read_text().splitlines():
        h, rel = line.split(None, 1)
        if sha(ROOT / rel) != h:
            raise SystemExit(f'repo input hash mismatch: {rel}')


SNAP_PATHS = None   # current basis: {snapshot key: committed main path}, same SNAP_SHA hashes


def load_snapshot(snap):
    if SNAP_PATHS is None:
        for line in (snap / 'SHA256SUMS').read_text().splitlines():
            h, rel = line.split(None, 1)
            if SNAP_SHA.get(rel) != h:
                raise SystemExit(f'SHA256SUMS disagrees with the pinned snapshot hash: {rel}')
    at = (lambda rel: snap / rel) if SNAP_PATHS is None else (lambda rel: SNAP_PATHS[rel])
    for rel, h in SNAP_SHA.items():
        if sha(at(rel)) != h:
            raise SystemExit(f'snapshot hash mismatch: {rel}')
    spec = importlib.util.spec_from_file_location('pq_parent_binding_snapshot', at('pq_parent_binding.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    inv = {k: json.loads(at(f'dsrom_s81_pq_parent_20261007/{k}_inventory.json').read_text()) for k in ('half', 'full')}
    return mod, inv


def decl_widths(text, env):
    """{name: (width, depth)} for reg/wire declarations `reg [A:0] a [0:D-1], b;`"""
    out = {}
    for m in re.finditer(r'^\s*(?:reg|wire)\s+(?:signed\s+)?(?:\[([^\]]+):0\]\s+)?([^;]+);', text, re.M):
        try:
            w = eval(m[1], {}, env) + 1 if m[1] else 1
        except NameError:
            continue
        for item in m[2].split(','):
            item = item.strip()
            mm = re.match(r'(\w+)\s*(?:\[0:([^\]]+)\])?\s*(?:=.*)?$', item)
            if mm:
                try:
                    d = eval(mm[2], {}, env) + 1 if mm[2] else 1
                except NameError:
                    continue
                out.setdefault(mm[1], (w, d))
    return out


def native_bus(phw):
    t = SPINE.read_text()
    bw = re.search(r'parameter integer BW = ([^\n]+)', t)[1]
    BW = eval(bw.split('//')[0].strip().rstrip(')'), {}, dict(PHW=phw))
    src = re.search(r'wire \[BW-1:0\] bc_in = \{([^}]*)\};', t, re.S)[1]
    if src.replace(' ', '') == 'bc_hr,bt_d':      # v11+: non-BF fields registered once more (bc_hr <= bc_h), then bt_d
        src = re.search(r'wire \[BW-1025:0\] bc_h = \{([^}]*)\};', t, re.S)[1] + ', bt_d'
    dst = re.search(r'assign \{(f_cfg_go[^}]*)\} = bc;', t, re.S)[1]
    src = [s.strip() for s in src.split(',')]
    dst = [s.strip() for s in dst.split(',')]
    assert len(src) == len(dst)
    w = decl_widths(t, dict(PHW=phw, KMAX=6144, NBLK=192))
    fields = [dict(port=d, reg=s, bits=w[s][0]) for s, d in zip(src, dst)]
    assert sum(f['bits'] for f in fields) == BW == 1624 + phw, (BW, sum(f['bits'] for f in fields))
    fam = lambda p: ('cfg' if p.startswith('f_cfg') else 'go' if p.startswith('f_go') else
                     'q' if p.startswith('f_xs') else 'bf')
    for f in fields:
        f['family'] = fam(f['port'])
    # mutual exclusion of the two beat families: one streamer head, family bit selects xs or xb valid
    assert re.search(r'p1_xs_v <= (s_adv\w*) && hw\[0\] && !h_fam;', t) and re.search(r'p1_xb_v <= s_adv\w* && hw\[0\] && h_fam;', t)
    return BW, fields, t


def lane_layouts(fields, phw):
    """native / union (W2) / serial-union (W3) layouts, bit offsets, and the no-truncation checks."""
    regs = {}
    for f in fields:
        regs.setdefault(f['reg'], []).append(f)
    shared = [r for r, fs in regs.items() if len({f['family'] for f in fs}) > 1]
    always = [f for f in fields if f['family'] in ('cfg', 'go')]
    q_only = [f for f in fields if f['family'] == 'q' and f['reg'] not in shared]
    b_only = [f for f in fields if f['family'] == 'bf' and f['reg'] not in shared]
    sh = [regs[r][0] for r in shared]
    def lay(items, base=0):
        out, o = [], base
        for f in items:
            out.append(dict(field=f['port'] if f['reg'] not in shared else f['reg'], reg=f['reg'], lsb=o,
                            msb=o + f['bits'] - 1, bits=f['bits']))
            o += f['bits']
        return out, o
    fixed, o = lay(always + sh)
    qv = q_only[0]; bv = next(f for f in b_only if f['port'] == 'f_xb_v')
    assert qv['port'] == 'f_xs_v' and qv['bits'] == 1 == bv['bits']
    fixed += [dict(field='f_xs_v', reg='bt_xs_v', lsb=o, msb=o, bits=1), dict(field='f_xb_v', reg='bt_xb_v', lsb=o + 1,
              msb=o + 1, bits=1)]
    o += 2
    qp = [f for f in q_only if f['port'] != 'f_xs_v']
    bp = [f for f in b_only if f['port'] != 'f_xb_v']
    qlay, qend = lay(qp, o)
    blay, bend = lay(bp, o)
    union_w = max(qend, bend)
    # W3: the BF payload in two halves over two cycles; half bit + max(q payload, ceil(bf payload / 2))
    bf_pay = sum(f['bits'] for f in bp)
    half = math.ceil(bf_pay / 2)
    w3 = o + 1 + max(sum(f['bits'] for f in qp), half)
    # checks: every native field once per family, widths untruncated
    for fam, lay_ in (('q', qlay), ('bf', blay)):
        got = {x['field']: x['bits'] for x in fixed + lay_}
        for f in fields:
            if f['family'] in (fam, 'cfg', 'go'):
                key = f['reg'] if f['reg'] in shared else f['port']
                assert got[key] == f['bits'], (fam, key)
    assert sum(f['bits'] for f in fields) - sum(regs[r][0]['bits'] for r in shared) == \
        o + sum(f['bits'] for f in qp) + sum(f['bits'] for f in bp)
    return dict(
        native=dict(bits=sum(f['bits'] for f in fields), distinct_register_bits=sum(f['bits'] for f in fields)
                    - sum(regs[r][0]['bits'] for r in shared),
                    duplicated_registers={r: [f['port'] for f in regs[r]] for r in shared}),
        union_W2=dict(bits=union_w, fixed=fixed, q_overlay=qlay, bf_overlay=blay,
                      q_slot_bits=qend, bf_slot_bits=bend,
                      rule='q payload and BF payload overlay the same wires; f_xs_v / f_xb_v are never both 1 '
                           '(one streamer head, family bit); cfg/go/shared pos,b always present'),
        serial_W3=dict(bits=w3, bf_payload_bits=bf_pay, bf_half_bits=half,
                       rule='W2 with the BF payload in two halves (half bit); a BF beat occupies two lane cycles; '
                            'BF-slot deserialiser (half register + enable) presents the full beat; needs BF beat '
                            'spacing >= 2 in the stream'),
        legacy_lane=dict(bits=564, fields='x0 283 (q0 e0 + 17 ctl) | x1 266 (q1 e1) | cc 15 (go cfg_go cfg_ph[10] '
                                         'cfg_np[3])', source='tools/dsrom_s81_fulldie.py X0B/X1B/CCB'))


def root_inventory():
    t = RET.read_text()
    body = t[t.index('module ot_v41_ret_root'):]
    w = decl_widths(body, dict(QD=QD, D=ROOTD, QW=7))
    q = sum(w[n][0] for n in ('qt', 'qd', 'qe'))
    b = sum(w[n][0] for n in ('bv', 'bt', 'bd', 'be'))
    assert w['qt'][1] == QD and w['bt'][1] == ROOTD
    bits = QD * q + ROOTD * b
    hdr = body[:body.index(');')]
    outs = {m[2]: (eval(m[1]) + 1 if m[1] else 1) for m in re.finditer(r'output reg\s+(?:\[(\d+):0\]\s+)?(\w+)', hdr)}
    ins = {m[2]: (eval(m[1]) + 1 if m[1] else 1) for m in re.finditer(r'input\s+wire\s+(?:\[(\d+):0\]\s+)?(\w+)', hdr)}
    payload_out = sum(v for k, v in outs.items() if k != 'fault')
    raw_in = sum(v for k, v in ins.items() if k not in ('clk', 'rst_n'))
    rne = 'wire [32:0] rb = {1\'b0, cd} + 33\'h7FFF + {32\'d0, cd[16]};'
    assert rne in body, 'root RNE rounding line changed: re-derive the return contract'
    assert (payload_out, raw_in) == (69, 66), (payload_out, raw_in)
    return dict(queue_entry_bits=q, buffer_entry_bits=b, bits_per_root=bits, roots=R, bits_total=bits * R,
                raw_in_bits=raw_in, out_payload_bits=payload_out, out_fields=outs,
                rounding='BF16 RNE inside the root (rb = fp32 + 0x7FFF + lsb); RWB passes r_fp32 / r_bf16 unchanged and '
                         'selects by the op format exactly as the spine return stage; no other rounding site')


def pq_storage(kmax):
    t = SPINE.read_text()
    nblk = kmax // 32
    w = decl_widths(t, dict(PHW=9, KMAX=kmax, NBLK=nblk, BAW=math.ceil(math.log2(nblk))))
    s = {n: w[n][0] * w[n][1] for n in ('qb', 'eb', 'bb')}
    return dict(KMAX=kmax, NBLK=nblk, arrays={n: dict(width=w[n][0], depth=w[n][1], bits=s[n]) for n in s},
                bits=sum(s.values()))


# ------------------------------------------------------------------------------------------------ SRAM maps
def sram_maps(kmax, macro):
    """bb: 4 read-group replicas x 8 bank-pair macros (256 b = 2 lanes x 8 subs x 16 b, row = hi);
    qb: 4 banks by (index bit 3, bit 0), row = (i >> 4) * 4 + ((i >> 1) & 3).  Exhaustive bijection / conflict checks."""
    words, width = macro['words'], macro['bits']
    nbb, nblk = 2 * kmax, kmax // 32
    # bb
    seen = {}
    for i in range(nbb):
        hi, kl, sub = i >> 7, (i >> 3) & 15, i & 7
        loc = (kl >> 1, hi, ((kl & 1) * 8 + sub) * 16)
        assert loc not in seen and hi < words
        seen[loc] = i
    rows_bb = (nbb - 1 >> 7) + 1
    for blk in range(nbb // 64):                       # loader write block: 64 consecutive words (VRD)
        touched = {}
        for i in range(blk * 64, blk * 64 + 64):
            hi, kl = i >> 7, (i >> 3) & 15
            touched.setdefault((kl >> 1, hi), 0)
            touched[(kl >> 1, hi)] += 16
        assert len(touched) == 4 and all(v == width for v in touched.values()), blk
    for hi in range(rows_bb):                          # one read group: 16 lanes at (hi, sub) -> 8 macros, 1 row each
        for sub in range(8):
            ms = {(((hi << 7) | (kl << 3) | sub) >> 3 & 15) >> 1 for kl in range(16)}
            assert len(ms) == 8
    # qb
    seenq = {}
    for i in range(2 * nblk):
        loc = (((i >> 3) & 1, i & 1), (i >> 4) * 4 + ((i >> 1) & 3))
        assert loc not in seenq and loc[1] < words
        seenq[loc] = i
    rows_qb = max(l[1] for l in seenq) + 1
    bank = lambda i: ((i >> 3) & 1, i & 1)
    for spar in (0, 1):
        for u in range(256):
            for b in range(8):
                i0, i1 = spar * nblk + ((u << 4) | b), spar * nblk + ((u << 4) | 8 | b)
                if i1 < 2 * nblk:
                    assert bank(i0) != bank(i1)
    for par in (0, 1):
        for k in range(0, kmax, 64):
            blk = par * nblk + k // 32
            assert bank(blk) != bank(blk + 1) and (blk & 1) == 0
    bb_macros, qb_macros = 4 * 8, 4
    parity_bits = (bb_macros * rows_bb + qb_macros * rows_qb) * (width // 64) + 2 * nblk
    return dict(macro=macro['name'], macro_um=[macro['w'], macro['h']], macro_area_um2=macro['area'],
                bb=dict(replicas=4, macros_per_replica=8, macros=bb_macros, rows_used=rows_bb, rows=words,
                        why_replicas='4 BF byte groups read 4 independent rows (hi per group) every beat; 1R1W macro has '
                                     'one read port, so each group owns a copy (spend area, no 768:1 flop mux)'),
                qb=dict(banks=4, macros=qb_macros, rows_used=rows_qb, rows=words,
                        why_banks='reads (blk0, blk1) differ in index bit 3; writes (blk, blk+1) differ in bit 0'),
                eb=dict(storage='flops', bits=2 * nblk * 10),
                protection=dict(scheme='even parity per 64-b slice of every macro word (flop side array) + 1 per eb entry; '
                                       'checked on the full macro word before the sub-select; mismatch -> sticky fault '
                                       '(fail closed, op replay by the controller); buffers are rewritten every phase',
                                parity_bits=parity_bits,
                                alternative='SECDED (72,64) in a compiled 1R1W 128x288 macro: +12.5 % macro width, '
                                            'corrects single errors; price below'),
                macros=bb_macros + qb_macros,
                read_during_write='excluded by protocol: a word is read only after `have` covers it; have is visible '
                                  'to the streamer >= 1 cycle after the write edge (bench assertion obligation)')


# ------------------------------------------------------------------------------------------------ geometry
def box(i):
    return (i['x'], i['y'], i['x'] + i['w'], i['y'] + i['h'])


def gap_um(a, b):
    dx = max(0.0, max(a[0], b[0]) - min(a[2], b[2]))
    dy = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
    return dx + dy


def stations(d):
    return 0 if d <= FINAL_SEG_UM else math.ceil(d / CC_REACH_UM)


def geometry():
    g = json.loads(GEOM.read_text())
    if g['generator_sha256'] != sha(GEN):
        raise SystemExit('geometry extract was not built by the pinned generator ' + str(GEN))
    hub = {i['n']: i for i in g['hub_and_ends']}
    vm, ga = hub['sp_vm'], hub['sp_gather']
    wfc = next(r for r in g['regions'] if r['name'] == 'wfc_selected_child')['rect']
    cap = hub['sp_capture']
    slot = (vm['x'], vm['y'] + vm['h'], vm['x'] + vm['w'], cap['y'])
    core_slot = dict(rect=[round(v, 3) for v in slot], w=slot[2] - slot[0], h=slot[3] - slot[1],
                     area_mm2=(slot[2] - slot[0]) * (slot[3] - slot[1]) / 1e6,
                     occupied_by='wfc_selected_child soft reservation ' + str(wfc))
    die_x_slack = g['die_um'][0] - g['geo']['x_le'] + g['geo']['x_lw']
    hub_w = vm['w']
    frame_w = g['frames'][0]['rect'][2] - g['frames'][0]['rect'][0]
    ends = [i for i in g['hub_and_ends'] if i['n'].startswith('hr_')]
    return dict(raw=g, vm=vm, gather=ga, core_slot=core_slot, die_x_slack_um=die_x_slack, hub_column_w=hub_w,
                frame_w=frame_w, return_ends=ends, hx=[hub['hx_W'], hub['hx_E']])


# ------------------------------------------------------------------------------------------------ the design
def design(snap=SNAP):
    verify_repo_inputs()
    mod, inv = load_snapshot(snap)
    stages = {k: v['stages'] for k, v in inv.items()}
    PHW = max(s['PHW'] for v in stages.values() for s in v)
    SAW = max(s['SAW'] for v in stages.values() for s in v)
    KMAX = max(s['KMAX'] for v in stages.values() for s in v)
    assert (PHW, SAW, KMAX) == (9, 11, 6144)
    st = pq_storage(KMAX)
    assert st['bits'] == max(s['operand_storage_bits'] for v in stages.values() for s in v) == 298752
    screen = pq_storage(256)['bits']
    BW, fields, _ = native_bus(PHW)
    lanes = lane_layouts(fields, PHW)
    root = root_inventory()
    assert root['bits_per_root'] == 16768 and root['bits_total'] == 2146304
    ports = mod.native_ports(PHW, SAW)
    native_pins = sum(p['bits'] for p in ports.values())
    by_owner = {}
    for p in ports.values():
        by_owner[p['owner']] = by_owner.get(p['owner'], 0) + p['bits']
    assert by_owner['field_broadcast'] == BW and by_owner['field_return'] == R * root['out_payload_bits']

    mi = json.loads(MACROS.read_text())['macros']
    mname = 'ot_sram_1r1w_128x256_m1_r2c2'
    mm = mi[mname]
    macro = dict(name=mname, words=128, bits=256, area=mm['area_um2'], h=mm['height_um'],
                 w=round(mm['area_um2'] / mm['height_um'], 3))
    srams = sram_maps(KMAX, macro)
    G = geometry()
    rs = json.loads(RSTORE.read_text())['q1']['area_rule']
    ff_um2 = 0.37908                                  # DFFASRHQNx1 (area rule of the return-storage model)
    assert '0.37908' in rs

    # ---------------- blocks: pins (explicit port-bit layouts per face), area
    cfgrep = 4 * (5 * 19 + 18) + 4 + 2                # spine GRW: one region group's configuration replica word
    groups = [(e['n'], int(re.search(r'x(\d+)__', e['m'])[1])) for e in G['return_ends']]
    assert sum(n for _, n in groups) == R
    ret_lane = root['out_payload_bits'] + 2           # + fault + busy (legacy CRET = 66 + 2)
    vmw = 1 + 19 + 32
    blocks = {}
    root_faces = {'tree_in (S, column clock)': root['raw_in_bits'] + 1, 'ret_out (N, to rstg)': ret_lane,
                  'clk_rst': 2}
    root_cells = (root['bits_per_root'] + 2 * ROOTD) * ff_um2 + (128 + 66 + 33) * ff_um2 + ESTIMATES['root_logic_cell_um2'][0]
    root_area = root_cells / UTIL
    side = math.sqrt(root_area)
    blocks['ret_root_r128'] = dict(instances=R, faces=root_faces, pins=sum(root_faces.values()),
        storage_bits=root['bits_per_root'], parity_bits=2 * ROOTD, cell_um2_est=round(root_cells, 1),
        area_um2_est=round(root_area, 1), outline_um_est=[round(side, 1), round(side, 1)],
        clock='column clock (the column FIFO is the column clock / reset root), same domain as the node tree; no crossing',
        placement='frame empty q position (14 pairs in a 16-position frame: 4 BF + 10 q of 12 q positions) beside '
                  'the node strip; output joins the existing rstg return sub-column; final segment <= 100 um both faces',
        frame_position_um2=round(510.84 * 183.6, 1),
        microarch_obligation='ROOTD=128 associative sibling search cannot be one cycle at 833 ps: register the 128-b '
                             'match/free vectors (stage A), encode + update in stage B with bypass of the entry inserted '
                             'or removed last cycle; registered queue head (prefetch). Pairing decisions identical; '
                             '+1 cycle per root pass. Exact gate owned by pq_parent (Codex).')
    rwb = []
    for name, n in groups:
        faces = {'ret_in (from hr end block)': n * (ret_lane + 1) + 2, 'cfg_replica_in': cfgrep,
                 'rowcount_out (per tag)': 4 * (math.ceil(math.log2(n + 1))), 'vm_write_out': n * vmw,
                 'fault_out': 1, 'clk_rst': 2}
        cells = n * ESTIMATES['rwb_logic_cell_um2_per_region'][0] + (n * (69 + 90) + cfgrep) * ff_um2
        rwb.append(dict(name='rwb_' + name[3:], regions=n, faces=faces, pins=sum(faces.values()),
                        cell_um2_est=round(cells, 1), area_um2_est=round(cells / UTIL, 1)))
    blocks['rwb'] = dict(instances=len(rwb), per_instance=rwb,
        placement='inside sp_gather (stream_1p2), abutting each hr_<half><tier> end block; VM write face toward the VM '
                  '(173 um gap gather -> VM)',
        function='spine return stages 0-3 (registered root word, per-tag config replica, base + row + pos*stride, '
                 'format select, VM write) and the per-tag row counts; RG = the end block group (10/11 regions)')
    lane_w2 = lanes['union_W2']['bits']
    lane_w3 = lanes['serial_W3']['bits']
    vm_read = 1 + 19 + 64 * 32
    core_faces = {'vm_read (S, abut VM north face)': vm_read + 1,
                  'issuer (W)': by_owner['issuer'], 'phase_rom (E, 2 x ot_rom_4096x72)': by_owner['phase_ROM'],
                  'stream_rom (E, 1 x ot_rom_4096x72)': by_owner['stream_ROM'],
                  'lane_out W2 (W/E to hx end blocks)': lane_w2,
                  'cfg_replica_out (to RWB chain)': cfgrep, 'rowcount_in (12 RWB)': sum(r['faces']['rowcount_out (per tag)'] for r in rwb),
                  'fault_status': by_owner['fault_status'] + len(rwb), 'clk_rst': 2}
    flops = srams['eb']['bits'] + srams['protection']['parity_bits'] + 4 * BW + 4000
    core_cells = flops * ff_um2 + ESTIMATES['core_logic_cell_um2'][0]
    halo = 5.4
    core_macro = srams['macros'] * (macro['w'] + 2 * halo) * (macro['h'] + 2 * halo)
    core_area = core_macro + core_cells / UTIL
    blocks['pq_core'] = dict(instances=1, faces=core_faces, pins=sum(core_faces.values()), sram=srams,
        flops_est=flops, cell_um2_est=round(core_cells, 1), macro_um2_with_halo=round(core_macro, 1),
        area_um2_est=round(core_area, 1), clock='stream_1p2 (hub); VM read crosses serial_0p9 -> stream_1p2',
        placement='hub west column, VM north face slot ' + str(G['core_slot']['rect']),
        sub_blocks=dict(pq_xbuf=dict(macros=srams['macros'], area_um2_est=round(core_macro + (srams['protection']['parity_bits']
                                     + srams['eb']['bits']) * ff_um2 / UTIL, 1)),
                        pq_ctl=dict(area_um2_est=round((ESTIMATES['core_logic_cell_um2'][0] + 4 * BW * ff_um2) / UTIL, 1))))
    total_new_pins = blocks['pq_core']['pins'] + sum(r['pins'] for r in rwb) + R * blocks['ret_root_r128']['pins']

    # ---------------- lane distribution cost per die (area scales with lane width; legacy stations are 566 wide)
    g = G['raw']
    xa, sa, cfa = g['x_chain_stations']['area_um2'], g['slot_stations']['area_um2'], g['kind_totals_mm2']['cfifo'] * 1e6
    leg = 566
    def lane_cost(w, bf_stations_frac):
        f = (w + 2) / leg - 1
        return dict(lane_bits=w, x_chain_um2=round(xa * f, 0), cfifo_um2=round(cfa * (5 * w) / (5 * 564 + 68) - cfa
                    + cfa * 68 / (5 * 564 + 68) * 0, 0), slot_station_um2=round(sa * f * bf_stations_frac, 0))
    W1 = lane_cost(BW, 1.0)
    W2i = lane_cost(lane_w2, 8 / 9)     # interleaved BF slots: extension runs to the 4th BF slot (8 of 9 stations)
    W2b = lane_cost(lane_w2, 4 / 9)     # BF slots at the column foot: 4 of 9 stations
    W3 = lane_cost(lane_w3, 1.0)
    for d in (W1, W2i, W2b, W3):
        d['total_mm2'] = round((d['x_chain_um2'] + d['cfifo_um2'] + d['slot_station_um2']) / 1e6, 3)
    deser = 512 * math.ceil(lanes['serial_W3']['bf_payload_bits'] / 2) * ff_um2 / UTIL / 1e6
    W3['bf_deserialisers_mm2'] = round(deser, 3)
    W3['total_mm2'] = round(W3['total_mm2'] + deser, 3)

    # ---------------- latency / credit obligations (cycles at 1.2 GHz)
    vm, ga, slot = G['vm'], G['gather'], G['core_slot']['rect']
    core_box = tuple(slot)
    k_core_rwb = stations(gap_um(core_box, box(ga)))
    k_rwb_vm = max(1, stations(gap_um(box(ga), box(vm))))
    k_hx = stations(min(gap_um(core_box, box(h)) for h in G['hx']))
    cdc = ESTIMATES['vm_cdc_latency_cycles'][0]
    sens = json.loads(SENS.read_text())
    pq = next(v for v in sens['variants'] if v['configuration'] == 'pq_qelem')
    coef = (pq['baseline_AR_tok_s'] - pq['conditional_AR_tok_s']) / pq['baseline_AR_tok_s']
    lat = dict(
        root_pipeline=dict(cycles=3, per='phase (last row: <= 3 root-level adds, +1 each)', path='return'),
        rwb_to_vm=dict(cycles=k_rwb_vm + cdc, per='phase end (last VM write)', stations=k_rwb_vm, cdc=cdc),
        rowcount_to_core=dict(cycles=k_core_rwb + 1, per='op retire / idle (phase end)', stations=k_core_rwb,
                              distance_um=round(gap_um(core_box, box(ga)), 1)),
        vm_read_round_trip=dict(cycles=2 * cdc + 2, per='op whose first beat waits on its load (exposed only then)'),
        vm_read_rate=dict(value='<= 0.75 words / stream cycle (0.9 / 1.2 GHz)', per='exposed load: +K/(64*3) cycles',
                          kmax_cost_cycles=math.ceil(2 * KMAX / 64 / 3)),
        lane_root=dict(cycles=k_hx, per='0 if hx_W / hx_E end blocks move to the core W/E faces (requested); else '
                                       'every op start'),
        W3_serial=dict(cycles='+2 latency per BF beat stream + 1 per adjacent BF beat pair', per='BF phases only'))
    per_phase = lat['root_pipeline']['cycles'] + max(lat['rwb_to_vm']['cycles'], lat['rowcount_to_core']['cycles'])
    credits = dict(
        vm_read=dict(depth=2 * (cdc + 1) + 2 + 2, rule='loader becomes request / response: x_re carries a credit '
                     'against a core-side x_q FIFO of depth >= round trip (2 x (CDC + register) + VM macro 2); RTL '
                     'change: ld/rq pipeline consumes x_q on its valid, not one cycle after x_re (payload invariant)'),
        vm_write=dict(depth_per_region=2 * (k_rwb_vm + cdc) + 2, rule='per-region write FIFO + credit from the VM '
                      'face; no upstream backpressure exists (the root has none), so the mapping must guarantee the '
                      'region row rate <= 0.75 / stream cycle over any window longer than the FIFO; INPUT REQUESTED: '
                      'max rows per region per window from the mapping'),
        broadcast=dict(rule='no flow control (timed broadcast); existing meso D8 column FIFOs absorb drift; unchanged'),
        root_input=dict(rule='no flow control (tree accepts every partial; QD=ROOTD=128 is the source depth; overflow '
                             'is a fault); unchanged'),
        cfg_replica=dict(rule=f'timing obligation: replica chain {k_core_rwb} stations must land before the first '
                              'row of the op (field latency >> chain); assert in bench'))
    cost = dict(added_cycles_per_phase=per_phase, AR_fraction_per_cycle_per_phase=coef,
                AR_loss_fraction_est=round(per_phase * coef, 5),
                basis='linear in the measured +1-return-cycle sensitivity (pq_qelem: %.1f -> %.1f tok/s); historical '
                      'source-pinned phases, NOT the 1792 geometry' % (pq['baseline_AR_tok_s'], pq['conditional_AR_tok_s']))

    # ---------------- options
    roots_mm2 = R * root_area / 1e6
    core_mm2 = core_area / 1e6
    rwb_mm2 = sum(r['area_um2_est'] for r in rwb) / 1e6
    options = {
        'A_monolithic_native': dict(partition='one R128 parent: spine + 128 roots + return stages, 1633-b bus',
            pins=native_pins + R * 68 - by_owner['field_return'] + R * 2,
            area_mm2_est=round(roots_mm2 + core_mm2 + rwb_mm2 + W1['total_mm2'], 3), lane=W1,
            verdict='REJECT: one %.2f mm2 block (roots inside) with %d pins (raw 68-b returns in instead of 69); '
            'roots far from their regions; 1633-b lane x2.9 field infra (+%.1f mm2)' % (
                roots_mm2 + core_mm2 + rwb_mm2, native_pins + R * 68 - by_owner['field_return'] + R * 2, W1['total_mm2'])),
        'B_split_native_lane': dict(partition='roots in frames, 12 RWB in gather, PQ core at VM north, native 1633 lane',
            area_mm2_est=round(roots_mm2 + core_mm2 + rwb_mm2 + W1['total_mm2'], 3), lane=W1,
            verdict='REJECT: +%.1f mm2 lane infrastructure on every die and x wiring x2.9 for no function' % W1['total_mm2']),
        'C_split_union_lane': dict(partition='as B with the W2 union lane (%d b) on BF dies, %d b on q-only dies' % (
            lane_w2, lanes['union_W2']['q_slot_bits']), area_mm2_est=round(roots_mm2 + core_mm2 + rwb_mm2 + W2i['total_mm2'], 3),
            lane=dict(interleaved=W2i, bf_at_foot=W2b), verdict='RECOMMENDED baseline: no stream change, exact by '
            'construction (pure re-wiring of the native fields); BF-die lane +%.1f mm2' % W2i['total_mm2']),
        'D_split_serial_union': dict(partition='as C with the W3 serialised union lane (%d b) everywhere' % lane_w3,
            area_mm2_est=round(roots_mm2 + core_mm2 + rwb_mm2 + W3['total_mm2'], 3), lane=W3,
            verdict='PARALLEL ALTERNATIVE: drop-in legacy lane width; costs +2 cycles on BF beat streams and +1 per '
                    'adjacent BF beat pair; adopt only with the measured adjacency (INPUT REQUESTED) and exact gate'),
        'E_central_roots': dict(partition='roots + RWB as one hub block beside gather (raw 68-b trunks unchanged)',
            area_mm2_est=round(roots_mm2 + rwb_mm2, 3), verdict='REJECT: needs %.2f mm2 compact hub area next to gather; '
            'the hub columns are full (8 slabs, 173 um inter-slab channels) and the die x slack is only %.0f um' % (
                roots_mm2 + rwb_mm2, G['die_x_slack_um']))}

    half_bf = sum(1 for s in stages['half'] if s['SAW'] == 11)
    mi_ = {k: json.loads((MAP / v / 'inventory.json').read_text()) for k, v in (('half', 'half_dedicated'), ('full', 'full_shared'))}
    dies = dict(mapping={k: dict(stages=v['stages'], layer_dies_TP4=v['layer_dies'], bf_stages=v['bf_stages'],
                                 q_stages=v['q_stages'], pairs_per_die=v['pairs_bf_stage']) for k, v in mi_.items()},
                die_count_change=0,
                condition='0 extra dies if (1) the root fits the empty q position of every frame, (2) the 12 RWB '
                          'fit sp_gather, (3) the die owner provides the VM-north core slot (re-stack: relocate the '
                          'WFC child 1015 x 449 um, or widen both hub columns by up to %.0f um / 2 of die x slack)' % G['die_x_slack_um'],
                fallback='if any frame cannot host the root: one extra tier-channel row of root blocks (+%.0f um '
                         'channel height per tier, 6 tiers) - priced by re-running the die generator; if that '
                         'forces a slot loss the mapping re-runs at 13 pairs a region (stages x 14/13)' % (side + 2 * halo),
                half_dies_with_bf_lane=4 * mi_['half']['bf_stages'], full_dies_with_bf_lane=4 * mi_['full']['bf_stages'],
                half_check_bf_stages_equal_saw11_stages=half_bf == mi_['half']['bf_stages'])
    per_die_area = dict(roots_mm2=round(roots_mm2, 3), rwb_mm2=round(rwb_mm2, 3), pq_core_mm2=round(core_mm2, 3),
                        lane_W2_interleaved_mm2=W2i['total_mm2'], lane_W2_bf_at_foot_mm2=W2b['total_mm2'],
                        total_bf_die_mm2=round(roots_mm2 + rwb_mm2 + core_mm2 + W2i['total_mm2'], 3),
                        total_q_die_mm2=round(roots_mm2 + rwb_mm2 + core_mm2, 3),
                        die_mm2=g['die_um'][0] * g['die_um'][1] / 1e6, core_slot=G['core_slot'],
                        core_fits_vm_north_slot=core_area <= G['core_slot']['area_mm2'] * 1e6)

    staged = [
        dict(stage=1, block='ret_root_r128 (x128, one master)', size_um=blocks['ret_root_r128']['outline_um_est'],
             faces='S tree_in 67 b, N ret_out 71 b, both through abutting relay stations', closure='column clock 1.2 GHz '
             'SS>=+15 / FF>=+15 ps DRC 0; pipelined CAM; exact gate by pq_parent with a mis-paired negative control',
             parallel_with=[2, 3]),
        dict(stage=2, block='pq_xbuf (36 x %s + parity)' % mname, size_um_est='~700 x 330',
             faces='write 1024+512+20 b + addresses; read addresses 4 x 9 + 2 x 9; read data 4 x 256 + 2 x 256 + 20 '
                   '(macro outputs are registers)', closure='macro placement + parity; RDW-free assertion bench',
             parallel_with=[1, 3]),
        dict(stage=3, block='rwb (one master, N=11 / N=10 parameter)', size_um_est='~%d x %d' % (
             math.ceil(math.sqrt(rwb[0]['area_um2_est'])), math.ceil(math.sqrt(rwb[0]['area_um2_est']))),
             faces='ret_in N x 72, cfg replica 458, VM write N x 52, rowcount 16', closure='stream 1.2 GHz; VM face '
             'via ratio CDC owner', parallel_with=[1, 2]),
        dict(stage=4, block='pq_ctl (issuer, ROM 2-cycle adapters, loader request/response + 2 actquant, reader, '
             'streamer, beat assembly, W2 lane encoder)', size_um_est='<= 1015 x 450',
             closure='after the R128 screen hierarchy report; BST registers at the lane faces'),
        dict(stage=5, block='lane infrastructure (die generator): cfifo W%d, x-chain stations %d b, BF-slot stations' % (
             lane_w2, lane_w2 + 2), closure='die owner; q-only dies carry the 567-b q lane (legacy 564 + 3)'),
        dict(stage=6, block='pq_core parent = pq_xbuf + pq_ctl at the VM north slot', closure='hierarchical, '
             'registered faces only'),
        dict(stage=7, block='die integration (roots in frames, RWB in gather, core slot, hx end blocks at core faces)',
             closure='full-die SS/FF/DRC/IR per owner directive 14')]

    gated = ['ROOT microarch exactness (pipelined CAM + registered queue head) - pq_parent/Codex',
             'union-lane don\'t-care proof: element outputs unchanged with the other family\'s payload on its pins, '
             'plus a negative control that consumes payload without its valid',
             'VM read request/response loader change (variable latency) exact gate',
             'VM 128 write ports at serial_0p9 sustain the region row rate (mapping burst input)',
             'root / RWB / core areas are ESTIMATES until synthesis screens',
             'die generator legality for roots in frames and the VM-north core slot (die owner)']
    return dict(schema='opentallas.s81.pq-fullshape-design.v1', adopted=False, physical_qualified=False,
        sources=dict(snapshot=(str(snap.resolve().relative_to(ROOT)) if snap.resolve().is_relative_to(ROOT) else str(snap)),
                     snapshot_origin='/home/ubuntu/.claude/jobs/724d7460/tmp/pq_snapshot_1117', snapshot_sha256=SNAP_SHA, spine_rtl_sha256=sha(SPINE), ret_rtl_sha256=sha(RET),
                     macro_index_sha256=sha(MACROS), geometry_extract_sha256=sha(GEOM), sensitivity_sha256=sha(SENS)),
        problem=dict(PHW=PHW, SAW=SAW, KMAX=KMAX, pq_storage=st, screen_storage_bits_R128_6_8_256=screen,
                     storage_ratio=st['bits'] / screen, phase_rom_entries=2 << PHW, stream_rom_words=1 << SAW,
                     native_bus_bits=BW, legacy_lane_bits=564, native_pins=native_pins, native_pins_by_owner=by_owner,
                     codex_def_pins=19355, def_vs_port_model_delta=native_pins - 19355,
                     return_word=dict(legacy_raw_per_region=68, root_payload=root['out_payload_bits'],
                                 lane_with_status=ret_lane), roots=root),
        lanes=lanes, blocks=blocks, new_partition_pins_total=total_new_pins,
        max_pins_per_block=dict(native_parent=native_pins, pq_core=blocks['pq_core']['pins'],
                                rwb=max(r['pins'] for r in rwb), ret_root=blocks['ret_root_r128']['pins']), per_die_area=per_die_area,
        latency=lat, credits=credits, cost=cost, options=options, recommendation='C_split_union_lane (+ D in parallel)',
        dies=dies, staged_plan=staged, estimates=ESTIMATES, gated=gated)


CUR = OUT / 'current_main'
CURRENT = dict(
    SPINE=CUR / 'inputs/rtl/ot_v41_spine_pqc_w17w10.d0178820d.sv',   # production native source (Codex native_elaboration)
    GEOM=CUR / 'geometry_extract.json', GEN=CUR / 'inputs/pinned/dsrom_s81_fulldie.cfc076112.py',
    INSERTION=CUR / 'inputs/calibration/measured_insertion.bb7c46846.json',
    REPO_SUMS=CUR / 'inputs/REPO_INPUTS.SHA256SUMS',
    SNAP_PATHS={'pq_parent_binding.py': ROOT / 'tools/s81/pq_parent_binding.py',
                'dsrom_s81_pq_parent_20261007/full_inventory.json':
                    ROOT / 'results/uarch/dsrom_s81_pq_parent_20261007/full_inventory.json',
                'dsrom_s81_pq_parent_20261007/half_inventory.json':
                    ROOT / 'results/uarch/dsrom_s81_pq_parent_20261007/half_inventory.json'})
STREAM = CUR / 'stream_stats.json'


def spine_params(t):
    return {k: int(re.search(r'parameter integer %s\s*=\s*(\d+)' % k, t)[1]) for k in ('RG', 'RPT', 'BST', 'GAP', 'GUARD')
            if re.search(r'parameter integer %s\s*=\s*(\d+)' % k, t)}


def current_extras(d):
    """current-basis refinements: production spine parameters, mapping-derived credits / serial-lane cost, cycles"""
    t = SPINE.read_text()
    sp = spine_params(t)
    hist_sp = spine_params((ROOT / 'rtl/v41die/ot_v41_spine_pqc_w17w10.sv').read_text())
    st = json.loads(STREAM.read_text()) if STREAM.exists() else {}
    lat, cr = d['latency'], d['credits']
    rpt = sp.get('RPT', 0)
    # cycles relative to the native production parent (v13b): its RPT repeaters on the root inputs and on the row writes
    # are the long-wire stations the split replaces: root -> RWB is local (hr end block abuts the RWB), RWB -> VM keeps
    # its own stations
    rc = lat['rowcount_to_core']['cycles'] - rpt
    rw = lat['rwb_to_vm']['cycles'] - rpt
    rootc = ROOT_CONTRACT['cam_max_cycles_per_row'] + ROOT_CONTRACT['stations']
    added = rootc + max(rc, rw, 0)
    coef = d['cost']['AR_fraction_per_cycle_per_phase']
    out = dict(spine_source=str(SPINE.relative_to(ROOT)), spine_sha256=sha(SPINE), spine_params=sp,
               historical_spine_params=hist_sp,
               cycles=dict(added_cycles_per_phase=added, vs_historical=added - d['cost']['added_cycles_per_phase'],
                           AR_loss_fraction_est=round(added * coef, 5),
                           rule='root contract (CAM +1 per pass, <= 4 passes on a row\'s chain, + 2 in/out stations) %d '
                                '+ max(rowcount %d, rwb->VM %d) - RPT %d (v13b already pays RPT on the root inputs and '
                                'row writes; the split replaces those repeaters by placed stations)'
                                % (rootc, lat['rowcount_to_core']['cycles'], lat['rwb_to_vm']['cycles'], rpt),
                           price_status='PARTIAL: per-phase delta x historical +1-return-cycle sensitivity; the 1,792 '
                                        'per-token critical-phase list is not composed (mapping has %s compiled phases, '
                                        'of which only the token-active subset is on the path)' % (
                                            st.get('half', {}).get('phases'),)),
               rwb_replica_groups=[dict(rwb=r['name'], regions=r['regions'], replica_copies=-(-r['regions'] // sp.get('RG', 16)))
                                   for r in d['blocks']['rwb']['per_instance']])
    for case in ('half', 'full'):
        if case not in st:
            continue
        s = st[case]
        burst = s['max_rows_region_phase']
        depth = cr['vm_write']['depth_per_region']
        out[case] = dict(mapping_sha256=s['mapping_sha256'], phases=s['phases'], bf_phases=s['bf_phases'],
            vm_write=dict(max_rows_region_phase=burst, fifo_depth=max(depth, burst),
                          holds_whole_region_phase_burst=max(depth, burst) >= burst,
                          rule='a region emits <= %d rows a phase (root <= 1 row/cycle); a FIFO >= the burst absorbs it '
                               'with zero drain, so no rate assumption on the 0.75/cycle VM side is needed' % burst),
            serial_lane_W3=dict(bf_max_back_to_back=s['bf_max_back_to_back'],
                                adjacent_valid_pairs=s['bf_adjacent_valid_pairs'],
                                extra_cycles_at_phase_end_sum=s['bf_serial_extra_cycles_sum'],
                                max_beat_delay=s.get('bf_serial_beat_delay_max'),
                                rule='two lane cycles per valid BF beat, in order; idle native slots absorb the delay'))
    out['budget_sheets'] = budget_sheets(d)
    pl = PQ_PARENT_PLACEMENT
    root_res = pl['root_strip_w_um'] * pl['root_row_h_um']
    out['placement_pq_parent'] = dict(pl, root_reservation_um2=round(root_res, 1),
        roots_per_die_mm2=round(R * root_res / 1e6, 3), root_cell_outline_um2=round(pl['root_w_um'] * pl['root_h_um'], 1),
        root_outline_vs_estimate=round(pl['root_w_um'] * pl['root_h_um'] / d['blocks']['ret_root_r128']['area_um2_est'], 3),
        core_slot_mm2=round(pl['core_slot_h_um'] * pl['core_slot_w_um'] / 1e6, 3),
        core_estimate_mm2=round(d['blocks']['pq_core']['area_um2_est'] / 1e6, 3),
        core_fits=d['blocks']['pq_core']['area_um2_est'] <= pl['core_slot_h_um'] * pl['core_slot_w_um'],
        roots_per_tier=[2 * c for c in json.loads(GEOM.read_text())['tier_cols']],
        supersedes='design recommendation (1): roots in empty q element positions - wrong: mixed 1,792 frames are 4 '
                   'BF full-width + 10 q half-width = 9 fully occupied rows, no empty positions')
    return out


ROOT_CONTRACT = dict(cam_max_cycles_per_row=4, stations=2,
                     source='tools/s81_root_contract.py cam_contract().latency (+1 per pass, <= 1 + 3 passes)')
PQ_PARENT_PLACEMENT = dict(
    status='PROVISIONAL: Codex /root/s81/pq_parent packing update relayed 2026-10-07 ~12:31 PT (mailbox '
           'claude_pq_design_msgs); not yet committed as a generator layout',
    root_row_h_um=164.16, root_rows='one root row in each of the first 6 tier channels (one root per column, '
                                     'below its frame)',
    frame_spare_um=dict(before=241, after=77), pairs_per_die=1792, bf_pairs_per_die=512,
    root_w_um=132.192, root_h_um=133.92, station_w_um=8.64, stations=2, root_strip_w_um=142.56,
    core_slot_h_um=449.28, core_slot_w_um=1728.0, core_slot='explicit slot after the VM',
    su_restack='capture-up / SU restack keeps the same 25.61188 mm2 SU')
INSERTION = ROOT / 'results/rtl/budgets_20261006/measured_insertion.json'   # daemon-mutated on main: current basis pins a snapshot
MODEL_BASIS = dict(
    label='MODELED VERSION: main@e2a4ad579 with calibration snapshot observed 2026-10-07T12:10:55-07:00',
    main_commit='e2a4ad579',
    calibration_snapshot=dict(path='current_main/inputs/calibration/measured_insertion.bb7c46846.json',
                              source_path='results/rtl/budgets_20261006/measured_insertion.json',
                              source_commit='bb7c46846 (2026-10-07 12:07:44 -0700, closure-loop daemon)',
                              observed_at='2026-10-07T12:10:55-07:00 (worktree file mtime when read)',
                              sha256='4a72c6e5137d1f983c9d1ee67da23f03c5016edb0d7726b1b8f4473aa1cd4e11',
                              note='the live file on main is rewritten by the closure-loop daemon; this basis never '
                                   'reads it'),
    generator=dict(path='current_main/inputs/pinned/dsrom_s81_fulldie.cfc076112.py',
                   source='tools/dsrom_s81_fulldie.py @ e2a4ad579'),
    geometry_status='PROVISIONAL: generator rebuild of the frame model (empty-q-slot root assumption superseded by '
                    'the pq_parent placement: 164.16 um root rows in the first 6 tier channels, 449.28 x 1,728 um core '
                    'slot after the VM); the geometry owner is rebuilding the actual layout')
ANALOGUE = {'ret_root_r128': 'ot_s81ph_root_tile', 'rwb': 'dsfd_cfifo', 'pq_xbuf': 'ot_v41_rom_elem_q_qxpq_w10',
            'pq_ctl': 'ot_v41_rom_elem_q_qxpq_w10', 'lane_station': 'dsfd_stnh_566x1'}


def rwb_outline(w):
    """pin-limited outline: ret_in on N, vm_write on S (width = the larger), cfg replica + rowcount + fault on W/E"""
    f = w['faces']
    wd = max(f['ret_in (from hr end block)'], f['vm_write_out']) / PIN_DENSITY
    ht = max(f['cfg_replica_in'] / PIN_DENSITY, (f['rowcount_out (per tag)'] + 3) / PIN_DENSITY, w['area_um2_est'] / wd)
    return dict(outline_um=[round(wd, 1), round(ht, 1)], cell_utilisation=round(w['cell_um2_est'] / (wd * ht), 3),
                limiter='pins (%d on the N face): the block is pin-limited, not area-limited' % f['ret_in (from hr end block)'])


def budget_sheets(d):
    """per hardening-stage block: pins per face, face length the pins need at the r8 station pin density, area,
    and the clock-insertion target (the measured SS/FF mean of the nearest measured analogue block; a target, not a
    measurement of this block)"""
    ins = json.loads(INSERTION.read_text())['blocks']
    def tgt(k):
        a = ins[ANALOGUE[k]]
        return dict(analogue=ANALOGUE[k], ss_ps=a['ss']['mean'], ff_ps=a['ff']['mean'], source_commit=a['source_commit'])
    b = d['blocks']
    rows = []
    def face_rows(faces):
        return {f: dict(pins=n, face_um_needed=round(n / PIN_DENSITY, 1)) for f, n in faces.items()}
    r = b['ret_root_r128']
    rows.append(dict(stage=1, block='ret_root_r128', instances=128, outline_um_est=r['outline_um_est'],
                     area_um2_est=r['area_um2_est'], faces=face_rows(r['faces']), pins=r['pins'],
                     relay='abutting station on S and N faces; final segment <= 100 um', insertion_target=tgt('ret_root_r128')))
    x = b['pq_core']['sub_blocks']['pq_xbuf']
    xf = {'loader_write (N)': 1024 + 512 + 20 + 2 * 9 + 8, 'read_addr (W)': 4 * 7 + 2 * 7 + 6,
          'read_data (S)': 4 * 256 + 2 * 256 + 20, 'parity_fault': 1, 'clk_rst': 2}
    rows.append(dict(stage=1, block='pq_xbuf', instances=1, area_um2_est=x['area_um2_est'], macros=x['macros'],
                     outline_um_est=[700, 330], faces=face_rows(xf), pins=sum(xf.values()),
                     relay='macro outputs registered; abutting pq_ctl (no die wire)', insertion_target=tgt('pq_xbuf')))
    for w in b['rwb']['per_instance'][:2]:
        rows.append(dict(stage=1, block='rwb (N=%d)' % w['regions'], instances=sum(1 for z in b['rwb']['per_instance']
                         if z['regions'] == w['regions']), area_um2_est=w['area_um2_est'],
                         outline_um_est=[round(math.sqrt(w['area_um2_est']), 1)] * 2, faces=face_rows(w['faces']),
                         pins=w['pins'], relay='hr end block abutting; VM face 1 station + ratio CDC',
                         insertion_target=tgt('rwb'),
                         note=rwb_outline(w)))
    c = b['pq_core']
    rows.append(dict(stage=2, block='pq_ctl', instances=1, area_um2_est=c['sub_blocks']['pq_ctl']['area_um2_est'],
                     faces=face_rows({k: v for k, v in c['faces'].items()}), pins=c['pins'] + sum(xf.values()) - 3,
                     relay='BST/lane registers at the W/E faces; VM read abutting', insertion_target=tgt('pq_ctl')))
    lane = d['lanes']['union_W2']['bits'] + 2
    rows.append(dict(stage=3, block='lane station / cfifo W%d' % (lane - 2), faces=face_rows({'in': lane, 'out': lane}),
                     pins=2 * lane, relay='stations <= 215 um (cc reach)', insertion_target=tgt('lane_station')))
    return dict(pin_density_per_um=round(PIN_DENSITY, 3), insertion_source=str(INSERTION.relative_to(ROOT)),
                insertion_sha256=sha(INSERTION), rows=rows)


def main():
    global SPINE, GEOM, GEN, REPO_SUMS, SNAP_PATHS
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--basis', choices=['historical', 'current'], default='historical',
                    help='historical: the d95b57661 inputs (pinned); current: current-main inputs (current_main/)')
    ap.add_argument('--snapshot', type=Path, default=SNAP)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    global INSERTION
    if a.basis == 'current':
        SPINE, GEOM, GEN, REPO_SUMS, SNAP_PATHS, INSERTION = (CURRENT[k] for k in (
            'SPINE', 'GEOM', 'GEN', 'REPO_SUMS', 'SNAP_PATHS', 'INSERTION'))
    out = a.out or (OUT / 'reproduce/design.json' if a.basis == 'historical' else CUR / 'design.json')
    d = design(a.snapshot)
    if a.basis == 'current':
        d['sources']['snapshot'] = {k: str(v.relative_to(ROOT)) for k, v in SNAP_PATHS.items()}
        d['sources']['snapshot_origin'] = 'committed on main (identical hashes to pq_snapshot_1117)'
        d['sources']['stream_stats_sha256'] = sha(STREAM) if STREAM.exists() else None
        d['current_basis'] = current_extras(d)
        d['model_basis'] = MODEL_BASIS
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(d, indent=1, default=str) + '\n')
    p = d['problem']
    print(json.dumps(dict(storage=p['pq_storage']['bits'], ratio=p['storage_ratio'], native_bus=p['native_bus_bits'],
        union=d['lanes']['union_W2']['bits'], serial=d['lanes']['serial_W3']['bits'], pins=p['native_pins'],
        roots_bits=p['roots']['bits_total'], per_die=d['per_die_area'], cycles=d['cost'],
        sram_macros=d['blocks']['pq_core']['sram']['macros']), indent=1, default=str))


if __name__ == '__main__':
    main()
