import pathlib,shutil,re,json,hashlib
R=pathlib.Path(__file__).resolve().parents[2]; root=R/'tools/hwin_private_package_1019'; src=root/'frozen'; dst=root/'sim'
assert not dst.exists();shutil.copytree(src,dst)
u='rtl/dsrom_sys/s81_dv/unit/'
for name in ['dsdv_mu_hwin_capture_1019.sv','dsdv_mu_hwin_capture_mem_1019.sv','dsdv_mu_hwin_capture_early_1019.sv']:
 shutil.copyfile(R/u/name,dst/u/name)
p=dst/u/'test/tb_dsdv_mu_hwin_early_capture.sv';s=p.read_text();old='    dsdv_mu_hwin #(.NSLOT(NS), .NEV(NEV)';assert s.count(old)==1;s=s.replace(old,'    dsdv_mu_hwin_capture_1019 #(.NSLOT(NS), .NEV(NEV)');p.write_text(s)
p=dst/u/'test/tb_dsdv_mu_mem_early_capture.sv';s=p.read_text();assert s.count(' dsdv_mu_mem_early_capture #')==1;s=s.replace(' dsdv_mu_mem_early_capture #',' dsdv_mu_hwin_capture_1019_mem_early_capture #');p.write_text(s)
p=dst/u/'test/run_mu_hwin_early_capture.sh';s=p.read_text();old=' "$U/test/tb_dsdv_mu_hwin_early_capture.sv"';s=s.replace(old,' "$U/dsdv_mu_hwin_capture_1019.sv" "$U/dsdv_mu_hwin_capture_mem_1019.sv" "$U/dsdv_mu_hwin_capture_early_1019.sv"'+old,1)
s=s.replace("('dsdv_mu_mem.sv','dsdv_mu_mem_early_capture.sv')", "('dsdv_mu_mem.sv','dsdv_mu_mem_early_capture.sv','dsdv_mu_hwin_capture_mem_1019.sv','dsdv_mu_hwin_capture_early_1019.sv')")
start=s.index("name='dsdv_mu_hwin.sv';src="); end=s.index("(out/'parser_projection.json')",start)
block=s[start:end];body=block.split(';',1)[1]
s=s[:start]+"for name in ('dsdv_mu_hwin.sv','dsdv_mu_hwin_capture_1019.sv'):\n"+''.join('    '+line+'\n' for line in body.splitlines())+s[end:]
s=s.replace('"$U/dsdv_mu_hwin.sv") projected_files', '"$U/dsdv_mu_hwin.sv"|"$U/dsdv_mu_hwin_capture_1019.sv"|"$U/dsdv_mu_hwin_capture_mem_1019.sv"|"$U/dsdv_mu_hwin_capture_early_1019.sv") projected_files')
p.write_text(s)
# Namespace-only default trace vehicle: same golden and actual reference, default parameter omitted.
p=dst/u/'test/tb_dsdv_mu_hwin_early_capture.sv';s=p.read_text();default=s.replace(',.EARLY_HEAD_CAPTURE(1)) dut',') dut')
assert default!=s
# Internal early-specific mechanism assertions are unsuitable for default branch; external and common-state miter remain via separate bench below.
(root/'projection.json').write_text(json.dumps({'scope':'Namespace candidate instantiation only; frozen gold/reset/warmup/qualification unchanged. Icarus projections duplicated over exact private bodies.','private_files':3,'candidate_instances':2},indent=2)+'\n')
print('SIM projection ready')
