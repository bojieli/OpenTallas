#!/usr/bin/env python3
"""Checked native SU ROM installation and actual dispatcher pin driver.

Native ROM PCs never become command-processor/SM kernel entry PCs. ROM
installation is elaboration readmemh; query operand installation is an actual
finite VM provider responsibility. No arithmetic/completion is manufactured.
"""
import argparse,copy,hashlib,json
from pathlib import Path

ALIASES={'prenorm':'rmsnorm4096','qknorm':'qknorm128','rope':'rope128',
         'round_q':'rope128','swiglu':'swiglu3072','softmax':'softmax8x8224'}

def integer(x,limit,name):
    if type(x)!=int or not 0<=x<limit:raise ValueError(name)
    return x

def owner(token,position,job,generation):
    integer(token,151936,'token18 vocabulary');integer(position,1<<20,'position20')
    integer(job,1<<32,'job32');integer(generation,16,'generation4')
    return (position<<54)|(token<<36)|(generation<<32)|job

def install(rom,dispatcher,provider):
    rom=Path(rom).resolve();m=json.loads((rom/'manifest.json').read_text())
    if (m['N'],m['M'],m['word_bits'],m['slots'],m['capacity'])!=(256,64,690,42,8224):
        raise ValueError('native geometry')
    params={'ENABLE':1};pins={}
    for name in ('Q0','Q1','Q2','Q3','META'):
        path=rom/(name+'.hex');data=path.read_bytes()
        if hashlib.sha256(data).hexdigest()!=m['ROM_sha256'][path.name]:raise ValueError('ROM source pin '+name)
        values=[int(x,16) for x in data.split()]
        if len(values)!=42 or any(v>=1<<(42 if name=='META' else 690) for v in values):raise ValueError('ROM extent')
        for pc,v in enumerate(values):
            if name=='META' and v!=m['entries'][pc]['metadata']:raise ValueError('metadata mismatch')
        params[name]=str(path);pins[name]=m['ROM_sha256'][path.name]
    sources={}
    for name,path in [('dispatcher',dispatcher),('provider',provider)]:
        p=Path(path).resolve();s=p.read_text();sources[name]=dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        if name=='dispatcher' and ('OWNER_W' not in s or 'launch_queries' not in s or 'cmd_valid_length' not in s):raise ValueError('dispatcher ABI')
        if name=='provider' and any(('parameter '+q+'=') not in s and q+'=""' not in s for q in ('Q0','Q1','Q2','Q3','META')):raise ValueError('ROM provider ABI')
    manifest_pin=hashlib.sha256((rom/'manifest.json').read_bytes()).hexdigest()
    m=copy.deepcopy(m)
    for entry in m['entries']:entry.pop('fields',None)
    return dict(schema='opentallas.qwen.native_su_install.v1',manifest=m,manifest_sha256=manifest_pin,rom_parameters=params,
        dispatcher_parameters=dict(ENABLE=1,OWNER_W=74,CAPACITY=8224),ROM_sha256=pins,source_pins=sources,
        install_kind='immutable elaboration readmemh; reset before launch',
        production_default_enabled=False,actual_quarter_RTL=False,full_decode_executable=False,
        VM=dict(words=262144,QID='tag[15:14]=quarter; tag[13:0]=transaction; no address offset',
            readonly_zero_word=262143,readonly_zero_bits=0,query_slots='sequential replay in shared VM',
            scores=dict(base=0,head_stride=8224,quarter_stride=16448),
            exp=dict(base=65792,head_stride=8224,quarter_stride=16448),
            publication=dict(base=131584,head_stride=8224,quarter_stride=16448),
            denominator=dict(base=210144,quarter_stride=2),
            rms=dict(input=229376,gain=237568,scalar=[220000+q for q in range(4)],output_ranges=[[q*1024,(q+1)*1024] for q in range(4)]),
            qknorm=dict(input=0,Qgain=8192,Kgain=8320,output=16384),
            rope=dict(input=16384,cos=4096,signed_sin=4224,output=0),
            swiglu=dict(gate=0,up=4096,output=8192)),
        model=dict(duplicate_full_RMS_reductions=4,extra_square_elements=12288,rsqrts=4,measured_cycles=None))

def descriptor(contract,kernel):
    if kernel not in ALIASES:raise ValueError('unresolved native stage: '+kernel)
    m=contract['manifest'];s=dict(m['stages'][ALIASES[kernel]])
    # The graph has a distinct Q rounding boundary; use the actual compiled
    # final RoPE word separately instead of silently fusing away a graph edge.
    if kernel=='rope':s['count']-=1
    if kernel=='round_q':s=dict(pc=s['pc']+s['count']-1,count=1)
    pcs=list(range(s['pc'],s['pc']+s['count']))
    if not pcs or any(not m['entries'][p]['metadata']>>41 for p in pcs):raise ValueError('invalid ROM entry')
    return dict(unit='SU',dispatch='ot_qwen_r25_su_dispatch',owner_bits=74,
        ROM_PC=s['pc'],ROM_count=s['count'],ROM_metadata=[m['entries'][p]['metadata'] for p in pcs],
        ROM_sha256=contract['ROM_sha256'],source_pins=contract['source_pins'],
        dispatch_resolved=True,CP_kernel_entry_resolved=False,arithmetic_RTL_qualified=False,
        provider_visibility_required=True)

def resolve(program,contract):
    p=copy.deepcopy(program);resolved=set();missing=set()
    for b in p['batches']:
        for op in b['operations']:
            if op['unit']=='SU' and op['kernel'] in ALIASES:
                op['production_entry']=descriptor(contract,op['kernel']);resolved.add(op['kernel'])
            else:missing.add(op['kernel'])
    p['native_SU_install']=contract;p['resolved_native_SU_entries']=sorted(resolved)
    p['missing_production_entries']=sorted(missing)
    p['full_decode_executable']=False
    return p

def launch(contract,kernel,*,token,position,job,generation,queries=1):
    own=owner(token,position,job,generation)
    if type(queries)!=int or queries not in (1,4) or position+queries>8224:raise ValueError('query extent')
    d=descriptor(contract,kernel)
    return dict(launch_v=1,launch_checked=3,launch_owner=own,launch_pc=d['ROM_PC'],
                launch_count=d['ROM_count'],launch_position=position,launch_queries=queries)

class NativeSUHost:
    """One actual dispatcher stage; provider gates every query before ROM use.

    Driver stage_query returns true only after operand/gain/position constants
    have write acknowledgments and same-sector visibility, with VM exclusively
    leased. Driver must gate ROM request acceptance during query replacement;
    dispatcher has no per-query operand-install handshake. finished_v retires
    only the single admitted launch, so exclusivity is mandatory.
    """
    def __init__(self,pins,contract,kernel,**identity):
        self.pins=pins;self.contract=contract;self.kernel=kernel
        self.request=launch(contract,kernel,**identity);self.state='PREPARE'
    def step(self):
        if self.state=='DONE':return self.state
        if self.state=='FAILED':raise RuntimeError('terminal native host failure')
        s=self.pins.snapshot();p=dict(self.request,launch_v=0,finished_rdy=0)
        try:
            if s['fault']:raise RuntimeError('actual native dispatcher fault')
            if self.state=='PREPARE':
                if s['finished_v']:raise RuntimeError('stale native completion')
                receipt=self.pins.stage_query(self.contract,self.kernel,self.request)
                if receipt is not None:
                    if not isinstance(receipt,dict) or receipt.get('owner')!=self.request['launch_owner'] or receipt.get('queries')!=self.request['launch_queries'] or not receipt.get('visibility_checked') or not receipt.get('exclusive_dispatch'):
                        raise RuntimeError('unqualified VM operand installation receipt')
                    if self.request['launch_queries']==4 and not receipt.get('query_gate_installed'):
                        raise RuntimeError('sequential query ROM gate missing')
                    self.state='LAUNCH'
            elif self.state=='LAUNCH':
                if s['finished_v']:raise RuntimeError('completion before launch')
                p['launch_v']=1
                if s['launch_rdy']:self.state='WAIT'
            elif self.state=='WAIT' and s['finished_v']:
                p['finished_rdy']=1;self.state='DONE'
            self.pins.drive(p);self.pins.tick()
        except Exception:
            self.state='FAILED';raise
        return self.state

def main():
    a=argparse.ArgumentParser();a.add_argument('--rom',required=True,type=Path)
    a.add_argument('--dispatcher',required=True,type=Path);a.add_argument('--provider',required=True,type=Path)
    a.add_argument('--program',type=Path);a.add_argument('--out',required=True,type=Path);x=a.parse_args()
    c=install(x.rom,x.dispatcher,x.provider)
    result=resolve(json.loads(x.program.read_text()),c) if x.program else c
    x.out.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
