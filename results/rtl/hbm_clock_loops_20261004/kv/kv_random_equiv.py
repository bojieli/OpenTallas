#!/usr/bin/env python3
"""Seeded random transaction-level equivalence of KV lifecycle implementations.

Each seed is a scripted, reactive bench (the pinned HA4 fixture's port harness and test SRAM,
plus random lifecycles over random rows: hydrate, BEGIN, 16 STAGE beats in random order, COMMIT
with 528 sector transactions under random backpressure and receipt order, PUBLISH, ACQUIRE,
CONSUMER events/commands in random order, RELEASE with drain) and, for some seeds, one injected
protocol violation. Every external transaction is logged without cycle numbers (commands,
responses with all fields, shared-memory ops, commit, sector requests with address/data, drains,
final state); the logs of every implementation must be identical to the original's.
Usage: kv_random_equiv.py --out DIR --seeds N [--impl name=path ...]
"""
import argparse
import random
import re
import subprocess
import sys
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
BASE = '8564e79eaf906c820aec5eb92bfda1cca80ee43d'
FIXTURE = 'tests/test_canonical_qwen_kv_controller.py'
ORIGINAL = ('original', 'rtl/model/qwen_kv_lifecycle_20261003/ot_gpu_qwen_kv_lifecycle_controller.sv',
            'ot_gpu_qwen_kv_lifecycle_controller')

TASKS = r'''
integer seed, fcnt, i_, b_;
function [31:0] fold(input [511:0] v); integer q; begin fold=0; for(q=0;q<16;q=q+1) fold=fold^v[q*32+:32]; end endfunction
function integer rnd(input integer n); begin rnd=($random(seed) & 32'h7fffffff) % n; end endfunction
always @(posedge clk) begin
 if(cmd_valid && cmd_ready) $display("CMD %0d %0d %0d %0d", cmd_op, cmd_identity, cmd_key, cmd_sequence);
 if(rsp_valid && rsp_ready) $display("RSP f%0d op%0d id%0d k%0d s%0d pc%0d pr%0d c%0d b%0d cap%h", rsp_fault, rsp_op, rsp_identity, rsp_key, rsp_sequence, rsp_PC, rsp_producer, rsp_consumer, rsp_stage_beat, fold(rsp_capture));
 if(shared_valid && shared_ready) $display("SH w%0d a%0d sm%0d r%0d d%h", shared_write, shared_addr, shared_SM, shared_rank, fold(shared_wdata));
 if(commit_valid && commit_ready) $display("COMMIT %0d %0d %0d %0d %h %h", writer_identity, writer_key, writer_stage_base, writer_stage_SM, writer_K_base, writer_V_base);
 if(payload_req_valid && payload_req_ready) $display("REQ w%0d s%0d a%h m%0d l%0d d%h", payload_req_write, payload_req_sector, payload_req_source_addr, payload_req_rmw, payload_req_rmw_last, payload_req_data);
 if(drain_valid && drain_ready) $display("DRAIN %0d %0d", drain_identity, drain_key);
 if(fault) begin fcnt=fcnt+1; if(fcnt==40) begin final_state(); $finish; end end
end
task final_state;
 $display("FINAL fault%0d idle%0d wr%0d rv%0d rf%0d op%0d id%0d k%0d s%0d pc%0d", fault, idle, writer_retained, rsp_valid, rsp_fault, rsp_op, rsp_identity, rsp_key, rsp_sequence, rsp_PC);
endtask
task waitc(input integer n); integer q; begin for(q=0;q<n;q=q+1) @(negedge clk); end endtask
task rsp2;
 integer w; begin w=0; while(!rsp_valid) begin @(negedge clk); w=w+1; if(w>4000) begin $display("TIMEOUT rsp"); final_state(); $finish; end end
 waitc(rnd(3)); rsp_ready=1; @(negedge clk); rsp_ready=0; end
endtask
task offer2(input [2:0] kind,input [63:0] identity,input [19:0] k);
 integer w; begin @(negedge clk); cmd_op=kind; cmd_identity=identity; cmd_key=k;
 cmd_sequence=cmd_sequence+1; cmd_PC=rnd(1737); cmd_valid=1; w=0;
 #1; while(!cmd_ready) begin @(negedge clk); #1; w=w+1; if(w>4000) begin $display("TIMEOUT cmd"); final_state(); $finish; end end
 @(negedge clk); cmd_valid=0; cmd_op=rnd(8); cmd_identity={$random(seed),$random(seed)}; cmd_key=$random(seed); end
endtask
task hydrate2(input [19:0] k, input [63:0] prod);
 integer w; begin waitc(rnd(2)); hydrate_key=k; hydrate_producer=prod; hydrate_valid=1; w=0;
 #1; while(!hydrate_ready) begin @(negedge clk); #1; w=w+1; if(w>4000) begin $display("TIMEOUT hyd"); final_state(); $finish; end end
 @(negedge clk); hydrate_valid=0; hydrate_key=$random(seed); end
endtask
task stages2(input [63:0] id, input [19:0] k, input integer skip);
 integer perm[0:15]; integer t, x; reg [511:0] d;
 begin for(t=0;t<16;t=t+1) perm[t]=t;
 for(t=15;t>0;t=t-1) begin x=rnd(t+1); i_=perm[t]; perm[t]=perm[x]; perm[x]=i_; end
 for(t=0;t<16;t=t+1) if(t!=skip) begin
  for(x=0;x<16;x=x+1) d[x*32+:32]=$random(seed);
  cmd_stage_beat=perm[t]; cmd_stage_data=d; offer2(1,id,k); rsp2(); end end
endtask
task payloads2(input [63:0] id, input [19:0] k, input integer bad_at);
 integer tr, sec, w; reg isw; reg [33:0] addr; reg [255:0] d;
 begin for(tr=0;tr<528;tr=tr+1) begin
  w=0; while(!payload_req_valid) begin @(negedge clk); w=w+1; if(w>4000) begin $display("TIMEOUT req"); final_state(); $finish; end end
  sec=payload_req_sector; isw=payload_req_write; addr=payload_req_source_addr;
  waitc(rnd(3)); payload_req_ready=1; @(negedge clk); payload_req_ready=0;
  waitc(rnd(2));
  for(i_=0;i_<8;i_=i_+1) d[i_*32+:32]=$random(seed);
  payload_identity=id; payload_key=k; payload_sector=sec; payload_source_addr=addr; payload_write=isw; payload_rdata=d;
  if(tr==bad_at) case(rnd(4)) 0: payload_identity=id+1; 1: payload_source_addr=addr+32; 2: payload_sector=sec+1; 3: payload_write=!isw; endcase
  if(rnd(3)==0) begin payload_visible=1; payload_reverse=1; payload_valid=1;
   #1; while(!payload_ready) begin @(negedge clk); #1; end @(negedge clk); payload_valid=0; payload_visible=0; payload_reverse=0; end
  else begin payload_visible=1; payload_valid=1;
   #1; while(!payload_ready) begin @(negedge clk); #1; end @(negedge clk); payload_valid=0; payload_visible=0;
   waitc(rnd(3)); payload_reverse=1; payload_valid=1;
   #1; while(!payload_ready) begin @(negedge clk); #1; end @(negedge clk); payload_valid=0; payload_reverse=0; end
 end end
endtask
task commit2(input [63:0] id, input [19:0] k, input integer bad_at);
 integer w; begin offer2(2,id,k); w=0;
 while(!commit_valid) begin @(negedge clk); w=w+1; if(w>4000) begin $display("TIMEOUT commit"); final_state(); $finish; end end
 waitc(rnd(4)); commit_ready=1; @(negedge clk); commit_ready=0;
 payloads2(id,k,bad_at); rsp2(); end
endtask
task meta2(input [63:0] id, input [19:0] k, input rec);
 begin metadata_valid=1; metadata_identity=id; metadata_key=k; metadata_record=rec;
 #1; while(!metadata_ready) begin @(negedge clk); #1; end @(negedge clk); metadata_valid=0; end
endtask
task publish2(input [63:0] id, input [19:0] k, input integer bad);
 begin offer2(3,id,k); waitc(rnd(4));
 if(bad) begin meta2(id,k,1); end
 else begin meta2(id,k,0); waitc(rnd(3)); meta2(id,k,1); end
 rsp2(); end
endtask
task cev(input [63:0] id, input [19:0] k, input st, input acc, input rev);
 begin consumer_valid=1; consumer_identity=id; consumer_key=k; consumer_stage=st; consumer_accepted=acc; consumer_reverse=rev;
 @(negedge clk); consumer_valid=0; consumer_accepted=0; consumer_reverse=0; end
endtask
task rmev(input [63:0] id, input [19:0] k, input st);
 begin reader_metadata_valid=1; reader_metadata_identity=id; reader_metadata_key=k; reader_metadata_stage=st;
 @(negedge clk); reader_metadata_valid=0; end
endtask
'''


def body(rng: random.Random) -> str:
    out = []
    a = out.append
    a('seed=%d; fcnt=0;' % rng.randrange(1, 1 << 30))
    a('cmd_stage_SM=%d;' % rng.randrange(32))
    bad = rng.random() < 0.45
    kinds = ['stage_skip', 'payload', 'meta_order', 'consumer_id', 'consumer_dup', 'drain_copies', 'acq_prod',
             'begin_pos', 'rel_early', 'rm_early', 'drain_id', 'hydrate_live']
    bad_kind = rng.choice(kinds) if bad else None
    nlife = rng.randint(1, 3)
    pubs = {}           # row -> (pos, producer)
    hyd_rows = rng.sample(range(72), rng.randint(0, 4))
    for r in hyd_rows:
        pos = rng.randrange(0, 8190)
        prod = rng.randrange(1, 1 << 40)
        a('hydrate2(%d, 64\'d%d);' % ((r << 13) | pos, prod))
        pubs[r] = (pos, prod)
    nid = rng.randrange(1000, 1 << 30)
    for life in range(nlife):
        last = life == nlife - 1
        r = rng.choice(list(pubs) + [rng.randrange(72)]) if pubs else rng.randrange(72)
        if r in pubs:
            pos = pubs[r][0] + 1
            if pos > 8191:
                r = rng.randrange(72)
                while r in pubs:
                    r = rng.randrange(72)
                pos = 0
        else:
            pos = 0
        if last and bad_kind == 'begin_pos':
            pos = pos + 1 + rng.randrange(3)
        k = (r << 13) | (pos & 8191)
        w = nid
        nid += 1
        base = rng.randrange(0, 1009)
        kb = rng.randrange(0, (1 << 29)) * 32
        vb = (kb + (1 << 22) + rng.randrange(0, 1 << 20) * 32) % (1 << 34)
        if vb + (1 << 22) > (1 << 34) or kb + (1 << 22) > (1 << 34):
            kb, vb = 0x100000, 0x1000000
        a("cmd_stage_base=%d; cmd_K_base=34'h%x; cmd_V_base=34'h%x;" % (base, kb, vb))
        a('offer2(0, %d, %d); rsp2();' % (w, k))
        a('stages2(%d, %d, %d);' % (w, k, rng.randrange(16) if (last and bad_kind == 'stage_skip') else -1))
        a('commit2(%d, %d, %d);' % (w, k, rng.randrange(528) if (last and bad_kind == 'payload') else -1))
        a('publish2(%d, %d, %d);' % (w, k, 1 if (last and bad_kind == 'meta_order') else 0))
        pubs[r] = (pos, w)
        # readers on random published rows (including this one)
        readers = rng.sample(sorted(pubs), min(len(pubs), rng.randint(1, 3)))
        live = []
        for rr in readers:
            p, prod = pubs[rr]
            kk = (rr << 13) | p
            rid = nid
            nid += 1
            if last and bad_kind == 'acq_prod' and not live:
                prod = prod + 1
            a('cmd_producer=%d; offer2(4, %d, %d); rsp2();' % (prod, rid, kk))
            live.append((rid, kk))
        for rid, kk in live:
            for stg in (0, 1):
                eid = rid + 1 if (last and bad_kind == 'consumer_id' and stg == 1) else rid
                order = rng.randrange(3)
                if last and bad_kind == 'rel_early' and stg == 1:
                    a('offer2(6, %d, %d); waitc(20);' % (rid, kk))
                    break
                if order == 0:   # events before the command
                    a('cev(%d, %d, %d, 1, 0); waitc(%d); cev(%d, %d, %d, 0, 1);' % (eid, kk, stg, rng.randrange(3), eid, kk, stg))
                    a('cmd_consumer=%d; offer2(5, %d, %d); rsp2();' % (stg, rid, kk))
                elif order == 1:  # both in one callback after the command
                    a('cmd_consumer=%d; offer2(5, %d, %d); waitc(%d); cev(%d, %d, %d, 1, 1); rsp2();' % (stg, rid, kk, rng.randrange(4), eid, kk, stg))
                else:
                    a('cmd_consumer=%d; offer2(5, %d, %d); waitc(%d); cev(%d, %d, %d, 1, 0); waitc(%d); cev(%d, %d, %d, 0, 1); rsp2();'
                      % (stg, rid, kk, rng.randrange(4), eid, kk, stg, rng.randrange(3), eid, kk, stg))
                if last and bad_kind == 'consumer_dup' and stg == 0:
                    a('cev(%d, %d, %d, 1, 0); waitc(10);' % (rid, kk, stg))
                if last and bad_kind == 'rm_early' and stg == 0:
                    a('rmev(%d, %d, 1); waitc(10);' % (rid, kk))
                a('waitc(%d); rmev(%d, %d, %d);' % (rng.randrange(3), rid, kk, stg))
        for rid, kk in live:
            a('offer2(6, %d, %d); while(!drain_valid) @(negedge clk); waitc(%d); drain_ready=1; @(negedge clk); drain_ready=0;'
              % (rid, kk, rng.randrange(4)))
            did = rid + 1 if (last and bad_kind == 'drain_id') else rid
            copies = 127 if (last and bad_kind == 'drain_copies') else 255
            a('waitc(%d); drain_done_valid=1; drain_done_identity=%d; drain_done_key=%d; drain_done_allcopies=%d; @(negedge clk); drain_done_valid=0; rsp2();'
              % (rng.randrange(4), did, kk, copies))
        if last and bad_kind == 'hydrate_live' and live:
            a('cmd_producer=%d; offer2(4, %d, %d); rsp2(); hydrate2(%d, 5); waitc(20);' % (pubs[readers[0]][1], nid, live[0][1], live[0][1]))
    a('waitc(10); final_state();')
    return '\n'.join(out), bad_kind


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--seeds', type=int, default=40)
    ap.add_argument('--first', type=int, default=1)
    ap.add_argument('--impl', action='append', default=[], help='name=path (module ot_hbm_accel_kv_lifecycle)')
    ap.add_argument('--jobs', type=int, default=16)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    src = subprocess.check_output(['git', 'show', BASE + ':' + FIXTURE], cwd=ROOT, text=True)
    m = types.ModuleType('fx')
    m.__file__ = str(ROOT / FIXTURE)
    exec(compile(src, str(ROOT / FIXTURE), 'exec'), m.__dict__)
    impls = [ORIGINAL] + [(n, p, 'ot_hbm_accel_kv_lifecycle') for n, p in (x.split('=', 1) for x in a.impl)]

    def run(seed):
        rng = random.Random(seed)
        b, kind = body(rng)
        logs = {}
        for name, path, mod in impls:
            d = out / ('s%04d' % seed) / name
            d.mkdir(parents=True)
            tb = m.bench(b).replace('ot_gpu_qwen_kv_lifecycle_controller', mod)
            tb = tb.replace('task offer(', TASKS + '\ntask offer(', 1)
            tb = tb.replace('initial begin #500000;', 'initial begin #50000000;')
            (d / 'tb.sv').write_text(tb)
            c = subprocess.run(['iverilog', '-g2012', '-s', 'tb', '-o', str(d / 'sim'), str((ROOT / path) if not Path(path).is_absolute() else path), str(d / 'tb.sv')],
                               capture_output=True, text=True)
            if c.returncode:
                return seed, 'COMPILE ' + name + c.stderr[-800:]
            r = subprocess.run(['vvp', '-n', str(d / 'sim')], capture_output=True, text=True)
            log = [l for l in r.stdout.splitlines() if re.match(r'^(CMD|RSP|SH|COMMIT|REQ|DRAIN|FINAL|TIMEOUT|PASS)', l)]
            (d / 'log.txt').write_text('\n'.join(log) + '\n')
            (d / 'sim').unlink()
            logs[name] = log
        ref = logs['original']
        bad = [n for n in logs if logs[n] != ref]
        final = next((l for l in reversed(ref) if l.startswith('FINAL')), 'NOFINAL')
        nreq = sum(1 for l in ref if l.startswith('REQ'))
        return seed, ('MISMATCH ' + ','.join(bad)) if bad else ('OK %d lines %d sectors inject=%s %s' % (len(ref), nreq, kind, final))

    with ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(run, range(a.first, a.first + a.seeds)))
    ok = True
    lines = []
    for seed, r in res:
        lines.append('seed %d: %s' % (seed, r))
        ok &= r.startswith('OK') and 'TIMEOUT' not in r
    (out / 'summary.txt').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    faults = sum(1 for _, r in res if 'fault1' in r)
    print('seeds %d, faulted %d, all identical: %s' % (len(res), faults, ok))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
