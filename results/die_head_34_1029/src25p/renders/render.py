import json,sys
sys.path[:0]=["tools/die_plan"]
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
B="/srv/opentallas-scratch2/claude/die-head-34/"
raw=json.load(open(B+"src25p_m864/source_plan.json")); R=json.load(open(B+"src25p_m864/src25p_report.json"))["types"]
for tn in ["hd_tile","hd_spn_wshim_rx","hd_turn_b","hd_spn_eshim_rx"]:
    t=raw["partition_types"][tn]; rep=R[tn]
    bins=json.load(open(t["clock"]["sink_bins_file"]))["bins"]
    w,h=t["outline_um"]; fig,ax=plt.subplots(figsize=(9,9))
    ax.add_patch(plt.Rectangle((0,0),w,h,fill=False))
    for hc in t.get("hard_cores",[]):
        ox,oy=hc["origin_um"]; dx,dy=hc.get("track_offset_um",[0,0]); cw,ch=hc["outline_um"]
        ax.add_patch(plt.Rectangle((ox+dx,oy+dy),cw,ch,color="0.8")); ax.text(ox+dx+5,oy+dy+5,hc["inst"].split(".")[-1],fontsize=7)
    ax.scatter([b[0] for b in bins],[b[1] for b in bins],s=[max(1,b[2]/3) for b in bins],c="tab:blue",alpha=.5)
    for n,x,y,s in rep["taps"]:
        ax.plot(x,y,"r^"); ax.add_patch(plt.Circle((x,y),200,fill=False,ec="r",lw=.3))
    ax.set_xlim(-20,w+20); ax.set_ylim(-20,h+20); ax.set_aspect("equal")
    ax.set_title("%s: %d taps r200, worst sink-tap %.1f um, max load %d" % (tn,len(rep["taps"]),rep["worst_sink_nearest_tap_l1_um"],rep["max_load"]))
    fig.savefig(B+"taps_%s.png"%tn,dpi=80)
