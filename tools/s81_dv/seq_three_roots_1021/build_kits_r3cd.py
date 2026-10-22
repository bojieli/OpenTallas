"""STW-S81c-COLLB (10-22) structural successor of dsdv_seq_host_r3a/r3b (both TERMINAL FAIL GPL-0305).

Cause (ot-epyc5 ref_gate/dsdv_seq_host_r3a-20261021-232424/cts.log): RePlAce routability weighted congestion
3.13 (r2a 1.34), routability inflation +1889 %, the inflated cells filled 45 tiny 1322-2644 um2 seam fences to
their 0.5 target and overflow stalled (lk_7 / sq_20 / vc_0 / vc_3 / vc_4) -> penalty 1e32 -> Inf/NaN.
Structural defect: every SQ landing half sat in ONE band SOUTH of u_l1, but the sq<->vc seams (12-20, 1,296
bits) attach to u_l1's NORTH face (rn_o/rs_i/tw_o/cf_o/cn_o/cs_o/cg_o/dn_i/vf_i) -> each of those buses ran
N face -> around the macro -> south band -> back north to the vc band (two hairpins past the u_l1 flanks).
The per-seam boxes were also assigned in index order (x = 54 + (ix%4)*91.8), not under their pins.

Successor (no RTL / child / timing-limit change; landing record unchanged):
  * the landing half of each seam sits on the face its child pins use: lk band north of u_l0, SQ-south band
    (seams 0-11), SQ-north band (seams 12-20), VC band south of u_l2 -> every seam is a straight vertical hop
    between two facing child faces (sq N / vc S pin columns are already x-aligned);
  * one fence per (region, band) instead of 42 per-seam boxes, 4-7x taller bands (std util <~10 %);
  * reset copies of each region in their own fence beside the region (sq: in the channel beside u_l1 so
    both sq bands are equidistant);
  * ck_sq / rst_n_sq enter beside the u_l1 centre (the sq region now spans both u_l1 faces).
  r3c MAIN keeps the r3a outline 475.2 x 1339.2; r3d FALLBACK enlarges it (+43.2 W, +86.4 H: both inter-child
  gaps +43.2) for wider bands.
"""
from pathlib import Path
import json, copy

D = Path('tools/s81_dv/seq_three_roots_1021')
record = json.loads(Path('results/arch/codex_seq_three_roots_1021/dsdv_seq_host_c_r3_lp_record.json').read_text())
r3a_f = (D / 'r3a_fences.tcl').read_text()
tail = r3a_f[r3a_f.index('proc lpf_seq'):r3a_f.index('foreach r {lk_0')]
base = json.loads((D / 'dsdv_seq_host_r3a.json').read_text())

# sq <-> vc seams attach to u_l1 NORTH / u_l2 SOUTH; sq <-> lk seams to u_l1 SOUTH / u_l0 NORTH
def band_of(region, other):
    if region == 'sq':
        return 'sqN' if other == 'vc' else 'sqS'
    return region

VARIANTS = {
    # name: outline, sq at y, vc at y, band y-ranges, band x-range, rst boxes, ck/rst pin y
    'c': dict(w=475.2, h=1339.2, sq_y=691.2, vc_y=1080.0,
              bands={'lk': (507.6, 583.2), 'sqS': (604.8, 680.4), 'sqN': (853.2, 934.2), 'vc': (950.4, 1069.2)},
              bx=(43.2, 426.6),
              rst={'lk': (432.0, 507.6, 464.4, 583.2), 'sq': (351.0, 696.6, 426.6, 837.0), 'vc': (432.0, 950.4, 464.4, 1069.2)},
              pin={'sq': 756.0, 'vc': 1036.8}),
    'd': dict(w=518.4, h=1425.6, sq_y=734.4, vc_y=1166.4,
              bands={'lk': (507.6, 604.8), 'sqS': (626.4, 723.6), 'sqN': (896.4, 1004.4), 'vc': (1026.0, 1155.6)},
              bx=(43.2, 469.8),
              rst={'lk': (475.2, 507.6, 507.6, 604.8), 'sq': (351.0, 739.8, 469.8, 880.2), 'vc': (475.2, 1026.0, 507.6, 1155.6)},
              pin={'sq': 799.2, 'vc': 1101.6}),
}

for suffix, v in VARIANTS.items():
    name = 'dsdv_seq_host_r3' + suffix
    s = copy.deepcopy(base)
    s['name'] = name
    s['outline'] = {'w': v['w'], 'h': v['h'], 'exact': True}
    s['children'][1]['at'] = [86.4, v['sq_y']]
    s['children'][2]['at'] = [86.4, v['vc_y']]
    for r in ('sq', 'vc'):
        y = v['pin'][r]
        s['pin_ranges']['ck_' + r] = [y, round(y + 6.48, 2)]
        s['pin_ranges']['rst_n_' + r] = [round(y + 10.8, 2), round(y + 17.28, 2)]
    s['structural_change'] = (
        'Successor of r3a/r3b (GPL-0305: routability weighted congestion 3.13, 45 tiny seam fences saturated by '
        'inflation). Each seam landing half now sits on the child face its pins use: sq<->vc seams in a band NORTH '
        'of u_l1 (was south: two hairpins of 1,296 bits around u_l1), sq<->lk seams south of u_l1, lk band north '
        'of u_l0, vc band south of u_l2. One fence per region band (4 bands + 3 reset fences, was 45 boxes), '
        'std util < ~10 %. ck_sq/rst_n_sq enter beside the u_l1 centre. ' +
        ('Outline unchanged 475.2 x 1339.2.' if suffix == 'c' else 'Outline enlarged to 518.4 x 1425.6 (both inter-child gaps +43.2 um).') +
        ' No RTL, child view, landing record or timing-limit change.')
    j = s['job']
    j['owner'] = 'STW-S81c-COLLB'
    j['branch'] = 'claude/s81-seq-r3cd-1022'
    j['tag'] = name
    j['views_to'] = 'physical/ref_tile/' + name + '/views'
    j['record_to'] = 'results/rtl/ref_tile/' + name
    fence = str(D / ('r3' + suffix + '_fences.tcl'))
    s['pin_hook_before_flops'] = [fence]
    (D / (name + '.json')).write_text(json.dumps(s, indent=2) + '\n')

    own = {}
    used = set()
    for seam in record['landings']:
        for side, reg, other in (('w', seam['src_region'], seam['dst_region']), ('r', seam['dst_region'], seam['src_region'])):
            b = band_of(reg, other)
            own['u_lpl_' + seam['name'] + '_' + side] = b
            used.add(b)
    lines = ['# STW-S81c-COLLB r3' + suffix + ': one landing fence per region band on the child face its seam pins use;',
             '# release exclusive regions before DPL/CTS (lp_fence_release.tcl). Generated by build_kits_r3cd.py.',
             'set ::lpf_blk [ord::get_db_block]', 'set ::lpf_dbu [$::lpf_blk getDbUnitsPerMicron]',
             'array set ::lpf_g {}', 'array set ::lpf_n {}', 'array set ::lpf_c {}']
    groups = []

    def box(g, b4):
        lines.extend([f'set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_{g}"]',
                      'odb::dbBox_create $::lpf_r ' + ' '.join(f'[expr {{round({x:.6f}*$::lpf_dbu)}}]' for x in b4),
                      f'set ::lpf_g({g}) [odb::dbGroup_create $::lpf_r "lp_fence_grp_{g}"]'])
        groups.append(g)

    x0, x1 = v['bx']
    for b, (y0, y1) in v['bands'].items():
        assert b in used, b
        box(b, (x0, y0, x1, y1))
    for i, reg in enumerate(('lk', 'sq', 'vc')):
        g = reg + '_rst'
        box(g, v['rst'][reg])
        for h in [f'u_lpr_{reg}_p'] + [f'u_lpr_{reg}_c{k}' for k in range(8 if reg == 'sq' else 4)] + [f'u_lprc_u_l{i}']:
            own[h] = g
    # sanity: fences disjoint
    boxes = [(x0, y0, x1, y1) for (y0, y1) in v['bands'].values()] + list(v['rst'].values())
    for a in range(len(boxes)):
        for c in range(a + 1, len(boxes)):
            p, q = boxes[a], boxes[c]
            assert p[2] <= q[0] or q[2] <= p[0] or p[3] <= q[1] or q[3] <= p[1], (p, q)
    lines += ['array set ::lpf_own {' + ' '.join(f'{k} {g}' for k, g in own.items()) + '}', tail,
              'foreach r {' + ' '.join(groups) + '} {',
              '  if {![info exists ::lpf_n($r)] || $::lpf_n($r) < 1} { error "LP_FENCE: region $r got no landing cells" }',
              '  if {![info exists ::lpf_c($r)]} { set ::lpf_c($r) 0 }',
              '  puts "LP_FENCE $r cells=$::lpf_n($r) read_cone=$::lpf_c($r)"', '}']
    Path(fence).write_text('\n'.join(lines) + '\n')
    print(name, 'fences', groups)
