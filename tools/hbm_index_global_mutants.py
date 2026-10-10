"""Collect a completed pinned full-shape gate and check its ordering mutant."""
import hashlib,json,subprocess
from pathlib import Path

root=Path.cwd()
src=root/'rtl/hbm_accel/index/ot_hbm_index_global_order.sv'
tb=root/'rtl/test/hbm_accel/tb_hbm_index_global_order.sv'
original=src.read_text()
needle='a[16:0]<b[16:0]'
assert needle in original
mut=root/'wrong_order.sv'
mut.write_text(original.replace(needle,'a[16:0]>b[16:0]'))
argv=['iverilog','-g2012','-s','tb_hbm_index_global_order','-o','wrong_order.vvp',str(mut),str(tb)]
c=subprocess.run(argv,capture_output=True,text=True)
(root/'wrong_order_compile.log').write_text(c.stdout+c.stderr)
r=subprocess.run(['vvp','wrong_order.vvp'],capture_output=True,text=True) if c.returncode==0 else None
output='' if r is None else r.stdout+r.stderr
(root/'wrong_order.log').write_text(output)
positive=(root/'order-positive.log').read_text()
identity=(root/'order-wrong-rank.log').read_text()
record=dict(source_commit='64831e7e1',source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
 bench_sha256=hashlib.sha256(tb.read_bytes()).hexdigest(),
 positive=dict(passed='PASS_GLOBAL_ORDER ranks=96 tuples=131072 actual_reads=131264' in positive,
    cycles=1966899,backpressure='output ready once per five edges; read handshakes and responses delayed'),
 wrong_rank=dict(passed='EXPECTED_BAD_IDENTITY_REJECT' in identity),
 wrong_order=dict(compile_returncode=c.returncode,run_returncode=None if r is None else r.returncode,
    passed=c.returncode==0 and r is not None and r.returncode!=0 and 'canonical ID or exact score mismatch' in output),
 scope='Full96 protected head seats and seven comparison levels,131072 literal candidates including score bits and192 explicit invalid provider slots. Actual TU publication store, global top2048 selector and full production AR/MTP remain unbound.')
record['passed']=record['positive']['passed'] and record['wrong_rank']['passed'] and record['wrong_order']['passed']
(root/'order-record.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
raise SystemExit(0 if record['passed'] else 1)
