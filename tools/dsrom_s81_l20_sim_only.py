#!/usr/bin/env python3
"""Run canonical S81 L20 source with existing exact arithmetic stand-ins.

SIM_ONLY functional invocation, not native timing or an S81 hardware verdict.
No output oracle is used by dispatch or arithmetic. Compare H/PF only at END.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

os.environ.setdefault('HDC_V41_ARITH', 'chunk8')
import numpy as np
import v41_fullshape_isa as M
from dsrom_s81_execution_binding import CanonicalS81Execution


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    result = dict(scope='S81.L20.position1048575', functional='SIM_ONLY',
                  headline_timing=False, completed=False, exact=None,
                  source_stage=37, simulation_ticks=0, native_cycles=None)
    start = time.monotonic()
    try:
        print('SIM_ONLY canonical S81 L20 source loading; expected comparison only at END', flush=True)
        execution = CanonicalS81Execution(M.ROOT)
        source_nodes = [execution.source.nodes[n] for n in execution.target_source_nodes(
            [20], position=1048575, include_head=False)]
        nodes = [n for n in source_nodes if n['kind'] == 'instruction']
        assert len(nodes) == 144
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
        trace = []
        with (a.output/'operations.jsonl').open('x') as log:
            for pc, node in enumerate(nodes):
                literal = node['instruction']
                word = M.I.encode(full_shape=True, **{k:tuple(v) if isinstance(v,list) else v
                                                    for k,v in literal.items()})
                assert hashlib.sha256(word.to_bytes(256,'little')).hexdigest() == node['template_word_sha256']
                f = M.I.decode(word, full_shape=True)
                f['_tag'] = literal['_tag']
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
                        method = {0:'ctl',1:'me',2:'su',3:'qe',4:'xu',5:'he'}[f['unit']]
                        if method=='ctl':rank.ctl(f,pc)
                        else:getattr(rank,method)(f,pc,rank.log)
                        if rank.unwritten:raise M.Defect(str(rank.unwritten[-1]))
                result['simulation_ticks'] += 1
                log.write(json.dumps(dict(node=node['id'], unit=f['unit'],
                    arithmetic='SIM_ONLY_EXACT', simulation_tick=result['simulation_ticks']))+'\n')
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
    except BaseException as exc:
        result.update(failure=repr(exc))
        raise
    finally:
        result['elapsed_seconds'] = time.monotonic()-start
        (a.output/'terminal.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)


if __name__=='__main__':
    main()
