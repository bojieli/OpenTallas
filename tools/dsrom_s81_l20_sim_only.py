#!/usr/bin/env python3
"""Run canonical S81 L20 source with existing exact arithmetic stand-ins.

SIM_ONLY functional invocation, not native timing or an S81 hardware verdict.
No output oracle is used by dispatch or arithmetic. Compare H/PF only at END.
"""
import argparse
import csv
import copy
import hashlib
import json
import os
from pathlib import Path
import time

os.environ.setdefault('HDC_V41_ARITH', 'chunk8')
import numpy as np
import v41_fullshape_isa as M
from dsrom_s81_execution_binding import CanonicalS81Execution
from dsrom_s81_head_source_binding import HeadSourceBinding


def attention_math_scope(scope, *, sim_only_endpoint=False):
    native = 'QK.I61.I62.PV.native.SIM_ONLY-source-KVT-descriptor-TP4'
    simulated = 'QK.I61.I62.PV.SIM_ONLY-att-endpoint.SIM_ONLY-source-KVT-descriptor-TP4'
    if scope not in (native, simulated):
        raise ValueError('attention source scope is not the selected QK/softmax/PV path')
    return 'NATIVE' if scope == native and not sim_only_endpoint else 'SIM_ONLY-att-endpoint'


def head_chain(ranks, model, output, result):
    binding=HeadSourceBinding()
    compiled=binding.compile(opt_in=True,entry14=0)
    checkpoint=model.w.ck
    buf,dtype,shape=checkpoint.raw('head.weight')
    assert dtype=='BF16' and shape==[129280,5120]
    weights=np.frombuffer(buf,dtype='<u2').reshape(shape)
    gamma=checkpoint.get('norm.weight')
    inputs=[(r.read(np.arange(20480),'head_actual_H',144).reshape(4,5120).copy(),
             r.read(np.arange(41152,41156),'head_actual_PF',144).copy()) for r in ranks]
    all_logits=[]
    with (output/'head_operations.jsonl').open('x') as log:
        for pc,entry in enumerate(compiled['instructions']):
            f=M.I.decode(int(entry['word_hex'],16),full_shape=True)
            print('SIM_ONLY',entry['source_node'],'tick',result['simulation_ticks'],flush=True)
            for rank in ranks:
                rank.fetch=rank.source_fetch
                rank.crom[:5120,0]=gamma;rank.crom[:5120,1]=0;rank.crom_ok[:5120]=True
                if f['unit']==M.I.UNIT_SU:
                    rank.su(f,144+pc,rank.log)
                elif f['unit']==M.I.UNIT_ME:
                    assert pc==5 and f['me_k']==5120 and f['me_nout']==32320 and f['me_amax']
                    # Capture the produced XN before any output writes. Storage
                    # is released BF16; arithmetic is eight sequential FP32
                    # products followed by the padded 1024-leaf tree.
                    x=rank.read(f['me_xbase']+np.arange(5120),'head_XN',149).copy()
                    logits=np.empty(32320,dtype=M.F)
                    for begin in range(0,32320,128):
                        end=min(begin+128,32320)
                        w=M.G.from_bits(weights[rank.r*32320+begin:rank.r*32320+end].astype(np.uint32)<<16)
                        logits[begin:end]=M.V.csum(M.G.mul(w,x[None,:]))
                    rank.write(f['me_obase']*16,logits)
                    all_logits.append(logits)
                elif f['unit']!=M.I.UNIT_CTL:
                    raise M.Defect('unsupported literal head operator')
                if rank.unwritten:raise M.Defect(str(rank.unwritten[-1]))
            result['simulation_ticks']+=1
            log.write(json.dumps(dict(node=entry['source_node'],arithmetic='SIM_ONLY_EXACT',
                simulation_tick=result['simulation_ticks']))+'\n');log.flush()
    assert len(all_logits)==4 and not any(r.rope_held or r.unwritten for r in ranks)
    # Golden comparison is at the chain's END, using its actual produced L20
    # carry as the argument, never a 40-layer token's cached head activations.
    errors=[]
    for rank,(h,pf),got in zip(ranks,inputs,all_logits):
        ref_x=M.V.rmsnorm_bf16(model.hc_pre(h,pf),gamma,model.eps)
        reference=np.empty(32320,dtype=M.F)
        for begin in range(0,32320,128):
            end=min(begin+128,32320)
            w=M.G.from_bits(weights[rank.r*32320+begin:rank.r*32320+end].astype(np.uint32)<<16)
            reference[begin:end]=M.V.mv(w,ref_x)
        errors.append(dict(rank=rank.r,logits_bit_mismatches=int(np.count_nonzero(M.G.bits(got)!=M.G.bits(reference)))))
    joined=np.concatenate(all_logits)
    assert np.isfinite(joined).all()
    chosen=int(np.argmax(joined)) # SIM_ONLY exact lowest-ID global argmax service.
    np.save(output/'head_logits.npy',joined)
    result['head']=dict(component_chain='produced_L20_H_PF_to_released_head_NOT_full40layer_token',
        instructions=7,arithmetic='SIM_ONLY_EXACT',storage_dies=binding.head_dies,
        source_fence='SIM_ONLY_SYNCHRONOUS_CONSUMERS',global_argmax_service='SIM_ONLY',
        selected_id=chosen,selected_value_bits=int(M.G.bits(joined[chosen])),errors=errors,
        exact=not any(e['logits_bit_mismatches'] for e in errors))
    result['exact']=bool(result['exact'] and result['head']['exact'])



def capture_h_chain_inputs(ranks, nodes, execution, output, result, *, pause=True):
    """Produced pre-I75 operands only. Files do not confer native VM leases."""
    if result['simulation_ticks'] != 75 or nodes[75]['id'] != 'L20.I75':
        raise M.Defect('H-chain export must precede the real I75 after I74')
    if any(r.unwritten or r.rope_held for r in ranks):
        raise M.Defect('H-chain export has unresolved source writes/read state')
    # These are the final source writers, not the I1 ancestor or consumer PCs.
    selected = [('T', 74, 20480), ('CA', 60, 16), ('POA', 57, 4), ('Y', 72, 5120)]
    source_order = list(execution.source.nodes)
    operands = {}
    for name, pc, count in selected:
        node = nodes[pc]
        if node['id'] != f'L20.I{pc}' or name not in node['instruction'].get('_writes', []):
            raise M.Defect('H-chain boundary source writer changed: '+name)
        literal = node['instruction']
        address = (literal['xu_dst'] if name == 'CA' else
                   literal['coll_dst'] if name == 'Y' else literal['o_base'])
        source_count = (literal['xu_n'] if name == 'CA' else
                        literal['coll_n'] if name == 'Y' else
                        literal['su_nin'] * literal['su_nout'])
        if source_count != count:
            raise M.Defect('H-chain boundary source extent changed: '+name)
        files = {}
        for rank in ranks:
            if rank.V[name] != address:
                raise M.Defect('H-chain boundary differs from the source VM home: '+name)
            values = rank.read(address+np.arange(count), 'native_I75_'+name, 75)
            path = output/f'I75.{name}_rank{rank.r}.u32'
            # Same raw little-endian FP32 format as NativeTargetEntry::load.
            # No rounding, host result computation, accepted owner or VM ACK.
            M.G.bits(values).astype('<u4').tofile(path)
            files[path.name] = M.sha(path)
        operands[name] = dict(producer=9+source_order.index(node['id']),
            source_node=node['id'], template_sha256=node['template_word_sha256'],
            address=address, count=count, bytes_per_rank=count*4, files=files)
    manifest = dict(scope='produced source operands before native L20.I75 -> L20.I76',
        position=1048575, token=16754, stage=37, seed=20260930,
        instructions_completed=75, expected_outputs_used=False,
        payload_format='little-endian raw binary32; no native lease/acceptance/ACK in files',
        operands=operands,
        I75=dict(producer=9+source_order.index(nodes[75]['id']),
            template_sha256=nodes[75]['template_word_sha256']),
        I76=dict(producer=9+source_order.index(nodes[76]['id']),
            template_sha256=nodes[76]['template_word_sha256']),
        dynamics={str(r.r):[int(v) for v in r.dyn] for r in ranks},
        source_inputs_sha256=execution.input_sha256,
        native_publication_qualified=False,
        native_loader='existing SourceIo offer/visible and source-owned publication tags; actual same-bank ACK required',
        initial_H='unchanged released initial TargetEntry H; no expected/final H imported')
    (output/'native_h_chain_inputs.json').write_text(json.dumps(manifest,indent=2)+'\n')
    result['h_chain_inputs'] = manifest
    if pause:
        result.update(scope='S81.L20.produced_native_h_chain_inputs',
            disposition='PAUSED_BEFORE_NATIVE_I75', completed=False, exact=None)


def main():
    if M.V.ARITH != 'chunk8' or M.V.FUSE:
        raise ValueError('S81 caller requires resolved ARITH=chunk8 and FUSE empty; '
                         f'got ARITH={M.V.ARITH!r}, FUSE={sorted(M.V.FUSE)!r}')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--head-chain',action='store_true',help='carry produced L20 H/PF directly into released head')
    p.add_argument('--carry-input',type=Path,help='actual carry.npz retained by an earlier invocation; head-only debugging')
    p.add_argument('--native-i0',type=Path,help='actual native_L20_I0.tsv; replace only the measured rank I0')
    p.add_argument('--capture-index-inputs',action='store_true',
                   help='stop before I44 after saving produced I36 and I44 operands for the native join')
    p.add_argument('--capture-field-inputs',action='store_true',
                   help='stop before I7; export actual produced I6.XN for native stage37 field actors')
    p.add_argument('--native-index-result',type=Path,
                   help='completed native rank3 I36/I44 directory; consume its actual score output')
    p.add_argument('--native-attention-result',type=Path,
                   help='completed native QK/softmax/PV directory; import four actual I63 ACC outputs')
    p.add_argument('--sim-only-att-endpoint',action='store_true',
                   help='label the selected CPU attention endpoint arithmetic SIM_ONLY, including older TSV emitters')
    p.add_argument('--capture-attention-inputs',action='store_true',
                   help='capture produced attention operands in this continuation, stopping before I63')
    p.add_argument('--capture-h-chain-inputs',action='store_true',
                   help='stop before I75; export produced T/I74, CA/I60, POA/I57 and Y/I72 for native I75->76')
    a = p.parse_args()
    if a.capture_field_inputs and (a.carry_input or a.head_chain or a.native_index_result or
            a.native_attention_result or a.capture_index_inputs or a.capture_attention_inputs or
            a.capture_h_chain_inputs):
        p.error('--capture-field-inputs requires only the source I0..I6 prefix')
    if a.sim_only_att_endpoint and not a.native_attention_result:
        p.error('--sim-only-att-endpoint requires the actual completed adapter/VM attention result')
    if a.capture_h_chain_inputs and (a.carry_input or a.head_chain or
            a.capture_index_inputs or a.capture_attention_inputs):
        p.error('--capture-h-chain-inputs requires the L20 prefix through I74, without another capture stop/head path')
    native_pv=None
    native_pv_bits={}
    if a.native_attention_result:
        if a.carry_input or a.capture_index_inputs or a.capture_attention_inputs:
            p.error('--native-attention-result requires the L20 continuation through I63')
        # Refuse incomplete native output before loading any model or creating
        # this continuation's output. Only the native PV writer/readback files
        # are inputs; captured I63.S and comparison payloads are never read.
        try:
            directory=a.native_attention_result
            terminal_file=directory/'native_L20_ATT.tsv'
            terminal_bytes=terminal_file.read_bytes()
            reader=csv.DictReader(terminal_bytes.decode('utf-8').splitlines(),delimiter='\t')
            if reader.fieldnames!=['scope','position','ranks','qk_accept','pv_accept','terminal']:
                raise ValueError('native attention terminal is not the PV continuation record')
            rows=list(reader)
            if len(rows)!=1 or None in rows[0] or any(v is None for v in rows[0].values()):
                raise ValueError('native attention requires one complete terminal row')
            native_pv=rows[0]
            arithmetic_scope = attention_math_scope(native_pv['scope'],
                                                    sim_only_endpoint=a.sim_only_att_endpoint)
            if a.sim_only_att_endpoint:
                native_pv['raw_tsv_scope'] = native_pv['scope']
                native_pv['scope'] = 'QK.I61.I62.PV.SIM_ONLY-att-endpoint.SIM_ONLY-source-KVT-descriptor-TP4'
            for key in ('position','ranks','qk_accept','pv_accept','terminal'):
                text=native_pv[key]
                if not text.isascii() or not text.isdecimal():
                    raise ValueError('native attention '+key+' must be an unsigned integer')
                native_pv[key]=int(text)
            if native_pv['position']!=1048575 or native_pv['ranks']!=4:
                raise ValueError('native attention requires actual DS1M four-rank source output')
            if not 0<=native_pv['qk_accept']<native_pv['pv_accept']<native_pv['terminal']:
                raise ValueError('native attention accepted/terminal edges are not causal')
            files={}
            for rank in range(4):
                path=directory/f'native_L20_I63_rank{rank}.u32'
                payload=path.read_bytes()
                if len(payload)!=8192*4:
                    raise ValueError(f'native I63 rank{rank} requires exactly 8192 raw32 words')
                native_pv_bits[rank]=np.frombuffer(payload,dtype='<u4').copy()
                files[path.name]=hashlib.sha256(payload).hexdigest()
            native_pv.update(source_terminal_sha256=hashlib.sha256(terminal_bytes).hexdigest(),
                files=files,stage=37,producer=2534,address=74272,words_per_rank=8192,
                template_sha256='6124df21d8de509ccbb8e0f114d2ed9776a4316dd810e92c35c0a07acfb9083a',
                attention_arithmetic=arithmetic_scope,
                native_attention_math=arithmetic_scope == 'NATIVE',
                scope_note=('actual adapter/VM I63 readback; attention arithmetic '+arithmetic_scope+
                            '; remaining L20 arithmetic and fences SIM_ONLY; no physical timing credit'))
        except (OSError,UnicodeError,ValueError,KeyError) as exc:
            p.error(str(exc))
    a.output.mkdir(exist_ok=False)
    result = dict(scope='S81.L20.position1048575', functional='SIM_ONLY',
                  arithmetic_mode=dict(arith=M.V.ARITH, fuse=sorted(M.V.FUSE)),
                  headline_timing=False, completed=False, exact=None,
                  source_stage=37, simulation_ticks=0, native_cycles=None)
    if native_pv is not None:
        result['native_attention']=native_pv
    start = time.monotonic()
    try:
        print('SIM_ONLY canonical S81 L20 source loading; expected comparison only at END', flush=True)
        execution = CanonicalS81Execution(M.ROOT)
        source_nodes = [execution.source.nodes[n] for n in execution.target_source_nodes(
            [20], position=1048575, include_head=False)]
        nodes = [n for n in source_nodes if n['kind'] == 'instruction']
        assert len(nodes) == 144
        native_i0=None
        native_index=None
        if a.native_index_result:
            with (a.native_index_result/'native_L20_index.tsv').open() as stream:
                rows=list(csv.DictReader(stream,delimiter='\t'))
            assert len(rows)==1
            native_index=rows[0]
            assert int(native_index['rank'])==3 and int(native_index['position'])==1048575
            cycles=[int(native_index[k]) for k in ('key_accept','key_visible','scan_accept','terminal')]
            assert 0<=cycles[0]<=cycles[1]<=cycles[2]<=cycles[3]
            score_file=a.native_index_result/'native_L20_I44.u32'
            assert score_file.stat().st_size==262144*4
            native_scores=np.fromfile(score_file,dtype='<u4')
            assert not np.any(native_scores&0xffff)
            result['native_index']=dict(native_index,source_sha256=M.sha(score_file),
                scope_note='rank3 native writer/scorer; other ranks and operators SIM_ONLY')
        if a.capture_attention_inputs:
            assert not a.capture_index_inputs and not a.carry_input
        if a.native_i0:
            assert not a.carry_input
            with a.native_i0.open() as stream:
                rows=list(csv.DictReader(stream,delimiter='\t'))
            assert len(rows)==1
            native_i0=rows[0]
            assert native_i0['scope']=='L20.I0.native-component'
            for key,value in [('position',1048575),('producer',2470),('address',40992)]:
                assert int(native_i0[key])==value
            native_i0={k:int(v) if k!='scope' else v for k,v in native_i0.items()}
            assert 0<=native_i0['rank']<4 and 0<=native_i0['raw32']<2**32
            assert 0<=native_i0['accepted_cycle']<=native_i0['visible_read_cycle']
            assert nodes[0]['template_word_sha256']=='0a8042d53254c972480a5c7c05cf676d0c5e3cbea44e456aa5537b16ce93e622'
            result['native_i0']=dict(native_i0,source_sha256=M.sha(a.native_i0),
                cycles_to_visible_read=native_i0['visible_read_cycle']-native_i0['accepted_cycle'],
                scope_note='one measured rank I0; remaining ranks and operators SIM_ONLY')
        actions = [n for n in source_nodes if n['kind']=='runtime_action']
        fences = [n for n in source_nodes if n['kind']=='consumer_done_fence']
        assert len(fences)==1
        for node in actions:
            action=node['action']
            if action['required']:
                raise M.Defect('required source action has no stand-in: '+node['id'])
            print('SIM_ONLY',node['id'],'optional source action not required; no restored selection',flush=True)
        bind, scratch = M.case(1048576, 20260930, 20)
        # Existing retained images supply released payload and initial state;
        # source dispatch below selects matrices from actual produced EIDs.
        golden = M.load_golden(1048576, scratch, 20260930, 20)
        base = M.BoundLayout(bind)
        consts = M.KC.load('deepseek-v4.1-flash')
        params = json.loads(M.KC.OUT.read_text())['models']['deepseek-v4.1-flash']
        consts = dict(consts, _sinkhorn_iters=params['unit_parameters']['sinkhorn_iters']['value'])
        model, _ = M.LC.build_model(M.LC.Checkpoint(), engram=False)
        state, desc = M.LC.synthetic_state(model, 1048576, seed=20260930, layers=[20])
        stores = M.indexed_stores(model, state, 20)
        win = np.stack(state['win'][20]).astype(M.F)
        rope = {(1, 1048575): M.V.rope_cs(model.freqs_yarn, 1048575)}
        del state
        ranks = []
        for r in range(4):
            man, image, pin = M.rank_images(1048576, r, scratch, golden)
            lay = M.BoundLayout(bind)
            rank = M.Rank(r, lay, man, image, golden, win, rope, consts, 1048575, stores=stores)
            rank.source_fetch = rank.fetch
            ranks.append(rank)
        if a.carry_input:
            assert a.head_chain
            carry=np.load(a.carry_input,allow_pickle=False)
            for rank in ranks:
                rank.vm[:]=0;rank.ok[:]=False
                rank.write(0,carry['H'][rank.r].reshape(-1))
                rank.write(41152,carry['PF'][rank.r])
            result['carry_source_sha256']=M.sha(a.carry_input)
            result['exact']=True
            head_chain(ranks,model,a.output,result)
            result['completed']=True
            return
        trace = []
        with (a.output/'operations.jsonl').open('x') as log:
            for pc, node in enumerate(nodes):
                if a.capture_field_inputs and pc == 7:
                    writer = nodes[6]
                    if (result['simulation_ticks'] != 7 or writer['id'] != 'L20.I6' or
                            'XN' not in writer['instruction'].get('_writes', [])):
                        raise M.Defect('field input export must follow the actual I6 XN writer')
                    files = {}
                    for rank in ranks:
                        if rank.unwritten or rank.rope_held or rank.V['XN'] != 46464:
                            raise M.Defect('field input has unresolved source state/address')
                        values = rank.read(46464 + np.arange(5120), 'produced_I6_XN', 7)
                        if rank.unwritten:
                            raise M.Defect('I6 XN input contains unwritten source elements')
                        path = a.output / f'I6.XN_rank{rank.r}.u32'
                        M.G.bits(values).astype('<u4').tofile(path)
                        files[path.name] = M.sha(path)
                    manifest = dict(scope='produced I0..I6 prefix before native L20.I7/I8',
                        functional='SIM_ONLY_EXACT', position=1048575, token=16754, stage=37,
                        source_node=writer['id'], producer=9+list(execution.source.nodes).index(writer['id']),
                        template_sha256=writer['template_word_sha256'], address=46464, count=5120,
                        instructions_completed=7, expected_outputs_used=False,
                        native_publication_qualified=False, files=files,
                        source_inputs_sha256=execution.input_sha256)
                    (a.output/'native_field_inputs.json').write_text(json.dumps(manifest,indent=2)+'\n')
                    result.update(scope='S81.L20.produced_native_field_inputs',
                        disposition='PAUSED_BEFORE_NATIVE_I7', completed=False, exact=None,
                        field_inputs=manifest)
                    return
                literal = node['instruction']
                word = M.I.encode(full_shape=True, **{k:tuple(v) if isinstance(v,list) else v
                                                    for k,v in literal.items()})
                assert hashlib.sha256(word.to_bytes(256,'little')).hexdigest() == node['template_word_sha256']
                f = M.I.decode(word, full_shape=True)
                f['_tag'] = literal['_tag']
                if pc==63 and native_pv is not None:
                    fields={'unit':M.I.UNIT_ME,'me_mmode':1,'me_round':1,'me_hg':1,
                            'me_nout':512,'me_tiles':16,'me_xbase':63936,'me_xcs':5120,
                            'me_xks':1,'me_xjs':640,'me_obase':4642,'me_d_k':M.I.FULL_DYN['T1']}
                    if (node['id']!='L20.I63' or node['template_word_sha256']!=native_pv['template_sha256'] or
                        any(f[key]!=value for key,value in fields.items()) or
                        9+list(execution.source.nodes).index(node['id'])!=native_pv['producer']):
                        raise M.Defect('native PV output does not match the actual selected I63 literal/geometry')

                if a.capture_h_chain_inputs and pc==75:
                    capture_h_chain_inputs(ranks,nodes,execution,a.output,result)
                    return # I75 T and I76 H remain real downstream native computations
                if native_pv is not None and pc==75:
                    # Export THIS actual PV continuation's produced suffix
                    # operands once while continuing through the existing END
                    # comparison. Files grant no native VM lease or ACK.
                    capture_h_chain_inputs(ranks,nodes,execution,a.output,result,pause=False)
                if a.capture_attention_inputs and pc in (20,38,55,63):
                    name,address,count={20:('I20.KVN',54720,512),38:('I38.LAT',93728,512),
                        55:('I55.Q',55744,8192),63:('I63.S',63936,10240)}[pc]
                    for rank in ranks:
                        values=rank.read(address+np.arange(count),'native_'+name,pc)
                        M.G.bits(values).astype('<u4').tofile(a.output/f'{name}_rank{rank.r}.u32')
                    if pc==63:
                        result.update(scope='S81.L20.produced_native_attention_inputs',
                            disposition='PAUSED_BEFORE_NATIVE_I63',completed=False,exact=None,
                            input_files={p.name:M.sha(p) for p in a.output.glob('*.u32')})
                        return
                if a.capture_index_inputs and pc in (36,44):
                    spans=[('I36_input',94496,128)] if pc==36 else [
                        ('I44_query',98720,4096),('I44_weights',102848,32)]
                    for rank in ranks:
                        for name,address,count in spans:
                            values=rank.read(address+np.arange(count),'native_'+name,pc)
                            M.G.bits(values).astype('<u4').tofile(a.output/f'{name}_rank{rank.r}.bin')
                    if pc==44:
                        manifest=dict(scope='produced source operands before native I36 writer/I44 scorer',
                            position=1048575,token=16754,stage=37,seed=20260930,
                            instructions_completed=44,expected_outputs_used=False,
                            I36=dict(producer=2507,address=94496,count=128,
                                template_sha256=nodes[36]['template_word_sha256']),
                            I44=dict(producer=9+list(execution.source.nodes).index(node['id']),
                                template_sha256=node['template_word_sha256'],
                                query_address=98720,query_count=4096,weights_address=102848,weights_count=32,
                                output_address=102880,output_count=262144),
                            dynamics={str(r.r):[int(v) for v in r.dyn] for r in ranks},
                            files={p.name:M.sha(p) for p in a.output.glob('*.bin')})
                        (a.output/'native_index_inputs.json').write_text(json.dumps(manifest,indent=2)+'\n')
                        result.update(scope='S81.L20.produced_native_index_inputs',
                            disposition='PAUSED_BEFORE_NATIVE_I44',completed=False,exact=None)
                        return
                print('SIM_ONLY', node['id'], 'unit', f['unit'], 'tick', pc, flush=True)
                for rank in ranks:
                    # Constants remain addressed by the literal template. The
                    # reader resolves each operand to its released named span;
                    # it never edits c_base/d_base or consumes expected values.
                    reference = base.bind['instruction_trace'][pc]
                    assert reference['tag']==literal['_tag']
                    bound = reference['fields']
                    def fetch(ff, operand, addresses, at, rank=rank, bound=bound):
                        if ff[operand+'_src'] in (M.I.SRC_CLO,M.I.SRC_CHI):
                            actual_base = int(bound.get(operand+'_base',0))
                            delta = actual_base-ff[operand+'_base']
                            mapped = np.asarray(addresses,dtype=np.int64)+delta
                            return rank.crom_read(mapped,ff[operand+'_src']==M.I.SRC_CHI,at)
                        return rank.source_fetch(ff,operand,addresses,at)
                    rank.fetch=fetch
                    binding = execution.source.bindings[node['id']]
                    if binding.get('address_bound'):
                        eids = None
                        if binding['selector_slot'] is not None:
                            eids = [int(x) for x in M.G.bits(rank.read(
                                np.arange(366688,366694), 'actual_EID', pc))]
                        actual = execution.source.resolve(node['id'], rank.r, expert_ids=eids)
                        dispatch = execution.dispatch(node['id'], rank.r, expert_ids=eids)
                        assert dispatch['source_dispatch_bound']
                        alias = actual['fragments'][0]['matrix'].get('original_alias', binding['alias'])
                        if binding['selector_slot'] is not None:
                            alias = binding['alias'].replace('exp0.', 'exp%d.' % eids[binding['selector_slot']], 1)
                        if '.group' in alias:
                            group = int(alias.split('.group')[1])
                            dense = rank.dense_w('wo_a')[group*1024:(group+1)*1024]
                            rank.dense[alias] = dense
                            old = dict(base.mats['wo_a'])
                            old.update(base_word=f['me_wbase'], nrows=f['me_nout'], ncols=f['me_k'])
                        elif alias not in base.mats:
                            # A produced EID can select any released expert,
                            # not just those in the old token's image catalogue.
                            matrices=[x['matrix'] for x in actual['fragments']]
                            assert sum(m['rows'] for m in matrices)==f['qe_nout']
                            assert all(m['K']==32*f['qe_nb'] for m in matrices)
                            m=matrices[0]
                            assert all(x['tensor']==m['tensor'] for x in matrices)
                            if alias not in rank.q:
                                ck=model.w.ck
                                raw=M.V._blocked(ck.get(m['tensor']),ck.get(m['source_scale_tensor']),m['tensor'])
                                rs=m['rank_slices'][rank.r]
                                r0,r1=rs['rows'];c0,c1=rs['cols']
                                rank.q[alias]=M.V.Q8(raw.q[r0:r1,c0:c1],raw.e[r0:r1,c0//32:c1//32])
                                assert rank.q[alias].shape==(f['qe_nout'],32*f['qe_nb'])
                            old=dict(base_word=f['qe_wbase'],format='FP4_E2M1' if f['qe_fp4'] else 'FP8_E4M3',
                                geometry=dict(nout=f['qe_nout'],nb=f['qe_nb'],tiles=f['qe_tiles']))
                        else:
                            old = dict(base.mats[alias])
                            old['base_word'] = f['qe_wbase'] if f['unit']==3 else f['me_wbase']
                        rank.lay.qtrace = {}
                        rank.lay.engine_matrix = lambda engine, address, alias=alias, old=old: (alias, old)
                        rank.lay.qe_matrix = lambda address, eid, stride, alias=alias, old=old: (alias, old)
                    elif f['unit']==M.I.UNIT_HE:
                        alias = 'hc_attn_fn' if pc==1 else 'hc_ffn_fn'
                        old = dict(base.mats[alias], base_word=f['he_wbase'])
                        rank.lay.engine_matrix = lambda engine, address, alias=alias, old=old: (alias,old)
                if f['unit']==M.I.UNIT_COLL:
                    M.collective(ranks, f, pc, trace)
                elif f['unit']==M.I.UNIT_CTL and f['ctl']==M.I.CTL_END:
                    pass
                else:
                    for rank in ranks:
                        if pc==63 and native_pv is not None:
                            # Raw native output at the real literal boundary,
                            # not expected PV or captured probability input.
                            rank.write(native_pv['address'],native_pv_bits[rank.r].view(M.F))
                            continue
                        if pc==44 and native_index and rank.r==3:
                            rank.write(102880,native_scores.view(M.F))
                            continue
                        if pc==0 and native_i0 and rank.r==native_i0['rank']:
                            reference_rank=copy.copy(rank)
                            reference_rank.vm=rank.vm.copy()
                            reference_rank.ok=rank.ok.copy()
                            reference_rank.su(f,pc,[])
                            reference_bits=int(M.G.bits(reference_rank.read(
                                np.array([native_i0['address']]),'I0_reference',pc))[0])
                            result['native_i0']['reference_raw32']=reference_bits
                            result['native_i0']['bit_mismatches']=int(reference_bits!=native_i0['raw32'])
                            if reference_bits!=native_i0['raw32']:
                                raise M.Defect('native I0 differs from exact source arithmetic')
                            # This operand was produced and read back by the
                            # native SU/VM path, never taken from the reference.
                            rank.write(native_i0['address'],np.array([native_i0['raw32']],dtype=np.uint32).view(M.F))
                            continue
                        method = {0:'ctl',1:'me',2:'su',3:'qe',4:'xu',5:'he'}[f['unit']]
                        if method=='ctl':rank.ctl(f,pc)
                        else:getattr(rank,method)(f,pc,rank.log)
                        if rank.unwritten:raise M.Defect(str(rank.unwritten[-1]))
                if a.capture_attention_inputs and pc==47:
                    for rank in ranks:
                        values=rank.read(447360+np.arange(512),'native_I47_SELG',pc)
                        M.G.bits(values).astype('<u4').tofile(a.output/f'I47.SELG_rank{rank.r}.u32')
                result['simulation_ticks'] += 1
                log.write(json.dumps(dict(node=node['id'], unit=f['unit'],
                    arithmetic=('NATIVE_RANK_I0_PLUS_SIM_ONLY_OTHER_RANKS' if pc==0 and native_i0 else
                                'NATIVE_RANK3_I44_PLUS_SIM_ONLY_OTHER_RANKS' if pc==44 and native_index else
                                (native_pv['attention_arithmetic']+'_TP4_I63_PV_READBACK')
                                if pc==63 and native_pv is not None else 'SIM_ONLY_EXACT'),
                    simulation_tick=result['simulation_ticks']))+'\n')
                log.flush()
        # Every functional operator and collective above returns only after
        # all writes. Check the source fence explicitly; this is a synchronous
        # SIM_ONLY consumer fence, never a fabricated native ACK/receipt.
        assert not any(r.unwritten or r.rope_held for r in ranks)
        assert stores['ik_new'] is not None
        assert all(stores['ckv_new'][r] is not None for r in range(4))
        result['source_fence']=dict(node=fences[0]['id'],completed=True,scope='SIM_ONLY_SYNCHRONOUS_CONSUMERS')
        print('SIM_ONLY',fences[0]['id'],'all functional consumers done',flush=True)
        mismatches = []
        for rank in ranks:
            for region, expected in [('H','h_out'),('PF','pre_out')]:
                want = golden['z'][expected].reshape(-1)
                got = rank.read(rank.V[region]+np.arange(len(want)), 'END_'+region, 143)
                mismatches.append(dict(rank=rank.r, region=region,
                    count=int(np.count_nonzero(M.G.bits(got)!=M.G.bits(want)))))
        result.update(completed=True, exact=not any(x['count'] for x in mismatches), mismatches=mismatches)
        # Retain the produced END operands independently of the optional head
        # arithmetic. Native HEAD loads these bits through its existing VM
        # writer/ACK path; files alone confer no publication or lease credit.
        if result['exact']:
            for rank in ranks:
                M.G.bits(rank.vm[:20480]).astype('<u4').tofile(a.output/f'H_rank{rank.r}.u32')
                M.G.bits(rank.vm[41152:41156]).astype('<u4').tofile(a.output/f'PF_rank{rank.r}.u32')
            result['head_input_scope']='PRODUCED_L20_END_H_PF_ONLY_NO_NATIVE_PUBLICATION_CREDIT'
        if result['exact'] or a.head_chain:
            np.savez(a.output/'carry.npz',H=np.stack([r.vm[:20480].reshape(4,5120) for r in ranks]),
                PF=np.stack([r.vm[41152:41156] for r in ranks]))
        if a.head_chain:
            result['completed']=False
            head_chain(ranks,model,a.output,result)
            result['completed']=True
    except BaseException as exc:
        result.update(failure=repr(exc))
        raise
    finally:
        result['elapsed_seconds'] = time.monotonic()-start
        (a.output/'terminal.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)


if __name__=='__main__':
    main()
