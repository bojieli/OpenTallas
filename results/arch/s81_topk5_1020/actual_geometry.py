import odb,sys,json,collections
from pathlib import Path
out={}
for path in sys.argv[2:]:
    db=odb.dbDatabase.create();odb.read_db(db,path);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
    die=b.getDieArea();core=b.getCoreArea();area=lambda z:z.dx()*z.dy()/u**2
    terms=collections.Counter();rects=collections.Counter();cells=collections.Counter();std=0
    for i in b.getInsts():
        m=i.getMaster();cells[str(m.getType())]+=1
        if not m.isBlock():std+=m.getWidth()*m.getHeight()/u**2
    for t in b.getBTerms():
        role=str(t.getSigType());terms[role]+=1
        for p in t.getBPins():rects[role]+=len(p.getBoxes())
    rows=[r.getBBox() for r in b.getRows()]
    out[Path(path).name]={'db_units_per_um':u,'outline_area_um2':area(die),'core_bbox_area_um2':area(core),'row_rectangles':len(rows),'sum_row_area_um2':sum(area(r) for r in rows),'actual_std_area_um2':std,'std_over_outline':std/area(die),'std_over_core':std/area(core),'BTerms_by_native_sigtype':dict(terms),'BPin_rectangles_by_native_sigtype':dict(rects),'native_cell_master_types':dict(cells)}
Path(sys.argv[1]).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
