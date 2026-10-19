import hashlib,json,pathlib,re,gzip
p=pathlib.Path(__file__).resolve().parent
def load(n):
 r=(p/n).read_text();return json.loads(re.sub(r'"name": "([^"\n]*)"',lambda m:'"name": '+json.dumps(m[1]),r))
o=load('original_cex.json');r=load('replay_cex.json');rr={s['name']:s for s in r['signal']}
def iv(s):
 c=s['wave'][0];return s.get('data',[''])[0] if c=='=' else c if c in '01xz' else ''
n=0
for s in o['signal']:
 a=iv(s)
 if not any(c in '01' for c in a):continue
 b=iv(rr[s['name']])
 for idx,c in enumerate(a[::-1]):
  if c in '01':assert idx<len(b) and b[::-1][idx]==c;n+=1
assert n==19963
# Import the same lossless waveform decoder without discarding blank initial data.
from decode_replay import decode
os={s['name']:decode(s) for s in o['signal']};rs={s['name']:decode(s) for s in r['signal']}
inputs=['clk','rst_n','kp_in','kpv_in','gf_in']
assert all(os[n]==rs[n] for n in inputs)
m=json.loads((p/'manifest.json').read_text())
for name,sha in m['dut_gold_cell_model_sha256_before_and_after_identical'].items():assert hashlib.sha256((p/'source'/name).read_bytes()).hexdigest()==sha
assert hashlib.sha256((p/'replay.ys').read_bytes()).hexdigest()==m['after_script_sha256']
assert hashlib.sha256((p/'original_cex.json').read_bytes()).hexdigest()==m['source_cex_sha256']
assert hashlib.sha256(gzip.decompress((p/'replay.log.gz').read_bytes())).hexdigest()=='040ebc678d12f6e9ba796afc9f7d8efa0ab2e9fd895a770bc63b715125d6a8fd'
(p/'constraint_validation.json').write_text(json.dumps({'known_initial_bits_checked':n,'missing_initial_names':[],'initial_mismatches':[],'input_samples_checked':50,'input_mismatches':[],'source_gold_cell_hashes_match_prelaunch_manifest':True,'script_and_original_cex_identity_match':True,'full_terminal_log_hash_matches_remote':True},indent=2)+'\n')
print('19963 initial bits/50 input samples and frozen source/formula identities PASS.')
