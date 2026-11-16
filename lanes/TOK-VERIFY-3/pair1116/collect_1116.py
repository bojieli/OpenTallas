from pathlib import Path
import json,re,sys
p=Path(sys.argv[1]);r=json.loads((p/'inputs.json').read_text());log=(p/'run.log').read_text()
sys.path.insert(0,'/srv/opentallas-scratch2/claude/kw45/src_kv_pin_eb1e73448bd0/tools/qwen_kv_die/bc4_epoch_1113');from epoch_calendar import epoch_calendar
summary=next(x for x in log.splitlines() if x.startswith('RESULT '));vals={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',summary)}
assert 'BC4_EPOCH_PASS' in log and vals['errors']==vals['rf_errors']==0
assert vals['stale_differences']>0 and vals['lost_base_errors']==3 and vals['early_by']==3 and vals['rf_min_cfg_gap']==2
origins=[int(x) for x in re.findall(r'^EPOCH input_sample=(\d+)',log,re.M)];events=[]
for n in origins:
 e=epoch_calendar(n,r['profile']);c=e['source_control_events']
 assert f"START source_sample={c['admission']} " in log
 assert f"BASE source_sample={c['token_base_tx']} side=TX value=2" in log
 assert f"BASE source_sample={c['token_base_rx']} side=RX value=4" in log
 assert f"START source_sample={c['first_token']} " in log
 rf=epoch_calendar(n,r['profile'],rf=True);assert f"FEEDBACK_START receiver_sample={rf['d2d_control_sampling_events']['first_token']} " in log
 events.append(dict(native=e,rf=rf))
assert len(events)==3
r.update(status='PASS_COMPONENT_ONLY',summary=vals,observed_epochs=events,build_time=(p/'build.time').read_text().strip(),runtime=(p/'run.time').read_text().strip(),initial_assumed_example_origin=222)
# Inputs preserve the initial illustrative epoch222. The actual measured origin is221; the formula matches every observed event.
(p/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(status=r['status'],summary=vals,first_epoch=events[0],build_time=r['build_time'],runtime=r['runtime'])))
