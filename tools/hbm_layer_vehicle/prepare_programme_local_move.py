#!/usr/bin/env python3
"""Disabled exact SOURCE13 collar+r10 reparent event; no physical stage claim.

Reads actual (optionally already composed) wrappers and their connectivity top.
Keeps the two old command/IO face registers locally, all producer bodies and
native fault captures. Adds explicit configuration/reset and status transports.
No source/profile/plan is activated and no programme dates are invented.
"""
import argparse, hashlib, json, re
from pathlib import Path

HUBS={'NW':'hbm_arch_q_hub__q_hub_nw','NE':'hbm_arch_q_hub__q_hub_ne'}
BODS={'NW':'hbm_arch_q_b113','NE':'hbm_arch_q_b113__physical_v1'}
CTRL='xi_u_sfucore_Q_ctl_u_core_procdff_66941_D'
IO='xi_u_sfucore_Q_ctl_u_core_procdff_66936_D'
FAULT='xo_u_sfucore_Q_ctl_u_core_procdff_66891_Q'
HFAULT='xi_u_col_sfu_Q_c_fault'
OUTS=['xo_u_sfup_Q_q1_compiler_control','xo_u_sfup_Q_q1_io_word']
STATUS=['w_u_col_sfu_Q_active','w_u_col_sfu_Q_ready','w_u_col_sfu_Q_fault',
        'w_u_sfup_Q_q1_programme_done','w_u_sfup_Q_q1_fault']
FORWARD=[('cfg_v',1,'w_u_hleaf_Q_b_cfg_v[0]'),('cfg_target',8,'w_u_hleaf_Q_b_cfg_target[7:0]'),
         ('cfg_addr',12,'w_u_hleaf_Q_b_cfg_addr[11:0]'),('cfg_data',256,'w_u_hleaf_Q_b_cfg_data[255:0]'),
         ('desc_v',1,'w_u_hleaf_Q_b_desc_v[0]'),('launch_v',1,'w_u_hleaf_Q_b_launch_v[0]'),
         ('old_hub_rst_n',1,'rst_n'),('old_r10_rst_n',1,'rst_n_t352')]


def close_at(s, pos):
    """Match parentheses while ignoring Verilog comments, strings and attributes."""
    assert s[pos]=='('
    depth=0;i=pos
    while i<len(s):
        if s.startswith('//',i):
            j=s.find('\n',i);i=len(s) if j<0 else j;continue
        if s.startswith('/*',i):
            j=s.find('*/',i+2);assert j>=0;i=j+2;continue
        if s[i]=='"':
            i+=1
            while i<len(s):
                if s[i]=='\\':i+=2;continue
                if s[i]=='"':i+=1;break
                i+=1
            continue
        if s[i]=='(':depth+=1
        elif s[i]==')':
            depth-=1
            if depth==0:return i
        i+=1
    raise ValueError('unclosed Verilog parentheses')


def call(s, name):
    hits=list(re.finditer(r'\b'+re.escape(name)+r'\s*\(',s))
    if len(hits)!=1:raise ValueError(f'{name}: expected one actual instance, got{len(hits)}')
    m=hits[0];p=s.index('(',m.start());q=close_at(s,p)
    end=q+1
    while s[end].isspace():end+=1
    if s[end]!=';':raise ValueError('instance terminator missing')
    start=s.rfind('\n',0,m.start())+1
    return start,end+1,s[start:end+1]


def expression_ports(block):
    result={}
    for m in re.finditer(r'\.(\w+)\s*\(',block):
        p=block.index('(',m.start());q=close_at(block,p)
        if m[1] in result:raise ValueError('duplicate named port')
        result[m[1]]=block[p+1:q].strip()
    return result


def port(block, name, value):
    hits=list(re.finditer(r'\.'+re.escape(name)+r'\s*\(',block))
    if len(hits)!=1:raise ValueError('missing or duplicate port '+name)
    p=block.index('(',hits[0].start());q=close_at(block,p)
    return block[:p+1]+value+block[q:]


def header(s):
    m=re.search(r'\bmodule\s+\w+\s*',s);p=m.end()
    if s[p]=='#':
        p=s.index('(',p);p=close_at(s,p)+1
        while s[p].isspace():p+=1
    assert s[p]=='('
    return p,close_at(s,p)


def change_header(s, remove, additions):
    p,q=header(s);h=s[p+1:q]
    for n in remove:
        pattern=r'^\s*(?:input|output)\s+wire\s+(?:\[[^\]]+\]\s*)?'+re.escape(n)+r'\s*,?[^\n]*\n'
        h,count=re.subn(pattern,'',h,flags=re.M)
        if count!=1:raise ValueError('actual ANSI port missing '+n)
    h=h.rstrip();h=re.sub(r',\s*$','',h)
    h+=',\n'+',\n'.join('    '+a for a in additions)+'\n'
    return s[:p+1]+h+s[q:]


def replace_call(s,name,new):
    a,b,_=call(s,name);return s[:a]+new+s[b:]


def add_body(s, body):
    m=list(re.finditer(r'\bendmodule\b',s))
    if len(m)!=1:raise ValueError('one selected module required')
    return s[:m[0].start()]+'\n'+body+'\n'+s[m[0].start():]


def st(name,w,d,ea,q,eq,rst='rst_n',clk='clk'):
    return f'    ot_dp_st #(.W({w})) {name} (.clk({clk}), .rst_n({rst}), .d({d}), .ea({ea}), .q({q}), .eq({eq}));'


def move_pair(hub, bod, region):
    if 'u_prog_move_ingress_o' in hub:raise ValueError('event already applied')
    _,_,collar=call(hub,'u_u_col_sfu_Q');_,_,r10=call(hub,'u_u_sfup_Q_q1')
    cp=expression_ports(collar);rp=expression_ports(r10)
    if cp.get('clk')!='clk' or cp.get('clk_in')!='clk' or rp.get('clk')!='clk':raise ValueError('selected native producer clock changed')
    if rp.get('PAGE_AW')!='1' or rp.get('rst_n')!=('rst_n_t352' if region=='NW' else 'rst_n_t350'):raise ValueError('selected r10 profile changed')
    if cp.get('rst_n')!='rst_n' or cp.get('tgt')!='S_u_col_sfu_Q_tgt[7:0]':raise ValueError('selected collar reset/target changed')
    for n,w,x in FORWARD[:6]:
        if cp[n]!=x:raise ValueError('selected collar ingress changed '+n)
    target=118 if region=='NW' else 119
    forward=FORWARD[:-1]+[('old_r10_rst_n',1,rp['rst_n'])]
    if not re.search(r'S_u_col_sfu_Q_tgt\s*=\s*8\x27b'+format(target,'08b'),hub):raise ValueError('frozen target default changed')
    if 'w_u_col_sfu_Q_' in bod or 'w_u_sfup_Q_q1_' in bod:raise ValueError('destination already contains programme producers')
    decls=re.findall(r'^\s*wire\s+\[[^\]]+\]\s+(?:w_u_col_sfu_Q_\w+|w_u_sfup_Q_q1_\w+)\s*;',hub,re.M)
    if not decls:raise ValueError('actual producer declarations absent')
    hub=replace_call(hub,'u_u_col_sfu_Q','');hub=replace_call(hub,'u_u_sfup_Q_q1','')
    moved=[]
    for output,w in zip(OUTS,(1742,471)):
        _,_,face=call(hub,'u_bout_'+output);hub=replace_call(hub,'u_bout_'+output,'')
        if expression_ports(face).get('W')!=str(w):raise ValueError('actual command/IO face width changed')
        face=port(face,'rst_n','prog_old_hub_rst_n');face=port(face,'ea','prog_old_hub_rst_n');moved.append(face)
    _,_,faultbin=call(hub,'u_bin_'+HFAULT);hub=replace_call(hub,'u_bin_'+HFAULT,'')
    faultbin=port(faultbin,'d',FAULT+'[0:0]');faultbin=port(faultbin,'ea',FAULT+'[1]');faultbin=port(faultbin,'rst_n','prog_old_hub_rst_n')
    # The old private fault destination capture moves too; no silent edge deletion.
    qdecls=[]
    for n in [HFAULT+'_q',HFAULT+'_eq']:
        m=re.search(r'^\s*wire(?:\s+\[[^\]]+\])?\s+'+n+r'\s*;',hub,re.M)
        if not m:raise ValueError('actual fault capture declaration absent')
        qdecls.append(m[0])
    for old,out,w in [(CTRL,OUTS[0],1742),(IO,OUTS[1],471)]:
        _,_,binface=call(bod,'u_bin_'+old)
        if expression_ports(binface).get('W')!=str(w):raise ValueError('actual command/IO capture width changed')
        binface=port(binface,'d',out+f'[{w-1}:0]');binface=port(binface,'ea',out+f'[{w}]');bod=replace_call(bod,'u_bin_'+old,binface)
    hub=change_header(hub,OUTS+[HFAULT],['output wire [281:0] prog_move_ingress_o','input wire [5:0] prog_move_status_i'])
    bod=change_header(bod,[CTRL,IO,FAULT],['input wire [281:0] prog_move_ingress_i','output wire [5:0] prog_move_status_o'])
    # Existing source identities become local wires only in the explicit changed ABI.
    local=['    wire [1742:0] '+OUTS[0]+';','    wire [471:0] '+OUTS[1]+';','    wire [1:0] '+FAULT+';']+decls+qdecls
    local+=['    wire [280:0] prog_ingress_q;','    wire prog_ingress_eq;',
            '    wire prog_old_hub_rst_n = prog_ingress_eq && prog_ingress_q[279];',
            '    wire prog_old_r10_rst_n = prog_ingress_eq && prog_ingress_q[280];',
            st('u_prog_move_ingress_i',281,'prog_move_ingress_i[280:0]','prog_move_ingress_i[281]','prog_ingress_q','prog_ingress_eq')]
    shift=0;mapping=[]
    for name,width,expr in forward:
        sel=f'prog_ingress_q[{shift+width-1}:{shift}]';mapping.append(dict(field=name,lsb=shift,width=width,actual_source=expr))
        if name in cp:
            if name in ('cfg_v','desc_v','launch_v'):sel='(prog_ingress_eq && '+sel+')'
            collar=port(collar,name,sel)
        shift+=width
    assert shift==281
    collar=port(collar,'rst_n','prog_old_hub_rst_n');collar=port(collar,'tgt',f"8'd{target}")
    r10=port(r10,'rst_n','prog_old_r10_rst_n')
    local+=[collar,r10,*moved,faultbin,
            st('u_prog_move_status_o',5,'{'+', '.join(reversed(STATUS))+'}','rst_n','prog_move_status_o[4:0]','prog_move_status_o[5]')]
    bod=add_body(bod,'\n'.join(local))
    # Only actual used status wires remain driven in the old hub. Unused declarations are harmless and unobserved.
    hb=['    wire [4:0] prog_status_q;','    wire prog_status_eq;',
        st('u_prog_move_status_i',5,'prog_move_status_i[4:0]','prog_move_status_i[5]','prog_status_q','prog_status_eq'),
        st('u_prog_move_ingress_o',281,'{'+', '.join(x for _,_,x in reversed(forward))+'}','rst_n','prog_move_ingress_o[280:0]','prog_move_ingress_o[281]')]
    hb+=['    assign '+name+f' = prog_status_q[{i}];' for i,name in enumerate(STATUS)]
    hub=add_body(hub,'\n'.join(hb))
    return hub,bod,dict(region=region,target=target,forward_fields=mapping,return_status=STATUS,old_control_IO_faces_preserved=4,old_fault_faces_preserved=2)


def top_pair(top,region,stages,status_stages):
    _,_,hub=call(top,region+'_hub');_,_,bod=call(top,region+'_b113')
    hp=expression_ports(hub);bp=expression_ports(bod)
    if hp['clk']!=bp['clk'] or hp['clk']!='clk_stream':raise ValueError('actual parent core clock identity differs')
    if 'arst_n' not in hp or 'arst_n' not in bp:raise ValueError('actual regional reset identities absent')
    target=118 if region=='NW' else 119
    if hp.get('S_u_col_sfu_Q_tgt')!="8'b"+format(target,'08b'):raise ValueError('actual bound top target differs')
    for portname in OUTS+[HFAULT]:
        hub=drop_port(hub,portname)
    for portname in [CTRL,IO,FAULT]:bod=drop_port(bod,portname)
    lines=[]
    def path(tag,width,n):
        names=[f'prog_move_{region}_{tag}_{i}' for i in range(n-1)]
        for name in names:lines.append(f'    wire [{width}:0] {name};')
        for i in range(1,n-1):
            lines.append(st(f'u_prog_move_{region}_{tag}_{i}',width,names[i-1]+f'[{width-1}:0]',names[i-1]+f'[{width}]',names[i]+f'[{width-1}:0]',names[i]+f'[{width}]',rst='rst_n',clk=hp['clk']))
        return names[0],names[-1]
    a,b=path('ingress',281,stages);c,d=path('status',5,status_stages)
    hub=append_ports(hub,{'prog_move_ingress_o':a,'prog_move_status_i':d})
    bod=append_ports(bod,{'prog_move_ingress_i':b,'prog_move_status_o':c})
    top=replace_call(top,region+'_hub',hub);top=replace_call(top,region+'_b113',bod)
    return add_body(top,'\n'.join(lines))


def drop_port(block,name):
    hits=list(re.finditer(r'\.'+re.escape(name)+r'\s*\(',block))
    if len(hits)!=1:raise ValueError('actual top port absent '+name)
    a=hits[0].start();p=block.index('(',a);b=close_at(block,p)+1
    while b<len(block) and block[b].isspace():b+=1
    if block[b:b+1]==',':b+=1
    else:
        q=a-1
        while block[q].isspace():q-=1
        if block[q]!=',':raise ValueError('cannot remove final connection')
        a=q
    return block[:a]+block[b:]


def append_ports(block,ports):
    # The final matching parenthesis belongs to the actual instance port list.
    name=re.search(r'\b(\w+)\s*\(\s*\.',block)
    if not name:raise ValueError('named instance port list absent')
    p=block.index('(',name.start());q=close_at(block,p)
    text=block[p+1:q].rstrip();text=re.sub(r',\s*$','',text)
    return block[:p+1]+text+',\n'+',\n'.join(f'        .{k}({v})'for k,v in ports.items())+'\n    '+block[q:]


def connection_guard(top, texts):
    rows=[]
    for region in ('NW','NE'):
        for mod,inst in [(HUBS[region],region+'_hub'),(BODS[region],region+'_b113')]:
            text=texts[mod];p,q=header(text)
            declared=set(re.findall(r'\b(?:input|output)\s+(?:wire|reg)\s+(?:\[[^\]]+\]\s*)?(\w+)',text[p:q]))
            _,_,block=call(top,inst);m=re.search(r'\b'+inst+r'\s*\(',block);pos=block.index('(',m.start())
            actual=set(expression_ports(block[pos:]))
            if declared!=actual:raise ValueError('changed actual parent port graph differs '+mod+':'+str((sorted(declared-actual),sorted(actual-declared))))
            rows.append(dict(module=mod,ports=len(declared),connections=len(actual),missing=[],extra=[]))
    return rows


def main():
    p=argparse.ArgumentParser();p.add_argument('--source-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--ingress-stages',type=int,required=True);p.add_argument('--status-stages',type=int,default=2);a=p.parse_args()
    if min(a.ingress_stages,a.status_stages)<2:raise ValueError('both real source and destination native captures are required')
    if a.out.exists() and any(a.out.iterdir()):raise ValueError('fresh immutable output required')
    primitive=a.source_dir/'ot_dp_st.sv'
    primitive_sha=hashlib.sha256(primitive.read_bytes()).hexdigest()
    if primitive_sha!='d3d3f04be300eebdf3a00476647c86a0181bbb6a9a77ef238d5a348c18bffba2':raise ValueError('exact selected delay primitive changed')
    a.out.mkdir(parents=True,exist_ok=True);topname='hbm_arch_B2o_bound_top';top=(a.source_dir/(topname+'.sv')).read_text();receipts=[];texts={};inputs=[dict(module=topname,sha256=hashlib.sha256(top.encode()).hexdigest())]
    for region in ('NW','NE'):
        hn,bn=HUBS[region],BODS[region];h=(a.source_dir/(hn+'.sv')).read_text();b=(a.source_dir/(bn+'.sv')).read_text()
        inputs.extend([dict(module=n,sha256=hashlib.sha256(t.encode()).hexdigest())for n,t in [(hn,h),(bn,b)]])
        h,b,record=move_pair(h,b,region);receipts.append(record);texts[hn]=h;texts[bn]=b
        (a.out/(hn+'.sv')).write_text(h);(a.out/(bn+'.sv')).write_text(b);top=top_pair(top,region,a.ingress_stages,a.status_stages)
    guards=connection_guard(top,texts)
    (a.out/(topname+'.sv')).write_text(top)
    (a.out/'connection_guard.json').write_text(json.dumps(guards,indent=2)+'\n')
    result=dict(status='DISABLED_SOURCE_EVENT_NOT_PHYSICALLY_QUALIFIED',enabled=False,SOURCE13_mutated=False,physical_ingress_stages=None,prototype_ingress_stages=a.ingress_stages,prototype_status_stages=a.status_stages,added_native_FF_per_lane=282*a.ingress_stages+6*a.status_stages,added_native_FF_paired=2*(282*a.ingress_stages+6*a.status_stages),added_ingress_edges=a.ingress_stages,added_observer_return_edges=a.status_stages,clock_ps=833,exact_physical_latency=None,new_ingress_payload_bits=281,real_CFG_desc_launch_bits=279,actual_distinct_reset_identity_bits=2,status_bits=5,source_inputs=inputs,records=receipts,cost_baseline='Versus exact SOURCE13: producer state and old wide/fault face banks move, not recreated. Existing absolute parent FF/pin/clock budgets remain unjoined.',launch_latency_note='Ingress I is configuration/descriptor/launch arrival latency. It does not add I to every L730 traversal or every resident programme opcode; actual VM0/COPY/observer issue and fence dates still need model qualification.',physical_new_banks='UNPLACED; source/clock/reset/START/PG/model and parent child views required',native_delay_primitive='ot_dp_st exact selected unchanged',native_delay_sha256=primitive_sha,regional_reset_note='Actual hub and B113 arst_n differ; original native faces retain their respective delivered resets. Two actual hub reset identities are retimed as ingress bits. Any prototype top relay uses the actual top rst_n; physical regional reset/66/START joins remain unqualified.',qualification='No whole-move miter or native programme proof claimed. Actual reset delivery is retimed, epoch gates strobe and reset release; genuine66/START and reset-pending-transaction controls still required.',service_calendar='Actual VM0/COPY/observer/fault and completion dates must account for new ingress/status edges; no programme dates invented',generator='prepare_programme_local_move.py')
    (a.out/'event.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ('source_inputs','records')}))

if __name__=='__main__':main()
