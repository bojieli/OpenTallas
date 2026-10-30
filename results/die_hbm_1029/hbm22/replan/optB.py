import sys, json, os
N=int(sys.argv[1]); mode=sys.argv[2]
sys.argv=['x','lanes.json','rows103.json','rows_h8b.json']
import replan_est as R, opt as O
if mode=='B':
    R.SIZE.update({'NW_spu0':466.56,'NW_spu1':1468.8+1218.24})
    A=[n for n in R.A0 if n not in ('NW_b110','NW_b111')]; C=R.C0+['NW_b111','NW_b110']
else:
    A=list(R.A0); C=list(R.C0)
res=[]
for seed in range(N):
    b=O.run(A,C,20000,seed); res.append(b)
    rect=R.apply_rows({'A':b[1][0],'C':b[1][1]}); s=R.score(rect)
    mv=[n for n in b[1][0]+b[1][1] if abs(rect[n][0]-R.rect0[n][0])>0.01 or abs(rect[n][1]-R.rect0[n][1])>0.01]
    print(seed,round(b[0]),{k:v for k,v in s.items() if k!='edge_over'},'moved',len(mv)); print('   A',b[1][0]); print('   C',b[1][1])
json.dump(res,open('optB_%s_%s.json'%(mode,os.environ.get('MOVEPEN','0')),'w'))
