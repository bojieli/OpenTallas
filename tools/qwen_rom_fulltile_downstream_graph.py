#!/usr/bin/env python3
"""Exhaustive bitwise Boolean proof of retained ROM CE and masked merge cones.

This checks combinational connectivity at named logical mask boundaries; it
does not prove mask FF transition/reset behavior or physical replica retention.
"""
import argparse, ast, hashlib, json, re
from pathlib import Path
from qwen_rom_fulltile_mapped_gate import TOP
from qwen_rom_fulltile_mapped_gate_r2 import capture_drivers
from qwen_rom_hold_capture_loaded_map import block

def boolean(expr, values, universe):
    node=ast.parse(expr.replace('!', '~').replace('*','&').replace('+','|'),mode='eval').body
    def visit(n):
        if isinstance(n,ast.Name): return values[n.id]
        if isinstance(n,ast.Constant) and n.value in (0,1): return universe if n.value else 0
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.Invert): return universe ^ visit(n.operand)
        if isinstance(n,ast.BinOp):
            a,b=visit(n.left),visit(n.right)
            if isinstance(n.op,ast.BitAnd):return a&b
            if isinstance(n.op,ast.BitOr):return a|b
            if isinstance(n.op,ast.BitXor):return a^b
        raise ValueError('unsupported Liberty function '+expr)
    return visit(node)

def variables(count):
    return [(sum(1<<row for row in range(1<<count) if (row>>bit)&1)) for bit in range(count)]

class Graph:
    def __init__(self,net,text):
        self.net=net;self.outputs={};self.functions={};self.ff_polarity={}
        for m in re.finditer(r'\bcell\s*\(([^)]+)\)',text):
            kind=m[1].strip().strip('"');body=block(text,m.start())
            state=re.search(r'next_state\s*:\s*"([^";]+)"',body)
            if state:self.ff_polarity[kind]=state[1].replace(' ','')
            for p in re.finditer(r'\bpin\s*\(([^)]+)\)',body):
                pb=block(body,p.start());f=re.search(r'\bfunction\s*:\s*"([^";]+)"',pb)
                if f:self.functions[kind,p[1].strip().strip('"')]=f[1]
        for name,c in net['cells'].items():
            for pin,direction in c['port_directions'].items():
                if direction=='output':
                    for bit in c['connections'][pin]:
                        if bit in self.outputs:raise ValueError('multiple drivers')
                        self.outputs[bit]=(name,c,pin)
    def seed_boundary(self,bit,value,seeds,universe):
        """Bind polarity along exact scalar BUF/INV to an actual FF output."""
        seen=set()
        while isinstance(bit,int):
            if bit in seen:raise ValueError('boundary cycle')
            seen.add(bit)
            if bit in seeds and seeds[bit]!=value:raise ValueError('contradictory boundary values')
            seeds[bit]=value
            if bit not in self.outputs:return
            name,c,pin=self.outputs[bit]
            if c['type'].startswith('DFF'):return
            inputs={p:v for p,v in c['connections'].items() if c['port_directions'][p]=='input'}
            if len(inputs)!=1:return
            p,wire=next(iter(inputs.items()))
            if len(wire)!=1:return
            expr=self.functions[c['type'],pin]
            zero=boolean(expr,{p:0},1);one=boolean(expr,{p:1},1)
            if (zero,one)==(0,1):pass
            elif (zero,one)==(1,0):value=universe^value
            else:raise ValueError('nontransparent scalar boundary')
            bit=wire[0]
    def eval(self,bit,seeds,universe,memo):
        if bit in seeds:return seeds[bit]
        if bit in ('0','1'):return universe if bit=='1' else 0
        if bit in memo:return memo[bit]
        name,c,pin=self.outputs[bit]
        if c['type'].startswith('DFF') or c['type'].startswith('ot_'):
            raise ValueError('unbound sequential/macro boundary '+name)
        vals={p:self.eval(bits[0],seeds,universe,memo) for p,bits in c['connections'].items() if c['port_directions'][p]=='input'}
        result=boolean(self.functions[c['type'],pin],vals,universe);memo[bit]=result;return result

def check(work,progress=None):
    progress={} if progress is None else progress
    raw=(work/'mapped.json').read_bytes();net=json.loads(raw)['modules'][TOP]
    graph=Graph(net,(work/'ss_merged.lib').read_text());captures=capture_drivers(net)
    out=net['netnames']['u_tile.u_logic.wrom_q']['bits']
    if len(out)!=512:raise ValueError('wrong merge width')
    patterns=variables(10);universe=(1<<1024)-1;merge=[]
    for pair in range(2):
        for bit in range(256):
            seeds={};expected=0
            for bank in range(5):
                ff=net['cells'][captures[f'u_tile.g_col[{pair}].g_bank[{bank}].u_rom'][bit]]
                if graph.ff_polarity[ff['type']]!='!D':raise ValueError('changed capture polarity')
                if set(ff['connections'])!={'D','CLK','QN'}:raise ValueError('changed capture pins')
                seeds[ff['connections']['QN'][0]]=universe^patterns[bank]
                name=f'u_tile.u_logic.g_pair[{pair}].g_bank[{bank}].g_cap.g_direct.g_mask[{bit//32}].local_sel'
                mask=net['netnames'][name]['bits']
                if len(mask)!=1 or mask[0] in seeds:raise ValueError('aliased mask/data boundary')
                graph.seed_boundary(mask[0],patterns[bank+5],seeds,universe)
                expected|=patterns[bank]&patterns[bank+5]
            if graph.eval(out[pair*256+bit],seeds,universe,{})!=expected:raise ValueError('masked merge truth differs at '+str(pair*256+bit))
            merge.append(pair*256+bit)
    progress.update(mapped_sha256=hashlib.sha256(raw).hexdigest(),masked_merge_bits=merge,
        truth_assignments_per_merge_bit=1024,masked_merge_combinational_graph='PASS',
        next_stage='macro_CE_producer_boundary')
    # Every macro CE must be the actual wrom_re AND its high-address bank decode.
    addr=net['netnames']['u_tile.u_logic.u_me.wrom_addr']['bits']
    read=net['netnames']['u_tile.u_logic.u_me.wrom_re']['bits']
    if len(addr)!=24 or len(read)!=1:raise ValueError('producer widths differ')
    pat=variables(13);universe=(1<<8192)-1;seeds={}
    graph.seed_boundary(read[0],pat[12],seeds,universe)
    for i,b in enumerate(addr[12:]):
        if isinstance(b,int):graph.seed_boundary(b,pat[i],seeds,universe)
    ce=[]
    for pair in range(2):
        for bank in range(5):
            macro=f'u_tile.g_col[{pair}].g_bank[{bank}].u_rom';c=net['cells'][macro]
            expected=pat[12]
            for i,b in enumerate(addr[12:]):
                value=seeds[b] if isinstance(b,int) else universe if b=='1' else 0
                expected&=value if (bank>>i)&1 else universe^value
            actual=graph.eval(c['connections']['ce_in'][0],seeds,universe,{})
            if actual!=expected:raise ValueError('macro CE truth differs '+macro)
            ce.append(macro)
    progress.update(macro_CE_witnesses=ce,next_stage='mask_transition_boundary')
    # Check actual mask D mux functions using old-mask, bank-strobe and the
    # source-attributed early-select FF. This permits sharing logically while
    # explicitly retaining the physical replica failure.
    src_early={name:c for name,c in net['cells'].items() if c['type'].startswith('DFF') and c.get('attributes',{}).get('src','').endswith('ot_qwen_rom_tile_context_candidate_r2.sv:180.13-182.64')}
    if len(src_early)!=5:raise ValueError('early select source count differs')
    def source_ff_ancestors(bit,seen=None):
        seen=set() if seen is None else seen
        if bit in seen or bit not in graph.outputs:return set()
        seen.add(bit);name,c,p=graph.outputs[bit]
        if c['type'].startswith('DFF'):return {name}
        found=set()
        for p,d in c['port_directions'].items():
            if d=='input':
                for b in c['connections'][p]:found.update(source_ff_ancestors(b,seen))
        return found
    controls=[];pat=variables(3);u=255
    for bank in range(5):
        term=net['cells'][f'u_tile.u_logic.g_distribution.u_tree.g_bank[{bank}].g_term[0].u_buf']
        early_names=source_ff_ancestors(term['connections']['A'][0]) & set(src_early)
        if len(early_names)!=1:raise ValueError('early source linkage differs')
        early_name=next(iter(early_names));early=src_early[early_name]
        if graph.ff_polarity[early['type']]!='!D':raise ValueError('early polarity differs')
        for pair in range(2):
            for chunk in range(8):
                mask_name=f'u_tile.u_logic.g_pair[{pair}].g_bank[{bank}].g_cap.g_direct.g_mask[{chunk}].local_sel'
                mask_bit=net['netnames'][mask_name]['bits'][0];seeds={}
                graph.seed_boundary(mask_bit,pat[0],seeds,u)
                mask_owners={graph.outputs[b][0] for b in seeds if b in graph.outputs and graph.outputs[b][1]['type'].startswith('DFF')}
                if len(mask_owners)!=1:raise ValueError('mask lacks exact scalar FF boundary')
                mask_ff_name=next(iter(mask_owners));ff=net['cells'][mask_ff_name]
                if graph.ff_polarity[ff['type']]!='!D':raise ValueError('mask polarity differs')
                graph.seed_boundary(net['netnames']['u_tile.u_logic.code_rd_bank']['bits'][bank],pat[1],seeds,u)
                seeds[early['connections']['QN'][0]]=u^pat[2]
                expected=(pat[1]&pat[2])|((u^pat[1])&pat[0])
                if graph.eval(ff['connections']['D'][0],seeds,u,{})!=expected:raise ValueError('mask next-state mux differs '+mask_name)
                if ff['connections']['CLK']!=early['connections']['CLK'] or ff['connections']['SETN']!=['1']:raise ValueError('mask clock/set differs')
                reset_seeds={net['ports']['reset_stream_n']['bits'][0]:1}
                if graph.eval(ff['connections']['RESETN'][0],reset_seeds,1,{})!=1:raise ValueError('mask reset connectivity differs')
                reset_seeds={net['ports']['reset_stream_n']['bits'][0]:0}
                if graph.eval(ff['connections']['RESETN'][0],reset_seeds,1,{})!=0:raise ValueError('mask reset deassert connectivity differs')
                controls.append(dict(logical_mask=mask_name,actual_FF=mask_ff_name,early_select_FF=early_name,truth_assignments=8))
    return dict(status='PASS_ACTUAL_ROM_CE_MASK_TRANSITIONS_AND_MASKED_MERGE_GRAPH_ONLY',mapped_sha256=hashlib.sha256(raw).hexdigest(),
        capture_bits=2560,merge_bits=merge,truth_assignments_per_merge_bit=1024,
        macro_CE_witnesses=ce,truth_assignments_per_CE=8192,
        mask_state_reset_enable_transitions=controls,mask_logical_transitions_qualified=True,
        physical_mask_FF_count=len({r['actual_FF'] for r in controls}),physical_replica_survival='FAIL_RETAINED',
        parent_IO_and_clock_context_qualified=False,contextual_SSFF=False,P_and_R_admitted=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise SystemExit('refuse overwrite')
    progress={}
    try:result=check(a.work,progress)
    except Exception as e:result=dict(status='FAIL_ACTUAL_DOWNSTREAM_GRAPH_RETAINED',reason=str(e),partial_completed_checks=progress,contextual_SSFF=False)
    a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k in ('status','reason')}));raise SystemExit(0 if result['status'].startswith('PASS') else 1)
