"""Source-only certificate joining every actual SU-X table to ME/XPF templates.

No consumer RTL/API is changed. Four complete1024b ME templates are emitted
for review, even though the current PW image cannot hold them simultaneously.
The certificate covers affine addresses and unchanged arithmetic fields only.
"""
import argparse,hashlib,json
from pathlib import Path
from collections import Counter
import global_boundary as G

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def build(program,manifest_path,metadata_path):
    words=[int(x,16) for x in Path(program).read_text().split()]
    manifest=json.loads(Path(manifest_path).read_text())
    metadata=json.loads(Path(metadata_path).read_text())
    c=G.layer_contract(program)
    xpfs={x['consumer_pc']:x for x in metadata['xpf_records']}
    templates=[];cases=[];native=[];clone_proofs=[]
    for u in range(4):
        me=list(words);xr=[]
        for name,e in c['epochs'].items():
            original=int(e['word'],16);patched=G.rewrite_me(original,u,e)
            mask=((1<<24)-1)<<G.ISA.LAYOUT['me_xbase'][0]
            if (original^patched)&~mask:raise ValueError('non-address ME field changed')
            me[e['pc']]=patched
            x=xpfs[e['pc']]
            actual=int(x['xpf72'],16);rewritten=G.rewrite_xpf72(actual,u,e)
            if G.get(patched,G.ISA.LAYOUT,'me_xbase') != (rewritten>>1)&((1<<24)-1):
                raise ValueError('ME/XPF disagree')
            xr.append(dict(x,consumer_pc=e['pc'],epoch=name,xpf72=f'{rewritten:018x}'))
        # Native59, arithmetic words, END and all other instructions are exact.
        if me[11]!=words[11]:raise ValueError('native59 word changed')
        templates.append(dict(user=u,programme_hex=[f'{x:0256x}' for x in me],xpf_records=xr))
    for st in manifest['stages']:
        stage=st['stage']
        for u in range(4):
            address_sets={name:[] for name in ('qkv','o','down')}
            owners={name:[] for name in address_sets}
            for sl in st['slices']:
                records=sl['prog_users'][u]
                if any(r['addr']==12 for r in records):raise ValueError('clone slot24 already occupied')
                if any(r['addr']>=6 for r in records):raise ValueError('actual decode uses reserved head/clone namespace')
                source_pair=next(r for r in records if r['addr']==1)
                source_xs=(int(source_pair['payload_hex'],16)>>512)&((1<<457)-1)
                if G.get(source_xs,G.SU_LAYOUT,'dst')!=1 or G.get(source_xs,G.SU_LAYOUT,'d')>>22!=1:
                    raise ValueError('instruction3 not actual XS producer')
                clone_proofs.append(dict(stage=stage,user=u,slice=sl['slice'],
                    source_instruction=3+128*u,candidate_instruction=24+128*u,
                    candidate_pair_addr=12+64*u,source_word=f'{source_xs:0115x}',
                    clone_low_word=f'{source_xs:0115x}',clone_high_word=0,
                    bit_identical=True,head_model_reserved_local_indices=[12,23],
                    head_actual_payload_bound=False))
                for record in sl['prog_users'][u]:
                    pair=int(record['payload_hex'],16)
                    for part in range(2):
                        word=(pair>>(512*part))&((1<<457)-1)
                        if not word:continue
                        g=lambda k:G.get(word,G.SU_LAYOUT,k)
                        if g('dst')!=1 or g('d')>>22!=1:continue
                        if g('nout')>1 and g('nin')==128 and g('dso')==1536:name='qkv'
                        elif g('nout')==1 and g('nin')==128 and g('sfu')==4:name='down'
                        elif g('nout')==1 and g('nin')==128 and g('sfu')==0:name='o'
                        else:raise ValueError('unrecognized actual X producer')
                        base=g('d')&((1<<22)-1)
                        for o in range(g('nout')):
                            for i in range(g('nin')):
                                address_sets[name].append(base+o*g('dso')+i*g('dsi'))
                        owners[name].append(dict(slice=sl['slice'],instruction=2*record['addr']+part+128*u,
                          instruction_sha256=hashlib.sha256(f'{word:0115x}'.encode()).hexdigest()))
            for name,e in c['epochs'].items():
                family='qkv' if name=='gu' else name
                got=sorted(address_sets[family]);base=e['base']+65536*u
                want=list(range(base,base+e['elements']))
                if got!=want:raise ValueError(f'actual table coverage differs stage{stage} user{u} {name}')
                cases.append(dict(stage=stage,user=u,epoch=name,consumer_pc=e['pc'],
                  first=base,last=base+e['elements']-1,elements=len(got),
                  duplicate_addresses=sum(n-1 for n in Counter(got).values()),producers=owners[family]))
                # Native stream/tap driver derives both endpoints from this certificate.
                f=G.ISA.decode(words[e['pc']])
                native.append(f"{base:x} {got[0]:x} {f['me_k']} {f['me_split']} {e['elements']//64} {(stage-1)*16+u*4+list(c['epochs']).index(name)}\n")
    return dict(schema='opentallas.qwen.me-xpf-su-table-address-join.v1',
      source=dict(programme_sha256=sha(program),table_manifest_sha256=sha(manifest_path),metadata_sha256=sha(metadata_path)),
      templates=templates,cases=cases,case_count=len(cases),
      clone24_model=dict(proofs=clone_proofs,local_index=24,
        actual_decode_indices=[0,11],declared_head_model_indices=[12,23],
        max_relocated_instruction=408,max_relocated_pair_addr=204,
        instruction_store_capacity=512,per_user_instruction_stride=128,
        prog_records_per_user=7,rows_per_stage=110,rows_for36=3960,remaining_rom_rows=136,
        native_table_ROMs=48,read_slots=89,loader_port_reserved_edges=94,
        caller_range_reserved_edges=104,aggregate144_port_edges=13536,
        aggregate144_caller_edges=14976,delta_vs88slot_transport_edges_per_load=1,
        delta_vs88slot_transport_aggregate_edges=144,token_critical_path_delta=None,
        provisional_head_rows=98,provisional_combined_rows=4058,provisional_remaining_rows=38,
        actual_head_payload_bound=False,RTL_implemented=False),
      arithmetic_bits_changed=False,production_bound=False,
      qualification='affine address/payload publication only; timing/store selection/full numerical layer unbound'),native

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--programme',type=Path,required=True)
    ap.add_argument('--table-manifest',type=Path,required=True);ap.add_argument('--metadata',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    receipt,events=build(a.programme,a.table_manifest,a.metadata);a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'certificate.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (a.out/'x_events.txt').write_text(''.join(events))
    print('ACTUAL_TABLE_ME_XPF_ADDRESS_CERT_PASS',receipt['case_count'],flush=True)
if __name__=='__main__':main()
