import sys,importlib.util,subprocess,pathlib
r=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
s=r/'src';b=next((r/'routes/gate/work/orfs/results/asap7').glob('*/base'))
sp=importlib.util.spec_from_file_location('ck',s/'tools/closure_loop/ck_insertion.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
sroot,libs=m.macro_libs(b,'tt')
t=m.tcl('tt','4_1_cts.odb','4_cts.sdc',False,'core_clk',libs,True)
t=t.replace('puts "OT_CK [expr {[dict exists $bnd $i] ? 1 : 0}] $a"','puts "OT_COHORT [expr {[dict exists $bnd $i] ? 1 : 0}] $a $i $cp"')
(out/'census.tcl').write_text(t)
cmd=['docker','run','--rm','-v',f'{b}:/base:ro','-v',f'{out}:/t:ro','-v',f'{sroot}:/src:ro','openroad/orfs:latest','bash','-lc','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /t/census.tcl']
with (out/'census.log').open('w') as f: z=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
print('CENSUS_RC',z.returncode);sys.exit(z.returncode)
