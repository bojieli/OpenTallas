"""Simulation-only separation of existing engine interfaces from actual core END.

Keeps the real core FSM/decode/DYN/ROM/native-head bodies. External service ports
are one-to-one existing instance ports, not arithmetic replacements. No service
ready/idle/output is fabricated: caller must supply native or exact SIM_ONLY work.
"""
from pathlib import Path
import argparse, ast, hashlib, json, re
import dsrom_s81_actual_core_end_enroll as E
ROOT=Path(__file__).resolve().parents[1]
SELECT=dict(E.PARAMETERS, X_SU=0,X_SEL=0,X_EG=0,X_HE=1,X_ME=0,X_ATT=0,X_IDX=0,KV_HBM=0,W_HBM=0,
            SUN=16,SUM=8,SW=8,HS=8,HHW=8,HTL=9,HBAW=16,XU_KW=12,QLB=272,ROM_BST=17)
LEAVES=[('me0','ot_hdc_v41_matvec','rtl/hdc/v41/ot_hdc_v41_matvec.sv'),
        ('su','ot_hdc_v41_stream','rtl/hdc/v41/ot_hdc_v41_stream.sv'),
        ('qe','ot_hdc_v41_qe','rtl/hdc/v41/ot_hdc_v41_qe.sv'),
        ('xu','ot_hdc_v41_xu','rtl/hdc/v41/ot_hdc_v41_xu.sv'),
        ('he','ot_hdc_v41x_he_adapt','rtl/hdc/v41x/ot_hdc_v41x_he_adapt.sv')]

def uncomment(s):return re.sub(r'/\*.*?\*/|//[^\n]*','',s,flags=re.S)
def group(s,pos):
    if s[pos]!='(':raise ValueError('expected source parenthesis')
    n=1;i=pos+1
    while n:
        if s[i]=='(':n+=1
        if s[i]==')':n-=1
        i+=1
    return s[pos+1:i-1],i

def named(s):
    result={};pos=0
    while pos<len(s):
        m=re.search(r'\.(\w+)\s*\(',s[pos:])
        if not m:break
        key=m[1];start=pos+m.end()-1;value,pos=group(s,start)
        if key in result:raise ValueError('duplicate source binding '+key)
        result[key]=value.strip()
    return result

def integer(expr,env):
    expr=expr.strip()
    # Selected instance parameter conditional is source MP geometry only.
    if '?' in expr:
        c,t,f=expr.split('?')[0],expr.split('?')[1].split(':')[0],expr.split(':')[-1]
        return integer(t if integer(c,env) else f,env)
    for key in sorted(env,key=len,reverse=True):
        expr=re.sub(r'\b'+re.escape(key)+r'\b',str(env[key]),expr)
    if re.search(r'[^\d\s()+*/%<>=!-]',expr):raise ValueError('nonconstant source expression '+expr)
    node=ast.parse(expr,mode='eval')
    if any(isinstance(n,(ast.Call,ast.Name,ast.Attribute)) for n in ast.walk(node)):raise ValueError('expression')
    return int(eval(compile(node,'source width','eval'),{'__builtins__':{}},{}))

def interface(module,text,overrides):
    clean=uncomment(text)
    m=re.search(r'\bmodule\s+'+module+r'\s*#\s*\(',clean)
    p,end=group(clean,m.end()-1)
    params={}
    for item in p.split(','):
        d=re.fullmatch(r'\s*parameter\s+integer\s+(\w+)\s*=\s*(.*?)\s*',item)
        if not d:raise ValueError('unsupported parameter '+item)
        params[d[1]]=integer(overrides.get(d[1],d[2]),dict(SELECT,**params))
    h,unused=group(clean,clean.index('(',end))
    ports={};direction=None;width=1
    for item in h.split(','):
        d=re.fullmatch(r'\s*(?:(input|output)\s+(?:wire|reg)\s*(\[[^]]+\])?\s*)?(\w+)\s*',item)
        if not d:raise ValueError('unsupported ANSI declarator '+item)
        if d[1]:
            direction=d[1];width=1
            if d[2]:
                hi,lo=d[2][1:-1].split(':');width=integer(hi,params)-integer(lo,params)+1
        if direction is None or width<1:raise ValueError('invalid port '+item)
        ports[d[3]]=(direction,width)
    return ports,params

def prepare(output):
    output=Path(output);E.prepare(output)
    core=output/'native'/E.hook.CORE.name
    text=core.read_text();before=text
    ports=[];manifest=[];dependencies={}
    for role,module,path in LEAVES:
        m=re.search(r'\b'+module+r'\s*#\s*\(',text)
        if not m:raise ValueError('missing selected instance '+module)
        params,end=group(text,m.end()-1)
        inst=re.match(r'\s*(\w+)\s*\(',text[end:])
        connections,end2=group(text,end+inst.end()-1)
        stop=re.match(r'\s*;',text[end2:]);end2+=stop.end()
        pp,values=interface(module,(ROOT/path).read_text(),named(params))
        connections=re.sub(r'`ifdef HDC_MUTATE_RESTORE.*?`else(.*?)`endif',r'\1',connections,flags=re.S)
        cc=named(connections)
        if module=='ot_hdc_v41_qe' and set(pp)-set(cc)=={'qr_issue_ready'} and values['WEIGHT_STALL']==0:
            # Existing parent leaves this input unbound; disabled source branch
            # never observes it. Preserve that source fact, not a forced-ready tie.
            pp.pop('qr_issue_ready')
        if set(pp)!=set(cc):raise ValueError('unbound source ports '+module+str(set(pp)^set(cc)))
        assigns=[]
        for name,(direction,width) in pp.items():
            if name in ('clk','rst_n'):
                if cc[name]!=name:raise ValueError('clock source binding')
                continue
            alias='service_'+role+'_'+name
            topdir='output' if direction=='input' else 'input'
            ports.append(f'    {topdir} wire [{width-1}:0] {alias},')
            if not cc[name]:raise ValueError('empty selected active binding '+alias)
            left,right=(alias,cc[name]) if topdir=='output' else (cc[name],alias)
            assigns.append(f'    assign {left} = {right};')
            manifest.append(dict(role=role,module=module,instance=inst[1],leaf_port=name,
                                 leaf_direction=direction,top_port=alias,top_direction=topdir,
                                 width_bits=width,original_connection=cc[name]))
        text=text[:m.start()]+'// Existing '+module+' instance boundary; caller-owned native/SIM_ONLY service.\n'+'\n'.join(assigns)+text[end2:]
        dependencies[path]=E.sha(ROOT/path)
    text=text.replace('module ot_hdc_core_v41x #(','module ot_dsrom_s81_actual_core_end #(',1)
    text=text.replace(') (\n',') (\n'+'\n'.join(ports)+'\n',1)
    text=text.replace('\nendmodule','\n`ifdef HDC_MUTATE_RESTORE\n    initial $fatal(1,"mutation macro not enrolled for component separation");\n`endif\nendmodule',1)
    guard=' || '.join(f'{name}!={value}' for name,value in SELECT.items())
    text=text.replace('\nendmodule',f'\n    initial if ({guard}) $fatal(1,"selected actual core/control separation parameters changed");\nendmodule',1)
    # Verify source control body unchanged by separation, not a reconstructed FSM.
    begin='    // -- sequencer ';end='    // -- units '
    if text[text.index(begin):text.index(end)]!=before[before.index(begin):before.index(end)]:
        raise ValueError('real control changed')
    dest=output/'native'/'ot_dsrom_s81_actual_core_end.sv';dest.write_text(text)
    core.unlink()  # one enrolled top definition, no duplicate core
    counts={role:{'core_to_service_bits':sum(x['width_bits'] for x in manifest if x['role']==role and x['top_direction']=='output'),
                  'service_to_core_bits':sum(x['width_bits'] for x in manifest if x['role']==role and x['top_direction']=='input')}
            for role,module,path in LEAVES}
    record=dict(status='ACTUAL_CORE_CONTROL_SEPARATED_SIMULATION_BOUNDARIES_NOT_SERVICES',
        parameters=SELECT,interfaces=manifest,boundary_bits=counts,
        source_sha256=dependencies,selected_core_sha256=E.sha(dest),
        added_state_bits=0,added_arithmetic_MACs=0,added_cycles=0,field_instances=0,
        replicas=4,physical_increment_mm2=0,
        physical_scope='Externalization is simulation source partition only, not a new hardware interface/area optimization',
        hardware_transport_area=None,hardware_transport_latency=None,
        service_rule='ready/idle/fault and result/read/write strobes must come from actual native participant or explicit exactSIM_ONLY source service; hold idle low until accepted command and writes/read/replies/ACKs drained; never idle1 with callback debts',
        command_accept='Old go && ready at shared rising edge; preserve core gos in waited and real native ROM/head busy',
        caller_contract='All external input ports must be explicitly driven; named engine ports unchanged width/order; one shared cold reset/edge; no source worker/expected output injection',
        native_result='Existing head_final handshake->EAM1->actual literal S_ISSUE END. C8 retire is caller-owned and is not synthesized here',
        no_run=True,no_native_archive_claim=True)
    (output/'split.json').write_text(json.dumps(record,indent=2)+'\n')
    return record
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',type=Path,required=True)
    r=prepare(p.parse_args().prepare);print(r['status']);print(json.dumps(r['boundary_bits']))
