import json,re
from pathlib import Path
B=Path('/srv/opentallas-scratch2/claude/kw32/kvbind_27db6/bind_kv_q/rtl')
dead={'fhN':list(range(4)),'piN':list(range(277,285)),'piN_d1':list(range(285,289)),'piN_d2':list(range(4)),'piN_d3':list(range(4,12)),'rhN':list(range(12,16))}
width={'fhN':16,'piN':289,'piN_d1':289,'piN_d2':289,'piN_d3':289,'rhN':16}
cert=[]
for f in sorted(B.glob('kv3_pc*.sv')):
 s=f.read_text()
 if 'i_phy_Q__sN_piN_d3_q' not in s:continue
 used={k:set() for k in dead};examples=[]
 for line in s.splitlines():
  for key in dead:
   name='i_phy_Q__sN_'+key+'_q'
   if name not in line:continue
   if re.match(r'\s*wire\b',line) or '.q('+name+')' in line:continue
   refs=list(re.finditer(re.escape(name)+r'\[(\d+)(?::(\d+))?\]',line))
   if not refs:raise ValueError('unindexed consumer '+str(f)+': '+line)
   for m in refs:
    a=int(m[1]);b=int(m[2]or m[1]);used[key].update(range(min(a,b),max(a,b)+1))
   examples.append(line.strip())
 for key in dead:
  omitted=set(range(width[key]))-used[key]
  assert omitted==set(dead[key]),(f,key,sorted(omitted))
 cert.append({'type_module':f.stem,'source':str(f),'used_bits':{k:sorted(v) for k,v in used.items()},'dead_bits':dead,'uses':examples,'live_bits':sum(map(len,used.values()))})
assert len(cert)==6,len(cert)
out=Path(__file__).with_name('consumer_certificate.json');out.write_text(json.dumps({'verdict':'PASS','variants':cert,'native_pi_bits_per_variant':1156,'dead_fh_rh_bits_per_variant':32,'clock_classification':'fh/rh combinational clock forwarding; no read of corresponding face data bits'},indent=1));print('PASS',len(cert),'variants, each1156livebits/32deadforwardingbits')
