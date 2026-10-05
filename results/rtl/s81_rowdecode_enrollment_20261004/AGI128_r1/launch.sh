#!/bin/bash
set -eu
root=/home/ubuntu/s81-rowdecode-enrollment-20261004-r1
mkdir "$root"
mkdir "$root/package" "$root/baseline" "$root/toolchain" "$root/compiler-tmp"
tar -xzf /home/ubuntu/s81-rowdecode-source-75f7-20261004.tar.gz -C "$root/package"
tar -xzf /home/ubuntu/s81-rowdecode-oldobjects-57e3-20261004.tar.gz -C "$root/baseline" pq pb
cat > "$root/toolchain/g++-11" <<'CXX'
#!/bin/bash
exec docker run --rm --user "$(id -u):$(id -g)" -v /home:/home -w "$PWD" -e TMPDIR=/home/ubuntu/s81-rowdecode-enrollment-20261004-r1/compiler-tmp --entrypoint /usr/bin/g++-11 ot-host:22.04 "$@"
CXX
chmod +x "$root/toolchain/g++-11"
export PATH="$root/toolchain:$PATH"
export TMPDIR="$root/compiler-tmp"
ulimit -f unlimited
ulimit -t unlimited
ulimit -v unlimited
python3 - <<'PY'
import json,socket,datetime
from pathlib import Path
r=Path('/home/ubuntu/s81-rowdecode-enrollment-20261004-r1')
d={'task':'s81-rowdecode-enrollment','host':socket.gethostname(),'approved':True,'threads':2,'reservation_GiB':8,'minimum_host_reserve_GiB':24,'admitted_by':'Epicurus direct userP0 instruction/Kepler coordination','observed_UTC':'2026-10-04T20:40Z','measured_idle_cores':49.55943945835301,'measured_mem_available_KiB':77386608,'home_free_bytes':571177750528,'compiler':'cached ot-host22.04 GCC11.4.0 exact baseline package','scope':'one sequential q/BF minimum archive closure only; no runtime/pnr/qualification','old_partial_runs_preserved':True}
(r/'admission.json').write_text(json.dumps(d,indent=2)+'\n')
PY
nohup bash -c 'root=/home/ubuntu/s81-rowdecode-enrollment-20261004-r1; export PATH="$root/toolchain:$PATH" TMPDIR="$root/compiler-tmp"; python3 "$root/package/tools/enroll_s81_rowdecode_archives.py" --baseline-root "$root/baseline" --output-root "$root/repaired" --execute --admission "$root/admission.json"; rc=$?; echo "$rc" > "$root/exit_code"; exit "$rc"' > "$root/launcher.log" 2>&1 < /dev/null &
echo "$!" > "$root/launcher.pid"
echo "LAUNCHED $(cat "$root/launcher.pid") $root"
