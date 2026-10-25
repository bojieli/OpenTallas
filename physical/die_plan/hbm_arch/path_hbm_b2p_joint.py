"""Joint current R1 plan postprocess: explicit E-channel track budget and current clock geometry."""
import argparse,copy,json,math,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parents[2]/'tools/die_plan'))
import schema as S
import check as C

def reserve_root_e(plan, need=9500, limit=.55):
    P=S.Plan(plan);t=plan['partition_types']['root'];W,H=t['outline_um']
    tile=[c for c in t['hard_cores'] if c['inst'].startswith('u_tkm_SW_tile')]
    edge=max(c['origin_um'][0]+c['outline_um'][0] for c in tile)
    # M5 remains available to glue over the child cores; only the physically
    # clear exterior strip is claimed on M5. M7 can cross M5-capped children.
    outer=S.usable_tracks(P.layers['M5'],'M5',edge,W)
    start=W
    while start>0:
        cap=outer+S.usable_tracks(P.layers['M7'],'M7',start,W)
        if cap*limit>=need:break
        start=round(max(0,start-8.64),4)
    if cap*limit<need:raise ValueError('root E-channel cannot carry the declared bounded demand')
    prior=copy.deepcopy(t.get('die_ft_bands',[]))
    t['die_ft_bands']=[b for b in prior if b['dir']!='NS']+[
        dict(dir='NS',span_um=[round(edge,4),W],layers=['M5'],die_share=1.0,
             note='R1 joint E-channel: M5 only outside the TKM hard-core field; no M5 claim over children'),
        dict(dir='NS',span_um=[start,W],layers=['M7'],die_share=1.0,
             note='R1 joint E-channel: minimum track-sized M7 span for bounded9500-bit NE landing demand; GRT proof required')]
    return dict(need_b=need,limit=limit,m5_span_um=[edge,W],m7_span_um=[start,W],
                m5_tracks=outer,m7_tracks=cap-outer,capacity_tracks=cap,
                ratio=round(need/cap,6),source='explicit9500-bit NE landing bound; parent net-union audit/GRT remains required')

def selected_strap_abi(plan, out):
    modules={"ot_hgi_coll_tkm_tp192_tile_core__idpin","ot_hgi_coll_tkm_tp192_tile_core__terminal_idpin"}
    changed=[];files=set();instances=set()
    for tn,t in plan["partition_types"].items():
        for c in t.get("hard_cores",[]):
            if c["module"] not in modules:continue
            old=c.get("parent_id_straps",{}).get("tile_tid")
            if old is None or old.get("width")!=6:raise ValueError("selected TKM requires exact6-bit parent tile ID")
            c["parent_id_straps"]={"strap_tile_tid":old}
            files.add(c["pins_file"]);instances.add(c["inst"])
            changed.append(dict(type=tn,inst=c["inst"],id=old["value"],width=6))
    if len(changed)!=32:raise ValueError(f"expected32 selected TKM IDs, found{len(changed)}")
    for rel in files:
        path=out/rel;pins=json.loads(path.read_text())
        got=0
        for pin in pins:
            if pin["name"] in {f"tile_tid[{i}]" for i in range(6)}:
                pin["name"]=pin["name"].replace("tile_tid","strap_tile_tid",1);got+=1
        if got!=6:raise ValueError(f"{rel}: expected6 ID pins, found{got}")
        path.write_text(json.dumps(pins)+"\n")
    cp=out/"core_conns.json";conn=json.loads(cp.read_text())
    for table in conn.values():
        for inst in instances:
            if inst in table and "tile_tid" in table[inst]:
                table[inst]["strap_tile_tid"]=table[inst].pop("tile_tid")
    cp.write_text(json.dumps(conn,indent=1)+"\n")
    removed=[]
    for t in plan["partition_types"].values():
        keep=[]
        for e in t.get("internal_stations",[]):
            if any(e.get("launch","")==inst+".tile_tid" or e.get("capture","")==inst+".tile_tid" for inst in instances):
                removed.append(e.get("conn"));continue
            keep.append(e)
        if "internal_stations" in t:t["internal_stations"]=keep
    return dict(instances=changed,pin_files=sorted(files),removed_legacy_id_stations=removed,
                data_cycle_delta=0,removed_id_face_ff=192,
                scope="exact strap_tile_tid[5:0] only; actual wrapper and six-bit-only SDC exception required before route")

def main():
    a=argparse.ArgumentParser();a.add_argument('--src',required=True);a.add_argument('--out',required=True)
    a.add_argument('--regen-clock',action='store_true');x=a.parse_args()
    src,out=Path(x.src),Path(x.out)
    if out.exists():raise ValueError('new output directory required; prior verdicts are immutable')
    out.mkdir(parents=True)
    for p in src.iterdir():
        if p.name.startswith('g0') or p.name in ('die_plan.json',):continue
        if p.is_dir():shutil.copytree(p,out/p.name)
        else:shutil.copy2(p,out/p.name)
    plan=json.loads((src/'die_plan.json').read_text())
    report={'root_e':reserve_root_e(plan)}
    report["selected_strap_abi"]=selected_strap_abi(plan,out)
    rt=plan['partition_types']['root']
    tk=[c for c in rt['hard_cores'] if c['inst'].startswith('u_tkm_SW_')]
    cent=[sum(c['origin_um'][i]+c['outline_um'][i]/2 for c in tk)/len(tk) for i in (0,1)]
    report['partition_tap_before']=rt['clock']['tap_um']
    rt['clock']['tap_um']=list(S.tap_clear(rt,*cent,clear=8.64))
    report['partition_tap_after']=rt['clock']['tap_um']
    report['clock_metric_note']='Moving a partition tap does not alter fixed sink-pair distance853.38um; actual common-branch repeater graph remains required'
    if x.regen_clock:
        import b2m
        clog=[];report['htree']=b2m.clock(plan,out,clog);report['clock_log']=clog
    P=S.Plan(plan,out/'die_plan.json')
    R=C.Report();report['station_sites']=C.check_station_sites(P,R)
    report['station_findings']=R.items
    report['lane_cycle_delta']={} # No data station or wire topology is altered by the E-track reservation.
    report['scope']='PLAN CANDIDATE ONLY; EW compact-band repair, fixed-core clock graph, G0/G0C and physical gates remain open'
    plan['note']=plan.get('note','')+' | R1 joint prototype: track-sized M7 E landing span, exterior-only M5, fresh clock geometry'
    (out/'die_plan.json').write_text(json.dumps(plan,indent=1)+'\n')
    (out/'joint_report.json').write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps(report,indent=1))
if __name__=='__main__':main()
