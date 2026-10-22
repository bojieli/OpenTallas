import pathlib,re,json,hashlib,subprocess
r=pathlib.Path(__file__).resolve().parents[2];p='rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hwin.sv'
a=subprocess.check_output(['git','-C',str(r),'show','1e057b7bf:'+p]).decode();s=(r/'tools/hwin_private_package_1019/frozen'/p).read_text()
s=s.replace(', parameter integer EARLY_HEAD_CAPTURE = 0','')
patterns=[(r'    wire retire_wrap=.*?begin:g_retire_legacy\n',''),(r'    end else begin:g_retire_early\n.*?    end endgenerate\n',''),(r'        wire event_wrap=.*?begin:g_legacy\n',''),(r'        end else begin:g_early\n.*?        end\n','')]
for pattern,replacement in patterns:
 s,n=re.subn(pattern,replacement,s,flags=re.S);assert n==1,(pattern,n)
assert s==a
out=r/'results/arch/s81_hwin_private_package_1019';(out/'selected_anchor_hwin.sv').write_text(a)
(out/'selected_anchor_projection.json').write_text(json.dumps({'anchor':'1e057b7bf','reference_file':'tools/hwin_private_package_1019/frozen/'+p,'projection':'EARLY_HEAD_CAPTURE=0 exact generate selection, remove unused new prediction wires and final parameter','verdict':'BYTE_IDENTICAL','anchor_sha256':hashlib.sha256(a.encode()).hexdigest(),'frozen_source_sha256':hashlib.sha256((r/'tools/hwin_private_package_1019/frozen'/p).read_bytes()).hexdigest(),'main_short_reference_used':False},indent=2)+'\n')
print('SELECTED_ANCHOR_PROJECTION BYTE_IDENTICAL')
