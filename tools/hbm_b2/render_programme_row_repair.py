"""Inspect the disabled same-netlist programme row/pin repair before CAD."""
import argparse
import csv
import json
import hashlib
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


def main():
    p=argparse.ArgumentParser();p.add_argument('candidate',type=Path);a=p.parse_args();d=a.candidate
    m=json.loads((d/'model.json').read_text());rows=list(csv.DictReader((d/'actual_FF_rows.csv').open()))
    pinpath=d/'native_pins_clock_entry.json'
    if not pinpath.exists():pinpath=d/'native_pins.json'
    pins=json.loads(pinpath.read_text());adjpath=d/'adjacent_all_orientations/adjacent_model.json'
    if not adjpath.exists():adjpath=d/'adjacent/adjacent_model.json'
    adj=json.loads(adjpath.read_text())
    ingpath=d/'ingress_central_reset/ingress_first_capture.json'
    if not ingpath.exists():ingpath=d/'ingress/ingress_first_capture.json'
    ing=json.loads(ingpath.read_text());W,H=m['outline_um']
    seen=set();viol=[]
    for r in rows:
        x,y=float(r['x_um']),float(r['y_um']);box=[x-.54,y-.135,x+.54,y+.135]
        ix,iy=round(box[0]/2.16),round(box[1]/.27)
        assert abs(box[0]-ix*2.16)<1e-6 and abs(box[1]-iy*.27)<1e-6
        assert (ix,iy) not in seen;seen.add((ix,iy))
        if not(4.32<=box[0] and 4.32<=box[1] and box[2]<=W-4.32 and box[3]<=H-4.32):viol.append([r['cell'],'frame'])
        for q in m['macros']:
            u,v,U,V=q['rect_um'];u-=4.32;v-=4.32;U+=4.32;V+=4.32
            if box[0]<U-1e-8 and box[2]>u+1e-8 and box[1]<V-1e-8 and box[3]>v+1e-8:viol.append([r['cell'],q['name']])
    if viol:
        (d/'FAIL_native_rows.json').write_text(json.dumps(dict(status='FAIL_ACTUAL_MACRO_HALO_ROWS',violations=viol),indent=2)+'\n')
    assert len(rows)==20842 and len(pins)==2904 and not viol,viol[:10]
    occupied=set();shapes=[]
    for q in pins:
        key=(q['layer'],q['x'],q['y']);assert key not in occupied;occupied.add(key)
        assert 0<=q['x']<=W and 0<=q['y']<=H
        if q['layer']=='M4':
            assert abs((q['y']-.024)/.048-round((q['y']-.024)/.048))<1e-6
            assert q['face']in ('W','E')
            # Exact normal backend io_tcl M4 width .024, inward length .192.
            x0,x1=(0,.192)if q['face']=='W'else(W-.192,W)
            shape=[x0,q['y']-.012,x1,q['y']+.012]
        else:
            assert q['layer']=='M5'and q.get('w')==.048 and q.get('h')==.48
            shape=[q['x']-.024,q['y']-.24,q['x']+.024,q['y']+.24]
        assert 0<=shape[0]and shape[2]<=W and 0<=shape[1]and shape[3]<=H
        for layer,other in shapes:
            if layer!=q['layer']:continue
            assert not(shape[0]<other[2]-1e-8 and other[0]<shape[2]-1e-8 and shape[1]<other[3]-1e-8 and other[1]<shape[3]-1e-8)
        shapes.append((q['layer'],shape))
    rowmap={r['cell']:r for r in rows};masters=ing['FF_native_pin_masters'];output_upper=0.;input_upper=0.
    for q in ing['rows']:
        x,y=q['planned_GEN_input_pin_um']
        for sink in q['first_sequential_sinks']:
            for u,v,U,V in sink.get('native_pin_rects_R0_MX_um',[]):
                input_upper=max(input_upper,*(abs(x-X)+abs(y-Y)for X,Y in [(u,v),(u,V),(U,v),(U,V)]))
    for r in rows:
        if not r['planned_output_pin_x_um']:continue
        x,y=float(r['x_um']),float(r['y_um']);px,py=float(r['planned_output_pin_x_um']),float(r['planned_output_pin_y_um'])
        master=masters[r['master']]
        for u,v,U,V in master['pins']['QN']:
            for X,Y in [(u,v),(u,V),(U,v),(U,V)]:
                output_upper=max(output_upper,abs(x-master['w']/2+X-px)+abs(y-master['h']/2+Y-py),
                                  abs(x-master['w']/2+X-px)+abs(y+master['h']/2-Y-py))
    assert input_upper<=405 and output_upper<=405
    checks=dict(status='NECESSARY_NATIVE_ROW_AND_PIN_GEOMETRY_ONLY',actual_FF=20842,native_masters=1,
        inputs_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest()for f in [d/'model.json',d/'actual_FF_rows.csv',pinpath,adjpath,ingpath]},
        native_footprint_um=[1.08,.27],unique_native_lower_left_sites=len(seen),macro_halo_violations=len(viol),
        row_grid_um=[2.16,.27],ABI=2904,pin_names_unique=len({q['name']for q in pins}),pin_track_or_outline_violations=0,
        native_pin_rectangles=2904,same_layer_signal_rectangle_overlaps=0,
        M4_data_pin_shape_um=[.192,.024],M5_clock_reset_shape_um=[.048,.48],
        adjacent_edges=adj['edge_classes'],first_input_bits=621,first_input_failures=ing['bits_exceed405'],
        first_input_max_all_R0_MX_native_pin_corners_um=input_upper,output_capture_bits=2282,
        output_capture_max_all_R0_MX_native_pin_corners_um=output_upper,
        extra1088_rows='Conservative reservation only; not actual cells or clock sinks',
        parent_unplaced_obligations='Existing9538 distinct wrapper capture FF plus new2304 upstream FF are outside this native core; no parent row/clock credit',
        held=['No PLACE/CTS/route/STA','Actual native orientation/clock/reset/START/pin access and parent source-event integration required'])
    (d/'row_pin_gate.json').write_text(json.dumps(checks,indent=2)+'\n')
    fig,ax=plt.subplots(figsize=(12,12))
    for q in m['macros']:
        x,y,X,Y=q['rect_um'];ax.add_patch(Rectangle((x-4.32,y-4.32),X-x+8.64,Y-y+8.64,facecolor='#f7dddd',edgecolor='none'))
        ax.add_patch(Rectangle((x,y),X-x,Y-y,facecolor='#d0d7de',edgecolor='#49525c',lw=.5))
        ax.text((x+X)/2,(y+Y)/2,f"leaf{q['leaf']}",ha='center',va='center',fontsize=6,color='#49525c')
    groups={'Native leaf FF':([],[],'#397ac7'),'Native control/relay FF':([],[],'#d47b28'),'Native output captures':([],[],'#218550')}
    for r in rows:
        group='Native output captures'if r['planned_output_pin_x_um']else'Native control/relay FF'if r['ownership']=='top_other'else'Native leaf FF'
        groups[group][0].append(float(r['x_um']));groups[group][1].append(float(r['y_um']))
    for label,(xs,ys,col)in groups.items():ax.scatter(xs,ys,s=.7,color=col,label=f'{label}: {len(xs):,}',rasterized=True)
    for face,col in [('W','#a13870'),('E','#146e80')]:
        pp=[q for q in pins if q.get('face')==face];ax.scatter([q['x']for q in pp],[q['y']for q in pp],s=2,color=col)
    clock=[q for q in pins if q['name']=='clk'][0]
    ax.scatter([clock['x']],[clock['y']],s=30,c='#a82323',marker='+',zorder=5)
    ax.annotate('Planned M5 clock/reset entry\n(full shapes clear macro+4.32/PG)',(clock['x'],clock['y']),
                xytext=(420,400),fontsize=7,arrowprops=dict(arrowstyle='->',lw=.7),ha='center')
    ax.set(xlim=(-15,W+15),ylim=(-15,H+15),aspect='equal',xlabel='Native core X (um)',ylabel='Native core Y (um)')
    ax.set_title('Disabled programme row/pin repair — same actual0525 post-SYNTH source\n20,842 actual FF + 44 SRAM; no new state or latency; geometry only',fontsize=12)
    ax.legend(loc='upper left',fontsize=8);ax.grid(alpha=.15)
    bad=sum(q['bad']for q in adj['edge_classes'].values())
    fig.text(.5,.025,f"Adjacent first-sequential edges: {bad} over405 um; inputs: {ing['bits_exceed405']}/621 over405 um\nNo timing/clock/START/source-event/parent adoption or PLACE release inferred",ha='center',fontsize=10)
    fig.tight_layout(rect=[0,.06,1,1]);fig.savefig(d/'programme_repaired_native_rows.png',dpi=150)
    print(checks['status'],'row/macro violations',len(viol),'adjacent failures',bad,flush=True)


if __name__=='__main__':main()
