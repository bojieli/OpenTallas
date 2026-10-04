#!/usr/bin/env python3
"""Drive the small native token->ROM->VM path with raw DUT-addressed reads.

No row copy, expected activation, numerical inference, program replay or full
parent build. Missing source, identity, response, or commit is a hard error.
"""
import argparse, ctypes as C, hashlib, json, re, struct, subprocess
from pathlib import Path
from dsrom_checkpoint import Checkpoint, DEFAULT_CHECKPOINT

ROOT=Path(__file__).resolve().parents[1]
CANONICAL=ROOT/'results/uarch/dsrom_s81_released_binding_20261004/canonical'
PROMPT=Path('/home/ubuntu/OpenTallas/build/workloads/deepseek-v4.1-flash-prefix/TA-DS41-CHAT-1-P10.json')

class Input(C.Structure):
    _fields_=[(n,C.c_uint32) for n in ['reset_n','start','token','vm_base','req_ready','rsp_valid','commit_ready']]+[
        ('identity',C.c_uint64),('rsp_identity',C.c_uint64),('rsp_macro',C.c_uint32),
        ('rsp_row',C.c_uint32),('rsp_data',C.c_uint32*8)]
class Output(C.Structure):
    _fields_=[(n,C.c_uint32) for n in ['req_valid','req_macro','req_row','rsp_ready','vm_valid','vm_address']]+[
        ('req_identity',C.c_uint64),('vm_identity',C.c_uint64),('vm_data',C.c_uint32*16)]+[
        (n,C.c_uint32) for n in ['busy','done','fault','committed_words']]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class EmbeddingROM:
    def __init__(self,checkpoint,inventory):
        self.source=checkpoint
        if (inventory['stages'],inventory['pairs_per_rank_die'],inventory['BF_dual_pairs'])!=(81,2417,519):
            raise ValueError('canonical S81 inventory required')
        self.storage=inventory['dedicated_storage']['global_tensors'][0]
        if (self.storage['tensor'],self.storage['shape'],self.storage['pairs'],self.storage['word_data_bits'])!=('embed.weight',[129280,5120],2525,256):
            raise ValueError('dedicated embedding geometry changed')
        _,_,self.descriptor=checkpoint.descriptor('embed.weight')
        if self.descriptor['dtype']!='BF16' or self.descriptor['shape']!=[129280,5120]:
            raise ValueError('released embedding descriptor')
    def read(self,macro,row):
        if type(macro)!=int or type(row)!=int or not 0<=macro<4*self.storage['pairs'] or not 0<=row<4096:
            raise ValueError('DUT embedding macro/row bounds')
        pair,leaf=divmod(macro,4);bank,parity=divmod(leaf,2)
        word=pair*16384+bank*8192+row*2+parity
        if word>=self.storage['words']:raise ValueError('unowned embedding word')
        # Only the DUT request address determines the checkpoint byte range.
        return self.source.raw('embed.weight',word*32,32)

def build(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    subprocess.run(['verilator','--cc','--build','--top-module','embedding_vm',
        '--prefix','Vembedding_vm','--Mdir',str(out),'-CFLAGS','-fPIC','-Wno-fatal',
        str(ROOT/'rtl/dsrom_sys/s81_bootstrap/ot_dsrom_s81_embedding.sv'),
        str(ROOT/'rtl/test/dsrom_s81_bootstrap/embedding_vm.sv')],check=True)
    # Discover the installed include root, not a different Verilator release.
    text=subprocess.check_output(['verilator','-V'],text=True)
    include=re.search(r'VERILATOR_ROOT\s*=\s*(\S+)',text).group(1)
    include=Path(include)/'include'
    lib=out/'libdsrom_s81_embedding.so'
    subprocess.run(['g++','-shared','-fPIC','-pthread','-std=c++17',
        '-I'+str(out),'-I'+str(include),'-I'+str(include/'vltstd'),
        '-I'+str(ROOT/'tools/runtime/dsrom'),
        str(ROOT/'tools/runtime/dsrom/s81_embedding_bridge.cpp'),
        str(out/'Vembedding_vm__ALL.a'),str(include/'verilated.cpp')]+
        ([str(include/'verilated_threads.cpp')] if int(re.search(r'Verilator (\d+)\.',text).group(1))>=5 else [])+
        ['-o',str(lib)],check=True)
    return lib

def run(lib,checkpoint,prompt,position,identity,out):
    p=json.loads(prompt.read_text());ids=p['token_ids']
    if type(position)!=int or not 0<=position<len(ids):raise ValueError('prompt position')
    token=ids[position]
    if type(token)!=int or not 0<=token<129280:raise ValueError('prompt token ID')
    if not 0<=identity<1<<47:raise ValueError('saved context identity')
    inventory=json.loads((CANONICAL/'inventory.json').read_text())
    source=Checkpoint(checkpoint);rom=EmbeddingROM(source,inventory)
    dut=C.CDLL(str(lib.resolve()))
    dut.s81_embedding_create.restype=C.c_void_p
    dut.s81_embedding_destroy.argtypes=[C.c_void_p]
    for name in ['s81_embedding_eval','s81_embedding_edge']:
        getattr(dut,name).argtypes=[C.c_void_p,C.POINTER(Input),C.POINTER(Output)]
    dut.s81_embedding_vm_word.argtypes=[C.c_void_p,C.c_uint32]
    dut.s81_embedding_vm_word.restype=C.c_uint32
    handle=dut.s81_embedding_create();i=Input();o=Output()
    i.token=token;i.identity=identity;i.req_ready=1;i.commit_ready=1
    requests=commits=cycles=0;pending=None;digest=hashlib.sha256()
    out.mkdir(parents=True,exist_ok=False)
    try:
        dut.s81_embedding_edge(handle,C.byref(i),C.byref(o))
        i.reset_n=1;i.start=1
        dut.s81_embedding_edge(handle,C.byref(i),C.byref(o));i.start=0;cycles=1
        with (out/'native_events.jsonl').open('w') as log:
            while not o.done:
                if o.fault:raise RuntimeError('native embedding fault')
                i.rsp_valid=0
                if pending is not None and cycles>=pending[0]:
                    _,macro,row,context,data=pending
                    i.rsp_valid=1;i.rsp_macro=macro;i.rsp_row=row;i.rsp_identity=context
                    for n,v in enumerate(struct.unpack('<8I',data)):i.rsp_data[n]=v
                dut.s81_embedding_eval(handle,C.byref(i),C.byref(o))
                response=i.rsp_valid and o.rsp_ready
                if o.req_valid and i.req_ready:
                    if pending is not None:raise RuntimeError('more than one outstanding DUT request')
                    macro,row,context=int(o.req_macro),int(o.req_row),int(o.req_identity)
                    if context!=identity:raise RuntimeError('foreign request context')
                    data=rom.read(macro,row);requests+=1
                    pending=(cycles+8,macro,row,context,data)
                    log.write(json.dumps(dict(event='ROM_REQUEST',cycle=cycles,macro=macro,row=row,identity=context,source_bytes=32))+'\n')
                if o.vm_valid and i.commit_ready:
                    if o.vm_identity!=identity:raise RuntimeError('foreign VM commit')
                    commits+=1
                    digest.update(struct.pack('<I16I',o.vm_address,*o.vm_data))
                    log.write(json.dumps(dict(event='VM_COMMIT',cycle=cycles,address=int(o.vm_address),identity=identity,words=16))+'\n')
                dut.s81_embedding_edge(handle,C.byref(i),C.byref(o));cycles+=1
                if response:pending=None
        if o.fault or pending is not None or requests!=320 or commits!=1280 or o.committed_words!=20480:
            raise RuntimeError('native request/commit conservation')
        # Export actual VM contents, not expected or host-expanded input bits.
        with (out/'actual_vm_committed.bin').open('wb') as f:
            for a in range(20480):f.write(struct.pack('<I',dut.s81_embedding_vm_word(handle,a)))
        result=dict(schema='opentallas.dsrom.S81.native-cold-embedding.v1',
            first_token_native_path_GO=True,full_parent_bootstrap_GO=False,
            scope='Small connected native ROM requester -> 16-lane VM commit SRAM endpoint; parent ABI hook supplied separately',
            prompt=str(prompt.resolve()),prompt_sha256=sha(prompt),prompt_digest=p['digest'],
            prompt_position=position,token=token,identity=identity,
            checkpoint=str(checkpoint.resolve()),snapshot='dba1be0a40aa45a94ad051997016db3960a90277',
            checkpoint_index_sha256=sha(checkpoint/'model.safetensors.index.json'),
            embedding_descriptor=rom.descriptor,embedding_shard=source.index['embed.weight'],
            source_read_bytes=source.read_bytes,ROM_requests=requests,VM_accepted_beats=commits,
            actual_VM_committed_words=int(o.committed_words),cycles=cycles,
            VM_commit_stream_sha256=digest.hexdigest(),actual_vm_sha256=sha(out/'actual_vm_committed.bin'),
            model= str(ROOT/'results/uarch/dsrom_s81_cold_input_20261004/model.json'),
            source_pin=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            mandatory_parent_files=['prog.hex','crom.hex','hbank.hex','hrom.hex','erom.hex','vm_init.hex','hbm0.hex','hbm1.hex','hbm2.hex','hbm3.hex'],
            parent_blockers=['Cicero native C8 ABI hookup and mandatory +DIR source images',
                'Native SSX producer before L0.I0; no host-computed norm/statistic',
                'Per-head-die storage delivery/TP4 arbitration and exact input lease'],
            macro_capture_and_SS_FF_qualified=False,no_CPU_inference=True,
            no_expected_activations=True,no_VM_preload=True,no_full_build=True)
        (out/'GO.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        print(json.dumps(result,sort_keys=True))
    finally:
        dut.s81_embedding_destroy(handle);source.close()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--build',type=Path)
    ap.add_argument('--library',type=Path)
    ap.add_argument('--checkpoint',type=Path,default=DEFAULT_CHECKPOINT)
    ap.add_argument('--prompt',type=Path,default=PROMPT)
    ap.add_argument('--position',type=int,default=0)
    ap.add_argument('--identity',type=int,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if bool(a.build)==bool(a.library):ap.error('exactly one of --build or --library required')
    lib=build(a.build) if a.build else a.library
    run(lib,a.checkpoint,a.prompt,a.position,a.identity,a.out)
if __name__=='__main__':main()
