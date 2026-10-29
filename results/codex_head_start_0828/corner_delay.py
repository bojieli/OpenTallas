"""Parse existing routed full-path reports at BOTH min/max in EACH corner."""
import json,re,sys,statistics as Stats
from pathlib import Path
run,rows,stages,plan,old,out=map(Path,sys.argv[1:7])
model_hop=float(sys.argv[7]) if len(sys.argv)>7 else 360.0
def parse(f):
    result={};blk=None
    for line in f.read_text().splitlines():
        if line.startswith('Startpoint:'): blk={'sp':line.split()[1]};continue
        if blk is None:continue
        m=re.match(r'\s+[-\d.]+\s+([-\d.]+)\s+[\^v]\s+(\S+)/CLK\s',line)
        if m and 'clk' not in blk and m.group(2)==blk['sp']:blk['clk']=float(m.group(1));continue
        m=re.match(r'\s+([-\d.]+)\s+data arrival time',line)
        if m and 'arr' not in blk:blk['arr']=float(m.group(1));continue
        m=re.match(r'Endpoint:\s+(\S+)',line)
        if m:blk['ep']=m.group(1)+'/D'
        if 'slack' in line and all(k in blk for k in ('ep','arr','clk')):
            result[blk['ep']]=round(blk['arr']-blk['clk'],3);blk=None
    return result
R=json.load(open(rows))['rows'];S={s['id']:s for s in json.load(open(stages))['stages']};P={g['region']:g for g in json.load(open(plan))['regions']}
doc=json.load(open(old));doc['corners']={};doc['corner_models']={}
for c in ('TT','FF'):
    low=parse(run/f'out_{c}/ddmin_{c}.rpt'); high=parse(run/f'out_{c}/ddmax_{c}.rpt');ports={}
    for r in R:
        if r['ep'] not in low or r['ep'] not in high:continue
        sf=P[S[r['cap']]['region']]['start_from'];port=sf['port'];v=(min(low[r['ep']],high[r['ep']]),max(low[r['ep']],high[r['ep']]))
        if port in ports:v=(min(v[0],ports[port][0]),max(v[1],ports[port][1]))
        assert v[0]<=v[1],(c,port,v)
        ports[port]=v
    doc['corners'][c]=ports
    H=[(r['hop_um'],min(low[r['ep']],high[r['ep']]),max(low[r['ep']],high[r['ep']])) for r in R if r.get('hop_um') and r['hop_um']<=model_hop and r['ep'] in low and r['ep'] in high]
    def bound(i):
        xs=[r[0] for r in H];ys=[r[i] for r in H];mx,my=Stats.mean(xs),Stats.mean(ys)
        slope=sum((x-mx)*(y-my) for x,y in zip(xs,ys))/sum((x-mx)**2 for x in xs)
        residuals=[r[i]-slope*r[0] for r in H]
        intercept=(min(residuals)-.01) if i==1 else (max(residuals)+.01)
        return [intercept,slope]
    doc['corner_models'][c]=dict(lo_ps=bound(1),hi_ps=bound(2))
    print(c,'candidate_model',doc['corner_models'][c])
    print(c,'measured_ports',len(ports),'parsed_minmax',len(low),len(high))
doc['model_max_hop_um']=model_hop
doc['basis']+='; candidate envelopes bound all measured rows at hops <= '+str(model_hop)+' um (ESTIMATE ONLY, actual new ports remain unmeasured); corners use existing SAME-corner min and max reports (no cross-corner combinations)'
out.write_text(json.dumps(doc,indent=0)+'\n')
