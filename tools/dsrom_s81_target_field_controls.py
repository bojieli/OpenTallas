"""Emit full canonical QAL/KVAL controls for borrowed native field participants.

No allocator, payload, numerical output, new return tree or model compilation.
The existing stream emitter's stream-only body and actual phase_cfg are reused.
"""
import argparse
import ast
import hashlib
import inspect
import json
from pathlib import Path
from types import SimpleNamespace


def native_stream(matrix, *, fp32_output=False):
    import v41_die_images_w17w10 as fast
    source = inspect.getsource(fast.add_phase)
    body = ast.parse(source).body[0].body
    def assignment(node, name):
        return isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
    start = next(i for i,n in enumerate(body) if assignment(n,'cap'))
    stop = next(i for i,n in enumerate(body) if assignment(n,'sbase'))
    rounds, demand, by_pair = {}, {}, {}
    for si,pair,first,count,stride,base,words in matrix['plans']:
        e0,elems = matrix['segments'][si]
        for j in range(count):
            by_pair.setdefault(pair,[]).append(dict(fmt=matrix['format'],e0=e0,
                elems=elems,row=first+j*stride,tensor=matrix['tensor']))
    for pair,segments in by_pair.items():
        for i,u,b,h in fast.S.element_order(segments):
            sg = segments[i]
            q = (u-fast.S.unit_range(sg['fmt'],sg['e0'],sg['elems'])[0])//fast.S.IL
            rounds.setdefault((q,b),set()).add(u)
            demand[q,b,pair] = demand.get((q,b,pair),0)+1
    bf = matrix['format']=='bf16'
    ns = dict(vars(fast),bf=bf,K=matrix['K'],
              field=SimpleNamespace(add_latency=8,fast=True),rounds=rounds,demand=demand)
    exec(compile(ast.Module(body=body[start:stop],type_ignores=[]),
                 inspect.getsourcefile(fast.add_phase),'exec'),ns)
    beats = ns['beats']
    phrom = fast.phase_words(dict(bf=bf,K=matrix['K'],nbeat=len(beats),sbase=0,
        nrows=matrix['rows'],fmt_fp32=[fp32_output,fp32_output],rsplit=0))
    return phrom,beats,hashlib.sha256(source.encode()).hexdigest()


def emit_native_phase_controls(execution,node,rank,out,connectivity,*,
                               fragment_index=0,expert_ids=None):
    """Source-exact controls for any selected QE/weight-ME fragment.

    Dynamic EIDs must be the caller's captured native tuple. This function
    does not select experts, encode weights, fork a source reader or grant GO.
    Partial-K pair plans remain explicit; no complete-K branch is invented.
    """
    from dsrom_s81_phase_capture_join import emitted_phase_profile
    resolved=execution.source.resolve(node,rank,expert_ids=expert_ids)
    dispatch=execution.dispatch(node,rank,expert_ids=expert_ids)
    if type(fragment_index) is not int or not 0<=fragment_index<len(resolved['fragments']):
        raise ValueError('actual selected fragment index required')
    if len(resolved['fragments'])!=len(dispatch['fragments']):
        raise ValueError('source fragment/dispatch coverage differs')
    matrix=resolved['fragments'][fragment_index]['matrix']
    fragment=dispatch['fragments'][fragment_index]
    instruction=fragment['instruction']
    me=instruction['unit']==1 and instruction.get('me_wsrc')==0
    qe=instruction['unit']==3 and instruction.get('qe_mode',0)==0
    if not (me or qe) or (matrix['format']=='bf16')!=me:
        raise ValueError('actual weight ME or mode0 QE controls required')
    fp32=not instruction.get('me_round',0) if me else bool(instruction.get('qe_unrounded',0))
    phrom,beats,stream_pin=native_stream(matrix,fp32_output=fp32)
    profile=emitted_phase_profile(execution.stage_join,connectivity,
        stage=fragment['stage'],rank=rank,phase=fragment['phase'],positions=1,
        key=fragment['key'],ME=me)
    if profile['source_matrix_sha256']!=fragment['source_matrix_sha256']:
        raise ValueError('actual capture profile/source dispatch differs')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    (out/'spine_phase.hex').write_text(''.join(f'{w:016x}\n' for w in phrom))
    (out/'spine_stream.hex').write_text(''.join(f'{w:010x}\n' for w in beats))
    pairs=sorted({p[1] for p in matrix['plans']})
    for pair in pairs:
        cfg=[execution.stage_join.cfg(fragment['stage'],rank,pair,a)
             for a in range(25*(fragment['phase']+1))]
        (out/f'e{pair}.cfg.hex').write_text(''.join(f'{w:012x}\n' for w in cfg))
    output_base=instruction['me_obase']*16 if me else instruction['qe_obase']
    info=dict(node=node,position=1048575,rank=rank,stage=fragment['stage'],
        phase=fragment['phase'],key=fragment['key'],fragment_index=fragment_index,
        captured_expert_ids=expert_ids,source_matrix_sha256=fragment['source_matrix_sha256'],
        instruction=instruction,output_base=output_base,rows=matrix['rows'],K=matrix['K'],
        format=matrix['format'],ordered_K_segments=matrix['segments'],plans=matrix['plans'],
        PHROM_words=phrom,stream_words=len(beats),stream_source_sha256=stream_pin,
        pairs=pairs,root_rows=profile['root_rows'],root_return_counts=profile['root_return_counts'],
        actual_BF_site_IDs=execution.stage_join.stage_map['BF_site_IDs'],
        input_VM_base=instruction['me_xbase'] if me else instruction['qe_xbase'],
        ME=me,FP32_output=fp32,cfg_phase_must_not_be_relabelled=True,
        native_execution_qualified=False)
    (out/'binding.json').write_text(json.dumps(info,indent=2)+'\n')
    return info


def emit(execution,node,rank,out,connectivity):
    from dsrom_s81_minimum_return_binding import bind_return_phase
    resolved = execution.source.resolve(node,rank)
    dispatched = execution.dispatch(node,rank)
    source = execution.source.nodes[node]['instruction']
    if source['unit'] != 3 or source.get('qe_mode',0) != 0 or len(resolved['fragments']) != 1:
        raise ValueError('one actual full native QAL/KVAL fragment required')
    matrix = resolved['fragments'][0]['matrix']
    fragment = dispatched['fragments'][0]
    if (matrix['format'] != 'fp8' or matrix['K'] != 5120 or
            matrix['rows'] != source['qe_nout'] or matrix['rows'] not in (320,128)):
        raise ValueError('full source dimensions changed')
    pairs = sorted({p[1] for p in matrix['plans']})
    phrom,beats,stream_hash = native_stream(matrix)
    out = Path(out);out.mkdir(parents=True,exist_ok=False)
    (out/'spine_phase.hex').write_text(''.join(f'{w:016x}\n' for w in phrom))
    (out/'spine_stream.hex').write_text(''.join(f'{w:010x}\n' for w in beats))
    bindings = []
    for pair in pairs:
        # Keep every actual predecessor phase. No synthetic zero CFG prefix.
        cfg = [execution.stage_join.cfg(fragment['stage'],rank,pair,a)
               for a in range(25*(fragment['phase']+1))]
        path = out/f'e{pair}.cfg.hex'
        path.write_text(''.join(f'{w:012x}\n' for w in cfg))
        bindings.append(bind_return_phase(execution.stage_join,connectivity,fragment,
            pair=pair,positions=1,phrom0=phrom[0],phrom1=phrom[1],cfg_path=path,
            identity=0,format=0,output_base=fragment['instruction']['qe_obase'],
            output_position_stride=matrix['rows'],ME=False))
    owned = [r for b in bindings for r in b['component_rows']]
    if sorted(owned) != list(range(matrix['rows'])):
        raise ValueError('full native output coverage missing or duplicated')
    symbol = 's81_native_field_' + node.lower().replace('.','_') + '_bindings'
    cpp = ['#pragma once','#include "s81_minimum_return_participant.hpp"',
           f'inline std::vector<dsrom_s81_minimum::ReturnPhaseBinding> {symbol}(uint64_t id){{',
           'if(id>=(1ull<<47))throw std::runtime_error("field context identity47");',
           'std::vector<dsrom_s81_minimum::ReturnPhaseBinding> out;']
    for b in bindings:
        cpp.append('{dsrom_s81_minimum::ReturnPhaseBinding b;')
        for k in ('stage','rank','pair','root','phase','positions_minus_one','format','phrom0','phrom1',
                  'output_base','output_position_stride','region_pair_begin','region_pair_end',
                  'branch_a_leaf','branch_b_leaf'):
            cpp.append(f'b.{k}={b[k]}ull;')
        for k in ('emitted_key','source_matrix_sha256','cfg_path'):
            cpp.append(f'b.{k}={json.dumps(b[k])};')
        cpp.append('b.identity=id;b.component_rows={'+','.join(map(str,b['component_rows']))+'};out.push_back(b);}')
    cpp.append('return out;}')
    (out/'native_field_bindings.hpp').write_text('\n'.join(cpp)+'\n')
    info = dict(node=node,position=1048575,stage=fragment['stage'],rank=rank,
        phase=fragment['phase'],key=fragment['key'],rows=matrix['rows'],pairs=pairs,
        root_return_counts=bindings[0]['whole_root_quota'] if len(bindings)==1 else
            [sum(len(b['component_rows']) for b in bindings if b['root']==r) for r in range(128)],
        PHROM_words=phrom,stream_words=len(beats),stream_source_sha256=stream_hash,
        output_base=fragment['instruction']['qe_obase'],source_matrix_sha256=fragment['source_matrix_sha256'],
        cfg_phase=fragment['phase'],input_cut_local_phase=0,
        cfg_phase_must_not_be_relabelled=True,cpp_binding_symbol=symbol,bindings=bindings,
        scope='all canonical QAL/KVAL rows; existing native participants still required',
        native_execution_qualified=False)
    (out/'binding.json').write_text(json.dumps(info,indent=2)+'\n')
    return info


def main():
    from dsrom_s81_execution_binding import CanonicalS81Execution
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--owner',type=Path,required=True)
    p.add_argument('--layer',type=int,required=True)
    p.add_argument('--rank',type=int,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    execution=CanonicalS81Execution(a.owner)
    connectivity=json.loads((a.owner/'results/uarch/dsrom_s81_rd64_connectivity_20261004/canonical_binding_r1/connectivity.json').read_text())
    for pc in (7,8):
        result=emit(execution,f'L{a.layer}.I{pc}',a.rank,a.out/f'I{pc}',connectivity)
        print(result['node'],result['stage'],result['phase'],len(result['pairs']),result['rows'],flush=True)

if __name__=='__main__':main()
