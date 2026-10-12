#!/usr/bin/env python3
"""Complete functional DSROM TP4 program and additive descriptor lowering.

Functional execution reads model weights and producer state; it accepts no layer
activation/oracle callbacks. Descriptor templates are UNBOUND, not runnable RTL
images. Missing hardware side effects are named runtime dependency actions,
never invented ISA opcodes. Pinned L0/L20 emitters are unchanged.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ.setdefault('HDC_V41_ARITH', 'chunk8')
os.environ.setdefault('HDC_V41_FUSE', '')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import numpy as np
import hdc_replay_v41 as R
import hdc_golden_v41 as G
I, P = R.I, R.P
PIN = 'd2c28c279c4b8df731f9c4937e790831529a954b'
CONFIG = 'compiler/models/deepseek-v4.1-flash/inference_config.json'
SOURCES = ['tools/hdc_replay_v41.py', 'tools/hdc_golden_v41.py', 'tools/hdc_program_v41.py',
           'tools/hdc_isa_v41.py', 'tools/v41_program_constants.py', 'tools/rtl_v41_fullshape_layer_campaign.py',
           'results/rtl/v41_program_constants.json', CONFIG]

def source_pins():
    result = {}
    for path in SOURCES:
        raw = subprocess.check_output(['git', 'show', PIN + ':' + path], cwd=ROOT)
        if (ROOT / path).read_bytes() != raw:
            raise ValueError('pinned source differs: ' + path)
        result[path] = {'commit': PIN, 'sha256': hashlib.sha256(raw).hexdigest()}
    return result


def jsonable(x):
    if isinstance(x, set): return sorted(x)
    if isinstance(x, tuple): return [jsonable(y) for y in x]
    if isinstance(x, list): return [jsonable(y) for y in x]
    if isinstance(x, dict): return {str(k): jsonable(v) for k, v in x.items()}
    return x


class FullLayerBuilder(R.ShapeBuilder):
    """Reuse exact L0/L20 operations and implement missing functional families."""
    def __init__(self, layer):
        lay = R.ShapeLayout(R.SHIPPED, tp_exact=True, rope_storage='hbm_cache', layer=layer)
        super().__init__(lay)
        self.layer = layer
        self.actions = []
        extras=[]
        if layer in R.KV_SRC and R.RATIO[layer]==2:extras += [('CP_KVL',128),('CP_SCL',128),('CPROJ',1024)]
        if layer in R.ENGRAM:extras += [('EKVL',6400)]
        base=lay.vm.map['SLOT2']; cursor=base
        for name,n in extras:
            lay.vm.map[name]=cursor;cursor+=n
        # Scratch is inserted before external persistent stores, not after their
        # enormous conceptual HBM ranges. Existing L0/L20 maps remain identical.
        for name in list(lay.vm.map):
            if name not in dict(extras) and lay.vm.map[name]>=base:
                lay.vm.map[name]+=cursor-base
        self.scratch_end=cursor
        if layer in R.KV_SRC and R.RATIO[layer]==2:
            lay.mat[(layer,'cwkv')]=lay.place(128,5120)
            lay.mat[(layer,'cwgate')]=lay.place(128,5120)
        # Row split of the actual [25600,6144] Engram output, not K split.
        self.V = lay.vm.map

    def action(self, kind, **fields):
        self.actions.append(dict(kind=kind, before_instruction=len(self.prog), hardware_binding=None, **fields))

    def compressor_tp(self, L):
        if R.RATIO[L] == 1:
            return super().compressor_tp(L)
        v, hd, ihd = self.V, self.s['hd'], self.s['ihd']
        t, slot = f'L{L}.compressor', f'SLOT{L}'
        self.me(self.lay.mat[(L, 'cwkv')], v['XN'], v['CP_KVL'], {'XN'}, {'CP_KVL'}, t+'.kv_projection',me_round=0)
        self.me(self.lay.mat[(L, 'cwgate')], v['XN'], v['CP_SCL'], {'XN'}, {'CP_SCL'}, t+'.gate_projection',me_round=0)
        self.coll(I.COLL_ALL_GATHER, v['CP_KVL'], v['CPROJ'], 128,
                  {'CP_KVL'}, {'CPROJ'}, t + '.kv_projection_gather')
        self.coll(I.COLL_ALL_GATHER, v['CP_SCL'], v['CPROJ']+hd, 128,
                  {'CP_SCL'}, {'CPROJ'}, t + '.gate_projection_gather')
        self.su({'CPROJ'}, {slot}, t + '.slot_store', su_nout=1, su_nin=2*hd,
                a_base=v['CPROJ'], a_si=1, dst=I.DST_VM, o_base=v[slot],
                o_d=I.DYN['SLOTW'], o_si=1)
        self.action('persistent_ratio2_slot', source=L, slot_bits=2*2*hd*32,
                    slot_index='position%2', complete='position%2==1', producer='projection_gather',
                    group_first_position='position-1', restore_before='slot_store')
        pred, a, b = I.PRED_ODD, v[slot], v[slot]+2*hd
        self.su({slot}, {'CM'}, t, pred=pred, su_nout=1, su_nin=hd, a_base=a+hd,
                a_si=1, b_base=b+hd, b_si=1, m1=I.M1_MAXB, dst=I.DST_VM, o_base=v['CM'], o_si=1)
        self.su({slot,'CM'}, {'CE'}, t, pred=pred, su_nout=2, su_nin=hd, a_base=a+hd,
                a_so=2*hd, a_si=1, b_base=v['CM'], b_si=1, ad=I.AD_NEGB,
                sfu=I.SFU_EXP, dst=I.DST_VM, o_base=v['CE'], o_so=hd, o_si=1)
        self.su({'CE'}, {'CD'}, t, pred=pred, su_nout=1, su_nin=hd, a_base=v['CE'],
                a_si=1, c_base=v['CE']+hd, c_si=1, ad=I.AD_C, dst=I.DST_VM, o_base=v['CD'], o_si=1)
        self.su({'CE','CD'}, {'CP'}, t, pred=pred, su_nout=2, su_nin=hd,
                a_base=v['CE'], a_so=hd, a_si=1, b_base=v['CD'], b_si=1,
                m1=I.M1_DIVB, dst=I.DST_VM, o_base=v['CP'], o_so=hd, o_si=1)
        self.su({slot,'CP'}, {'POOL','SS'}, t, **P.segmented(dict(pred=pred,
                su_nout=1, su_nin=hd, a_base=a, a_si=1, b_base=v['CP'], b_si=1,
                m1=I.M1_AB, c_base=b, c_si=1, d_base=v['CP']+hd, d_si=1,
                qm=I.QM_POS, ad=I.AD_Q, rnd=1, dst=I.DST_VM, o_base=v['POOL'], o_si=1,
                red=I.RED_SUM, red_sq=1, r_base=v['SS']), R.RMS_SPLIT))
        self.rmsnorm('POOL', hd, 0, 'LAT', t, pred, have_ss='SS')
        self.me(self.lay.mat[(L,'iwk')], v['LAT'], v['IKA'], {'LAT'}, {'IKA'}, t+'.index_key', pred=pred)
        self.bf16('IKA', ihd, 'IKA', t, pred, sq='SS')
        self.rmsnorm('IKA', ihd, 0, 'IKN', t, pred, have_ss='SS')
        self.rope('IKN', v['IKN'], 1, ihd, 'rope_yarn', I.DYN['ROPE_G2'], False, t, pred)
        self.qdq(I.QE_QDQ4, 'IKN', ihd//32, v['IKQ'], {'IKQ'}, t, pred)
        self.kvt_write('IKQ', f'IK{L}', 0, I.DYN['N2M1'], t, pred, width=ihd)
        self.rope('LAT', v['LAT'], 1, hd, 'rope_yarn', I.DYN['ROPE_G2'], False, t, pred)
        self.qdq(I.QE_QDQ4E, 'LAT', hd//32, 0, {f'CKV{L}'}, t, pred, dsel=I.DYN['CKV2'])
        self.action('completed_group_publication', source=L, predicate='position%2==1',
                    compressed_row='(position+1)//2-1', wait_for=['actual_IK_visible','all9_CKV_burst_visible'])

    def indexer_tp(self, L):
        if L == 20: return super().indexer_tp(L)
        v, ih, ihd = self.V, self.s['ih'], self.s['ihd']
        src = max(x for x in R.KV_SRC if x <= L)
        ratio = R.RATIO[L]
        scan, ns, stride = ('SC2','NSL2','SC2') if ratio==2 else ('SC1','NSL1','SC1')
        t = f'L{L}.indexer'
        self.action('index_scan_binding', layer=L, kv_source=src, scan_rows=f'ceil(floor((position+1)/{ratio})/4)',
                    rank_base='rank*scan_rows', preserve_head_order=list(range(32)))
        self.linq(self.lay.qmat[(L,'iwq_b')], 'QR', 'IQ', set(), set(), t)
        self.rope('IQ', v['IQ'], ih, ihd, 'rope_yarn', I.DYN['ROPE'], False, t)
        self.qdq(I.QE_QDQ4, 'IQ', ih*ihd//32, v['IQQ'], {'IQQ'}, t)
        self.me(self.lay.mat[(L,'iwp')], v['XN'], v['WP'], {'XN'}, {'WP'}, t)
        self.su({'WP'}, {'WTS'}, t, su_nout=1, su_nin=ih, a_base=v['WP'], a_si=1,
                a_rnd=1, m1=I.M1_AIMM, imm1=self.imm('index_w_scale'), rnd=1,
                dst=I.DST_VM, o_base=v['WTS'], o_si=1, _imm={'imm1':'index_w_scale'})
        self.me(dict(n=0,tiles=0,k=ihd,base=0), v['IQQ'], v['IS'],
                {'IQQ','WTS',f'IK{src}'}, {'IS'}, t, me_xcs=8*ihd, me_wsrc=1,
                me_ts=ihd, me_ks=1, me_js=0, me_jsh=3, me_xks=1, me_xjs=ihd,
                me_ots=1, me_ojs=0, me_mmode=1, me_d_nout=scan,
                me_d_tiles=('ceil',scan,16), me_hg=2, me_ogs=0, me_fuse=1, me_wts=v['WTS'])
        if L>20:
            self.action('candidate_mask', source=20, score_region='IS', masked_value='-inf',
                        global_key='rank*SC1+local_id', candidate_block_width=8)
        self.action('finite_topk_padding', score_region='IS', absent_score='-inf',
                    absent_ids='never selected', live_k=f'min(512,(position+1)//{ratio})',
                    collective_scope='static512 descriptor needs live extent sideband or qualified padded merge')
        self.xu({'IS'}, {'SEL'}, t, xu_op=I.XU_SEL, xu_src=v['IS'], xu_dst=v['SEL'], xu_d_n=scan, xu_d_k=ns)
        self.su({'IS','SEL'}, {'SV'}, t, su_nout=1, su_nin=0, su_d_nin=ns,
                a_base=v['IS'], a_si=1, a_ind=I.IND_I, a_ibase=v['SEL'],
                dst=I.DST_VM, o_base=v['SV'], o_si=1)
        self.coll(I.COLL_TOPK_MERGE, v['SV'], v['SELG'], 512, {'SV','SEL'}, {'SELG'},
                  t+'.topk_merge', ibase=v['SEL'], k=512, stride=stride)

    def linq(self, mat, x, out, reads, writes, tag, pred=0, **over):
        if tag.endswith('.engram') and out=='EKV':
            super().linq(mat,x,'EKVL',reads,{'EKVL'},tag,pred,**over)
            self.coll(I.COLL_ALL_GATHER,self.V['EKVL'],self.V['EKV'],6400,
                      {'EKVL'},{'EKV'},tag+'.projection_gather')
        else: super().linq(mat,x,out,reads,writes,tag,pred,**over)

    def engram(self, L):
        self.action('engram_checkpoint_codec', layer=L, table_rows=24, columns=256,
                    scales_per_row=8, scale_block=32, beats264_bits=192, wire_bytes=6336,
                    decoded_BF16_bytes=12288, hash_history='last4 compressed token IDs',
                    actual_codec_binding=None, gate_coefficient='FP32(q_weight*k_weight) in golden order')
        first=len(self.prog)
        super().engram(L)
        for f,_,_,tag in self.prog[first:]:
            if f.get('xu_op')==I.XU_EGATHER: f['xu_layer']=R.ENGRAM.index(L)
        self.action('engram_gate_reduction', layer=L, order='golden chunk8 csum per residual/key/dot; no reassociation',
                    current_descriptor_numeric_gate=None)

    def build_layer(self):
        L=self.layer;D=self.s['dim']
        if L in R.ENGRAM:self.engram(L)
        self.hc_mix_issue(L,'attn')
        self.hc_pre('PF','X',f'L{L}.attn_norm','SS')
        self.rmsnorm('X',D,0,'XN',f'L{L}.attn_norm',have_ss='SS')
        if R.RATIO[L]:
            self.action('restore_position_selection', source=max(x for x in R.IDX_SRC if x<=L),
                        region='SELG', required=L not in R.IDX_SRC, candidate_source=20 if L>20 else None)
        self.attention(L,hook=lambda:self.hc_mix_finish(L,'attn'))
        self.hc_post('Y','POA','CA',f'L{L}.hc_post')
        self.hc_mix_issue(L,'ffn')
        self.hc_pre('PA','X',f'L{L}.ffn_norm','SS')
        self.rmsnorm('X',D,0,'XN',f'L{L}.ffn_norm',have_ss='SS')
        self.moe(L,hook=lambda:self.hc_mix_finish(L,'ffn'))
        self.hc_post('YALL','POF','CF',f'L{L}.hc_post')
        self.emit(dict(unit=I.UNIT_END,wait=31),set(),set(),'end')
        prog=P.schedule(self.prog)
        for f,(_,rd,wr,_) in zip(prog,self.prog):f['_reads'],f['_writes']=rd,wr
        return prog


def head_descriptors():
    b=FullLayerBuilder(0);v=b.V;v['LOGITS']=v['SLOT2']
    b.hc_pre('PF','X','head','SS')
    b.rmsnorm('X',5120,0,'XN','head',have_ss='SS')
    mat=dict(base=0,n=32320,k=5120,tiles=R.cdiv(R.cdiv(32320,16*8),4),split=1,macs=32320*5120)
    b.me(mat,v['XN'],v['LOGITS'],{'XN'},{'LOGITS'},'head',me_round=0,me_amax=1,me_oen=1)
    b.emit(dict(unit=I.UNIT_END,wait=31),set(),set(),'end')
    inst=P.schedule(b.prog)
    for f,(_,rd,wr,_) in zip(inst,b.prog):f['_reads'],f['_writes']=rd,wr
    for f in inst:I.encode(full_shape=True,**f)
    return jsonable(inst)


def functional_ops(layer):
    p=f'L{layer}';ops=[]
    if layer in R.ENGRAM:ops.append(dict(kind='engram',layer=layer,output=p+'.engram'))
    ops.extend(dict(kind=k,layer=layer,output=p+'.'+k) for k in
               ['attn_mix','attn_norm','attention','attn_post','ffn_mix','ffn_norm','moe','ffn_post'])
    return ops


def matrix_contracts(layer, builder):
    """Physical addresses/images NULL; mathematical slices are executable contracts."""
    out=[]
    for key,m in list(builder.lay.mat.items())+list(builder.lay.qmat.items()):
        if not isinstance(key,tuple) or key[0]!=layer or not isinstance(m,dict):continue
        if 'w13' in key:continue
        k=m.get('nb',m.get('k',0))* (32 if 'nb' in m else (8 if 'fn' in key else m.get('split',1)))
        out.append({'logical_key':list(key),'rows_per_rank':m.get('n'),'input_elements':k,
                    'MACs_per_rank':m.get('macs'),'engine':'QE' if 'nb' in m else ('HE' if 'fn' in key else 'ME'),
                    'dtype':'FP4' if m.get('fp4') else ('FP8_blockscaled' if 'nb' in m else ('FP32' if 'fn' in key else 'BF16_in_FP32_bank_words')),
                    'actual_ROM_descriptor':None,'actual_ROM_image_sha256':None,
                    'functional_base_placeholder':m.get('base'),'expert_selection':'runtime router EID, ascending6' if 'exp' in key else None})
    return out


def build_program(*, opt_in=False):
    if not opt_in:raise ValueError('explicit opt_in required for unbound functional program')
    pins=source_pins()
    if G.FUSE or not G.chunked('me') or not G.chunked('qe') or not G.chunked('su'):
        raise ValueError('functional program requires chunk8 and FUSE empty')
    config=json.loads((ROOT/CONFIG).read_text())
    if config['n_layers']!=40 or config['kv_source_layers']!=R.KV_SRC or config['index_source_layers']!=R.IDX_SRC:
        raise ValueError('golden topology drift')
    stages=[];ops=[dict(kind='embedding',output='initial_h_pre')]
    old=I.SU_LANES;I.SU_LANES=8
    try:
        for L in range(40):
            b=FullLayerBuilder(L);inst=b.build_layer();ops.extend(functional_ops(L))
            coll=[{'instruction':i,'tag':f['_tag'],'op':f['coll_op'],'n':f['coll_n'],
                   'k':f.get('coll_k',0),'round':f.get('coll_rnd',0),'source':f['coll_src'],
                   'destination':f['coll_dst'],'sequence':f.get('coll_seq'), 'actual_transport_binding':None,'input_bytes_per_rank':f['coll_n']*(8 if f['coll_op']==I.COLL_TOPK_MERGE else 4),
                   'output_bytes_per_rank':(f.get('coll_k',0)*4 if f['coll_op']==I.COLL_TOPK_MERGE else f['coll_n']*(16 if f['coll_op']==I.COLL_ALL_GATHER else 4)),
                   'port_bits_per_cycle':None,'service_cycles':None}
                  for i,f in enumerate(inst) if f['unit']==I.UNIT_COLL]
            stages.append({'layer':L,'ratio':R.RATIO[L],
                'kv_source':max((x for x in R.KV_SRC if x<=L),default=None) if R.RATIO[L] else None,
                'index_source':max((x for x in R.IDX_SRC if x<=L),default=None) if R.RATIO[L] else None,
                'instructions':jsonable(inst),'runtime_actions':b.actions,'collectives':coll,
                'constant_contracts':[{'name':name,'elements':n,'replicated':True,'actual_CROM_base':None,'image_sha256':None} for name,n in [('attn_norm',5120),('ffn_norm',5120),('q_norm',1280),('kv_norm',512),('gate.bias',384),('hc_attn_base',24),('hc_attn_scale',3),('hc_ffn_base',24),('hc_ffn_scale',3)]]+([{'name':'compressor.norm','elements':512,'actual_CROM_base':None},{'name':'indexer.k_norm','elements':128,'actual_CROM_base':None}] if L in R.KV_SRC else []),
                'rank_head_constants':{'name':'attn_sink','elements':16,'head_start':'rank*16','actual_CROM_base':None},
                'matrices':matrix_contracts(L,b),'scratch_map':b.V,'scratch_elements':b.scratch_end,'scratch_fits_existing_2p19_VM':b.scratch_end<=2**19,
                'inputs':['previous.h','previous.pre','persistent.window', 'persistent.CKV/IK/slots','position.sel/cand'],
                'outputs':['h','pre','window_written','CKV/IK_visible_if_group_complete','position.sel/cand'],
                'runtime_barriers':{'CKV_source_sequence':['id_done+enc_done','prelease drain prior old jobs/returns while C/W/P consumers stay enabled','exclusive all32PC lease','9 actual burst-visible writes','publish row','f_job'],
                  'deadlock_rule':'Never wait for new f_done while f_job is withheld; drain only prior epochs',
                  'ID_table_lifetime':'No new sel_v while prior fetch/responses/AG still use table; reserve K512 rank rows and finite hop credits before fetch',
                  'before_GO':'step_ready: producer inputs + source state + destination credits reserved',
                  'after_END':'step_done: all actual KV burst fences + vector/collective/consumer drains; END alone insufficient',
                  'actual_binding':None},
                'boundary':{'replicated_per_rank':True,'h_shape':[4,5120],'h_BF16_bytes':40960,
                  'pre_FP32_bytes':16,'packed_bytes':40976,'FP32_VM_bytes':81936,'latency_cycles':None}})
    finally:I.SU_LANES=old
    ops.extend([dict(kind='head_norm',output='head.x'),dict(kind='head_tp4',output='head.logits'),
                dict(kind='global_argmax',output='next_token'),dict(kind='complete',output='DONE')])
    for i,op in enumerate(ops):
        op['id']=i;op['depends_on']=[] if i==0 else [i-1]
    return {'schema':'opentallas.w11.dsrom-full-tp4-functional-program.v1',
        'status':'COMPLETE_FUNCTIONAL_PROGRAM_HARDWARE_BINDINGS_UNRESOLVED','opt_in':True,
        'source_pins':pins,'tp':4,'layers':40,'arithmetic':'chunk8, FUSE=[], force=None',
        'functional_ops':ops,'stages':stages,
        'head':{'instructions':head_descriptors(),'weight_shape':[129280,5120],'rank_rows':32320,'dot_input_elements':5120,
                'partition':'contiguous output rows only; no K split','logit_dtype':'FP32','rank_offset':'rank*32320',
                'global_argmax':'max logit, tie lowest global vocabulary ID; reject NaN',
                'ROM_image':None,'collective_binding':None,'cycles':None},
        'embedding':{'weight_shape':[129280,5120],'broadcast':'replicated BF16 row into4 HC copies per rank',
                     'initial_pre':[1,0,0,0],'actual_image':None},
        'persistent_state':['token history','40 window rings','4 CKV stores','4 IK stores','3 ratio2 open slots',
                            'per-position selection from latest index source','per-position candidate mask fromL20'],
        'consumer_cost_contract':{'scope':'Per-stage matrices carry rank-local MACs/shapes/dtypes; collectives carry actual descriptor FP32 VM input/output bytes. Engine, ROM/Engram port rates, routes and event calendars unresolved.',
              'embedding_BF16_bytes_per_rank':10240,'stage_h_pre_packed_bytes_per_rank':40976,
              'Engram_raw_bytes_per_layer':6336,'Engram_decoded_BF16_bytes_per_layer':12288,
              'Engram_projection_FP32_VM_bytes_per_rank':25600,'Engram_gather_FP32_VM_output_bytes_per_rank':102400,
              'head_MACs_per_rank':32320*5120,'head_FP32_logit_bytes_per_rank':32320*4,
              'head_final_argmax_payload_fields':['FP32 value','u32 global ID'],'head_pair_payload_bits_per_rank':64,
              'head_argmax_transport_or_cycles':None,'ROM_physical_word_addresses':None,'Engram_physical_home':None},
        'functional_execution_scope':'Layers interpreted with golden composite arithmetic and causal producer state; head explicitly row-sharded TP4. New multi-rank ISA/data transport execution remains untested and unbound.',
        'word_encoding':{'profile_bits':2048,'templates':'ISA descriptors with zero unbound addresses; no executable image export',
                         'runtime_actions':'software functional/dependency sideband, not ISA opcodes'},
        'complete_functional_execution_available':True,'full_shape_numerical_test_run':False,
        'complete_encoded_hardware_program_ready':False,'engine_RTL_build_ready':False,'physical_admission':False,
        'full_token_cycles':None,'full_token_rate':None,'jobs_launched':0,'adopt':False}


def validate_program(program):
    expected=['embedding']
    for L in range(40):expected.extend(op['kind'] for op in functional_ops(L))
    expected.extend(['head_norm','head_tp4','global_argmax','complete'])
    ops=program['functional_ops']
    if program['layers']!=40 or program['tp']!=4 or [x['kind'] for x in ops]!=expected:
        raise ValueError('incomplete functional program')
    wanted_layers=[L for L in range(40) for _ in functional_ops(L)]
    if [o['layer'] for o in ops if 'layer' in o]!=wanted_layers:raise ValueError('layer order')
    for i,o in enumerate(ops):
        if o['id']!=i or o['depends_on']!=([] if i==0 else [i-1]):raise ValueError('broken dependency')
    if [s['layer'] for s in program['stages']]!=list(range(40)):raise ValueError('stage order')
    if program['head']['dot_input_elements']!=5120:raise ValueError('head input split')
    for s in program['stages']:
        L=s['layer']
        if s['ratio']!=R.RATIO[L]:raise ValueError('ratio drift')
        for field,sources in [('kv_source',R.KV_SRC),('index_source',R.IDX_SRC)]:
            wanted=max((x for x in sources if x<=L),default=None) if R.RATIO[L] else None
            if s[field]!=wanted:raise ValueError('source alias')
    return True


def tp_head(weight, x):
    """Each rank evaluates full-K rows in golden order, then gathers logits."""
    n=len(weight);ends=[n*r//4 for r in range(5)]
    return np.concatenate([G.mv(weight[ends[r]:ends[r+1]],x) for r in range(4)])


def lowest_argmax(logits):
    a=np.asarray(logits,dtype=np.float32)
    if a.ndim!=1 or not len(a) or not np.isfinite(a).all():raise ValueError('nonfinite/empty logits')
    return int(np.argmax(a))


def execute(program, model, tokens, position, state, traces=None):
    """Interpret causal functional ops on actual model weights/state, without force.

    Model composites attention/MoE preserve golden numerical primitives; descriptor
    templates and physical TP transport are separately unqualified. This is a
    software reference executor, not a cycle or RTL simulator.
    """
    validate_program(program)
    if model.L!=program['layers'] or G.FUSE or G.ARITH!='chunk8':raise ValueError('model/program mismatch or arithmetic fusion')
    oldlen=len(state['tokens']);state['tokens'].extend(map(int,tokens))
    ctxs=[{'pos':position+j,'hist':state['tokens'][:oldlen+j+1],
           'h':np.repeat(model.w['embed.weight'][t][None,:],model.hc,axis=0).astype(np.float32),
           'pre':np.array([1,0,0,0],np.float32)} for j,t in enumerate(tokens)]
    traces=traces if traces is not None else [None]*len(ctxs)
    if len(traces)!=len(ctxs):raise ValueError('trace extent')
    for op in program['functional_ops']:
        kind=op['kind'];L=op.get('layer')
        if kind in ('embedding','complete'):continue
        for c,tr in zip(ctxs,traces):
            h=c['h']
            if kind=='engram':
                c['h']=model.engram_layer(h,L,c['hist'])
                if tr is not None:tr[f'L{L}.engram']=c['h']
            elif kind=='attn_mix':
                c['res']=h;c['a_pre'],c['a_post'],c['a_comb']=model.hc_mixes(h,L,'attn')
            elif kind=='attn_norm':
                c['x']=G.rmsnorm_fold(model.hc_pre(h,c['pre']),model.lw(L,'attn_norm.weight'),model.eps)
                if tr is not None:tr[f'L{L}.attn_norm']=c['x']
            elif kind=='attention':
                c['y']=model.attention(L,c['x'],c['pos'],state,tr,c)
                if tr is not None:tr[f'L{L}.attn']=c['y']
            elif kind=='attn_post':c['h']=model.hc_post(c['y'],c['res'],c['a_post'],c['a_comb'])
            elif kind=='ffn_mix':
                c['res']=h;c['f_pre'],c['f_post'],c['f_comb']=model.hc_mixes(h,L,'ffn')
            elif kind=='ffn_norm':
                c['x']=G.rmsnorm_fold(model.hc_pre(h,c['a_pre']),model.lw(L,'ffn_norm.weight'),model.eps)
                if tr is not None:tr[f'L{L}.ffn_norm']=c['x']
            elif kind=='moe':
                c['y']=model.moe(L,c['x'],tr)
                if tr is not None:tr[f'L{L}.ffn']=c['y']
            elif kind=='ffn_post':
                c['h']=model.hc_post(c['y'],c['res'],c['f_post'],c['f_comb']);c['pre']=c['f_pre']
                if tr is not None:tr[f'block{L}'],tr[f'pre{L}']=c['h'],c['pre']
            elif kind=='head_norm':
                c['x']=G.rmsnorm_fold(model.hc_pre(h,c['pre']),model.w['norm.weight'],model.eps)
                if tr is not None:tr['final_norm']=c['x']
            elif kind=='head_tp4':
                c['logits']=tp_head(model.w['head.weight'],c['x'])
                if tr is not None:tr['logits']=c['logits']
            elif kind=='global_argmax':c['next_token']=lowest_argmax(c['logits'])
            else:raise ValueError('unknown functional op: '+kind)
    return {'logits':[c['logits'] for c in ctxs],'next_tokens':[c['next_token'] for c in ctxs],
            'claim':'software functional execution only; actual TP transport/RTL unqualified'}


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--emit-functional-program',action='store_true');a=ap.parse_args()
    if not a.emit_functional_program:ap.error('--emit-functional-program is required; no hardware admission')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build_program(opt_in=True),indent=2)+'\n')
