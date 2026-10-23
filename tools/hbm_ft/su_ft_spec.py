#!/usr/bin/env python3
"""FT-HBM-SU: SU pgslice feedthrough spec (16 x ot_hbm_su_static_pgslice_lg__pv*, HBM r18h5).

Inputs (all read-only):
  --ftspec-dir  FT-TOOL plan_v2 per-block ftspecs (opentallas.die_feedthrough.ftspec.v1; die-frame track assignment,
                per-face port legalisation, in+out registers + one every <= reach, repeater sites <= 450 um)
  --paths       FT-HBM lane census paths (lane_census_paths_r18h5.json): s1000 = stages straight through blocks,
                r1000 = stages along today's channel route, both at 1.0 mm hops.  gain = r1000 - s1000.
  --domains     lane_domains.py table (source bus -> stream / serial / hbm die clock)
  --insts       coordinator insts.tsv (name master x y w h orient)
Selection per instance:
  all          every lane FT-TOOL routes straight through the block
  gain         lanes whose straight route saves >= 1 stage (FT-HBM census)            <- recommended ft set
  gain_stream  gain lanes on the stream die clock (one ft clock root ck_ft, 833.333 ps) <- pilot kit set
Writes the spec JSON (--out) and, for --pilot, a filtered ftspec.v1 (--pilot-out) that pushdown.py consumes.
"""
import argparse, collections, glob, json, math, os

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--ftspec-dir', required=True); ap.add_argument('--paths', required=True)
ap.add_argument('--domains', required=True); ap.add_argument('--insts', required=True)
ap.add_argument('--pilot', default='su_SW3'); ap.add_argument('--pilot-variant', default='ot_hbm_su_static_pgslice_rgf_lp__ftsw3')
ap.add_argument('--out', required=True); ap.add_argument('--pilot-out', required=True)
ap.add_argument('--pitch', type=float, default=0.08); ap.add_argument('--occ', type=float, default=0.6)
a = ap.parse_args()

P = json.load(open(a.paths))
gain = collections.defaultdict(int)
for p in P:
    k = (p['src'], p['dst']); gain[k] = max(gain[k], p['r1000'] - p['s1000'])
DOM = json.load(open(a.domains))['domains']
INST = {}
for l in open(a.insts):
    f = l.rstrip('\n').split('\t')
    if f[1].startswith('ot_hbm_su_static_pgslice_lg'):
        INST[f[0]] = dict(master=f[1], x=float(f[2]), y=float(f[3]), w=float(f[4]), h=float(f[5]), orient=f[6])


def cls(m):            # synthesised classes of the 16 parameter variants (r18h5 views/synth meta std_area_um2)
    pv = int(m.split('__pv')[1])
    return 'Q0G0' if pv == 0 else ('heavy_G01' if pv < 8 else 'light_G23')


def cap(face, w, h):   # M8 tracks across an E/W face (horizontal), M9 across N/S at occupancy occ
    return (h if face in 'WE' else w) / a.pitch * a.occ


insts, pilot = {}, None
for f in sorted(glob.glob(os.path.join(a.ftspec_dir, 'su_*.json'))):
    s = json.load(open(f)); b = s['block']; W, H = s['outline']; ports = {q['name']: q for q in s['ports']}
    sel = collections.defaultdict(list)
    for p in s['paths']:
        g = gain.get((p['src'].split('/')[0], p['dst'].split('/')[0]), 0)
        d = DOM.get(p['src'], '?')
        rec = dict(path=p['path'], lane=p['lane'], src=p['src'], dst=p['dst'], bits=p['bits'], domain=d, gain_stages=g,
                   in_port=dict((k, ports[p['in']][k]) for k in ('name', 'face', 'lo', 'hi', 'layer')),
                   out_port=dict((k, ports[p['out']][k]) for k in ('name', 'face', 'lo', 'hi', 'layer')),
                   regs=p['stages'], latency_cycles=p['stages'], len_um=p['len_um'], rep_sites=p['rep_sites'],
                   regs_um=p['regs_um'], die_in_xy=ports[p['in']]['die_xy'], die_out_xy=ports[p['out']]['die_xy'])
        sel['all'].append(rec)
        if g > 0:
            sel['gain'].append(rec)
            if d == 'stream':
                sel['gain_stream'].append(rec)

    def faces(rs):
        c = collections.Counter()
        for r in rs:
            c[r['in_port']['face']] += r['bits']; c[r['out_port']['face']] += r['bits']
        return {k: dict(bits=v, ratio=round(v / cap(k, W, H), 3)) for k, v in sorted(c.items())}
    I = INST[b]
    insts[b] = dict(master=s['master'], cls=cls(s['master']), slot=[I['x'], I['y'], W, H], orient=s['orient'],
                    ftspec_variant=s['variant'],
                    sets={k: dict(paths=len(v), bits=sum(r['bits'] for r in v), bit_regs=sum(r['bits'] * r['regs'] for r in v),
                                  gain_stages=sum(r['gain_stages'] for r in v), faces=faces(v),
                                  domains=dict(collections.Counter(r['domain'] for r in v)),
                                  max_face_ratio=max([x['ratio'] for x in faces(v).values()] or [0]))
                          for k, v in sel.items()},
                    gain_paths=sel['gain'])
    if b == a.pilot:
        keep = {r['path'] for r in sel['gain_stream']}
        q = dict(s); q['variant'] = a.pilot_variant
        q['paths'] = [p for p in s['paths'] if p['path'] in keep]
        names = {p['in'] for p in q['paths']} | {p['out'] for p in q['paths']}
        q['ports'] = [x for x in s['ports'] if x['name'] in names]
        q['clock'] = 'block'
        q['ft_bits'] = sum(p['bits'] for p in q['paths']); q['ft_bit_stages'] = sum(p['bits'] * p['stages'] for p in q['paths'])
        q['note'] = (f'FT-HBM-SU pilot: FT-TOOL plan_v2 ftspec {s["variant"]} of {b} filtered to the gain lanes on the '
                     'stream die clock (su_ft_spec.py gain_stream); port ranges unchanged (die-frame aligned with the '
                     'neighbours); stations = ot_hbm_rly (the die relay function) on the ft root ck_ft / reset rs_ft')
        pilot = q
tot = {k: dict(paths=sum(v['sets'].get(k, {}).get('paths', 0) for v in insts.values()),
               bits=sum(v['sets'].get(k, {}).get('bits', 0) for v in insts.values()),
               gain_stages=sum(v['sets'].get(k, {}).get('gain_stages', 0) for v in insts.values()))
       for k in ('all', 'gain', 'gain_stream')}
over = {k: sorted([(b, v['sets'][k]['max_face_ratio']) for b, v in insts.items() if v['sets'].get(k, {}).get('max_face_ratio', 0) > a.occ],
                  key=lambda x: -x[1]) for k in ('all', 'gain')}
out = dict(schema='opentallas.hbm_ft.su_pgslice_ft_spec.v1', die='HBM r18h5 (die_case_v16, 26x33 mm)',
           master_re='^ot_hbm_su_static_pgslice_lg__pv', inputs=dict(ftspec_dir=a.ftspec_dir, paths=a.paths, domains=a.domains, insts=a.insts),
           totals=tot, faces_over_occupancy=over, instances=insts, pilot=dict(block=a.pilot, variant=a.pilot_variant,
           paths=len(pilot['paths']), bits=pilot['ft_bits'], bit_stages=pilot['ft_bit_stages'], ports=len(pilot['ports'])))
out['notes'] = {
 'variants': 'the 16 masters __pv0..15 differ only in QID/G parameters but synthesise to 3 classes (r18h5 views/synth std_area_um2: '
             'pv0 Q0G0 583.2k, pv1-7 heavy G0/1 534.6k, pv8-15 light G2/3 287.7k; each + 192 SRAM 128x256 = 0.75 mm2). With STRAP=1 '
             '(pos pin = {qid,g}) one physical kit per class; ft ports make every INSTANCE its own variant (slot y offsets of 150 um '
             'between g0/g1 columns, per-instance lane loads), as the 16 SYNTH pv cells already are.',
 'ft_set': 'recommended = gain (lanes whose straight route saves >= 1 stage at 1.0 mm hops); all-lanes overloads 8 faces (>0.6). '
           'pilot = gain lanes on the stream die clock (one ft root ck_ft 833.333 ps); serial (6%) / unresolved (4%) lanes stay in '
           'the channels until a second ft clock is added.',
 'ports': 'E-W ft on M8 (W/E faces), N-S ft on M9 (N/S faces); ranges = FT-TOOL plan_v2 per-face legalised, die-frame tracks: '
          '929 of 935 neighbour ft legs line up at 0.0 um in die coordinates (the 2.2-mm column gaps / 459-um row gaps between SU slots '
          'carry the die-level hop, 1 relay at most at 1.0-1.2 mm reach).',
 'registers': 'in + out registered at the pins (pin-register rule), one more every <= 1.0 mm (E-W 1797 um: 3 regs / latency 3 '
              'cycles incl. the pin regs; N-S 2825 um: 4 regs), repeater sites <= 450 um (rep_sites per path; block P&R inserts them). '
              'latency_cycles per path = regs (each register is one die-relay stage moved inside the block: static schedule takes '
              'FT-TOOL hbm_schedule.tsv stages_new).',
 'stations': 'ot_hbm_ft_stn #(W) = the hbfd_rly die relay function (posedge, async clear), one relayed clear per <= 32 '
             'flops; rs_ft -> 3 ot_rst_relay levels (2 / 40 / 1,176 groups for the pilot, <= 32 loads a net, native census); '
             'release 9 ck_ft edges after rs_ft (die relay 3): lanes carry zeros until then.',
 'blocker': 'pre_route_gate native census (<= 32 loads) on the light base rgf_lp REFUSES before floorplan: 282 base-kit nets over '
            '32 (u_lpl_*_r.rc read counters up to 4,181 loads, u_sout.dd 512, u_rg*.src1_c 64, KIND0 vm_we 93-96, pos_r* 41-49, '
            'ck_r* as data 40); base kit is functionally frozen and predates the census: needs a fanout/replication fix by the '
            'light-kit owner (claude/hbm-pglg-d4h-1021) before any rgf_lp kit (with or without ft) can harden.',
 'kit': 'physical/ref_tile/hbm_su_pgslice_lg_ft_d4g: light landed-region slice (rgf_lp, 32 KIND0 + 32 CLOSED bank6_clock) re-laid in '
        'the die slot 1797.12 x 2825.28 (the light kit 1235.52 x 3045.6 did not fit); children 2.52 mm2 = 49.6% of the slot, '
        'parent fill ~52-55% with glue + ft (below the 60-70% target because the hard children are themselves ~45% dense; a '
        'narrower outline cannot hold 3 pair columns, 2 columns need 16 rows > 2825 um). PG top M7 (pins), signals M2-M7, '
        'ft nets M8/M9 inside corridors only (pushdown FASTROUTE fence + ft_audit), abstract = exact routed shapes (ref_tile export).',
 'not_covered': 'heavy G0/1 and Q0G0 classes need hardened KIND1/KIND2 leaves (none CLOSED); the light rgf_lp interface/latency '
                'differs from the r18h5 die binding (monolithic scoped_d4g pgslice.sv SYNTH): binding needs the lp record offsets '
                'in the SU schedule + the sibling stream tile (HBM-PGLG8 / codex pgstream-safe3-bind).'}
json.dump(out, open(a.out, 'w'), indent=1)
json.dump(pilot, open(a.pilot_out, 'w'), indent=1)
print(json.dumps(tot)); print('over', json.dumps(over)); print('pilot', json.dumps(out['pilot']))
