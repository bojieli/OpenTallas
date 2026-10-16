"""Re-run every ./sql bash command of the first BI recording against the new sandbox; time each one."""
import json, glob, subprocess, time, sys, statistics as st
cmds = []
for d in sorted(glob.glob('/home/ubuntu/landing-scratch/genui2/rec/bi/[0-9][0-9]')):
    for l in open(f'{d}/events.jsonl'):
        e = json.loads(json.loads(l)['line']) if json.loads(l)['line'].startswith('{') else {}
        if e.get('type') == 'tool_call' and e['tool'] == 'bash':
            c = (e.get('input') or {}).get('command', '')
            if './sql' in c and 'screen.html' not in c: cmds.append(c.replace('/home/ubuntu/landing-scratch/genui2/bi', '/dev/shm/genui3/bi'))
T = []
for c in cmds:
    t0 = time.time(); r = subprocess.run(['bash', '-c', c], cwd='/dev/shm/genui3/bi', capture_output=True, text=True, timeout=120); dt = time.time() - t0
    T.append((dt, c[:100].replace('\n', ' '), 'SQL error' in r.stdout))
v = sorted(x[0] for x in T)
print(f'{len(T)} commands: median {st.median(v)*1000:.0f} ms, p90 {v[int(.9*(len(v)-1))]*1000:.0f} ms, max {v[-1]*1000:.0f} ms, total {sum(v):.1f} s, errors {sum(x[2] for x in T)}')
for x in sorted(T, reverse=True)[:int(sys.argv[1]) if len(sys.argv) > 1 else 6]: print(f'  {x[0]*1000:7.0f} ms  {x[1]}')
