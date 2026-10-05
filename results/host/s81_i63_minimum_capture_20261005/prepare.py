import hashlib, json, os, re, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(sys.argv[1]) / 'tools'))
import hdc_isa_v41 as I
import rtl_hdc_v41x_attn_campaign as A

repo, base = map(Path, sys.argv[1:3])
inp = base / 'inputs'
src = base / 'source'
files = {}
def tracked(p):
    files[str(p.relative_to(inp))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return p
ids = np.fromfile(tracked(inp/'I47.SELG_rank0.u32'), dtype='<u4')
assert len(ids)==512 and len(set(map(int,ids)))==512
kvn = np.fromfile(tracked(inp/'I20.KVN_rank0.u32'),dtype='<u4').view('<f4')
lat = np.fromfile(tracked(inp/'I38.LAT_rank0.u32'),dtype='<u4').view('<f4')
assert kvn.size==lat.size==512
assert (np.fromfile(tracked(inp/'I63.S_rank0.u32'),dtype='<u4').size==10240)

# Actual retained sparse stored-history words, never reconstructed golden rows.
window={}; address=0
wp=tracked(inp/'history/r0/hbm_s0.hex')
for t in wp.read_text().split():
    if t.startswith('@'): address=int(t[1:],16)
    else: window[address]=int(t,16);address+=1
rows=[]
for row in range(1048448,1048575):
    start=0x40000+(row%128)*17;sc=window[start+16]
    rows.append(sum((window[start+g]|(((sc>>(8*g))&255)<<256))<<(265*g) for g in range(16)))
rows.append(A.row_word(0,*A.fp8_row_codes(kvn)))

wanted={}
for gid in map(int,ids):
    if gid==1048575:continue
    die=(gid>>4)&3;stack=(gid>>6)&3;local=((gid>>8)<<4)|(gid&15)
    wanted.setdefault((die,stack),set()).update(range(0x400000+9*local,0x400000+9*local+9))
stored={}
for die,stack in sorted(wanted):
    path=tracked(inp/f'history/r{die}/ckv_s{stack}.hex')
    for line in path.open():
        sa,sw=line.split();a=int(sa,16)
        if a in wanted[die,stack]: stored[die,stack,a]=int(sw,16)
for gid in map(int,ids):
    if gid==1048575:
        # Explicit SIM_ONLY source quantization of produced LAT, not an oracle row.
        rows.append(A.row_word(1,*A.fp4_row_codes(lat)));continue
    die=(gid>>4)&3;stack=(gid>>6)&3;local=((gid>>8)<<4)|(gid&15)
    raw=sum(stored[die,stack,0x400000+9*local+j]<<(256*j) for j in range(9))
    codes=[(raw>>(4*j))&15 for j in range(512)]
    scales=[(raw>>(2048+8*j))&255 for j in range(32)]
    rows.append(A.row_word(1,codes,scales))
assert len(rows)==640
with (inp/'source_kv_beats.u32').open('wb') as f:
    for beat in range(160):
        raw=sum(rows[4*beat+j]<<(4240*j) for j in range(4))
        f.write(raw.to_bytes(2120,'little'))
tracked(inp/'source_kv_beats.u32')

s=(repo/'tools/runtime/dsrom/s81_minimum_l20_kv_factory.cpp').read_text()
m=re.search(r'\{2534,1,"([^"]+)",\{([^}]+)\}',s)
assert m[1]=='6124df21d8de509ccbb8e0f114d2ed9776a4316dd810e92c35c0a07acfb9083a'
words=[int(x.strip().rstrip('u'),0) for x in m[2].split(',')]
f=I.decode(sum(x<<(32*j) for j,x in enumerate(words)),full_shape=True)
names=['nout','tiles','k','wbase','ts','ks','js','xbase','xks','xjs','xcs','hg','ogs','round','obase','ots','ojs','mmode','oen','m']
with (src/'adapter_config.hpp').open('w') as out:
    out.write('inline void configure(VDsromAttention& a) {\n')
    for n in names: out.write(f' a.i_{n}={640 if n=="k" else f["mx_m" if n=="m" else "me_"+n]};\n')
    out.write('}\n')
manifest=dict(scope='ONE controlled-source rank0 I63 PV diagnostic; no original accepted-input reconstruction',
    identity47=2147483648,producer=2534,source_node='L20.I63',stage=37,rank=0,position=1048575,
    source_order='127 retained WINDOW rows, current KVN source quantization,512 retained selected IDs/CKV rows',
    P_source='retained produced I63.S; native adapter BF16 RNE cut',
    current_rows='SIM_ONLY source quantization of produced KVN/LAT; no shard/oracle rows read',
    template_sha256=m[1],input_sha256=files,hardware_timing_credit=False)
(inp/'frozen_inputs.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('FROZEN_I63_INPUTS rows=640 P_words=10240 packed_beats=160',flush=True)
