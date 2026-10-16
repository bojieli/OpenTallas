#!/usr/bin/env python3
"""Source-exact adjacent calendar pin proposal from an actual link DEF packet.

This assigns no die home and claims no slot/route/timing qualification. The die
lead must collision-check the translated R0 frames and preserve zero extra
relay edges on all control bits and on epoch_go before using EP_SKEW unchanged.
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from qwen_split.source_pin_plan import rtl_ports
SOURCE='rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_seq_dies.sv'
TOP='qkd_d2d_cal_seq'
LINK_SOURCE='rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv'
CONTROL=('cfg_tx_we','cfg_rx_we','cfg_addr','cfg_data','cal_start','cal_seg')


def propose(packet):
    ports=rtl_ports(ROOT/SOURCE,TOP)
    linkports=rtl_ports(ROOT/LINK_SOURCE,'qkd_d2d_static')
    for p in CONTROL:
        if linkports.get(p)!=(ports[p][0],'input'):
            raise ValueError(f'actual link source has incompatible control port {p}')
    if any(linkports.get(p)!=(1,'output') for p in ('fwd_epoch','epoch_abort')):
        raise ValueError('actual link source epoch/abort ABI changed')
    bits=[p if ports[p][0]==1 else f'{p}[{i}]' for p in CONTROL for i in range(ports[p][0])]
    if len(bits)!=42 or any(ports[p][1]!='output' for p in CONTROL):
        raise ValueError('actual sequencer source control ABI changed')
    names=bits+['fwd_epoch','epoch_abort']
    pp=packet['pins']
    if packet['master']!='qkd_d2d_static' or any(p not in pp for p in names):
        raise ValueError('actual link packet must contain all42 control bits and both return pins')
    w,h=packet['outline_um']; gap=21.6; size=43.2
    if any(pp[n]['layer']!='M4' or abs(pp[n]['center_um'][0]-w)>.2 for n in names):
        raise ValueError('proposal requires actual east-facing M4 link pins')
    low=min(pp[n]['center_um'][1] for n in names)
    high=max(pp[n]['center_um'][1] for n in names)
    yoff=round(round(((low+high-size)/2)/2.16)*2.16,6)
    if not 1.0<=low-yoff<=high-yoff<=size-1.0:
        raise ValueError('actual pin span needs a taller sequencer slot')
    # The actual captured geometry is a baseline, not a closure claim.
    # New sequencer pins use >=3 M4 tracks even
    # when the old link's control cluster uses2; monotone local spreading
    # costs <1um of wire, never an extra scheduled edge.
    target_y={n:round(pp[n]['center_um'][1]-yoff,6) for n in names}
    ordered=sorted(names,key=lambda n:target_y[n]);clusters=[]
    for n in ordered:
        if clusters and target_y[n]-target_y[clusters[-1][-1]]<.144-1e-6:
            clusters[-1].append(n)
        else:clusters.append([n])
    for ns in clusters:
        mid=(target_y[ns[0]]+target_y[ns[-1]])/2
        first=.012+round((mid-.144*(len(ns)-1)/2-.012)/.048)*.048
        for i,n in enumerate(ns):target_y[n]=round(first+.144*i,6)
    pinlist=[]; edges=[]
    for n in names:
        sn={'fwd_epoch':'epoch_go','epoch_abort':'halt'}.get(n,n)
        y=target_y[n]
        if abs((y-.012)/.048-round((y-.012)/.048))>1e-6:
            raise ValueError(f'actual {n} cannot mirror on the sequencer M4 track lattice')
        pinlist.append(dict(name=sn,layer='M4',face='W',center_um=[.072,y],size_um=[.144,.024]))
        delta=[round(w+gap+.072-pp[n]['center_um'][0],6),round(y+yoff-pp[n]['center_um'][1],6)]
        edges.append(dict(link_pin=n,seq_pin=sn,control_bit=bits.index(n) if n in bits else None,
                          direction='seq_to_link' if n in bits else 'link_to_seq',
                          delta_um=delta,manhattan_um=round(abs(delta[0])+abs(delta[1]),6),extra_relay_edges=0))
    for n,x in (('ck',21.612),('rst_n',23.772),('reload',10.812),('tok_go',30.252)):
        if n in ports:
            pinlist.append(dict(name=n,layer='M5',face='S',center_um=[x,.072],size_um=[.024,.144]))
    status=['cal_ready','running']+[f'layer[{i}]' for i in range(6)]+['adm_done','tok_start','fault']
    for i,n in enumerate(status):
        pinlist.append(dict(name=n,layer='M4',face='E',center_um=[size-.072,round(4.332+1.728*i,6)],size_um=[.144,.024]))
    actual={p if n==1 else f'{p}[{i}]' for p,(n,d) in ports.items() for i in range(n)}
    if {p['name'] for p in pinlist}!=actual or len(pinlist)!=len(actual):
        raise ValueError('pin proposal is not a one-to-one cover of the actual source ABI')
    # kv_die face ports are regular-pitch groups. The real link's cfg_data
    # face has a deliberate gap after bit19, so expose TWO physical aliases
    # rather than one falsely contiguous 32-bit group. Bind base first, then hi.
    dieports={p:[p] for p in ports if p!='cfg_data'}
    dieports['cfg_data_lo']=['cfg_data']
    groups={p:([p] if n==1 else [f'{p}[{i}]' for i in range(n)])
            for p,(n,d) in ports.items() if p!='cfg_data'}
    groups['cfg_data_lo']=[f'cfg_data[{i}]' for i in range(20)]
    groups['cfg_data_hi']=[f'cfg_data[{i}]' for i in range(20,32)]
    pinby={p['name']:p for p in pinlist}; faces={}
    for port,ns in groups.items():
        ps=[pinby[n] for n in ns];face=ps[0]['face'];layer=ps[0]['layer'];axis=1 if face in 'WE' else 0
        ys=[p['center_um'][axis] for p in ps]
        step=round(ys[1]-ys[0],6) if len(ys)>1 else .096
        if any(abs(y-(ys[0]+i*step))>1e-6 for i,y in enumerate(ys)):
            raise ValueError(f'{port}: cannot represent as one regular physical face group')
        faces[port]=['face',len(ns),face,layer,round(ys[0]+len(ns)*step/2,6),round(step/.048)]
    return dict(scope='PROPOSED_DIE_DRIVEN_PINS_AND_SOURCE_MAP_ONLY',top=TOP,source=SOURCE,
                source_sha256=hashlib.sha256((ROOT/SOURCE).read_bytes()).hexdigest(),
                link_interface_source=LINK_SOURCE,link_interface_sha256=hashlib.sha256((ROOT/LINK_SOURCE).read_bytes()).hexdigest(),
                link_packet=packet,outline_um=[size,size],orient='R0',
                relative_to_link_R0_origin_um=[w+gap,yoff],link_gap_um=gap,
                link_matched_pin_span_um=[low,high],new_face_min_pitch_um=.144,pins=pinlist,edges=edges,
                control_bundle_lsb_first=bits,
                binding_template=dict(module=TOP,file=SOURCE,ports=dieports,sliced={'cfg_data_hi':'cfg_data_lo'},classed={}),
                required_binding_parameters=['EP_SKEW'],die_master_face_ports=faces,
                face_model_note='Regular-pitch kv_die frame groups; cfg_data split20/12 preserves the actual gap. Requested Tcl pin shapes are authoritative before actual routed readback.',
                compiler=dict(extra_control_relay_edges=0,extra_epoch_relay_edges=0,
                              EP_SKEW='package_epoch_edges - extra_epoch_relay_edges - extra_control_relay_edges',
                              no_implicit_package_skew=True,local_epoch_capture_edges=(1 if TOP.endswith('_pin') else 0),
                              local_compensation='EP_SKEW-1 internally' if TOP.endswith('_pin') else 'raw source'),
                by_design_connections=({'u_seq.tok_go':'constant0; raw AUTO=1 ignores this input; no physical port'} if TOP.endswith('_pin') else {}),
                remaining=['die lead actual home/collision/all-incident-port assignment','clock phase-minus-insertion and pair reach TT/FF',
                           'sequencer source synthesis/CTS/route/native audit','route final DEF readback and exact matched-pin proof',
                           'HOST reload/rst/status/fault producer-consumer wiring','physical package_epoch_edges'],
                physical_qualified=False,strict_die_bind_closed=False)


def draw(r,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,axes=plt.subplots(1,3,figsize=(18,6),gridspec_kw={'width_ratios':[2,1,1]})
    lw,lh=r['link_packet']['outline_um'];sx,sy=r['relative_to_link_R0_origin_um'];sw,sh=r['outline_um']
    by={p['name']:p for p in r['pins']}
    for ax in axes[:2]:
        ax.add_patch(Rectangle((0,0),lw,lh,facecolor='#b9cfea',edgecolor='black'))
        ax.add_patch(Rectangle((sx,sy),sw,sh,facecolor='#b9dfb4',edgecolor='black'))
        for e in r['edges']:
            x,y=r['link_packet']['pins'][e['link_pin']]['center_um']
            q=by[e['seq_pin']]['center_um']
            ax.plot([x,sx+q[0]],[y,sy+q[1]],color='#265a98' if e['control_bit'] is not None else '#b44728',lw=.7)
        ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um');ax.grid(alpha=.15)
    axes[0].text(lw/2,lh/2,'qkd_d2d_static\nactual routed DEF footprint',ha='center',va='center')
    axes[0].text(sx+sw/2,sy+sh+8,'proposed cal seq\n43.2 x 43.2',ha='center',va='bottom',fontsize=8)
    axes[0].set_xlim(-10,sx+sw+10);axes[0].set_ylim(-10,lh+10)
    axes[0].set_title('R0 relative frames; die home not assigned')
    axes[1].set_xlim(lw-5,sx+8);axes[1].set_ylim(147,174)
    axes[1].set_title(f'42 control + 2 epoch/abort requested paths\n{max(e["manhattan_um"] for e in r["edges"]):.3f} um worst requested hop',fontsize=10)
    axes[1].text((lw+sx)/2,148,'21.6 um gap',ha='center',fontsize=8)
    ax=axes[2]
    ax.add_patch(Rectangle((0,0),sw,sh,facecolor='#edf5ea',edgecolor='black'))
    for p in r['pins']:
        x,y=p['center_um']
        ax.plot(x,y,'o',ms=2.5,color='red' if p['name']=='ck' else '#265a98')
        if p['face']=='E':ax.text(x+1,y,p['name'],fontsize=6,va='center')
    for n,textxy in [('ck',(15,-7)),('rst_n',(31,-10)),('reload',(4,-7))]:
        p=by[n]
        ax.annotate(n,xy=p['center_um'],xytext=textxy,fontsize=8,ha='center',arrowprops={'arrowstyle':'->','lw':.7})
    for n,ty in [('epoch_go',29.5),('halt',25.5)]:
        ax.annotate(n,xy=by[n]['center_um'],xytext=(-6,ty),fontsize=7,ha='right',arrowprops={'arrowstyle':'->','lw':.6})
    ax.text(-2,13,'cfg/cal\n3 tracks',fontsize=7,ha='right',va='center')
    ax.text(-2,32,'cfg\n3 tracks',fontsize=7,ha='right',va='center')
    ax.set_xlim(-15,sw+22);ax.set_ylim(-12,sh+3);ax.set_aspect('equal');ax.grid(alpha=.15)
    ax.set_title(f'Sequencer source pin assignment ({len(r["pins"])} bits)\ncentred ck; AUTO tok_go internal0',fontsize=10)
    ax.set_xlabel('local um');ax.set_ylabel('local um')
    fig.suptitle('Source-exact calendar pin proposal: geometry only; clock/STA/route OPEN',fontsize=12)
    fig.tight_layout();fig.savefig(out/'pin_proposal.png',dpi=160);plt.close(fig)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('packet',type=Path);ap.add_argument('out',type=Path)
    ap.add_argument('--consumer-e-packet',type=Path,help='all actual Eface pins; propose a coherent monotone3track repair of the unclosed consumer')
    ap.add_argument('--pin-capture',action='store_true',help='actual captured-input successor; raw source stays historical')
    a=ap.parse_args()
    global SOURCE,TOP
    if a.pin_capture:
        SOURCE='rtl/qwen_sys/d2d_static_20261015/qkd_d2d_cal_seq_pin.sv';TOP='qkd_d2d_cal_seq_pin'
    original=json.loads(a.packet.read_text());packet=original
    full=None;target=None
    if a.consumer_e_packet:
        full=json.loads(a.consumer_e_packet.read_text())
        if full['source_def_sha256']!=original['source_def_sha256'] or full['outline_um']!=original['outline_um']:
            raise ValueError('consumer packet provenance/outline does not match actual link44 packet')
        if any(full['pins'].get(n)!=p and full['pins'][n]['center_um']!=p['center_um'] for n,p in original['pins'].items()):
            raise ValueError('actual consumer pin coordinates disagree between packets')
        target={};last=-1
        for n,p in sorted(full['pins'].items(),key=lambda np:np[1]['center_um'][1]):
            if p['layer']!='M4' or n in ('VDD','VSS'):
                raise ValueError('consumer Eface packet includes a nonfunctional/nonM4 pin')
            y=max(p['center_um'][1],last+.144)
            y=round(.012+round((y-.012)/.048)*.048,6);last=y
            q=copy.deepcopy(p);dy=y-p['center_um'][1]
            q['center_um'][1]=y;q['rect_um'][1]=round(q['rect_um'][1]+dy,6);q['rect_um'][3]=round(q['rect_um'][3]+dy,6)
            q['requested_shift_y_um']=round(dy,6);target[n]=q
        if last>=full['outline_um'][1]-1:
            raise ValueError('consumer3track pins do not fit original outline')
        ys=sorted(p['center_um'][1] for p in target.values())
        if min(b-a for a,b in zip(ys,ys[1:]))<.144-1e-6:
            raise ValueError('consumer3track repair retains a local pin collision')
        packet=copy.deepcopy(original)
        packet['scope']='REQUESTED consumer successor pin coordinates; NOT actual routed pins. Immutable original packet retained separately.'
        packet['basis_source_def_sha256']=packet.pop('source_def_sha256')
        packet['basis_source_commit']=packet.pop('source_commit')
        packet['pins']={n:target[n] for n in original['pins']}
    r=propose(packet);a.out.mkdir(parents=True,exist_ok=True)
    if full:
        r['actual_link_pin_packet']=original
        r['consumer_e_packet_sha256']=hashlib.sha256(a.consumer_e_packet.read_bytes()).hexdigest()
        r['consumer_target']=dict(scope='REQUESTED_ALL_EFACE_SUCCESSOR_PINS_ONLY',pins=target,
             count=len(target),minimum_center_pitch_um=.144,minimum_edge_spacing_um=.120,
             all_pairs_same_layer_overlap=0,max_shift_y_um=max(p['requested_shift_y_um'] for p in target.values()),
             source_def_sha256=full['source_def_sha256'],source_commit=full['source_commit'],
             source_order_preserved=True,footprint_changed=False,physical_qualified=False)
        lines=['# REQUESTED all-Eface3track pin successor; NOT an actual routed view.',
               '# Basis actual DEF sha256 '+full['source_def_sha256']]
        for n,p in target.items():
            x,y=p['center_um'];x0,y0,x1,y1=p['rect_um']
            lines.append(f'place_pin -pin_name {{{n}}} -layer M4 -location {{{x:.6f} {y:.6f}}} -pin_size {{{x1-x0:.6f} {y1-y0:.6f}}}')
        (a.out/'qkd_d2d_static_e_3track.tcl').write_text('\n'.join(lines)+'\n')
    r['packet_sha256']=hashlib.sha256(a.packet.read_bytes()).hexdigest()
    (a.out/'plan.json').write_text(json.dumps(r,indent=2)+'\n')
    lines=['# PROPOSED die-driven calendar pins; actual link DEF packet sha256 '+r['packet_sha256'],
           '# 43.2 x 43.2; R0 source ABI only, no home/clock/route qualification.']
    for p in r['pins']:
        x,y=p['center_um'];w,h=p['size_um']
        lines.append(f'place_pin -pin_name {{{p["name"]}}} -layer {p["layer"]} -location {{{x:.6f} {y:.6f}}} -pin_size {{{w:.6f} {h:.6f}}}')
    (a.out/'qkd_d2d_cal_seq.tcl').write_text('\n'.join(lines)+'\n')
    draw(r,a.out)
    print(json.dumps(dict(pins=len(r['pins']),control_bits=42,relative_home=r['relative_to_link_R0_origin_um'],
                         max_matched_hop_um=max(e['manhattan_um'] for e in r['edges']),qualified=False)))


if __name__=='__main__':main()
