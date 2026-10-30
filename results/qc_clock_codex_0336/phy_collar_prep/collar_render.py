import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,ax=plt.subplots(1,2,figsize=(12,7))
for a,title in zip(ax,['Existing fullbits construction constraints','Reviewed PREP fallback: paired collars']):
 a.set_title(title);a.add_patch(Rectangle((0,0),1563.57,2320.056,fc='#ddd',ec='black'));a.set_xlim(650,1700);a.set_ylim(2040,2430);a.set_aspect('equal');a.set_xlabel('local x (um)');a.set_ylabel('local y (um)')
ax[0].add_patch(Rectangle((0,2320.056),1563.84,8.208,fc='orange',alpha=.5));ax[0].plot([753,810.534],[2319.96]*2,'r-',lw=5);ax[0].plot([782.136,1036.32],[2324.16]*2,'b-',lw=3);ax[0].plot([811]*2,[2208,2330],color='purple',ls='--');ax[0].text(850,2160,'1057 bits across x811\n~104um M6 overbody depth\nif channel M4/M6 carries 85');ax[0].text(1100,2350,'3.888um usable gap\nno native-body repeaters',fontsize=9)
ax[1].add_patch(Rectangle((0,2320.056),1632.96,73.224,fc='lightgreen',ec='green'));ax[1].add_patch(Rectangle((1563.84,0),69.12,2393.28,fc='lightgreen',ec='green'));ax[1].plot([753,810.534],[2319.96]*2,'r-',lw=5);ax[1].plot([782.136,1036.32],[2393.28]*2,'b-',lw=3);ax[1].plot([800,800,1598,1598],[2320,2358.72,2358.72,2050],'m--');ax[1].text(880,2230,'69.12um N + E usable collars\n1512-track cut upper budget\n1 N-bank / 9 E-bank proposal\npaired neighbor repack UNPROVEN',fontsize=9)
fig.suptitle('Licensed N-face SerDes preserved; PREP only — no timing/route/adoption')
fig.tight_layout();fig.savefig('/tmp/qcclock0336/collar_geometry_prep.png',dpi=160)
