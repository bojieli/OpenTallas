#!/usr/bin/env python3
"""A2-F (field-major write front) vs A2 (quarter-major) cycle-exact differential gate.

Both fronts (tools/s81_vm/area_a2_controlled.sv = A2, tools/s81_vm/area_a2f.sv = A2-F) are elaborated side by side
from the same source pins and compared on EVERY output bit (4-state !==) on EVERY edge: o_slice_v/row/tag, o_mask,
o_data (16,384 b) and the 16 per-quarter faults.  Stimulus (seeded):
  phase L  legal full-load schedules: every cycle up to 53 sources, <= 3 per bank, random rows/masks/tags/data;
  phase B  bursts with 4+ writers on a bank (lane overflow -> sticky faults) and random valid patterns;
  reset    mid-run reset, held 7 edges, then phase L again (reset release / epoch re-arm on both).
Mutants of A2-F (each must be rejected by a mismatch): quarter select swapped, data taken one stage early, one data
bit flipped, quarter BASE shifted, reset held.  Clock/reset roots are tied per design in the bench (functional
equivalence only; physical delivery is per-root phi - R).
"""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/arch/s81_vm_a2f_split4_2118'
SOURCES = ['tools/s81_vm/area_a2_controlled.sv', 'tools/s81_vm/area_id_native.sv',
           'tools/s81_vm/area_id_native_join.sv', 'tools/s81_vm/area_a2_hardmasters.sv', 'tools/s81_vm/area_a2f.sv', 'tools/s81_vm/area_a2f_field4.sv', 'tools/s81_vm/area_a2f_split4_composed.sv']
MUTANTS = ['S81_A2F_MUT_SEL_SWAP', 'S81_A2F_MUT_STAGE', 'S81_A2F_MUT_DATA', 'S81_A2F_MUT_BASE',
           'S81_A2F_MUT_HELD_RESET']

BENCH = r'''`timescale 1ns/1ps
module tb;
 reg ck=0;always #5 ck=~ck;
 reg rst=0;
 reg [52:0] v=0;reg [741:0] row=0;reg [847:0] mask=0;reg [423:0] tag=0;reg [27135:0] data=0;
 wire [127:0] av,fv;wire [1791:0] ar,fr;wire [1023:0] at,ft;wire [511:0] am,fm;wire [16383:0] ad,fd;
 wire [15:0] af,ff;
 s81_a2_controlled ref_a2(
  .ck_header(ck),.ck_payload({4{ck}}),.ck_control({16{ck}}),.ck_meta({16{ck}}),.ck_fault({16{ck}}),.ck_data({128{ck}}),
  .rst_header_n(rst),.rst_payload_n({4{rst}}),.rst_control_n({16{rst}}),.rst_meta_n({16{rst}}),.rst_fault_n({16{rst}}),
  .rst_data_n({128{rst}}),.i_v(v),.i_row(row),.i_tag(tag),.i_mask(mask),.i_data(data),
  .o_slice_v(av),.o_slice_row(ar),.o_slice_tag(at),.o_mask(am),.o_data(ad),.o_fault(af));
 s81_a2f_controlled_split4 dut(
  .ck_header(ck),.ck_payload({4{ck}}),.ck_control({4{ck}}),.ck_meta({4{ck}}),.ck_fault({4{ck}}),.ck_data({128{ck}}),
  .rst_header_n(rst),.rst_payload_n({4{rst}}),.rst_control_n({4{rst}}),.rst_meta_n({4{rst}}),.rst_fault_n({4{rst}}),
  .rst_data_n({128{rst}}),.i_v(v),.i_row(row),.i_tag(tag),.i_mask(mask),.i_data(data),
  .o_slice_v(fv),.o_slice_row(fr),.o_slice_tag(ft),.o_mask(fm),.o_data(fd),.o_fault(ff));
 integer cycle,s,b,k,seed,seed0,phase,checked=0,writes=0,faulty=0,nv;
 integer cnt[0:31];reg [2:0] occ[0:31];
 reg [13:0] r;reg [4:0] bank;
 task tick;begin @(posedge ck);#1;end endtask
 task compare;begin
  if(fv!==av)$fatal(1,"MISMATCH_V cycle%0d",cycle);
  if(fr!==ar)$fatal(1,"MISMATCH_ROW cycle%0d",cycle);
  if(ft!==at)$fatal(1,"MISMATCH_TAG cycle%0d",cycle);
  if(fm!==am)$fatal(1,"MISMATCH_MASK cycle%0d",cycle);
  if(fd!==ad)$fatal(1,"MISMATCH_DATA cycle%0d",cycle);
  if(ff!==af)$fatal(1,"MISMATCH_FAULT cycle%0d %h %h",cycle,ff,af);
  checked=checked+1;if(av!==0)nv=nv+1;if(af!==0)faulty=faulty+1;
 end endtask
 task stim(input integer legal);begin
  v=0;row=0;mask=0;tag=0;data=0;
  // legal = lane l (ascending-source prefix count) of a bank drains at t+l: <= 3 per bank and drain edges unique
  for(b=0;b<32;b=b+1)begin cnt[b]=0;occ[b]=occ[b]>>1;end
  for(s=0;s<53;s=s+1)if($random(seed)%4!=0)begin
   r=$random(seed);bank=r[4:0]^{r[7:5],2'b00};
   if(legal && (cnt[bank]>=3 || occ[bank][cnt[bank]]))begin end
   else begin
    if(cnt[bank]<3)occ[bank][cnt[bank]]=1'b1;
    cnt[bank]=cnt[bank]+1;v[s]=1;row[14*s+:14]=r;tag[8*s+:8]=$random(seed);mask[16*s+:16]=$random(seed);
    for(k=0;k<16;k=k+1)data[512*s+32*k+:32]=$random(seed);
    writes=writes+1;
   end
  end
 end endtask
 initial begin
  seed=1;if($value$plusargs("seed=%d",seed))begin end seed0=seed;
  nv=0;cycle=0;for(b=0;b<32;b=b+1)occ[b]=0;
  repeat(7)begin tick();compare();end
  @(negedge ck);rst=1;
  for(cycle=0;cycle<120;cycle=cycle+1)begin @(negedge ck);if(cycle<100)stim(1);else begin v=0; end tick();compare();end
  if(af!==0)$fatal(1,"LEGAL_PHASE_FAULTED %h",af);
  for(cycle=120;cycle<150;cycle=cycle+1)begin @(negedge ck);if(cycle<135)stim(0);else v=0;tick();compare();end
  if(af===0)$fatal(1,"BURST_PHASE_NO_FAULT");
  @(negedge ck);rst=0;v=0;
  for(cycle=150;cycle<160;cycle=cycle+1)begin tick();compare();end
  @(negedge ck);rst=1;for(b=0;b<32;b=b+1)occ[b]=0;
  for(cycle=160;cycle<260;cycle=cycle+1)begin @(negedge ck);if(cycle<240)stim(1);else v=0;tick();compare();end
  if(af!==0)$fatal(1,"RESTART_PHASE_FAULTED %h",af);
  $display("PASS a2f==a2 seed%0d edges%0d writes%0d valid_edges%0d fault_edges%0d",seed0,checked,writes,nv,faulty);
  $finish;
 end
endmodule
'''


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def sim(tmp, define, seed, tag):
    exe = str(Path(tmp) / f'{tag}.vvp')
    cmd = ['iverilog', '-g2012', '-s', 'tb', '-o', exe] + (['-D' + define] if define else []) + \
          [str(ROOT / s) for s in SOURCES] + [str(Path(tmp) / 'bench.sv')]
    b = subprocess.run(cmd, capture_output=True, text=True)
    if b.returncode:
        raise RuntimeError(b.stdout + b.stderr)
    r = subprocess.run(['vvp', '-n', exe, f'+seed={seed}'], capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()[-3:]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--seeds', type=int, nargs='+', default=[1, 2])
    ap.add_argument('--out', default=str(OUT / 'equiv_proof.json'))
    ap.add_argument('--bench', default=None, metavar='DEFINE|gold',
                    help='kit bench mode: one simulation (seed = --seeds[0]); prints A2F_EQUIV PASS / FAIL, no proof file')
    a = ap.parse_args()
    if a.bench:
        with tempfile.TemporaryDirectory(prefix='s81-a2f-') as tmp:
            (Path(tmp) / 'bench.sv').write_text(BENCH)
            rc, tail = sim(tmp, None if a.bench == 'gold' else a.bench, a.seeds[0], 'bench')
        ok = rc == 0 and any(t.startswith('PASS a2f==a2') for t in tail)
        print('\n'.join(tail))
        print('A2F_EQUIV %s %s' % ('PASS' if ok else 'FAIL', a.bench))
        sys.exit(0 if ok else 1)
    recs = []
    with tempfile.TemporaryDirectory(prefix='s81-a2f-') as tmp:
        (Path(tmp) / 'bench.sv').write_text(BENCH)
        for seed in a.seeds:
            rc, tail = sim(tmp, None, seed, f'gold{seed}')
            ok = rc == 0 and any(t.startswith('PASS a2f==a2') for t in tail)
            recs.append(dict(variant='gold', seed=seed, rc=rc, tail=tail, pass_=ok))
            print('gold', seed, ok, tail[-1] if tail else '')
            if not ok:
                raise SystemExit('GOLD FAIL')
        for m in MUTANTS:
            rc, tail = sim(tmp, m, a.seeds[0], m)
            rej = rc != 0 and any('MISMATCH' in t or 'FAULT' in t for t in tail)
            recs.append(dict(variant=m, seed=a.seeds[0], rc=rc, tail=tail, rejected=rej))
            print(m, 'rejected' if rej else 'NOT REJECTED', tail[-1] if tail else '')
            if not rej:
                raise SystemExit('MUTANT SURVIVED ' + m)
    out = dict(schema='opentallas.s81.vm-a2f-equiv.v1',
               status='PASS_A2F_CYCLE_EXACT_TO_A2_ALL_OUTPUTS_ALL_EDGES_FUNCTIONAL_ONLY',
               sources={s: sha(s) for s in SOURCES}, gate_sha256=sha('tools/s81_vm/area_a2f_equiv_gate.py'),
               simulator='iverilog -g2012', records=recs,
               not_claimed='no physical view, timing, native clock/reset delivery or production adoption')
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + '\n')


if __name__ == '__main__':
    main()
