import json, pathlib, subprocess, re
D=pathlib.Path('/srv/opentallas-scratch/claude/kv-tok/veh')
R=pathlib.Path('/srv/opentallas-scratch/claude/qwen-kvsys/kvs14r-4db097403-codexmub')
A=['python3',str(D/'tools/qwen_layerbench/kv_attn_grp_map_pickup.py'),'--die-v',str(R/'port_bind_v2/die_bound.v'),'--slice',str(D/'g7/P0/cut/slice.json'),'--relay-stages',str(R/'case_kv/relay_stages.json'),'--out',str(D/'pickup-proof/kva_grp_map.svh'),'--facts',str(D/'pickup-proof/kva_grp_facts.json'),'--stacks','WS,ES']
boot=R/'case_kv/boot_ages.json'
p=subprocess.run(A+['--boot-ages',str(boot)],capture_output=True,text=True);assert p.returncode==0,p.stderr
print(p.stdout,end='')
f=json.loads((D/'pickup-proof/kva_grp_facts.json').read_text());assert len(f['age_drives'])==9 and f['vport_programmable']==8
for row in f['age_drives']:
 print('BOOT_ASSIGN',row['net'],row['value'])
old=(D/'g7/P0/cut/kva_grp_map.svh').read_text().splitlines();new=(D/'pickup-proof/kva_grp_map.svh').read_text().splitlines()
assert [x for x in new if 'exact sealed boot age' not in x]==old
print('SOURCE_MAP_IDENTICAL_EXCEPT_9_BOOT_ASSIGNMENTS PASS')
p=subprocess.run(A,capture_output=True,text=True);assert p.returncode!=0 and 'zero is not a schedule' in p.stderr
print('MISSING_BOOT_REJECT PASS',p.stderr.strip())
b=json.loads(boot.read_text());b['words'][3]^=1;(D/'pickup-proof/bad_boot.json').write_text(json.dumps(b))
p=subprocess.run(A+['--boot-ages',str(D/'pickup-proof/bad_boot.json')],capture_output=True,text=True);assert p.returncode!=0 and 'disagree' in p.stderr
print('CORRUPT_BOOT_REJECT PASS',p.stderr.strip())
print('FIXTURE_BOOT_PROOF PASS (no RTL or gold changes; not token qualification)')
