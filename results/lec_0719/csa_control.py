import pathlib,shutil,subprocess,json,sys
p=pathlib.Path.cwd();fx=p/'lec_csa31'
for mode in ['pre','fix']:
 k=p/('csa_'+mode);(k/'rtl').mkdir(parents=True,exist_ok=True)
 shutil.copyfile(fx/'lec_bbx.v',k/'rtl/lec_bbx.v');shutil.copyfile(fx/('lec_t1_'+mode+'.sv'),k/'rtl/lec_t1.sv')
 n=k/'run/results/asap7/lec_t1/base';n.mkdir(parents=True,exist_ok=True);shutil.copyfile(fx/('netlist_'+mode+'.v'),n/'1_2_yosys.v')
 (k/'config.mk').write_text('export DESIGN_NAME = lec_t1\nexport PLATFORM = asap7\nexport VERILOG_FILES = /work/rtl/lec_bbx.v /work/rtl/lec_t1.sv\nexport VERILOG_INCLUDE_DIRS = /work/rtl\nexport VERILOG_DEFINES = -DSYNTHESIS\nexport SYNTH_HDL_FRONTEND = slang\nexport SYNTH_BLACKBOXES = lec_bbx\n')
 r=subprocess.run([sys.executable,str(p/'lec.py'),str(k),'--mem','4']);d=json.load(open(k/'lec/lec.json'));print(mode,r.returncode,d['verdict'],flush=True)
 assert (r.returncode,d['verdict'])==((1,'NOT EQUIVALENT') if mode=='pre' else (0,'EQUIVALENT'))
 if mode=='pre':assert sorted(x['point'] for x in d['failing'])==[f'po:y[{i}]' for i in range(24,31)]
