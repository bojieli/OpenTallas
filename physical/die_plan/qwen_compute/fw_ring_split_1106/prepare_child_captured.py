import argparse,json,sys,pathlib,re
a=argparse.ArgumentParser();a.add_argument('--plan',required=True);a.add_argument('--bound',required=True);x=a.parse_args();S=pathlib.Path(__file__).resolve().parents[3];sys.path[:0]=[str(S/'tools/die_plan'),str(S/'physical/die_plan/qwen_compute/cores')]
import schema,gen_phys,param_wrap,sle_ctl_pins,cells
P=pathlib.Path(x.plan);p=schema.load(P);t='slw_fw_v1__cl51d45468';band='x_ctl_i';W=632;m='fw_cland_w632_n';params=dict(W=W,DEPTH=4,WFALL=1,WREG=1,DSREP=1)
bound=pathlib.Path(x.bound).read_text();assert f'ot_dp_clk_landing_cas {param_wrap.param_text(params)} u_cland_x_ctl_i (' in bound
pins=[(b,x,y,f) for n,b,l,x,y,f in gen_phys.type_pins(schema.Plan(p,P),t) if n==band];assert len(pins)==W and {a[3] for a in pins}=={'N'}
order=[a[0] for a in sorted(pins,key=lambda a:(a[1],a[0]))];outline=[109.2,51.84];table=sle_ctl_pins.ring_pins(m,W,'N',outline,order)
out=S/'physical/die_plan/qwen_compute/fw_ring_split_1106';out.mkdir(exist_ok=True);(out/'wrapper.sv').write_text(param_wrap.wrapper_sv(m,'ot_dp_clk_landing_cas',params));(out/'pins.json').write_text(json.dumps(table,indent=1)+'\n')
(out/'child.json').write_text(json.dumps(dict(master=m,type=t,band=band,params=params,origin_um=[275.568,1270.08],outline_um=outline,cells=cells.ring_cells(W-1),cycles_added=0,scope='Unadopted child candidate; reset/collector event and source equivalence required before parent GEN'),indent=1)+'\n')
print('CHILD_CANDIDATE',m,len(pins),cells.ring_cells(W-1),'actual parent bitorder captured; no parent event/adoption')
