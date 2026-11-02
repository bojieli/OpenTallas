from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent
names=['u_bound.u_bout_o_host_hbm_rst_n/eq$_DFF_PN0_','u_bound.u_ist_o_host_hbm_rst_n_3/eq$_DFF_PN0_','u_bound.u_rrl_101/q$_DFF_P_','u_bound.u_ist_o_kvs_hroot_Q_o_ctl_0/eq$_DFF_PN0_','u_bound.u_bout_o_kvs_hroot_Q_o_ctl/eq$_DFF_PN0_']
xy={}
for line in (R/'complete_model.tsv').open():
 a=line.rstrip().split('\t')
 if a[0]=='C' and a[-1] in names:
  z=list(map(float,a[4:8]));xy[a[-1]]=[(z[0]+z[2])/2,(z[1]+z[3])/2]
a=(431.968,.096);b=(1900.704,723.48);sep=sum(abs(x-y) for x,y in zip(a,b));cap=4*405+2*150
out=dict(scope='SOURCE_PRESERVING_INFEASIBILITY_CUT_NO_GATE_RELAXATION',source_pins={'o_host_hbm_rst_n[1]':a,'o_kvs_hroot_Q_o_ctl[144]':b},fixed_pin_manhattan_um=sep,existing_path_seq_edges=4,seq_edge_gate_um=405,pin_edges=2,pin_gate_um=150,path_total_capacity_um=cap,deficit_um=sep-cap,shared_existing_terminal='u_rrl_101.q',native_points=xy,meaning='Even freely movable zero-area FF points cannot satisfy this unchanged source graph and both existing pins. Real footprint/clock restrictions cannot repair infeasibility. All original reset connections/count/depth/root/cycles preserved.')
(R/'exact_constraint_cut.json').write_text(json.dumps(out,indent=2))
fig,ax=plt.subplots(2,1,figsize=(15,9),gridspec_kw={'height_ratios':[2,1]})
x=[a[0]]+[xy[n][0] for n in names]+[b[0]];y=[a[1]]+[xy[n][1] for n in names]+[b[1]]
ax[0].plot(x,y,'o-',color='#bc3d37',lw=2);ax[0].set(xlim=(0,1930),ylim=(-25,860),aspect='equal',xlabel='x (um)',ylabel='y (um)',title='Existing source graph: shared reset terminal fork; all connections retained')
labels=['HBM reset pin','HBM bout.eq','HBM ist3.eq','rrl101.q','CTL ist0.eq','CTL bout.eq','CTL pin144']
for xx,yy,s in zip(x,y,labels):ax[0].annotate(s,(xx,yy),xytext=(5,7),textcoords='offset points',fontsize=9)
u1=sum(a);u2=sum(b);radius=2*405+150
for k,(u,c,l) in enumerate([(u1,'#3979ad','HBM-side allowed u of rrl101'),(u2,'#cf763d','CTL-side allowed u of rrl101')]):
 ax[1].plot([u-radius,u+radius],[k,k],color=c,lw=12,solid_capstyle='butt');ax[1].plot(u,k,'k|',ms=20);ax[1].text(u-radius,k+.18,l,fontsize=10)
ax[1].annotate('',xy=(u1+radius,.5),xytext=(u2-radius,.5),arrowprops={'arrowstyle':'<->','color':'#bc3d37','lw':2});ax[1].text((u1+u2)/2,.58,f'No overlap: {sep-cap:.3f} um gap',ha='center',color='#bc3d37')
ax[1].set(ylim=(-.4,1.5),yticks=[],xlabel='u = x+y (um)',title=f'Fixed pin separation {sep:.3f} > unchanged path capacity {cap:.3f} um')
fig.suptitle('Hroot source-preserving reset relocation: INFEASIBLE before clock or footprint constraints\nNo repoint, new FF, added cycle, root move or gate relaxation; actual reset graph unchanged',fontsize=13)
fig.tight_layout(rect=(0,0,1,.93));fig.savefig(R/'source_preserving_cut.png',dpi=150)
