#!/usr/bin/env python3
"""Minimum full-width station reverse-fault state upset qualification.

No forward control protection, mapped retention, root commit guard or timing
qualification is inferred from this component campaign.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RTL = 'rtl/physical/ot_qwen_die_dualfault_station_r22.sv'

def run(out):
    out.mkdir(parents=True, exist_ok=False)
    original = (ROOT / RTL).read_text()
    cases = []
    with tempfile.TemporaryDirectory(prefix='qwen-fault-upsets-') as tmp:
        tmp = Path(tmp)
        for mutant in range(3):
            source = original
            if mutant == 1:
                source = source.replace('wire bad_pair = (bf_q == bfn_q) | (tf_q == tfn_q) | (cf_q == cfn_q);', 'wire bad_pair = 0;')
                source = source.replace('afn_q <= bfn_q & tfn_q & cfn_q & ~bad_pair;', 'afn_q <= ~(bf_q | tf_q | cf_q);')
            (tmp/'dut.sv').write_text(source)
            for tap, split in [(0,0),(1,0),(0,1),(1,1)]:
                regs = ['bf_q','bfn_q','af_q','afn_q']
                if tap: regs += ['tf_q','tfn_q']
                if split: regs += ['cf_q','cfn_q']
                checks = []
                for name in regs:
                    for fault in [0,1]:
                        value = fault if 'n_' not in name else 1-fault
                        sample = '@(posedge clk); #1;' if not name.startswith('af') else '#1;'
                        checks.append(f'''// {name}, valid starting fault={fault}
            @(negedge clk); bf={fault}; tf={fault}; cf={fault};
            repeat(4) @(negedge clk);
            if (decoded !== 1'b{fault}) $fatal(1,"baseline {name}");
            force dut.g_selected.{name} = 1'b{1-value};
            {sample}
            checks=checks+1;
            if (decoded !== 1'b1) begin errors=errors+1; $display("MISSED {name} from fault={fault}"); end
            @(negedge clk); release dut.g_selected.{name};
            repeat(4) @(negedge clk);
''')
                bench = '''module tb;
reg clk=0,rst_n=0,bf=0,tf=0,cf=0;
always #5 clk=~clk;
wire af,afn;
wire decoded = DECODE;
ot_qwen_die_dualfault_station_r22 #(.ENABLE_FULLWIDTH(1),.TAP(TAPVAL),.SPLIT(SPLITVAL)) dut
(.clk(clk),.rst_n(rst_n),.a_d(508'b0),.b_fault(bf),.b_fault_n(~bf),
 .t_fault(tf),.t_fault_n(~tf),.c_fault(cf),.c_fault_n(~cf),.a_fault(af),.a_fault_n(afn));
integer checks=0,errors=0;
initial begin
 #1; rst_n=1; #1; rst_n=0;
 repeat(3) @(negedge clk);
 if ({af,afn} !== 2'b01) $fatal(1,"cold reset pair");
 rst_n=1;
 CHECKS
 if(errors) $fatal(1,"FAIL checks=%0d missed=%0d",checks,errors);
 $display("PASS checks=%0d",checks); $finish;
end
endmodule
'''.replace('DECODE','af' if mutant==2 else 'af | ~afn').replace('TAPVAL',str(tap)).replace('SPLITVAL',str(split)).replace('CHECKS','\n'.join(checks))
                key=f'm{mutant}_t{tap}_s{split}'
                (out/f'{key}.sv').write_text(bench)
                build=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(tmp/'sim'),str(tmp/'dut.sv'),str(out/f'{key}.sv')],capture_output=True,text=True)
                if build.returncode: raise RuntimeError(build.stderr)
                sim=subprocess.run(['vvp',str(tmp/'sim')],capture_output=True,text=True)
                log=sim.stdout+sim.stderr
                (out/f'{key}.log').write_text(log)
                cases.append(dict(case=key,expected_pass=mutant==0,observed_pass=sim.returncode==0,upset_checks=len(checks),exit_code=sim.returncode,log_sha256=hashlib.sha256(log.encode()).hexdigest()))
    result=dict(schema='opentallas.qwen_station_dualfault_upset.v1',pass_all=all(c['expected_pass']==c['observed_pass'] for c in cases),cases=cases,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [RTL,'tools/qwen_station_dualfault_upset_regression.py']},
        covered='Every active reverse-fault state bit, both valid starting polarities, all four branch shapes; cold POR pair; two broken-protection controls',
        excluded=['forward descriptor/go and data protection','multiple simultaneous upsets','combinational faults','mapped sequential driver retention','reset-tree release','root publication guard','SS/FF timing','whole-token adoption'],adoption=False)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(pass_all=result['pass_all'],cases=len(cases),positive_upset_checks=sum(c['upset_checks'] for c in cases if c['expected_pass']))))
    if not result['pass_all']: raise SystemExit(1)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    run(parser.parse_args().out)
