import json, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
s=json.load(open('straps.json')); new=json.load(open('ep_new.json'))['endpoints']; old=json.load(open('ep_old.json'))['endpoints']
phy=[[103.68,16375.92,17418.24,17452.8],[103.68,103.68,17418.24,1180.56]]
def draw(ax,box,title):
    X0,Y0,X1,Y1=box
    for r in phy: ax.add_patch(plt.Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],color='#f3c',alpha=.12,lw=0))
    for z in s:
        c='b' if z[4]=='serdes_row' else 'k'; lw=1.6 if z[4]=='serdes_row' else .5
        if z[0]=='M8': ax.plot([z[2],z[3]],[z[1],z[1]],c,lw=lw)
        else: ax.plot([z[1],z[1]],[z[2],z[3]],c,lw=lw)
    o=[e['die_xy_um'] for e in old if e['type']=='hd_serdes']; n=[e['die_xy_um'] for e in new if e['type']=='hd_serdes']
    ax.scatter([p[0] for p in o],[p[1] for p in o],s=18,facecolors='none',edgecolors='r',label='old R4 grid taps (in VDDPHY window)')
    ax.scatter([p[0] for p in n],[p[1] for p in n],s=22,c='g',marker='s',label='R21 edge taps (core-VDD strip)')
    g=[e['die_xy_um'] for e in new if e['type']!='hd_serdes']
    ax.scatter([p[0] for p in g],[p[1] for p in g],s=2,c='0.5')
    ax.set_xlim(X0,X1); ax.set_ylim(Y0,Y1); ax.set_title(title,fontsize=9); ax.legend(loc='upper right',fontsize=7)
fig,ax=plt.subplots(2,1,figsize=(16,10),dpi=100)
draw(ax[0],(0,0,17521.92,2400),'HEAD-R21 bottom band: pink=VDDPHY window, blue=mesh serdes_row M8, black=mesh; red o=old taps, green=new taps')
draw(ax[1],(0,15150,17521.92,17556.48),'HEAD-R21 top band')
fig.savefig('r21_serdes_taps.png',bbox_inches='tight')
fig,ax=plt.subplots(figsize=(12,8),dpi=100); draw(ax,(11400,0,14800,1500),'zoom lk_ES0'); fig.savefig('r21_serdes_taps_zoom.png',bbox_inches='tight')
