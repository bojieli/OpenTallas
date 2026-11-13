"""Native, binary-power-up qualification of explicitly selected R8 SRAM banks.

Run by r8_strap_lec under ot-run. Full-width actual-macro lockstep and mutants
are combined with W1 all-binary-state convergence SAT for the exact selected
shape. The reviewed source hash enforces the bit-independent counter topology.
This is not a four-state X-startup proof or physical sign-off.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
MODULE = 'rtl/common/ot_dp_dly_cnt_sram.sv'
MACRO = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v'
# Reviewed resetless modulo32 common pointer and independent bit slices.
MODULE_SHA = '8432571b47468098f683d898da036067e1bd49b608c5e8e17ad867a1921de10f'
MACRO_SHA = '9286563862a9cac862351ef03094fab7f53edd82c38784349d588e0958e0bde2'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def shape_ok(bank):
    return (bank.get('module') == 'ot_dp_dly_cnt_sram' and bank.get('BASE') == 0
            and 1 <= bank['W'] <= 291 and 0 <= bank['DMAX'] <= 32
            and 1 <= bank.get('CW', 5) <= 6 and bank['DMAX'] < (1 << bank.get('CW', 5)))


def bench_text(coupons, mutate_tie=False):
    """All bits, continuously from first defined sample; reset stimulus never masks checks."""
    width = max(b['W'] for b, _ in coupons)
    lines = ['`timescale 1ns/1ps', 'module tb;', 'reg clk=0; always #0.4165 clk=~clk;',
             f'reg [{width-1}:0] d;', 'reg [31:0] age=0;', f'wire [{len(coupons)-1}:0] bad;']
    for k, (b, count) in enumerate(coupons):
        w, mx, cw = b['W'], b['DMAX'], b.get('CW', 5)
        gate_count = (count + 1 if count < mx else count - 1) if mutate_tie and k == 0 and mx else count
        lines += [f'wire [{w-1}:0] q{k};',
                  f'ot_dp_dly_cnt_sram #(.W({w}),.DMAX({mx}),.BASE(0),.CW({cw})) u{k} '
                  f'(.clk(clk),.strap_cnt({cw}\'d{gate_count}),.d(d[{w-1}:0]),.q(q{k}));']
        if count:
            lines += [f'reg [{w-1}:0] h{k}[0:{count-1}];',
                      f'always @(posedge clk) begin h{k}[0]<=d[{w-1}:0]; '
                      f'for(integer j=1;j<{count};j=j+1) h{k}[j]<=h{k}[j-1]; end',
                      f'assign bad[{k}]=(age>=32\'d{count})&&(q{k}!==h{k}[{count-1}]);']
        else:
            lines += [f'assign bad[{k}]=(q{k}!==d[{w-1}:0]);']
    lines += ['reg [63:0] rnd=64\'h9e3779b97f4a7c15;', 'reg warm_reset=1;',
              "initial begin d='0; #0.1; for(integer n=1;n<=1024;n=n+1) begin",
              'if(n>1) @(negedge clk); warm_reset=!((n>=128&&n<139)||(n>=777&&n<793));',
              f'for(integer b=0;b<{width};b=b+1) begin rnd={{rnd[62:0],rnd[63]^rnd[62]^rnd[60]^rnd[59]}}; '
              'd[b]=rnd[0]^((n%29)==0)^(!warm_reset&&((b%7)==0)); end',
              "#0.001; if(|bad) $fatal(1,\"SRAM_SELECTED_MISMATCH\");",
              "@(posedge clk); age=32'(n); #0.001; if(|bad) $fatal(1,\"SRAM_SELECTED_MISMATCH\"); end",
              '$display("SRAM_SELECTED_PASS"); $finish; end', 'endmodule']
    return '\n'.join(lines) + '\n'


def execute(cmd, log, env):
    with Path(log).open('w') as f:
        return subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env=env).returncode


def qualify(tn, banks, variants, out, theorem_receipt=None, simulation_only=False, simulation_receipt=None):
    """Explicit native result; callers must not relabel this as legacy EQUIVALENT."""
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    hashes = dict(module=digest(ROOT / MODULE), macro=digest(ROOT / MACRO))
    result = dict(schema='opentallas.r8_sram_native.v1', type=tn, banks=banks, hashes=hashes, backend_sha256=digest(__file__),
                  startup='all arbitrary binary states; ordinary uninitialized 4-state X is outside contract',
                  reset='none; warm reset elsewhere preserves all-bit history', rows=[], verdict='FAIL')
    if hashes != dict(module=MODULE_SHA, macro=MACRO_SHA) or not all(shape_ok(b) for b in banks):
        result['reason'] = 'unreviewed source/macro topology or unsupported declared shape'
        (out / 'receipt.json').write_text(json.dumps(result, indent=1)+'\n')
        return result
    env = dict(os.environ)
    env['PATH'] = str(Path.home()/'.local/opentallas-tools/bin') + ':' + env['PATH']
    if any(v['ties'].get(b['site']) != v['gold'].get(b['site']) for v in variants for b in banks):
        result['reason'] = 'selected top-level tie differs from independent bind-report pad-minus-base'
        (out/'receipt.json').write_text(json.dumps(result, indent=1)+'\n')
        return result
    result['selected_variants'] = variants
    coupons = []
    for b in banks:
        for count in sorted({v['gold'][b['site']] for v in variants}):
            if not 0 <= count <= b['DMAX']:
                raise ValueError(f"selected SRAM count {count} outside declared bank")
            coupons.append((b, count))
    # Ensure the first tie-mutated bank can exhibit a legal alternate age.
    coupons.sort(key=lambda x: (not bool(x[0]['DMAX']), x[0]['site'], x[1]))
    kinds = ['nominal']
    if any(b['DMAX'] for b, _ in coupons): kinds.append('tie_mutant')
    if any(c >= 3 for _, c in coupons): kinds.append('age_mutant')
    if any(c > 15 for _, c in coupons): kinds.append('count_mutant')
    if simulation_receipt:
        sim = json.loads(Path(simulation_receipt).read_text())
        if (sim.get('hashes') != hashes or sim.get('backend_sha256') != result['backend_sha256']
                or sim.get('banks') != banks or sim.get('selected_variants') != variants
                or sim.get('verdict') != 'WAIT_BINARY_FORMAL'):
            raise ValueError('SRAM simulation cache does not match source/backend/selected banks/variants')
        result['rows'] = sim['rows']
        kinds = []
    for kind in kinds:
        tb = out / f'{kind}.sv'
        tb.write_text(bench_text(coupons, kind == 'tie_mutant'))
        flags = {'age_mutant':['-DOT_DP_DLY_SRAM_AGE_MUT'], 'count_mutant':['-DOT_DP_DLY_SRAM_COUNT_TRUNC_MUT']}.get(kind, [])
        obj = out / f'obj_{kind}'
        cmd = ['verilator','--binary','--timing','--x-initial','unique','--x-assign','unique','-j','4',
               '-Wno-fatal','-Werror-WIDTH','-Werror-SELRANGE','-DOT_MEM_NO_INIT','--top-module','tb',
               '--Mdir',str(obj),*flags,str(ROOT/MODULE),str(ROOT/MACRO),str(tb)]
        rc = execute(cmd, out/f'{kind}_build.log', env)
        if rc:
            result['rows'].append(dict(kind=kind, build_rc=rc, pass_=False)); break
        for seed in (1,17,93):
            log = out/f'{kind}_seed{seed}.log'
            rc = execute([str(obj/'Vtb'), f'+verilator+seed+{seed}', '+verilator+rand+reset+2'], log, env)
            text = log.read_text()
            ok = (rc == 0 and 'SRAM_SELECTED_PASS' in text) if kind == 'nominal' else (rc != 0 and 'SRAM_SELECTED_MISMATCH' in text)
            result['rows'].append(dict(kind=kind, seed=seed, rc=rc, pass_=ok))
    if not result['rows'] or not all(r['pass_'] for r in result['rows']):
        result['reason'] = 'native lockstep or required mutant control failed'
        (out/'receipt.json').write_text(json.dumps(result, indent=1)+'\n')
        return result
    if simulation_only:
        result['verdict'] = 'WAIT_BINARY_FORMAL'
        (out/'receipt.json').write_text(json.dumps(result, indent=1)+'\n')
        return result
    cache = json.loads(Path(theorem_receipt).read_text()) if theorem_receipt else {}
    if cache and cache.get('hashes') != hashes:
        raise ValueError('SRAM theorem cache source/macro hash mismatch')
    # One-bit universal proof is valid for this exact reviewed independent-bit
    # topology; full-width native comparisons above test all actual bit positions.
    for mx, cw in sorted({(b['DMAX'], b.get('CW',5)) for b in banks}):
        if mx == 0:
            continue
        tag = f'all_binary_max{mx}_cw{cw}'
        proven = next((r for r in cache.get('rows', []) if r.get('kind') == 'all_binary_convergence'
                       and r.get('DMAX') == mx and r.get('CW') == cw and r.get('BASE') == 0
                       and r.get('steps', 0) >= 36 and r.get('pass_') is True), None)
        if proven:
            result['rows'].append(dict(proven, cached_from=str(theorem_receipt), cache_sha256=digest(theorem_receipt)))
            continue
        formal = ROOT/'rtl/test/kv_r8_sram_delay/formal_domain.sv'
        script = (f'read_verilog -formal -sv -D SYNTHESIS -D OT_MEM_NO_INIT {ROOT/MODULE} {ROOT/MACRO} {formal}; '
                  f'chparam -set BASE 0 -set DMAX {mx} -set CW {cw} formal_domain; '
                  'prep -top formal_domain -flatten; setattr -mod -unset keep_hierarchy; setattr -unset keep_hierarchy; '
                  f'flatten; memory_map; opt; select -module formal_domain; write_rtlil {out/tag}.il; async2sync; chformal -lower; opt; '
                  'sat -seq 36 -prove-asserts -verify -set-assumes -set-def-inputs -set-init-def')
        log = out/f'{tag}.log'
        rc = execute(['yosys','-Q','-T','-p',script], log, env)
        ok = rc == 0 and 'SAT proof finished - no model found: SUCCESS!' in log.read_text()
        result['rows'].append(dict(kind='all_binary_convergence', DMAX=mx, CW=cw, BASE=0, steps=36, rc=rc, pass_=ok))
    result['theorem'] = ('For any later time choose the state 36 cycles earlier as the arbitrary initial binary state. '
                         'The universal convergence proof applies again because count is static and the DUT has no reset '
                         'or absolute-time state. Thus the proved delay holds at every later cycle; no DUT initialization '
                         'or invalid-payload masking is assumed. All stored and read bits are independent in the pinned source.')
    result['verdict'] = 'PASS_BINARY_NATIVE' if result['rows'] and all(r['pass_'] for r in result['rows']) else 'FAIL'
    (out/'receipt.json').write_text(json.dumps(result, indent=1)+'\n')
    return result
