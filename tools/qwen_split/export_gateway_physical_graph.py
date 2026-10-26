#!/usr/bin/env python3
"""Expose the real nested gateway boundary without counting logical parent aliases as pins."""
import argparse,copy,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from die_port_bind import parse_modules

def export(model):
    path='rtl/qwen_sys/static_schedule_20261014/ot_qwen_a_operand_gateway_v1.sv'
    text=subprocess.check_output(['git','show','d8fdf94f1:'+path],cwd=ROOT,text=True)
    mod=next(m for m in parse_modules(text,path)if m.name=='ot_qwen_a_operand_gateway_v1')
    assert not mod.port_parse_errors
    ports={p:dict(direction=mod.ports[p][0],bits=mod.width(p,mod.env()))for p in mod.order}
    aliases={'su_va_re':'a_re','su_va_addr':'a_addr','su_va_q':'a_q','su_vm_va_re':'vm_re',
        'su_vm_va_addr':'vm_addr','su_vm_va_q':'vm_q',**{p:p for p in('embed_code_re','embed_code_addr','embed_code_q','embed_scale_re','embed_scale_addr','embed_scale_q')}}
    seq=model['nodes']['seq']['ports']
    for p,q in aliases.items():assert seq[p]==ports[q],(p,q)
    edges=copy.deepcopy(model['directed_edges'])
    rewrites=[]
    for e in edges:
        for side in('source','sink'):
            n,p=e[side]
            if n=='seq'and p in aliases:
                q=aliases[p];e[side]=['gateway',q]
                rewrites.append(dict(edge=e['name'],side=side,logical_alias=['seq',p],actual_nested_pin=['gateway',q],bits=e['bits']))
    controls=[('start_idle',1,'start && st == S_IDLE'),('su_go',1,'su_go'),('a_src',1,'a_src'),('token',18,'token'),('tok_r',18,'tok_r')]
    for p,bits,expr in controls:
        assert ports[p]==dict(direction='input',bits=bits)
        edges.append(dict(name='gateway_control_'+p,source=['seq','internal:u_ctrl.'+expr],sink=['gateway',p],bits=bits,
            evidence='Actual leaf input expression in source clock variant; thin-controller physical boundary pin not yet assigned.',
            physical_source_pin=None))
    edges.append(dict(name='gateway_faults',source=['gateway','embed_faults'],sink=['seq','internal:u_ctrl.embed_faults'],bits=64,
        evidence='Actual existing core fault register observes OR(embed_faults); no extra error/data edge.',physical_sink_pin=None))
    roots=dict(model['actual_clock_roots']);assert roots['seq']==3;roots['seq']=2;roots['gateway']=1
    assert sum(roots.values())==957
    activity=subprocess.check_output(['git','show','1680c684e:results/arch/qwen_a_operand_gateway_1015/programme_activity.json'],cwd=ROOT,text=True)
    return dict(schema='opentallas.qwen.gateway-physical-projection.v1',qualified=False,
        logical_top=model['profile']['top_module'],logical_graph_sha256=hashlib.sha256(json.dumps(model,sort_keys=True).encode()).hexdigest(),
        actual_nested_gateway=dict(instance='u_seq.u_seq.u_ctrl.u_a_gateway',master=mod.name,source=path,source_ref='d8fdf94f1',
            source_sha256=hashlib.sha256(text.encode()).hexdigest(),ports=ports,clock_source='seq.ck_gateway',
            physical_home=None,native_pin_timing=None,clock_phase_binding=None),
        physical_root_ownership=roots,logical_parent_pin_aliases_removed=rewrites,directed_edges=edges,directed_edge_count=len(edges),
        controller_interior_boundaries='Named existing expressions/nets are explicit unresolved physical cut endpoints, not invented source ports.',
        activity_source_ref='1680c684e',activity=json.loads(activity),
        limits=['All original source parent aliases remain logical wires; never place/count them as another physical interface.',
            'Real gateway still includes combinational VM return passthrough and decoding; physical preflight pending.',
            'Possible removal of unobservable nonembedding return branch requires separate complete selected-SU proof.',
            'No geometry distances/rates/globalcycles or registered-face qualification inferred.'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.write_text(json.dumps(export(json.loads(a.model.read_text())),indent=2)+'\n')
if __name__=='__main__':main()
