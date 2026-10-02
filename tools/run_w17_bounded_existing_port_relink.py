"""Exactly one independently approved aggregate-capped native relink. No runtime."""
import argparse,hashlib,json,os,selectors,shutil,signal,subprocess,time,uuid
from pathlib import Path
import w17_existing_port_relink_plan as plans
ROOT=Path(__file__).resolve().parents[1]

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def validate(plan_path,go_path,bundle):
    p=json.loads(plan_path.read_text());g=json.loads(go_path.read_text())
    if p!=plans.build(ROOT):raise ValueError('exact enrolled relink plan')
    if g.get('schema')!='w17.existing_public_ports.relink_GO.v1' or g.get('scope')!='NATIVE_RELINK_ONLY' or g.get('plan_sha256')!=sha(plan_path) or g.get('source_commit')!=p['source_commit'] or g.get('execution_allowed') is not True or g.get('runtime_allowed') is not False:raise ValueError('fresh independent relink GO')
    for name,h in p['input_sha256'].items():
        path=bundle/name.lstrip('/')
        if path.is_symlink() or not path.is_file() or sha(path)!=h:raise ValueError('relocated input pin '+name)
    return p

def run(plan_path,go_path,bundle,output):
    p=validate(plan_path,go_path,bundle);free=int(Path('/proc/meminfo').read_text().split('MemAvailable:')[1].split()[0])
    if free<28*(1<<20) or shutil.disk_usage(output.parent).free<18*(1<<30):raise ValueError('fresh RAM/disk reserve')
    if os.getloadavg()[0]>len(os.sched_getaffinity(0))-10:raise ValueError('fresh CPU headroom')
    output.mkdir(exist_ok=False)
    image=subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',p['image']],text=True).strip()
    if image!=p['image']:raise ValueError('immutable image identity')
    name='w17-native-relink-'+uuid.uuid4().hex[:12];cpus=','.join(map(str,sorted(os.sched_getaffinity(0))[:2]))
    replacements={'FRESH_OWNED_RELINK_NAME':name,'TWO_ADMITTED_HOST_CPUS':cpus,'HOST_UID:HOST_GID':f'{os.getuid()}:{os.getgid()}','VERIFIED_INPUT_BUNDLE:/inputs:ro':f'{bundle.resolve()}:/inputs:ro','FRESH_OUTPUT:/output:rw':f'{output.resolve()}:/output:rw'}
    argv=[replacements.get(x,x) for x in p['future_container_argv']]
    # Tool identity commands and relink share this same capped container.
    image_index=argv.index(p['image'])
    tool_script='set -eu; g++ --version; sha256sum "$(readlink -f "$(command -v g++)")"; exec "$@"'
    argv=argv[:image_index+1]+['sh','-c',tool_script,'w17-native-relink']+argv[image_index+1:]
    handle=dict(supervisor_PID=os.getpid(),owned_container=name,argv=argv,plan_sha256=sha(plan_path),go_sha256=sha(go_path))
    with (output/'handle.json').open('x') as f:f.write(json.dumps(handle,indent=2)+'\n')
    print(json.dumps(handle),flush=True)
    def stop(signum,frame):raise SystemExit('owned supervisor signal '+str(signum))
    signal.signal(signal.SIGTERM,stop)
    start=time.monotonic();status='RELINK_FAIL';terminal=None;process=None
    try:
        process=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
        sel=selectors.DefaultSelector();sel.register(process.stdout,selectors.EVENT_READ);left=2<<20
        with (output/'relink.log').open('xb') as log:
            while sel.get_map():
                if time.monotonic()-start>60:raise TimeoutError('relink60s cap')
                for key,_ in sel.select(0.25):
                    chunk=os.read(key.fileobj.fileno(),65536)
                    if not chunk:sel.unregister(key.fileobj);continue
                    if len(chunk)>left:raise RuntimeError('relink2MiB log cap')
                    log.write(chunk);log.flush();left-=len(chunk)
        terminal=process.wait(timeout=5)
        if terminal==0:
            validate(plan_path,go_path,bundle)
            if (output/'v41_existing_port_trace').stat().st_size>2<<30:raise ValueError('output2GiB cap')
            status='NATIVE_RELINK_ONLY_PASS'
    except BaseException as error:terminal=str(error)
    finally:
        try:subprocess.run(['docker','kill',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
        except Exception as error:status='RELINK_CLEANUP_FAIL';terminal=str(error)
        if process is not None:
            if process.poll() is None:process.kill()
            process.wait(timeout=5)
    binary=output/'v41_existing_port_trace'
    receipt=dict(status=status,terminal=terminal,handle=handle,seconds=time.monotonic()-start,binary_sha256=sha(binary) if binary.is_file() else None,input_pin_postcheck=status=='NATIVE_RELINK_ONLY_PASS',runtime_invoked=False,no_qualification_transfer=True)
    with (output/'receipt.json').open('x') as f:f.write(json.dumps(receipt,indent=2)+'\n')
    return 0 if status=='NATIVE_RELINK_ONLY_PASS' else 1

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--go',type=Path,required=True);ap.add_argument('--bundle',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    raise SystemExit(run(a.plan,a.go,a.bundle,a.output))
