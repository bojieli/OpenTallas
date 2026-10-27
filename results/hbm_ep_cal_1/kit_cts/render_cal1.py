import sys, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
B=[];S=[]
for l in open(sys.argv[1]):
    f=l.split()
    if f[0]=="B": B.append(tuple(map(float,f[1:5]))+(f[5],))
    elif f[0]=="S": S.append(tuple(map(float,f[1:6]))+(f[6],))
fig,ax=plt.subplots(figsize=(8,11))
ax.add_patch(plt.Rectangle((0,0),250.56,375.84,fill=False,lw=1.5))
for (mx,my) in [(34.56,17.28),(34.56,95.31),(34.56,202.77),(34.56,280.8)]: ax.add_patch(plt.Rectangle((mx,my),171.288,77.784,fill=True,fc="#dddddd",ec="gray"))
mac=[s for s in S if "sram" in s[5]]
for (x0,y0,x1,y1,m) in B: ax.plot([x0,x1],[y0,y1],"-",color="k",lw=0.6)
xs=[s[2] for s in S if "sram" not in s[5]]; ys=[s[3] for s in S if "sram" not in s[5]]; a=[s[4] for s in S if "sram" not in s[5]]
sc=ax.scatter(xs,ys,c=a,s=2,cmap="viridis",vmin=min(a),vmax=max(a))
for s in mac: ax.plot(s[2],s[3],"rs",ms=6)
bx=[b[2] for b in B]; by=[b[3] for b in B]; ax.plot(bx,by,"o",mfc="none",mec="r",ms=3,lw=0)
ax.plot(125.28,187.92,"b*",ms=14)
plt.colorbar(sc,label="TT insertion ps (placement RC)",shrink=0.6)
ax.set_aspect("equal"); ax.set_xlim(-5,256); ax.set_ylim(-5,381)
ax.set_title(sys.argv[3]); fig.tight_layout(); fig.savefig(sys.argv[2],dpi=110)
