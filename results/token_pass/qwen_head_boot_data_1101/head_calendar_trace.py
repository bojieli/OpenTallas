import json,collections,hashlib,sys
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/qwen_layerbench')
import dv_lower as D
base=Path('/home/ubuntu/OpenTallas/results/rtl/qe3_ctlm3_1021/selected_source/rtl/test/qwen_dv/calr_port')
paths=[base/f'calendar_m{i}.viamap.hex' for i in range(2)]
rows=[[int(s,16) for s in p.read_text().split()] for p in paths]
def macro(m,a):return sum(((rows[m][a//8]>>(8*b+a%8))&1)<<b for b in range(266))
words=[macro(0,a)|(macro(1,a)<<266) for a in range(256)]
dw=[int(s,16) for s in (base/'dw.hex').read_text().split()]
first,count=(dw[3]>>16)&65535,dw[3]&65535
entries=[]; elapsed=0
for idx in range(first,first+count):
 e=(words[idx//4]>>(128*(idx%4)))&((1<<128)-1)
 cmd=e&((1<<116)-1)
 d=D.decode_cmd(cmd); elapsed+=e>>116
 entries.append(dict(index=idx,segment_relative_issue_edge=elapsed,stored_delay=e>>116,cmd_hex=f'{cmd:029x}',decoded=d))
report=dict(scope='Selected actual59P CALR HEAD37 physical masks, decoded source fields only',first=first,count=count,
 sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[base/'dw.hex']},
 kinds=dict(collections.Counter(e['decoded']['kind'] for e in entries)),
 root=[e for e in entries if e['decoded']['kind']==3],
 station_summary={k:sorted({e['decoded'][k] for e in entries if e['decoded']['kind']==2}) for k in ('mode','wsrc','nwords','sbase','sdst','amax','kc')},first_station_entries=[e for e in entries if e['decoded']['kind']==2][:4],
 native_SU_entries=[e for e in entries if e['decoded']['kind']==1])
report['selected_receiver_slices']=sorted({e['decoded']['dst'] for e in entries if e['decoded']['kind']==2 and e['decoded']['mode']==2})
report['native_s8_receiver_slices']=[1,3,5,6,8,10]
report['calendar_to_native_s8_btab_join']='MISMATCH' if report['selected_receiver_slices']!=report['native_s8_receiver_slices'] else 'MATCH'
boot_first,boot_count=(dw[4]>>16)&65535,dw[4]&65535
report['boot']=dict(first=boot_first,count=boot_count,entries=[])
for idx in range(boot_first,boot_first+boot_count):
    e=(words[idx//4]>>(128*(idx%4)))&((1<<128)-1); cmd=e&((1<<116)-1)
    report['boot']['entries'].append(dict(index=idx,decoded=D.decode_cmd(cmd)))
out=Path('/srv/opentallas-scratch/claude/wt/codex-qwen-headboot-1101/results/token_pass/qwen_head_boot_data_1101/head37_calendar_trace.json')
out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='entries'},indent=2))
