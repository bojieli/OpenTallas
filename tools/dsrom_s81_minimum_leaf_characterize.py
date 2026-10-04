"""One registered unchanged W6/equality/merge diagnostic, no VM engine RTL."""
from pathlib import Path
import argparse,gzip,hashlib,importlib.util,json,re,subprocess,time
ROOT=Path(__file__).resolve().parents[1]
NS=ROOT/'results/uarch/dsrom_s81_minimum_protected_group_20261004'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(cmd,cwd,log):
    t=time.monotonic()
    with log.open('x') as f:p=subprocess.run(cmd,cwd=cwd,stdout=f,stderr=subprocess.STDOUT)
    if p.returncode:raise RuntimeError(f'{cmd[0]} failed: {log}')
    return time.monotonic()-t

def characterize(out,library_helper):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    spec=importlib.util.spec_from_file_location('libmerge',library_helper)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper);helper.OUT=NS
    text,cells=helper.merged('ss')
    allowed={'NAND2x1_ASAP7_75t_R','INVx1_ASAP7_75t_R','BUFx4_ASAP7_75t_R','DFFHQNx1_ASAP7_75t_R'}
    # Preserve the original tables/templates; remove only unselected cells.
    for cell in cells:
        if cell not in allowed:text=text.replace(cells[cell],'')
    lib=out/'allowed_ss.lib';lib.write_text(text)
    for c in ('ss','ff'):
        for f in ('ao','invbuf','oa','simple','seq'):
            (out/f'{f}_{c}.lib').write_bytes(gzip.decompress((NS/'inputs'/f'{f}_{c}.lib.gz').read_bytes()))
    src=(NS/'inputs/w6_codec.sv').read_text()
    functions={}
    for name in ('encode64','decode64'):
        start=src.index('  function automatic logic',src.index('package'))
        for m in re.finditer(r'  function automatic logic[^\n]+',src):
            if name+'(' in m[0]:start=m.start();break
        end=src.index('endfunction',start)+len('endfunction');functions[name]=src[start:end].replace('function automatic logic','function automatic').replace('input logic','input').replace('logic ','reg ')
    defs={'encode':('63:0','71:0',functions['encode64'],'encode64(d)'),
          'decode':('71:0','65:0',functions['decode64'],'decode64(d)'),
          'equal83':('165:0','0:0','','(d[82:0]==d[165:83])'),
          'merge256':('519:0','255:0', '''function automatic [255:0] merge(input [519:0] x);
reg [255:0] z;integer k;begin
z=x[255:0];for(k=0;k<8;k=k+1)if(x[512+k])z[32*k+:32]=x[256+32*k+:32];merge=z;end endfunction''','merge(d)')}
    result={}
    for name,(iw,ow,fun,expr) in defs.items():
        work=out/name;work.mkdir();sv=work/'leaf.sv'
        sv.write_text(f'module leaf(input clk,input [{iw}] din,output reg [{ow}] q);\nreg [{iw}] d;\n{fun}\nalways @(posedge clk) begin d<=din;q<={expr};end\nendmodule\n')
        script=work/'map.ys';mapped=work/'mapped.v'
        script.write_text(f'read_liberty -lib {lib}\nread_verilog -sv {sv}\nhierarchy -top leaf\nproc\nflatten\nopt\ntechmap\nopt\ndfflibmap -liberty {lib}\nabc -liberty {lib}\nclean\ncheck -assert\nwrite_verilog -noattr {mapped}\nwrite_json {work/"mapped.json"}\n')
        elapsed=run(['yosys','-s',str(script)],work,work/'map.log')
        graph=json.loads((work/'mapped.json').read_text())['modules']['leaf']['cells']
        counts={}
        for v in graph.values():counts[v['type']]=counts.get(v['type'],0)+1
        if set(counts)-allowed:raise ValueError('Unexpected mapped cells: '+str(counts))
        timings={}
        for corner in ('ss','ff'):
            tcl=work/f'{corner}.tcl'
            reads='\n'.join(f'read_liberty {out/f"{f}_{corner}.lib"}' for f in ('ao','invbuf','oa','simple','seq'))
            tcl.write_text(reads+f'''\nread_verilog {mapped}
link_design leaf
create_clock -name core -period 1111.111111 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core]
set_clock_uncertainty -hold 25 [get_clocks core]
set_input_transition 20 [get_ports din*]
report_units
report_checks -from [all_registers -output_pins] -to [all_registers -data_pins] -path_delay max -group_count 1 -digits 6 -fields {{slew capacitance input_pin net}}
report_checks -from [all_registers -output_pins] -to [all_registers -data_pins] -path_delay min -group_count 1 -digits 6 -fields {{slew capacitance input_pin net}}
report_check_types -max_slew -max_capacitance
exit
''')
            sec=run(['sta','-exit',str(tcl)],work,work/f'{corner}.log');s=(work/f'{corner}.log').read_text()
            if re.search(r'^Error:',s,re.M):raise RuntimeError(s[-1800:])
            slack=[float(x) for x in re.findall(r'([-\d.]+)\s+slack',s)]
            arrival=[float(x) for x in re.findall(r'([-\d.]+)\s+data arrival time',s)]
            if len(slack)!=2:raise RuntimeError('Missing register-to-register report: '+s[-1500:])
            timings[corner]={'setup_slack_ps':slack[0],'hold_slack_ps':slack[1],'arrival_ps':arrival,'log_sha256':sha(work/f'{corner}.log'),'elapsed_s':sec}
        result[name]={'source_sha256':sha(sv),'mapped_sha256':sha(mapped),'cell_counts':counts,'corners':timings,'map_elapsed_s':elapsed}
    record={'schema':'dsrom.s81.minimum_registered_leaf_characterization.v1','clock_GHz_target':.9,'SS_setup_uncertainty_ps':60,'FF_hold_uncertainty_ps':25,'wire_and_CTS_included':False,'whole_group_or_physical_admission':False,'source_inputs_sha256':{str(p.relative_to(NS)):sha(p) for p in (NS/'inputs').iterdir()},'runner_sha256':sha(__file__),'library_helper_sha256':sha(library_helper),'tools':{t:subprocess.check_output([t,'-V' if t=='yosys' else '-version'],text=True).strip() for t in ('yosys','sta')},'results':result}
    (out/'record.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n');return record
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--library-helper',type=Path,required=True);a=ap.parse_args();r=characterize(a.out,a.library_helper);print(json.dumps({k:v['corners'] for k,v in r['results'].items()},indent=2))
