import json,sys,collections
def load(f):
    r=json.load(open(f)); return r, collections.Counter(json.dumps(e,sort_keys=True) for e in r["findings"])
ra,a=load(sys.argv[1]); rb,b=load(sys.argv[2])
print(ra["verdict"],ra["errors"],ra["pending_view"],ra["warnings"],"|",rb["verdict"],rb["errors"],rb["pending_view"],rb["warnings"])
print("only base:",sum((a-b).values()),"only new:",sum((b-a).values()))
for s in (a-b): print("-",s[:400])
for s in (b-a): print("+",s[:400])
if len(sys.argv)>3:
    for s in a:
        if '"ERROR"' in s: print("ERR",s[:300])
