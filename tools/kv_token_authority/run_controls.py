"""Fleet-side tiny component controls; deliberately failing mutants retained."""
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parent
def run(args):
    p=subprocess.run(args,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print('$ '+' '.join(args),flush=True)
    print(p.stdout,end='',flush=True)
    print('RETURN_CODE',p.returncode,flush=True)
    return p

assert run([sys.executable,'-m','unittest','-v','test_identity_verdict.py']).returncode==0
assert run(['iverilog','-V']).returncode==0
source=(root/'kva_identity_scoreboard.sv').read_text()
assert run(['iverilog','-g2012','-s','tb','-o','base.vvp','kva_identity_scoreboard.sv','tb_identity_scoreboard.sv']).returncode==0
for case in range(13):
    p=run(['vvp','base.vvp',f'+CASE={case}'])
    assert p.returncode==0 and f'IDENTITY_CONTROL_PASS case={case}' in p.stdout
mutants=[
    ('unguarded',source.replace("if(status_authoritative === 1'b1) begin",'if(1) begin'),1,'STARTUP_AUTHORITY_ORACLE'),
    ('trace_mask',source.replace("if(status_authoritative === 1'b1) begin",'if(0) begin'),2,'FIRST_KNOWN_IDLE_ORACLE'),
    ('fallback',source.replace('k=lookup(status_id);','k=lookup(status_id); if(k<0) k=0;'),3,'WRONG_IDENTITY_ORACLE'),
]
for name,mutant,case,witness in mutants:
    assert mutant!=source
    path=root/(name+'.sv');path.write_text(mutant)
    assert run(['iverilog','-g2012','-s','tb','-o',name+'.vvp',str(path),'tb_identity_scoreboard.sv']).returncode==0
    p=run(['vvp',name+'.vvp',f'+CASE={case}'])
    (root/(name+'.fail.log')).write_text(p.stdout+f'RETURN_CODE {p.returncode}\n')
    assert p.returncode!=0 and witness in p.stdout
    print('MUTANT_CAUGHT',name,witness,flush=True)
print('ALL_IDENTITY_CONTROLS_PASS',flush=True)
