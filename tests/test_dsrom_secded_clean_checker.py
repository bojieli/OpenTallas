import importlib.util,json,random,subprocess,sys
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P/'tools'))
import dsrom_secded_clean_checker as C
from mem_compiler import ecc
def independent_check(cw,k):
    pos=ecc.positions(k);syn=(cw>>k)&511
    for j,p in enumerate(pos):
        if (cw>>j)&1:syn^=p
    ov=cw.bit_count()&1
    return syn,ov,int(syn==0 and ov==0)
def test_original_equations_only_and_no_fix_selector():
    src=(P/'rtl/dft/ot_rom_secded_dec.sv').read_text();cone=(C.OUT/'checker_cone.sv').read_text()
    assert C.extract(src)==cone
    assert 'assign syn[gi] = cw[K + gi] ^ (^t);' in cone
    assert 'pos_of(gj)' in cone and 'assign overall = ^cw;' in cone
    assert 'assign clean = syn_zero & ~overall;' in cone
    assert 'g_fix' not in cone and 'corrected' not in cone
def test_current_nonce_and_finite_priced_state():
    m=json.loads((C.OUT/'model.json').read_text())
    assert m['retained_word_state_bits']==412*(274+74+12)+256*(282+74+12)
    assert m['own_extra_state_beyond_Maxwell_exception_hold_bits']==11312
    assert m['provisional_checker_latency_cycles']==2
    assert not m['engine_opt_in_default'] and not m['PR_admitted']
    assert m['guaranteed_II_cycles'] is None
def test_checker_actual_RTL_against_full_retained_decoder_and_source_oracle(tmp_path):
    count={}
    for k in (256,272):
        d=tmp_path/f'K{k}';d.mkdir();n=k+10;rng=random.Random(20261002+k)
        payloads=[0,(1<<k)-1,1,1<<(k-1),rng.getrandbits(k)]
        words=[]
        for payload in payloads:
            w=ecc.encode(payload,k);words.append(w);words.extend(w^(1<<b) for b in range(n))
        # All1024 check/parity syndromes at full dynamic payload width.
        base=ecc.encode(rng.getrandbits(k),k)
        words.extend(base^(x<<k) for x in range(1024))
        words.extend(base^(1<<a)^(1<<b) for a in range(n) for b in range(a+1,n))
        words.extend(rng.getrandbits(n) for _ in range(256))
        count[k]=len(words)
        mem=d/'vectors.hex'
        mem.write_text(''.join(f'{cw|(syn<<n)|(ov<<(n+9))|(clean<<(n+10)):0{(n+14)//4}x}\n' for cw in words for syn,ov,clean in [independent_check(cw,k)]))
        tb=d/'tb.sv';tb.write_text(f'''`timescale 1ns/1ps
module tb;
localparam K={k}, N={n}, V={len(words)};
reg[N-1:0] cw;
wire[8:0] syn; wire ov,clean,corrected,bad;wire[K-1:0] data;
reg[N+10:0] vectors[0:V-1];integer i;
ot_rom_secded_clean_checker #(.K(K),.R(9),.N(N)) chk(cw,syn,ov,clean);
ot_rom_secded_dec #(.K(K),.R(9),.N(N)) retained(cw,data,corrected,bad);
initial begin
$readmemh("{mem}",vectors);
for(i=0;i<V;i=i+1) begin
cw=vectors[i][N-1:0];#1;
if(syn!==vectors[i][N+8:N] || ov!==vectors[i][N+9] || clean!==vectors[i][N+10]) $fatal(1,"checker mismatch K%0d i%0d",K,i);
if(clean!==(!corrected && !bad)) $fatal(1,"retained flags disagree");
if(clean && data!==cw[K-1:0]) $fatal(1,"unchecked direct data differs");
end
cw={{N{{1'bx}}}};#1;if(clean===1'b1) $fatal(1,"unknown word qualified");
$display("PASS K%0d N%0d vectors%0d",K,N,V);$finish;
end
endmodule
''')
        compiled=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(d/'sim'),str(P/'rtl/dft/ot_rom_secded_dec.sv'),str(C.OUT/'checker_cone.sv'),str(tb)],capture_output=True,text=True)
        assert compiled.returncode==0,compiled.stderr
        run=subprocess.run(['vvp',str(d/'sim')],capture_output=True,text=True)
        assert run.returncode==0 and f'PASS K{k} N{n} vectors{len(words)}' in run.stdout,run.stdout+run.stderr
        print(run.stdout.strip())
    assert count=={256:37860,272:42316}
