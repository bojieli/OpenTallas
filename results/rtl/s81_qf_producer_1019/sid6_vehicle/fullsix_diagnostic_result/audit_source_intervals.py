from pathlib import Path
import re,json,collections,hashlib
import gzip
out=Path(__file__).resolve().parent; b=out.parent; s=gzip.decompress((out/'diagnostic.log.gz').read_bytes()).decode()
ident=json.loads((out/'diagnostic_expected_identity.json').read_text()); plans=json.loads((b/'retained_xs_program_model/contract.json').read_text())['plans']; lookup={(r['frame'],r['configured_row14']):r for r in ident['rows']}; sem={r['semantic_row']:r for r in ident['rows']}
expected=collections.Counter()
for p in plans:
 for x in p['placement']:
  for j,ix in enumerate(x['rows']):
   if ix<len(p['rows']):expected[(p['frame'],x['pair'],j,p['rows'][ix],x['seg'],x['nseg'])]+=1
pv=collections.Counter(); bad=[]; leaf=collections.Counter(); pv_records=[]
pat=r'^ACTUAL_PAIR_PV t=(\d+) id=(\S+) valid=([01]+) rows=([0-9a-f]+) vals=([0-9a-f]+) seg=([0-9a-f]+) nseg=([0-9a-f]+) err=([01]+) pos=([0-9a-f]+)'
for t,id,v,rows,vals,seg,nseg,err,pos in re.findall(pat,s,re.M):
 frame,q=id.rsplit('_q',1);v=int(v,2);rows=int(rows,16);seg=int(seg,16);nseg=int(nseg,16)
 for j in range(2):
  if not(v>>j&1):continue
  row=(rows>>(16*j))&65535;r=lookup.get((frame,row&16383));lo=(seg>>(5*j))&31;n=(nseg>>(5*j))&31
  if r is None:bad.append(dict(t=t,id=id,j=j,row=row));continue
  key=(frame,int(q),j,r['semantic_row'],lo,n);pv[key]+=1;leaf[(r['semantic_row'],lo)]+=1
  if (int(err,2)>>j)&1:bad.append(dict(t=t,id=id,j=j,error=1))
  pv_records.append(dict(t=int(t),id=id,macro=j,row16=row,semantic_row=r['semantic_row'],seg=lo,nseg=n,data=(int(vals,16)>>(32*j))&0xffffffff))
lanes=['u_f_3L01','u_f_3L02','u_f_3L03','u_f_3R01','u_f_3R02','u_f_3R03']; returns=[];covered=collections.Counter(); pads=[];illegal=[]; frames={};arr={}
for typ,t,l,w in re.findall(r'^(FRAME_RETURN|CAP_ARR) t=(\d+) lane=(\d+) word=([0-9a-f]+)',s,re.M):
 t=int(t);l=int(l);w=int(w,16)
 if typ=='CAP_ARR':arr[(t,l)]=w;continue
 frames[(t,l)]=w;tag=(w>>3)&0xffffffff;row=(tag>>13)&65535;r=lookup[(lanes[l],row&16383)];lo=(tag>>8)&31;k=(tag>>5)&7;n=tag&31; span=list(range(lo,lo+(1<<k)));occupied=[x for x in span if x<n];padding=[x for x in span if x>=n]
 # Keep unchanged original encoded span; padding is reported explicitly, never counted as a real leaf.
 if n!=3 or lo%(1<<k) or lo>=n or any((r['semantic_row'],x) not in leaf for x in occupied):illegal.append([t,l,tag])
 for x in occupied:covered[(r['semantic_row'],x)]+=1
 returns.append(dict(t=t,lane=l,word=f'{w:018x}',semantic_row=r['semantic_row'],tag=f'{tag:08x}',lo=lo,k=k,nseg=n,encoded_span=span,occupied_source_segments=occupied,implicit_padding=padding))
joinbad=[dict(t=t,lane=l,word=f'{w:018x}',cap_at_t_plus_6=None if (t+6,l) not in arr else f'{arr[(t+6,l)]:018x}') for (t,l),w in frames.items() if arr.get((t+6,l))!=w]
extraarr=[(t,l) for t,l in arr if (t-6,l) not in frames]
fmt=lambda c:[dict(key=list(k),count=v) for k,v in sorted(c.items())]
result=dict(scope='READ ONLY first actual coupled diagnostic source-leaf and original-return-encoding audit; no DUT rerun, no numeric qualification',raw_log_sha256=hashlib.sha256(s.encode()).hexdigest(),expected_original_placement_leaves=sum(expected.values()),actual_pair_PV_leaves=sum(pv.values()),placement_missing=fmt(expected-pv),placement_extra=fmt(pv-expected),PV_unknown_or_error=bad,actual_leaf_identity_count=len(leaf),actual_leaf_repetition=fmt(collections.Counter({k:v for k,v in leaf.items() if v!=1})),return_words=len(returns),return_original_encodings=dict(collections.Counter(f'lo{r["lo"]}/k{r["k"]}/n{r["nseg"]}' for r in returns)),return_occupied_leaf_count=sum(covered.values()),occupied_missing=fmt(leaf-covered),occupied_extra_or_repeated=fmt(covered-leaf),illegal_original_encodings=illegal,implicit_padding_occurrences=sum(len(r['implicit_padding']) for r in returns),padding_not_source_leaf_credit=True,unchanged_lo_k_nseg=True,no_dedup_clamping_gold_fill=True,frame_to_CAP_exact_words=len(frames),measured_DR_edges=6,frame_CAP_mismatches=joinbad,extra_CAP_arrivals=extraarr,actual_pair_PV=pv_records,actual_return_intervals=returns,numeric_payload_gold_PASS=None,native_phase=None,healthy_CAP_PASS=False)
(out/'source_interval_audit.json').write_text(json.dumps(result,indent=2)+'\n')
for k,v in result.items():
 if k not in ('actual_pair_PV','actual_return_intervals'):print(k,v)
