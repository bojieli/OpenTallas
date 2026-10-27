"""Gate copy for check.py (b1-native schema 8dba47653): drop the opt-in R9-R13 model keys on internal_stations that no
schema version declares (serial_k, bits_parallel, r9_segments, r13_* ...). 'bits' already holds the serialised wire
count. Everything else is unchanged. Usage: strip_gate_copy.py IN_PLAN OUT_PLAN g0_report.json"""
import json, sys, re, collections
src, dst, rep = sys.argv[1:4]
r = json.load(open(rep)); keys = collections.Counter()
for f in r['findings']:
    m = re.search(r"internal_stations\[\d+\]: unknown key '([^']+)'", f.get('msg', ''))
    if f.get('check') == 'schema' and m: keys[m.group(1)] += 1
other = [f['msg'] for f in r['findings'] if f.get('check') == 'schema' and 'internal_stations' not in f.get('msg', '')]
P = json.load(open(src)); n = 0
for t in P['partition_types'].values():
    for s in t.get('internal_stations', []):
        for k in keys:
            if k in s: s.pop(k); n += 1
json.dump(P, open(dst, 'w'), indent=1)
print(json.dumps(dict(stripped_keys=dict(keys), removed=n, other_schema_errors=len(other), other_sample=other[:5])))
