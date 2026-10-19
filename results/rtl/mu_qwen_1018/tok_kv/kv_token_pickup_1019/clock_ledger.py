import re,json,hashlib,pathlib
p=pathlib.Path('/srv/opentallas-scratch/claude/qwen-kvsys/kvs14r-4db097403-codexmub/port_bind_v2/die_bound.v')
s=p.read_text();rows=[]
for line in s.splitlines():
 m=re.match(r'\s*(\w+) (head_WS_0_0__\w+) \((.*)\);',line)
 if not m:continue
 ports=dict(re.findall(r'\.(\w+)\(([^()]*)\)',m[3]))
 rows.append(dict(master=m[1],instance=m[2],ports={k:v for k,v in ports.items() if re.search(r'clk|ck|rst|reset|kpv|valid',k)}))
out=dict(die=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),head='head_WS_0_0',instances=rows,clock_phase_age_proof='not established; connectivity identities only')
pathlib.Path('pickup-proof/head_WS_0_0_clock_reset.json').write_text(json.dumps(out,indent=2)+'\n')
for r in rows:print(r['master'],r['instance'],r['ports'])
print('HEAD_INSTANCES',len(rows))
