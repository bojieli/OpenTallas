"""Independent encoded-operand stage read unions and retained value provenance."""
import argparse
import collections
import gzip
import hashlib
import json
import struct
import subprocess
from pathlib import Path
import hdc_isa_v41 as I

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ('4080bb5fd','results/rtl/w17_connected_token_preparation_20261001/full40_crom_bound_templates_v2.json')
DEMAND = ('f4bce8fa0','results/uarch/w11_crom_demand_20261001/demand_v2.json.gz')
MANIFEST = ('70f73928f','results/uarch/w11_dsrom_crom_writer_20261001/manifest.json.gz')
LAYOUT = ('2a4980765','results/quality/w16_engram_initializer_20261001/frozen_closure.json')

def sha(raw): return hashlib.sha256(raw).hexdigest()

def read(ref, path):
    return subprocess.check_output(['git','show',ref+':'+path],cwd=ROOT)

def load(pin, compressed=False):
    raw=read(*pin)
    if compressed: raw=gzip.decompress(raw)
    return json.loads(raw), dict(commit=subprocess.check_output(['git','rev-parse',pin[0]],cwd=ROOT).decode().strip(),path=pin[1],decoded_sha256=sha(raw))

def ranges(values):
    result=[]
    for a in sorted(values):
        if result and result[-1][1]==a: result[-1][1]+=1
        else: result.append([a,a+1])
    return result

def address_sha(values):
    return sha(b''.join(struct.pack('<I',a) for a in sorted(values)))

def operand_addresses(fields, axis):
    if fields['su_d_nin'] or fields['su_d_nout']:
        raise ValueError('dynamic dimensions unbound')
    return {fields[axis+'_base'] + o*fields[axis+'_so'] +
            (i//2 if axis in 'bd' and fields['b_half'] else i)*fields[axis+'_si']
            for o in range(fields['su_nout']) for i in range(fields['su_nin'])}

def build(candidate_demand=None):
    program,pref=load(PROGRAM)
    demand,dref=load(DEMAND,True)
    manifest,mref=load(MANIFEST,True)
    layout,lref=load(LAYOUT)
    if candidate_demand is not None and candidate_demand!=demand:
        raise ValueError('immutable demand identity mismatch')
    isa=read('d2c28c279','tools/hdc_isa_v41.py')
    if sha(isa)!=sha(Path(I.__file__).read_bytes()): raise ValueError('ISA source identity')
    outputs=[]
    for rank in program['ranks']:
        rid=rank['rank']; records={r['global_instruction']:r for r in demand['ranks'][rid]['records']}
        binary=gzip.decompress(read(PROGRAM[0],PROGRAM[1].removesuffix('.json')+f'.rank{rid}.templates.bin.gz'))
        if sha(binary)!=rank['encoded_template_sha256']: raise ValueError('rank program identity')
        constants=manifest['rank_images'][rid]['constants']
        stages=rank['stages']+[dict(layer='head',instruction_count=7,bindings=rank['head_bindings'],unbound=[])]
        result=[]; global_union=set(); address_stages=collections.defaultdict(set)
        tensor_stages=collections.defaultdict(set); visited=set(); offset=0; operand_count=0
        for stage in stages:
            union=set(); invalid=set(); grouped=collections.defaultdict(list); provenance=[]; commands=[]
            for b in stage['bindings']:
                if b['kind']=='checkpoint_CROM': grouped[b['instruction']].append(b)
            for b in stage['unbound']:
                grouped[b['instruction']].append(dict(b,kind='unbound_generated',tensor=f"L{stage['layer']}.engram.q_times_k"))
            for localpc,bindings in sorted(grouped.items()):
                pc=offset+localpc; visited.add(pc); rec=records[pc]
                if rec['layer']!=stage['layer'] or rec['instruction']!=localpc: raise ValueError('PC/layer identity')
                fields=I.decode(int.from_bytes(binary[pc*256:(pc+1)*256],'little'),full_shape=True)
                if rec['pred']!=fields['pred']: raise ValueError('predicate identity')
                expected={o['operand']:o for o in rec['operand_demands']}
                if set(expected)!={b['operand'] for b in bindings}: raise ValueError('all operand coverage')
                operands=[]
                for b in bindings:
                    axis=b['operand']; o=expected[axis]; symbolic=operand_addresses(fields,axis)
                    if ranges(symbolic)!=o['unique_address_ranges'] or len(symbolic)!=o['unique_words']:
                        raise ValueError('independent address union mismatch')
                    if o['tensor']!=b['tensor'] or o['kind']!=b['kind'] or fields[axis+'_src']!=I.SRC_CLO:
                        raise ValueError('operand source/tensor identity')
                    if b['kind']=='checkpoint_CROM':
                        c=constants[b['tensor']]; addresses=symbolic
                        if not all(c['base_word']<=a<c['end_word_exclusive'] for a in addresses):
                            raise ValueError('retained tensor extent')
                        source=dict(kind='retained_checkpoint_slice',manifest=mref,
                            tensor_base=c['base_word'],tensor_end=c['end_word_exclusive'],
                            output_slice_sha256=c['output_slice_sha256'],source=c['source'])
                        valid=True; operand_count+=1
                    else:
                        if stage['layer'] not in (1,14) or axis!='b' or len(symbolic)!=20480 or ranges(symbolic)!=[[0,20480]]:
                            raise ValueError('generated product identity')
                        base=layout['layout']['invalid_source_hole'][0] if stage['layer']==1 else layout['layout']['L14_span'][0]
                        addresses={base+a for a in symbolic};valid=stage['layer']==14
                        source=dict(kind='retained_generated_product' if valid else 'INVALID_MISSING_PARAMETER_PAIR',
                            product_commit='60545ff45' if valid else None,
                            product_path='results/uarch/w11_engram_product_source_20261001/L14.product.crom64-logical-slice.bin.gz' if valid else None,
                            product_sha256='f2297940486c2604a7a4baf8887ed319c264f77cb10ccc3f164c16e01182f377' if valid else None,
                            raw_parameter_authority=None if not valid else '821709d3d88772edd88cba5e28039a1295dbc0fc')
                    union.update(addresses)
                    if not valid: invalid.update(addresses)
                    tensor_stages[b['tensor']].add(str(stage['layer']))
                    item=dict(operand=axis,tensor=b['tensor'],kind=b['kind'],
                        original_encoded_base=fields[axis+'_base'],outer_stride=fields[axis+'_so'],
                        inner_stride=fields[axis+'_si'],half_inner=bool(axis in 'bd' and fields['b_half']),
                        unique_words=len(addresses),global_ranges=ranges(addresses),
                        global_sorted_addressSHA=address_sha(addresses),source_valid=valid,provenance=source)
                    operands.append(item);provenance.append(dict(pc=pc,**item))
                commands.append(dict(pc=pc,local_pc=localpc,pred=fields['pred'],nin=fields['su_nin'],nout=fields['su_nout'],operands=operands))
            for a in union: address_stages[a].add(str(stage['layer']))
            global_union.update(union)
            result.append(dict(layer=stage['layer'],rank=rid,stage_pc_span=[offset,offset+stage['instruction_count']],
                commands=commands,command_count=len(commands),unique_words=len(union),ranges=ranges(union),
                global_sorted_addressSHA=address_sha(union),L1invalid_ranges=ranges(invalid),invalid_words=len(invalid),
                valid_words=len(union-invalid),L14valid=stage['layer']==14,
                global_constant_operands=[p for p in provenance if p['kind']=='checkpoint_CROM' and not p['tensor'].startswith('layers.')],
                physical_home=None,local_repacked_image_sha256=None,actual_service_bound=False))
            offset+=stage['instruction_count']
        if offset!=4778 or visited!=set(records) or len(visited)!=491 or operand_count!=729:
            raise ValueError('complete stage/PC/operand coverage')
        if global_union!=set(range(549760)): raise ValueError('complete logical read union')
        outputs.append(dict(rank=rid,original_program_sha256=sha(binary),stages=result,
            command_count=len(visited),bound_operand_count=operand_count,generated_operand_count=2,
            global_unique_words=len(global_union),sum_stage_unique_words=sum(s['unique_words'] for s in result),
            crossstage_address_copies=[dict(address=a,stages=sorted(ss)) for a,ss in address_stages.items() if len(ss)>1],
            crossstage_tensor_copies=[dict(tensor=t,stages=sorted(ss)) for t,ss in tensor_stages.items() if len(ss)>1],
            max_stage_words=max(s['unique_words'] for s in result)))
    return dict(schema='w11.stage-CROM-read-union.v1',source_pins=[pref,dref,mref,lref],ISA_sha256=sha(isa),ranks=outputs,
        stage_homes_count=164,max_regular_stage_words=33648,
        scope='Independent full encoded operand rectangular read union; every491 command and731 source operands per rank. RoPE held-cache reads remain separate provider; physical service, replication and local remap unqualified.',
        checkpoint_payload_reads=0,hardware_admission=False,image_admission=False,
        geometry_credit=False,physical_bank_count=None,token_latency=None)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    out=Path(a.output)
    if out.exists(): raise ValueError('preserve existing evidence')
    out.write_bytes(gzip.compress(json.dumps(build(),sort_keys=True).encode(),mtime=0))
