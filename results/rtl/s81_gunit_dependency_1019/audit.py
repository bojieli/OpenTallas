import hashlib,json,re,subprocess,pathlib
W=pathlib.Path(__file__).resolve().parents[3]
OUT=pathlib.Path(__file__).resolve().parent
BASE='6339f977f'; CAND='843d4b1ae'; GATE='d9ef27598'; HOP='f03c17fc9'
def git(*a): return subprocess.check_output(['git','-C',str(W),*a])
def blob(r,p):
 try:return git('show',r+':'+p)
 except subprocess.CalledProcessError:return None
def sha(b):return hashlib.sha256(b).hexdigest() if b is not None else None
bench=blob(CAND,'rtl/dsrom_sys/s81_dv/unit/test/run_gunit_bench.sh').decode()
files=set(re.findall(r'(?:rtl|physical)/[^\s"$]+\.(?:sv|v)',bench))
spec=json.loads(blob(CAND,'physical/ref_tile/dsdv_gunit_l5/spec.json'))
files.update(spec['sources'])
macro='physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/'
files.update(git('ls-tree','-r','--name-only',CAND,'--',macro).decode().splitlines())
files.update(['tools/s81_dv/gunit_controls/gen_predecode.py','tools/s81_dv/gunit_controls/gen_predecode_fs.py','tools/s81_dv/layer_prog/lower_gu.py','tools/s81_dv/layer_prog/gu_hc_contract.py','tools/s81_dv/layer_prog/gu_hc_contract.json','tools/ref_tile/specs_s81dv/dsdv_gunit_l5.json'])
hop={}
for l in blob(HOP,'results/rtl/s81_gunit_wm_1019/hop/witness/sources.sha256').decode().splitlines():
 s,p=l.split(None,1)
 if '/src/' in p:hop[p.split('/src/',1)[1]]=s
files.update(hop)
rows=[]
for p in sorted(files):
 b=blob(BASE,p); c=blob(CAND,p); g=blob(GATE,p)
 rows.append({'path':p,'base_sha256':sha(b),'gate2_sha256':sha(g),'candidate_sha256':sha(c),'base_equal_candidate':b==c,'gate2_equal_candidate':g==c,'hop_receipt_sha256':hop.get(p),'candidate_matches_hop_receipt':sha(c)==hop[p] if p in hop else None,'modules_candidate':re.findall(r'\bmodule\s+([A-Za-z_][A-Za-z_0-9]*)',re.sub(r'//[^\n]*|/\*.*?\*/','',c.decode(),flags=re.S)) if c and p.endswith(('.sv','.v')) else [],'scope':'physical-view' if p.startswith(macro) else 'compiler-or-kit' if p.startswith('tools/') else 'RTL graph source'})
helpers=git('show','--format=','--name-only','ed66e7b19').decode().splitlines()
helpers=[p for p in helpers if p.startswith(('tools/closure_loop/','tools/ref_tile/','physical/common_flow/'))]
manifest={'base':git('rev-parse',BASE).decode().strip(),'candidate':git('rev-parse',CAND).decode().strip(),'gate2':git('rev-parse',GATE).decode().strip(),'scope':'Source graph metadata and counterexample to default identity; not elaborated equivalence or native census','files':rows,'ancestor_helper_files_NOT_required_for_artifact_extraction_and_NOT_approved':helpers,'proof_refs':{'controls':'f9f27923f','controls_map_pickup':'12ab196b6','uncapped_map_failure':'3ca0d8055','Q4_component':'b0ad9e1d0','whole_model':'e6269d903','whole_candidate_source':'ed66e7b19','whole_candidate_benches':'4ae2f57dd','iter2_source':'d9ef27598','lifetime_guard':'843d4b1ae','HOP':'f03c17fc9'}}
(OUT/'dependency_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Independent arithmetic counterexample: exact literal expressions in the two source files.
main=blob(BASE,'rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_tail.sv').decode(); cand=blob(CAND,'rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_tail.sv').decode()
assert 'parameter integer SK = 9' in main and 'CAP = 42 * SK' in main
assert 'L = EREADY + 1 + SK + CAP + 2' in main
assert 'SLAT = 17 + (Q4 != 0) + (2 * ITERS - 1) * (15 + (Q4 != 0))' in cand
assert 'L = EREADY + CAP + 3' in cand
eready=1+24+6+24+5+2+16+5+24+80+8+5+8+25+8+6
facts={'EREADY':eready,'main_default_tail_L':eready+1+9+42*9+2,'candidate_all_flags_zero_tail_L':eready+17+39*15+1+3,'candidate_Q4_tail_L':eready+18+39*16+1+3,'default_delta_edges':216,'Q4_additional_edges':40,'default_identity':'DISPROVED','stale_comment_plus55':'not relative to current main','graph_counterexample':['main gated ot_hdc_sinkhorn plus ot_hdc_cg','candidate core-clock ot_hdc_sinkhorn_p even with every new flag zero']}
(OUT/'default_counterexample.json').write_text(json.dumps(facts,indent=2)+'\n')
# Extract evidence only, never the changed RTL or production helpers.
paths=git('ls-tree','-r','--name-only',CAND,'--','results/rtl/s81_gunit_lifetime_1019').decode().splitlines()
for p in paths:
 dest=W/p; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(blob(CAND,p))
(OUT/'artifact_extraction.json').write_text(json.dumps({'source_commit':git('rev-parse',CAND).decode().strip(),'files':[{'path':p,'sha256':sha(blob(CAND,p))} for p in paths],'RTL_files_imported':[],'warning':'Harness proves historical candidate; actual main does not contain that branch. Do not execute make_vehicle against main and assume same source.'},indent=2)+'\n')
print(json.dumps({'audited_files':len(rows),'changed_or_absent_vs_main':sum(not r['base_equal_candidate'] for r in rows),'hop_receipt_mismatches':sum(r['candidate_matches_hop_receipt'] is False for r in rows),'artifacts_extracted':len(paths),'default_facts':facts},indent=2))
