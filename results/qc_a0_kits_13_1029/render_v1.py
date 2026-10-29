import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; from matplotlib.patches import Rectangle
RF=(115.344,140.4); RL=(172.8,110.16); ND=(47.52,432.0)
rom=[(x,y) for x in (22.488,268.32) for y in (22.176,152.352,282.528,412.704,542.88)]
rf_now=[(268.32,673.92),(268.32,834.432),(268.32,994.944),(142.152,834.432),(142.152,994.944),(15.984,673.92),(15.984,834.432),(15.984,994.944)]
dx=76.68-15.984
def draw(ax,title,rfs,node):
    ax.add_patch(Rectangle((0,0),457.92,1157.76,fill=False,lw=1.5))
    for x,y in rom: ax.add_patch(Rectangle((x,y),*RL,fc='#9ecae1',ec='k',lw=.5))
    for x,y in rfs: ax.add_patch(Rectangle((x,y),*RF,fc='#fdae6b',ec='k',lw=.5))
    ax.add_patch(Rectangle(node,*ND,fc='#a1d99b',ec='k',lw=.8)); ax.text(node[0]+3,node[1]+200,'NODE',rotation=90,fontsize=8)
    # tile W pins n_a/n_b/t_out/n_y, E pins tap/rst
    for (y0,y1,c,l) in ((699.6,800.6,'r','n_a'),(800.7,900.8,'m','n_b'),(901,1001.2,'b','t_out'),(1001.4,1102.6,'c','n_y')):
        ax.plot([0,0],[y0,y1],c,lw=4); ax.text(-40,(y0+y1)/2,l,fontsize=6,color=c)
    ax.plot([457.9,457.9],[561,674],'k',lw=4); ax.text(460,600,'tap/rst',fontsize=6)
    ax.plot(228.97,578.88,'k*',ms=8)
    ax.set_xlim(-50,520); ax.set_ylim(-10,1170); ax.set_aspect('equal'); ax.set_title(title,fontsize=8)
f,a=plt.subplots(1,3,figsize=(13,10))
draw(a[0],'NK now (node E col): 2056 node-bus bits cross ~390 um',rf_now,(394.488,688.656))
draw(a[1],'V1: node W edge x=20.52, rawfault cols +60.70 um',[(x+dx,y) for x,y in rf_now],(20.52,688.656))
v2=[(8.64,673.92),(8.64,834.432),(8.64,994.944),(132.62,834.432),(132.62,994.944),(256.61,673.92),(256.61,834.432),(256.61,994.944)]
v2=[(8.64 if x<100 else 132.62 if x<200 else 256.61,y) for x,y in rf_now]
draw(a[2],'V2: rawfault cols packed W (gap 8.64): only 13.9 um opens',v2,(394.488,688.656))
plt.tight_layout(); plt.savefig('nk_v1_v2_plan.png',dpi=90)
