"""HEAD-START-3: MEASURED START data delay (launch FF CLK pin -> capture D, incl. clk->Q, logic, BUF8 chain, wire; GRT RC,
TT max path with the x1.10/x1.05 droop derate as in the STA, FF min path) per crossing endpoint, from report_checks -to D."""
import json,re,sys,collections,statistics as S
def parse(f):
    out={}; blk=None
    for ln in open(f):
        if ln.startswith('Startpoint:'): blk=dict(sp=ln.split()[1]); continue
        if blk is None: continue
        m=re.match(r'\s+[-\d.]+\s+([-\d.]+)\s+[\^v]\s+(\S+)/CLK\s',ln)
        if m and 'clk' not in blk and m.group(2)==blk['sp']: blk['clk']=float(m.group(1)); continue
        m=re.match(r'\s+([-\d.]+)\s+data arrival time',ln)
        if m and 'arr' not in blk: blk['arr']=float(m.group(1)); continue
        m=re.match(r'Endpoint:\s+(\S+)',ln)
        if m: blk['ep']=m.group(1)+'/D'
        if 'slack' in ln and 'ep' in blk and 'arr' in blk and 'clk' in blk:
            out[blk['ep']]=round(blk['arr']-blk['clk'],3); blk=None
    return out
mx=parse(sys.argv[1]); mn=parse(sys.argv[2])
ca=json.load(open(sys.argv[3])); plan=json.load(open(sys.argv[4])); st={s['id']:s for s in json.load(open(sys.argv[5]))['stages']}
P={g['region']:g for g in plan['regions']}
X=[r for r in ca['rows'] if r['cross']]
rows=[]
for r in X:
    sf=P[st[r['cap']]['region']]['start_from'] if r['cap'] in st else {}
    rows.append(dict(ep=r['ep'],cap=r['cap'],launch=r['launch_setup'],dd_max_TT=mx.get(r['ep']),dd_min_FF=mn.get(r['ep']),hop_um=sf.get('hop_um'),sync_dist_ps=sf.get('sync_dist_ps'),skew_limit_ps=sf.get('start_skew_limit_ps'),asbuilt=r['asbuilt'],replan=r['replan']))
v=sorted(x['dd_max_TT'] for x in rows if x['dd_max_TT'] is not None); w=sorted(x['dd_min_FF'] for x in rows if x['dd_min_FF'] is not None)
q=lambda a,f: round(a[int(f*(len(a)-1))],1)
over=[x for x in rows if x['dd_max_TT'] is not None and x['skew_limit_ps'] is not None and x['dd_max_TT']>x['skew_limit_ps']]
hb=collections.defaultdict(list)
for x in rows:
    if x['hop_um'] is not None and x['dd_max_TT'] is not None: hb[int(x['hop_um']//100)*100].append(x['dd_max_TT'])
summ=dict(crossings=len(rows),parsed_max=len(v),parsed_min=len(w),
  dd_max_TT=dict(min=q(v,0),p10=q(v,.1),median=q(v,.5),p90=q(v,.9),max=q(v,1)),
  dd_min_FF=dict(min=q(w,0),median=q(w,.5),max=q(w,1)),
  dd_max_over_plan_skew_limit=len(over),
  over_and_asbuilt_fail=sum(1 for x in over if x['asbuilt']<0), asbuilt_fail=sum(1 for x in rows if x['asbuilt']<0),
  dd_max_TT_median_by_hop100=dict(sorted((k,round(S.median(a),1)) for k,a in hb.items())),
  per_um_ps=round(S.median([x['dd_max_TT']/x['hop_um'] for x in rows if x['hop_um'] and x['hop_um']>150 and x['dd_max_TT']]),3))
print(json.dumps(summ,indent=1))
json.dump(dict(summary=summ,rows=rows),open(sys.argv[6],'w'),indent=0)
