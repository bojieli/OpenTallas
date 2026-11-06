from pathlib import Path
import re,json,hashlib
R=Path('/srv/opentallas-scratch2/claude/codex-ds-img2-service-1105');S=Path('/srv/opentallas-scratch2/claude/tok-ds-2/v0copy/rtl');top=(S/'s81_bound_top.sv').read_text()
def graph(p,base):
 s=p.read_text();g={}
 for line in s.splitlines():
  m=re.search(r'ot_dp_rrelay(_nl)?\s+(\w+)\s*\([^\n]*\.d\((\w+)\)[^\n]*\.q\((\w+)\)',line)
  if m:g[m[4]]=(m[3],1.5 if m[1] else 1)
 for dest,src in re.findall(r'(?:wire|assign)\s+(\w+)\s*=\s*(\w+)(?:\[0\])?\s*;',s):g[dest]=(src,0)
 def age(n):
  if n in base:return base[n]
  src,d=g[n];return (int(age(src))+d) if d else age(src)
 return s,age

def instance(n):
 m=re.search(r'\b(\w+)\s+(?:#\([^\n]*\)\s+)?'+n+r'\s*\((.*?)\n    \);',top,re.S)
 assert m,n
 return m[1],dict(re.findall(r'\.(\w+)\((\w+)\)',m[2]))
rows=[]
for pref in ['s_0N','s_0S','s_7N','s_7S']:
 ct,cp=instance(pref+'_C');lt,lp=instance(pref+'_LP');C=S/(ct+'.sv');L=S/(lt+'.sv')
 c,ca=graph(C,{'arst_n':0});nb=[k for k,v in cp.items() if v==lp['arst_n']];assert len(nb)==1
 arst=ca(nb[0]);assert cp['lpc_o0']==lp['lpc_i0']
 tx=next(x for x in c.splitlines() if ' u_bout_lpc_o0 ' in x)
 payload=re.search(r'\.d\(\{[^,]+,\s*(\w+)(?:\[0\])?\}\)',tx)[1]
 assert '.q(lpc_o0[1:0])' in tx
 kage=int(ca(payload))+2
 l,la=graph(L,{'arst_n':arst,'lpc_i0_q':kage})
 assert re.search(r'u_bin_lpc_i0[^\n]*\.d\(lpc_i0\[1:0\]\)[^\n]*\.q\(lpc_i0_q\)',l)
 lanes=[]
 for m in re.finditer(r'\bot_s81_mu72_lnland(?:_nst)?\s*#\([^\n]*\)\s+(\w+)\s*\((.*?)\n    \);',l,re.S):
  b=m[2];a=re.search(r'\.rs_k\((\w+)(?:\[0\])?\)',b)[1];n=re.search(r'\.rs_n\((\w+)(?:\[0\])?\)',b)[1]
  assert '.ck_k(clk)' in b and '.ck_n(clk)' in b
  ka,na=la(a),la(n);assert int(ka)==ka and int(na)==na
  lanes.append(dict(instance=m[1],rs_k=a,rs_n=n,writer_reset_edge=ka,reader_reset_edge=na,writer_rq_edge=ka+4,reader_rq_edge=na+4,KN_bias=(int(na-ka)%8),NK_bias=(int(ka-na)%8)))
 assert lanes,pref
 rows.append(dict(station=pref,origin=pref+'_C.arst_n=0',C_local=ca('rst_n'),LP_arst=arst,C_lpc_payload=ca(payload),LP_lpc_after_tx_rx=kage,LP_local=la('rst_n'),lanes=lanes,source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [C,L]}))
out=dict(scope='Frozen11-01 V1c actualv0copy source, per-station static derivation; no bias adoption',D=4,K=2,forests_each=3,rq_each=1,pin_cycles_added=0,rows=rows)
(R/'frozen_all_LP_epoch_receipts.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
