"""Independent ideal clock/domain + data-graph comparison of actual ODB dumps.
This is a netlist structural proof, not routed timing or a fresh RTL simulation.
"""
from pathlib import Path
import gzip,json,re,sys,collections
p=Path.cwd();kind,out=sys.argv[1:3];before_census=p/f'data/{kind}_widen.tsv.gz';after_census=p/f'physical/{kind}_public_clock_install/clock_census.tsv';before_geom=p/('actual_nk/geom.tsv'if kind=='nk'else'physical/nl_widen2/geom/geom.tsv');after_geom=p/f'physical/{kind}_public_clock_install/geom_clock_installed.tsv'
if len(sys.argv)>3:after_census=Path(sys.argv[3])
norm=lambda s:s.replace(chr(92),'')
def clocks(file):
 op=gzip.open if file.suffix=='.gz'else open;rows=[l.rstrip().split('\t')for l in op(file,'rt')if l.startswith('S\t')];masters={norm(r[3]):r[5]for r in rows};gates={n for n,m in masters.items()if m.startswith('ICG')};buffers={n for n,m in masters.items()if m.startswith(('BUF','INV','CKINV'))};sig={};bad=[]
 for r in rows:
  n,pin,m=norm(r[3]),r[4],r[5]
  if m.startswith(('BUF','INV','CKINV')):continue
  if m.startswith('ICG')and pin!='CLK':bad.append((n,pin));continue
  if not m.startswith('ICG')and pin not in ('CLK','CK','clk'):bad.append((n,pin));continue
  path=list(map(norm,r[1].split('>')));parity=sum(masters.get(q,'').startswith(('INV','CKINV'))for q in path)%2;owner=tuple(q for q in path if q in gates);sig[n+'/'+pin]=(parity,owner)
 if bad:raise ValueError(('clock cone reaches nonclock terminal',bad[:5]))
 return sig,buffers,gates
B,bb,bg=clocks(before_census);A,ab,ag=clocks(after_census);clockdiff={k:(B.get(k),A.get(k))for k in B.keys()|A.keys()if B.get(k)!=A.get(k)}
def graph(file,clockbuf,gates):
 cells={};nets=[]
 for l in open(file):
  f=l.rstrip().split('\t')
  if f[0]=='C':cells[norm(f[1])]=f[2]
  elif f[0]=='N':nets.append(f[3:])
 result=collections.Counter();drivers={'P:ck'}|{'I:'+n+'/Y'for n in clockbuf}|{'I:'+n+'/GCLK'for n in gates}
 for terms in nets:
  terms=list(map(norm,terms))
  isclock=any(t in drivers for t in terms)
  if not isclock:result[tuple(sorted(terms))]+=1
 return {n:m for n,m in cells.items()if n not in clockbuf},result
before_geom=after_census.parent/'logic_before.tsv'
after_geom=after_census.parent/'logic_after.tsv'
bm,bn=graph(before_geom,bb|ab,bg);am,an=graph(after_geom,bb|ab,ag)
masterdiff={k:(bm.get(k),am.get(k))for k in bm.keys()|am.keys()if bm.get(k)!=am.get(k)};datadiff={k:(bn.get(k),an.get(k))for k in bn.keys()|an.keys()if bn.get(k)!=an.get(k)}
r=dict(scope='actual netlist data graph and ideal gated-clock ancestry; no new RTL simulation or timing claim',kind=kind,clock_terminals=len(A),clock_signature_mismatches=len(clockdiff),clock_signature_sample=list(clockdiff.items())[:5],data_nets_before=sum(bn.values()),data_nets_after=sum(an.values()),data_net_mismatches=len(datadiff),data_sample=list(datadiff.items())[:5],data_master_mismatches=len(masterdiff),master_sample=list(masterdiff.items())[:5])
Path(out).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));sys.exit(bool(clockdiff or datadiff or masterdiff ))
