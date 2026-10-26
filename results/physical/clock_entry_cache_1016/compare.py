import importlib.util,sys,time,json,re,hashlib
from pathlib import Path
sys.path[:0]=['tools/ref_tile/tests','tools/ref_tile']
import test_multiple_cts_roots as T
import clock_entry_constraints as CE
spec=importlib.util.spec_from_file_location('uncached','uncached.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
cached_generate=CE.generate
out=Path('evidence');out.mkdir(exist_ok=True)
cases=['','related','tie','tie_gate','constant_data','async_reset','wrong_input','wrong_output','unknown_port','cross_data','extra_alias','tie_port','tie_reg','tie_gate_port','async_reset_data','related_wrong_input','related_cut','declared_reset']
receipt=[]
for case in cases:
 pair=[]
 for label,gen in [('uncached',old.generate),('cached',cached_generate)]:
  CE.generate=gen
  start=time.monotonic();rc,text=T.Physical().run_flow(case);elapsed=time.monotonic()-start
  p=out/((case or 'positive')+'_'+label+'.log');p.write_text(text)
  semantic=[re.sub(r'/tmp/[^ /\n]+','/tmp/FIXTURE',line) for line in text.splitlines() if any(tag in line for tag in ['OT_ENTRIES','OT_MULTI_ROOT','CTS_MEASURE','MULTI_ROOT_RESULT','OT_HYBRID:'])]
  pair.append(dict(mode=label,rc=rc,seconds=elapsed,semantic=semantic,sha256=hashlib.sha256(text.encode()).hexdigest()))
 assert pair[0]['rc']==pair[1]['rc'],(case,'return code')
 assert pair[0]['semantic']==pair[1]['semantic'],(case,pair[0]['semantic'],pair[1]['semantic'])
 receipt.append(dict(case=case or 'positive',runs=pair))
 print('CACHE_IDENTITY_PASS',case or 'positive',*[round(x['seconds'],3) for x in pair],flush=True)
CE.generate=cached_generate
(out/'receipt.json').write_text(json.dumps(dict(schema='opentallas.clock_cache_comparison.v1',cases=receipt,source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['tools/ref_tile/clock_entry_constraints.py','uncached.py','compare.py']}),indent=2)+'\n')
print('CACHE_COMPARISON_ALL_PASS',len(receipt),flush=True)
