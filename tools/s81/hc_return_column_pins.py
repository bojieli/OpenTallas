#!/usr/bin/env python3
"""Provisional v22 return-column pin assignments, projected from actual neighbor pins.

COLUMN chooses real RTL bit ownership. Unrelated global broadcasts are retained;
projection onto a local face does not claim those external seams meet timing.
"""
import argparse, copy, hashlib, json, sys
from pathlib import Path
import v19_pins_1014 as V
ROOT = Path(__file__).resolve().parents[2]
W = 144.18
PITCH = .096


def pack(ports, h):
    """Bounded ordered packing; reserve pitch before nearest-coordinate projection."""
    groups = {}
    for p, bits in ports.items():
        for i, b in enumerate(bits):
            groups.setdefault(tuple(b[:2]), []).append((b[2], p, i))
    for (face, layer), values in groups.items():
        values.sort()
        length = W if face in 'NS' else h
        assert (len(values)-1)*PITCH < length-.6, (face, layer, len(values), length)
        previous = -.096
        for k, (desired, p, i) in enumerate(values):
            lo = .3 + k*PITCH
            hi = length-.3-(len(values)-1-k)*PITCH
            pos = max(lo, previous+PITCH, min(desired, hi))
            ports[p][i][2] = round(pos, 3)
            previous = pos


def make(kind, column):
    old = json.loads((ROOT / ('physical/s81_die_pins/v20_hc_return/ot_s81_hc_'+kind+'.json')).read_text())
    oldp = old['ports']; ports = {}; bindings = {}
    def take(name, src, indices):
        indices = list(indices)
        ports[name] = [copy.deepcopy(oldp[src]['per_bit'][i]) for i in indices]
        bindings[name] = dict(source_port=src, source_bits=indices)
        for b in ports[name]:
            if b[0] in 'NS': b[2] -= W*column
    for p in ['clk','rst_in','tid','last','fv','fdx','rv_in','yb_n','yb_s']:
        take(p,p,range(oldp[p]['bits']))
    take('rdh_in', 'rd_in' if kind=='ctra' else 'rdh_in', range(108))
    data = []
    for half in range(2):
        for rs in range(2):
            for rc in range(2):
                q = 8*rs+column+4*rc
                if kind=='ctra': start = 108+64*(q if half==0 else max(0,q-2)); src='rd_in'
                else: start = 64*(q+2 if half==0 else q); src='rdd_in'
                data.extend(range(start,start+64))
    take('rdp_in',src,data)
    # For A, shifted q<2 input is a physical constant, not an invented source.
    if kind=='ctra' and column<2:
        bindings['rdp_in']['constant_zero_bits']=list(range(256,320))
    for suffix in ['n','s']:
        take('hrq_'+suffix,'hrq_'+suffix,(128*(column+4*bank)+b for bank in range(2) for b in range(128)))
    if kind=='ctra':
        take('rdm','rdm',(108+512*rs+64*(column+4*chunk)+b for rs in range(2) for chunk in range(2) for b in range(64)))
        take('header_delay','rdm',range(108))
        take('rvm','rvm',range(8))
        for p in ['rq_q','hs_run','hs_c','rq_q_c1','rq_q_c2','rq_q_c3','hs_run_c1','hs_run_c2','hs_run_c3','hs_c_c1','hs_c_c2','hs_c_c3','cs','hov_d']:
            take(p,p,range(oldp[p]['bits']))
        for suffix in ['n','s']:
            take('nflt_'+suffix,'nflt_'+suffix,[column,column+4])
            for p in ['hnz','pflt']: take(p+'_'+suffix,p+'_'+suffix,[column])
        for p,y in [('flag_fault',2.4),('flag_hnz',2.592)]: ports[p]=[['W','M4',y,.192]]
        for p,y in [('peer_fault',3.072),('peer_hnz',3.456)]:
            ports[p]=[['E','M4',y+.096*i,.192] for i in range(3)]
    else:
        take('rdm','rdm',(512*rs+64*(column+4*chunk)+b for rs in range(2) for chunk in range(2) for b in range(64)))
    h = 30.24 if kind=='ctra' else 25.92
    pack(ports,h)
    return ports,bindings,h


def neighbor_audit(out):
    ln=[V.lef_bits('physical/ref_tile/s81hc_ctnl_l%d_ref/views/ot_s81_hc_ctnl_l%d/ot_s81_hc_ctnl_l%d.lef'%(c,c,c))[1] for c in range(4)]
    rn=V.lef_bits('physical/ref_tile/s81hc_ctrn_ref/views/ot_s81_hc_ctrn/ot_s81_hc_ctrn.lef')[1]
    cp=V.lef_bits('physical/ref_tile/s81hc_ctpl_ref/views/ot_s81_hc_ctpl/ot_s81_hc_ctpl.lef')[1]
    heights=[95.04,95.04,99.36,99.36];rows=[12.96,112.32,544.32,643.68];H=771.12
    reports=[]
    def xy(pin,w,h):
        f,ly,c,d=pin
        return {'N':(c,h-.042),'S':(c,.042),'W':(.042,c),'E':(w-.042,c)}[f]
    for kind in ['ctra','ctrb']:
        h=30.24 if kind=='ctra' else 25.92
        y=H-(330.48 if kind=='ctra' else 360.72)-h
        for c in range(4):
            rec=json.loads((out/('c'+str(c))/('ot_s81_hc_'+kind+'_column.json')).read_text());p=rec['ports'];bind=rec['source_bit_binding'];edges=[]
            def edge(port,i,other,ox,oy):
                px,py=xy(p[port]['per_bit'][i],W,h);px+=W*c;py+=y
                edges.append(dict(port=port,bit=i,neighbor=other,length_um=round(abs(px-ox)+abs(py-oy),3),rectangle_lower_bound_um=round(max(W*c-ox,0,ox-W*(c+1))+max(y-oy,0,oy-y-h),3)))
            for suff,bank0 in [('n',0),('s',2)]:
                for i in range(256):
                    bank,bi=divmod(i,128);j=bank0+bank
                    pin=ln[c]['hrq'][bi+(128 if kind=='ctrb' else 0)]
                    edge('hrq_'+suff,i,'ctnl[%d][%d].hrq'%(j,c),144.72*c+pin[2],H-rows[j]-heights[c]+pin[3])
                for i in range(128):
                    col=(i//16)%4;j=bank0+i//64;pin=ln[col]['yb'][i%16]
                    edge('yb_'+suff,i,'ctnl[%d][%d].yb'%(j,col),144.72*col+pin[2],H-rows[j]-heights[col]+pin[3])
                if kind=='ctra':
                    for i in range(2):
                        j=bank0+i;pin=ln[c]['flt'][0];edge('nflt_'+suff,i,'ctnl[%d][%d].flt'%(j,c),144.72*c+pin[2],H-rows[j]-heights[c]+pin[3])
                    for dst,src in [('hnz','hnz_d'),('pflt','pflt_d')]:
                        pin=cp[src][0];edge(dst+'_'+suff,0,'ctpl.'+src,144.72*c+pin[2],H-([211.68,425.52][suff=='s'])-118.8+pin[3])
            for port in ['rdh_in','rdp_in','rdm']+(['header_delay'] if kind=='ctra' else []):
                src=bind[port]['source_port'];const=bind[port].get('constant_zero_bits',[])
                for i,oldbit in enumerate(bind[port]['source_bits']):
                    if i in const or (port=='header_delay' and c!=0):continue
                    if port in ['rdm','header_delay']:
                        rp='rdm';bi=oldbit+(1132 if kind=='ctrb' else 0)
                    else:
                        rp='rd_out';bi=oldbit+(1004 if src=='rdd_in' else 0)
                    pin=rn[rp][bi];edge(port,i,'ctrn.%s[%d]'%(rp,bi),pin[2],H-12.96+pin[3])
            if kind=='ctra' and c==0:
                for col in range(4):
                    suffix='' if col==0 else '_c'+str(col)
                    for port in ['rq_q','hs_run','hs_c']:
                        for i in range(p[port+suffix]['bits']):
                            pin=ln[col][port][i]
                            for j in range(4):edge(port+suffix,i,'ctnl[%d][%d].%s'%(j,col,port),144.72*col+pin[2],H-rows[j]-heights[col]+pin[3])
            reports.append(dict(kind=kind,column=c,rectangle_lower_bound_over500=[x for x in edges if x['rectangle_lower_bound_um']>500],examined=len(edges),max_um=max(x['length_um'] for x in edges),over500=[x for x in edges if x['length_um']>500],hops=edges))
    report=dict(scope='ACTUAL_CLOSED_CTNl_CTRn_CTPL_NEIGHBORS_AT_V22_ORIGINS_ONLY',qualification='GEOMETRY_ONLY_NOT_TIMING; global capture/command/reset and peer flag joins still require explicit parent audit',leaves=reports)
    (out/'neighbor_geometry.json').write_text(json.dumps(report,indent=1)+'\n')
    return [dict(kind=r['kind'],column=r['column'],examined=r['examined'],over500=len(r['over500']),rectangle_lower_bound_over500=len(r['rectangle_lower_bound_over500']),max_um=r['max_um']) for r in reports]


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--rtl',type=Path,required=True);ap.add_argument('--out',type=Path,default=ROOT/'physical/s81_die_pins/v22_hc_return_columns');a=ap.parse_args()
    sys.path.insert(0,str(ROOT/'tools'))
    from die_port_bind import parse_modules
    modules={m.name:m for m in parse_modules(a.rtl.read_text(),str(a.rtl))}
    report=[]
    for kind in ['ctra','ctrb']:
        for c in range(4):
            ports,bindings,h=make(kind,c); out=a.out/('c'+str(c));out.mkdir(parents=True,exist_ok=True)
            master='ot_s81_hc_'+kind+'_column'
            module=modules[master];env=module.env({'COLUMN':c,'S_RD':2,'S_RT':4,'READ_STAGE':1,'CHAIN_STEP':6})
            actual={p:module.width(p,env) for p in module.ports}
            assert actual=={p:len(bits) for p,bits in ports.items()},(master,c,actual)
            path=V.write(out,master,[W,h],ports,'clk','Actual v20 neighbor pin positions with exact COLUMN RTL bit subsets; bounded local face packing. Global broadcast seams still need native audit.','v22_hc_return_columns',dict(clock_entries={'serial':['clk']},params={'COLUMN':c,'S_RD':2,'S_RT':4,'READ_STAGE':1,'CHAIN_STEP':6},source='tools/s81/hc_return_column_pins.py',qualification='PROVISIONAL v22 shape; GEN18r legality/pin_align and exact successor RTL ABI/native timing pending',source_bit_binding=bindings))
            report.append(dict(master=master,column=c,file=str(path.relative_to(a.out)),outline_um=[W,h],pins=sum(map(len,ports.values())),clock='independent serial root delivered at phi-wire-R; actual native R unresolved'))
    (a.out/'layout.json').write_text(json.dumps(dict(schema='opentallas.s81.return_column_pin_plan.v1',scope='PROVISIONAL_TOP_DOWN_PINS_NOT_CLOSURE',source_rtl_sha256=hashlib.sha256(a.rtl.read_bytes()).hexdigest(),source_port_widths_all8='PASS',leaves=report,remaining=['Exact source ABI comparison after COLUMN0 merge integration','All peer/neighbor pin-to-pin distances and native pair timing','GEN18r legality and pin_align0; cth contains no own registers','All root CTS insertion/spread and native boundary audits']),indent=1)+'\n')
    print(json.dumps(dict(leaves=report,neighbor_audit=neighbor_audit(a.out))))
if __name__=='__main__':main()
