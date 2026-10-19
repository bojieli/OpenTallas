#!/usr/bin/env python3
"""PG-aware clock bay MODEL, derived from actual master pins and supply shapes.

This selects sites before topology; it never moves an existing clock. A legal
model site still requires literal rail contacts, PDN continuity/short checks and
the independent placed-pin 405um audit before timing may run.
"""
from bisect import bisect_left
from collections import Counter, defaultdict
import math


class ClockPowerSites:
    def __init__(self, width, height, hard, pins, m8, m9, pitch=8.64,
                 halo=1.08, clear=.6, half=12., margin=.3):
        self.width, self.height = width, height
        self.pitch, self.clear, self.half, self.margin = pitch, clear, half, margin
        self.halo = halo
        self.hard = [(n, (a-halo,b-halo,c+halo,d+halo)) for n,(a,b,c,d) in hard]
        self.pins, self.m8, self.m9 = pins, m8, m9
        self.m9x = {n: [r[0] for r in rr] for n,rr in m9.items()}
        self.bins = defaultdict(list)
        for _, r in self.hard:
            for j in range(math.floor((r[1]-.3)/100), math.floor((r[3]+.3)/100)+1):
                self.bins[j].append(r)
        self.spans = {}

    def occupied_rows(self, block):
        """Hard/pad halo plus exact already placed standard-cell footprints."""
        u = block.getDbUnitsPerMicron()
        hard = dict(self.hard)
        result = []
        for obj in block.getInsts():
            if obj.getName() in hard:
                result.append((obj.getName(), hard[obj.getName()]))
            elif obj.isPlaced():
                q=obj.getBBox()
                result.append((obj.getName(),(q.xMin()/u,q.yMin()/u,q.xMax()/u,q.yMax()/u)))
        return result

    def free_spans(self, y):
        key = round(y*1000)
        if key not in self.spans:
            # Include actual PG pin overhang: literal followpin contacts must
            # fit as well as the cell body. Master offsets are orientation-bound.
            orient = 'R0' if round(y/.27)%2 == 0 else 'MX'
            shapes = [r for mm in self.pins.values() for r in mm[orient].values()]
            bottom=y+min(r[1] for r in shapes);top=y+max(r[3] for r in shapes)
            intervals = sorted((r[0],r[2]) for r in self.bins[math.floor(y/100)]
                               if r[1] < top and r[3] > bottom)
            merged=[]
            for a,b in intervals:
                if merged and a<=merged[-1][1]:merged[-1][1]=max(b,merged[-1][1])
                else:merged.append([a,b])
            left=0.;free=[]
            for a,b in merged+[[self.width,self.width]]:
                if a>left:free.append((left,min(a,self.width)))
                left=max(left,b)
            self.spans[key]=free
        return self.spans[key]

    def requirement(self, x, y):
        """Conservative common BUF/PAD site and actual M9 contact budget."""
        orient='R0' if round(y/.27)%2==0 else 'MX'
        if x<0 or y<0 or x+1.62>self.width or y+.27>self.height:return None
        xmin=min(r[0] for mm in self.pins.values() for r in mm[orient].values())
        xmax=max(r[2] for mm in self.pins.values() for r in mm[orient].values())
        free=next(((a,b) for a,b in self.free_spans(y) if a<=x+min(0,xmin) and b>=x+max(1.62,xmax)),None)
        if free is None:return None
        # Rail extents are site-aligned inward, matching actual dbRow coverage.
        lo=math.ceil((max(free[0],x-self.half)-1e-9)/.054)*.054
        hi=math.floor((min(free[1],x+1.62+self.half)+1e-9)/.054)*.054
        contacts={}
        for net in ('VDD','VSS'):
            opposite='VSS' if net=='VDD' else 'VDD'
            phase,width=self.m8[opposite]
            rails=[mm[orient][net] for mm in self.pins.values()]
            bottom=y+min(r[1] for r in rails);top=y+max(r[3] for r in rails)
            # Use full actual PG shape, not just its centre. Check nearby actual
            # periodic core stripes with the canonical stack clearance.
            k=math.floor((bottom-phase)/self.pitch)
            for kk in (k-1,k,k+1):
                edge=phase+kk*self.pitch
                if bottom<=edge+width+self.clear and top>=edge-self.clear:return None
            stripes=self.m9[net];start=bisect_left(self.m9x[net],lo+self.margin-1e-9)
            fit=next((r for r in stripes[start:start+8]
                      if r[0]>=lo+self.margin-1e-9 and r[2]<=hi-self.margin+1e-9
                      and r[1]<=bottom and r[3]>=top),None)
            if fit is None:return None
            contacts[net]=list(fit)
        return dict(x_um=x,y_um=y,orientation=orient,row_segment_um=[lo,hi],
                    actual_m9_contacts=contacts,power_qualified=False)

    def __call__(self,x,y):
        return self.requirement(x,y) is not None

    def identity(self):
        return dict(schema='opentallas.qwen.clock_power_site_model.v1',
                    actual_m8_pitch_um=self.pitch,actual_m8_edge_width_um=self.m8,
                    actual_m9_stripes={n:len(v) for n,v in self.m9.items()},
                    actual_master_pg_bboxes_um=self.pins,macro_halo_um=self.halo,
                    opposite_m8_clear_um=self.clear,row_half_um=self.half,
                    m9_contact_margin_um=self.margin,model_only=True,
                    power_qualified=False,timing_qualified=False,production_admitted=False)

    @classmethod
    def from_block(cls,block,odb,masters):
        u=block.getDbUnitsPerMicron();die=block.getDieArea();pitch=round(8.64*u)
        m8={};m9={};pins={};hard=[]
        for netname in ('VDD','VSS'):
            net=block.findNet(netname)
            if net is None:raise ValueError('missing actual supply '+netname)
            horizontal=[];vertical=[]
            for sw in net.getSWires():
                for wire in sw.getWires():
                    if wire.isVia():continue
                    layer=wire.getTechLayer().getName()
                    if layer=='M8' and wire.xMax()-wire.xMin()>(die.xMax()-die.xMin())/2:
                        horizontal.append((wire.yMin(),wire.yMax()))
                    if layer=='M9' and wire.yMax()-wire.yMin()>(die.yMax()-die.yMin())/2:
                        vertical.append(tuple(v/u for v in (wire.xMin(),wire.yMin(),wire.xMax(),wire.yMax())))
            edges=Counter(a%pitch for a,b in horizontal);widths=Counter(b-a for a,b in horizontal)
            if len(edges)!=1 or len(widths)!=1 or not vertical:
                raise ValueError('ambiguous/missing actual core supply mesh '+netname)
            m8[netname]=(next(iter(edges))/u,next(iter(widths))/u)
            m9[netname]=sorted(set(vertical))
        for obj in block.getInsts():
            if obj.getMaster().isBlock() or obj.getMaster().isPad():
                q=obj.getBBox();hard.append((obj.getName(),tuple(v/u for v in (q.xMin(),q.yMin(),q.xMax(),q.yMax()))))
        for master in masters:
            if master is None:raise ValueError('missing actual clock master')
            name='__clock_power_site_probe_'+master.getName()
            if block.findInst(name) is not None:raise ValueError('probe name collision')
            obj=odb.dbInst.create(block,master,name)
            try:
                if master.getWidth()/u>1.62 or master.getHeight()/u!=.27:
                    raise ValueError('unsupported clock master footprint '+master.getName())
                pins[master.getName()]={}
                for orient in ('R0','MX'):
                    obj.setOrient(orient);obj.setLocation(0,0);shapes={}
                    for net in ('VDD','VSS'):
                        pin=obj.findITerm(net)
                        if pin is None:raise ValueError('clock master missing '+net)
                        layers={g.getTechLayer().getName() for p in pin.getMTerm().getMPins() for g in p.getGeometry()}
                        if 'M1' not in layers:raise ValueError('no literal M1 PG contact '+master.getName()+'/'+net)
                        q=pin.getBBox();shapes[net]=tuple(v/u for v in (q.xMin(),q.yMin(),q.xMax(),q.yMax()))
                        if shapes[net][3]-shapes[net][1]<.018-1e-9:raise ValueError('undersized literal PG rail')
                    pins[master.getName()][orient]=shapes
            finally:odb.dbInst.destroy(obj)
        return cls(die.xMax()/u,die.yMax()/u,hard,pins,m8,m9)


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    import odb
    from openroad import Tech,Design
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--odb',required=True);p.add_argument('--out',required=True)
    p.add_argument('--manifest')
    a=p.parse_args();tech=Tech();design=Design(tech);design.readDb(a.odb)
    policy=ClockPowerSites.from_block(design.getBlock(),odb,
                                    [design.getDb().findMaster(n) for n in ('BUFx24_ASAP7_75t_R','BUFx12f_ASAP7_75t_R')])
    result=policy.identity()
    result['sample_32_rows']=[dict(y_um=round(i*.27,3),accepted=policy(100.,i*.27)) for i in range(32)]
    if a.manifest:
        cells=json.loads(Path(a.manifest).read_text())['cells']
        rejected=[n for n,_,x,y in cells if not policy(x,y)]
        result.update(existing_clock_cells=len(cells),rejected_existing_sites=len(rejected),rejected_examples=rejected[:100])
    Path(a.out).write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result,indent=1),flush=True)
