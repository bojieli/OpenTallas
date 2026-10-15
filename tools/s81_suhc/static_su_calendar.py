#!/usr/bin/env python3
"""Compile explicit native SU edge events; never infer durations from graph prices.

Each job is source-bound to measured native evidence and contains all reads,
responses, writes, announce and completion edges. Missing operations or evidence
reject the entire calendar. The compiler emits no operands or arithmetic values.
VM ages are edges of the VM clock, so callers must first lower the actual 3:4
clock phase using s81_compile_schedule; treating L12 as 12 SU edges is invalid.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HIER = 'rtl/dsrom_sys/s81_suhc/hier/'
OPS = dict(QN=0, KV=1, QB=2, SW=3, SE=4, SO=5, GQ=6, GK=7,
           RA=8, RB=9, QR=10, RW=11, CN=12, IK=13, MOE=15)
SOURCES = {k: [HIER+'dsfd_sp_su_static.sv', HIER+'ot_s81_su_calendar_ctl.sv'] for k in OPS}
for ks, files in [('QN GQ', ['ot_s81_su_qn.sv']), ('KV GK', ['ot_s81_su_kv.sv','ot_s81_su_qn.sv']),
                  ('QB', ['ot_s81_su_qb.sv']), ('SW', ['ot_s81_su_sw.sv','ot_s81_su_qb.sv']),
                  ('SE SO', ['ot_s81_su_sm.sv']), ('RA RB QR RW', ['ot_s81_su_rxt.sv']),
                  ('CN IK', ['ot_s81_su_kv.sv','ot_s81_su_cn_ik.sv']),
                  ('MOE', ['ot_s81_su_moe_sum_static.sv'])]:
    for k in ks.split(): SOURCES[k] += [HIER+f for f in files]

COMMON_SOURCES = ['rtl/hdc/ot_hdc_fastfp.sv',
 'rtl/hdc/ot_hdc_fp32_f12.sv',
 'rtl/hdc/ot_hdc_fp32_mul_lat.sv',
 'rtl/hdc/ot_hdc_fp32_add_lat.sv',
 'rtl/hdc/ot_hdc_prefix.sv',
 'rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv',
 'rtl/hdc/ot_hdc_fastfp_lat_f12.sv',
 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_ctl.sv',
 'rtl/dsrom_sys/s81_suhc/ot_s81_su_rx.sv',
 'rtl/dsrom_sys/s81_suhc/ot_s81_su_rw.sv',
 'rtl/hdc/v41x/ot_hdc_v41x_spshort.sv',
 'rtl/hdc/v41x/ot_dsrom_su_norm.sv',
 'rtl/hdc/v41x/ot_dsrom_su_swiglu.sv',
 'rtl/hdc/v41x/ot_dsrom_su_f12.sv',
 'rtl/hdc/v41x/ot_dsrom_su_fdiv_f12.sv',
 'rtl/hdc/v41x/ot_dsrom_su_softmax.sv',
 'rtl/hdc/v41x/ot_dsrom_su_softmax_add.sv',
 'rtl/hdc/v41x/ot_dsrom_su_softmax_add6.sv',
 'rtl/hdc/v41x/ot_dsrom_su_softmax_exp6.sv',
 'rtl/hdc/v41x/ot_dsrom_su_softmax_f12r.sv',
 'rtl/hdc/v41x/ot_dsrom_su_softmax_m9.sv',
 'rtl/hdc/v41x/ot_dsrom_su_add6.sv',
 'rtl/hdc/ot_hdc_delay.sv',
 'rtl/hdc/ot_hdc_sfu.sv',
 'rtl/hdc/ot_hdc_fpu.sv',
 'rtl/hdc/ot_hdc_fp32_mul_pipe.sv',
 'rtl/proto/ot_fp32_add_rne_pipe.sv',
 'rtl/hdc/v41/ot_hdc_fsqrt.sv',
 'rtl/hdc/v41/ot_hdc_fdiv.sv',
 'rtl/hdc/v41/ot_hdc_softplus.sv',
 'rtl/hdc/v41x/ot_hdc_v41x_sfu.sv',
 'rtl/hdc/v41/ot_hdc_actquant.sv',
 'rtl/hdc/v41x/ot_dsrom_aq12.sv',
 'rtl/hdc/v41x/ot_dsrom_divc.sv',
 'rtl/hdc/ot_sram_dline.sv',
 'rtl/hdc/ot_sram_bank.sv',
 'rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv',
 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_tile.sv',
 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_norm_lg.sv']
COMMON_SOURCES += [
    HIER+'ot_s81_su_moe_sum_static.sv',
    'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
    'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v']
for paths in SOURCES.values():
    paths.extend(p for p in COMMON_SOURCES if p not in paths)
    paths.extend([HIER+'ot_s81_su_calendar_store.sv', HIER+'dsfd_sp_su_static_programmed.sv'])

def row_counts(k, count):
    """Actual production dimensions, including separately masked exponent writes."""
    if not isinstance(count, int) or count < 1: raise ValueError('positive count required')
    if k in ('QN','KV','SO','GQ','GK','CN','IK','MOE') and count!=1: raise ValueError('fixed-shape count must be one')
    if k=='SE' and count>40: raise ValueError('softmax storage NVMAX40 exceeded')
    return {
        'QN': (1,80,40), 'KV': (5,32,26), 'QB': (1,64*count,64*count),
        'SW': (1,128*count,64*count), 'SE': (2,16*count,16*count),
        'SO': (5,512,256), 'GQ': (1,80,0), 'GK': (1,32,0),
        'RA': (1,count,count), 'RB': (1,2*count,count),
        'QR': (5,4*count,4*count), 'RW': (1,count,1),
        'CN': (5,32,48), 'IK': (5,32,8), 'MOE': (0,7*80,80),
    }[k]

def digest(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()

def inventory():
    return dict(schema='opentallas.s81.static-su-inventory.v1', qualified=False,
        shape=dict(QN_N=256,QN_D=1280,KV_N=512,QB_NB=32,SW_W=1024,SM_H=16,SM_LPH=16,S_RD=16,S_WR=16),
        microarchitecture=dict(input_bytes_per_su_edge=1024,output_bytes_per_su_edge=1024,
            read_request_bits=240,response_bits=8208,write_bits=8688,
            calendar_bits_per_su_edge=1024,calendar_controller_flops_upper_bound=512,
            mapped_calendar_default=dict(depth=4096,bytes=524288,macro_64x512_count=128,
                                         canonical_capacity_proven=False),
            control_replica_count=1,physical_slot=None,physical_qualified=False),
        vm=dict(read_slots=16,write_slots=16,response_vm_edges=12,
                commit_observed_vm_edges='11 + bank-prefix (0..2)',macro_write_visibility_edges=None,phase_lowering_required=True,
                source='rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm_static.sv',
                source_sha256=digest('rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm_static.sv')),
        operations={k: dict(kind=v, counts_order=['parameters','operand_reads','masked_writes'],
                            counts_at_count1=row_counts(k,1),
                            sources={p:digest(p) for p in SOURCES[k]},
                            native_duration=None, production_calendar_qualified=False)
                    for k,v in OPS.items()})

def compile_program(program):
    n=program['cycles']
    if not isinstance(n,int) or n<1: raise ValueError('cycles')
    depth=program.get('program_depth',4096)
    if depth<64 or depth&(depth-1) or n>depth: raise ValueError('mapped program capacity exceeded')
    words=[0]*n
    occupied=set()
    def put(c, lo, width, value):
        if not 0<=c<n or not 0<=value<(1<<width): raise ValueError('event bounds')
        bits=((1<<width)-1)<<lo
        if (c,lo) in occupied: raise ValueError('conflicting calendar field')
        occupied.add((c,lo)); words[c] |= value<<lo
    known=inventory()['operations']
    if not program.get('jobs'): raise ValueError('empty production program')
    last_end=-1
    for job in program['jobs']:
        k=job['op']
        if k not in known: raise ValueError('unsupported operation '+k)
        if job.get('sources') != known[k]['sources']: raise ValueError('stale/incomplete source binding '+k)
        # Pinned actual native replay evidence must include every result port.
        e=job['evidence']; p=Path(e['path'])
        if not p.is_absolute(): p=ROOT/p
        if hashlib.sha256(p.read_bytes()).hexdigest()!=e['sha256']: raise ValueError('stale native timing evidence')
        ev=json.loads(p.read_text())
        if ev.get('passed') is not True or ev.get('arithmetic')!='native-rtl' or ev.get('sources')!=job['sources'] or ev.get('op')!=k:
            raise ValueError('not native operation evidence')
        if ev.get('events') != job['events']: raise ValueError('native event timing differs')
        start=job['start']; end=job['done']
        if start<=last_end or end<=start: raise ValueError('overlapping SU jobs')
        last_end=end
        params, rin, wout=row_counts(k,job['count'])
        events=job['events']; reads=events['reads']; responses=events['responses']; writes=events['writes']
        if len(reads)!=params+rin or len(responses)!=len(reads) or len(writes)!=wout:
            raise ValueError('incomplete full-shape port coverage '+k)
        if sorted((x['slot'],x['row']) for x in responses)!=sorted((x['slot'],x['row']) for x in reads):
            raise ValueError('read response identity mismatch')
        if end < max((x['commit_cycle'] for x in writes),default=start): raise ValueError('done before commit')
        put(start,752,1,1); put(start,753,4,OPS[k]); put(start,757,2,job['gain_set'])
        put(start,759,1,int(job['fp4'])); put(start,760,8,job['id'])
        put(end,768,1,1); put(end,769,8,job['tag'])
        mo=events.get('moe_operands',[])
        if len(mo)!=(80 if k=='MOE' else 0): raise ValueError('incomplete MOE operand pulse coverage')
        for pulse in mo:
            if not start<=pulse['cycle']<=end: raise ValueError('MOE pulse outside job')
            put(pulse['cycle'],789,1,1);put(pulse['cycle'],790,14,pulse['output_row'])
        for r in reads:
            c=r['cycle']; s=r['slot']
            if not start<=c<=end or not 0<=s<16: raise ValueError('read outside job')
            if s>=2 and r['row']%4!=s%4: raise ValueError('native VM SU read row colour')
            put(c,s,1,1); put(c,16+14*s,14,r['row'])
        for r in responses:
            if not start<=r['cycle']<=end or not 0<=r['slot']<16: raise ValueError('response outside job')
            put(r['cycle'],240+r['slot'],1,1)
        for w in writes:
            c=w['cycle']; s=w['slot']
            if not start<=c<=w['commit_cycle']<=end or not 0<=s<16: raise ValueError('write outside job')
            put(c,256+s,1,1); put(c,272+14*s,14,w['row']); put(c,496+16*s,16,w['mask'])
    put(n-1,788,1,1)
    return words

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--program',type=Path); ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if a.program:
        words=compile_program(json.loads(a.program.read_text()))
        a.out.write_text(''.join(f'{w:0256x}\n' for w in words))
    else: a.out.write_text(json.dumps(inventory(),indent=2)+'\n')
if __name__=='__main__': main()
