import sys,csv
import numpy as np
f,vs,out=sys.argv[1],float(sys.argv[2]),sys.argv[3]
X=[];Y=[];D=[]
with open(f) as fh:
    r=csv.reader(fh); next(r)
    for row in r:
        v=float(row[5]); X.append(float(row[3])); Y.append(float(row[4])); D.append((v if vs==0 else vs-v)*1e3)
X=np.array(X);Y=np.array(Y);D=np.array(D)
bs=5.0
nx=int(X.max()//bs)+1; ny=int(Y.max()//bs)+1
G=np.zeros((ny,nx))
np.maximum.at(G,( (Y//bs).astype(int),(X//bs).astype(int)),D)
np.save(out+'.npy',G)
pass



# row/col profiles
print('rowmax(y bins of 50um):',[round(G[int(i/bs):int((i+50)/bs)].max(),2) for i in range(0,int(ny*bs),50)])
print('colmax(x bins of 50um):',[round(G[:,int(i/bs):int((i+50)/bs)].max(),2) for i in range(0,int(nx*bs),50)])
