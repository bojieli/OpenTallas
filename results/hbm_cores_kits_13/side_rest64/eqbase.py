# HBM-CORES-KITS-13: exact finite-prefix base case of the 4 gold-gold equality hypotheses in kept4.json
# (raw_prefix_miter: STEPS edges from entirely free state, fresh inputs + RTL X each edge, no reset/hyp/X mask).
import pathlib,sys,json,os,collections
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));import lec_engine as lec
src=pathlib.Path(os.environ["K13_INPUT"]);out=pathlib.Path(os.environ["K13_EQOUT"]);out.mkdir(exist_ok=True);log=[]
g=lec.read_aig(src/"gold.aig");gm=lec.read_map(src/"gold.map")
L=lec.Lec(g,gm,lec.read_aig(src/"gate.aig"),lec.read_map(src/"gate.map"))
lec.normalize_gold_elements(L,lec.slang_elements(src/"gold.aliases.json"),log)
eqs=[(b,h) for a,b,h in json.loads((HERE/"kept4.json").read_text()) if h[0]=="eq" and a=="gold"]
for steps in tuple(int(s) for s in os.environ.get("K13_EQSTEPS","1,2,3,4").split(",")):
 roots=[];pairs=[]
 for k,h in eqs:
  roots+= [L.gc[k],L.gc[h[2]]]
 m=lec.raw_prefix_miter(L.gold,roots,steps)
 o=m.outs;m.outs=[m.XOR(o[2*i],o[2*i+1])^(h[3]&1) for i,(k,h) in enumerate(eqs)]
 m.onames=["eqbase:%s"%k for k,h in eqs]
 st=lec.prove(m,out,1000,log,tag="eqbase%d"%steps)
 print("steps",steps,collections.Counter(st.values()),[k.split("u_rsq.")[-1] for k,v in st.items() if v!="proved"],flush=True)
assert all(v=="proved" for v in st.values()), "equality initial base failed"
print("EQBASE_DONE",flush=True)
