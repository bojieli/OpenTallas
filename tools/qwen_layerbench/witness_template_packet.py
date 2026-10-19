"""Concrete optional MODEL packet in unused canonical PW; no receiver RTL adoption."""
import argparse,hashlib,json
from pathlib import Path

def dense_digest(pw,dw):
    d=0x51484f5354505247
    for desc,words in enumerate((pw,dw)):
        for addr,v in enumerate(words):
            d=((d<<7)|(d>>57))&((1<<64)-1);d^=v;d^=(desc<<10)|addr
    return f'{d:016x}'
def encode(g,family):
    value=g['first_w5']|(g['local_pidx']<<13)|(g['required_mask']<<22)|(family<<130)
    for sl,d in g['delta_by_slice'].items():value|=d<<(34+8*int(sl))
    assert value.bit_length()<=134
    return [value&((1<<64)-1),(value>>64)&((1<<64)-1),value>>128]
def decode(words):
    value=words[0]|(words[1]<<64)|((words[2]&63)<<128)
    return dict(first_w5=value&8191,local_pidx=(value>>13)&511,
      required_mask=(value>>22)&4095,family=(value>>130)&15,
      deltas=[(value>>(34+8*s))&255 for s in range(12)])
def main():
    ap=argparse.ArgumentParser()
    for k in ('model','pw','calendar','out'):ap.add_argument('--'+k,type=Path,required=True)
    a=ap.parse_args();m=json.loads(a.model.read_bytes());gs=m['source_groups'];base=400
    pw=[int(x,16) for x in a.pw.read_text().split()]
    original=pw.copy();cal=json.loads(a.calendar.read_bytes());dw=cal['descriptor']
    if len(pw)!=1024 or len(gs)!=13 or any(pw[base:base+3*len(gs)]):raise ValueError('unused profile PW no longer matches exact source')
    records=[]
    for family,g in enumerate(gs):
        words=encode(g,family)
        if family==0:words[2]|=(0x57544e31<<32)|(1<<24)|(base<<14)|(len(gs)<<6)
        d=decode(words)
        if (d['first_w5'],d['local_pidx'],d['required_mask'],d['family'])!=(g['first_w5'],g['local_pidx'],g['required_mask'],family):raise AssertionError('packed record differs')
        for sl,delta in g['delta_by_slice'].items():assert d['deltas'][int(sl)]==delta
        first=base+3*family;pw[first:first+3]=words
        records.append(dict(family_id=family,family=g['family'],local_pidx=g['local_pidx'],first_PW=first,words=[f'{w:016x}' for w in words]))
    assert pw[:400]==original[:400] and pw[439:]==original[439:]
    text=''.join(f'{v:016x}\n' for v in pw);a.out.mkdir(parents=True,exist_ok=True);(a.out/'model_pw.hex').write_text(text)
    out=dict(schema='opentallas.qwen.witness-template-PW-model-packet.v1',production_bound=False,RTL_loader_implemented=False,
      source={k:dict(path=str(getattr(a,k)),sha256=hashlib.sha256(getattr(a,k).read_bytes()).hexdigest()) for k in ('model','pw','calendar')},
      profile='WTN1 revision1 source406 diagnostic only',programme_PW_unchanged=[0,399],
      witness_PW_first=400,witness_PW_last=438,witness_PW_words=39,metadata_PW_total=439,
      ME_XPF_controls_and_footers_unchanged=[976,1023],records=records,
      model_pw_sha256=hashlib.sha256(text.encode()).hexdigest(),calendar_copy_candidate_digest=dense_digest(pw,dw),
      previous_calendar_copy_digest=dense_digest(original,dw),same_ascending_PW_transfers=1024,same_DW_transfers=8,
      loader_model=dict(atomic_seal_after_PW=438,execution_permitted_only_after='all PW/DW copies committed and compiled profile/digest matches',
        reject_partial_duplicate_outoforder_padding_or_header=True,partial_record_register_bits=128,template_storage_bits=1742,
        candidate_additional_state_cost_unpriced=['128bit partial assembly','13bit loaded mask','sequence/index/seal/fault registers','lookup/capture pipeline'],
        source_native_read_ports_added=0,source_external_bus_bits_added=0),
      exact_bit_layout='first13,pidx9,mask12,delta_by_slice96,family4; record0 thirdPW[63:32]WTN1,[31:24]rev1,[23:14]base400,[13:6]count13,[5:0]recordtail',
      physical_admission=False,execution_and_role_bindings=False)
    (a.out/'manifest.json').write_text(json.dumps(out,indent=2)+'\n')
    print('WITNESS_TEMPLATE_PW_MODEL_PACKET_PASS',len(records),'roundtrips,39PW,439total; new digest',out['calendar_copy_candidate_digest'],'production false')
if __name__=='__main__':main()
