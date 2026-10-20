#!/usr/bin/env python3
"""Extract actual reset cone for native D8 epoch benches; unknown producers stay explicit inputs."""
import argparse, collections, hashlib, json, re
from pathlib import Path

def extract(text, lane):
    inst={}; uses=collections.defaultdict(list); taps=collections.defaultdict(list);aliases={}
    for line in text.splitlines():
        m=re.match(r'\s*(\w+)\s+(?:#\(.*?\)\s+)?(\w+)\s+\(',line)
        if m:
            master,name=m.groups(); ports=dict(re.findall(r'\.(\w+)\((\w+)\)',line));inst[name]=(master,ports,line.strip())
            for port,net in ports.items():uses[net].append(dict(instance=name,master=master,port=port))
            if master in ('qfd_rst_rep','qfd_rst_rep_p8'):
                for out in ['q0','q1']:
                    if out in ports:taps[ports[out]].append((name,out))
        m=re.match(r'\s*assign\s+(\w+)(?:\[0:0\])?\s*=\s*(\w+)(?:\[0:0\])?\s*;',line)
        if m:aliases[m[1]]=m[2]
    selected={};roots={};blockers=[]
    # Follow only known reset/control producers with explicit output directions.
    for name,(master,ports,line) in inst.items():
        if master.startswith(('qfd_rlyr0_', 'qfd_rlyr_', 'qfd_rlyrl_')):
            if 'b' in ports: taps[ports['b']].append((name,'b'))
        elif master == 'qfd_rstsync':
            for out in ['rso_d','rso_f']:
                if out in ports:taps[ports[out]].append((name,out))
        elif master == 'qfd_rstseq':
            for out in ['rso_io','rso_f','rso_s','rso_ctlm','rso_seq']:
                if out in ports:taps[ports[out]].append((name,out))
    def walk(net,seen=()):
        if net in seen:raise ValueError('reset cycle '+net)
        if net in aliases:return dict(net=net,alias=walk(aliases[net],(*seen,net)))
        candidates=taps.get(net,[])
        if len(candidates)>1:raise ValueError('multiple reset drivers '+net)
        if candidates:
            name,out=candidates[0];master,ports,line=inst[name];selected[name]=line
            upstream = 'd' if master in ('qfd_rst_rep','qfd_rst_rep_p8') else ('arst_n' if master=='qfd_rstsync' else ('rsi' if master=='qfd_rstseq' else 'a'))
            node=dict(net=net,instance=name,master=master,output=out,clock=ports.get('clk',ports.get('ck',ports.get('ckf'))),
                      clock_pin=name+'/'+('clk' if 'clk' in ports else ('ck' if 'ck' in ports else 'ckf')),
                      input=walk(ports[upstream],(*seen,net)))
            if master in ('qfd_rst_rep','qfd_rst_rep_p8'):node['nominal_local_edges']=10 if master.endswith('_p8') else 2
            return node
        roots[net]=[u for u in uses[net] if not(u['master'] in ('qfd_rst_rep','qfd_rst_rep_p8') and u['port']=='d')]
        return dict(net=net,unresolved_root=True,endpoint_candidates=roots[net])
    first=(lane.get('stations') or [lane['landing']])[0]; landing=lane['landing']
    if first not in inst or landing not in inst:raise ValueError('lane instance absent')
    en=inst[first][1].get('en');rs=inst[landing][1].get('rs')
    if not en or not rs:raise ValueError('actual en/rs pin absent')
    result=dict(schema='opentallas.qwen.d8-reset-cone.v1',bid=lane['bid'],landing=landing,
                source_pin=first+'/en',receiver_pin=landing+'/rs',
                en_trace=walk(en),rs_trace=walk(rs),qualified=False)
    result['root_inputs']=roots;result['exact_instances']=[selected[k]for k in sorted(selected)]
    clocks=set()
    def collect(node):
        if 'clock_pin' in node:clocks.add(node['clock_pin'])
        for k in ['input','alias']:
            if k in node:collect(node[k])
    collect(result['en_trace']);collect(result['rs_trace'])
    result['required_actual_clock_pins']=sorted(clocks)
    result['blockers']=['UNMEASURED_NATIVE_ROOT_EPOCH:'+r for r in sorted(roots)]
    result['upstream_boundary_models']=[dict(root=net,instance=u['instance'],master=u['master'],port=u['port'],
         instance_statement=inst[u['instance']][2],production_clock_reset_correlation=False)
         for net,ends in roots.items() for u in ends if u['master']=='qfd_ckbump']
    if result['upstream_boundary_models']:
        result['blockers'].append('NO_PRODUCTION_UPSTREAM_CLOCK_RESET_CORRELATION')
    result['bench_requirement']='Instantiate exact listed reset cells with measured per-cell-domain TT/FF clocks, actual root producer RTL/programme and real D8 en/rs. Observe RAW en/rs pin edges, source first write and receiver first legal output across cold/paired/source-only/receiver-only restart. Never infer a global release edge by summing nominal_local_edges across different clocks.'
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--netlist',type=Path,required=True);p.add_argument('--lanes',type=Path,required=True);p.add_argument('--bid',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    lanes=json.loads(a.lanes.read_text()); found=[r for r in lanes['lanes']if r['bid']==a.bid]
    if len(found)!=1:p.error('lane missing or ambiguous')
    result=extract(a.netlist.read_text(),found[0]);result['source_sha256']={str(f):hashlib.sha256(f.read_bytes()).hexdigest()for f in[a.netlist,a.lanes]}
    a.out.write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(dict(bid=a.bid,instances=len(result['exact_instances']),roots=result['root_inputs'],qualified=False)))
if __name__=='__main__':main()
