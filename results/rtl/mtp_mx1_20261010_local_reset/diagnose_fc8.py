import importlib.util, pathlib, subprocess, json
r=pathlib.Path('/srv/opentallas-scratch/claude/closure-loop/hfd_cmdproc_s_mtp_native_mx1_rb-fc8-hm10-96ee08233-tc')
spec=importlib.util.spec_from_file_location('ck',r/'cl/ck_insertion.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
base=next((r/'routes/hfd_cmdproc_s_mtp_native_mx1_rb_fc8_hm10_96ee08233_tc_cal/work/orfs/results/asap7').glob('*/base'))
d=pathlib.Path('/srv/opentallas-scratch/codex/mx1-root');d.mkdir(parents=True,exist_ok=True)
t=m.tcl('tt','4_1_cts.odb','4_cts.sdc',False,'core_clk')
t=t[:t.index('set regs')]+'''report_clock_latency -clock core_clk
report_checks -path_delay max -group_path_count 20 -format full_clock_expanded
report_checks -path_delay min -group_path_count 20 -format full_clock_expanded
report_checks -path_delay max -to [get_ports {t_host[0]}] -format full_clock_expanded
report_checks -path_delay max -to [get_pins -hierarchical {*i0_f_loader*/D}] -format full_clock_expanded
exit
'''
(d/'diag.tcl').write_text(t)
p=subprocess.run(['docker','run','--rm','-v',f'{base}:/base:ro','-v',f'{d}:/t:ro','openroad/orfs:latest','bash','-lc','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /t/diag.tcl'],capture_output=True,text=True)
(d/'tt_paths.txt').write_text(p.stdout+p.stderr);print(str(d/'tt_paths.txt'))
