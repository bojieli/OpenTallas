from pathlib import Path
import re,json,sys
p=Path(sys.argv[1]);s=p.read_text();errors=[]
go=[int(x)for x in re.findall(r'^BF_CORE_SAMPLE (\d+)$',s,re.M)]
raw=[int(x)for x in re.findall(r'^XS_CONTROL (\d+) cfg=0 go=1$',s,re.M)]
rows=[dict(zip(['date','side','row','seg','n','pos','val','err'],m))for m in re.findall(r'^BF_PARTIAL_SAMPLE (\d+) side=(\d+) row=(\d+) seg=(\d+) n=(\d+) pos=(\d+) val=([0-9a-f]+) err=(\d+)$',s,re.M)]
for r in rows:
 for k in r:
  r[k]=int(r[k],16 if k=='val'else 10)
gold={0:0xbb801a5a,1:0xbcac1a54}
if go!=[766]:errors.append('expected independently composed core input GO766, got '+str(go))
if len(rows)!=2:errors.append('expected exactly two native selected partials')
if raw!=[709]:errors.append(f'raw XS date differs from retained same-calendar BF history shifted by512: {raw}')
for r in rows:
 if r['row']not in gold or r['val']!=gold.get(r['row']):errors.append('independent segment0 partial mismatch '+str(r))
 if (r['seg'],r['n'],r['pos'],r['err'],r['side'])!=(0,4,0,0,r['row']):errors.append('partial metadata mismatch '+str(r))
 if len(go)==1 and r['date']-go[0]!=175:errors.append('retained native internalGO→partial174 plus native CPIN1 edge differs '+str(r))
end=re.search(r'BF_END partials=(\d+) goes=(\d+) events=(\d+) consumed=(\d+) xf=(\d) sf=(\d) ringfault=(\d) cf=(\d) seq=(\d) front=(\d)',s)
if not end:errors.append('missing end guard')
else:
 z=list(map(int,end.groups()))
 if z[0:2]!=[2,1]or z[2]!=z[3]or any(z[4:]):errors.append('terminal guard '+str(z))
r=dict(status='PASS'if not errors else'FAIL',source_cut_only=True,physical_epoch_qualified=False,native_provider_qualified=False,fullmission_programme_qualified=False,core_input_go=go,raw_xs_go=raw,partials=rows,errors=errors)
print(json.dumps(r,indent=2));sys.exit(bool(errors))
