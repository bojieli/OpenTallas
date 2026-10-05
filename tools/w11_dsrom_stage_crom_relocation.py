"""Exact stage-local ISA base-field relocation, diagnostic only until admitted."""
import argparse
import gzip
import json
from pathlib import Path
import hdc_isa_v41 as I
import w11_dsrom_stage_crom_union as U

MODEL_PIN='3977c33920751cbd40db970ae3d87a7046e0d658'
UNION_PIN=('8e28902ff','results/uarch/w11_stage_crom_union_20261001/read_union.json.gz')
PREFIX='results/quality/w16_engram_initializer_20261001/'

def authorities(candidates=None):
    models={}
    refs=[]
    for banks in (6,9,16):
        model,ref=U.load((MODEL_PIN,PREFIX+f'stage_local{banks}.json'))
        models[banks]=model;refs.append(ref)
    if candidates is not None and candidates!=models:
        raise ValueError('immutable stage geometry/catalog/value authority mismatch')
    return models,refs

def require_publication(candidates=None):
    models,_=authorities(candidates)
    for model in models.values():
        for rank in model['rank_values']:
            for home in rank['homes']:
                if home['source_invalid_words'] or home['complete_image_SHA256'] is None:
                    raise ValueError('L1 invalid immutable image slots; publication prohibited')
        if model['fit']['physical_admission'] is not True:
            raise ValueError('actual physical home/catalog/service not admitted')
    return True

def build(candidates=None, diagnostic_dir=None):
    models,modelrefs=authorities(candidates)
    union,uref=U.load(UNION_PIN,True)
    program,pref=U.load(U.PROGRAM)
    isa=U.read('d2c28c279','tools/hdc_isa_v41.py')
    if U.sha(isa)!=U.sha(Path(I.__file__).read_bytes()): raise ValueError('ISA source identity')
    ranks=[]
    for rank in union['ranks']:
        rid=rank['rank'];source=program['ranks'][rid]
        original=gzip.decompress(U.read(U.PROGRAM[0],U.PROGRAM[1].removesuffix('.json')+f'.rank{rid}.templates.bin.gz'))
        if U.sha(original)!=source['encoded_template_sha256'] or U.sha(original)!=rank['original_program_sha256']:
            raise ValueError('original encoded rank identity')
        patched=bytearray(original);changes=[];stages=[];allowed={};covered=set();operands=0
        for stage in rank['stages']:
            layer=stage['layer'];addresses=sorted(a for lo,hi in stage['ranges'] for a in range(lo,hi))
            local={a:i for i,a in enumerate(addresses)}
            if len(local)!=stage['unique_words'] or U.address_sha(local)!=stage['global_sorted_addressSHA']:
                raise ValueError('immutable stage union identity')
            home_refs=[]
            for banks,model in models.items():
                mstage=next(s for s in model['stages'] if s['layer']==layer)
                home=next(h for h in model['rank_values'][rid]['homes'] if h['layer']==layer)
                if mstage['global_address_SHA256']!=stage['global_sorted_addressSHA'] or mstage['unique_words']!=len(local):
                    raise ValueError('geometry stage union mismatch')
                if {c['PC'] for c in mstage['commands']}!={c['pc'] for c in stage['commands']}:
                    raise ValueError('catalog command coverage mismatch')
                if home['source_invalid_words']!=stage['invalid_words']:
                    raise ValueError('image validity mismatch')
                home_refs.append(dict(banks=banks,complete_image_SHA256=home['complete_image_SHA256'],
                    diagnostic_payload_SHA256=home['diagnostic_placeholder_payload_SHA256'],
                    validity_SHA256=home['validity_SHA256'],request_catalog_SHA256=mstage['request_catalog_word_SHA256'],
                    fill_catalog_SHA256=mstage['fill_catalog_word_SHA256'],
                    physical_owner=None,actual_service_bound=False))
            invalid_local=U.ranges(local[a] for lo,hi in stage['L1invalid_ranges'] for a in range(lo,hi))
            for model in models.values():
                ms=next(s for s in model['stages'] if s['layer']==layer)
                if ms['invalid_L1_local_ranges']!=invalid_local: raise ValueError('local invalid extent')
            bindings=[]
            for command in stage['commands']:
                pc=command['pc'];covered.add(pc)
                word=int.from_bytes(original[pc*256:(pc+1)*256],'little')
                f=I.decode(word,full_shape=True);new=word;mask=0
                for operand in command['operands']:
                    axis=operand['operand'];oldbase=f[axis+'_base']
                    globalbase=oldbase
                    if operand['kind']=='unbound_generated':
                        globalbase+=508800 if layer==1 else 529280
                    base=local[globalbase]
                    offsets={o*f[axis+'_so']+(i//2 if axis in 'bd' and f['b_half'] else i)*f[axis+'_si']
                        for o in range(f['su_nout']) for i in range(f['su_nin'])}
                    global_reads={globalbase+delta for delta in offsets}
                    if U.ranges(global_reads)!=operand['global_ranges']:
                        raise ValueError('operand independent global address proof')
                    if any(local[globalbase+delta]!=base+delta for delta in offsets):
                        raise ValueError('stage packing not affine; cannot preserve stride')
                    bit,width=I.FULL_LAYOUT[axis+'_base'];fieldmask=((1<<width)-1)<<bit
                    if not 0<=base<1<<width: raise ValueError('local base field overflow')
                    mask|=fieldmask;new=(new&~fieldmask)|(base<<bit);operands+=1
                    bindings.append(dict(pc=pc,operand=axis,tensor=operand['tensor'],
                        original_encoded_base=oldbase,global_base=globalbase,diagnostic_local_base=base,
                        stride_and_half_unchanged=True,source_valid=operand['source_valid'],
                        global_ranges=operand['global_ranges'],local_ranges=U.ranges(base+d for d in offsets),
                        published_base=None))
                if (new^word)&~mask: raise AssertionError('non-base instruction bits changed')
                patched[pc*256:(pc+1)*256]=new.to_bytes(256,'little');allowed[pc]=mask
            stages.append(dict(layer=layer,rank=rid,unique_words=len(local),
                global_sorted_addressSHA=stage['global_sorted_addressSHA'],
                invalid_local_ranges=invalid_local,bindings=bindings,candidate_homes=home_refs))
        if len(covered)!=491 or operands!=731: raise ValueError('all source operand coverage')
        for pc in range(len(original)//256):
            old=int.from_bytes(original[pc*256:(pc+1)*256],'little')
            new=int.from_bytes(patched[pc*256:(pc+1)*256],'little')
            if (new^old)&~allowed.get(pc,0): raise AssertionError('unexpected program bit mutation')
            if new!=old: changes.append(pc)
        name=f'rank{rid}.stage-local.NOT_RUNNABLE.bin.gz'
        if diagnostic_dir is not None:
            out=Path(diagnostic_dir);out.mkdir(parents=True,exist_ok=True)
            if (out/name).exists(): raise ValueError('preserve existing diagnostic evidence')
            (out/name).write_bytes(gzip.compress(bytes(patched),mtime=0))
        ranks.append(dict(rank=rid,original_program_sha256=U.sha(original),
            diagnostic_program_sha256=U.sha(patched),diagnostic_file=name if diagnostic_dir is not None else None,
            published_program_sha256=None,source_operand_count=operands,CROM_command_count=len(covered),
            changed_pcs=changes,stages=stages,runnable=False))
    return dict(schema='w11.stage-local-CROM-relocation.v1',source_pins=[uref,pref]+modelrefs,
        ISA_sha256=U.sha(isa),ranks=ranks,
        proof='Every coefficient local address equals ordinal(global address), retaining every stride/half/predicate/arithmetic/rounding/control bit; only declared CROM source base fields may change.',
        physical_home_and_rank_replication=None,adopted_geometry=None,
        actual_service_bound=False,image_admission=False,hardware_admission=False,
        L1_source_authority=None,publication_blocked=True,checkpoint_payload_reads=0,
        token_latency=None)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    parser.add_argument('--diagnostic-dir');args=parser.parse_args()
    path=Path(args.output)
    if path.exists(): raise ValueError('preserve existing evidence')
    path.write_bytes(gzip.compress(json.dumps(build(diagnostic_dir=args.diagnostic_dir),sort_keys=True).encode(),mtime=0))
