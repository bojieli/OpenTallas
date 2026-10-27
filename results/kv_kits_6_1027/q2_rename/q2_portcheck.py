import json,re,sys
sv=open(sys.argv[1]).read()
m=re.search(r"module qkd_ectlk_q2 \((.*?)\);",sv,re.S)
ports={}
for d,w,n in re.findall(r"(input|output) wire (?:\[(\d+:\d+)\] )?(\w+)",m.group(1)):
  hi,lo=(map(int,w.split(":")) if w else (0,0)); ports[n]=(d,set(range(min(hi,lo),max(hi,lo)+1)),bool(w))
rtlbits={(n,b) for n,(d,s,v) in ports.items() for b in s}
for f in sys.argv[2:]:
  P=json.load(open(f))["pins"]; bad=[]; seen=set()
  for p in P:
    mm=re.fullmatch(r"(\w+)(?:\[(\d+)\])?",p["name"]); n,b=mm.group(1),int(mm.group(2) or 0)
    if (n,b) not in rtlbits: bad.append(p["name"])
    seen.add((n,b))
  print(f.split("/")[-1], "pins",len(P),"not_in_rtl",len(bad),bad[:6],"rtl_bits_without_pin",len(rtlbits-seen),sorted(rtlbits-seen)[:6])
