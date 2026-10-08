import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_capture_user32_codec as C

def values(user):
 ctx={n:0 for n,w in C.FIELDS};ctx['user']=user;ctx['expert']=383;ctx['phase']=285;ctx['key_word']=2151149568;ctx['pc']=66;ctx['xversion']=123
 h,c=C.fields();hv={n:0 for n in h};cv={n:0 for n in c}
 for n in ('user','generation','rank'):hv[n]=cv[n]=ctx[n]
 hv['operation_sequence']=cv['operation_sequence']=7
 cv['EID']=ctx['expert'];cv['phase']=ctx['phase'];cv['key']=ctx['key_word']
 return ctx,hv,cv

@pytest.mark.parametrize('user',[0,65535,65536,(1<<32)-1])
def test_widened_roundtrip_and_exact_full_user_association(user):
 ctx,h,c=values(user);hw,cw=C.fields()
 assert C.decode(C.encode(h,hw),hw)==h
 assert C.decode(C.encode(c,cw),cw)==c
 assert C.Association(ctx,7,1).match(h,c,1)

def test_upper_user_bits_cannot_alias_old16():
 ctx,h,c=values(65536);c['user']=0
 with pytest.raises(ValueError):C.Association(ctx,7,1).match(h,c,1)

def test_sparebits_and_wrongshard_rejected():
 ctx,h,c=values(1);hw,cw=C.fields()
 with pytest.raises(ValueError):C.decode(C.encode(h,hw)|(1<<144),hw)
 with pytest.raises(ValueError):C.Association(ctx,7,1).match(h,c,0)

def test_metadata_and_enrollment_not_free_and_not_admitted():
 m=C.build()
 assert m['header']['new144']==144 and m['command']['new237']==237
 assert m['TXplusRX_metadata_gross_FF']==1168
 assert m['reserve50pct_mm2_per_neighbor_endpoint']>0
 assert m['conditional_context_enrollment_next_packet_credit_occupied_edges']==2681
 assert m['context_association']['enrollment_packet_flits']==2
 assert m['additional_codec_validation_capture_edges'] is None
 assert not m['physical_build_admitted']


@pytest.mark.parametrize('changed',['pc','xversion','user','physical_shard','operation_sequence','token_valid'])
def test_explicit_fullcontext_enrollment_rejects_alias(changed):
 ctx,h,c=values(65536);word=C.enrollment_word(ctx,7,1)
 assert C.Association.from_enrollment(word,ctx,7,1).match(h,c,1)
 v=C.decode(word,C.enrollment_fields());v[changed]^=1
 with pytest.raises(ValueError):C.Association.from_enrollment(C.encode(v,C.enrollment_fields()),ctx,7,1)
