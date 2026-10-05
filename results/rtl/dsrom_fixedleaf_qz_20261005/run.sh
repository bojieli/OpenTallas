#!/bin/bash
set -uo pipefail
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
export NUM_CORES=16
qz_out=/srv/opentallas-scratch/codex/rawls-fixedleaf-qz-7957cd35b-r1
date -u +%FT%TZ > "$qz_out/started.txt"
/usr/bin/time -v -o "$qz_out/resources.txt" /srv/opentallas-scratch/admit.sh 16 -- env NUM_CORES=16 python3 /srv/opentallas/repos/rawls-fixedleaf-qz-7957cd35b/tools/dsrom_qz_exact.py --work "$qz_out/build" --output "$qz_out/exact.json" --build-workers 2 --build-jobs 8 --jobs 16 --seeds 4
qz_rc=$?
printf '%s\n' "$qz_rc" > "$qz_out/tool.exit"
python3 - "$qz_out" "$qz_rc" <<'PY'
import pathlib,sys,json,datetime,hashlib
out=pathlib.Path(sys.argv[1]);rc=int(sys.argv[2]);p=out/'exact.json';r=json.loads(p.read_text()) if p.exists() else {};passed=rc==0 and r.get('verdict')=='PASS'
t=dict(tool_returncode=rc,verdict=r.get('verdict','NO_RECORD'),gate_pass=passed,process_exit=0 if passed else 1,completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),record_sha256=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None,source_revision=r.get('git_commit'),raw_output_root=str(out),error=r.get('error'))
(out/'terminal.json').write_text(json.dumps(t,indent=2)+'\n');(out/'supervisor.exit').write_text(str(t['process_exit'])+'\n');print(json.dumps(t));sys.exit(t['process_exit'])
PY
