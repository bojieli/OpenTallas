#!/usr/bin/env python3
"""Q-B2 10-16: per-half source-bound path ledger and phase constants from an ACTUAL full-graph allocator run.

Inputs are the allocator's own outputs (b2_allocator_reprice.py --full-graph --production --compact-selector):
allocator_graph.json (canonical graph) and allocator_stage_of.json (r21_stage_of).  Stage convention (allocator
S, f081100e8): a direct wire is S = 1 and adds no external register; a relayed bus adds S - 1 edges; a registered fork
tree path of k legs adds sum(S) - 1 edges (the k - 1 fork registers counted exactly once, plus every relay).

Derived constants (fail closed, never a zero/fake calibration):
  controller_lnk  L = (TC + AM) / 2           TC = tc_to_port, AM = am_to_controller (equal across six halves)
  train_edges     TE = 14 + TC + RQ - 1 - TAG - CMD   (phase_protocol.validate_calibration), >= 2, equal for six
  halfband_lnk    (F + R) / 2 for HB0's band<->upper round trip (pword forward F, upper return R), applied to all six
                  halves so the six result ages stay equal (b0 = 0 halves ignore the return)
  controller_clnk CLNK = LC - TC (selects made CLNK edges early meet the port's tree words at the lanes), >= 0;
                  and the upper selects must satisfy SEL = LC + 3 + F (tb_qfd_halfband control law)
  xpf_transport   stage_of[xs_pf] - 1 (controller xpf -> tap)
Odd round trips and negative CLNK are reported as STRUCTURAL (need a real pad stage), never rounded.
"""
import argparse, hashlib, json, sys
from pathlib import Path

GROUPS = ('tc_to_port', 'am_to_controller', 'rq_to_train', 'tag_copy_to_issuer', 'issuer_to_train', 'lc_to_halfband',
          'selector_to_upper', 'upper_to_halfband', 'rb_to_vm')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ledger(graph, stage_of):
    buses = {b[0]: b for b in graph['buses']}
    S = lambda b: int(stage_of.get(b, 1))

    def direct(bid):
        if bid not in buses:
            raise ValueError(f'missing actual bus {bid}')
        _, _, n, es = buses[bid]
        return dict(source_pin='.'.join(es[0]), sink_pin='.'.join(es[-1]), bits=n, edges=S(bid) - 1,
                    stage_record_ids=[bid], stages=[S(bid)])

    def tree(prefix, sink, field):
        """registered fork path ending at (sink, field): walk back to the issuer."""
        path, ep = [], (sink, field)
        while True:
            inc = [b for b in buses.values() if tuple(b[3][-1]) == ep]
            if len(inc) != 1:
                raise ValueError(f'nonunique registered path into {ep}: {[b[0] for b in inc]}')
            b = inc[0]
            path.insert(0, b[0])
            src = tuple(b[3][0])
            if src[0].startswith(prefix + '_fork_'):
                ep = (src[0], 'a_' + field)
            else:
                break
        return dict(source_pin='.'.join(buses[path[0]][3][0]), sink_pin=f'{sink}.{field}', bits=buses[path[-1]][2],
                    edges=sum(S(b) for b in path) - 1, stage_record_ids=path, stages=[S(b) for b in path])

    halves = {}
    for hb in range(6):
        r = dict(
            tc_to_port=direct(f'b2_tc_{hb}'),
            am_to_controller=direct(f'b2_am_{hb}'),
            rq_to_train=direct(f'b2_rq_{hb}'),
            tag_copy_to_issuer=direct('b2_source_tag_v'),
            me_copy_to_issuer=direct('b2_source_me_go'),
            tw_port_to_halfband=direct(f'b2_tw_{hb}'),
            ty_halfband_to_port=direct(f'b2_ty_{hb}'),
            issuer_to_train=tree('command', f'sp_halfres_{hb}', 'train_start'),
            lc_to_halfband=direct(f'b2_lc_{hb}'),
            rb_to_vm=direct(f'b2_rb_{hb}'))
        # every command field must see the same registered age (equal-age group across fields)
        for f in ('train_count', 'capture_stride', 'payload_write', 'slot_count'):
            e = tree('command', f'sp_halfres_{hb}', f)['edges']
            if e != r['issuer_to_train']['edges']:
                raise ValueError(f'HB{hb} command field {f} age {e} != train_start {r["issuer_to_train"]["edges"]}')
        fwd = [direct(f'b2_pword_{hb}_{k}{u}') for u in range(8) for k in ('l', 'v')]
        r['pword_forward'] = dict(edges=max(x['edges'] for x in fwd), min_edges=min(x['edges'] for x in fwd),
                                  stage_record_ids=[x['stage_record_ids'][0] for x in fwd])
        halves[hb] = r
    sel = [tree('selector', f'tt_up4_leaf{u}', 'sel4') for u in range(8)]
    ret = [direct(f'b2_return_{k}{u}') for u in range(8) for k in ('l', 'use', 'v')]
    for hb in range(6):
        halves[hb]['selector_to_upper'] = max(sel, key=lambda x: x['edges'])
        halves[hb]['upper_to_halfband'] = max(ret, key=lambda x: x['edges'])
    return halves, sel, ret, (direct('xs_pf') if 'xs_pf' in buses else None)


def derive(halves, sel, ret, xpf):
    issues, out = [], {}
    def same(key):
        v = {halves[h][key]['edges'] for h in range(6)}
        if len(v) != 1:
            issues.append(f'{key} ages differ across halves {sorted(v)}: structural equal-age pad required')
        return max(v)
    TC, AM, RQ, LC, RB, CMD = (same(k) for k in ('tc_to_port', 'am_to_controller', 'rq_to_train', 'lc_to_halfband',
                                                    'rb_to_vm', 'issuer_to_train'))
    TAG = halves[0]['tag_copy_to_issuer']['edges']
    for k in ('tw_port_to_halfband', 'ty_halfband_to_port'):
        e = {halves[h][k]['edges'] for h in range(6)}
        if e != {0}:
            issues.append(f'{k} has relay edges {sorted(e)}: the abutted port<->halfband contact must be a direct wire '
                          '(its age is inside the qualified port/lane composition); re-home or pad structurally')
    ME = halves[0]['me_copy_to_issuer']['edges']
    if ME > TAG:
        issues.append(f'ME descriptor copy age {ME} > tag age {TAG}: the issuer would see the tag before its descriptor')
    F = {h: halves[h]['pword_forward']['edges'] for h in range(6)}
    if len(set(F.values())) != 1 or any(halves[h]['pword_forward']['min_edges'] != F[h] for h in range(6)):
        issues.append(f'pword forward ages not equal across the six halves / eight leaves {F}: the upper combines them '
                      'in one cycle; structural equal-age pads required')
    Fm = max(F.values())
    if len({x['edges'] for x in sel}) != 1:
        issues.append(f'selector ages differ across the eight upper leaves {sorted({x["edges"] for x in sel})}')
    if len({x['edges'] for x in ret}) != 1:
        issues.append(f'upper return ages differ {sorted({x["edges"] for x in ret})}')
    SEL = max(x['edges'] for x in sel); R = max(x['edges'] for x in ret)
    if (TC + AM) % 2:
        issues.append(f'TC+AM = {TC + AM} is odd: one real pad edge on the AM return group is required')
    L = (TC + AM) // 2
    TE = 14 + TC + RQ - 1 - TAG - CMD
    if TE < 2:
        issues.append(f'TRAIN_EDGES {TE} < 2: command path too slow against RQ; structural')
    if (Fm + R) % 2:
        issues.append(f'band<->upper round trip F+R = {Fm + R} odd: one real pad edge required')
    HL = (Fm + R) // 2
    if not 0 <= HL <= 54:
        issues.append(f'halfband lnk {HL} outside proved 0..54')
    # lane control (lc) must meet the port's tree words (tc -> port -> tw): the controller makes its selects CLNK
    # edges early, so CLNK = LC - TC (ot_qfd_tt_ctl_b2: XD - CLNK; results stay 5 + 2 LNK behind).
    CL = LC - TC
    if CL < 0:
        issues.append(f'CLNK = LC {LC} - TC {TC} = {CL} < 0: lane control would arrive after the tree words; pad LC by {-CL}')
    # the upper's selects (compact selector-4 fork tree: 3 fork registers) must meet the halfband words at the upper:
    # tb_qfd_halfband law: upper control = lane control + 3 + forward word link
    if SEL != LC + 3 + Fm:
        issues.append(f'selector age {SEL} != LC {LC} + 3 + F {Fm} = {LC + 3 + Fm}: structural pad on the '
                      f'{"selector" if SEL < LC + 3 + Fm else "lane-control/word"} path required')
    out = dict(TC=TC, AM=AM, RQ=RQ, LC=LC, RB=RB, CMD=CMD, TAG=TAG, ME=ME, F=Fm, R=R, SEL=SEL,
               controller_lnk=L, controller_clnk=CL, train_edges=TE, halfband_lnk=HL,
               xpf_transport_edges=(xpf['edges'] if xpf else None))
    return out, issues


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('allocated', type=Path, help='allocator --out dir (allocator_graph.json, allocator_stage_of.json)')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    g = a.allocated / 'allocator_graph.json'; s = a.allocated / 'allocator_stage_of.json'
    graph = json.loads(g.read_text()); stage_of = json.loads(s.read_text())
    halves, sel, ret, xpf = ledger(graph, stage_of)
    consts, issues = derive(halves, sel, ret, xpf)
    rec = dict(schema='qwen-b2-allocated-path-ledger-v1', allocator_graph_sha256=sha(g), allocator_stage_of_sha256=sha(s),
               stage_convention='edges = S - 1 per relayed bus; fork tree path = sum(S) - 1',
               halves={str(h): {k: v for k, v in r.items()} for h, r in halves.items()},
               selector_paths=sel, upper_return_paths=ret, xpf=xpf, constants=consts,
               structural_issues=issues, status='LEDGER_OK' if not issues else 'STRUCTURAL_PAD_REQUIRED')
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(constants=consts, issues=issues), indent=1))
    return 0 if not issues else 1


if __name__ == '__main__':
    sys.exit(main())
