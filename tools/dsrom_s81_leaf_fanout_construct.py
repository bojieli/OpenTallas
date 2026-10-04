"""Deterministic fanout-eight construction from retained native mapped leaves.
No resynthesis, clock rewiring, logical gates, or register cuts are introduced.
"""
import argparse,copy,hashlib,json,re,subprocess
from pathlib import Path
BUF='BUFx4_ASAP7_75t_R'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def construct(graph,limit=8,capture_buffer=False):
    if limit!=8:raise ValueError('selected construction is fanout eight')
    j=copy.deepcopy(graph);m=j['modules']['leaf']; cells=m['cells']; original=copy.deepcopy(cells)
    sinks={};clocks=set(m['ports']['clk']['bits']);bits=[]
    for c,v in cells.items():
        for p,bs in v['connections'].items():
            bits+= [b for b in bs if isinstance(b,int)]
            if v['port_directions'][p]=='input':
                for i,b in enumerate(bs):sinks.setdefault(b,[]).append((c,p,i))
    nextbit=max(bits)+1; added=[];rewired=[]
    def branch(src,ss):
        nonlocal nextbit
        out=nextbit;nextbit+=1;name=f'fanout_buf_{len(added)}'
        cells[name]={'type':BUF,'parameters':{},'attributes':{'keep':'1'},'port_directions':{'A':'input','Y':'output'},'connections':{'A':[src],'Y':[out]}}
        added.append(name)
        if len(ss)<=8:
            for c,p,i in ss:cells[c]['connections'][p][i]=out;rewired.append([c,p,i,src,out])
        else:
            # At most eight children, balanced deterministic contiguous groups.
            size=(len(ss)+7)//8
            for start in range(0,len(ss),size):branch(out,ss[start:start+size])
    for b,ss in sorted(sinks.items(),key=lambda x:str(x[0])):
        if isinstance(b,int) and b not in clocks and len(ss)>8:branch(b,ss)
    capture_buffers=0
    if capture_buffer:
        inputs=set(m['ports']['din']['bits'])
        # One fixed positive delay BUF on every internal register D landing.
        # Designed for a 25ps adverse clock-skew allowance; not a tuning sweep.
        for name,v in original.items():
            if 'DFFHQ' in v['type'] and v['connections']['D'][0] not in inputs:
                b=cells[name]['connections']['D'][0]
                branch(b,[(name,'D',0)]);capture_buffers+=1
    # Every old input resolves to precisely its original net after contracting BUF.
    parent={v['connections']['Y'][0]:v['connections']['A'][0] for n,v in cells.items() if n in added}
    def resolve(b):
        while b in parent:b=parent[b]
        return b
    for n,v in original.items():
        for p,bs in v['connections'].items():
            got=cells[n]['connections'][p]
            if v['port_directions'][p]=='input':assert [resolve(b) for b in got]==bs
            else:assert got==bs
    return j,{'buffer_count':len(added),'capture_buffer_count':capture_buffers,'rewired_input_pins':len(rewired),'logic_and_register_connections_equal_after_buffer_contraction':True,'clock_nets_unchanged':True,'max_signal_fanout':8}
def verilog(j):
    m=j['modules']['leaf'];used=set()
    for v in m['cells'].values():
        for bs in v['connections'].values():used.update(b for b in bs if isinstance(b,int))
    def bit(b):return f'n{b}' if isinstance(b,int) else "1'b"+b
    s=['module leaf(clk,din,q);','input clk;',f'input [{len(m["ports"]["din"]["bits"])-1}:0] din;',f'output [{len(m["ports"]["q"]["bits"])-1}:0] q;','wire '+','.join(f'n{b}' for b in sorted(used))+';']
    for p,v in m['ports'].items():
        for i,b in enumerate(v['bits']):
            pn=p if p=='clk' else f'{p}[{i}]'
            s.append(f'assign {bit(b)} = {pn};' if v['direction']=='input' else f'assign {pn} = {bit(b)};')
    for i,(name,v) in enumerate(m['cells'].items()):
        ports=','.join('.'+p+'('+ ('{'+','.join(bit(b) for b in reversed(bs))+'}' if len(bs)>1 else bit(bs[0]))+')' for p,bs in v['connections'].items())
        s.append(f'{v["type"]} cell_{i}({ports});')
    return '\n'.join(s+['endmodule',''])
def run(retained,out,capture_buffer=False):
    retained=Path(retained);out=Path(out);out.mkdir(exist_ok=False)
    results={}
    for name in ('encode','decode','equal83','merge256'):
        work=out/name;work.mkdir();p=retained/name/'mapped.json';j,proof=construct(json.loads(p.read_text()),capture_buffer=capture_buffer);v=work/'buffered.v';v.write_text(verilog(j))
        (work/'buffered.json').write_text(json.dumps(j,sort_keys=True)+'\n')
        timing={}
        for c in ('ss','ff'):
            old=(retained/name/f'{c}.tcl').read_text();old=re.sub(r'read_verilog [^\n]+',f'read_verilog {v}',old)
            t=work/f'{c}.tcl';t.write_text(old);log=work/f'{c}.log'
            with log.open('x') as f:r=subprocess.run(['sta','-exit',str(t)],stdout=f,stderr=subprocess.STDOUT)
            text=log.read_text()
            if r.returncode or re.search(r'^Error:',text,re.M):raise ValueError(text[-2000:])
            slacks=[float(s) for s in re.findall(r'([-\d.]+)\s+slack',text)]
            assert len(slacks)==2
            # Violations after the register timing sections are electrical.
            elec=text.split('max slew',1)[-1]
            timing[c]={'setup_slack_ps':slacks[0],'hold_slack_ps':slacks[1],'electrical_violations':re.findall(r'^.*\(VIOLATED\).*$',elec,re.M),'log_sha256':digest(log)}
        results[name]={'retained_map_sha256':digest(p),'buffered_netlist_sha256':digest(v),'construction':proof,'timing':timing}
    r={'schema':'dsrom.s81.native_leaf.fanout8.v1','target_GHz':.9,'wire_CTS_included':False,'results':results,'runner_sha256':digest(__file__)}
    (out/'record.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');return r
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--retained',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--capture-buffer',action='store_true');a=p.parse_args();print(json.dumps(run(a.retained,a.out,a.capture_buffer),indent=2))
