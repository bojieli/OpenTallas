import json,re,collections
R="/srv/opentallas-scratch2/claude/hbm-bind-4/"
Y=json.load(open(R+"g1/asbuilt.json"))["modules"]["hbm_current_native_top"]
cells=Y["cells"]; ports=Y["ports"]
fam={"cij":"cij_","cxij":"cxij_","hb_dbk":"hb_dbk_","hb_quant_u_dec":"hb_quant_","hcollgi":"hcollgi_","hcollgl":"hcollgl_","pgp":"pgp_","sfup":"sfup_","sfus":"sfus_","smw":"smw_","wbk":"wbk_","xl_ctl":"xl_"}
names=[n for n in cells if not n.startswith("$")]
for f,pre in fam.items():
    hit=sorted(n for n in names if re.match(r"(u_)?"+pre,n) and "ctl" in n or re.match(r"(u_)?"+pre+r"(NE|NW|SE|SW)",n))
    print(f,hit[:10],len(hit))
# drivers
drv={}
for cn,c in cells.items():
    for p,bits in c["connections"].items():
        d=c.get("port_directions",{}).get(p)
        if d=="output":
            for b in bits:
                if not isinstance(b,str): drv[b]=(cn,p)
sink=collections.defaultdict(set)
for cn,c in cells.items():
    for p,bits in c["connections"].items():
        if c.get("port_directions",{}).get(p)=="input":
            for b in bits:
                if not isinstance(b,str): sink[b].add((cn,p))
g=collections.defaultdict(lambda:[0,0,set(),set(),0])
for pn,p in ports.items():
    if p["direction"]!="input": continue
    if pn in("rst_n","clk_hbm","clk_stream") or pn.startswith("lk_"): continue
    s=set()
    for b in p["bits"]:
        s|=sink.get(b,set())
    nr=pn.startswith("native_required__")
    fm=re.sub(r"(_?)(NE|NW|SE|SW|\d+)","",pn.replace("native_required__",""))[:28]
    e=g[(nr,fm)]; e[0]+=1;e[1]+=len(p["bits"]);e[2]|={x[0] for x in s}
    if not s: e[4]+=len(p["bits"])
print("inputs by family (nr,family): ports bits nosinkbits sinks")
for k,e in sorted(g.items(),key=lambda x:(x[0][0],-x[1][1])):
    if not k[0]: print(k[1],e[0],e[1],e[4],sorted(e[2])[:3])
print("non-native tot",sum(e[1] for k,e in g.items() if not k[0]),sum(e[0] for k,e in g.items() if not k[0]))
print("nr tot",sum(e[1] for k,e in g.items() if k[0]),sum(e[0] for k,e in g.items() if k[0]),"zero-sink",sum(e[4] for k,e in g.items() if k[0]))
