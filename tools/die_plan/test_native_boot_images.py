import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('ptf',ROOT/'tools/qwen_static_kv/program_target_frames.py');ptf=importlib.util.module_from_spec(spec);spec.loader.exec_module(ptf)

def test_die_age_mode_is_explicit_and_count_exact():
 old=[0]*77;new=[0]*96
 assert ptf.encode_image(10,0x0b0b,old,[])['program_words']==77
 assert ptf.encode_image(10,0x0b0b,new,[],die_cfg_ages=True)['program_words']==96
 with pytest.raises(ValueError):ptf.encode_image(10,0x0b0b,new,[])
 with pytest.raises(ValueError):ptf.encode_image(10,0x0b0b,old,[],die_cfg_ages=True)

def test_native_bundle_uses_preboot_order_and_preserves_age_payload():
 images=[dict(target=t,program=[0]*(471 if t==1 else n),descriptors=[]) for t,n in ptf.TARGET_WORDS.items() if t!=10]
 images.append(dict(target=0,program=[0],descriptors=[0]));data=[0]*96;data[76]=0x12345678;images.append(dict(target=10,program=data,descriptors=[]))
 a=ptf.encode_boot_bundle(0x0b0b,images,mu=True,die_cfg_ages=True)
 assert a['target_order'][0]==10 and a['target_order'][-1]==0
 assert a['images'][0]['program_words']==96
 encoded=a['images'][0]['frames528'];assert (int(encoded[77],16)>>19)&((1<<64)-1)==0x12345678
 data[76]^=1;b=ptf.encode_boot_bundle(0x0b0b,images,mu=True,die_cfg_ages=True)
 assert a['images'][0]['digest']!=b['images'][0]['digest']
