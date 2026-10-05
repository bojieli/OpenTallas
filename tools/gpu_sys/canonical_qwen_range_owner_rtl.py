"""Source-controlled generator for the default-off actual seven-row RF owner.

Immutable metadata and ordered consumer PCs come from the canonical recipe.
The hardware retains each full239-bit producer AND consumer identity. Events
are new issuer ABI ports; nothing maps PC40 completion into those ports.
"""
from pathlib import Path
from tools.gpu_sys.canonical_qwen_source_mapping import SourcePlacement
ROW=dict(live=1,published=1,producer_started=1,producer_visible=1,
    producer_frame_retired=1,ACK_delivered=1,consumer_live=1,
    consumer_terminal=1,consumer_reverse=1,ACK_bitmap=32,
    producer_tuple=239,owner55=55,consumer_tuple=239,
    retire_PC=11,consumer_count=9,consumer_ordinal=9,source_version=11)
GLOBAL=dict(session_live=1,session=64,fault=1,quarantine=1)
BIND=dict(live=1,tuple=239,mask=7,go=1,terminal=1,reverse=1)
QUERY=dict(live=1,role=1,tuple=239,row=3,slot=9,phase=3,result=1,owner46=46)
FIELDS={'r':ROW,'g':GLOBAL,'b':BIND,'q':QUERY}
BITS={k:sum(d.values()) for k,d in FIELDS.items()}

def offsets(fields):
    out={};o=0
    for n,w in fields.items():out[n]=(o,w);o+=w
    return out
OFF={k:offsets(d) for k,d in FIELDS.items()}

def sel(group,field,expr):
    o,w=OFF[group][field]
    return f'{expr}[{o} +: {w}]'


def declarations():
    return '\n'.join(f' localparam integer {k.upper()}_{n.upper()}={o};' for k,d in OFF.items() for n,(o,w) in d.items())


def meta_ROM(p):
    bysm={i:[] for i in range(64)}
    for (v,r,sm),h in p.rf.items():bysm[r*32+sm].append((p.version_ids[v],h))
    lines=[' function automatic [48:0] source_meta(input [10:0] version);',' begin source_meta=0;case(SM_INDEX)']
    for sm,homes in bysm.items():
        lines.append(f' {sm}:case(version)')
        for vid,h in sorted(homes):
            # valid,initial,first,length,birth,retire,count; widths1,1,9,7,11,11,9.
            value=(1<<48)|((h.birth<0)<<47)|(h.first<<38)|((h.end-h.first)<<31)|(max(0,h.birth)<<20)|(h.retire<<9)|len(h.consumers)
            lines.append(f" 11'd{vid}:source_meta=49'h{value:013x};")
        lines.extend([' default:source_meta=0;endcase'])
    lines.extend([' default:source_meta=0;endcase end endfunction'])
    consumers={h.version:h.consumers for h in p.rf.values()}
    lines.extend([' function automatic [11:0] expected_consumer(input [10:0] version,input [8:0] ordinal);',' begin expected_consumer=0;case({version,ordinal})'])
    for version,pcs in sorted(consumers.items()):
        for ordinal,pc in enumerate(pcs):lines.append(f" 20'd{p.version_ids[version]*512+ordinal}:expected_consumer=12'd{2048+pc};")
    lines.extend([' default:expected_consumer=0;endcase end endfunction'])
    return '\n'.join(lines)


def generate(root):
    p=SourcePlacement.released()
    template=Path(__file__).with_name('canonical_qwen_range_owner_template.sv').read_text()
    for k,b in BITS.items():template=template.replace('@'+k.upper()+'_BITS@',str(b))
    template=template.replace('@DECLARATIONS@',declarations()).replace('@SOURCE_META@',meta_ROM(p))
    out=Path(root);out.mkdir(parents=True,exist_ok=True)
    target=out/'ot_gpu_qwen_native_range_owner.sv'
    target.write_text(template)
    return target

if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser();a.add_argument('--out',required=True);args=a.parse_args();print(generate(args.out))
