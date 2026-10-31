#!/usr/bin/env python3
"""g0delta.py BASE_REPORT NEW_REPORT -> exact message delta (errors/warnings), counts."""
import json, sys, collections
def msgs(p):
    j = json.load(open(p)); out = collections.Counter()
    def walk(o):
        if isinstance(o, dict):
            if "level" in o and ("msg" in o or "message" in o):
                out[(o["level"], o.get("check", o.get("rule", "")), o.get("msg", o.get("message")))] += 1
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(j); return out, j
a, ja = msgs(sys.argv[1]); b, jb = msgs(sys.argv[2])
new = b - a; gone = a - b
lv = lambda c, l: sum(v for k, v in c.items() if k[0] == l)
print(json.dumps(dict(base={l: lv(a, l) for l in ("ERROR", "WARN")}, new={l: lv(b, l) for l in ("ERROR", "WARN")},
                      new_msgs=sum(new.values()), gone_msgs=sum(gone.values()))))
for k in list(new)[:12]: print("NEW ", k[0], k[1], str(k[2])[:260])
for k in list(gone)[:12]: print("GONE", k[0], k[1], str(k[2])[:260])
