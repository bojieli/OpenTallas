#!/bin/bash
# lec_async.sh -- pre-route LEC off the placement critical path (COORD 11-01 05:1x, OWNER 12.28b closure first).
# FLOW-21 class fix, default-on in every kit runner (gen_phys type kits, S81/QC/KV/HBM core kits); OT_LEC_ASYNC=0
# restores the inline (blocking) LEC.
#   start  K NAME IMAGE MEM_GB CPUS [DOCKER]  host, before the flow container: arms K/lec_async.on and a watcher.
#          The flow container, at its LEC step, writes K/lec_async.ready (line 1 stop policy "1" = exit 1 stops
#          (lec.py NOT EQUIVALENT), "nz" = any non-zero exit stops (legacy_gate); line 2 = the command) and goes on
#          to floorplan/place/CTS/route at once.  The watcher runs that command in the admitted flow container with docker exec
#          (same /work, combined flow + LEC memory bounded by the existing MEM cap).  A stopping result writes K/lec_async.stop + the FAIL_PREFLOOR
#          "LEC NOT EQUIVALENT" marker and stops the flow container NAME: the route ends there, the kit is FAIL LEC.
#          KW-FIX-24 11-06: a LEC killed by a signal (exit >= 128: docker stop / lane kill / OOM) is no verdict: it
#          writes K/lec_async.aborted ("ABORTED rc=N oom=yes|no ..."), never FAIL_PREFLOOR / lec_async.stop / rc, and
#          drops ready/identity so no later scope reuses it as a proof; the flow goes on and needs a fresh LEC.
#          KW-FIX-24/LECUNIT 11-06 (COORD 19:2x (6), S81 serdes__t4 lost an 8-h LEC on a flow OOM): by default the
#          watcher runs that command as its OWN admitted unit, `ot-heavy --mem OT_LEC_MEM_GB (default MEM) -- docker run
#          --name NAME-lec` with the flow container's image, binds and environment, so the LEC and the flow no longer
#          share one memory cap.  The unit's own exit is read from K/lec_async.unit_rc (written by the LEC shell inside
#          the unit): a unit that never ran the command (not admitted, docker refused) or was killed is ABORTED, never a
#          verdict.  OT_LECUNIT=0 (or no ot-heavy on the host) keeps the old docker exec form; the form is fixed at
#          start in K/lec_async.mode.
#   wait   K                                inside the flow container: exec form, keep it alive until its LEC
#          finishes; unit form, return once the physical result is published (finish on the host waits for the LEC).
#   finish K RC [STOP_RC=5]                    host, after the flow container: waits for the LEC (aborts it if the
#          flow never reached its LEC step), prints the kit rc (STOP_RC = the runner's LEC exit code when the LEC
#          stopped the kit, else RC).
# Sign-off is unchanged: a kit is only countable with a routed LEC EQUIVALENT receipt.
set -u
# Identity covers proof inputs, never physical goal/clock-report state. A later stage
# may reuse this proof only while the exact RTL, proof driver and synth netlist agree.
identity() {
  python3 - "$1" "${2:-all}" "${3:-$1/lec_async.ready}" <<'PYID'
import hashlib,glob,re,shlex,sys,os,json
from pathlib import Path
k=Path(sys.argv[1]);h=hashlib.sha256();cfg=(k/'config.mk').read_text() if (k/'config.mk').exists() else ''
paths=[k/'lec.py']+[k/n for n in ('lec_options.json','lec_hints.json','reset_contract.json') if (k/n).is_file()]
try:
 receipt=json.loads((k/'reset_contract.json').read_text()).get('proof',{}).get('receipt')
 if receipt:paths.append(k/receipt[6:] if receipt.startswith('/work/') else k/receipt)
except (OSError,ValueError,AttributeError):pass
for key in sorted(os.environ):
 if key.startswith('OT_LEC_') and key not in ('OT_LEC_ASYNC','OT_LEC_ASYNC_POLL','OT_LEC_MEM_GB'):
  h.update((key+'='+os.environ[key]).encode())
for line in cfg.splitlines():
 if (re.match(r'^(?:override )?export (?:DESIGN_NAME|VERILOG_FILES|VERILOG_DEFINES|SYNTH_HDL_FRONTEND|ADDITIONAL_LIBS)\s*=',line) or
     re.match(r'^\s*(?:override\s+)?(?:export\s+)?OT_LEC_SLANG_UNROLL_LIMIT\s*[:?+]?=',line)):
  h.update(line.encode())
  if 'VERILOG_FILES' in line or 'ADDITIONAL_LIBS' in line:
   for x in shlex.split(line.split('=',1)[1]):
    if '$' not in x:paths.append(k/x[6:] if x.startswith('/work/') else Path(x))
paths += sorted((k/'rtl').rglob('*')) if (k/'rtl').exists() else []
ready=Path(sys.argv[3]);net=None
if ready.exists() and sys.argv[2]!='source':
 h.update(ready.read_bytes())
 try:
  args=shlex.split('\n'.join(ready.read_text().splitlines()[1:]));i=args.index('--netlist');net=args[i+1]
 except (ValueError,IndexError):pass
if sys.argv[2]=='source':pass
elif net:paths.append(k/net[6:] if net.startswith('/work/') else Path(net))
else:paths += [Path(x) for x in glob.glob(str(k/'run/results/asap7/*/base/1_2_yosys.v'))]
for f in sorted(set(paths),key=str):
 if f.is_file():
  # Mount-relative labels stay identical inside and outside the flow container.
  try:label=str(f.relative_to(k))
  except ValueError:label=str(f)
  h.update(label.encode());h.update(f.read_bytes())
print(h.hexdigest())
PYID
}
bootstrap() {
  python3 - "$1" "$2" "$(identity "$1" source)" <<'PYBOOT'
import datetime,hashlib,json,os,re,shlex,subprocess,sys,time
from pathlib import Path
k=Path(sys.argv[1]).resolve();dk=shlex.split(sys.argv[2]);ready=k/'lec_async.ready'
try:
 pid=int((k/'lec_async.pid').read_text());os.kill(pid,0)
 args=Path(f'/proc/{pid}/cmdline').read_bytes().decode().split('\0');i=args.index('watch')
 if Path(args[i+1]).resolve()!=k:raise ValueError('watcher kit differs')
 owner=args[i+2]
 if not re.fullmatch(r'[A-Za-z0-9_.-]+',owner):raise ValueError('invalid watcher owner')
 def inspect(n):
  p=subprocess.run(dk+['inspect',n],capture_output=True,text=True)
  if p.returncode:return None
  d=json.loads(p.stdout)[0]
  if not d.get('State',{}).get('Running'):return None
  if not any(Path(m.get('Source','/')).resolve()==k for m in d.get('Mounts',[])):raise ValueError('Docker kit mount differs')
  return d
 base=inspect(owner);separate=inspect(owner+'-lec')
 if base and not separate:
  top=subprocess.run(dk+['top',owner,'-eo','pid,args'],capture_output=True,text=True,check=True).stdout
  if not any(re.match(r'^\s*\d+\s+(?:/[^ ]*/)?bash\s+/work/lec_async.sh\s+wait\s+/work(?:\s|$)',x) for x in top.splitlines()):
   raise ValueError('original physical scope has not reached its proof wait')
 if not base and not separate:raise ValueError('no live original proof container')
 if separate:owner += '-lec'
 epoch=ready.stat().st_mtime
 files=[k/'lec.py',k/'config.mk',k/'freeze.json']+list((k/'rtl').rglob('*'))
 files += [k/n for n in ('lec_options.json','lec_hints.json','reset_contract.json') if (k/n).is_file()]
 try:
  receipt=json.loads((k/'reset_contract.json').read_text()).get('proof',{}).get('receipt')
  if receipt:files.append(k/receipt[6:] if receipt.startswith('/work/') else k/receipt)
 except (OSError,ValueError,AttributeError):pass
 cfg=(k/'config.mk').read_text()
 for line in cfg.splitlines():
  if re.match(r'^(?:override )?export (?:VERILOG_FILES|ADDITIONAL_LIBS)\s*=',line):
   for x in shlex.split(line.split('=',1)[1]):
    if '$' not in x:files.append(k/x[6:] if x.startswith('/work/') else Path(x))
 cmd=shlex.split('\n'.join(ready.read_text().splitlines()[1:]));net=None
 if '--netlist' in cmd:net=cmd[cmd.index('--netlist')+1]
 if net:files += [k/net[6:] if net.startswith('/work/') else Path(net)]
 else:files += list(k.glob('run/results/asap7/*/base/1_2_yosys.v'))
 if not any(f.name.endswith('.v') and 'rtl' not in f.parts for f in files):raise ValueError('proof netlist absent')
 for f in files:
  if f.is_file():
   f.resolve().relative_to(k)
   if f.stat().st_mtime>epoch+0.001:raise ValueError('proof input changed after readiness: '+str(f))
 freeze=json.loads((k/'freeze.json').read_text());commit=freeze.get('source_commit') or ''
 if not re.fullmatch(r'[0-9a-f]{7,40}',commit):raise ValueError('kit has no pinned freeze source')
 receipt=k/'PROVENANCE.json'
 if receipt.exists():
  rec=json.loads(receipt.read_text());src=rec.get('provenance') or {}
  if rec.get('schema')!='opentallas.kit_provenance.v1' or src.get('dirty') is not False or src.get('commit')!=commit:raise ValueError('initial source receipt differs')
  required={'config.mk','freeze.json','lec.py'}|{str(f.relative_to(k)) for f in (k/'rtl').rglob('*') if f.is_file()}
  if not required<=set(rec.get('files') or {}):raise ValueError('initial input receipt incomplete')
  for rel,digest in (rec.get('files') or {}).items():
   f=(k/rel).resolve();f.relative_to(k)
   if hashlib.sha256(f.read_bytes()).hexdigest()!=digest:raise ValueError('initial input receipt differs: '+rel)
  if not rec.get('files'):raise ValueError('initial input receipt empty')
  evidence='initial PROVENANCE hashes + unchanged staged netlist'
 else:evidence='pinned freeze + proof inputs unchanged since readiness'
 # Do not expose unrelated process environment. Proof-policy options must match.
 env={}
 for item in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0'):
  if b'=' in item:
   a,b=item.split(b'=',1)
   if a.startswith(b'OT_LEC_'):env[a.decode()]=b.decode()
 skip={'OT_LEC_ASYNC','OT_LEC_ASYNC_POLL','OT_LEC_MEM_GB'}
 for key in (set(env)|{x for x in os.environ if x.startswith('OT_LEC_')})-skip:
  if env.get(key)!=os.environ.get(key):raise ValueError('proof policy environment differs: '+key)
 scope=Path(f'/proc/{pid}/cgroup').read_text().strip()
 (k/'lec_async.owner').write_text(owner+'\n')
 runs=k/'lec_async.runs';runs.mkdir(exist_ok=True)
 (runs/(owner+'.json')).write_text(json.dumps(dict(run_id=owner,goal='proof-owner',source_id=sys.argv[3],started=epoch,scope=scope,host=os.uname().nodename))+'\n')
 (k/'lec_async.migration.json').write_text(json.dumps(dict(owner=owner,pid=pid,source_commit=commit,evidence=evidence,migrated=time.time()))+'\n')
 print('LEC_ASYNC migrated original proof owner '+owner,file=sys.stderr)
except Exception as e:
 print('LEC_ASYNC cannot migrate: '+str(e),file=sys.stderr);sys.exit(11)
PYBOOT
}
run_start() {
  python3 - "$1" "$2" "$3" <<'PYSTART'
import json,sys,time,socket,hashlib,shlex
from pathlib import Path
k,n,g=sys.argv[1:];p=Path(k)/'lec_async.runs';p.mkdir(exist_ok=True)
try:source_id=(Path(k)/'lec_async.source_identity').read_text().strip()
except OSError:source_id=''
h=hashlib.sha256()
for f in ('config.mk','constraint.sdc','pins.json','core.json','budget.json','clock_binding.json'):
 q=Path(k)/f
 if q.is_file():h.update(f.encode());h.update(q.read_bytes())
nets={}
ready=Path(k)/'lec_async.ready'
if ready.exists():
 args=shlex.split('\n'.join(ready.read_text().splitlines()[1:]))
 if '--netlist' in args:
  net=args[args.index('--netlist')+1];f=Path(k)/net[6:] if net.startswith('/work/') else Path(net)
  rel=str(f.relative_to(Path(k)));nets[rel]=hashlib.sha256(f.read_bytes()).hexdigest()
(p/(n+'.json')).write_text(json.dumps(dict(run_id=n,goal=g,source_id=source_id,physical_id=h.hexdigest(),netlists=nets,started=time.time(),host=socket.gethostname(),scope=Path("/proc/self/cgroup").read_text().strip()))+'\n')
PYSTART
}
phase_done() {
  python3 - "$1" "$2" "$3" "$4" <<'PYPHASE'
import json,os,sys,time
from pathlib import Path
k,n,g,rc=sys.argv[1:];k=Path(k)
try:r=json.loads((k/'lec_async.runs'/(n+'.json')).read_text())
except (OSError,ValueError):return_code=0;sys.exit(return_code)
if r.get('goal')!=g:sys.exit(0)
def rd(f):
 try:return (k/f).read_text().strip()
 except OSError:return ''
owner=rd('lec_async.owner')
try:owner_run=json.loads((k/'lec_async.runs'/(owner+'.json')).read_text())
except (OSError,ValueError):owner_run={}
checkpoint = {'place':'3_place.odb','cts':'4_cts.odb','grt':'5_1_grt.odb'}.get(g)
if checkpoint:
 candidates=[f for f in k.glob('run/results/asap7/*/base/'+checkpoint) if f.is_file() and f.stat().st_size>0]
 if candidates:
  f=max(candidates,key=lambda f:f.stat().st_mtime_ns);st=f.stat()
  r['checkpoint']=dict(path=str(f.relative_to(k)),size=st.st_size,mtime_ns=st.st_mtime_ns)
r.update(proof_scope=owner_run.get('scope',''),proof_host=owner_run.get('host',''),schema='opentallas.physical_completion.v1',ended=time.time(),rc=int(rc),
 proof_id=rd('lec_async.identity'),proof_owner=rd('lec_async.owner'),proof_pid=rd('lec_async.pid'),
 proof_pending=not (k/'lec_async.done').exists())
p=k/'physical_completion';p.mkdir(exist_ok=True);dest=p/(n+'.json');tmp=dest.with_suffix('.tmp')
tmp.write_text(json.dumps(r)+'\n');os.replace(tmp,dest)
PYPHASE
}
cmd=$1; shift
case $cmd in
identity) identity "$@"; exit 0 ;;
import-completed)
  ORIGINAL=$1; K=$2
  exec 9> "$K/lec_async.lock"; flock 9
  python3 "$(dirname "$0")/lec_completed_transfer.py" "$ORIGINAL" "$K" || exit $?
  identity "$K" source > "$K/lec_async.source_identity"
  identity "$K" > "$K/lec_async.identity"
  echo completed-transfer > "$K/lec_async.owner"
  touch "$K/lec_async.done"
  exit 0
  ;;
check-synth)
  # Successor synth may refresh a file even after start accepted its old bytes.
  # Refuse physical continuation if those bytes no longer match the reused proof.
  python3 - "$1" "$2" <<'PYCHECK'
import hashlib,json,sys
from pathlib import Path
k=Path(sys.argv[1]);n=sys.argv[2]
try:
 r=json.loads((k/'lec_async.runs'/(n+'.json')).read_text())
 for rel,digest in r.get('netlists',{}).items():
  f=(k/rel).resolve();f.relative_to(k.resolve())
  if hashlib.sha256(f.read_bytes()).hexdigest()!=digest:raise ValueError('synth changed reused proof netlist: '+rel)
except Exception as e:
 print('LEC_ASYNC '+str(e),file=sys.stderr);sys.exit(11)
PYCHECK
  ;;
start)
  K=$1; NAME=$2; IMAGE=$3; MEM=$4; CPUS=$5; DK=${6:-docker}; GOAL=${7:-route}
  exec 9> "$K/lec_async.lock"; flock 9
  if [ -f "$K/lec_async.on" ] && [ ! -f "$K/lec_async.ready" ] && [ ! -f "$K/lec_async.done" ]; then
    P=$(cat "$K/lec_async.pid" 2>/dev/null || true)
    OLD=$(cat "$K/lec_async.source_identity" 2>/dev/null || true)
    if [ -n "$P" ] && kill -0 "$P" 2>/dev/null; then
      [ -n "$OLD" ] && [ "$OLD" = "$(identity "$K" source)" ] || { echo 'LEC_ASYNC pending proof identity differs; retained' >&2; exit 11; }
      run_start "$K" "$NAME" "$GOAL"; exit 0
    fi
  fi
  if [ -f "$K/lec_async.ready" ] && [ ! -s "$K/lec_async.identity" ]; then
    bootstrap "$K" "$DK" || exit $?
    identity "$K" source > "$K/lec_async.source_identity"
    identity "$K" > "$K/lec_async.identity"
  fi
  if [ -f "$K/lec_async.ready" ]; then
    OLD=$(cat "$K/lec_async.identity" 2>/dev/null || true)
    NOW=$(identity "$K")
    if [ -n "$OLD" ] && [ "$OLD" = "$NOW" ]; then
      [ ! -f "$K/lec_async.stop" ] || { echo 'LEC_ASYNC existing proof failed; fresh fixed kit required' >&2; exit 5; }
      touch "$K/lec_async.on"; run_start "$K" "$NAME" "$GOAL"
      echo "LEC_ASYNC reuse proof $OLD owner $(cat "$K/lec_async.owner") for $NAME ($GOAL)" >&2
      exit 0
    fi
    echo 'LEC_ASYNC proof inputs differ or existing proof has no identity; retain its scope and use a fresh kit' >&2
    exit 11
  fi
  rm -f "$K"/lec_async.{on,ready,rc,stop,abort,aborted,done,pid,mode,unit_rc}
  identity "$K" source > "$K/lec_async.source_identity"
  if [ "${OT_LECUNIT:-1}" != 0 ] && command -v ot-heavy > /dev/null 2>&1; then echo unit; else echo exec; fi > "$K/lec_async.mode"
  echo "$NAME" > "$K/lec_async.owner"
  touch "$K/lec_async.on"; run_start "$K" "$NAME" "$GOAL"
  setsid nohup bash "$0" watch "$K" "$NAME" "$IMAGE" "$MEM" "$CPUS" "$DK" >> "$K/lec_async.log" 2>&1 < /dev/null 9>&- &
  echo $! > "$K/lec_async.pid"
  ;;
watch)
  K=$1; NAME=$2; IMAGE=$3; MEM=$4; CPUS=$5; DK=$6
  trap 'touch "$K/lec_async.done"' EXIT
  trap 'exit 143' TERM INT HUP
  MODE=$(cat "$K/lec_async.mode" 2>/dev/null || echo exec)
  echo "LEC_ASYNC watcher $(date '+%F %T') pid $$ waiting for the flow's LEC step"
  t0=$(date +%s)
  until [ -f "$K/lec_async.ready" ] || [ -f "$K/lec_async.abort" ]; do
    sleep "${OT_LEC_ASYNC_POLL:-5}"
    # the flow container must exist while we wait (a killed runner never calls finish)
    if [ $(( $(date +%s) - t0 )) -gt 180 ] && [ "$($DK inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null)" != true ] \
       && [ ! -f "$K/lec_async.ready" ]; then touch "$K/lec_async.abort"; fi
  done
  [ -f "$K/lec_async.ready" ] || { echo "LEC_ASYNC aborted: the flow ended before its LEC step"; exit 0; }
  sleep 1
  POL=$(sed -n 1p "$K/lec_async.ready"); RUN=$(sed -n '2,$p' "$K/lec_async.ready")
  identity "$K" > "$K/lec_async.identity"
  echo "LEC_ASYNC $(date '+%F %T') start ($POL): $RUN"
  LOG0=$(stat -c %s "$K/lec_async.log" 2>/dev/null || echo 0)
  OOMC=$NAME; NOV=
  if [ "$MODE" = unit ]; then
    # Own admitted unit: same image, binds, environment and LEC-option overrides as the exec form, its own memory cap.
    UN=$NAME-lec; OOMC=$UN; LMEM=${OT_LEC_MEM_GB:-$MEM}; LCPUS=${OT_LECUNIT_CPUS:-$CPUS}; VOL=(); ENVS=()
    while IFS= read -r b; do [ -z "$b" ] || VOL+=(-v "$b"); done < <($DK inspect -f '{{range .HostConfig.Binds}}{{println .}}{{end}}' "$NAME" 2>/dev/null)
    [ ${#VOL[@]} -gt 0 ] || VOL=(-v "$K:/work")
    while IFS= read -r e; do case $e in ''|HOSTNAME=*) ;; *) ENVS+=(-e "$e");; esac; done < <($DK inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$NAME" 2>/dev/null)
    for v in OT_LEC_HINTS_PRESEED OT_LEC_EARLY_COMPARE OT_LEC_SUPERSET_VEC OT_LEC_RESET_CYCLES; do [ -z "${!v+x}" ] || ENVS+=(-e "$v=${!v}"); done
    # a stopped leftover of this kit's own earlier unit only (a recycled name of another kit is never removed)
    if $DK inspect -f '{{range .Mounts}}{{println .Source}}{{end}}' "$UN" 2>/dev/null | grep -Fqx -- "$K"; then $DK rm -f "$UN" > /dev/null 2>&1; fi
    rm -f "$K/lec_async.unit_rc"
    echo "LEC_ASYNC $(date '+%F %T') own unit: ot-heavy --mem $LMEM -- $DK run --name $UN (not docker exec in $NAME)"
    ot-heavy --mem "$LMEM" -- $DK run --name "$UN" --cpus="$LCPUS" --memory="${LMEM}g" --memory-swap="${LMEM}g" "${VOL[@]}" "${ENVS[@]}" \
      -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; ( $RUN
); r=\$?; echo \$r > /work/lec_async.unit_rc; chown -R $(id -u):$(id -g) /work/lec /work/lec_run.log /work/lec_async.unit_rc 2>/dev/null; exit \$r" \
      >> "$K/lec_async.log" 2>&1 < /dev/null &
    UP=$!
    trap '$DK stop -t 10 "$UN" > /dev/null 2>&1; kill $UP 2>/dev/null; exit 143' TERM INT HUP
    while kill -0 $UP 2>/dev/null; do
      # the flow stopped before a place checkpoint (wait) or never needs this proof (finish): end the unit
      if [ -f "$K/lec_async.abort" ]; then $DK stop -t 10 "$UN" > /dev/null 2>&1; kill $UP 2>/dev/null; break; fi
      sleep "${OT_LEC_ASYNC_POLL:-5}"
    done
    wait $UP 2>/dev/null; lr=$?
    trap 'exit 143' TERM INT HUP
    if [ -f "$K/lec_async.unit_rc" ]; then lr=$(cat "$K/lec_async.unit_rc"); else NOV=1; fi
    [ ! -f "$K/lec_async.abort" ] || $DK rm -f "$UN" > /dev/null 2>&1
  else
  $DK exec \
    -e OT_LEC_HINTS_PRESEED -e OT_LEC_EARLY_COMPARE -e OT_LEC_SUPERSET_VEC -e OT_LEC_RESET_CYCLES \
    -w /OpenROAD-flow-scripts/flow "$NAME" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; $RUN; r=\$?; chown -R $(id -u):$(id -g) /work/lec /work/lec_run.log 2>/dev/null; exit \$r" \
    >> "$K/lec_async.log" 2>&1
  lr=$?
  fi
  if [ -f "$K/lec_async.abort" ]; then
    # Not a verdict: no rc, no LEC marker, and no ready/identity for a later scope to take as a finished proof.
    rm -f "$K/lec_async.ready" "$K/lec_async.identity"
    echo "LEC_ASYNC $(date '+%F %T') aborted with its flow (exit $lr)"
    exit 0
  fi
  if [ "$lr" -ge 128 ] || [ -n "$NOV" ]; then
    # KW-FIX-24: killed by a signal (docker stop / kill 137, SIGTERM 143, or the memory cap) -- not a LEC verdict, in
    # either stop policy.  OOM evidence (docker OOMKilled, or a memory line in this run's logs) is recorded beside it.
    OOM=no
    [ "$($DK inspect -f '{{.State.OOMKilled}}' "$OOMC" 2>/dev/null)" = true ] && OOM=yes
    { tail -c 20000 "$K/lec_run.log" 2>/dev/null; tail -c +$((LOG0 + 1)) "$K/lec_async.log" 2>/dev/null; } \
      | grep -Eqi 'Killed|out of memory|OOMKilled|Cannot allocate memory|std::bad_alloc|Error 137' && OOM=yes
    rm -f "$K/lec_async.ready" "$K/lec_async.identity"
    [ "$MODE" != unit ] || $DK rm -f "$UN" > /dev/null 2>&1
    echo "ABORTED rc=$lr oom=$OOM $(date '+%F %T')${NOV:+ unit=$UN did not complete its command}" > "$K/lec_async.aborted"
    echo "LEC_ASYNC $(date '+%F %T') aborted by signal (exit $lr, OOM evidence $OOM): no LEC verdict, the kit needs a fresh LEC"
    exit 0
  fi
  [ "$MODE" != unit ] || $DK rm -f "$UN" > /dev/null 2>&1
  echo $lr > "$K/lec_async.rc"
  tail -1 "$K/lec_run.log" 2>/dev/null
  if { [ "$POL" = nz ] && [ $lr != 0 ]; } || { [ "$POL" = 1 ] && [ $lr = 1 ]; }; then
    touch "$K/lec_async.stop"
    echo "FAIL_PREFLOOR LEC NOT EQUIVALENT (lec/lec.json; pre-route LEC ran beside the flow, exit $lr: route stopped)" >> "$K/FAIL_PREFLOOR"
    echo "LEC_ASYNC $(date '+%F %T') FAIL LEC exit $lr: stopping flow container $NAME"
    # Every later scope explicitly registered to share this same proof is a consumer.
    # Stop only those exact names; the proof itself has already returned its NEQ verdict.
    while IFS= read -r consumer; do
      [ -n "$consumer" ] || continue
      # A recycled Docker name must never stop a container from another kit.
      if $DK inspect -f '{{range .Mounts}}{{println .Source}}{{end}}' "$consumer" 2>/dev/null | grep -Fqx -- "$K"; then
        $DK stop -t 10 "$consumer" >/dev/null 2>&1
      fi
    done < <(python3 - "$K" <<'PYCONSUMERS'
import json,re,sys
from pathlib import Path
k=Path(sys.argv[1]);source=(k/'lec_async.source_identity').read_text().strip()
for f in (k/'lec_async.runs').glob('*.json'):
 try:r=json.loads(f.read_text())
 except (OSError,ValueError):continue
 if r.get('source_id')==source and re.fullmatch(r'[A-Za-z0-9_.-]+',r.get('run_id','')):print(r['run_id'])
PYCONSUMERS
)
  elif [ $lr != 0 ]; then
    echo "LEC WARNING (exit $lr): not proved, recorded in lec/lec.json; the flow continues"
  else
    echo "LEC_ASYNC $(date '+%F %T') LEC exit 0"
  fi
  ;;
wait)
  # Publish the physical result before waiting for proof. Only the original
  # owner keeps its admitted container alive; later diagnostic scopes reuse it.
  K=$1; NAME=${2:-}; GOAL=${3:-route}; RC=${4:-0}
  [ -z "$NAME" ] || phase_done "$K" "$NAME" "$GOAL" "$RC"
  OWNER=$(cat "$K/lec_async.owner" 2>/dev/null || true)
  [ -z "$NAME" ] || [ "$NAME" = "$OWNER" ] || exit 0
  # A flow that stopped before it has a place checkpoint (plan stop: cell cap, MPL-0034) has nothing a later scope
  # could resume, so its proof has no reader. Return now: this is the container's last step, so the LEC exec'd in it
  # ends with it and the admitted slot is released. Stops from place on keep the proof for stage resume.
  if [ "$RC" != 0 ] && [ -f "$K/lec_async.ready" ] && [ ! -f "$K/lec_async.rc" ] \
     && ! compgen -G "$K/run/results/asap7/*/base/3_place.odb" > /dev/null; then
    echo "LEC_ASYNC flow stopped rc $RC before a place checkpoint: pre-route LEC aborted"
    touch "$K/lec_async.abort"
    exit 0
  fi
  # Unit form: the LEC has its own admitted unit, so this container need not stay alive for it.
  [ "$(cat "$K/lec_async.mode" 2>/dev/null)" != unit ] || exit 0
  while [ -f "$K/lec_async.on" ] && [ -f "$K/lec_async.ready" ] && [ ! -f "$K/lec_async.rc" ]; do
    sleep "${OT_LEC_ASYNC_POLL:-5}"
  done
  ;;
finish)
  K=$1; RC=$2; SRC=${3:-5}; NAME=${4:-}; GOAL=${5:-route}
  OWNER=$(cat "$K/lec_async.owner" 2>/dev/null || true)
  if [ -n "$NAME" ] && [ "$NAME" != "$OWNER" ] && { [ "$GOAL" = place ] || [ "$GOAL" = cts ] || [ "$GOAL" = grt ]; }; then
    if [ -f "$K/lec_async.stop" ]; then echo "$SRC"; else echo "$RC"; fi
    exit 0
  fi
  [ -f "$K/lec_async.ready" ] || touch "$K/lec_async.abort"
  P=$(cat "$K/lec_async.pid" 2>/dev/null)
  until [ -f "$K/lec_async.done" ] || { [ -n "$P" ] && ! kill -0 "$P" 2>/dev/null; }; do sleep "${OT_LEC_ASYNC_POLL:-5}"; done
  # Keep identity/ready/on for exact proof reuse by later scopes.
  grep -h "^LEC_ASYNC\|^LEC WARNING" "$K/lec_async.log" 2>/dev/null | tail -2 >&2
  if [ -f "$K/lec_async.stop" ]; then echo "$SRC"; else echo "$RC"; fi
  ;;
*) echo "usage: lec_async.sh start|wait|finish ..." >&2; exit 2;;
esac
