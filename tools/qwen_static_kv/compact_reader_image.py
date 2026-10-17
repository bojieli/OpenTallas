#!/usr/bin/env python3
"""Source-op/resource compiler for compact native read calendars; no traces."""
import hashlib,json,math,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qwen_static_kv.reader_resource_schedule import ROOT,compile_reader,constants
import hdc_qwen_fullshape_isa_w12 as ISA
HBM=1024000;CORE=833334;HSTART=2048;CSTART=2516

def encode(cycles):
    code=[];previous=0
    for c in cycles:
        delta=c-previous
        if delta<1:raise ValueError('fixed output events must increase after cycle0')
        while delta>127:code.append(127);delta-=127
        code.append(128|delta);previous=c
    if len(code)>5*4096:raise ValueError('actual image exceeds five-macro storage; unsupported programme')
    return code

def decode(code):
    result=[];cycle=0
    for b in code:
        if not b&127:raise ValueError('invalid zero delta')
        cycle+=b&127
        if b&128:result.append(cycle)
    return result

def source_contract(program,plan):
    if (plan.get('tp'),plan.get('groups'),plan.get('layers'))!=(8,3072,36):raise ValueError('actual TP8/GT3072/all36 plan required')
    if hashlib.sha256(program).hexdigest()!=plan['files_sha256']['layer_candidate_program.hex']:raise ValueError('actual emitted programme SHA mismatch')
    rows=[ISA.decode_instruction(int(w,16)) for w in program.split()]
    if len(rows)!=25 or [(i,r['me_k'],r['me_wsrc']) for i,r in enumerate(rows) if r['unit']==1 and r['me_wsrc']]!=[(11,128,1)]:raise ValueError('actual sole native PC11/HD128 operation required')
    context=plan['required_core']['KV_elements_per_rank_layer']//(2*128)
    if context!=8192:raise ValueError('actual 8192 context required')
    expected=dict(T_RCD=19,T_RP=16,T_RAS=28,T_RTP=6,T_CCDL=3,T_RRDS=3,T_RRDL=4,T_FAW=15,T_RFC=342,T_RFCPB=196,T_REFI=3808,T_REFIPB=118,T_RREFD=8)
    actual=constants()
    if any(actual.get(k)!=v for k,v in expected.items()):raise ValueError('resource timing changed; compiler must be updated')
    return dict(pc=11,context=context,HD=128,layer_count=36,programme_sha256=hashlib.sha256(program).hexdigest(),native_op=rows[11])

def compile_images(program,plan,out,stages=36,period=1782,v_period=1,phase=137):
    contract=source_contract(program,plan)
    resource=compile_reader(stages,period,v_period=v_period)
    events=resource['events'];hb=[e['cycle'] for e in events]
    puts=[];end=-1
    for b in range(0,len(events),8):
        go=events[b+7]['cycle']+48
        first=max(go+4,end+1);puts.extend(first+i for i in range(8));end=first+7
    # Registered front put -> ring's input pin -> memory/publication: two HBM
    # edges. One extra CORE edge in the expected pin timeline gives the actual
    # ring's two synchronizer edges before its further pin/capture/check stages.
    ho=(HSTART*2+3)*HBM//2;co=phase*1000+CORE//2+(CSTART+1)*CORE
    ce=[(ho+(p+2)*HBM+CORE-co+CORE-1)//CORE for p in puts]
    core_producer=[c-1 for c in ce] # actual output metadata/valid pin register
    code_h,code_c=encode(hb),encode(core_producer)
    assert decode(code_h)==hb and decode(code_c)==core_producer
    if any(a>=b for a,b in zip(ce,ce[1:])):raise ValueError('CORE output collision')
    out.mkdir(parents=True,exist_ok=False)
    for domain,code in [('hbm',code_h),('core',code_c)]:
        padded=code+[0]*((-len(code))%32)
        words=[sum(padded[n+i]<<(8*i) for i in range(32)) for n in range(0,len(padded),32)]
        (out/(domain+'.hex')).write_text(''.join(f'{w:064x}\n' for w in words))
    (out/'hbm_expected.mem').write_text(''.join(f'{c}\n' for c in hb))
    (out/'front_expected.mem').write_text(''.join(f'{c}\n' for c in puts))
    (out/'core_expected.mem').write_text(''.join(f'{c}\n' for c in ce))
    # Real existing128-row landing bounds: source K II1 and two V issuers.
    lifetime=[]
    for stage in range(stages):
        ss=ce[stage*512:(stage+1)*512]
        for kind,begin in [('K',0),('V',256)]:
            offsets=list(range(256)) if kind=='K' else [256*(i//16)+8*(i%16) for i in range(256)]
            lo=max(ss[begin+i]+1-offsets[i] for i in range(256))
            hi=min((ss[begin+i+128]-offsets[i] for i in range(256) if begin+i+128<len(ss)),default=10**12)
            lifetime.append(dict(stage=stage+1,kind=kind,first_request_min=lo,first_request_max=hi,feasible=lo<=hi))
    report=dict(schema='opentallas.qwen-kv-compact-image.v1',status='SOURCE_CONSTRAINED_READ_ONLY_NOT_PRODUCTION',
      production_installable=False,actual_source_contract=contract,resource=resource,
      hbm_bytes=len(code_h),core_bytes=len(code_c),hbm_rows=(len(code_h)+31)//32,core_rows=(len(code_c)+31)//32,
      hbm_stop=stages*period,core_stop=max(ce[-1]+32,(ho+stages*period*HBM-co+CORE-1)//CORE),
      hbm_start_external_index=HSTART,core_start_external_index=CSTART,phase_ps=phase,
      core_metadata_output_pin_edges=1,core_bytecode_predecode_edges=1,
      source_period_core_equivalent=period*HBM/CORE,immutable_link_layer_core=2190,
      frame_vs_link_ratio=period*HBM/(CORE*2190),last_RD_offset_hbm=max(s['last']-(s['stage']-1)*period for s in resource['stages']),
      landing_lifetimes=lifetime,infeasible_landing_kinds=sum(not x['feasible'] for x in lifetime),
      missing=['actual PC11 start/source formatter writes/WDONE visibility','persistent HOST ingest/read/write windows',
        'actual32-group K and two-issuer V consumers and landing lifetimes','all128 physical phi-R/route/reset profiles',
        'actual HOST boot-loader ports/calendar storage placement/TT/FF/DRC and total token cost'],
      qualification='Source read-resource and compact storage mechanism only; fast reader is refused as native production if128-row landing lifetimes fail')
    (out/'image.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'params.svh').write_text(f'localparam integer HBYTES={len(code_h)},CBYTES={len(code_c)},HROWS={(len(code_h)+31)//32},CROWS={(len(code_c)+31)//32},HSTOP={report["hbm_stop"]},CSTOP={report["core_stop"]},NEVENTS={len(hb)},FRAME={period},NSTAGES={stages};\n')
    return report
