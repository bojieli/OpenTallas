#!/usr/bin/env python3
"""Exhaustive bitwise Boolean proof of retained ROM CE and masked merge cones.

This checks combinational and next-state pin functions using actual cells and
pinned source. It does not qualify initialized parent state, electrical timing,
complete operand bit order, or physical replica retention.
"""
import argparse, ast, hashlib, json, re, subprocess, tempfile
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
    def ancestors(self,bit,seen=None):
        seen=set() if seen is None else seen
        if bit in seen or bit not in self.outputs:return set()
        seen.add(bit);name,c,p=self.outputs[bit]
        if c['type'].startswith('DFF'):return {name}
        found=set()
        for p,d in c['port_directions'].items():
            if d=='input':
                for b in c['connections'][p]:found.update(self.ancestors(b,seen))
        return found

def address_boundary(graph,net):
    """Prove observable bank decoding without inventing unused HDL bit labels.

    The three bank-varying bits are identified by bank1/2/4 truth signatures.
    All nine remaining bits are checked for zero. Their individual cur-bit
    transition identities remain open; permutations of this zero-check group
    cannot change any legal/illegal bank decode observation.
    """
    base='u_tile.u_logic.u_me.';read=net['netnames'][base+'wrom_re']['bits'][0]
    ro=graph.ancestors(read)
    if len(ro)!=1:raise ValueError('read producer not scalar')
    read_name=next(iter(ro));rc=net['cells'][read_name]
    if rc['type']!='DFFASRHQNx1_ASAP7_75t_R':raise ValueError('read producer reset cell differs')
    candidates=graph.ancestors(net['cells']['u_tile.g_col[0].g_bank[0].u_rom']['connections']['ce_in'][0])-ro
    if len(candidates)!=12:raise ValueError('need all12 actual high-address FFs')
    names=sorted(candidates);p=variables(13);u=(1<<8192)-1;seeds={}
    graph.seed_boundary(read,p[12],seeds,u)
    for i,name in enumerate(names):
        c=net['cells'][name]
        if c['type']!='DFFHQNx1_ASAP7_75t_R' or not c.get('attributes',{}).get('src','').endswith('ot_qwen_w12_matvec.sv:491.5-547.8'):
            raise ValueError('address source/type differs')
        if c['connections']['CLK']!=rc['connections']['CLK'] or graph.ff_polarity[c['type']]!='!D':raise ValueError('address clock/polarity differs')
        seeds[c['connections']['QN'][0]]=u^p[i]
    signatures=[]
    for bank in range(5):
        observed=[]
        for pair in range(2):
            c=net['cells'][f'u_tile.g_col[{pair}].g_bank[{bank}].u_rom']
            t=graph.eval(c['connections']['ce_in'][0],seeds,u,{})
            # Exactly one high-address pattern accepts when read=1; all
            # patterns must reject when read=0. Exhaustive, not sampling.
            if t.bit_count()!=1 or t.bit_length()<=4096:raise ValueError('CE does not select exactly one read-qualified address')
            observed.append(t.bit_length()-1-4096)
        if observed[0]!=observed[1]:raise ValueError('column CE identity differs')
        signatures.append(observed[0])
    if signatures[0]!=0:raise ValueError('bank0 requires nonzero high address')
    if any(x==0 or x&(x-1) for x in (signatures[1],signatures[2],signatures[4])):raise ValueError('bank1/2/4 signatures not onehot')
    indices=[signatures[b].bit_length()-1 for b in (1,2,4)]
    if len(set(indices))!=3 or signatures[3]!=(signatures[1]|signatures[2]):raise ValueError('bank bit significance differs')
    return dict(status='PASS_OBSERVABLE_FULL12BIT_BANK_DECODE_ONLY',
        source_low_bank_bit_FFs={str(12+i):names[j] for i,j in enumerate(indices)},
        source_high_zero_check_FFs=[name for i,name in enumerate(names) if i not in indices],
        source_high_zero_check_bit_indices=list(range(15,24)),
        per_bit_transition_identity_for_zero_check_group='OPEN',
        actual_FF657178_classification='anonymous high-address decode FF; individual cur-bit identity not assumed',
        read_producer_FF=read_name,actual_address_FFs=names,truth_assignments=8192,
        accepted_truth_signatures=signatures,legal_high_address_values=[0,1,2,3,4],
        legal_full_address_range=[0,20479],illegal_address_or_read0_has_no_macro_CE=True,
        named_high_address_bits='unused dangling labels, not constants or missing hardware')

def kv_capture_boundary(graph,net):
    """Prove all512 actual held raw-code FF D muxes, not decoded FP32 bits."""
    source='ot_qwen_rom_tile_context_candidate_r2.sv:'
    ffs={name:c for name,c in net['cells'].items() if c['type']=='DFFHQNx1_ASAP7_75t_R' and c.get('attributes',{}).get('src','').endswith(source+'313.13-313.62')}
    quals={name:c for name,c in net['cells'].items() if c['type'].startswith('DFF') and c.get('attributes',{}).get('src','').endswith(source+'312.13-312.106')}
    if len(ffs)!=512 or len(quals)!=1:raise ValueError('KV source capture/qualifier FF counts differ')
    qual_name,qual=next(iter(quals.items()));pat=variables(3);u=255;rows=[]
    def macro_bits(bit,seen=None):
        seen=set() if seen is None else seen
        if bit in seen or bit not in graph.outputs:return set()
        seen.add(bit);name,c,p=graph.outputs[bit]
        if c['type']=='ot_sram_1r1w_128x256_m1_r2c2':
            if p!='rd_out':raise ValueError('wrong SRAM read output')
            return {(name,c['connections'][p].index(bit),bit)}
        if c['type'].startswith('DFF'):return set()
        found=set()
        for p,d in c['port_directions'].items():
            if d=='input':
                for b in c['connections'][p]:found.update(macro_bits(b,seen))
        return found
    for name,c in sorted(ffs.items()):
        mb=macro_bits(c['connections']['D'][0])
        if len(mb)!=1:raise ValueError('KV capture D does not bind one raw macro bit '+name)
        macro,index,bit=next(iter(mb))
        if graph.ff_polarity[c['type']]!='!D' or graph.ff_polarity[qual['type']]!='!D':raise ValueError('KV polarity differs')
        if c['connections']['CLK']!=qual['connections']['CLK'] or c['connections']['CLK']!=net['cells'][macro]['connections']['clk']:raise ValueError('KV clock differs')
        seeds={bit:pat[0],c['connections']['QN'][0]:u^pat[1],qual['connections']['QN'][0]:u^pat[2]}
        expected=(pat[2]&pat[0])|((u^pat[2])&pat[1])
        if graph.eval(c['connections']['D'][0],seeds,u,{})!=expected:raise ValueError('KV raw-code hold mux differs '+name)
        rows.append(dict(capture_FF=name,macro=macro,macro_raw_bit=index,truth_assignments=8))
    if len({(r['macro'],r['macro_raw_bit']) for r in rows})!=512:raise ValueError('KV raw code bits aliased')
    return dict(status='PASS_ALL512_RAW_KV_CODE_CAPTURE_D_MUXES_ONLY',qualifier_FF=qual_name,witnesses=rows,
        actual_raw_capture_FFs=512,named_raw_capture_labels='partial labels cannot establish missing FFs',
        E4M3_decoder_consumer_equivalence='OPEN',full_source_qualification=False)

def low_address_boundary(graph,net):
    addr=net['netnames']['u_tile.u_logic.u_me.wrom_addr']['bits'];rows=[];owners=set()
    for i,bit in enumerate(addr[:12]):
        seed={};graph.seed_boundary(bit,2,seed,3)
        ff={graph.outputs[b][0] for b in seed if b in graph.outputs and graph.outputs[b][1]['type'].startswith('DFF')}
        if len(ff)!=1:raise ValueError('low address bit has no scalar FF boundary')
        name=next(iter(ff));owners.add(name)
        if not net['cells'][name].get('attributes',{}).get('src','').endswith('ot_qwen_w12_matvec.sv:491.5-547.8'):raise ValueError('low address source differs')
        if net['cells'][name]['connections']['CLK']!=net['ports']['clk_stream']['bits']:raise ValueError('low address clock differs')
        for pair in range(2):
            for bank in range(5):
                macro=f'u_tile.g_col[{pair}].g_bank[{bank}].u_rom'
                pins=net['cells'][macro]['connections']['addr_in']
                if len(pins)!=12 or graph.eval(pins[i],seed,3,{})!=2:raise ValueError('macro address bit differs')
        rows.append(dict(source_low_bit=i,actual_FF=name,macro_address_pins_checked=10))
    if len(owners)!=12:raise ValueError('low address bits aliased')
    return dict(status='PASS_ALL120_MACRO_LOW_ADDRESS_PIN_LINKS',actual_low_address_FFs=12,witnesses=rows,
        cur_to_address_transition_bit_join='OPEN')

def kv_codec_boundary(graph,net,kv,work):
    source=(work/'inputs/13_ot_qwen_rom_tile_context_candidate_r2.sv').read_text()
    f=re.search(r'function automatic \[31:0\] e4m3_f32.*?endfunction',source,re.S)
    if not f:raise ValueError('pinned source codec absent')
    # Compile only the literal combinational function to obtain all256 source
    # values. This is not a new tile synthesis or numerical token campaign.
    tb='module codec;'+f[0]+' integer i; initial begin for(i=0;i<256;i=i+1) $display("%08x",e4m3_f32(i[7:0])); $finish;end endmodule'
    with tempfile.TemporaryDirectory(prefix='qrom-codec-source-') as d:
        p=Path(d);(p/'codec.sv').write_text(tb)
        subprocess.run(['iverilog','-g2012','-s','codec','-o',str(p/'sim'),str(p/'codec.sv')],check=True,capture_output=True)
        raw=subprocess.run(['vvp',str(p/'sim')],check=True,capture_output=True,text=True).stdout
    values=[int(v,16) for v in raw.splitlines()]
    if len(values)!=256:raise ValueError('codec truth table incomplete')
    outputs=net['netnames']['u_tile.u_logic.me_kv_q']['bits']
    if len(outputs)!=2048:raise ValueError('codec output geometry differs')
    captures={(r['macro'],r['macro_raw_bit']):r['capture_FF'] for r in kv['witnesses']}
    pattern=variables(8);u=(1<<256)-1;checked=0;constant_zero=0;unresolved=[]
    for lane in range(64):
        macro=f'u_tile.g_kv[{lane//32}].u_kv';seed={}
        for i in range(8):
            c=net['cells'][captures[macro,(lane%32)*8+i]]
            seed[c['connections']['QN'][0]]=u^pattern[i]
        for bit in range(32):
            expected=sum(1<<row for row,v in enumerate(values) if (v>>bit)&1)
            constant_zero+=expected==0
            try:
                actual=graph.eval(outputs[32*lane+bit],seed,u,{})
                if actual!=expected:raise ValueError('actual named output truth differs')
                checked+=1
            except (KeyError,ValueError) as e:
                unresolved.append(dict(lane=lane,decoded_bit=bit,mapped_named_bit=outputs[32*lane+bit],reason=str(e),source_function_constant_zero=expected==0))
    # Anonymous MEM_PIPE consumers must be actual FF D pins from the literal
    # operand always block. Classify their raw-code dependencies and exact
    # functions; do not repair or broaden the stale output-name regex.
    raw_owner={r['capture_FF']:(int(re.search(r'g_kv\[(\d+)\]',r['macro'])[1])*32+r['macro_raw_bit']//8) for r in kv['witnesses']}
    consumer_by_lane={i:[] for i in range(64)}
    for name,c in net['cells'].items():
        if c['type']!='DFFHQNx1_ASAP7_75t_R' or not c.get('attributes',{}).get('src','').endswith('ot_qwen_w12_matvec.sv:708.9-723.12'):continue
        deps=graph.ancestors(c['connections']['D'][0])
        if not deps or not deps<=set(raw_owner):continue
        lanes={raw_owner[d] for d in deps}
        if len(lanes)!=1:raise ValueError('operand codec capture mixes raw lanes')
        lane=next(iter(lanes));macro=f'u_tile.g_kv[{lane//32}].u_kv';seed={}
        for i in range(8):seed[net['cells'][captures[macro,(lane%32)*8+i]]['connections']['QN'][0]]=u^pattern[i]
        if graph.ff_polarity[c['type']]!='!D' or c['connections']['CLK']!=net['ports']['clk_stream']['bits']:raise ValueError('operand capture clock/polarity differs')
        truth=graph.eval(c['connections']['D'][0],seed,u,{})
        consumer_by_lane[lane].append((name,truth))
    consumer_rows=[];missing=[]
    for lane in range(64):
        for bit in range(32):
            expected=sum(1<<row for row,v in enumerate(values) if (v>>bit)&1)
            if expected in (0,u):continue
            matches=[dict(FF=name,logical_bit_encoding='D' if t==expected else 'QN',source='MEM_PIPE literal always block')
                     for name,t in consumer_by_lane[lane] if t in (expected,u^expected)]
            if not matches:missing.append(dict(lane=lane,bit=bit))
            else:consumer_rows.append(dict(lane=lane,bit=bit,actual_operand_capture_witnesses=matches,truth_assignments=256))
    return dict(status='PASS_LITERAL_SOURCE_E4M3_TO_ACTUAL_OPERAND_CAPTURE_PINS' if not missing else 'UNQUALIFIED_CODEC_CONSUMER_PIN_JOIN',source_function_sha256=hashlib.sha256(f[0].encode()).hexdigest(),
        source_truth_table=values,source_truth_sha256=hashlib.sha256(raw.encode()).hexdigest(),source_values_per_lane=256,
        decoded_output_bits_checked=checked,decoded_output_bits_expected=2048,unresolved_named_output_bits=unresolved,source_constant_zero_output_bits=constant_zero,
        actual_operand_capture_bit_witnesses=consumer_rows,missing_meaningful_consumer_bits=missing,
        downstream_operand_Q_to_multiplier_bit_order_qualified=False,
        full_parent_input_and_lifetime_qualification=False)

def check(work,progress=None):
    progress={} if progress is None else progress
    raw=(work/'mapped.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!='92b6cf36af938f89468c6ce07d7bd5624239172eecd914de3eb750ff435802a0':raise ValueError('different mapped source requires separate qualification')
    pins=json.loads((work/'inputpins.json').read_text());portable=json.loads((work/'portable_inputs.json').read_text())
    for name,expected in pins.items():
        if hashlib.sha256((work/portable[name]).read_bytes()).hexdigest()!=expected:raise ValueError('pinned input differs '+name)
    net=json.loads(raw)['modules'][TOP]
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
    recovered=address_boundary(graph,net)
    recovered['low_address_pin_graph']=low_address_boundary(graph,net)
    recovered['actual_complete_address_FFs']=24
    progress['anonymous_high_address_source_join']=recovered
    ce=[f'u_tile.g_col[{pair}].g_bank[{bank}].u_rom' for pair in range(2) for bank in range(5)]
    progress.update(macro_CE_witnesses=ce,next_stage='mask_transition_boundary')
    progress['KV_raw_capture_graph']=kv_capture_boundary(graph,net)
    progress['KV_codec_graph']=kv_codec_boundary(graph,net,progress['KV_raw_capture_graph'],work)
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
        address_observable_decoder_join=recovered,KV_raw_capture_graph=progress['KV_raw_capture_graph'],
        KV_codec_graph=progress['KV_codec_graph'],
        individual_address_cur_bit_transitions_qualified=False,all_parent_inputs_driven_initialized_contract_qualified=False,
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
