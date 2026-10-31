# DIE-HEAD-50: remap (by tap NAME) rr_t<i> raw-reset tap nets in a type after make_l48b added clock taps (reset taps are indexed after the clock taps, so they shift); match by identical tap xy
import json,sys,re
sys.path.insert(0,".")
import schema as S, reset_tree as RT, taps as TP
old,new,types=sys.argv[1],sys.argv[2],sys.argv[3].split(",")
def clear():
    for m in (TP,RT):
        for c in ("_CACHE","_TAPS"):
            if isinstance(getattr(m,c,None),dict): getattr(m,c).clear()
po=json.load(open(old+"/source_plan.json")); pn=json.load(open(new+"/source_plan.json"))
rep={}
for tn in types:
    clear(); a=RT.for_type(S.Plan(po),tn); clear(); b=RT.for_type(S.Plan(pn),tn)
    ta=list(a["taps"]); tb=list(b["taps"])  # tap names (clk, clk_tN, local reset taps, oK outs)
    na,nb=a["n_clock_taps"],b["n_clock_taps"]
    txt=json.dumps(pn["partition_types"][tn]); m={}
    for i in sorted({int(x) for x in re.findall(r"rr_t(\d+)\b",txt)}):
        if i<na: j=i; assert ta[i]==tb[j],(tn,i)
        else:
            c=[j for j in range(nb,len(tb)) if tb[j]==ta[i]]; assert len(c)==1,(tn,i,ta[i],c); j=c[0]
        m[i]=j
    txt=re.sub(r"rr_t(\d+)\b",lambda x:"rr_t%d"%m[int(x.group(1))],txt)
    pn["partition_types"][tn]=json.loads(txt); rep[tn]={k:v for k,v in m.items() if k!=v}
json.dump(pn,open(new+"/source_plan.json","w"),indent=1); open(new+"/source_plan.json","a").write("\n")
print(json.dumps(rep))
