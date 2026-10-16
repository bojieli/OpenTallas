#!/usr/bin/env python3
"""Compare the extracted control/lane partition to the actual source parent.

Scope: the existing descriptor/calendar fixture and every public pin on every
active edge. Real target RTL and mapped memory functional models are used on
both sides; this does not qualify full numerical layer/token execution.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[2]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--extract',type=Path,required=True)
    p.add_argument('--hierarchy',type=Path,required=True)
    p.add_argument('--rom-images',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    h=json.loads(a.hierarchy.read_text())
    partition=json.loads((a.extract/'named_partition.json').read_text())
    ports=partition['modules']['dsfd_sp_pq_joint_candidate']['ports']
    outputs={n:len(v['bits']) for n,v in ports.items() if v['direction']=='output'}
    fixture=(ROOT/'rtl/test/dsrom_sys/tb_s81_pq_produced_pins.sv').read_text()
    match=re.search(r'dsfd_sp_pq_produced\s+dut\s*\((.*?)\);',fixture,re.S)
    if not match:raise ValueError('Original source fixture must instantiate its real parent')
    body=match[1];reference={};declarations=[]
    for port,width in outputs.items():
        bindings=re.findall(r'\.'+re.escape(port)+r'\(\s*([^()]*)\)',body)
        live=[x.strip() for x in bindings if x.strip()]
        ref=live[0] if live else 'joint_reference_'+port
        if live and any(x!=ref for x in live):raise ValueError('Ambiguous original output binding '+port)
        if not live:declarations.append(f'wire [{width-1}:0] {ref};')
        if bindings:
            body=re.sub(r'\.'+re.escape(port)+r'\(\s*\)',f'.{port}({ref})',body)
        else:body+=f', .{port}({ref})'
        reference[port]=ref;declarations.append(f'wire [{width-1}:0] joint_candidate_{port};')
    candidate=body
    for port in outputs:
        candidate=re.sub(r'\.'+re.escape(port)+r'\([^()]*\)',f'.{port}(joint_candidate_{port})',candidate)
    candidate=candidate.replace('.ck_ctl(clk)','.ck_ctl(joint_ctl_clk)').replace('.ck_lane(clk)','.ck_lane(joint_lane_clk)').replace('.ck_cmd(clk)','.ck_cmd(joint_cmd_clk)').replace('.ck_calendar(clk)','.ck_calendar(joint_calendar_clk)')
    replacement='dsfd_sp_pq_produced dut('+body+');\n dsfd_sp_pq_joint_candidate candidate('+candidate+');'
    fixture=fixture[:match.start()]+replacement+fixture[match.end():]
    fixture=fixture.replace('module tb_s81_pq_produced_pins;','module tb_s81_pq_joint_lockstep;')
    fixture=fixture.replace('PRODUCED PASS','JOINT_LOCKSTEP PASS')
    candidate_concat='{'+','.join('joint_candidate_'+p for p in outputs)+'}'
    reference_concat='{'+','.join(reference[p] for p in outputs)+'}'
    check='''
 integer joint_mut=0,joint_tick=0,joint_compared=0;
 initial begin if($value$plusargs("mut=%d",joint_mut))begin end end
 always @(negedge clk)joint_tick=joint_tick+1;
 wire joint_ctl_clk=(joint_mut==1&&joint_tick>=280)?1'b0:clk;
 wire joint_lane_clk=(joint_mut==2&&joint_tick>=280)?1'b0:clk;
 wire joint_cmd_clk=(joint_mut==3&&joint_tick>=280)?1'b0:clk;
 wire joint_calendar_clk=(joint_mut==4&&joint_tick>=280)?1'b0:clk;
 always @(posedge clk)begin
  #2;if(rst_n)begin
   joint_compared=joint_compared+1;
   if(CANDIDATE !== REFERENCE)$fatal(1,"JOINT_LOCKSTEP FAIL all-public-pins tick=%0d mut=%0d",joint_tick,joint_mut);
  end
 end
'''.replace('CANDIDATE',candidate_concat).replace('REFERENCE',reference_concat)
    fixture=fixture.replace('module tb_s81_pq_joint_lockstep;','module tb_s81_pq_joint_lockstep;\n'+'\n'.join(declarations)+check)
    fixture=fixture.replace('$display("JOINT_LOCKSTEP PASS', '$display("JOINT_LOCKSTEP PIN_CHECKS %0d",joint_compared);$display("JOINT_LOCKSTEP PASS')
    bench=(a.out/'joint_lockstep.sv').resolve();bench.write_text(fixture)
    for source in a.rom_images.glob('pq_calendar_*.viamap.hex'):
        shutil.copy2(source,a.out/source.name)
    if len(list(a.out.glob('pq_calendar_*.viamap.hex')))!=2:raise ValueError('Both actual compiled calendar ROM images required')
    sources=[ROOT/f for f in h['source_sha256']]
    for source,expected in h['source_sha256'].items():
        if hashlib.sha256((ROOT/source).read_bytes()).hexdigest()!=expected:raise ValueError('Stale original source '+source)
    executable=a.out.resolve()/'obj/Vtb_s81_pq_joint_lockstep'
    verilator=os.environ.get('OT_VERILATOR',str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'))
    cmd=[verilator,'--binary','--timing','-j','8','--top-module','tb_s81_pq_joint_lockstep','--Mdir',str(executable.parent),'-Wno-fatal','-Wno-lint','-Wno-style',*[f'+define+{d}'for d in h['defines']],*[str(f)for f in sources],str((a.extract/'candidate.v').resolve()),str(bench)]
    with(a.out/'build.log').open('w')as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
    cases=[]
    for mode in [0,1,2,3,4]:
        with(a.out/f'mode{mode}.log').open('w')as log:
            rc=subprocess.run([str(executable),f'+mut={mode}','+OT_ROM_DIR='+str(a.out.resolve())],stdout=log,stderr=subprocess.STDOUT).returncode
        text=(a.out/f'mode{mode}.log').read_text()
        ok=(rc==0 and 'JOINT_LOCKSTEP PASS' in text and 'JOINT_LOCKSTEP PIN_CHECKS' in text)if mode==0 else(rc!=0 and 'JOINT_LOCKSTEP FAIL all-public-pins' in text)
        cases.append(dict(mode=mode,exit_code=rc,expected='pass'if mode==0 else'fail',PASS=ok))
        print(json.dumps(cases[-1]),flush=True)
        if not ok:raise RuntimeError(text[-2000:])
    receipt=dict(scope=__doc__,cases=cases,public_output_bits=sum(outputs.values()),outputs=outputs,
                 candidate_sha256=hashlib.sha256((a.extract/'candidate.v').read_bytes()).hexdigest(),
                 fixture_sha256=hashlib.sha256(bench.read_bytes()).hexdigest(),hierarchy_sha256=hashlib.sha256(a.hierarchy.read_bytes()).hexdigest(),
                 source_sha256=h['source_sha256'],rom_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest()for f in a.out.glob('pq_calendar_*.viamap.hex')},
                 source_clocks_unchanged=True,runtime_edges_added=0,physical_qualified=False,full_native_token_qualified=False)
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
