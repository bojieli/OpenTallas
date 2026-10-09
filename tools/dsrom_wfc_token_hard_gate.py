#!/usr/bin/env python3
"""Remote-only full-shape token minimum gate and epoch negative control."""
import argparse, hashlib, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if __import__('socket').gethostname()=='opentallas-codex':raise RuntimeError('remote only')
    a.out.mkdir(parents=True,exist_ok=True)
    sources=['rtl/dsrom_sys/mtp/ot_dsrom_wfc_tok_r3.sv','rtl/dsrom_sys/mtp/tb/tb_mtp_rom_tok_hard.sv']
    records=[]
    for name,defs,want in [('exact',[],'PASS'),('epoch_mutant',['-DOT_WFCTOK_MUT_NOEPOCH'],'FAIL')]:
        d=a.out/name;d.mkdir(exist_ok=True)
        cmd=['iverilog','-g2012','-s','tb_mtp_rom_tok_hard','-o',str(d/'sim.vvp')]+defs+[str(ROOT/s) for s in sources]
        r=subprocess.run(cmd,capture_output=True,text=True);(d/'build.log').write_text(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr)
        r=subprocess.run(['vvp','-n',str(d/'sim.vvp')],capture_output=True,text=True);(d/'run.log').write_text(r.stdout+r.stderr)
        ok=r.returncode==0 and 'MTP_TOK_HARD '+want in r.stdout
        records.append(dict(case=name,expected=want,ok=ok,returncode=r.returncode,result=r.stdout.strip()))
    rec=dict(all_ok=all(r['ok'] for r in records),cases=records,source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources})
    (a.out/'summary.json').write_text(json.dumps(rec,indent=2)+'\n')
    print('WFC_TOKEN_HARD_GATE '+('PASS' if rec['all_ok'] else 'FAIL'))
    if not rec['all_ok']:raise SystemExit(1)
if __name__=='__main__':main()
