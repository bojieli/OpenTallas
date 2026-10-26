#!/usr/bin/env python3
"""Packing/port/capacity model only; not native RTL or physical qualification."""
import argparse, hashlib, json, random
from pathlib import Path

def study():
    rng = random.Random(31522128)
    chunks = [[] for _ in range(8)]
    for p in range(8):
        begin = p * 3152 + 2128
        bit = begin
        while bit < begin + 1024:
            end = min(begin + 1024, (bit // 256 + 1) * 256)
            chunks[(bit // 256) % 8].append(dict(p=p, beat=bit // 2048,
                dest=bit % 256, source=bit-begin, width=end-bit))
            bit = end
    mem = [[{} for _ in range(8)] for _ in range(8)]
    payload = {}
    max_stripes = max_t_writes = 0
    for g in range(16):
        for p in range(8):
            for t in range(8):
                payload[g,p,t] = rng.getrandbits(1024)
            for wave in range(8):
                touched = set()
                per_bank = {}
                for stripe, cs in enumerate(chunks):
                    for ci,c in enumerate(cs):
                        if c['p'] != p: continue
                        lo=max(c['source'],wave*128)
                        hi=min(c['source']+c['width'],(wave+1)*128)
                        if hi <= lo: continue
                        touched.add(stripe)
                        for t in range(8):
                            per_bank[stripe,t]=per_bank.get((stripe,t),0)+1
                            row=g*len(cs)+ci
                            assert row < 128
                            shift=c['dest']+lo-c['source']
                            mask=((1 << (hi-lo))-1) << shift
                            part=((payload[g,p,t] >> lo) << shift) & mask
                            old=mem[stripe][t].get(row,0)
                            mem[stripe][t][row]=(old & ~mask)|part
                max_stripes=max(max_stripes,len(touched))
                max_t_writes=max(max_t_writes,max(per_bank.values()))
    assert max_stripes <= 2 and max_t_writes == 1
    checks = wrong_stripe = wrong_row = 0
    mask256=(1<<256)-1
    for P in range(1,9):
        for g in range(16):
            for t in range(8):
                expected=sum(payload[g,p,t] << (p*3152+2128) for p in range(P))
                for beat in range((P*3152+2047)//2048):
                    outputs=[]
                    aliased=[]
                    for stripe,cs in enumerate(chunks):
                        chosen=[(ci,c) for ci,c in enumerate(cs) if c['p']<P and c['beat']==beat]
                        assert len(chosen)<=1
                        out=bad=0
                        if chosen:
                            ci,c=chosen[0]
                            mask=((1<<c['width'])-1)<<c['dest']
                            out=mem[stripe][t][g*len(cs)+ci]&mask
                            bad=mem[stripe][t][g*len(cs)+(ci+1)%len(cs)]&mask
                        outputs.append(out);aliased.append(bad)
                    for stripe in range(8):
                        ref=(expected >> (beat*2048+stripe*256))&mask256
                        assert outputs[stripe]==ref
                        wrong_stripe+=outputs[stripe^1]!=ref
                        wrong_row+=aliased[stripe]!=ref
                        checks+=1
    assert wrong_stripe and wrong_row
    macro_area=94.824*41.040
    return dict(scope='CONDITIONAL BF16 consumer-stripe packing/port/capacity model; no actual die stripe map, RTL integration or timing claim',
        integration_scope='Current SM_X graph links collapse vms rr -> SM xw_data2048=8banks*256 (+rq17); these are planning provenance, not elaborated source bindings. Static xload exists only in component test; historical xload throughput bench has one producer feeding32SMs via relay. Proposed stripe banking requires real integration selection before adoption.',
        source_layout=dict(XC=3152,XOFF=2128,Pmax=8,token_t=8,groups=16,word_bits=1024,output_bits=2048),
        chunks=chunks,chunk_counts=[len(c) for c in chunks],rows_per_t_bank=[16*len(c) for c in chunks],
        max_rows=max(16*len(c) for c in chunks),write_proof=dict(input_bits_per_t_wave=128,
            simultaneous_t=8,max_destination_stripes_per_wave=max_stripes,max_writes_per_t_bank_per_edge=max_t_writes,
            independent_t_write_ports_per_leaf=8),
        proposed=dict(consumer_leaves=8,SRAMs_per_leaf=8,total_SRAMs=64,SRAMs_added=32,
            extra_macro_outline_um2=32*macro_area,extra_macro_outline_mm2=32*macro_area/1e6,
            replicas='must bind actual die hierarchy; no multiplied design-area claim'),
        checks=dict(exact_output_stripes=checks,swapped_consumer_stripe_mutant_mismatches=wrong_stripe,
            aliased_chunk_row_mutant_mismatches=wrong_row),
        rejected_shortcuts=['8 t-leaves x 4 old macros leave global 1024-bit OR and 2048-bit pack, so do not localize final consumer pins',
            '40 capacity-pooled macros do not supply 8 simultaneous t writes per consumer leaf'],
        remaining=['actual static xload source integration, replica count and source-pinned consumer mapping first',
            'actual distributed input routes, clocks and fixed compiler calendar',
            'real RTL plus 64 mapped SRAM models and failing mutants',
            'BD quantizers and 8512-FF ring distribution, including exact arithmetic',
            'local partial-word masks must zero inactive output bits; no assumed SRAM initialization',
            'actual views and child window placement; no assumed added-stage latency',
            'actual total clock sink partition; predecessor mapped 57188 FFs',
            'current grant, native pins, TT setup/FF hold/DRC0, composition and total cost'])

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    r=study();src=Path('rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static.sv')
    r['source_sha256']=hashlib.sha256(src.read_bytes()).hexdigest()
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ('chunk_counts','max_rows','proposed','checks')}))
