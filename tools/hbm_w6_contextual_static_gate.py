#!/usr/bin/env python3
"""Short source-qualified frontend/full32 elaboration checks, never synthesis/P&R."""
import argparse,json,subprocess,time
from pathlib import Path
import hbm_w6_component_gate as G

def execute(out,source):
    out.mkdir(parents=True,exist_ok=False)
    v=dict(verdict='FAIL_CONTEXT_STATIC_PREPARATION',physical=False,P_and_R_launched=False,source_commit=source)
    try:
        p=json.loads(G.PROPOSAL.read_text());pre=G.preflight(p,source,2);G.write_new(out/'preflight.json',pre)
        base=G.ROOT/'results/uarch/hbm_W6_contextual_plan_20261003/r1'
        plan=json.loads((base/'selected_plan.json').read_text())
        for path,h in plan['sourcepins'].items():G.require(G.sha(G.ROOT/path)==h,'context input '+path)
        for key,path in [('plan_tool_sha256','tools/hbm_w6_contextual_plan.py'),('source_adapter_sha256','tools/hbm_w6_physical_source_adapter.py')]:
            G.require(G.sha(G.ROOT/path)==plan[key],'context source '+path)
        representation=json.loads((base/'prepared_source/source_representation.json').read_text())
        flat=base/'prepared_source/w6_literal_inline.sv';top=base/'prepared_source/w6_full32_context.sv'
        G.require(G.sha(flat)==representation['literal_inline_sha256'] and G.sha(top)==representation['full32_top_sha256'],'exact selected representation')
        G.write_new(out/'sourcepins.json',dict(plan_sha256=G.sha(base/'selected_plan.json'),runner_sha256=G.sha(Path(__file__)),
                    flat_sha256=G.sha(flat),full32top_sha256=G.sha(top),proposal_sha256=G.sha(G.PROPOSAL)))
        jobs=[('flat_compile',['/usr/bin/iverilog','-g2012','-s','tb_w6_fullwidth_fence','-o',str(out/'flat.vvp'),str(G.ROOT/G.RTL[0]),str(flat),str(G.ROOT/G.RTL[2])]),
              ('flat_simulation',['/usr/bin/vvp',str(out/'flat.vvp')]),
              ('full32_elaboration',['/usr/bin/iverilog','-g2012','-s','ot_gpu_w6_full32_context','-Pot_gpu_w6_full32_context.ENABLE=1','-o',str(out/'full32.vvp'),str(flat),str(top)])]
        for phase,argv in jobs:
            start=time.monotonic()
            with (out/(phase+'.log')).open('xb') as log:r=subprocess.run(argv,cwd=G.ROOT,stdout=log,stderr=subprocess.STDOUT)
            G.write_new(out/(phase+'-end.json'),dict(argv=argv,returncode=r.returncode,wall_seconds=time.monotonic()-start,log_sha256=G.sha(out/(phase+'.log'))))
            G.require(r.returncode==0,phase+' failed')
        text=(out/'flat_simulation.log').read_text();trace=G.verify_trace(text)
        archived=G.ROOT/'results/rtl/hbm_W6_local_component_20261003/r3_expanded_component_pass/simulation.log'
        G.require((out/'flat_simulation.log').read_bytes()==archived.read_bytes(),'literal frontend trace byte-identical to original611 assertions/157 accepts')
        G.write_new(out/'trace_review.json',trace)
        v.update(verdict='PASS_LITERAL_FRONTEND_AND_FULL32_ELABORATION_ONLY',assertions=trace['checks'],acceptances=trace['accepted'],
                 flat_binary_sha256=G.sha(out/'flat.vvp'),full32_elaboration_binary_sha256=G.sha(out/'full32.vvp'),
                 source_representation=representation,SSFF_qualified=False)
    except Exception as exc:v['failure']=str(exc)
    G.write_new(out/'verdict.json',v)
    return 0 if v['verdict'].startswith('PASS_') else 1
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--source-commit',required=True);a=p.parse_args();raise SystemExit(execute(a.out,a.source_commit))
