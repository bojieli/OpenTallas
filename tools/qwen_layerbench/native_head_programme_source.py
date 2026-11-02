#!/usr/bin/env python3
"""Build a fresh typed native programme source, not a patch of an old PW image.

Current base instruction generator output is extended by four genuine HEAD
ME chunks+END. Storage is allocated anew with meta_rows30; cycle fields remain
explicit relocations for the global source linker. No old PW-free claim.
"""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hdc_isa as ISA


def build(base_program,gme_object,rank):
    base=[int(x,16)for x in base_program.read_text().split()]
    if len(base)!=25 or ISA.decode(base[-1])['unit']!=0:raise ValueError('actual current25word base generator source required')
    g=json.loads(gme_object.read_text());h=g['ranks'][rank]
    if h['rank']!=rank or len(h['programme_words'])!=5:raise ValueError('native fourchunk GME source object required')
    head=[int(r['word_hex'],16)for r in h['programme_words']]
    if [ISA.decode(w)['unit']for w in head]!=[1,1,1,1,0]:raise ValueError('legacy HEAD SU words must be absent')
    allwords=base+head;meta_rows=len(allwords);first=len(base)
    if meta_rows*16>976 or first+len(head)>4096:raise ValueError('actual dense programme metadata/PC capacity exceeded')
    slots=[]
    for n,r in enumerate(h['programme_words']):
        fixed=((first+n)<<32)|(r['unit']<<44)|(int(n==4)<<46)
        slots.append(dict(PW=984+n,fixed_hex=f'{fixed:016x}',relocations=[dict(symbol=r['issue_symbol'],bit=0,width=32,unit='head_cycle')]))
    # Actual qfd_dv_xpf_seg_loader: three64-bit words per188-bit record, one valid record.
    x=h['xpf'];xval=int(x['fixed_low92_hex'],16)
    xrec=dict(PW=[994,995,996],fixed_low92_hex=x['fixed_low92_hex'],relocations=[
        dict(symbol=x['arm_symbol'],bit=92,width=32,unit='head_cycle'),
        dict(symbol=x['producer_issue_symbol'],bit=124,width=32,unit='head_cycle'),
        dict(symbol=x['first_write_symbol'],bit=156,width=32,unit='head_cycle')])
    return dict(schema='opentallas.qwen.native-head-typed-programme-source.v1',status='UNQUALIFIED_RELOCATABLE_SOURCE',
      rank=rank,base_source=dict(path=str(base_program),sha256=hashlib.sha256(base_program.read_bytes()).hexdigest(),words=25,
        authority='explicit base instruction generator source, not82190 functional qualification or old PW-free capacity'),
      source_gme_sha256=hashlib.sha256(gme_object.read_bytes()).hexdigest(),programme=dict(meta_rows=meta_rows,word_bits=1024,PW_bits=64,PW_per_word=16,
        instructions=[dict(pc=pc,unit=ISA.decode(w)['unit'],word_hex=f'{w:0256x}')for pc,w in enumerate(allwords)],
        PW_instruction_range=[0,meta_rows*16],allocator_rule='fresh base generator recomputes payload allocation after meta_rows30; never overwrite an old PW image'),
      metadata_update=dict(PW=1017,bit=18,width=10,value=meta_rows,tag='CALS',method='fresh base generator preserves its stage/base issue fields and recomputes meta_rows'),
      GME=dict(base=first,rows=slots,zero_padding_PW=[989,990,991],descriptor_PW=993,descriptor_hex=f'{((0x43414c42<<32)|(5<<24)|first):016x}',
        stop_PW=992,stop_fixed_hex=f'{0x43414c47<<32:016x}',stop_relocation=dict(symbol='HEAD_GME_STOP',bit=0,width=32)),
      G_XPF=dict(records=[xrec],zero_padding_PW=list(range(997,1003)),stop_PW=1003,stop_fixed_hex=f'{0x58505447<<32:016x}',stop_relocation=dict(symbol='HEAD_XPF_STOP',bit=0,width=32)),
      base_fixed_issue_XPF_and_DW='recomputed/preserved by current base generator source ABI; actual CALR source event independently links nent1013',
      native_monitor=dict(pidx=17,copy_of=16,programme_pair=8,extra_pairs=0,copy_slice_symbol='EARLIEST_HEAD_PRODUCER_SLICE',primary_observation='actual GI c_su&&c_u0 only'),
      install_context='SEG_CAL1 programme metadata30; stage37 LOCAL_SEG base25 must begin GME/XPF before any native H SU issue; each primitive chunk<=8 rounds',
      executable=False,physical_adoption=False,remaining=['resolve fixedissue/XPF cycles from native commandfront/HR/tap/live-X leases','complete currentbase generator PW/descriptor/native CALR source join','sourcecoherent monitor17 copy/caller','actual native GME/XPF helper decoder/component execution','QC transitive module closure and boundary-source qualification'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-program',type=Path,required=True);p.add_argument('--gme-object',type=Path,required=True);p.add_argument('--rank',type=int,choices=range(8),required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=build(a.base_program,a.gme_object,a.rank);a.out.write_text(json.dumps(r,indent=2)+'\n');print('NATIVE_HEAD_TYPED_SOURCE',r['programme']['meta_rows'],'words',len(r['GME']['rows']),'GME rows')
