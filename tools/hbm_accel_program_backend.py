"""Concrete, opt-in CP20 Verilator process and source-native engine factory.

Simulation instrumentation only: no new ASIC logic and no numerical Python
executor. Original source partitions provide timing/refresh/CDC/credits. This
research cluster is not the canonical production memory qualification.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys

PARENT='5b8fb2a98e745fa7bbb382d68295bc6308d47e3e'
GUARDED_PARENT='0cde0cae02f38070f0b701c23dd973816609700a'
CALLBACK_SHA='0f758ce56d752a02b721dfc054047e3dd92ef4e50f4acb4a2cef9d066d7234a7'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec)
    sys.modules[name]=value
    spec.loader.exec_module(value)
    return value

def capture_sources(repo,out,*,parent=PARENT):
    """Read committed objects, never a peer's dirty source files."""
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    def capture(relative):
        data=subprocess.check_output(['git','show',f'{parent}:{relative}'],cwd=repo)
        path=out/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        return path
    source_list=capture('tools/gpu_sys/ds_hbm_cluster_sources.py')
    inventory=module(source_list,'ha5_source_inventory').sources20()[:-1]
    inventory+=['tools/gpu_sys/ds_hbm_sm_engine20.py','tools/gpu_sys/mem_image.py']
    for relative in inventory:capture(relative)
    record=dict(schema='opentallas.ha5-cp20-source.v1',parent=parent,
                files={p:digest(out/p) for p in inventory})
    if record['files']['tools/gpu_sys/ds_hbm_sm_engine20.py']!=CALLBACK_SHA:
        raise ValueError('SMEngine20 source changed; review the actual callback first')
    (out/'source_manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    return out

def capture_guarded(repo,source,*,parent=GUARDED_PARENT):
    """Attach parent-qualified Python successor without another HDL build."""
    source=Path(source)
    relative='tools/gpu_sys/ds_hbm_sm_engine20_guarded.py'
    data=subprocess.check_output(['git','show',f'{parent}:{relative}'],cwd=repo)
    path=source/relative
    if path.exists():raise ValueError('guarded callback capture already exists')
    path.write_bytes(data)
    record=dict(parent=parent,path=relative,sha256=digest(path),
                original_sha256=CALLBACK_SHA,class_name='SMEngine20Guarded')
    (source/'guarded_manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def guarded_factory(source):
    source=Path(source);record=json.loads((source/'guarded_manifest.json').read_text())
    base=source/'tools/gpu_sys/ds_hbm_sm_engine20.py';guard=source/record['path']
    if digest(base)!=CALLBACK_SHA or digest(guard)!=record['sha256']:
        raise ValueError('guarded callback/original source pin mismatch')
    name='tools.gpu_sys.ds_hbm_sm_engine20'
    existing=sys.modules.get(name)
    if existing is not None and digest(existing.__file__)!=CALLBACK_SHA:
        raise ValueError('another original SMEngine20 is already installed')
    if existing is None:module(base,name)
    return module(guard,'ha5_actual_sm_engine20_guarded').SMEngine20Guarded


def emit_top(path,mem_words):
    if type(mem_words) is not int or mem_words<=0:raise ValueError('source memory sizing required')
    # Fixed actual reduced cluster geometry; never pass this off as TP96/1M.
    ports='''input wire por_n,clk_host,clk_sm,clk_mem,clk_link,
 input wire [1:0] cmd_we, input wire [15:0] cmd_addr,
 input wire [127:0] cmd_wdata, input wire [1:0] db_v,
 output wire [1:0] db_rdy, input wire [63:0] db_token,db_pos,db_job,
 input wire [7:0] db_generation, output wire [1:0] cpl_v,
 input wire [1:0] cpl_rdy, output wire [217:0] cpl_data,
 input wire [3:0] im_we,input wire [13:0] im_addr,input wire [63:0] im_data,
 output wire rst_sm_n,sys_fault,
 input wire [1:0] probe_sel,input wire [31:0] probe_sector,
 output reg [255:0] probe_data,
 output wire [55:0] probe_pc,output wire [3:0] probe_issue,
 output wire [3:0] probe_fetch_request,probe_fetch_line'''
    connections=['por_n','clk_host','clk_sm','clk_mem','clk_link','cmd_we','cmd_addr','cmd_wdata',
                 'db_v','db_rdy','db_token','db_pos','db_job','db_generation','cpl_v','cpl_rdy',
                 'cpl_data','im_we','im_addr','im_data','rst_sm_n']
    text='`timescale 1ps/1ps\nmodule ha5_cp20_runtime('+ports+');\n'
    text+=f'ot_ds_hbm_source_entry20 #(.ENABLE(1),.MEM_WORDS({mem_words})) dut(\n'
    text+=','.join('.'+p+'('+p+')' for p in connections)+',.fault(sys_fault));\n'
    text+='initial begin : source_images\n string pfx; #1;\n'
    text+='if ($value$plusargs("ha5_native_mem_prefix=%s",pfx)) begin\n'
    for die in range(2):
        for part in range(2):
            target=f'dut.u_cluster.g_on.g_die[{die}].u_mem.u_ms.g_on.g_s[{part}].u_part.g_on.u_model.mem'
            text+=f'$readmemh($sformatf("%s_d{die}_p{part}.hex",pfx),{target});\n'
    text+='end else $fatal(1,"source-native images required"); end\n'
    text+='always @* begin probe_data=0; case(probe_sel)\n'
    for die in range(2):
        for part in range(2):
            base=f'dut.u_cluster.g_on.g_die[{die}]'
            text+=f'{die*2+part}: if(probe_sector<{mem_words}) probe_data={base}.u_mem.u_ms.g_on.g_s[{part}].u_part.g_on.u_model.mem[probe_sector];\n'
    text+='endcase end\n'
    for die in range(2):
        for sm in range(2):
            index=die*2+sm;base=f'dut.u_cluster.g_on.g_die[{die}].g_sm[{sm}].u_sm.g_on'
            text+=f'assign probe_pc[{index*14}+:14]={base}.pc;\n'
            text+=f'assign probe_issue[{index}]={base}.can_issue;\n'
            text+=f'assign probe_fetch_request[{index}]={base.removesuffix(".g_on")}.treq_v && {base.removesuffix(".g_on")}.treq_rdy;\n'
            text+=f'assign probe_fetch_line[{index}]={base.removesuffix(".g_on")}.trsp_v && {base.removesuffix(".g_on")}.trsp_rdy;\n'
    text+='endmodule\n';Path(path).write_text(text)


def build_command(source,work,verilator,*,mem_words,jobs):
    """Emit inspectable build plan; caller schedules against measured headroom."""
    source,work=Path(source).resolve(),Path(work).resolve()
    work.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((source/'source_manifest.json').read_text())
    for relative,sha in manifest['files'].items():
        if digest(source/relative)!=sha:raise ValueError('changed captured source: '+relative)
    top=work/'ha5_cp20_runtime.sv';emit_top(top,mem_words)
    driver=Path(__file__).with_name('hbm_accel_program_backend.cpp').resolve()
    rtl=[str(source/p) for p in manifest['files'] if p.endswith('.sv')]
    command=[str(verilator),'--cc','--exe','--build','--timing','-Wno-fatal','-O2',
             '-j',str(jobs),'--top-module','ha5_cp20_runtime','--Mdir',str(work/'obj'),
             str(top),*rtl,str(driver)]
    record=dict(schema='opentallas.ha5-cp20-build.v1',command=command,
                source_manifest=manifest,mem_words=mem_words,ndie=2,nsm=2,imw=14,
                driver_sha256=digest(driver),top_sha256=digest(top),
                new_asic_hardware=False,adopt=False,
                clocks_ps=dict(sm_period=833,host_period=4000,mem_period=1000,link_period=900),
                physical_timing='UNVALIDATED; simulator clocks are not SS/FF closure')
    (work/'build_manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    return command

class VerilatorPins:
    """Blocking pipe to actual evaluated RTL. tick owns one SM rising edge."""
    def __init__(self,binary,*,image_prefix,log,enable=False):
        if not enable:raise ValueError('explicit backend enable required')
        self.log=open(log,'a');self.closed=False
        self.process=subprocess.Popen([str(Path(binary).resolve()),
            '+gpu_sys_mem_prefix=', '+ha5_native_mem_prefix='+str(Path(image_prefix).resolve())],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,bufsize=1)
        self.state=self._receive()
        self.observers=[]
    def _receive(self):
        while True:
            line=self.process.stdout.readline()
            if not line:raise RuntimeError('actual RTL process terminated: '+str(self.process.poll()))
            self.log.write(line);self.log.flush()
            if line.startswith('HA5 '):return line.split()[1:]
    def _rpc(self,line):
        if self.closed:raise RuntimeError('backend closed')
        self.process.stdin.write(line+'\n');self.process.stdin.flush()
        return self._receive()
    def snapshot(self):
        values=self._rpc('S')
        time,cycle,rst,fault,rdy,valid,raw,pcs,issue,req,line=map(lambda v:int(v,16),values)
        return dict(time_ps=time,cycle=cycle,rst_sm_n=rst,sys_fault=fault,
            dies=[dict(db_rdy=(rdy>>d)&1,cpl_v=(valid>>d)&1,
                       cpl_data=(raw>>(109*d))&((1<<109)-1)) for d in range(2)],
            sms=[dict(pc=(pcs>>(14*i))&16383,can_issue=(issue>>i)&1,
                      fetch_request=(req>>i)&1,fetch_line=(line>>i)&1) for i in range(4)])
    def drive_die(self,index,**ports):
        if index not in (0,1):raise ValueError('actual die index')
        fields=('cmd_we','cmd_addr','cmd_wdata','db_v','db_token','db_pos','db_job','db_generation','cpl_rdy')
        widths=(1,8,64,1,32,32,32,4,1)
        for field,width in zip(fields,widths):
            value=ports[field]
            if type(value) is not int or not 0<=value<1<<width:raise ValueError(field+' narrowing')
        self._rpc('D '+str(index)+' '+' '.join(format(ports[f],'x') for f in fields))
    def tick(self):
        before=self.snapshot();self._rpc('T')
        for observer in self.observers:observer(before,self.snapshot())
    def boot(self):
        self._rpc('R 0')
        # Actual power reset sequencing, not a timeout or numerical gate.
        for _ in range(16):self.tick()
        self._rpc('R 1')
        while not self.snapshot()['rst_sm_n']:self.tick()
    def load_native(self,images):
        validate_native(images)
        if any(d['cpl_v'] or not d['db_rdy'] for d in self.snapshot()['dies']):
            raise RuntimeError('IMEM loading requires exclusively idle actual cluster')
        for (die,sm),words in images.items():
            for address,word in enumerate(words):
                self._rpc(f'I {1<<(die*2+sm):x} {address:x} {word:x}');self.tick()
        self._rpc('I 0 0 0')
    def read_bytes(self,die,address,size,*,mem_words):
        if die not in (0,1) or address<0 or size<0 or address+size>mem_words*64:
            raise ValueError('actual partition range; refuse modulo alias')
        result=bytearray()
        for x in range(address,address+size):
            part=(x>>7)&1;local=((x>>8)<<7)|(x&127);sector=local>>5
            word=int(self._rpc(f'M {die*2+part:x} {sector:x}')[0],16)
            result.append((word>>(8*(x&31)))&255)
        return bytes(result)
    def close(self):
        if not self.closed:
            self._rpc('Q');self.closed=True;self.process.wait();self.log.close()


def validate_native(images,entries=None):
    if not isinstance(images,dict) or set(images)!={(d,s) for d in range(2) for s in range(2)}:
        raise ValueError('all actual native SM images required')
    if any(not isinstance(v,(list,tuple)) or not v or len(v)>16384 for v in images.values()):
        raise ValueError('native OTG-1 word lists only; ABI3 program.bin is not IMEM')
    for words in images.values():
        if any(type(w) is not int or not 0<=w<1<<64 for w in words):
            raise ValueError('OTG-1 words required')
    if entries is not None:
        if not entries or any(type(pc) is not int or not 0<=pc<min(map(len,images.values())) for pc in entries.values()):
            raise ValueError('source entries outside actual native images')


def factory(compiled,*,source,build,mem_maps,expand,source_sha256,position_extent,
            swapin_positions=(),enable=False,read_logits_address=None):
    """Install real source-packed native images, then enroll original CP20 driver.

    mem_maps are existing source build_images/finish_images outputs, not golden
    or model construction. Caller retains descriptor/column/source ownership.
    Missing maps/entries cannot be replaced by synthetic engine callbacks.
    """
    if not enable:raise ValueError('explicit actual factory enable required')
    from tools.hbm_accel_program_engine import RTLColumnEngine
    source,build=Path(source),Path(build)
    record=json.loads((build/'build_manifest.json').read_text());mem_words=record['mem_words']
    if not source_sha256 or len(source_sha256)!=64:raise ValueError('prepared source SHA256 required')
    if set(mem_maps)!={0,1}:raise ValueError('both actual source memory maps required')
    validate_native(compiled['images'],compiled['entries'])
    for relative,sha in record['source_manifest']['files'].items():
        if digest(source/relative)!=sha:raise ValueError('changed actual source: '+relative)
    # Source image writer checks aliasing before allocation or simulator launch.
    writer=module(source/'tools/gpu_sys/mem_image.py','ha5_native_memory_images')
    images=build/'native_memory';images.mkdir(exist_ok=False)
    for die in range(2):writer.write_images(mem_maps[die],2,mem_words,images,'mem',die=die)
    callback=source/'tools/gpu_sys/ds_hbm_sm_engine20.py'
    if digest(callback)!=CALLBACK_SHA:raise ValueError('actual callback source pin mismatch')
    sm_engine=guarded_factory(source)
    native_record=dict(source_sha256=source_sha256,position_extent=position_extent,
        entries=compiled['entries'],native_word_sha256={f'{d}:{sm}':hashlib.sha256(
            b''.join(w.to_bytes(8,'little') for w in words)).hexdigest()
            for (d,sm),words in compiled['images'].items()},
        memory_files={p.name:digest(p) for p in images.glob('*.hex')},
        binary_sha256=digest(build/'obj/Vha5_cp20_runtime'),
        callback_sha256=digest(callback),guarded_callback=json.loads(
            (source/'guarded_manifest.json').read_text()),adopt=False,
        qualification='research simulator; released source-bound layer gate pending')
    (build/'runtime_manifest.json').write_text(json.dumps(native_record,indent=2)+'\n')
    pins=VerilatorPins(build/'obj/Vha5_cp20_runtime',image_prefix=images/'mem',
                       log=build/'runtime.log',enable=True)
    try:
        pins.boot();pins.load_native(compiled['images'])
        def logits(receipt):
            die,address,size=read_logits_address(receipt)
            return pins.read_bytes(die,address,size,mem_words=mem_words)
        engine=RTLColumnEngine(pins,compiled['entries'],expand,ndie=2,nsm=2,
            position_extent=position_extent,source_sha256=source_sha256,enable=True,
            sm_engine_factory=sm_engine,swapin_positions=swapin_positions,
            read_logits=logits if callable(read_logits_address) else None)
        return engine,pins
    except Exception:
        pins.close();raise


def compile_and_enroll(program,native_class,kinds,link,*,shared_first=False,
                       moe_sha256=None,**bindings):
    """Concrete join from an existing prepared DProgram to its real CP20 process.

    No constructor/build_images/inference call. Compilation may add source
    constant vectors; the original finish_images then packs those exact bytes.
    Adapter enable is explicit and separate from shared-first schedule opt-in.
    """
    from tools.hbm_accel_program_engine import compile_native
    if not bindings.get('enable',False):raise ValueError('explicit actual factory enable required')
    if not hasattr(program,'mem') or len(program.mem)!=2 or not hasattr(program,'CONST'):
        raise ValueError('existing prepared native two-die source program required')
    compiled=compile_native(program,native_class,kinds,link,enable=shared_first,
                            moe_sha256=moe_sha256,ndie=2,nsm=2)
    program.finish_images()  # source packing, never numerical model execution
    engine,pins=factory(compiled,mem_maps={d:program.mem[d] for d in range(2)},**bindings)
    return compiled,engine,pins


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    capture=sub.add_parser('capture')
    capture.add_argument('--repo',required=True);capture.add_argument('--out',required=True)
    capture.add_argument('--parent',default=PARENT);capture.add_argument('--guarded-parent',default=GUARDED_PARENT)
    build=sub.add_parser('plan')
    build.add_argument('--source',required=True);build.add_argument('--work',required=True)
    build.add_argument('--verilator',required=True);build.add_argument('--mem-words',type=int,required=True)
    build.add_argument('--jobs',type=int,required=True)
    args=parser.parse_args()
    if args.action=='capture':
        root=capture_sources(args.repo,args.out,parent=args.parent)
        print(json.dumps(capture_guarded(args.repo,root,parent=args.guarded_parent),indent=2))
    else:
        print(json.dumps(build_command(args.source,args.work,args.verilator,
                         mem_words=args.mem_words,jobs=args.jobs),indent=2))
