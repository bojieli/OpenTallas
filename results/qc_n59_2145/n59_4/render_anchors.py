import json,re,sys,matplotlib;matplotlib.use("Agg");import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=json.load(open(sys.argv[1]));pos=p['positions'];M=p['macros']
A={};import re
for l in open(sys.argv[2]):
    m=re.match(r'\s*\{\{(.*)\} ([\d.]+) ([\d.]+)\}',l);A[m[1]]=(float(m[2]),float(m[3]))
cls=[("svc p_cmd/emb/ea/dvf",r"u_svc\.(p_cmd|emb_|ea_c|dvf|g_ctxmu)","#d62728"),("formatter wd/wa/we_q + g_safe",r"u_formatter","#ff7f0e"),("qseat/qb_row",r"u_qseat\.|qb_row","#2ca02c"),("f_dd/rep/p_dd/dd_m",r"u_qb\.(f_dd|q[emd]_rep|p_dd|dd_m)","#17becf"),("pd chains",r"u_pd\d","#bcbd22"),("dr_o",r"dr_o","#e377c2"),("svc slot obs",r"g_slot","#9467bd")]
fig,ax=plt.subplots(1,2,figsize=(24,9),dpi=100)
for k,a in enumerate(ax):
    for b in M:a.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fc="#dddddd",ec="k",lw=0.6))
    regs=p['registers'];a.scatter([pos[r][0] for r in regs],[pos[r][1] for r in regs],s=0.15,c="#cccccc")
    for nm,rx,col in cls:
        S=[r for r in A if re.search(rx,r.replace('\\',''))]
        P=[pos[r] for r in S] if k==0 else [A[r] for r in S]
        a.scatter([q[0] for q in P],[q[1] for q in P],s=1.2,c=col,label=f"{nm} ({len(S)})")
    a.set_xlim(0,777.6);a.set_ylim(0,518.4);a.set_aspect("equal");a.legend(loc="upper left",fontsize=7,markerscale=5)
ax[0].set_title("current3 post-DPL: the 4746 registers to anchor, at their placed sites (21831 arcs >405)")
ax[1].set_title("joint L1-minimax anchor sites (model): 274 arcs >405 left = p_cmd->ea_c decode")
fig.savefig(sys.argv[3],bbox_inches="tight")
