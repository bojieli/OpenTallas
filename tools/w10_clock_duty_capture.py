#!/usr/bin/env python3
"""Observe retained Verilator objects; never edit RTL or rebuild a hardware model."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = Path('/home/ubuntu/w10-w18-recovery/baseline_wake')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def observer(build, top, exact):
    prefix = top.removeprefix('V') + '__DOT__'
    header = (build / (top + '___024root.h')).read_text()
    leaves = re.findall(r'CData[^;]*? (\w+g_leaf__BRA__\d+__KET____DOT__u_cg__DOT__en_l);', header)
    if exact:
        assert len(leaves) == 8
        groups = [('dut', prefix + 'dut__DOT__', sorted(leaves))]
    else:
        groups = []
        for e in range(2):
            p = prefix + f'dut__DOT__g_el__BRA__{e}__KET____DOT__u_e__DOT__'
            ls = [x for x in leaves if x.startswith(p)]
            assert len(ls) == 1, 'retained array simulator folds identical leaf gates'
            groups.append((f'e{e}', p, ls * 8))
    snapshot = []
    fields = ['time_ps', 'rst_pre', 'rst_post', 'go_pre']
    for name, p, ls in groups:
        fields += [name + '_' + x for x in ('go_elem_pre', 'go_e_pre', 'busy_pre', 'drain_pre', 'wake_pre', 'wake_post', 'leaf_mask')]
        elem_go = prefix+'go' if exact else prefix+'dut__DOT__g_go__BRA__1__KET____DOT__r'
        snapshot += [f'unsigned {name}_ge=r->{p}g_ir__DOT__r_go;',
                     f'unsigned {name}_busy=r->{p}walk_busy;',
                     f'unsigned {name}_drain=r->{p}drain;',
                     f'unsigned {name}_go=r->{elem_go};',
                     f'unsigned {name}_wake=r->{p}g_wake__DOT__g_leaf__BRA__7__KET____DOT__wake;']
    values = ['c->time()', 'reset_before', f'unsigned(r->{prefix}rst_n)', 'go_before']
    for name, p, ls in groups:
        mask = ' | '.join(f'(unsigned(r->{x})<<{i})' for i, x in enumerate(ls))
        values += [name + '_go', name + '_ge', name + '_busy', name + '_drain', name+'_wake',
                   f'unsigned(r->{p}g_wake__DOT__g_leaf__BRA__7__KET____DOT__wake)', '(' + mask + ')']
    return '''#include "verilated.h"
#include "%s.h"
#include "%s___024root.h"
#include <fstream>
int main(int argc,char**argv){
 auto c=std::make_unique<VerilatedContext>(); c->threads(1); c->commandArgs(argc,argv);
 auto t=std::make_unique<%s>(c.get(),""); auto r=t->rootp;
 std::ofstream out(argv[1]); out<<"%s\\n";
 while(!c->gotFinish()){
 unsigned clock_before=r->%sclk;
 unsigned reset_before=r->%srst_n,go_before=r->%sgo;
 %s
 t->eval();
 if(!clock_before && r->%sclk) out<<%s<<"\\n";
 if(!t->eventsPending())break; c->time(t->nextTimeSlot());
 } t->final(); return c->gotFinish()?0:2;
}
''' % (top, top, top, ','.join(fields), prefix, prefix, prefix,
       '\n'.join(snapshot), prefix, '<<","<<'.join(values))


def capture(work):
    work.mkdir(parents=True, exist_ok=False)
    receipt = dict(schema='opentallas.w10.retained-duty-capture.v1', hardware_jobs_launched=0,
                   model_rebuilt=False, records=[], retained_objects={})
    setups = [('exact', RECOVERY/'exact_r2/build', 'Vtb_w10_wake_exact', True)]
    for xf in (4, 8):
        setups.append((f'golden_xf{xf}', RECOVERY/'golden_n4_r1'/f'obj_n4_xf{xf}_nb2_m111_f1p1_front0_bp0',
                       'Vtb_v41_rom_array_w10_test', False))
    bins = {}
    for label, build, top, exact in setups:
        source = work/(label+'.cpp'); source.write_text(observer(build, top, exact))
        inputs = [build/(top+'__ALL.a'), build/(top+'___024root.h'), build/(top+'__verFiles.dat')]
        inputs += [build/(x+'.o') for x in ('verilated','verilated_timing','verilated_threads')]
        include = Path.home()/'.local/opentallas-tools/verilator-5.050/share/verilator/include'
        # Verilator packs its original main into a model object. Rename only
        # that symbol in a private archive; all retained objects stay immutable.
        private_archive = work/(label+'.a')
        subprocess.run(['objcopy','--redefine-sym','main=retained_original_main',str(inputs[0]),str(private_archive)],check=True)
        cmd = ['g++','-std=c++20','-O0','-pthread','-I'+str(include),'-I'+str(build),str(source)]
        cmd += [str(p) for p in [private_archive]+inputs[3:]]+['-o',str(work/label)]
        subprocess.run(cmd,check=True)
        receipt['retained_objects'][label] = {str(p):sha(p) for p in inputs}
        receipt['retained_objects'][label][str(source)] = sha(source)
        bins[label] = work/label
    cases = json.loads((RECOVERY/'golden_n4_r1.json').read_text())['cases']
    runs = [('exact',bins['exact'],[],None)]
    for c in cases:
        d = RECOVERY/'golden_n4_r1'/('n4_nb2_p6_fc_fast_pp_'+c['case'])
        args = [f'+DIR={d}',f'+OT_ROM_DIR={d}',f'+NROWS={c["rows"]}',
                f'+NCFG={len((d/"cfg.hex").read_text().split())}',
                f'+NST={len((d/"stream.hex").read_text().split())}']
        if c['case'].startswith('bf16'): args += ['+BF']
        if (d/'meta.hex').exists(): args = [f'+DIR={d}',f'+OT_ROM_DIR={d}',f'+PHASES={len((d/"meta.hex").read_text().split())}']
        runs.append((c['case'],bins[f'golden_xf{c["XF"]}'],args,d))
    for name, binary, args, vectors in runs:
        trace = work/(name+'.csv')
        run = subprocess.run([str(binary),str(trace)]+args,cwd=work,capture_output=True,text=True)
        log = work/(name+'.log'); log.write_text(run.stdout+run.stderr)
        assert run.returncode == 0 and ('PASS cycles=' in run.stdout if name=='exact' else re.search(r'DONE \d+ 0',run.stdout)), run.stdout[-1000:]
        receipt['records'].append(dict(case=name,command=[str(binary),str(trace)]+args,returncode=run.returncode,
            trace_path=str(trace),trace_sha256=sha(trace),log_path=str(log),log_sha256=sha(log),
            vectors_sha256={} if vectors is None else {str(p):sha(p) for p in sorted(vectors.iterdir()) if p.is_file()}))
    for name in ('exact_r2.json','golden_n4_r1.json'):
        p=RECOVERY/name;receipt.setdefault('qualification_sha256',{})[str(p)]=sha(p)
    (work/'capture.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);a=p.parse_args();capture(a.work)
