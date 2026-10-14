#!/usr/bin/env python3
"""Actual local conditioner/relay reset epoch proof, scheduled with ot-run."""
from pathlib import Path
import subprocess,json,hashlib,sys,argparse
ROOT=Path(__file__).resolve().parents[2]
SRC=['rtl/dsrom_sys/mtp/ot_dsrom_mtp_hrow_tiles.sv','rtl/dsrom_sys/s81_ph/relays/dsfd_die_relays.sv','rtl/dsrom_sys/mtp/tb_mtp_hrow_reset_ack.sv']
FULL=SRC+['rtl/dsrom_sys/mtp/ot_dsrom_mtp_hrow_die.sv','rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_rtt.sv','rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv','rtl/dsrom_sys/mtp/rtt/ot_dsrom_mtp_rstsync.sv','physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v']
a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);args=a.parse_args();args.out.mkdir(parents=True,exist_ok=True)
rec={}
for name,mut in [('positive',None),('mirror','OT_HROW_MUT_ACK_MIRROR'),('no_epoch','OT_HROW_MUT_ACK_NO_EPOCH'),('wrong_witness','OT_HROW_MUT_ACK_WRONG_WITNESS')]:
 exe=args.out/name;cmd=['iverilog','-g2012','-DOT_HROW_RESET_ACK','-s','tb_mtp_hrow_reset_ack','-o',str(exe)]+(['-D'+mut] if mut else [])+[str(ROOT/p) for p in SRC]
 b=subprocess.run(cmd,capture_output=True,text=True);(args.out/(name+'.build.log')).write_text(b.stdout+b.stderr)
 if b.returncode:rec[name]={'ok':False,'build_exit':b.returncode};continue
 r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);log=r.stdout+r.stderr;(args.out/(name+'.log')).write_text(log)
 rec[name]={'exit':r.returncode,'ok':r.returncode==0 and 'PASS' in log if mut is None else r.returncode!=0 and 'ACK_BAD' in log,'observed':log.strip()}
exe=args.out/'full94';cmd=['iverilog','-g2012','-DOT_HROW_RESET_ACK','-s','tb_mtp_hrow_reset_ack_full','-o',str(exe)]+[str(ROOT/p) for p in FULL]
b=subprocess.run(cmd,capture_output=True,text=True);(args.out/'full94.build.log').write_text(b.stdout+b.stderr)
if b.returncode:rec['full94']={'ok':False,'build_exit':b.returncode}
else:
 r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);log=r.stdout+r.stderr;(args.out/'full94.log').write_text(log);rec['full94']={'ok':r.returncode==0 and 'PASS' in log,'exit':r.returncode,'observed':log.strip()}
proof={'source_commit':(ROOT/'SOURCE_COMMIT').read_text().strip() if (ROOT/'SOURCE_COMMIT').exists() else subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FULL},'cases':rec,'ok':all(v['ok'] for v in rec.values()),'scope':'Actual two-FF conditioner and fixed r2079 reset consumers; full parent ACK graph elaboration separately; arithmetic production proof pending parent owner.'}
(args.out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2));sys.exit(0 if proof['ok'] else 1)
