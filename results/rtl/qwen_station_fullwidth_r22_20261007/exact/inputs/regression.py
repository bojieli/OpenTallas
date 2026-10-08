#!/usr/bin/env python3
"""Minimum actual producer/consumer transport slices plus full508-bit station.

Extracts unchanged packing, go admission, delay lines, tile input capture and
unpacking from the current W12 source. Arithmetic, VM scheduling and retirement
are outside this component test and are explicitly not claimed as qualified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SRC = 'rtl/hdc/ot_qwen_me_array_w12.sv'
DST = 'rtl/hdc/ot_qwen_rom_tile_w12.sv'
RTL = 'rtl/physical/ot_qwen_die_fullwidth_station_r22.sv'
DELAY = 'rtl/hdc/ot_hdc_delay.sv'


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def extracted():
    source, sink = (ROOT/SRC).read_text(), (ROOT/DST).read_text()
    packing = re.search(r'    wire \[IBW-1:0\] ib = \{.*?\};', source, re.S).group()
    fields = re.findall(r'i_\w+', packing)
    delays = '\n'.join(re.search(r'    ot_hdc_delay[^\n]* ' + name + r' .*?;', source).group()
                       for name in ['u_ib', 'u_go', 'u_xnet'])
    consumer = sink[sink.index('    localparam integer IBW ='):sink.index('    wire              wrom_re;')]
    decls = consumer[consumer.index('    wire [NW-1:0] b_nout'):consumer.index('    assign {b_nout')]
    source_decls = re.sub(r'\bb_', 'i_', decls)
    # Input stimulus packs named fields in the actual source order. Consumer
    # repacking uses the same names, so a source-vs-consumer permutation is seen.
    reverse = '{' + ', '.join('b_' + f[2:] for f in fields) + '}'
    text = '''module source_cut(input wire clk,rst_n,go,ready,
      input wire[378:0] word, input wire[127:0] xl,
      output wire tgo, output wire[378:0] tb, output wire[127:0] xl_d);
      localparam NW=18, AW=24, IBW=379, TG=4, NXL=1, BD=3, XVM=0, IREG=1;
    ''' + source_decls + '\nassign {' + ','.join(fields) + '} = word;\n' + packing + '\n' + delays + '\nendmodule\n'
    text += '''module sink_cut(input wire clk,rst_n,ib_go,
      input wire[378:0] ib, input wire[127:0] xl, output wire[507:0] observed);
      localparam NW=18,AW=24,TG=4,IREG=1,MEM_EXTRA=0;
    ''' + consumer + f'\nassign observed={{xl_i,go_i,{reverse}}};\nendmodule\n'
    return text, dict(source_slice_sha256=sha(packing+'\n'+delays), consumer_slice_sha256=sha(consumer))


BENCH = r'''
module tb;
    parameter ENABLE=1,TAP=1,SPLIT=1,NEG=0;
    reg clk=0,rst_n=0,go=0,ready=0;
    reg[378:0] word=0; reg[127:0] xl=0;
    reg bf=0,tf=0,cf=0;
    wire tgo; wire[378:0] tbword; wire[127:0] tx;
    source_cut producer(clk,rst_n,go,ready,word,xl,tgo,tbword,tx);
    wire[507:0] src={tx,tgo,tbword};
    reg[507:0] prevsrc=0;
    always @(posedge clk) prevsrc<=src;
    wire[507:0] changed=(NEG==1) ? (src ^ (508'b1 << 337)) :
       (NEG==2) ? {prevsrc[507:380],src[379:0]} :
       (NEG==3) ? {src[507:380],prevsrc[379],src[378:0]} : src;
    wire[507:0] b;
    wire[(TAP?508:1)-1:0] t;
    wire[(SPLIT?508:1)-1:0] c;
    wire af;
    ot_qwen_die_fullwidth_station_r22 #(.ENABLE_FULLWIDTH(ENABLE),.TAP(TAP),.SPLIT(SPLIT)) station
       (clk,rst_n,changed,b,t,c,bf,(NEG==4)?1'b0:tf,cf,af);
    wire[507:0] expected;
    ot_hdc_delay #(.W(508),.D(ENABLE)) reference(clk,rst_n,src,expected);
    wire[507:0] got,refgot;
    sink_cut tile(clk,rst_n,b[379],b[378:0],b[507:380],got);
    sink_cut ref_tile(clk,rst_n,expected[379],expected[378:0],expected[507:380],refgot);
    wire fault_expected;
    ot_hdc_delay #(.W(1),.D(ENABLE?2:0),.RESET(1)) fault_ref
       (clk,rst_n,bf|(TAP&&tf)|(SPLIT&&cf),fault_expected);
    reg af_prev=0;
    always @(posedge clk) af_prev<=af;
    integer n,k,bad=0,checked=0,accepted=0,seen=0; integer seed=9831;
    always #5 clk=~clk;
    initial begin
        repeat(5) @(negedge clk);
        rst_n=1;
        for(n=0;n<2100;n=n+1) begin
            @(negedge clk);
            if(n>8) begin
                checked=checked+1;
                if(b !== expected || (TAP && t !== expected) || (SPLIT && c !== expected)) bad=bad+1;
                if(got !== refgot) bad=bad+1;
                if(((NEG==5)?af_prev:af) !== fault_expected) bad=bad+1;
            end
            if(got[379]) seen=seen+1;
            // Random payload on every edge includes x motion without go;
            // admitted launches remain aligned with their379-bit descriptors.
            for(k=0;k<379;k=k+1) word[k]=$random(seed);
            for(k=0;k<128;k=k+1) xl[k]=$random(seed);
            go=n<2000 ? $random(seed) : 0;
            ready=$random(seed);
            if(go && ready) accepted=accepted+1;
            bf=$random(seed); tf=$random(seed); cf=$random(seed);
            // Directed one-branch faults catch dropped OR legs deterministically.
            if(n%16<3) begin bf=n%16==0;tf=n%16==1;cf=n%16==2; end
        end
        if(accepted!==seen) bad=bad+1;
        if(bad!=0) $fatal(1,"FAIL checks=%0d errors=%0d accepted=%0d seen=%0d",checked,bad,accepted,seen);
        $display("PASS checks=%0d accepted=%0d seen=%0d",checked,accepted,seen);
        $finish;
    end
endmodule
'''


def run(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    fragment, slice_hashes = extracted()
    (out/'transport_slices.sv').write_text(fragment)
    (out/'bench.sv').write_text(BENCH)
    cases = []
    with tempfile.TemporaryDirectory(prefix='qwen-station-r22-') as tmp:
        for enabled in [0,1]:
            for tap,split in [(0,0),(1,0),(0,1),(1,1)]:
                for neg in ([0,1,2,3,4,5] if enabled and tap and split else [0]):
                    key=f'e{enabled}_t{tap}_s{split}_n{neg}'
                    exe=Path(tmp)/key
                    command=['iverilog','-g2012','-s','tb','-o',str(exe),
                        f'-Ptb.ENABLE={enabled}', f'-Ptb.TAP={tap}', f'-Ptb.SPLIT={split}', f'-Ptb.NEG={neg}',
                        str(ROOT/RTL),str(ROOT/DELAY),str(out/'transport_slices.sv'),str(out/'bench.sv')]
                    build=subprocess.run(command,capture_output=True,text=True)
                    if build.returncode: raise RuntimeError(build.stderr)
                    sim=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
                    log=sim.stdout+sim.stderr
                    (out/f'{key}.log').write_text(log)
                    observed_pass=sim.returncode==0 and 'PASS checks=' in log
                    cases.append(dict(case=key,expected_pass=neg==0,observed_pass=observed_pass,
                                      exit_code=sim.returncode,log_sha256=sha(log)))
    result=dict(schema='opentallas.qwen_station_fullwidth_r22_exact.v1',
        pass_all=all(c['expected_pass']==c['observed_pass'] for c in cases), cases=cases,
        source_sha256={p:sha((ROOT/p).read_text()) for p in [SRC,DST,RTL,DELAY,
            'tools/qwen_station_fullwidth_r22_regression.py','tools/uarch_model_qwen_station_r22.py']},
        extracted_slices=slice_hashes, transport_slices_sha256=sha(fragment), bench_sha256=sha(BENCH),
        model_record_sha256=sha((ROOT/'results/uarch/qwen_station_fullwidth_r22_20261007/model.json').read_text()),
        scope='Actual producer pack/go-admission/delay and tile input-register/unpack slices,508-bit station all branch shapes;2091 cycle comparisons per case; no arithmetic substitutes instantiated',
        excluded=['VM request/split scheduling','arithmetic and tile fault production','actual result retirement/publication guard',
                  'complete token','die geometry','mutable fault protection','physical timing'],
        adoption=False)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    if not result['pass_all']: raise SystemExit('component exactness gate failed; immutable logs retained')
    print(json.dumps(dict(pass_all=True,cases=len(cases),adoption=False)))


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--out',required=True,type=Path)
    run(p.parse_args().out)
