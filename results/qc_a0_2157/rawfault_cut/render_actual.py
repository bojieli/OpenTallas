from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=Path('/srv/opentallas-scratch/claude/codex-qc-a0-2157');a=[x.split('\t')for x in(r/'placed_inst.tsv').read_text().splitlines()];p=[x.split('\t')for x in(r/'placed_pin.tsv').read_text().splitlines()];f,ax=plt.subplots(figsize=(9,10))
for ff,c,size in [(False,'#51718a',.5),(True,'#db8526',1)]:
 q=[x for x in a if x[1].startswith('DFF')==ff];ax.scatter([(float(x[2])+float(x[4]))/2 for x in q],[(float(x[3])+float(x[5]))/2 for x in q],s=size,c=c,alpha=.45,label='FF'if ff else 'logic')
ax.scatter([float(x[2])for x in p],[float(x[3])for x in p],s=3,c='red',label='actualpins');ax.set_xlim(0,115.344);ax.set_ylim(0,140.4);ax.set_aspect('equal');ax.legend();ax.set_title('Actual originalMODE3 rawfault LSL DPL\n76731sourcecells ->58386synthcells,12030FF\nAll114output anchors;390sourceinput FFmap exists\n193inputs await source-based anchor hook; no CTS/signoff')
f.savefig('/srv/opentallas-scratch/claude/wt/codex-qc-a0-2157/results/qc_a0_2157/rawfault_cut/actual_placement.png',dpi=130)
