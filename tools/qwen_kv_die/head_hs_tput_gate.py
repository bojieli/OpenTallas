#!/usr/bin/env python3
"""Source-pinned hierarchical head production step against the immutable class price."""
import hashlib, json, pathlib, subprocess, sys
def source_commit():
    # The closure loop runs benches from a source archive (no .git): it writes SOURCE_COMMIT there.
    f=pathlib.Path('SOURCE_COMMIT')
    if f.is_file() and f.read_text().strip(): return f.read_text().strip()
    return subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
rows=[json.loads(x) for x in pathlib.Path(sys.argv[1]).read_text().splitlines() if x.strip()]
base=[r for r in rows if r['run']=='base']
price_path=pathlib.Path('results/rtl/tput_map_1011/qwen_kv_die/record.json')
price=json.loads(price_path.read_text())['price']['cycles']
assert price==1816, 'published price changed; review the immutable baseline'
production=[r for r in base if r['vec'] in ('8192_normal','8192_peaky','8191_mixed')]
steps={r['vec']:r['res']['marks']['res_last_at_vm']-r['res']['marks']['ctl_sent'] for r in production if r['res']}
exact=len(base)==14 and all(r['rc']==0 and r['res'] and r['res']['exact'] for r in base)
cycles=max(steps.values()) if steps else None
ratio=cycles/price if cycles else None
ok=exact and len(production)==6 and ratio is not None and ratio<=1.10
record={'schema':'opentallas.qwen-head-hs-tput.v1','source_commit':source_commit(),'baseline_path':str(price_path),'baseline_sha256':hashlib.sha256(price_path.read_bytes()).hexdigest(),'price_cycles':price,'measured_cycles':cycles,'ratio':ratio,'per_vector':steps,'exact_runs':len(base),'exact':exact,'production_runs':len(production),'configuration':'HSUB=1 DQ=64 HT=1 SBD=16 HUBT=1 R8, ctx8192, VM stalls0/1','qualified':ok}
pathlib.Path(sys.argv[2]).write_text(json.dumps(record,indent=2)+'\n')
print(f'HEAD_HS_TPUT {"PASS" if ok else "FAIL"} cycles={cycles} price={price} ratio={ratio}')
sys.exit(0 if ok else 1)
