#!/usr/bin/env python3
"""Exact gate of the production head-die Markov head (rtl/dsrom_sys/mtp/ot_dsrom_markov_head_full340.sv).

NB consecutive bundles of one head die (production: all 85 = 340 A / 340 Markov) with RELEASED weights: lm_head rows
(A K0:4096, B K4096:5120) and mtp.2.markov_head rows are imaged from the released checkpoint for every bundle
(tools/dsrom_markov_head_bundle_image.build, full-snapshot mode), the embedding of the released token is served by
the die's ONE shared lookup (506 macros), x is the released activation. Golden: hdc_golden_v41 chunk8
(A/B/head/Markov/joined per row), die argmax = lowest-row first-max over valid rows on the RTL key (-0 canonical).
The bench checks every Markov engine's joined stream (row identity + bits), the die result, and lockstep (no fault).
Negatives: --mutant 1 (the die reduction ignores the bundle holding the golden argmax) must FAIL on the result;
--mutant 2 (bundle 0's embedding one cycle late) must FAIL (fault). Run on an admitted remote host only.
"""
import argparse, hashlib, json, os, struct, subprocess, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_golden_v41 as G
from dsrom_markov_head_binding_gate import viamap, packed
from dsrom_markov_head_bundle_image import build

SRC = ['rtl/hdc/ot_hdc_delay.sv', 'rtl/common/ot_prefix.sv', 'rtl/v41rom/ot_v41_bmul2.sv', 'rtl/v41rom/ot_dsrom_bmul3.sv',
       'rtl/v41rom/ot_v41_fadd.sv', 'rtl/v41rom/ot_dsrom_head_elem.sv',
       'rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_row.sv',
       'rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_embed_port.sv',
       'rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_head_A.sv',
       'rtl/dsrom_sys/mtp/ot_dsrom_markov_head_full340.sv']


def rows(snapshot, key, r0, n, width):
    idx = json.loads((snapshot / 'model.safetensors.index.json').read_text())['weight_map']
    with (snapshot / idx[key]).open('rb') as f:
        hn = struct.unpack('<Q', f.read(8))[0]; h = json.loads(f.read(hn))[key]
        assert h['dtype'] == 'BF16' and h['shape'] == [129280, width], h
        f.seek(8 + hn + h['data_offsets'][0] + r0 * width * 2); data = f.read(n * width * 2)
    assert len(data) == n * width * 2
    return np.frombuffer(data, dtype='<u2').reshape(n, width)


def rtl_key(bits):
    z = 0 if (bits & 0x7fffffff) == 0 else bits
    return (~z & 0xffffffff) if z >> 31 else (z ^ 0x80000000)


def main(a):
    out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    snap, manifest, inp = a.snapshot.resolve(), a.manifest.resolve(), a.input.resolve()
    m = json.loads(manifest.read_text()); die = next(x for x in m['dies'] if x['die'] == a.die)
    bl = [x for x in die['bundles'] if a.first <= x['bundle'] < a.first + a.nb]
    assert len(bl) == a.nb, 'bundle range'
    base = bl[0]['global_row0']
    for k, x in enumerate(bl):
        assert x['global_row0'] == base + 128 * k, 'contiguous bundle rows'
        assert x['B_VALID_ROWS'] == 128 or k == len(bl) - 1, 'only the last bundle may be ragged'
    die_rows = sum(x['B_VALID_ROWS'] for x in bl)
    receipt = json.loads((inp / 'released_inputs.json').read_text()); token = receipt['token']
    e = np.fromfile(inp / 'embed.bin', dtype='<u2'); assert e.size == 256
    xf = (np.load(inp / 'head_ref.npz')['xf'].astype(np.float32).reshape(-1).view(np.uint32) >> 16).astype('<u2')
    assert xf.size == 5120
    f32 = lambda v: (v.astype(np.uint32) << 16).view(np.float32)
    G.set_arith('chunk8')
    images = out / 'images'; images.mkdir()
    jg = np.zeros(128 * a.nb, dtype=np.uint32); valid = np.zeros(128 * a.nb, dtype=bool); manifests = []
    xa, xb = f32(xf[:4096]), f32(xf[4096:])
    for k, x in enumerate(bl):
        bdir = out / 'img' / f'b{x["bundle"]:03d}'; bdir.parent.mkdir(exist_ok=True)
        rec = build(snap, manifest, bdir, a.die, x['bundle']); manifests.append(dict(bundle=x['bundle'], row0=rec['global_row0'],
            valid=rec['B_VALID_ROWS'], released_payload_sha256=rec['released_payload_sha256']))
        for p in sorted(bdir.glob('*.viamap.hex')):
            (images / f'b{x["bundle"]:03d}_{p.name}').symlink_to(p.resolve())
        nv = x['B_VALID_ROWS']
        h = np.zeros((128, 5120), dtype='<u2'); w = np.zeros((128, 256), dtype='<u2')
        if nv:
            h[:nv] = rows(snap, 'head.weight', x['global_row0'], nv, 5120)
            w[:nv] = rows(snap, 'mtp.2.markov_head.head.weight', x['global_row0'], nv, 256)
        hf = f32(h)
        ra = G.csum(G.mul(hf[:, :4096], xa))
        rb = G.add(G.add(G.csum(G.mul(hf[:, 4096:], xb)), np.float32(0)), np.float32(0))
        joined = G.add(G.add(ra, rb), G.csum(G.mul(f32(w), f32(e))))
        jg[128 * k:128 * k + 128] = joined.view(np.uint32); valid[128 * k:128 * k + nv] = True
    keys = [rtl_key(int(v)) if ok else -1 for v, ok in zip(jg, valid)]
    best = max(range(len(keys)), key=lambda i: (keys[i], -i))
    best_row, best_bits = base + best, int(jg[best])
    (out / 'joined.hex').write_text(''.join(f'{int(v):08x}\n' for v in jg))
    for name, vec, words in [('xa', xf[:4096], 256), ('xb', xf[4096:], 64)]:
        (out / f'{name}.hex').write_text(''.join(f'{packed(vec[16*i:16*i+16]):064x}\n' for i in range(words)))
    ew = {token * 16 + b: packed(e[b * 16:b * 16 + 16]) for b in range(16)}
    viamap(images / 'zero.viamap.hex', {})
    for macro in range(506):
        words = {ad % 4096: v for ad, v in ew.items() if ad // 4096 == macro}
        if words: viamap(images / f'macro{macro:03}.viamap.hex', words)
        else: (images / f'macro{macro:03}.viamap.hex').symlink_to('zero.viamap.hex')
    macro = out / 'macro_ss.v'
    macro.write_text((inp / 'macro_source.v').read_text().replace('rd_out <= word_read(addr_in)', 'rd_out <= #0.744 word_read(addr_in)'))
    mutant_bundle = best // 128
    mon = []
    for k in range(a.nb):
        for q in range(4):
            m_ = f'dut.g_b[{k}].u.g_a[{q}].markov'
            mon.append(f' if({m_}.joined_valid)begin r={m_}.joined_row-ROWBASE;'
                       f'if(r<{128*k+32*q}||r>={128*k+32*q+32}||!vmask[r]||{m_}.joined_bits!==jg[r])$fatal(1,"joined b{k} q{q} row %0d",r);'
                       f'seen[r]=1;njoin=njoin+1;end')
    tb = f'''`timescale 1ns/1ps
module tb;
 reg clk=0;always #0.4165 clk=~clk;reg rst_n=0,start=0;wire start_ready;
 reg[16:0] d_i={token};reg[31:0] transaction=32'h12345;reg[255:0] xa=0,xb=0;
 wire head_go,done,best_valid,fault;wire[16:0] best_row;wire[31:0] best_bits;
 ot_dsrom_markov_head_full340 #(.ENABLE(1),.NB({a.nb}),.ROW_BASE({base}),.DIE_ROWS({die_rows}),.FIRST_BUNDLE({a.first}),
  .PINREG({a.pinreg}),.CACHE_PINREG(0),.IOREG({a.ioreg}),.RINGDLY({a.ringdly}),.A_INPUT_STAGES(4),.MUTANT({a.mutant}),.MUTANT_BUNDLE({mutant_bundle})) dut(
  .clk(clk),.rst_n(rst_n),.start(start),.start_ready(start_ready),.d_i(d_i),.transaction(transaction),
  .ext_embed_valid(1'b0),.ext_embed_data(256'b0),.ext_embed_beat(4'b0),.ext_embed_id(32'b0),.ext_embed_last(1'b0),.ext_embed_fault(1'b0),
  .head_go(head_go),.xa(xa),.xb(xb),.done(done),.best_valid(best_valid),.best_row(best_row),.best_bits(best_bits),.fault(fault));
 reg[255:0] am[0:255],bm[0:63];reg[31:0] jg[0:{128*a.nb-1}];reg vmask[0:{128*a.nb-1}];reg seen[0:{128*a.nb-1}];
 integer cyc=0,g0=-1,r,i,njoin=0,t0=-1,nv=0;reg[8*1024-1:0] dir;
 always @(posedge clk) cyc<=cyc+1;
 always @(negedge clk) if(rst_n) begin
  if(head_go&&g0<0) g0=cyc;
  if(g0>=0&&cyc-g0>=5) begin xa=am[(cyc-g0-5)%256];xb=bm[(cyc-g0-5)%64];end
  if(fault) $fatal(1,"die fault cycle %0d",cyc);
{chr(10).join(mon)}
  if(done) begin
   for(i=0;i<{128*a.nb};i=i+1) if(vmask[i]&&!seen[i]) $fatal(1,"valid row %0d never joined",i+ROWBASE);
   if(njoin!=nv) $fatal(1,"join count %0d != %0d",njoin,nv);
   if(!best_valid||best_row!={best_row}||best_bits!==32'h{best_bits:08x}) $fatal(1,"die argmax row %0d bits %08x (golden {best_row} {best_bits:08x})",best_row,best_bits);
   $display("DIEMETRICS nb={a.nb} rows=%0d start=%0d head_go=%0d done=%0d start_to_done=%0d head_go_to_done=%0d",nv,t0,g0,cyc,cyc-t0,cyc-g0);
   $display("PASS full340 nb={a.nb} sharedlookup joined=%0d argmax row=%0d",njoin,best_row);$finish;
  end
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR");
  $readmemh({{dir,"/xa.hex"}},am);$readmemh({{dir,"/xb.hex"}},bm);$readmemh({{dir,"/joined.hex"}},jg);
  for(i=0;i<{128*a.nb};i=i+1) begin vmask[i]=(i<{die_rows});seen[i]=0;if(i<{die_rows}) nv=nv+1;end
  repeat(5)@(negedge clk);rst_n=1;repeat(3)@(negedge clk);while(!start_ready)@(negedge clk);start=1;t0=cyc;@(negedge clk);start=0;
 end
 initial begin #{a.timeout_ns};$fatal(1,"timeout");end
endmodule
'''.replace('ROWBASE', str(base))
    (out / 'tb.sv').write_text(tb)
    obj = out / 'obj'
    p = subprocess.run(['verilator', '--binary', '--timing', '-j', str(a.jobs), '-Wno-fatal', *a.vflags.split(), '--top-module', 'tb', '--Mdir', str(obj),
                        *[str(ROOT / s) for s in SRC], str(macro), str(out / 'tb.sv')], capture_output=True, text=True)
    (out / 'compile.log').write_text(p.stdout + p.stderr)
    if p.returncode: print(p.stderr[-3000:]); raise SystemExit(2)
    p = subprocess.run([str(obj / 'Vtb'), f'+DIR={out}', f'+OT_ROM_DIR={images}'], capture_output=True, text=True)
    (out / 'sim.log').write_text(p.stdout + p.stderr); print(p.stdout[-2000:], p.stderr[-2000:], flush=True)
    passed = p.returncode == 0 and 'PASS full340' in p.stdout
    metrics = next((l for l in p.stdout.splitlines() if l.startswith('DIEMETRICS')), None)
    rec = dict(schema='opentallas.mtp.head_full340_gate.v1', ioreg=a.ioreg, ringdly=a.ringdly, die=a.die, first_bundle=a.first, nb=a.nb, row_base=base,
               die_rows=die_rows, token=token, pinreg=a.pinreg, mutant=a.mutant, mutant_bundle=mutant_bundle,
               golden=dict(best_row=best_row, best_bits=f'{best_bits:08x}'), passed=passed, exit=p.returncode,
               metrics=metrics, bundles=manifests, manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
               checkpoint=str(snap), source_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SRC},
               physical_qualified=False)
    (out / 'verdict.json').write_text(json.dumps(rec, indent=2) + '\n')
    return passed


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True); ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--snapshot', type=Path, required=True); ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--die', type=int, default=0); ap.add_argument('--first', type=int, default=0)
    ap.add_argument('--nb', type=int, default=85); ap.add_argument('--ioreg', type=int, default=1); ap.add_argument('--ringdly', type=int, default=1); ap.add_argument('--pinreg', type=int, default=1)
    ap.add_argument('--mutant', type=int, default=0); ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--timeout-ns', type=int, default=60000)
    ap.add_argument('--vflags', default='', help='extra Verilator flags (NB=85: -fno-inline bounds elaboration memory)')
    raise SystemExit(0 if main(ap.parse_args()) else 1)
