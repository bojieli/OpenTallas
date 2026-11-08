import json,sys
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.patches as pa
p=json.load(open(sys.argv[1])); out=sys.argv[2]
parts={q['name']:q for q in p['partitions']}
fig,ax=plt.subplots(figsize=(16,7.6))
for pn,col in (('host_w','#dbe9f6'),('host_e','#fbe3d6')):
    q=parts[pn]; t=p['partition_types'][q['type']]; x0,y0=q['origin_um']; x0-=parts['host_w']['origin_um'][0]; y0-=parts['host_w']['origin_um'][1]
    W,H=t['outline_um']; ax.add_patch(pa.Rectangle((x0,y0),W,H,fc=col,ec='k',lw=1.5))
    ax.text(x0+W/2,H+8,f"{q['type']} ({W}x{H})  {len(t['hard_cores'])} macros",ha='center',fontsize=10)
    for h in t['hard_cores']:
        hx,hy=h['origin_um']; hw,hh=h['outline_um']
        ax.add_patch(pa.Rectangle((x0+hx,y0+hy),hw,hh,fc='#999',ec='#444',lw=.4))
    for b in t['buses']:
        a,bb=b['window_um']; f=b['face']; c='red' if b['name'].startswith('l1_') else 'blue'
        if f in 'EW':
            xx=x0+(W if f=='E' else 0); ax.plot([xx,xx],[y0+a,y0+bb],c=c,lw=5,alpha=.7); ax.text(xx+(4 if f=='E' else -4),y0+(a+bb)/2,b['name']+f" {b['width']}",fontsize=7,rotation=90,ha='left' if f=='E' else 'right',va='center',color=c)
        else:
            yy=y0+(H if f=='N' else 0); ax.plot([x0+a,x0+bb],[yy,yy],c=c,lw=5,alpha=.7); ax.text(x0+(a+bb)/2,yy+(4 if f=='N' else -10),b['name']+f" {b['width']}",fontsize=7,ha='center',color=c)
    for s in t['clock'].get('sink_sites_um',[]): ax.plot(x0+s[0],y0+s[1],'g.',ms=3)
    tx,ty=t['clock']['tap_um']; ax.plot(x0+tx,y0+ty,'k*',ms=12)
    for r in t['reset'].get('local_taps_um',[]): ax.plot(x0+r[0],y0+r[1],'m^',ms=6)
ax.axvline(648,ls='--',c='k',lw=.8)
ax.set_xlim(-60,1360); ax.set_ylim(-40,620); ax.set_aspect('equal'); ax.set_title('HSPLIT probe plan (l48uo + head_host_split_delta): blue=die buses, red=seam l1_rx 558 E->W / l1_tx 554 W->E; *=clock tap, ^=reset taps, .=sink sites')
fig.savefig(out,dpi=110,bbox_inches='tight')
