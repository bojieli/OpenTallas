"""Emit full canonical QAL/KVAL controls for borrowed native field participants.

No allocator, payload, numerical output, new return tree or model compilation.
The existing stream emitter's stream-only body and actual phase_cfg are reused.
"""
import argparse
import ast
import hashlib
import gzip
import inspect
import json
from pathlib import Path
from types import SimpleNamespace


def native_stream(matrix, *, fp32_output=False, stream_base=0):
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
    phrom = fast.phase_words(dict(bf=bf,K=matrix['K'],nbeat=len(beats),sbase=stream_base,
        nrows=matrix['rows'],fmt_fp32=[fp32_output,fp32_output],rsplit=0))
    return phrom,beats,hashlib.sha256(source.encode()).hexdigest()


def emit_native_stage_tables(execution, stage, out, *, phw=10, saw=14, compact_binding=False):
    """Link ALL resident canonical phases using byte-identical stream bodies.

    No weights/activations, CFG remap or arithmetic change. Canonical key/phase
    order is authoritative; only PHROM SBASE is relocated. Original per-actor
    controls and software update path remain available with stream_base=0.
    """
    import re
    from dsrom_stage_program_join import digest
    if stage not in execution.stage_join.by_stage or not execution.stage_join.by_stage[stage]:
        raise ValueError('occupied canonical field stage required')
    if not 1<=phw<=10 or saw!=14:
        raise ValueError('canonical PHW and current SAW14 required')
    if execution.stage_join.stage_map['PHW_required_by_stage'][stage]!=phw:
        raise ValueError('canonical PHW/source mismatch')
    source={}
    for node,b in execution.source.bindings.items():
        if not b.get('address_bound'):
            continue
        f=execution.source.nodes[node]['instruction']
        fp32=not f.get('me_round',0) if f['unit']==1 else bool(f.get('qe_unrounded',0))
        source.setdefault((b['layer'],b['alias']),[]).append((node,fp32))
    phrom=[0]*(2<<phw); stream=[]; bodies={}; catalog=[]; phases=[]; original_words=0
    rows=execution.stage_join.by_stage[stage]
    if len(rows)>1<<phw:
        raise ValueError('canonical phase namespace overflow')
    for row in rows:
        m=row['matrix']; alias=re.sub(r'exp\d+\.', 'exp0.',row['original_alias'])
        bound=source.get((m['layer'],alias),[])
        if not bound or len({v for n,v in bound})!=1:
            raise ValueError((stage,row['phase'],'missing/conflicting source rounding'))
        fp32=bound[0][1]
        descriptor_templates=[]
        group=execution.stage_join.groups[(m['layer'],row['original_alias'])]
        for node,mode in bound:
            f=execution.source.nodes[node]['instruction']
            dynamic_shape={k:f.get(k,0) for k in ('me_d_nout','me_d_k','me_d_tiles') if f.get(k,0)}
            if dynamic_shape:
                raise ValueError((stage,row['key'],node,'mutable phase descriptor',dynamic_shape))
            K=f['me_k']*(1<<f.get('me_split',0)) if f['unit']==1 else f['qe_nb']*32
            count=f['me_nout'] if f['unit']==1 else f['qe_nout']
            if K!=m['K'] or count!=sum(x['rows'] for x in group):
                raise ValueError((stage,row['key'],node,'source shape conflicts with canonical descriptor'))
            if mode!=fp32:
                raise ValueError((stage,row['key'],node,'repeated key changes rounding descriptor'))
            descriptor_templates.append(dict(node=node,
                template_word_sha256=execution.source.nodes[node]['template_word_sha256'],
                input_base=f.get('me_xbase',f.get('qe_xbase')),
                output_base=f.get('me_obase',f.get('qe_obase')),
                dynamic_input_output={k:f[k] for k in ('me_d_xbase','me_d_obase','qe_d_obase') if f.get(k,0)},
                expert_selector_slot=execution.source.bindings[node]['selector_slot']))
        original,beats,pin=native_stream(m,fp32_output=fp32)
        if not beats or any(v<0 or v>=1<<40 for v in beats):
            raise ValueError('existing codec no longer zero extends into48bit carrier')
        # Dictionary equality compares COMPLETE encoded bodies, not hash-only
        # shape/class equivalence. Include all48 bits of every emitted word.
        body=b''.join(v.to_bytes(6,'little') for v in beats)
        if body not in bodies:
            if len(stream)+len(beats)>1<<saw:
                raise ValueError((stage,row['phase'],row['key'],'exact interned catalog exceeds stream capacity',len(stream)+len(beats),1<<saw))
            bodies[body]=(len(catalog),len(stream))
            catalog.append(dict(body=len(catalog),base=len(stream),words=len(beats),
                                sha256=hashlib.sha256(body).hexdigest()))
            stream.extend(beats)
        body_id,base=bodies[body]
        if body!=b''.join(v.to_bytes(6,'little') for v in stream[base:base+len(beats)]):
            raise ValueError('interned source body is not byte-identical')
        # Existing PHROM codec; retain all fields except its existing SBASE.
        fields=dict(bf=m['format']=='bf16',K=m['K'],nbeat=len(beats),sbase=base,
                    nrows=m['rows'],fmt_fp32=[fp32,fp32],rsplit=0)
        import v41_die_images_w17w10 as fast
        linked=fast.phase_words(fields)
        mask=((1<<16)-1)<<30
        if (linked[0]&~mask,linked[1])!=(original[0]&~mask,original[1]):
            raise ValueError('relocation changed arithmetic/rounding/row controls')
        phase=row['phase']; ME=m['format']=='bf16'
        if execution.stage_join.lookup(stage,row['key'],ME=ME)!=phase:
            raise ValueError('canonical key/phase changed')
        # Decode every linked descriptor through the actual packed bit fields.
        decoded=(bool(linked[0]&1),(linked[0]>>1)&8191,(linked[0]>>14)&65535,
                 (linked[0]>>30)&65535,(linked[0]>>46)&65535,
                 bool((linked[0]>>62)&1),bool((linked[0]>>63)&1),linked[1])
        if decoded!=(fields['bf'],m['K'],len(beats),base,m['rows'],fp32,fp32,0):
            raise ValueError('actual PHROM decode differs from source descriptor')
        if base+len(beats)>1<<saw:
            raise ValueError('relocated phase body exceeds stream depth')
        phrom[2*phase:2*phase+2]=linked
        phases.append(dict(phase=phase,key=row['key'],key_word=row['key_word'],layer=m['layer'],
            alias=m['alias'],expert=m['expert'],source_nodes=[n for n,v in bound],
            source_matrix_sha256=row['matrix_sha256'],ordered_physical_plan_sha256=digest(m['plans']),
            physical_owner_ranks=row['owners'],rank_slices=m['rank_slices'],
            cfg_word_range=[25*phase,25*(phase+1)],phrom_address=[2*phase,2*phase+1],
            PHROM_words=linked,original_local_PHROM_words=original,
            body=body_id,stream_base=base,stream_words=len(beats),stream_sha256=hashlib.sha256(body).hexdigest(),
            fp32_output=fp32,stream_source_sha256=pin,
            descriptor_templates=descriptor_templates,descriptor_stable_for_all_bound_commands=True))
        original_words+=len(beats)
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    (out/'spine_phase.hex').write_text(''.join(f'{w:016x}\n' for w in phrom))
    padded=stream+[0]*((1<<saw)-len(stream))
    (out/'spine_stream.hex').write_text(''.join(f'{w:012x}\n' for w in padded))
    for rank in range(4):
        keys=execution.stage_join.keys(stage,rank)
        if len(keys)!=1<<phw:
            raise ValueError('canonical key frame extent')
        (out/f'spine_keys.rank{rank}.hex').write_text(''.join(f'{k:08x}\n' for k in keys))
    record=dict(schema='opentallas.dsrom.canonical-interned-stage-controls.v1',stage=stage,
        PHW=phw,SAW=saw,phase_count=len(rows),PHROM_words=len(phrom),stream_depth_words=len(padded),
        original_append_stream_words=original_words,unique_stream_words=len(stream),catalog=catalog,
        phases=phases,canonical_inputs=execution.input_sha256,
        files_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.hex'))},
        stream_equality='complete48bit little-endian bodies compared byte-for-byte for EVERYphase',
        high8_stream_bits_zero=True,only_PHROM_SBASE_changed=True,CFG_remapped=False,
        all_resident_experts_bound=True,inactive_key_and_PHROM_slots_explicit_zero=True,
        unused_stream_tail_explicit_zero=True,hardware_provider_adopted=False,
        runtime_array_patching_removed=False,programming_service_priced=False,
        actual_phase_decode_checks=len(phases),descriptor_conflicts=[],
        descriptor_mutability_rule='Dynamic ME shape refused; all bound templates agree on K/rows/rounding. Input/output VM bases and their dynamic selectors are GO ports, not PHROM. i_np/batch position is a GO port, not a phase_words field. Expert IDs select existing canonical phase/key; all384 alternatives included.',
        source_pins={str(Path('tools')/n):hashlib.sha256((execution.owner/'tools'/n).read_bytes()).hexdigest()
            for n in ('dsrom_s81_target_field_controls.py','v41_die_images_w17w10.py','dsrom_s81_execution_binding.py','dsrom_stage_program_join.py')})
    if compact_binding:
        raw=(json.dumps(record,separators=(',',':'))+'\n').encode()
        (out/'binding.json.gz').write_bytes(gzip.compress(raw,mtime=0))
    else:
        (out/'binding.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def read_stage_binding(image):
    image=Path(image)
    candidates=[p for p in (image/'binding.json',image/'binding.json.gz') if p.is_file()]
    if len(candidates)!=1:
        raise ValueError('exactly one actual stage binding required')
    path=candidates[0]
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())


def emit_native_catalog(execution, out, *, reuse_root=None):
    """All CURRENT occupied stages; explicit failures never masquerade as images.

    Existing accepted stage37/38 artifacts are referenced without rerunning
    their bytewise checks. New images use the SAME per-phase linker/codec.
    Compressed binding JSON avoids duplicating millions of metadata lines.
    """
    out=Path(out).resolve()
    out.mkdir(parents=True,exist_ok=False)
    join=execution.stage_join
    occupied=[s for s,rows in join.by_stage.items() if rows]
    records=[]
    for stage in occupied:
        rows=join.by_stage[stage]
        phw=join.stage_map['PHW_required_by_stage'][stage]
        entry=dict(stage=stage,PHW=phw,SAW=14,assigned_phases=len(rows),
                   phase_capacity=1<<phw,PHROM_capacity_words=2<<phw,
                   stream_capacity_words=1<<14,CFG_word_extent=25*len(rows),
                   ranks=[dict(rank=r,die_id=4*stage+r,
                               valid_keys=sum(r in x['owners'] for x in rows)) for r in range(4)])
        try:
            reuse=Path(reuse_root)/f'stage{stage}' if reuse_root is not None and stage in (37,38) else None
            if reuse is not None:
                record=read_stage_binding(reuse)
                if (record['stage'],record['PHW'],record['SAW'],record['phase_count'])!=(stage,phw,14,len(rows)) or record['canonical_inputs']!=execution.input_sha256:
                    raise ValueError('accepted image belongs to a different canonical assignment')
                image=reuse.resolve()
                entry['accepted_image_source_commit']='5a92972790e27b4320f81794186a47afb86a11a0'
                entry['byte_checks_repeated']=False
            else:
                image=out/f'stage{stage}'
                record=emit_native_stage_tables(execution,stage,image,phw=phw,compact_binding=True)
                entry['byte_checks_repeated']=False
            binding=image/('binding.json.gz' if (image/'binding.json.gz').exists() else 'binding.json')
            try:
                image_path=str(image.relative_to(execution.owner))
            except ValueError:
                image_path=str(image)
            entry.update(status='ready',image_path=image_path,
                         binding_file=binding.name,binding_sha256=hashlib.sha256(binding.read_bytes()).hexdigest(),
                         reused_accepted_image=reuse is not None,
                         phase_count=record['phase_count'],unique_bodies=len(record['catalog']),
                         unique_stream_words=record['unique_stream_words'],
                         original_append_stream_words=record['original_append_stream_words'],
                         files_sha256=record['files_sha256'],descriptor_conflicts=record['descriptor_conflicts'],
                         key_binding='binding phases[].key/key_word at canonical phases[].phase; rank key frames preserve exact ownership',
                         actual_phase_decode_checks=record['actual_phase_decode_checks'])
        except ValueError as error:
            entry.update(status='blocked',failure_type=type(error).__name__,failure=error.args,
                         remaining_phase_checks_complete=False,image_path=None)
        records.append(entry)
        print('stage',stage,entry['status'],entry.get('unique_stream_words',entry.get('failure')),flush=True)
        # Incremental usable catalog while later stages are still linking.
        manifest=dict(schema='opentallas.dsrom.canonical-interned-fullcatalog.v1',
                      canonical_inputs=execution.input_sha256,occupied_stages=occupied,
                      empty_stages=[s for s,rows in join.by_stage.items() if not rows],
                      stages=records,complete=len(records)==len(occupied),
                      all_occupied_stages_ready=len(records)==len(occupied) and all(r['status']=='ready' for r in records),
                      phase_key_CFG_remapped=False,hardware_provider_adopted=False,
                      runtime_array_patching_removed=False,
                      source_only=True,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        tmp=out/'manifest.json.tmp'
        tmp.write_text(json.dumps(manifest,indent=2)+'\n')
        tmp.replace(out/'manifest.json')
    return manifest


def linked_native_stream(matrix, *, fp32_output, stage, phase, key, stage_image):
    """Existing local control bundle using source-bound immutable stage offsets."""
    image=Path(stage_image); bound=read_stage_binding(image)
    if bound['stage']!=stage or not 1<=bound['PHW']<=10 or bound['SAW']!=14:
        raise ValueError('selected stage table binding mismatch')
    row=next((r for r in bound['phases'] if r['phase']==phase),None)
    from dsrom_stage_program_join import digest
    if row is None or row['key']!=key or row['source_matrix_sha256']!=digest(matrix) or row['fp32_output']!=fp32_output:
        raise ValueError('phase/key/matrix/rounding differs from immutable stage image')
    for name,pin in bound['files_sha256'].items():
        if hashlib.sha256((image/name).read_bytes()).hexdigest()!=pin:
            raise ValueError('immutable stage image changed')
    phrom,beats,pin=native_stream(matrix,fp32_output=fp32_output,stream_base=row['stream_base'])
    loaded=[int(w,16) for w in (image/'spine_stream.hex').read_text().splitlines()]
    if beats!=loaded[row['stream_base']:row['stream_base']+len(beats)] or list(phrom)!=row['PHROM_words']:
        raise ValueError('linked local controls differ from actual stage image')
    return phrom,beats,pin


def emit_native_phase_controls(execution,node,rank,out,connectivity,*,
                               fragment_index=0,expert_ids=None,stage_image=None,static_native_cut=None):
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
    if static_native_cut is not None:
        if stage_image is not None:
            raise ValueError('select one canonical image through the actual static cut enrollment')
        from dsrom_s81_static_native_cut import selected_image
        stage_image=selected_image(static_native_cut,canonical_inputs=execution.input_sha256,
            stage=fragment['stage'],rank=rank)
    if stage_image is None:
        phrom,beats,stream_pin=native_stream(matrix,fp32_output=fp32)
    else:
        phrom,beats,stream_pin=linked_native_stream(matrix,fp32_output=fp32,
            stage=fragment['stage'],phase=fragment['phase'],key=fragment['key'],stage_image=stage_image)
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
        native_execution_qualified=False,immutable_stage_image=str(stage_image) if stage_image is not None else None,
        static_native_cut=str(static_native_cut) if static_native_cut is not None else None)
    (out/'binding.json').write_text(json.dumps(info,indent=2)+'\n')
    return info


def emit(execution,node,rank,out,connectivity,*,fragment_index=None,stage_image=None):
    from dsrom_s81_minimum_return_binding import bind_return_phase
    resolved = execution.source.resolve(node,rank)
    dispatched = execution.dispatch(node,rank)
    if fragment_index is None:
        if len(resolved['fragments']) != 1:
            raise ValueError('multi-fragment field requires explicit actual fragment selection')
        fragment_index=0
    if type(fragment_index) is not int or not 0<=fragment_index<len(resolved['fragments']):
        raise ValueError('actual field fragment index required')
    matrix = resolved['fragments'][fragment_index]['matrix']
    fragment = dispatched['fragments'][fragment_index]
    source = fragment['instruction']
    if source['unit'] != 3 or source.get('qe_mode',0) != 0:
        raise ValueError('actual native mode0 QE fragment required')
    if (matrix['format'] != 'fp8' or matrix['K'] != source['qe_nb']*32 or
            matrix['rows'] != source['qe_nout']):
        raise ValueError('full source dimensions changed')
    pairs = sorted({p[1] for p in matrix['plans']})
    fp32=bool(source.get('qe_unrounded',0))
    if stage_image is None:
        phrom,beats,stream_hash = native_stream(matrix, fp32_output=fp32)
    else:
        phrom,beats,stream_hash = linked_native_stream(matrix,fp32_output=fp32,
            stage=fragment['stage'],phase=fragment['phase'],key=fragment['key'],stage_image=stage_image)
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
            identity=0,format=1 if source.get('qe_unrounded',0) else 0,output_base=fragment['instruction']['qe_obase'],
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
    info = dict(node=node,fragment_index=fragment_index,instruction=source,position=1048575,stage=fragment['stage'],rank=rank,
        phase=fragment['phase'],key=fragment['key'],rows=matrix['rows'],pairs=pairs,
        root_return_counts=bindings[0]['whole_root_quota'] if len(bindings)==1 else
            [sum(len(b['component_rows']) for b in bindings if b['root']==r) for r in range(128)],
        PHROM_words=phrom,stream_words=len(beats),stream_source_sha256=stream_hash,
        output_base=fragment['instruction']['qe_obase'],source_matrix_sha256=fragment['source_matrix_sha256'],
        cfg_phase=fragment['phase'],input_cut_local_phase=0,
        cfg_phase_must_not_be_relabelled=True,cpp_binding_symbol=symbol,bindings=bindings,
        scope='all canonical mode0 QE rows; existing native participants still required',
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
    p.add_argument('--stage-tables',default='',help='opt-in comma-separated occupied canonical stages, or all; no payload')
    p.add_argument('--reuse-stage-images',type=Path,help='accepted stage37/38 image root for all-stage catalog; unchanged images referenced')
    a=p.parse_args()
    execution=CanonicalS81Execution(a.owner)
    if a.stage_tables=='all':
        r=emit_native_catalog(execution,a.out,reuse_root=a.reuse_stage_images)
        if not r['all_occupied_stages_ready']:
            raise SystemExit(1)
        return
    if a.stage_tables:
        stages=[int(x) for x in a.stage_tables.split(',')]
        if stages!=sorted(set(stages)) or not set(stages)<={s for s,rows in execution.stage_join.by_stage.items() if rows}:
            raise ValueError('ordered distinct occupied canonical stages required')
        for stage in stages:
            r=emit_native_stage_tables(execution,stage,a.out/f'stage{stage}',
                phw=execution.stage_join.stage_map['PHW_required_by_stage'][stage])
            print(stage,r['phase_count'],r['unique_stream_words'],flush=True)
        return
    connectivity=json.loads((a.owner/'results/uarch/dsrom_s81_rd64_connectivity_20261004/canonical_binding_r1/connectivity.json').read_text())
    for pc in (7,8):
        result=emit(execution,f'L{a.layer}.I{pc}',a.rank,a.out/f'I{pc}',connectivity)
        print(result['node'],result['stage'],result['phase'],len(result['pairs']),result['rows'],flush=True)

if __name__=='__main__':main()
