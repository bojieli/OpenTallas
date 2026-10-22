#!/usr/bin/env python3
"""H11 r4 (STW-S81c-DIE2-C25 10-22): bind a CLOSED S81 HEAD ctl glue view (R5 M4+M6 E face, or R6 second face) into the
H11 plan.  Writes a copy of the H11 plan with

  * facts['glue_closed'] = {kit, view, record, source, rtl_refs}: hd_bind.py binds the view and sources the glue RTL of
    record (R3 top ot_s81hd_ctl_glue_r3.sv + zones ot_s81hd_glue_rg.sv, preferred over the H10 ot_s81hd_ctl_peer.sv
    glue body; same frozen ports) from the record commit;
  * for an R6 kit: every ctl<->lane endpoint at the glue's R6 pin plan (results/arch/s81_head_1021/glue_r6/
    h11{m,f}_ctl_links_r6.json at --links-ref): ln_draft2 on the S face, ln_mesh4 on the N face (E-end windows), the other
    42 E links re-spread; so the router lands those links at the new faces.  R5 keeps the R3/H11 positions.

Checks: the kit outline equals the H11 ctl reserve; every moved endpoint sits on the ctl boundary of its new face.
Usage: hd_glue_bind_plan.py PLAN OUT --kit s81hd_glue_r6m --record SHA --source SHA [--links-ref SHA]"""
import argparse, json, os, subprocess

GLUE_RTL = ['rtl/dsrom_sys/s81_head/ot_s81hd_glue_rg.sv', 'rtl/dsrom_sys/s81_head/ot_s81hd_ctl_glue_r3.sv']


def show(ref, path):
    gd = os.environ.get('GIT_DIR') or os.environ.get('OT_GIT_DIR')
    cmd = ['git'] + (['--git-dir', gd] if gd else []) + ['show', f'{ref}:{path}']
    return subprocess.run(cmd, check=True, capture_output=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan'); ap.add_argument('out')
    ap.add_argument('--kit', required=True); ap.add_argument('--record', required=True); ap.add_argument('--source', required=True)
    ap.add_argument('--links-ref', default=None)
    a = ap.parse_args()
    p = json.load(open(a.plan)); B = p['blocks']
    ci = [i for i, b in enumerate(B) if b['master'] == 'ot_s81hd_ctl_glue']
    assert len(ci) == 1, ci
    ci = ci[0]; c = B[ci]
    spec = json.loads(show(a.source, f'physical/ref_tile/{a.kit}/spec.json'))
    assert spec['top'] == 'ot_s81hd_ctl_glue' and (spec['outline']['w'], spec['outline']['h']) == (c['w'], c['h']), \
        (a.kit, spec['outline'], c['w'], c['h'])
    moved = []
    if a.kit.startswith(('s81hd_glue_r6', 's81hd_glue_r8')):   # R8 = R6 pin plan + relay stations
        v = a.kit[-1]
        L = json.loads(show(a.links_ref or a.source, f'results/arch/s81_head_1021/glue_r6/h11{v}_ctl_links_r6.json'))
        # only the links R6 moved (E re-spread + the two lanes to N/S); W/lep/spine/seq endpoints stay as the H11 plan
        J = {r['link']: r for r in L['links'] if r['port'].startswith('ln_') and ('r3_pos_um' in r or 'r3_face' in r)}
        assert len(J) == 54, len(J)
        for l in p['links']:
            for k, e in enumerate(l['e']):
                if e[0] != ci or l['i'] not in J:
                    continue
                r = J[l['i']]
                assert r['port'] == e[1], (l['i'], e[1], r['port'])
                old = (l['endpoint_faces'][k], e[2], e[3])
                f, s = r['face'], r['pos_um']
                if f == 'E':
                    e[2], e[3] = round(c['x'] + c['w'], 4), round(c['y'] + s, 4)
                elif f == 'W':
                    e[2], e[3] = round(c['x'], 4), round(c['y'] + s, 4)
                elif f == 'N':
                    e[2], e[3] = round(c['x'] + s, 4), round(c['y'] + c['h'], 4)
                else:
                    e[2], e[3] = round(c['x'] + s, 4), round(c['y'], 4)
                assert 0 < s < (c['w'] if f in 'NS' else c['h']), (l['i'], f, s)
                l['endpoint_faces'][k] = f
                if (f, e[2], e[3]) != old:
                    moved.append(dict(link=l['i'], old=list(old), new=[f, e[2], e[3]]))
        assert sum(1 for m in moved if m['new'][0] in 'NS') == 12, 'R6 moves 2 lanes x 6 links to N/S'
    p['facts']['glue_closed'] = dict(kit=a.kit, view=f'physical/ref_tile/{a.kit}/views/ot_s81hd_ctl_glue', record=a.record,
                                     source=a.source, module='ot_s81hd_ctl_glue', rtl_refs={a.source: GLUE_RTL},
                                     outline_um=[c['w'], c['h']], moved_endpoints=len(moved),
                                     note='H11 r4 (STW-S81c-DIE2-C25): first CLOSED ctl glue view; frozen ports (R3 top)')
    json.dump(p, open(a.out, 'w'), indent=1)
    json.dump(dict(kit=a.kit, moved=moved), open(a.out + '.moved.json', 'w'), indent=1)
    print('HD_GLUE_BIND_PLAN', a.kit, 'record', a.record, 'moved endpoints', len(moved),
          'N/S', sum(1 for m in moved if m['new'][0] in 'NS'))


if __name__ == '__main__':
    main()
