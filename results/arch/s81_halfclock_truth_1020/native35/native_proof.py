import pathlib,json,re,hashlib
D=pathlib.Path.cwd();rows=[]
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def group(s,p):
 m=re.search(r'\bpin\s*\(\s*"?'+re.escape(p)+r'"?\s*\)\s*\{',s);assert m
 depth=0
 for i in range(m.end()-1,len(s)):
  depth+=(s[i]=='{')-(s[i]=='}')
  if depth==0:return m.start(),i+1
for v in ['buf','inv','chain','defaultbuf','defaultinv']:
 p=D/v/'export35e931766'; a=json.loads((p/'abstract.json').read_text());out='clk_out' if v.startswith('default') else 'ck_o'
 for c in ['ss','ff','tt']:
  raw=(p/f'sequential_{c}.lib.raw').read_text();merged=(p/f'fc_coupon_{c}.lib').read_text();x,y=group(raw,out);k,l=group(merged,out)
  other=raw[:x]+raw[y:];other2=merged[:k]+merged[l:];assert other==other2
  fc=a['forwarded_clock'][c];assert fc['timing_sense']==('positive_unate' if v in ['buf','defaultbuf'] else 'negative_unate')
  rows.append(dict(variant=v,corner=c,other_pin_FF_all_bytes_equal=True,other_bytes_sha256=sha(other),OT_WS=a['corners'][c]['ws'],sense=fc['timing_sense'],local=fc['clk_in_to_clk_out_ps']))
lat=[]
for v in ['buf','inv','chain']:
 a=json.loads((D/v/'export35e931766/abstract.json').read_text())['forwarded_clock']['tt'];b=json.loads((D/'qual35'/f'{v}_latency0/export/abstract.json').read_text())['forwarded_clock']['tt']
 delta={k:a['clk_in_to_clk_out_ps'][k]-b['clk_in_to_clk_out_ps'][k] for k in a['clk_in_to_clk_out_ps']}; assert max(abs(x) for x in delta.values())<0.001
 shifts={key:{k:a[key][k]-b[key][k] for k in a[key] if k.startswith('arrival')} for key in ['input_absolute_ps','output_absolute_ps','driver_absolute_ps']};assert all(abs(x-17)<0.001 for row in shifts.values() for x in row.values())
 # source latency does not alter native clock-free characterization
 assert (D/v/'export35e931766/fc_coupon_tt.lib').read_bytes()==(D/'qual35'/f'{v}_latency0/export/fc_coupon_tt.lib').read_bytes()
 lat.append(dict(variant=v,local_delta=delta,absolute_shifts=shifts,merged_lib_bytes_identical=True))
default=json.loads((D/'qual35/default_absent/export/abstract.json').read_text());assert not default.get('forwarded_clock')
sens=[]
base=json.loads((D/'inv/export35e931766/abstract.json').read_text())['forwarded_clock']['tt']
for name in ['load74','spef2']:
 p=D/'sensitivity35'/name/'export';a=json.loads((p/'abstract.json').read_text())['forwarded_clock']['tt'];delta={k:a['clk_in_to_clk_out_ps'][k]-base['clk_in_to_clk_out_ps'][k] for k in base['clk_in_to_clk_out_ps']}; assert max(abs(x) for x in delta.values())>0.1
 sens.append(dict(case=name,local_delta=delta,lib_changed=(p/'fc_coupon_tt.lib').read_bytes()!=(D/'inv/export35e931766/fc_coupon_tt.lib').read_bytes()))
proof=dict(source='35e931766',native_exports=rows,latency_invariance=lat,default_absent_no_receipt=True,causal=json.loads((D/'qual35/results.json').read_text()),sensitivity=sens)
(D/'NATIVE_PROOF.json').write_text(json.dumps(proof,indent=2));print('NATIVE_PROOF_PASS',len(rows),len(lat),len(sens))
