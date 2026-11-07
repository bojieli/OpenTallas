import re,sys,collections
f=sys.argv[1]
txt=open(f).read()
inst=re.findall(r"\bot_sram_\S+\s+(\S+)\s*\((.*?)\);",txt,re.S)
use=collections.defaultdict(list)
for nm,body in inst:
    for pm in re.finditer(r"\.(\w+)\(\s*(.*?)\s*\)\s*(?:,|$)",body,re.S):
        pin,conn=pm.group(1),pm.group(2)
        items=[s.strip() for s in conn.strip("{} \n").split(",")] if conn.startswith("{") else [conn]
        for it in items:
            use[it].append((nm[-12:],pin))
print("top nets:")
for n,v in sorted(use.items(),key=lambda kv:-len(kv[1]))[:8]:
    print(" ",n,len(v),collections.Counter(p for _,p in v).most_common(5),len({m for m,_ in v}))
# real signals per pin group
per=collections.Counter(); singles=collections.Counter()
for n,v in use.items():
    if len(v)>8: 
        for m,p in v: per[("hifan",p)]+=1
    else:
        for m,p in v: per[("sig",p)]+=1
print(sorted(per.items()))

c=collections.Counter(re.findall(r"^\s*(TIE\w+)\s",txt,re.M)); print("ties",c)
for n,v in sorted(use.items(),key=lambda kv:-len(kv[1]))[:4]:
    print(n, re.findall(r"^.*\.[HL]\(\s*"+re.escape(n)+r"\s*\).*$",txt,re.M)[:1], txt.count("("+n+")"))
