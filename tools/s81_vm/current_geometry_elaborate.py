#!/usr/bin/env python3
"""Replay the small source-pinned Verilator elaboration used by the geometry audit."""
import argparse,hashlib,json,pathlib,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--manifest',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);ap.add_argument('--read-pipe',type=int,choices=[0,4],default=4);ap.add_argument('--cap-pipe',type=int,choices=[0,2],default=2);ap.add_argument('--verilator',default='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator.real');a=ap.parse_args();m=json.loads(a.manifest.read_text());a.out.mkdir(parents=True,exist_ok=True);files=[]
 for q in m['files']:
  data=subprocess.check_output(['git','show',m['commit']+':'+q['path']],cwd=ROOT);assert hashlib.sha256(data).hexdigest()==q['sha256'];p=a.out/pathlib.Path(q['path']).name;p.write_bytes(data);files.append(str(p.resolve()))
 cmd=[a.verilator,'--json-only','-Wno-fatal','--top-module','dsfd_sp_vm',f'-GREAD_PIPE={a.read_pipe}',f'-GCAP_PIPE={a.cap_pipe}','+define+DSFD_SP_VM_MIX4','--Mdir',str((a.out/'obj').resolve()),'--json-only-output',str((a.out/'vm.tree.json').resolve())]+files
 with (a.out/'elaboration.log').open('w')as f:subprocess.run(cmd,stdout=f,stderr=f,timeout=60,check=True)
 (a.out/'command.json').write_text(json.dumps(cmd,indent=1)+'\n');print(a.out/'vm.tree.json')
if __name__=='__main__':main()
