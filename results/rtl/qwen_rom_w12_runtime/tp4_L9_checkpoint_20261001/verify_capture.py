import base64,datetime,hashlib,json,os,re,socket,sys
from pathlib import Path
def read_process(pid):
    p = Path('/proc') / str(pid)
    try:
        stat = p.joinpath('stat').read_text().rsplit(') ', 1)[1].split()
        argv = [x.decode(errors='replace') for x in p.joinpath('cmdline').read_bytes().split(b'\0') if x]
        try:
            cwd = os.readlink(p / 'cwd')
        except OSError:
            cwd = None
        # Verify PID did not recycle during the multi-file read.
        end = p.joinpath('stat').read_text().rsplit(') ', 1)[1].split()
        if stat[19] != end[19]:
            raise RuntimeError('process changed during identity read')
        return dict(pid=int(pid), start_ticks=int(stat[19]), argv=argv,
                    state=end[0], ppid=int(end[1]), cwd=cwd)
    except FileNotFoundError:
        return None

def capture(job, monitored):
    host = dict(hostname=socket.gethostname(), boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
    processes = {}
    for p in Path('/proc').iterdir():
        if p.name.isdigit() and int(p.name) != os.getpid():
            info = read_process(int(p.name))
            if info is not None:
                processes[p.name] = info
    associated = set(map(int, job['roots'])) | set(map(int, monitored))
    for pid, p in processes.items():
        if any(scope in arg for scope in job['scopes'] for arg in p['argv']) or any(
                p['cwd'] and (p['cwd'] == scope or p['cwd'].startswith(scope + '/')) for scope in job['scopes']):
            associated.add(int(pid))
    # Include descendants and remember them across polls even after reparenting.
    while True:
        added = {int(pid) for pid, p in processes.items() if p['ppid'] in associated}
        if added <= associated:
            break
        associated |= added
    return dict(host=host, processes={pid: p for pid, p in processes.items() if int(pid) in associated})

def evaluate(binding, snapshot):
    """Identity changes are inconclusive; wrapper exit cannot hide live children."""
    if binding['host'] != snapshot['host']:
        return dict(state='identity_changed', qualification='inconclusive', reason='host or boot changed')
    for pid, expected in binding['processes'].items():
        actual = snapshot['processes'].get(pid)
        if actual is None:
            continue
        if actual['start_ticks'] != expected['start_ticks'] or (
                actual['state'] != 'Z' and actual['argv'] != expected['argv']):
            return dict(state='identity_changed', qualification='inconclusive', pid=int(pid))
    live = [int(pid) for pid, p in snapshot['processes'].items() if p['state'] != 'Z']
    if live:
        return dict(state='live' if any(pid in live for pid in binding['roots'][:1]) else 'children_live',
                    live_pids=sorted(live))
    return dict(state='eligible_for_intake')

binding={'endpoint': 'ot-pve1', 'host': {'boot_id': '296c347e-2abf-40a7-8599-3db2b655ab78', 'hostname': 'ot-pve1'}, 'processes': {'1217332': {'argv': ['python3', 'tools/qwen_rom_rt_token.py', '--workdir', '/home/ubuntu/w12/rt_tp4d', '--stages', '/home/ubuntu/w12/st_tp4_sw64/stages.txt', '--token-oracle', '/home/ubuntu/w12/oracle_tp4', '--preload', '/tmp/qwen-vocab-embed-token0/vm_x_fp32.hex', '--tp', '4', '--coll-lat', '339', '--coll-depth', '1024', '--su-width', '64', '--lv', '7', '--smin', '7', '--smax', '11', '--tcut', '7', '--code-banks', '5', '--mem-extra', '1', '--bd', '41', '--xvm', '1', '--nws', '5', '--tws', '38', '--ord', '7', '--threads', '14', '--jobs', '8', '--result', '/home/ubuntu/w12/rt_tp4d_token.json'], 'cwd': '/home/ubuntu/w12/wt4', 'pid': 1217332, 'ppid': 1124167, 'start_ticks': 38691497, 'state': 'S'}, '1220907': {'argv': ['/home/ubuntu/w12/rt_tp4d/qwen_rom_rt', '--stages', '/home/ubuntu/w12/st_tp4_sw64/stages.txt', '/home/ubuntu/w12/rt_tp4d', '/tmp/qwen-vocab-embed-token0/vm_x_fp32.hex'], 'cwd': '/home/ubuntu/w12/rt_tp4d', 'pid': 1220907, 'ppid': 1217332, 'start_ticks': 38723505, 'state': 'R'}}, 'roots': [1217332, 1220907]}
job={'name': 'tp4_su64_token', 'host': 'ot-pve1', 'roots': [1217332, 1220907], 'scopes': ['/home/ubuntu/w12/rt_tp4d'], 'record': '/home/ubuntu/w12/rt_tp4d_token.json', 'extras': ['/home/ubuntu/w12/rt_tp4d/token.log', '/home/ubuntu/w12/rt_tp4d/build_params.json']}

snapshot=capture(job,binding['processes'])
identity=evaluate(binding,snapshot)
assert identity['state']=='live',identity
root=Path('/home/ubuntu/w12')
out=root/'rt_tp4d'
source=Path(snapshot['processes']['1217332']['cwd'])
sys.path.insert(0,str(source/'tools'))
import qwen_rom_rt_token as R
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source_pins={str(p.relative_to(source)):sha(p) for p in R.SOURCES}
log=(out/'token.log').read_bytes()
completed=re.findall(rb'^STAGE (L\d+) done (.*)$',log,re.M)
assert [n.decode() for n,_ in completed]==[f'L{i}' for i in range(10)],completed
checks={}
files={}
for name,_ in completed:
 name=name.decode()
 for d in range(4):
  actual=out/f'{name}_die{d}_x.hex'
  expected=root/'oracle_tp4'/f'L{int(name[1:]):02d}_die{d}_x.hex'
  a=actual.read_bytes(); b=expected.read_bytes()
  av=[int(w,16) for w in a.split()]; bv=[int(w,16) for w in b.split()]
  mismatches=sum(x!=y for x,y in zip(av,bv))+abs(len(av)-len(bv))
  assert len(av)==len(bv)==4096 and mismatches==0,(name,d,mismatches)
  checks[f'{name}_die{d}']=dict(words=len(av),mismatches=mismatches,actual_path=str(actual),expected_path=str(expected),actual_sha256=hashlib.sha256(a).hexdigest(),expected_sha256=hashlib.sha256(b).hexdigest())
  if name=='L9':
   files[actual.name]=base64.b64encode(a).decode()
   assert a==actual.read_bytes()
files['token_log_snapshot.log']=base64.b64encode(log).decode()
files['build_params.json']=base64.b64encode((out/'build_params.json').read_bytes()).decode()
params=json.loads((out/'build_params.json').read_text())
assert '-GG=6144' in params['die'] and '-GD=4' in params['die'] and '-GSW=64' in params['die']
assert '-GTCUT=7' in params['die'] and '-GSMIN=7' in params['die'] and '-GSMAX=11' in params['die']
assert '-GLAT=339' in params['coll'] and '-GDEPTH=1024' in params['coll']
stage_pins={}
line=next(line.split() for line in (root/'st_tp4_sw64/stages.txt').read_text().splitlines() if line.startswith('L9 '))
for d,p in enumerate(line[1:-1]):
 for f in ('matrix_int8.hex','matrix_scale_bf16.hex','crom.hex','program.hex','segments.hex'):
  stage_pins[f'L9/die{d}/{f}']=sha(Path(p)/f)
assert source_pins=={str(p.relative_to(source)):sha(p) for p in R.SOURCES}
second=capture(job,binding['processes'])
assert evaluate(binding,second)['state']=='live'
result=dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='pending',checkpoint_status='bit_exact',completed_layers=[n.decode() for n,_ in completed],checks=checks,stage_done_lines=[(b'STAGE '+n+b' done '+s).decode() for n,s in completed],identity=identity,host=snapshot['host'],driver=snapshot['processes']['1217332'],simulator=snapshot['processes']['1220907'],source_root=str(source),source_sha256_at_capture=source_pins,source_unchanged_during_capture=True,binary_sha256=sha(out/'qwen_rom_rt'),generated_core_sha256=sha(out/'gen/ot_qwen_rom_core.sv'),generated_vstream_sha256=sha(out/'gen/ot_hdc_vstream_rt.sv'),oracle_sha256=sha(root/'oracle_tp4/oracle.json'),stages_sha256=sha(root/'st_tp4_sw64/stages.txt'),preload_sha256=sha('/tmp/qwen-vocab-embed-token0/vm_x_fp32.hex'),new_layer_image_sha256=stage_pins,log_snapshot_sha256=hashlib.sha256(log).hexdigest(),design_point=dict(tp=4,groups_per_die=6144,tiles_per_die=1536,su_width=64,su_reducer_time_levels=7,tree_cut=7,smin=7,smax=11,collective_lat_cycles=339,collective_depth=1024),terminal_record_exists=Path(job['record']).exists(),claim_boundary='Completed L0-L9 checkpoint exactness only. Full token remains live and pending. Source hashes are current capture pins, not recovered launch-time driver pins. Binary/generated source/image hashes bind this observation; await final source_stable record. TP4 SU64 is not SU1024 product. No product-rate ratio, SS/FF closure or adoption.',adoption=False)
assert not result['terminal_record_exists']
print(json.dumps(dict(result=result,files=files),sort_keys=True))
