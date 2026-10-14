#!/usr/bin/env python3
"""Pinned structural m3 successor with M8 strip and current die IO contract."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import qwen_slab_structural_run as R
ROOT=Path(__file__).resolve().parents[1]
S='physical/qwen_slab_structural'
BENCH_SOURCES=['rtl/test/tb_qwen_slab_port_group.sv','rtl/physical/ot_qwen_slab_port_group.sv',
 'rtl/common/ot_meso_fifo.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv',
 'rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_prefix.sv',
 'rtl/hdc/ot_hdc_fpu.sv','rtl/hdc/ot_hdc_fp32_mul_pipe.sv','rtl/proto/ot_fp32_add_rne_pipe.sv']

# Variants (redesign-qwen 2026-10-08).  m3: the pinned structural m3 successor (MUL_LAT 10, KCP 4, OREG).
# s14o: the s14 die element (MUL_LAT 7, KCP 1, rom_lead 2) plus the m3 pin-anchored OREG stage, so the
#   od2 -> o_data reg->pin wire (TT+LB -281.7, 268 endpoints, 736 ps over 361 um) becomes od2 -> OREG (beside the pin);
#   +1 cycle per ME op on the result path, values unchanged.
# s14ok: s14o plus MUL_KCP 4 (kept C1 operand copies: local partial-product broadcast), 0 cycles.
# s14o_bf / s14ok_bf (qwen-band-integrate 2026-10-08): s14o / s14ok with BANDF 1, the r21m band-lane frame: the
#   element is slot GID = 8b + k of band b's slab and holds group g(split, slot) (per-split constants selected by the
#   registered split, one constant multiplier per split); routed at GID 40 (band 5 slot 0: in range at splits 7..10,
#   four non-zero group constants, the most per-split logic of any slot).  0 cycles; values unchanged for group g.
BF=['BANDF=1','GID=40','TCUT=7','SMIN=7','SMAX=11']
# qwen-tp8 (2026-10-12): --tp 8 benches the element at the TP8 die cut (GT 3072, GID 47 = the last of 48 groups, the
#   largest group constant), with the split random in 5..7 so the range test GID < GT >> split is exercised both ways,
#   and nout drawn near GID*W*IL (partial masks).  Mutants (--mutant, expect FAIL): lead = res_in one cycle early
#   (the --negative of TP4), gt = element built with the TP4 GT 6144, gid = element strapped GID 46.
TP8=['GT=3072','GID=47','SPR=1','NOUT_REL=1']
MUTANTS={'lead':['LEAD=8'],'gt':['DUT_GT=6144','LEAD=9'],'gid':['DUT_GID=46','LEAD=9']}
VARIANTS={
 'm3':dict(mul_lat=10,kcp=4,rom_lead=3),
 's14o':dict(mul_lat=7,kcp=1,rom_lead=2),
 's14ok':dict(mul_lat=7,kcp=4,rom_lead=2),
 's14o_bf':dict(mul_lat=7,kcp=1,rom_lead=2,extra=BF),
 's14ok_bf':dict(mul_lat=7,kcp=4,rom_lead=2,extra=BF),
}

def command(out,name,threads,variant='m3'):
    v=VARIANTS[variant]
    keep='ot_qwen_slab_pg_oreg1'+(' ot_hdc_mul_kcp48' if v['kcp']>1 else '')
    a=SimpleNamespace(height=455.76,mul_lat=v['mul_lat'],bw_m8=True,
      param=['OREG=1',f"MUL_KCP={v['kcp']}",'IN_STAGE=1','AM_SPLIT=1','S5_CTL=1','SCALE_PAIR=1']+v.get('extra',[]),
      hold_margin_ns=.010,cores=threads,sdc='port_group_m3_m8_die_p770.sdc',io_hold_extra=80,
      diamond=True,cts_derate=.75,rom_lead=v['rom_lead'],max_transition_ns=None,slew_margin_percent=30,
      td_only=True,orfs_var=['OT_IO_SKEW=90','OT_IO_HOLD_SKEW=50',
      f'SYNTH_KEEP_MODULES={keep}'],name=name)
    cmd=R.command(a,out)
    cmd[cmd.index('--clock-period-ns')+1]='0.770'
    mapping={'pre_cts.tcl':'pre_cts_skew_m3.tcl','post_plain.tcl':'post_plain_m3.tcl',
             'pre_ref.tcl':'pre_ref_skew_m3.tcl','pre_grt_bwm8.tcl':'pre_grt_m3_bwm8.tcl'}
    for i,v in enumerate(cmd):
        if '=' in v and v.split('=')[0].startswith(('PRE_','POST_')):
            for old,new in mapping.items():
                if v.endswith('/'+old): cmd[i]=v[:-len(old)]+new;break
    cmd+=['--step-tcl',f'PRE_RESIZE={S}/pre_resize_ioanchor.tcl']
    return cmd


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['model','bench','route'])
    p.add_argument('--out',type=Path);p.add_argument('--name');p.add_argument('--threads',type=int,default=16)
    p.add_argument('--negative',action='store_true')
    p.add_argument('--entries',action='store_true',help='use core-leaf/eight-child clock-entry slab parent (same cycles)')
    p.add_argument('--entry-mutant',action='store_true',help='swap two scale-return bits in the entries wrapper')
    p.add_argument('--latency',action='store_true',help='measure staged core versus original slab at the same actual pins')
    p.add_argument('--row-mutant',action='store_true',help='force old16-bit core under18-bit golden row interface')
    p.add_argument('--fullrows',action='store_true',help='18-bit production row boundary checks:65536/131072 and151936 nout')
    p.add_argument('--gid',type=int,help='exact group identity override for a common core view')
    p.add_argument('--gid-mutant',action='store_true',help='flip the core group strap while golden group stays unchanged')
    p.add_argument('--tp',type=int,choices=(4,8),default=4,help='bench: die cut (8: GT 3072, GID 47; see TP8)')
    p.add_argument('--mutant',choices=sorted(MUTANTS),help='bench: a TP8 mutant that must FAIL (implies --negative)')
    p.add_argument('--variant',choices=sorted(VARIANTS),default='m3');a=p.parse_args()
    v=VARIANTS[a.variant]
    if (a.entry_mutant or a.gid_mutant or a.row_mutant) and not a.entries: p.error('--entry-mutant requires --entries')
    if a.mode=='model':
        from uarch_model import qwen_slab_m3_closure_model
        print(json.dumps(qwen_slab_m3_closure_model(),indent=2));return
    a.out.mkdir(parents=True,exist_ok=False)
    if a.mode=='bench':
        cmd=['iverilog','-g2012','-s','tb_qwen_slab_port_group','-o',str(a.out/'bench.vvp')]
        if a.entries: cmd += ['-DOT_SLAB_ENTRIES','rtl/physical/ot_qwen_slab_pg_entries.sv']
        if a.entry_mutant: cmd += ['-DOT_SLAB_ENTRIES_MUT']; a.negative=True
        if a.gid_mutant: cmd += ['-DOT_SLAB_GID_MUT']; a.negative=True
        if a.row_mutant: cmd += ['-DOT_SLAB_ROW_MUT']; a.negative=True
        bf=v.get('extra',[])
        if a.tp==8 and bf: raise SystemExit('--tp 8 is the BANDF 0 frame (the band-lane frame is re-cut separately)')
        if a.mutant: a.negative=True;neg=MUTANTS[a.mutant]
        elif a.entry_mutant or a.gid_mutant or a.row_mutant: neg=['LEAD=9']
        else: neg=(['BMUT=1','LEAD=9'] if bf else ['LEAD=8']) if a.negative else ['LEAD=9']
        for kv in [f"MUL_LAT={v['mul_lat']}",f"MUL_KCP={v['kcp']}",'OREG=1','IN_STAGE=1','AM_SPLIT=1','S5_CTL=1','SCALE_PAIR=1']+bf+(TP8 if a.tp==8 else [])+([f'GID={a.gid}'] if a.gid is not None else [])+(['NW=18','FULLROWS=1'] if a.fullrows else [])+(['COMPARE_LATENCY=1'] if a.latency else [])+neg:
            cmd+=['-P','tb_qwen_slab_port_group.'+kv]
        cmd+=BENCH_SOURCES
        proc=subprocess.run(cmd,capture_output=True,text=True,cwd=ROOT)
        (a.out/'compile.log').write_text(proc.stdout+proc.stderr)
        if proc.returncode: raise SystemExit(proc.returncode)
        proc=subprocess.run(['vvp',str(a.out/'bench.vvp')],capture_output=True,text=True)
        (a.out/'run.log').write_text(proc.stdout+proc.stderr)
        evidence_sources=BENCH_SOURCES+(['rtl/physical/ot_qwen_slab_pg_entries.sv'] if a.entries else [])
        pins={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in evidence_sources}
        (a.out/'result.json').write_text(json.dumps(dict(returncode=proc.returncode,negative=a.negative,variant=a.variant,tp=a.tp,mutant=('narrow_row_width' if a.row_mutant else 'group_strap_bit' if a.gid_mutant else 'scale_return_bits' if a.entry_mutant else a.mutant),entries=a.entries,fullrows=a.fullrows,source_pins=pins),indent=2)+'\n')
        print((proc.stdout+proc.stderr)[-1500:]);raise SystemExit(proc.returncode)
    from uarch_model import qwen_slab_m3_closure_model
    cmd=command(a.out,a.name,a.threads,a.variant)
    (a.out/'recipe.json').write_text(json.dumps(dict(argv=cmd,variant=a.variant,model=qwen_slab_m3_closure_model()),indent=2)+'\n')
    with (a.out/'flow.log').open('w') as log: rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT).returncode
    (a.out/'flow.rc').write_text(str(rc)+'\n')
    if rc: raise SystemExit(rc)
    cmd=[sys.executable,'tools/w18/corner_sta.py','--orfs-dir',str(a.out/'work/orfs'),
         '--macro',R.MACRO,'--post-sdc',f'{S}/signoff833_die.sdc','--output',str(a.out/'corner_sta.json')]
    with (a.out/'corner.log').open('w') as log: rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT).returncode
    (a.out/'corner.rc').write_text(str(rc)+'\n');raise SystemExit(rc)

if __name__=='__main__':main()
