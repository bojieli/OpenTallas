from pathlib import Path
import json,sys
from types import SimpleNamespace
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan')
import schema as S,gen_phys as GP,placement_obstacles as PO
PTH=Path(__file__).parent;j=json.load(open(PTH/'clock_context.json'));tn='col_h9_r0_p2__t1__cl9f71e63d';t=j['type'];P=SimpleNamespace(types={tn:t},layers={l['name']:l for l in S.ASAP7_LAYERS},layer_budget=j['die']['layer_budget']);old=(298.592,596.128);taken=[(x,y)for n,x,y in j['taps']]+[(x,y)for n,x,y,tp in j['core_taps']if n!='clk_c2'];new=S.tap_clear(t,*old,taken=taken,strict=True,pin_snap=lambda x,y:GP._snap_tap(P,x,y),legal_axes=GP.clock_legal_axes(P,tn));boxes=PO.placement_boxes(t,halo=S.TAP_CLEAR_UM);hit=lambda p:[k for k,b in boxes.items()if b[0]+1e-8<p[0]<b[2]-1e-8 and b[1]+1e-8<p[1]<b[3]-1e-8];pin=(274.680,604.854)
report=dict(scope='DISABLED source-only historical-context PREP; rederive against fresh coherent S39 and actual selected child view',type=tn,tap='clk_c2',logical_core='u_r0.u_e2',actual_instance='u_bound.u_u_r0_u_e2',actual_pin='clk',old_consumed_xy=old,new_consumed_xy=new,L1move_um=sum(abs(a-b)for a,b in zip(old,new)),canonical_halo_um=S.TAP_CLEAR_UM,all_canonical_obstacles=len(boxes),new_halo_hits=hit(new),old_halo_hits=hit(old),outline=t['outline_um'],PG_clear=[dict(layer=ln,phase_um=phase,blocked=S.pg_blocked(ln,v-phase))for ln,v in zip(('M7','M6'),new)for phase in(0.,GP.CORE_MARGIN_UM)],native_staged_clock_rect={'layer':'M5','rect_um':[231.36,0,231.384,.084],'macro_origin_um':[43.308,604.812],'absolute_center_um':pin,'warning':'historical child view clock shape24x84nm is not current M5 clock-entry qualification'},direct_core_clock_hop_um=sum(abs(a-b)for a,b in zip(new,pin)),grid_source_clock_changes=0,reset_graph_changes=0,RTL_changes=0,FF_changes=0,cycles_changes=0,reason='CP2 early core-only physical entry. clk_c2 top port is not passed into bound RTL; core adapter installs delivered clock after synth. No source-grid tap or native reset dependency changes.',remaining=['regenerate all76 physical identities and resolve exact actualclk pin; historical core_taps.txt uses nonexistent ck','rederive same candidate against exact new S39 macro views/obstacles/pins before adoption','no actual placement/CTS/TTFF/source qualification from this static PREP'])
assert not report['new_halo_hits'];assert not any(q['blocked']for q in report['PG_clear']);assert report['direct_core_clock_hop_um']<405
(PTH/'clock_candidate.json').write_text(json.dumps(report,indent=2)+'\n')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,(ax,z)=plt.subplots(1,2,figsize=(13,7))
for a in(ax,z):
 for n,b in PO.placement_boxes(t).items():
  a.add_patch(Rectangle(b[:2],b[2]-b[0],b[3]-b[1],fc='#d5b889',ec='#775c36',lw=.3))
 for n,b in boxes.items():
  a.add_patch(Rectangle(b[:2],b[2]-b[0],b[3]-b[1],fill=False,ec='#d89089',lw=.25))
 a.plot(*old,'rx',ms=9,label='old clk_c2 body collision');a.plot(*new,'go',ms=5,label='proposed same-name entry');a.plot(*pin,'b*',ms=8,label='historical child clk pin; dashed=L1 metric only');a.plot([new[0],new[0],pin[0]],[new[1],pin[1],pin[1]],'b--',lw=1)
 a.set_aspect('equal');a.set_xlabel('um');a.set_ylabel('um')
ax.set_xlim(0,1442.88);ax.set_ylim(0,1226.88);ax.set_title('Exact failed historical physical context');z.set_xlim(245,360);z.set_ylim(535,630);z.set_title('Nearest canonical 8.64um-halo / PG-safe track\n34.560um entry move; actual clock-pin hop67.198um');z.legend(fontsize=7)
fig.suptitle('DISABLED col clk_c2 PREP — existing-name geometry only / zero RTL, FF, reset, or cycle changes\nHistorical child view is not current clock-entry qualification. Fresh coherent source event + LOOK required.',fontsize=11);fig.tight_layout();fig.savefig(PTH/'clock_candidate_LOOK.png',dpi=160)
print(json.dumps({k:report[k]for k in('new_consumed_xy','L1move_um','all_canonical_obstacles','direct_core_clock_hop_um','new_halo_hits')}))
