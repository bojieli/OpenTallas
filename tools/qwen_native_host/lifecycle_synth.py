#!/usr/bin/env python3
"""Ship exact three-source bundle to fleet; tiny generic synthesis through ot-run."""
import base64,io,pathlib,shlex,subprocess,tarfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
SOURCES=['rtl/qwen_sys/host_lifecycle_20261014/qkd_host_lifecycle.sv','rtl/qwen_sys/redesign_qwen/ot_qwen_tp8_token_epoch_allocator.sv','rtl/qwen_sys/redesign_qwen/ot_qwen_tp8_token_cohort.sv']
buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode='w:gz') as archive:
 for source in SOURCES:archive.add(ROOT/source,arcname=pathlib.Path(source).name)
payload=base64.b64encode(buf.getvalue()).decode()
yosys='read_verilog -sv '+' '.join(pathlib.Path(p).name for p in SOURCES)+'; hierarchy -top qkd_host_lifecycle; synth -top qkd_host_lifecycle; stat'
command='taskdir=$(mktemp -d /tmp/q-host-lifecycle-synth.XXXXXX); trap \'rm -rf "$taskdir"\' EXIT; cd "$taskdir"; echo '+shlex.quote(payload)+' | base64 -d | tar xz; yosys -p '+shlex.quote(yosys)
proc=subprocess.run(['ot-run','--mem','2','--threads','1','--','bash','-lc',command],capture_output=True,text=True)
print(proc.stdout+proc.stderr,end='')
raise SystemExit(proc.returncode)
