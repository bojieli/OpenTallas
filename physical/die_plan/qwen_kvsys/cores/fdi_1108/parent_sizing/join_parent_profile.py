from pathlib import Path
import json,re,os,shutil,sys
r=Path(sys.argv[1])
profile=json.load(open(r/'native_cut_profile.json'));top=profile['top'];body=(r/'qkd_hr_host_parent.sv').read_text();fixed='qkd_hr_host_parent_fixed_c45'
body,n=re.subn(r'^module\s+'+re.escape(top)+r'(?=\s*\()', 'module '+fixed,body,count=1,flags=re.M);assert n==1
head=re.search(r'^module\s+'+fixed+r'\((.*?)\);',body,re.M|re.S);assert head
ports=[x.strip() for x in head[1].split(',')];assert all(re.fullmatch(r'\w+',x) for x in ports)
decls=re.findall(r'^\s*(?:input|output|inout)\s+(?:signed\s+)?(?:\[[^]]+\]\s+)?\w+\s*;',body,re.M)
decls=[d for d in decls if re.search(r'(\w+)\s*;',d)[1] in ports]
assert len(decls)==len(ports) and {re.search(r'(\w+)\s*;',d)[1] for d in decls}==set(ports)
params={'D2D_BOOT_ORDER':1,'ENABLE_NATIVE':1,'ENABLE_SERVICE':1,'ENABLE_TOKEN':1,'NL':2,'REQUIRE_MISSION_START':1}
# These are the actual bound instance values; preserve the declared parameter ABI but reject any other profile.
actual=(r/'rtl/kv3_hub_Wi_part_bound.sv').read_text();pm=re.search(r'\b'+top+r'\s*#\((.*?)\)\s*u_host\s*\(',actual,re.S);assert pm
assert {k:int(v) for k,v in re.findall(r'\.(\w+)\((\d+)\)',pm[1])}==params
lines=['// Exact native HOST source composition; fixed profile guarded, whole native outer ABI retained.', 'module '+top+' #(', ',\n'.join(' parameter integer '+k+' = '+str(v) for k,v in params.items()), ') ('+', '.join(ports)+');']
lines+=decls
lines+=['generate if ('+' || '.join(k+' != '+str(v) for k,v in params.items())+') begin : g_unsupported_native_profile',' initial $error("unsupported native HOST physical profile");','end endgenerate',fixed+' u_native_parent (',',\n'.join(' .'+p+'('+p+')' for p in ports),');','endmodule',body]
(r/'native_host_profile.sv').write_text('\n'.join(lines)+'\n')
