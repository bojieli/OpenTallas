#!/usr/bin/env python3
"""Trace actual selected CAP CW ports to all80 registered native leaf inputs.

The bound lane already includes native input_q receiver stages. This view
adds no leaf +3 and infers neither source-frame arrival nor SRAM residence.
"""
from pathlib import Path
import argparse,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/s81_dv'))
from layer_prog.emitted_leaf_routes import Wiring
from layer_prog.emitted_norm_source import inventory,_params


class CaptureWiring(Wiring):
    """Also read the receiver's emitted epoch+data concatenated lane pads."""
    def __init__(self,text):
        super().__init__(text)
        self.capture_bitdelays={}
        for params,ports in re.findall(r'^\s*ot_dp_dly\s+#\((.*?)\)\s+\w+\s*\((.*?)\);',text,re.M):
            p=_params(params);c=_params(ports)
            if not c['q'].startswith('{'):continue
            source=self.bits(c['d']);target=self.bits(c['q'])
            assert len(source)==len(target)==int(p['W'])
            for a,b in zip(source,target):
                assert b not in self.capture_bitdelays
                self.capture_bitdelays[b]=(a,int(p['D']))
    def trace(self,bit,terminals,stack=()):
        if bit in self.capture_bitdelays:
            assert bit[0] not in stack
            source,delay=self.capture_bitdelays[bit]
            name,index,age=self.trace(source,terminals,stack+(bit[0],))
            return name,index,age+delay
        return super().trace(bit,terminals,stack)


def collect(bound):
    bound=Path(bound);source=inventory(bound);raw=json.load(open(bound/'bind_latency.json'))
    assert raw['schema']=='opentallas.die_plan.bind.v1'
    lanes={b['lane']:b for b in raw['buses']};assert len(lanes)==len(raw['buses'])
    rows=[];returns=[]
    for sl in source['slices']:
        text=Path(sl['wrapper_file']).read_text();w=CaptureWiring(text)
        matches=list(re.finditer(r'^\s*(ot_s81sl_capc5r_e6|ot_s81sl_capc5r_w3|ot_s81sl_capc2_w3)\s*(?:#\((.*?)\))?\s+(\w+)\s*\((.*?)^\s*\);',text,re.M|re.S))
        assert len(matches)==1,'one actual selected CAP constructor required'
        m=matches[0];family=m[1]
        assert _params(m[2] or '') == ({} if family=='ot_s81sl_capc2_w3' else {'MUT':'0'}), 'selected CAP parameter profile differs'
        ports=_params(m[4]);terms={p:w.bits(ports[p]) for p in ('cw_s_v','cw_s_a','cw_s_d','cw_n_v','cw_n_a','cw_n_d')}
        names={n for bits in terms.values() for n,_ in bits}
        receiver_names=set(w.inputs)
        for port in ('rt_w','rt_e'):
            if port not in ports:continue
            pinbits=w.bits(ports[port]);assert len(pinbits)%70==0
            for k in range(len(pinbits)//70):
                traced=[];input_lane=None
                for field_bit in [1,*range(3,68)]:
                    q,index,local=w.trace(pinbits[70*k+field_bit],receiver_names)
                    expr,n=w.inputs[q];outside=w.bits(expr)[index]
                    if outside[0] in w.landings:outside=w.bits(w.landings[outside[0]])[outside[1]]
                    bus=next((b for b in raw['buses'] if b['dst']==sl['part'] and b['bus_in']==outside[0]),None)
                    assert bus and n==bus['width']==70 and outside[1]==index==field_bit
                    assert input_lane is None or input_lane==bus['lane'];input_lane=bus['lane']
                    traced.append((local,bus['source_bits'][index]))
                assert len({age for age,_ in traced})==1
                # bind_latency.bound_stages ALREADY includes lane_pad(L), as
                # emitted by bind.py. The path below observes that pad after
                # u_bin's *_b receiver: count it once, not a second time.
                pad=sum(delay for target,(src,delay) in w.capture_bitdelays.items() if target==pinbits[70*k+1])
                assert traced[0][0]==pad, 'unexpected internal CAP ingress stage requires explicit pricing'
                frames={re.match(r'u_f_\d[LR]\d{2}',source_bit[1])[0] for _,source_bit in traced if source_bit[0]=='leaf'}
                assert len(frames)==1 and all(b[0]=='leaf' for _,b in traced)
                returns.append(dict(frame=frames.pop(),sid=sl['sid'],slice=sl['logical_slice'],CAP_family=family,
                    CAP_port=port,CAP_lane=k,lane=input_lane,source_partition=bus['src'],local_edges=traced[0][0],
                    bound_lane_edges=bus['bound_stages'],receiver_pad_already_in_bound_edges=pad,source_boundary_to_CAP_input_edges=bus['bound_stages'],
                    checked_return_bits=[1,*range(3,68)],source_bits=[bit for _,bit in traced],
                    event_basis='native frame producer source_bits before partition source ot_dp_st -> CAP wrapper raw70-bit input; bound source/receiver stages and receiver pad included once',
                    component_frame_publication_epoch_joined=False))
        for leaf in range(5):
            lane=lanes['dn_'+sl['part'][:-2]+'_L'+str(leaf)]
            assert lane['src']==sl['part'] and lane['dst']==sl['part'][:-2]+'_L'+str(leaf)
            header=re.search(r'^\s*output\s+wire\s+\[(\d+):0\]\s+'+re.escape(lane['bus_out'])+r'\s*,\s*//\s*(\d+) data \+ epoch \[(\d+)\]: lane '+re.escape(lane['lane'])+r', (\d+) cycles:',text,re.M)
            assert header and [int(header[i])for i in (1,2,3)]==[lane['width']]*3 and int(header[4])==lane['bound_stages']
            expr,width=w.outputs[lane['bus_out']];assert width==lane['width']
            hits={}
            for busbit,bit in enumerate(w.bits(expr)):
                try:n,i,age=w.trace(bit,names)
                except ValueError:continue
                hits.setdefault((n,i),[]).append((busbit,age))
            face='s' if leaf<3 else 'n';k=leaf if leaf<3 else leaf-3;mapping={};ages=set()
            for field,bits in [('v',2),('a',24),('d',64)]:
                requested=terms['cw_'+face+'_'+field][bits*k:bits*(k+1)];assert len(requested)==bits
                mapped=[]
                for bit in requested:
                    route=hits.get(bit,[]);assert len(route)==1,('missing or duplicate actual CAP bit',sl['part'],leaf,field,bit,route)
                    index,age=route[0];mapped.append(index);ages.add(age)
                mapping[field]=mapped
            assert len(ages)==1,'CAP valid/address/data local pipeline differs'
            local=ages.pop()
            rows.append(dict(sid=sl['sid'],slice=sl['logical_slice'],leaf=leaf,CAP_family=family,CAP_instance=m[3],lane=lane['lane'],active_width=width,
                CAP_output_to_registered_leafdn_edges=lane['bound_stages']+local,local_edges=local,bound_lane_edges=lane['bound_stages'],bus_bits=mapping,
                event_basis='CAP wrapper output pins -> registered native leafdn_i0_q; receiver stages included once'))
    assert len(rows)==80 and len(returns)==72 and len({r['frame'] for r in returns})==72
    return dict(status='PASS_ACTUAL_CAPTURE_BOUNDARY_WIRING',source_top_sha256=source['source_top_sha256'],source_files_sha256=source['source_files_sha256'],
        bind_latency_sha256=hashlib.sha256((bound/'bind_latency.json').read_bytes()).hexdigest(),leaves=rows,frame_returns=returns,
        scope='actual emitted CAP CW valid/address/data to registered native leaf boundary only',native_input_q_already_included=True,
        source_frame_arrival_qualified=False,SRAM_residency_qualified=False,leases_qualified=False,full_token=False,added_rtl_cycles=0)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bound',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    if a.out.exists():raise ValueError('preserve previous route verdict')
    try:r=collect(a.bound)
    except Exception as e:a.out.write_text(json.dumps(dict(status='FAIL',error=str(e)),indent=2));raise
    a.out.write_text(json.dumps(r,indent=2));print(r['status'],len(r['leaves']))
