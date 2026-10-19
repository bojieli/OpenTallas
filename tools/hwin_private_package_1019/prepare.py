import pathlib,subprocess,re,hashlib,json
R=pathlib.Path(__file__).resolve().parents[2]; O=R/'results/arch/s81_hwin_private_package_1019'; O.mkdir(parents=True,exist_ok=True)
def blob(p):return subprocess.check_output(['git','-C',str(R),'show','69e7ec3a6:'+p]).decode()
def sha(t):return hashlib.sha256(t.encode()).hexdigest()
u='rtl/dsrom_sys/s81_dv/unit/'
names=['hwin','boot_enable','retire_due','retire_advance','slot_step','record','decode24','fire_flag','cfg_bad','phase_action','mem','reset_tree','mem_early_capture','early_current_hit']
mp={'dsdv_mu_'+n:'dsdv_mu_hwin_capture_1019'+('' if n=='hwin' else '_'+n) for n in names}
groups=[('dsdv_mu_hwin.sv','dsdv_mu_hwin_capture_1019.sv',names[:10]),('dsdv_mu_mem.sv','dsdv_mu_hwin_capture_mem_1019.sv',names[10:12]),('dsdv_mu_mem_early_capture.sv','dsdv_mu_hwin_capture_early_1019.sv',names[12:])]
records=[]
for src,dst,ns in groups:
 s=blob(u+src); modules=re.findall(r'(?m)^module\s+(\w+).*?^endmodule[^\n]*\n?',s,re.S)
 bodies=[]
 for n in ns:
  old='dsdv_mu_'+n
  matches=re.findall(r'(?m)^(?:\(\*[^\n]*?\*\)\s*)?module\s+'+old+r'\b.*?^endmodule[^\n]*\n?',s,re.S)
  assert len(matches)==1,(old,len(matches)); body=matches[0]
  renamed=re.sub(r'\b('+'|'.join(map(re.escape,mp))+r')\b',lambda m:mp[m[0]],body)
  inv={v:k for k,v in mp.items()}
  rev=re.sub(r'\b('+'|'.join(map(re.escape,inv))+r')\b',lambda m:inv[m[0]],renamed)
  assert rev==body
  records.append(dict(source=src,original=old,private=mp[old],file=dst,body_sha256=sha(body),reverse_sha256=sha(rev)))
  bodies.append(renamed)
 target=R/u/dst;assert not target.exists();target.write_text('`timescale 1ns/1ps\n// Private exact selected-anchor HWIN source; namespace projection only.\n'+ '\n'.join(bodies))
# Preserve frozen reference/source/bench dependencies as validation snapshots; no old public file import.
inputs=['rtl/lib/ot_rst_relay.sv','rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v','physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.v']+[u+n for n in ['dsdv_mu_hslot.sv','dsdv_mu_mem.sv','dsdv_mu_mem_early_capture.sv','dsdv_mu_hwin.sv','test/tb_dsdv_mu_hwin_early_capture.sv','test/tb_dsdv_mu_mem_early_capture.sv','test/run_mu_hwin_early_capture.sh']]
stage=R/'tools/hwin_private_package_1019/frozen'
for p in inputs:
 t=stage/p;t.parent.mkdir(parents=True,exist_ok=True);t.write_text(blob(p))
(O/'extraction_map.json').write_text(json.dumps({'main':subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD']).decode().strip(),'source_commit':'69e7ec3a6','map':records,'external_leaf':'ot_sram_1r1w_64x16_m1'},indent=2)+'\n')
print('EXTRACTED',len(records),'types; reverse projection PASS')
