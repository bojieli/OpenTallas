#!/usr/bin/env python3
"""Diagnostic overlay of source-local real leaves on the selected r14 placement.
No functional hardening, timing qualification or replacement outer architecture.
"""
import argparse, collections, hashlib, json, math, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_accel_die_fp as H
import dsrom_s81_fulldie as S

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def prepare(out):
    out.mkdir(parents=True, exist_ok=True)
    m = H.build(H.ADOPTED)
    masters = H.masters(m, 1)
    widths = H.port_widths(m, 1)
    pins = {name: {p for p, _, _ in S.pin_rects(mst, 1, {pt: widths.get((name, pt), 0) for pt in mst.order})} for name, mst in masters.items()}
    real_ports = H.real_ports()
    by = {i.name:i for i in m['insts']}
    missing = []
    for bid, cls, bits, eps in m['buses']:
        for inst, port in eps:
            master = by[inst].master
            names = real_ports.get(master, {}).get(port, [f'{port}[{i}]' for i in range(bits)])
            available = set(S.real_lef(H.REAL[master])['pins']) if master in H.REAL else pins[master]
            absent = [n for n in names[:bits] if n not in available]
            if absent: missing.append(dict(bus=bid, instance=inst, port=port, count=len(absent), examples=absent[:8]))
    # Compare complete generated pin spans with centroid-only wire pricing.
    spans = {}
    pin_rectangles = {}
    for master, mst in masters.items():
        groups = collections.defaultdict(list)
        pin_rectangles[master] = {}
        for name, layer, rect in S.pin_rects(mst, 1, {pt: widths.get((master, pt), 0) for pt in mst.order}):
            groups[name.rsplit('[',1)[0]].append(rect)
            pin_rectangles[master][name] = rect
        spans[master] = {k:[min(r[0] for r in v),min(r[1] for r in v),max(r[2] for r in v),max(r[3] for r in v)] for k,v in groups.items()}
    segment_bounds=[]
    def absolute_box(inst, port):
        it=by[inst]
        if it.master in H.REAL:
            rs=[S.real_lef(H.REAL[it.master])['pins'][p][1] for p in real_ports[it.master][port]]
            a,b,c,d=min(r[0] for r in rs),min(r[1] for r in rs),max(r[2] for r in rs),max(r[3] for r in rs)
        else:a,b,c,d=spans[it.master][port]
        if it.orient in ('MY','R180'):a,c=it.w-c,it.w-a
        if it.orient in ('MX','R180'):b,d=it.h-d,it.h-b
        return [it.x+a,it.y+b,it.x+c,it.y+d]
    def indexed_centres(inst, port, bits):
        it=by[inst]
        if it.master in H.REAL:
            r=S.real_lef(H.REAL[it.master])['pins']; rs=[r[p][1] for p in real_ports[it.master][port][:bits]]
        else:rs=[pin_rectangles[it.master][f'{port}[{q}]'] for q in range(bits)]
        out=[]
        for a,b,c,d in rs:
            x,y=(a+c)/2,(b+d)/2
            if it.orient in ('MY','R180'):x=it.w-x
            if it.orient in ('MX','R180'):y=it.h-y
            out.append((it.x+x,it.y+y))
        return out
    for bid,cls,bits,eps in m['buses']:
        root=absolute_box(*eps[0])
        for peer in eps[1:]:
            dest=absolute_box(*peer)
            centre=abs((root[0]+root[2]-dest[0]-dest[2])/2)+abs((root[1]+root[3]-dest[1]-dest[3])/2)
            bound=max(abs(a-c)+abs(b-d) for a in (root[0],root[2]) for b in (root[1],root[3]) for c in (dest[0],dest[2]) for d in (dest[1],dest[3]))
            rc=indexed_centres(*eps[0],bits);dc=indexed_centres(*peer,bits)
            paired_max=max(abs(a-c)+abs(b-d) for (a,b),(c,d) in zip(rc,dc))
            segment_bounds.append(dict(actual_bit_paired_Manhattan_max_um=round(paired_max,3),paired_geometric_430p56_stage_upper=(None if cls=="clock_trunk" else math.ceil(paired_max/H.LINK_STAGE_UM)),bus=bid,kind=cls,bits=bits,endpoints=[eps[0],peer],centroid_Manhattan_um=round(centre,3),pin_span_Manhattan_upper_um=round(bound,3),pin_spread_additional_upper_um=round(bound-centre,3),geometric_430p56_stage_upper=(None if cls=="clock_trunk" else math.ceil(bound/H.LINK_STAGE_UM)),pipeline_edges_installed=False))
    channel_faces=[]
    for st,g in m['groups'].items():
        smboxes=[it.box() for it in g['sms']]
        # The hub quadrants and row boundary are measured from placed boxes.
        hub=m['hub']['su_'+st]
        gap=min(z[1] for z in smboxes)-(hub.y+hub.h) if st[0]=='N' else hub.y-max(z[3] for z in smboxes)
        for it in g['sms']:
            face='E' if it.orient in ('MY','R180') else 'W'
            expected='E' if st[1]=='W' else 'W'
            channel_faces.append(dict(instance=it.name,orientation=it.orient,activation_face=face,face_toward_spine=face==expected,row_hub_gap_um=round(gap,3),gap_positive=gap>0))
    source = ROOT / 'results/uarch/hbm_accel_fulldie_inputs_20261004/providers/sm_r2/routes/sm_r2/fp/macro_place.tcl'
    slots = [(key, float(x), float(y)) for key,x,y in re.findall(r'\{((?:bd|tc):[^}]+)\}\s+\{([\d.]+) ([\d.]+)\}', source.read_text())]
    assert collections.Counter(k.split(':')[0] for k,_,_ in slots) == {'bd':32, 'tc':32}
    leaves=[]
    for parent in m['insts']:
        if parent.master != 'hfd_sm': continue
        for key,x,y in slots:
            kind=key.split(':')[0]; master='ot_hbm_accel_bd_col' if kind=='bd' else 'ot_hbm_accel_tc16'
            rel=f'physical/hbm_accel_sm_views/{master}/{master}.lef'
            v=S.real_lef(rel)
            # Source-local origin is the LL of an R0 macro; mirror the whole bbox.
            xx=parent.w-x-v['w'] if parent.orient in ('MY','R180') else x
            yy=parent.h-y-v['h'] if parent.orient in ('MX','R180') else y
            leaves.append(dict(name=parent.name+'__'+key.replace(':','_'), parent=parent.name, master=master, x=round(parent.x+xx,3), y=round(parent.y+yy,3), orient=parent.orient, slot=key))
    for master in ('ot_hbm_accel_bd_col','ot_hbm_accel_tc16'):
        p=ROOT/f'physical/hbm_accel_sm_views/{master}/{master}.lef'
        (out/(master+'.lef')).write_bytes(p.read_bytes())
    inv=[dict(name=i.name,master=i.master,kind=i.kind,box_um=list(i.box()),orient=i.orient,view=('real' if i.master in H.REAL else 'PLACEHOLDER_OPEN')) for i in m['insts']]
    paths=H.manhattan_paths(m)
    long_segments=[]
    for k,v in paths.items():
        if v['stages_430']>4: long_segments.append(dict(path=k,**v))
    # Native overlay replaces opaque SM placeholder instances by real leaf geometry.
    # Their functional shell ports are checked above, never treated as real hardened SM pins.
    cmds=['set blk [ord::get_db_block]', 'set db [ord::get_db]', 'set lib [lindex [$db getLibs] end]']
    cmds += [f'set i [$blk findInst {p.name}]; if {{$i eq "NULL"}} {{error "missing {p.name}"}}; odb::dbInst_destroy $i' for p in m['insts'] if p.master=='hfd_sm']
    for l in leaves:
        cmds.append(f'set master [$db findMaster {l["master"]}]; set i [odb::dbInst_create $blk $master {l["name"]}]; $i setOrient {l["orient"]}; $i setLocation {round(l["x"]*1000)} {round(l["y"]*1000)}; $i setPlacementStatus FIRM')
    cmds += ['write_db /work/real_leaf_overlay.odb', 'write_def /work/real_leaf_overlay.def', 'puts "OT_REAL_LEAF_OVERLAY_DONE"']
    (out/'overlay.tcl').write_text('\n'.join(cmds)+'\n')
    rec=dict(scope='PLACEMENT_DEFECT_HUNT_ONLY',selected_source='77ef36ea3/r14b',geometry=H._legality(m),variant=m['variant'],replicated_missing_pins=missing,row_hub_face_checks=channel_faces,wire_segment_pin_span_bounds=segment_bounds,inventory=inv,real_leaf_count=len(leaves),real_leaves=leaves,source_placement_sha256=sha(source),real_LEF_sha256={p.name:sha(p) for p in out.glob('*.lef')},station_closing_pitch_um=H.LINK_STAGE_UM,modeled_waypoint_spacing_um=H.WAYPOINT_UM,paths=paths,paths_above_four_430um_stages=long_segments,SSFF_signoff=False,IR_signoff=False,functional_real_leaf_connections=False,remaining_SM_internal_abstracts='128 xstore and 10 ring macros per SM plus logic/protection open; not replaced with fake hardware')
    (out/'inventory.json').write_text(json.dumps(rec,indent=1)+'\n')
    print(json.dumps(dict(real_leaf_count=len(leaves),missing_pin_groups=len(missing),geometry=rec['geometry'])))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.out)
