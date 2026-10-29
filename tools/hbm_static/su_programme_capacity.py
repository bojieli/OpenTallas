#!/usr/bin/env python3
"""Census actual two-part programme images against explicit producer capacities."""
import argparse,json,math,tempfile
from pathlib import Path
from su_programme_compile import lower_root5
DEFAULT=[3,10,9,13,2,1,1,1,1,1]
def census(root):
    records=[]
    for image in sorted(root.rglob('native_prog.mem')):
        words=[int(x,16) for x in image.read_text().split()]
        rec=dict(image=str(image.relative_to(root)),edges=len(words))
        caps=[[max(1,math.ceil(len({(w>>(q*2470+c*256))&((1<<min(256,2470-c*256))-1) for w in words})/128)) for c in range(10)] for q in range(2)]
        rec['needed_caps']=caps
        rec['default_declared_capacity_excess']=[dict(part=q,column=c,needed=caps[q][c],available=DEFAULT[c]) for q in range(2) for c in range(10) if caps[q][c]>DEFAULT[c]]
        try:
            with tempfile.TemporaryDirectory(prefix='su-capacity-') as tmp:
                man=lower_root5(image,Path(tmp),parts=2,line_bits=4940,resident_edges=7111)
                assert man['dictionary_caps_per_quarter']==caps
                rec['lowering']='PASS'
        except Exception as exc:
            rec['lowering']='FAIL';rec['reason']=str(exc) or type(exc).__name__
        rec['default_physical_capacity_excess']=[dict(part=q,column=c,needed=caps[q][c],available=(3 if DEFAULT[c]<=3 else 13)) for q in range(2) for c in range(10) if caps[q][c]>(3 if DEFAULT[c]<=3 else 13)]
        rec['installable_default']=len(words)<=7111 and not rec['default_physical_capacity_excess'] and rec['lowering']=='PASS'
        records.append(rec)
    profiles={}
    for rec in records:
        profile='/'.join(rec['image'].split('/')[:2])
        p=profiles.setdefault(profile,dict(records=0,max_edges=0,max_caps=[0]*10,default_fits=True))
        p['records']+=1;p['max_edges']=max(p['max_edges'],rec['edges']);p['default_fits'] &= rec['installable_default']
        p['max_caps']=[max(p['max_caps'][c],*(x[c] for x in rec['needed_caps'])) for c in range(10)]
    aggregate=[max(r['needed_caps'][q][c] for r in records for q in range(2)) for c in range(10)]
    return dict(candidate_caps=aggregate,candidate_classes=['S' if x<=3 else 'L' for x in aggregate],candidate_instantiations='ot_hbm_su_programme_pslice_c5 #(.SB(2470),.NC(10),.DICT_CAP({'+','.join("32'd"+str(x) for x in reversed(aggregate))+'})) pgp_NW/pgp_NE',schema='opentallas.su_programme.capacity.v1',parts=2,slice_bits=2470,resident_edges=7111,actual_default_caps=DEFAULT,profiles=profiles,records=records,physical_adoption=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('out',type=Path);p.add_argument('--candidate-wrapper',type=Path);a=p.parse_args()
    result=census(a.root);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['profiles'],indent=2))

    if a.candidate_wrapper:
        caps=result['candidate_caps']
        if not caps or max(caps)>13 or any(r['edges']>7111 or r['lowering']!='PASS' for r in result['records']):
            raise SystemExit('candidate capacity exceeds existing S/L masters or resident EDGES; hold installation')
        literal="{"+",".join("32'd"+str(x) for x in reversed(caps))+"}"
        a.candidate_wrapper.write_text("// Explicit candidate profile only; requires new physical qualification. Original master unchanged.\n"
            "module ot_hbm_su_programme_pslice_c5_2q_candidate (\n"
            " input logic clk,rst_n,cfg_we,input logic [15:0] cfg_bank,input logic [6:0] cfg_row,\n"
            " input logic [255:0] cfg_data,input logic start,input logic [15:0] length,\n"
            " output logic busy,valid,done,fault,output logic [15:0] edge_index,output logic [2469:0] command);\n"
            " ot_hbm_su_programme_pslice_c5 #(.SB(2470),.NC(10),.DICT_CAP("+literal+")) u_c5 (.*);\nendmodule\n")
