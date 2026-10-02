from pathlib import Path
import sys,struct
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w17_D1_dispatch_drain as m

@pytest.mark.parametrize('key',['pid','start_ticks','cmdline','cwd','cgroup'])
def test_owner_identity_mutation_rejected(key):
 p=dict(pid=1,start_ticks=10,cmdline='make explicit',cwd='/owned',cgroup='owned');q=dict(p);q[key]='wrong'
 with pytest.raises(ValueError,match='identity'):m.check_identity(p,q)

def test_zombie_recipe_not_live_but_any_unknown_live_child_blocks():
 rows=[{'pid':1,'state':'T'},{'pid':2,'state':'S'},{'pid':3,'state':'Z'},{'pid':4,'state':'S'}]
 assert m.live_workers(rows,1,2)==[{'pid':4,'state':'S'}]

@pytest.mark.parametrize('field,value',[('authorized',False),('phase','other'),('source_head','wrong'),('packet_SHA256','wrong'),('remote_ready',False),('fleet_lease_verified',False),('runtime_authorized',True),('wall_limit',900),('per_process_AS',3),('per_file_limit',512)])
def test_no_go_no_signal(field,value):
 go=dict(authorized=True,phase='FREEZE_DRAIN_NATIVE_DISPATCH',source_head='head',packet_SHA256='packet',remote_ready=True,fleet_lease_verified=True,runtime_authorized=False);go[field]=value
 with pytest.raises(ValueError):m.check_GO(go,'packet','head')

def test_truncated_or_wrong_ELF_not_retained(tmp_path):
 p=tmp_path/'a.o';p.write_bytes(b'\x7fELF');assert not m.valid_object(p)
 b=bytearray(64);b[:6]=b'\x7fELF\x02\x01';struct.pack_into('<HH',b,16,1,62);struct.pack_into('<Q',b,40,64);struct.pack_into('<HH',b,58,64,1)
 p.write_bytes(b);assert not m.valid_object(p)  # truncated section table
 b+=bytes(64);p.write_bytes(b);assert m.valid_object(p)
 struct.pack_into('<H',b,16,2);p.write_bytes(b);assert not m.valid_object(p)
