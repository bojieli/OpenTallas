# DIE-HEAD-ROUTE-1 s20 unit database. env: CKPT UNIT_ID UNITS_DIR MODE(a|b) OUT_ODB R_UM
# a: full-die DB, every routable net that is not a unit net marked special (no shapes). b: geometric crop (unit box +- R snapped out to 10.8 um gcells,
# grown to whole kept instances), instances that intersect kept, PDN clipped, tracks/rows clipped, NO boundary pins (reach check guarantees own nets stay inside).
import os,json,sys
import odb
uid=os.environ['UNIT_ID']; ud=os.environ['UNITS_DIR']; mode=os.environ['MODE']; R=float(os.environ.get('R_UM','453.6'))
db=odb.dbDatabase.create(); odb.read_db(db,os.environ['CKPT']); blk=db.getChip().getBlock(); dbu=blk.getDbUnitsPerMicron()
own=set(open(f'{ud}/nets_{uid}.txt').read().split())
unit=[u for u in json.load(open(f'{ud}/units.json'))['units'] if u['id']==uid][0]
nmark=0; nown=0
for n in blk.getNets():
    if n.getSigType() not in ('SIGNAL','CLOCK') or n.isSpecial(): continue
    if n.getName() in own: nown+=1
    else: n.setSpecial(); nmark+=1
print(f'UNIT {uid} mode {mode}: own nets in db {nown} of {len(own)}; others marked special {nmark}',flush=True)
if mode=='b':
    G=10800
    bx=[int(round(v*dbu)) for v in unit['box_um']]; Rd=int(round(R*dbu))
    x0=(bx[0]-Rd)//G*G; y0=(bx[1]-Rd)//G*G; x1=-(-(bx[2]+Rd)//G)*G; y1=-(-(bx[3]+Rd)//G)*G
    die=blk.getDieArea(); x0=max(die.xMin(),x0); y0=max(die.yMin(),y0); x1=min(die.xMax(),x1); y1=min(die.yMax(),y1)
    keep=[]; drop=[]
    for i in blk.getInsts():
        b=i.getBBox()
        (keep if not(b.xMax()<=x0 or b.xMin()>=x1 or b.yMax()<=y0 or b.yMin()>=y1) else drop).append(i)
    for i in keep:
        b=i.getBBox(); x0=min(x0,b.xMin()); y0=min(y0,b.yMin()); x1=max(x1,b.xMax()); y1=max(y1,b.yMax())
    x0=max(die.xMin(),x0//G*G); y0=max(die.yMin(),y0//G*G); x1=min(die.xMax(),-(-x1//G)*G); y1=min(die.yMax(),-(-y1//G)*G)
    for i in drop: odb.dbInst.destroy(i)
    for bt in list(blk.getBTerms()):
        b=bt.getBBox()
        if b.xMax()<=x0 or b.xMin()>=x1 or b.yMax()<=y0 or b.yMin()>=y1: odb.dbBTerm.destroy(bt)
    ndel=0
    for n in list(blk.getNets()):
        if n.getITermCount()==0 and n.getBTermCount()==0 and n.getSigType() in ('SIGNAL','CLOCK') and not n.getSWires(): odb.dbNet.destroy(n); ndel+=1
    inside=lambda r: r.xMin()>=x0 and r.xMax()<=x1 and r.yMin()>=y0 and r.yMax()<=y1
    overlaps=lambda r: not(r.xMax()<=x0 or r.xMin()>=x1 or r.yMax()<=y0 or r.yMin()>=y1)
    psb=dict(kept=0,clipped=0,removed=0)
    for n in blk.getNets():
        if not n.isSpecial(): continue
        for sw in n.getSWires():
            for sb in list(sw.getWires()):
                r=odb.Rect(sb.xMin(),sb.yMin(),sb.xMax(),sb.yMax())
                if inside(r): psb['kept']+=1; continue
                if sb.isVia() or not overlaps(r): odb.dbSBox_destroy(sb); psb['removed']+=1; continue
                lay,st=sb.getTechLayer(),sb.getWireShapeType()
                cx0,cy0,cx1,cy1=max(r.xMin(),x0),max(r.yMin(),y0),min(r.xMax(),x1),min(r.yMax(),y1)
                odb.dbSBox_destroy(sb); odb.dbSBox_create(sw,lay,cx0,cy0,cx1,cy1,st); psb['clipped']+=1
    rows=[(r.getName(),r.getSite(),r.getOrigin(),r.getOrient(),r.getDirection(),r.getSiteCount(),r.getSpacing()) for r in blk.getRows()]
    for r in list(blk.getRows()): odb.dbRow.destroy(r)
    for name,site,(ox,oy),orient,direc,cnt,sp in rows:
        if oy<y0 or oy+site.getHeight()>y1: continue
        sx=ox+-(-(x0-ox)//sp)*sp if x0>ox else ox
        k=(min(x1,ox+cnt*sp)-sx)//sp
        if k>0: odb.dbRow.create(blk,name,site,sx,oy,orient,direc,k,sp)
    for tg in list(blk.getTrackGrids()):
        lay=tg.getTechLayer(); px=[tg.getGridPatternX(k) for k in range(tg.getNumGridPatternsX())]; py=[tg.getGridPatternY(k) for k in range(tg.getNumGridPatternsY())]
        odb.dbTrackGrid.destroy(tg); ng=odb.dbTrackGrid.create(blk,lay)
        for pats,lo,hi,add in ((px,x0,x1,ng.addGridPatternX),(py,y0,y1,ng.addGridPatternY)):
            for o,c,s in pats:
                no=o+-(-(lo-o)//s)*s if lo>o else o; cnt=(hi-no)//s+1
                if cnt>0: add(no,cnt,s)
    blk.setDieArea(odb.Rect(x0,y0,x1,y1)); blk.setCoreArea(odb.Rect(x0,y0,x1,y1))
    print(f'CROP box_um=[{x0/dbu:.2f} {y0/dbu:.2f} {x1/dbu:.2f} {y1/dbu:.2f}] area_mm2={(x1-x0)*(y1-y0)/dbu/dbu/1e6:.3f} kept_insts={len(keep)} dropped={len(drop)} nets_deleted={ndel} pdn={psb}',flush=True)
# DIE-ROUTE-ABS-1: SNAP_TAP_PINS=1 puts the die tap terminals (t_*__clk_tN, M9) on the M9 x / M8 y track grid (7 nm M8 min-step stubs).
if os.environ.get("SNAP_TAP_PINS"):
    sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
    import die_unit_obs
    print("TAP_PIN_SNAP",die_unit_obs.snap_tap_pins(blk,odb,dbu),flush=True)
# DIE-ROUTE-ABS-1: GRT-only die obstructions (grt/obs.tcl: PG duplicates + clock-leg reservations) are fixed shapes in detail route.
# DROP_GRT_OBS=<obs.tcl> deletes exactly those (layer + rectangle match); real PG special wires stay.
if os.environ.get("DROP_GRT_OBS"):
    sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
    import die_unit_obs
    _r=die_unit_obs.parse_obs_tcl(open(os.environ["DROP_GRT_OBS"]).read(),dbu)
    print("GRT_OBS_DROP",die_unit_obs.drop_grt_obstructions(blk,_r,odb.dbObstruction.destroy),flush=True)
# guides: the DB's own guides are what DRT misread (DRT-0218 'guide not connected'); write the unit's own-net guides as a guide file and drop the DB guides (as the HBM cutter does)
nw=0
with open(os.path.dirname(os.environ['OUT_ODB'])+'/route.guide','w') as f:
    for n in blk.getNets():
        if n.getName() in own:
            gs=list(n.getGuides())
            if not gs: continue
            f.write(n.getName()+'\n(\n')
            for g in gs:
                r=g.getBox(); f.write(f"{r.xMin()} {r.yMin()} {r.xMax()} {r.yMax()} {g.getLayer().getName()}\n"); nw+=1
            f.write(')\n')
for n in blk.getNets():
    for g in list(n.getGuides()): odb.dbGuide_destroy(g)
print('GUIDES written for own nets:',nw,flush=True)
odb.write_db(db,os.environ['OUT_ODB']); print('UNIT_DB_WRITTEN',flush=True)
