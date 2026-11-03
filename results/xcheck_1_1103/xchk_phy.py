"""XCHECK-1 PHY census: per die, PHY-like hard macros in type contents -> lib file, min_period, setup/hold/clk->q (tt/ff/ss)."""
import json, re, sys, subprocess, collections, os
wt = sys.argv[1]; plans = sys.argv[2:]
files = subprocess.run(['git', '-C', wt, 'ls-files', '*.lib'], capture_output=True, text=True).stdout.split()
bymod = collections.defaultdict(list)
for f in files:
    b = os.path.basename(f)
    m = re.match(r'(.+?)_(tt|ff|ss)(_[^.]*)?\.lib$', b)
    if m: bymod[m.group(1)].append(f)
def libinfo(f):
    s = open(os.path.join(wt, f), errors='ignore').read()
    mp = re.findall(r'min_period\s*:\s*([\d.]+)', s)
    # first scalar values of setup/hold/rise tables are model-dependent; grab simple "values (\"x\")" after timing_type
    out = {'min_period': mp[:1]}
    for tt in ('setup_rising', 'hold_rising', 'rising_edge'):
        i = s.find('timing_type : ' + tt)
        if i < 0: i = s.find('timing_type : "' + tt)
        if i >= 0:
            v = re.search(r'values\s*\(\s*"([^"]+)"', s[i:i + 3000])
            out[tt] = v.group(1).split(',')[0].strip() if v else None
    tu = re.search(r'time_unit\s*:\s*"([^"]+)"', s); out['tu'] = tu.group(1) if tu else None
    return out
seen = set()
for pf in plans:
    p = json.load(open(pf)); die = p['die'].get('name'); T = p['partition_types']
    used = collections.Counter(q['type'] for q in p['partitions'])
    for tn, t in T.items():
        if tn not in used: continue
        for c in (t.get('contents') or []):
            if not isinstance(c, dict): continue
            m = c.get('module', '')
            if not re.search(r'phy|serdes|ucie|pma|pdie', m, re.I): continue
            k = (die, m)
            if k in seen: continue
            seen.add(k)
            libs = sorted(bymod.get(m, []))
            info = {os.path.basename(l): libinfo(l) for l in libs if re.search(r'_(tt|ff)\.lib$', l)}
            print(json.dumps({'die': die, 'type': tn, 'n': used[tn], 'module': m, 'status': c.get('status'), 'libs': len(libs), 'info': info})[:700])
