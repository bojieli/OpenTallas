#!/usr/bin/env python3
import pathlib,subprocess,json,collections,hashlib,sys
root=pathlib.Path(__file__).resolve().parents[2];out=pathlib.Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
recs=[]
for w in (16,1):
 dst=out/f'w{w}';dst.mkdir(exist_ok=True)
 ys=f'read_verilog -sv physical/hbm_native_bounded_cdc_1014/ot_hbm_native_bounded_cdc.sv\nhierarchy -check -top ot_hbm_native_bounded_cdc -chparam W {w}\nproc\nflatten\nopt\nmemory_map\nopt\ncheck -assert\nstat\nwrite_json {dst}/actual.json\n'
 p=subprocess.run(['yosys','-p',ys],cwd=root,text=True,capture_output=True);(dst/'yosys.log').write_text(p.stdout+p.stderr)
 if p.returncode:raise RuntimeError(p.stdout[-2000:]+p.stderr[-2000:])
 d=json.loads((dst/'actual.json').read_text())['modules']['ot_hbm_native_bounded_cdc'];clocks={v['bits'][0]:k for k,v in d['ports'].items() if k in ('wclk','rclk')};ff=collections.Counter();storage=0;codebits={b for n,v in d['netnames'].items() if n.startswith('u_codebank.codewords[') for b in v['bits'] if isinstance(b,int)}
 for n,c in d['cells'].items():
  if c['type'] in ('$dff','$dffe','$adff','$adffe','$sdff','$sdffe'):
   bits=int(c['parameters']['WIDTH'],2);ff[clocks[c['connections']['CLK'][0]]]+=bits
   storage+=len(set(c['connections']['Q']) & codebits)
 recs.append({'W':w,'depth':16,'coded_record_bits':78,'stored_codeword_bits':storage,'real_ff_by_root':dict(ff),'real_ff_total':sum(ff.values()),'actual_json_sha256':hashlib.sha256((dst/'actual.json').read_bytes()).hexdigest(),'actual_json':'w'+str(w)+'/actual.json','scope':'Actual Yosys optimized logical FF census; ASIC cell area, pin placement, clock phase and P&R remain unmeasured.'})
 print(recs[-1],flush=True)
 assert storage==16*78 and max(ff.values())<=15000
(out/'census.json').write_text(json.dumps({'schema':'opentallas.native.bounded_cdc.actual_census.v1','cases':recs,'claim_boundary':'Distinct sixteen-entry SECDED codeword FF storage, never plain raw payload array or SRAM area inheritance.'},indent=2)+'\n')
