import importlib.util,sys,re,json,hashlib,time
from pathlib import Path
sys.path[:0]=['tools/ref_tile/tests','tools/ref_tile']
import test_multiple_cts_roots as T
import clock_entry_constraints as CE
spec=importlib.util.spec_from_file_location('uncached','uncached.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
new=CE.generate
result=[]
for label,gen in [('uncached',old.generate),('cached',new)]:
 def instrument(*args,gen=gen,**kwargs):
  text=gen(*args,**kwargs)
  marker='\not_ce_apply\n'
  assert text.count(marker)==1
  probe='''
set ::ot_perf_query_n 0
rename find_timing_paths ot_perf_find_timing_paths
proc find_timing_paths {args} {incr ::ot_perf_query_n;return [ot_perf_find_timing_paths {*}$args]}
set ot_perf_start [clock microseconds]
for {set ot_perf_repeat 0} {$ot_perf_repeat < 50} {incr ot_perf_repeat} {ot_ce_apply}
puts "APPLY_PERF [expr {[clock microseconds]-$ot_perf_start}] us queries=$::ot_perf_query_n"
rename find_timing_paths {}
rename ot_perf_find_timing_paths find_timing_paths
'''
  return text.replace(marker,probe)
 CE.generate=instrument
 rc,text=T.Physical().run_flow('related')
 assert rc==0,text[-5000:]
 match=re.search(r'APPLY_PERF (\d+) us queries=(\d+)',text);assert match
 Path('evidence/timing_'+label+'.log').write_text(text)
 result.append(dict(mode=label,microseconds=int(match[1]),queries=int(match[2]),calls=50))
 print(label,match.group(0),flush=True)
assert result[0]['queries']-result[1]['queries']==100,result
Path('evidence/timing.json').write_text(json.dumps(dict(scope='50 reapplications on same actual20register two-root related-path fixture; process startup excluded. No performance extrapolation to production.',runs=result,source_hashes={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['tools/ref_tile/clock_entry_constraints.py','uncached.py','timing.py']}),indent=2)+'\n')
print('APPLY_PERF_PASS',flush=True)
