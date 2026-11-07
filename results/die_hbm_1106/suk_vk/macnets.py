import re,sys,collections
f=sys.argv[1]; lef=sys.argv[2]
txt=open(f).read()
# LEF faces
L=open(lef).read()
size=re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)",L); W=float(size.group(1))
face={}
for m in re.finditer(r"PIN\s+(\S+)(.*?)END\s+\1",L,re.S):
    n=m.group(1); rs=re.findall(r"LAYER\s+(\S+)\s*;\s*RECT\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)",m.group(2))
    if not rs: continue
    x=float(rs[0][1]); face[n]=("W" if x<W/2 else "E",rs[0][0])
print("LEF W",W,"pins",len(face),collections.Counter(face.values()))
inst=re.findall(r"\bot_sram_\S+\s+(\S+)\s*\((.*?)\);",txt,re.S)
print("insts",len(inst))
tot=collections.Counter(); netuse=collections.defaultdict(set); rows=[]
for nm,body in inst:
    c=collections.Counter()
    for pm in re.finditer(r"\.(\w+)\(\s*(.*?)\s*\)\s*(?:,|$)",body,re.S):
        pin,conn=pm.group(1),pm.group(2)
        if conn.startswith("{"):
            items=[s.strip() for s in conn.strip("{} \n").split(",")]
        else: items=[conn] if conn else []
        ex=[]
        for it in items:
            mm=re.match(r"(\d+)'[hbd]([0-9a-fA-F]+)$",it)
            if mm:
                ex+=["CONST"]*int(mm.group(1))
            else: ex.append(it)
        n=len(ex)
        for k,net in enumerate(ex):
            idx=n-1-k
            pn=f"{pin}[{idx}]" if n>1 or f"{pin}[0]" in face else pin
            fc=face.get(pn,face.get(pin,("?","?")))[0]
            if net=="CONST": c[(fc,pin,"const")]+=1
            elif net=="" : c[(fc,pin,"open")]+=1
            else:
                c[(fc,pin,"net")]+=1; netuse[net].add(nm)
    rows.append((nm,c)); tot.update(c)
for nm,c in rows[:1]:
    print(nm); [print(" ",k,v) for k,v in sorted(c.items())]
print("total"); [print(" ",k,v) for k,v in sorted(tot.items())]
print("distinct nets",len(netuse),"shared>1 macro",sum(1 for v in netuse.values() if len(v)>1))
