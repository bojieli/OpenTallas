#!/usr/bin/env python3
"""Size a separate S81 column-core / top-transit-channel contract.

This produces a geometry REQUEST, never an adopted layout or timing result.
All original root/pair IDs and body calendars are retained. The full hub is a
fixed obstacle. Core-local return stages in the transit strip become explicit
top-level leaves on their original regional clock, with no added stages.
"""
import argparse
import hashlib
import json
from pathlib import Path

from cluster_extract import frame_members, load_plan


def propose(plan, core_width=1092.096, transit_width=109.728, clearance=8.64):
    assert core_width > 0 and transit_width > 0 and clearance > 0
    fm = frame_members(plan)
    old_columns = sorted({f['x'] for f in plan['frames'].values()})
    gaps = [b-a for a, b in zip(old_columns, old_columns[1:])]
    split = max(range(len(gaps)), key=gaps.__getitem__) + 1
    # Anchor the western outer edge and eastern outer edge. Expand toward hub.
    old_pitch = min(gaps)
    old_width = old_pitch - clearance
    pitch = core_width + transit_width + clearance
    delta = pitch - old_pitch
    shifts = {x: (k * delta if k < split else -(len(old_columns)-k)*delta)
              for k, x in enumerate(old_columns)}
    cores, channels, promoted, affected = [], [], [], []
    for r, rows in sorted(fm.items()):
        f = plan['frames'][str(r)]
        x = f['x'] + shifts[f['x']]
        # Core includes the ingress FIFO below its frame; channel follows all
        # actual root streets, including this ingress access strip.
        y0 = min(i[3] for i in rows)
        y1 = max(i[3]+i[5] for i in rows)
        cores.append(dict(root=r, column_x=f['x'], shift_x=shifts[f['x']],
                          box_um=[x, y0, x+core_width, y1]))
        channels.append(dict(root=r, box_um=[x+core_width, y0, x+core_width+transit_width, y1]))
        for i in rows:
            if i[2]+i[4] > f['x']+core_width+1e-6:
                promoted.append(dict(instance=i[0], master=i[1], root=r,
                                     source_box_um=i[2:6],
                                     clocks='Preserve literal source clock/reset memberships; no new clock inferred',
                                     reason='Native local leaf intersects separately routed transit channel'))
            affected.append(i[0])
    # Every fixed hub/PHY/link block is tested, rather than assuming that a
    # smaller aggregate field area means that all individual slots fit.
    fixed = [i for i in plan['insts'] if not i[8].startswith('frame_') and
             i[7] not in ('stn', 'hstn', 'hend', 'xstg')]
    conflicts = []
    for c in cores+channels:
        x0,y0,x1,y1 = c['box_um']
        for i in fixed:
            dx = min(x1,i[2]+i[4])-max(x0,i[2])
            dy = min(y1,i[3]+i[5])-max(y0,i[3])
            if dx>1e-6 and dy>1e-6:
                conflicts.append(dict(root=c['root'], fixed=i[0], overlap_um2=dx*dy))
    # List source bus incidence; these exact IDs are the compiler's starting
    # point when the promoted leaves are exported from their source cluster.
    names = {p['instance'] for p in promoted}
    buses = [dict(id=b[0], kind=b[1], width=b[2], terminals=b[3])
             for b in plan.get('buses', []) if any(p[0] in names for p in b[3])]
    memberships = {name: [] for name in names}
    for bus in buses:
        if 'clock' in bus['kind'] or 'reset' in bus['kind']:
            for inst, port in bus['terminals']:
                if inst in memberships:
                    memberships[inst].append(dict(bus=bus['id'], kind=bus['kind'],
                                                  width=bus['width'], port=port))
    for item in promoted:
        item['literal_clock_reset_memberships'] = memberships[item['instance']]
    outside = [c for c in cores+channels if min(c['box_um'])<0 or
               c['box_um'][2]>plan['die'][0] or c['box_um'][3]>plan['die'][1]]
    return dict(schema='opentallas.s81.regional_transit_contract.v1', status='REQUEST_NOT_ADOPTED',
                source_scope=plan.get('scope'), die_um=plan['die'], roots=len(fm),
                column_count=len(old_columns), west_columns=split,
                old_pitch_um=old_pitch, requested_pitch_um=pitch,
                core_width_um=core_width, transit_width_um=transit_width,
                column_shifts_um={str(x):dx for x,dx in shifts.items()},
                cores=cores, channels=channels, promoted_local_leaves=promoted,
                promoted_incident_buses=buses,
                fixed_body_conflicts=conflicts, outside_die=outside,
                fixed_instances_checked=[i[0] for i in fixed],
                source_members=len(affected),
                pending=['All existing displaced die-top stations must be replanned INSIDE the reserved channels',
                         'Use actual native leaf outlines and legal orientations; unknown views fail binding',
                         'Native growth inside cores needs a complete leaf-overlap and pin-density audit',
                         'Actual channel tracks/cuts, per-class reach and all changed incident joins are unmeasured',
                         'Literal clocks/reset/PHY and exact compiled latency must be conserved',
                         'No full native or GRT/TT/FF/SS timing claim'])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--transit-width', type=float, default=109.728)
    ap.add_argument('--png')
    args=ap.parse_args()
    result=propose(load_plan(args.plan), transit_width=args.transit_width)
    result['source_sha256']=hashlib.sha256(Path(args.plan).read_bytes()).hexdigest()
    out=Path(args.out);out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result,indent=1)+'\n')
    if args.png:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        fig, ax = plt.subplots(figsize=(13, 10))
        for c in result['cores']:
            x0,y0,x1,y1=c['box_um']
            ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#b9cfe0',edgecolor='#486478',lw=.4))
        for c in result['channels']:
            x0,y0,x1,y1=c['box_um']
            ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#e6ab02',edgecolor='none'))
        for i in load_plan(args.plan)['insts']:
            if i[0].startswith('sp_'):
                ax.add_patch(Rectangle((i[2],i[3]),i[4],i[5],fill=False,edgecolor='#111111',lw=1))
                if i[4] >= 1000 and i[5] >= 80:
                    ax.text(i[2]+i[4]/2,i[3]+i[5]/2,i[0],fontsize=7,ha='center')
        ax.set(xlim=(0,result['die_um'][0]),ylim=(0,result['die_um'][1]),aspect='equal',
               xlabel='um',ylabel='um',title='S81 transit110 geometry REQUEST: 128 cores + separate gold channels\n'
               f'Fixed body conflicts {len(result["fixed_body_conflicts"])}, outside {len(result["outside_die"])}; '
               f'{len(result["promoted_local_leaves"])} local leaves need explicit top ownership\n'
               'No native-growth, cut, reach, clock/reset, compiler or routed timing qualification')
        fig.tight_layout(); fig.savefig(args.png,dpi=140); plt.close(fig)
    print('TRANSIT_REQUEST roots',result['roots'],'columns',result['column_count'],
          'fixed conflicts',len(result['fixed_body_conflicts']),'outside',len(result['outside_die']),
          'promoted leaves',len(result['promoted_local_leaves']))


if __name__=='__main__':
    main()
