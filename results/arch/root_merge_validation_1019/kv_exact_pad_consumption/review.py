import json,pathlib,subprocess,hashlib,time,os
here=pathlib.Path.cwd()
source=pathlib.Path('/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-593176b58-codexmub')
base=pathlib.Path('/srv/opentallas-scratch/claude/qwen-kvsys/codex-canonical-landlag/gen4_bind_r3')
for name in ('rtl','physical'):
    p=here/name
    if not p.exists():p.symlink_to(source/name,target_is_directory=True)
for name in ('head_st_rtl.py','pv_trunk_gen.py','kv_bootage.py'):
    p=here/'tools/qwen_kv_die'/name
    if not p.exists():p.symlink_to(source/'tools/qwen_kv_die'/name)
baseline=json.loads((base/'port_bind_v2.json').read_text())
checks={'die_bound.v':'37779a7cd65c0c2d749c0809c96ddc8c082e50af3180374721f8c6ea6e5c87aa','output_pads.pv.json':'865ba1aa13c3faa1f0868712b8dfb469584a6937f820c5173bfbd4ab3dbd83fc'}
for name,sha in checks.items():assert hashlib.sha256((base/name).read_bytes()).hexdigest()==sha
args=['python3',str(here/'tools/die_port_bind.py'),str(base/'die_bound.v'),'--no-macro-dirs','--pad-file',str(base/'output_pads.pv.json'),'--strap-file',str(base/'straps.json'),'--out',str(here/'candidate.json')]
for root in baseline['rtl_roots']:args += ['--rtl-root',str(source/root)]
for path in baseline['rtl_files']:args += ['--rtl-file',path]
for path in ('rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv','physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_bb.v','physical/qwen_missing_phy/ot_qfd_serdes_112g_x12_phy/ot_qfd_serdes_112g_x12_phy_bb.v'):args += ['--prefer',str(source/path)]
for name in ('qkd_hbm3e_phy_pc','qkd_ckbump','qkd_fwdbump','ot_qkvd_ucie_x64_phy','ot_qkvd_ucie_x64_phy_model','ot_qfd_serdes_112g_x12_phy','qkd_pll_analog_model'):args += ['--allow-model',name]
t=time.time()
with open(here/'candidate.log','w')as out:r=subprocess.run(args,stdout=out,stderr=subprocess.STDOUT)
receipt=dict(args=args,checker_sha256=hashlib.sha256((here/'tools/die_port_bind.py').read_bytes()).hexdigest(),input_sha256=checks,returncode=r.returncode,elapsed_s=time.time()-t,baseline_summary=baseline['summary'],qualified_release=False)
if (here/'candidate.json').exists():
    candidate=json.loads((here/'candidate.json').read_text());receipt['candidate_summary']=candidate['summary'];receipt['summary_identical']=candidate['summary']==baseline['summary'];receipt['die_sha_identical']=candidate['die_sha256']==baseline['die_sha256']
(here/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
raise SystemExit(0 if receipt.get('summary_identical') and r.returncode==1 else 1)
