#!/usr/bin/env python3
"""S81-RATEFIX: judge one fullsix run (pipelined or serial calendar) from diagnostic.log + the classification.
PASS = 512 rows, 0 missing/unknown, return words equal to the P600 baseline with the row op-tag bits [15:14]
masked (word bits 30/31: the op tag is the cfg7 go count), every tb source/read check accounted, 0 element faults
(Q_LIFETIME fault / CFG7 st fault), 0 xs/cal faults.  The tb attributes reads to the epoch of the LAST GO, and counts
calendar ENDs (15 per serial run): in a pipelined run the GO of phase n+1 precedes phase n's last reads and there is
ONE end, so those two tb checks are re-derived here (reads attributed by stream window) and their err++ discounted."""
import sys,json,re,gzip,collections
from pathlib import Path
d=Path(sys.argv[1]);base=json.load(open(sys.argv[2]))
s=(d/'diagnostic.log').read_text() if (d/'diagnostic.log').exists() else gzip.open(d/'diagnostic.log.gz','rt').read()
c=json.load(open(d/'diagnostic_classification.json'));w=c['frame_return_words']
con=json.load(open(d/'model/contract.json'))
M=~((1<<30)|(1<<31))
bv={(x['semantic_row'],int(x['word'],16)&M) for x in base['frame_return_words']}
nv={(x['semantic_row'],int(x['word'],16)&M) for x in w if 'semantic_row' in x}
err=int(re.findall(r'FULLSIX_SOURCE_CHECK errors=(\d+)',s)[-1])
erc=[tuple(map(int,m)) for m in re.findall(r'EPOCH_READ_COUNTS epoch=(\d+) actual=(\d+) expected=(\d+)',s)]
ctlmm=len(re.findall(r'RETAINED_CONTROL_MISMATCH',s))
ctlline=re.findall(r'RETAINED_CONTROL_MISMATCH (.*)',s)
other=dict(qout=len(re.findall('RETAINED_QOUTPUT_MISMATCH',s)),macro=len(re.findall('XS_MACRO_READ_MISMATCH',s)),
 src=len(re.findall('QNORM_SOURCE_(MISMATCH|AGE_MISMATCH|COUNTS|MISSING)',s)))
reads=[(int(t),int(e),par,v) for t,e,par,v in re.findall(r'ACTUAL_QREAD t=(-?\d+) epoch=(\d+) gates=\S+ blocks=\S+ parity=(\d) source=\S+ valid=(\S+)',s)]
gos=[int(t) for t in re.findall(r'ACTUAL_GO t=(-?\d+)',s)]
exp=[e for _,_,e in erc]
# re-attribution by stream window: phase n's stream rows [a,b] (calendar edges) -> reads at [a+k, b+k], k from epoch 0
if con.get('calendar_mode',{}).get('mode')=='pipeline':
  win=[(e['pipeline']['stream'][0],e['pipeline']['stream'][1]) for e in con['epochs']]
else:
  win=[(e['is_d_shift']-1100+103,e['is_d_shift']-1100+166) for e in con['epochs']]
k=reads[0][0]-win[0][0] if reads else 0
att=collections.Counter()
for t,_,_,_ in reads:
  n=[i for i,(a,b) in enumerate(win) if a+k<=t<=b+k+4]
  att[n[0] if len(n)==1 else -1]+=1
reatt=[att[i] for i in range(15)]
tb_attr_err=sum(1 for e,a,x in erc if a!=x)
badpar=sum(1 for t,e,p,v in reads if p!='0')
efault=len(re.findall(r'^Q_LIFETIME .* fault=1',s,re.M))
cfgf=sum(1 for st in re.findall(r'^CFG7_TRACE .* st=([01]+)',s,re.M) if int(st,2)&2)
fx=re.findall(r'FULLSIX_PREPARATORY_TRACE_END (.*)',s)
residual=err-tb_attr_err-ctlmm
ok=(len(w)==625 and not c['missing_semantic_rows'] and not c['unknown_row_identities'] and nv==bv and residual==0
    and reatt==exp and att[-1]==0 and badpar==0 and efault==0 and cfgf==0 and sum(other.values())==0)
first=min(x['t'] for x in c['actual_tag_captures']);last=max(x['t'] for x in w)
r=dict(dir=str(d),calendar=con.get('calendar_mode'),returns=len(w),missing=len(c['missing_semantic_rows']),
 unknown=len(c['unknown_row_identities']),words_equal_P600_tagmasked=nv==bv,only_new=len(nv-bv),only_600=len(bv-nv),
 tb_errors=err,tb_epoch_attribution_errs=tb_attr_err,tb_control_mismatch=ctlline,residual_errors=residual,
 reads_reattributed=reatt,reads_expected=exp,reads_unattributed=att[-1],read_parity_bad=badpar,gos=len(gos),
 element_faults=efault,cfg7_faults=cfgf,other_mismatch=other,trace_end=fx,CAPcause=c['CAP_sticky_causes'],
 first_capture=first,last_return=last,span_edges=last-first+1,PASS=ok)
(d/'ratefix_result.json').write_text(json.dumps(r,indent=1)+'\n')
print('RATEFIX_RESULT',json.dumps(r))
