import sys,json,glob,os
sys.path.insert(0,sys.argv[1])
import kit_ln_copies as K, kit_ln_copies_proof as KP
B=sys.argv[2]; NG=sys.argv[3]; out=[]
for f in sorted(glob.glob(B+'/s81p_ot_s81sl_*leaf__t*.sv')):
    tn=os.path.basename(f)[5:-3]; old=open(f).read()
    t,m,r=K.apply(old,True,[NG])
    ok,why=KP.text_check(old,t,r)
    out.append((tn,ok,r['relay']['shared_bit'],r['cf']['readers'],len(r['relay']['lanes'])))
print(json.dumps(dict(n=len(out),text_ok=sum(o[1] for o in out),bits=sorted(set(o[2] for o in out)),readers=sorted(set(o[3] for o in out)),lanes=sorted(set(o[4] for o in out)),bad=[o for o in out if not o[1]],types=[o[0] for o in out])))
