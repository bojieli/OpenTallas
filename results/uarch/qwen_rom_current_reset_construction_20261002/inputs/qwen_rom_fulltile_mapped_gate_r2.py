#!/usr/bin/env python3
"""Actual ROM-pin -> FF-D capture proof; no dependence on optimized net names."""
import argparse,hashlib,json,re
from pathlib import Path
from qwen_rom_fulltile_mapped_gate import ff_endpoints,TOP

def capture_drivers(net):
    data_ff={};all_capture=[];per_macro={}
    for name,c in net['cells'].items():
        if c['type']=='DFFHQNx1_ASAP7_75t_R':data_ff.setdefault(c['connections']['D'][0],[]).append((name,c))
    for name,c in net['cells'].items():
        if c['type']!='ot_rom_4096x266_m8':continue
        rd=c['connections']['rd_out']
        if len(rd)!=266 or len(c['connections']['clk'])!=1:raise ValueError('wrong ROM interface')
        drivers=[]
        for bit in rd[:256]:
            owners=data_ff.get(bit,[])
            if len(owners)!=1:raise ValueError('payload bit lacks one direct nonreset capture FF-D')
            ffname,ff=owners[0]
            if ff['connections']['CLK']!=c['connections']['clk']:raise ValueError('ROM/capture clock differs')
            drivers.append(ffname)
        if len(set(drivers))!=256:raise ValueError('ROM capture replicas aliased')
        per_macro[name]=drivers;all_capture.extend(drivers)
    if len(per_macro)!=10 or len(set(all_capture))!=2560:raise ValueError('incomplete10ROM/2560capture drivers')
    return per_macro

def source_capture_proof(source):
    endpoints={}
    for name,c in source['cells'].items():
        if c['type']=='$dff':
            con=c['connections']
            for bit in con['Q']:endpoints[bit]=(name,c)
    rows={}
    for pair in range(2):
        for bank in range(5):
            macro=f'u_tile.g_col[{pair}].g_bank[{bank}].u_rom'
            cap=f'u_tile.u_logic.g_pair[{pair}].g_bank[{bank}].g_cap.g_direct.cap'
            rd=source['cells'][macro]['connections']['rd_out'][:256]
            q=source['netnames'][cap]['bits']
            if len(q)!=256:raise ValueError('source cap width')
            for i,b in enumerate(q):
                _,ff=endpoints[b];con=ff['connections'];offset=con['Q'].index(b)
                if con['D'][offset]!=rd[i] or con['CLK']!=source['cells'][macro]['connections']['clk'] or int(ff['parameters']['CLK_POLARITY'],2)!=1:
                    raise ValueError('source hierarchy is not direct positive-edge capture')
            rows[macro]=dict(source_net=cap,width=256,source_FF_cells=sorted({endpoints[b][0] for b in q}))
    return rows

def inspect(work):
    from qwen_rom_hold_capture_loaded_map import block
    text=(work/'ss_merged.lib').read_text()
    library={m[1].strip().strip('"'):block(text,m.start()) for m in re.finditer(r'\bcell\s*\(([^)]+)\)',text)}
    terminal=json.loads((work/'terminal.json').read_text())
    if terminal['status']!='PASS_COMPLETE_SOURCE_MAP_ONLY_CONTEXT_OPEN':raise ValueError('derived exact classification did notPASS')
    pins=json.loads((work/'sourcepins.json').read_text());assert pins['SMIN']==6 and pins['optin']==1
    net=json.loads((work/'mapped.json').read_text())['modules'][TOP]
    source=json.loads((work/'source_proc.json').read_text())['modules'][TOP]
    source_proof=source_capture_proof(source)
    del source
    captures=capture_drivers(net)
    drivers={};links={}
    for name,c in net['cells'].items():
        con=c['connections'];kind=c['type']
        if kind.startswith('DFF') and kind.endswith('_ASAP7_75t_R'):
            for pin in ('Q','QN'):
                for bit in con.get(pin,[]):drivers[bit]=name
        elif kind in library and set(con)=={'A','Y'} and len(con['A'])==len(con['Y'])==1:
            out=re.search(r'\bpin\s*\(Y\)',library[kind])
            if out:
                body=block(library[kind],out.start());function=re.search(r'function\s*:\s*"([^";]+)"',body)
                if function and function[1].replace(' ','') in ('A','!A','~A'):links[con['Y'][0]]=con['A'][0]
    def selected(pattern,expected):
        bits=[b for name,n in net['netnames'].items() if re.fullmatch(pattern,name) for b in n['bits']]
        owners=[];missing=[]
        for bit in bits:
            seen=set()
            while bit not in drivers and bit in links and bit not in seen:seen.add(bit);bit=links[bit]
            if bit not in drivers:missing.append(bit)
            else:owners.append(drivers[bit])
        return dict(expected=expected,named_bits=len(bits),unique_FF_count=len(set(owners)),unresolved_bits=missing,FF_endpoints=owners,
                    PASS=len(bits)==expected and len(set(owners))==expected and not missing)
    base=r'u_tile\.u_logic\.'
    endpoints={'mask':selected(base+r'g_pair\[[01]\]\.g_bank\[[0-4]\]\.g_cap\.g_direct\.g_mask\[[0-7]\]\.local_sel',80),
      'bank_strobe':selected(base+r'code_rd_bank',5),'early_select':selected(base+r'code_sel_q',5),
      'KV_capture':selected(base+r'g_kv_local\.g_kvcap\.cap',512),
      'address_producer':selected(base+r'u_me\.wrom_addr',24),'read_producer':selected(base+r'u_me\.wrom_re',1)}
    # Source-attributed evidence is separate from named-wire diagnostics.
    src_groups={}
    for name,c in net['cells'].items():
        if c['type'].startswith('DFF'):
            src=c.get('attributes',{}).get('src','')
            if 'ot_qwen_rom_tile_context_candidate_r2.sv:' in src:src_groups.setdefault(src,[]).append(name)
    early={name for src,names in src_groups.items() if src.endswith('ot_qwen_rom_tile_context_candidate_r2.sv:180.13-182.64') for name in names}
    output_driver={}
    for name,c in net['cells'].items():
        for pin,direction in c.get('port_directions',{}).items():
            if direction=='output':
                for bit in c['connections'][pin]:output_driver[bit]=(name,c)
    def cone_ff(bit,seen=None):
        seen=set() if seen is None else seen
        if bit in seen or bit not in output_driver:return set()
        seen.add(bit);name,c=output_driver[bit]
        if c['type'].startswith('DFF'):return {name}
        if c['type'] in ('ot_rom_4096x266_m8','ot_sram_1r1w_128x256_m1_r2c2'):return set()
        found=set()
        for pin,direction in c.get('port_directions',{}).items():
            if direction=='input':
                for b in c['connections'][pin]:found.update(cone_ff(b,seen))
        return found
    early_links={}
    for bank in range(5):
        name=f'u_tile.u_logic.g_distribution.u_tree.g_bank[{bank}].g_term[0].u_buf'
        c=net['cells'][name];early_links[name]=sorted(cone_ff(c['connections']['A'][0]) & early)
    early_connected=len(early)==5 and all(len(v)==1 for v in early_links.values()) and len({v[0] for v in early_links.values() if v})==5
    endpoints['early_select_source_attributed']=dict(expected=5,actual_FF_count=len(early),term_input_links=early_links,PASS=early_connected)
    macros={n:sum(c['type']==n for c in net['cells'].values()) for n in ('ot_rom_4096x266_m8','ot_sram_1r1w_128x256_m1_r2c2')}
    tree=[name for name,c in net['cells'].items() if '.u_tree.' in name and c['type']=='BUFx4_ASAP7_75t_R']
    ff_counts={kind:sum(c['type']==kind for c in net['cells'].values()) for kind in ('DFFHQNx1_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R')}
    model=json.loads((work/'model.json').read_text())
    passed=all(e['PASS'] for k,e in endpoints.items() if k!='early_select') and list(macros.values())==[10,2] and len(tree)==76 and terminal['mapped_cell_area_um2']<=model['slot']['complete_cell_area_ceiling_um2']
    return dict(status='PASS_COMPLETE_MAPPED_SURVIVAL_ONLY' if passed else 'FAIL_COMPLETE_MAPPED_SURVIVAL_RETAINED',source_commit=pins['commit'],
      raw_mapped_sha256=hashlib.sha256((work/'mapped.json').read_bytes()).hexdigest(),
      source_proc_sha256=hashlib.sha256((work/'source_proc.json').read_bytes()).hexdigest(),
      source_ROM_capture_proof=source_proof,source_attributed_FF_groups=src_groups,macro_counts=macros,ROM_payload_bit_to_direct_capture_FF_D=captures,endpoint_checks=endpoints,
      mapped_FF_counts=ff_counts,source_distribution_buffers=tree,mapped_cell_area_um2=terminal['mapped_cell_area_um2'],
      source_root_reset_producer_installed=False,CTS_installed=False,contextual_SSFF=False,P_and_R_admitted=False)

def check(work):return inspect(work)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise SystemExit('refuse overwrite')
    try:result=check(a.work)
    except Exception as e:result=dict(status='FAIL_COMPLETE_MAPPED_SURVIVAL_RETAINED',reason=str(e),contextual_SSFF=False,P_and_R_admitted=False)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(result['status']);raise SystemExit(0 if result['status'].startswith('PASS') else 1)
