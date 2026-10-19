import copy,json,pathlib,sys
sys.path.insert(0,'tools/qwen_dv');from soft_cone_inventory import inventory
p=pathlib.Path('native_final');d=json.loads((p/'reimport.json').read_text());m=d['modules']['qfd_dv_stream_controls'];d['modules']={'qfd_dv_stream_controls':m}
for c in m['cells'].values():
 if c['type'].startswith('DFF'):c['type']='$_DFF_NATIVE'
r=inventory(d,'qfd_dv_stream_controls');r['scope']='Actual native primitive graph with DFF explicitly recognized as sequential. Native gate counts are combinational depth, not Liberty delay/STA. Original clock input excluded from load violation classification.'
r['highest_output_depth_note']='Endpoint list covers actual native FF inputs; no output timing qualification.'
(p/'depth.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['issues','highest_generic_stage_depth']},indent=2))
