import json,sys,matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; from matplotlib.patches import Rectangle
t=json.load(open(sys.argv[1])); W,H=t['outline_um']; f,a=plt.subplots(figsize=(18,10))
a.add_patch(Rectangle((0,0),W,H,fc='#f4f6f8',ec='k'))
for h in t['hard_cores']:
    x,y=h['origin_um'];w,hh=h['outline_um'];n=h['inst']
    col='#5b9bf0' if n.startswith('u_vmb') else '#f4a6cf' if n.startswith('u_mu_fused_') and n[11].isdigit() else '#7ee2a0' if 'mu_fused_n' in n else '#ffe08a' if any(k in n for k in ('hb_vms','xl_Q_ctl','smw','dbk','calendar','vmdel')) else '#c9ccd3'
    a.add_patch(Rectangle((x,y),w,hh,fc=col,ec='k',lw=.4))
    if w*hh>9e4 or 'mu_fused_n' in n: a.text(x+w/2,y+hh/2,n.replace('u_','')[:16],fontsize=5,ha='center',va='center')
for s in t['internal_stations']:
    if str(s.get('conn','')).startswith('mu_tree') and ('n4' in s['conn']):
        p=[s['from_um']]+s.get('regs_um',[])+[s['to_um']]; a.plot([q[0] for q in p],[q[1] for q in p],'r-',lw=1)
a.axvline(3957.12,color='orange',ls=':'); a.set_xlim(-50,W+50); a.set_ylim(-50,H+50); a.set_aspect('equal')
a.set_title(sys.argv[3]); plt.tight_layout(); plt.savefig(sys.argv[2],dpi=110)
