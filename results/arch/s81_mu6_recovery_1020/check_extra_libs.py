import glob,re,json,pathlib
v=pathlib.Path('/work/results/asap7/opentallas_dsdv_gunit_l5_asap7_ref_dsdv_gunit_l5_ro3_ro3_648ee10c0/base/6_final.v').read_text()
r=[]
for p in glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*TT*FAKE.lib'):
 for n in re.findall(r'cell\s*\(\s*([^()]+?)\s*\)',pathlib.Path(p).read_text()):
  n=n.strip('"');r.append(dict(library=p,cell=n,netlist_occurrences=len(re.findall(r'(?<![\w$])'+re.escape(n)+r'(?![\w$])',v))))
json.dump(r,open('/audit/extra_libs_unused.json','w'),indent=2)
assert all(x['netlist_occurrences']==0 for x in r),r
print('EXTRA_LIBS_UNUSED_PASS',len(r))
