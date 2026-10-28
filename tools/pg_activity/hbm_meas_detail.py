import json
aS=630.72*1036.8/1e6; aN=630.72*1209.6/1e6; slot=16*(aS+aN)
P={"mean":{"s":0.2183586,"n":0.2253245,"bdc_pl":0.01441102,"bdc_cts":0.02784638},
   "peak":{"s":0.2244373,"n":0.2317754,"bdc_pl":0.01460438,"bdc_cts":0.02804141}}
clk_per_reg=0.01383314/10670
out={"schema":"pg-activity-5.hbm.v1","label":"power basis UNCHECKED-ESTIMATE (placed halves + BDC clock factor); activity MEASURED (14 cases, tb_hgi_sm_e2e g_sm[0].u_sm, intel2 pg-act4-1027/hbm)",
 "regs":{"s":145605,"n":149992},"match":{"s":"130929/145605","n":"135169/149992","bdc":"10658/10670"},"cases":{}}
for k,v in P.items():
  f=v["bdc_cts"]/v["bdc_pl"]
  mult=16*(v["s"]+v["n"])*f
  add=16*(v["s"]+145605*clk_per_reg+v["n"]+149992*clk_per_reg)
  out["cases"][k]=dict(W_s=v["s"],W_n=v["n"],bdc_meas_cts_factor=f,slot_W_mult=mult,slot_W_add=add,
     w_mm2_mult=mult/slot,w_mm2_add=add/slot)
out["sm_slot"]={"area_mm2":slot,"w_mm2_meas_cts":max(out["cases"]["peak"]["w_mm2_mult"],out["cases"]["peak"]["w_mm2_add"]),
  "basis":"peak case (case1, largest summed toggle), max of BDC multiplicative CTS factor and additive clock-per-register"}
json.dump(out,open("hbm_power_meas5.json","w"),indent=1); print(json.dumps(out,indent=1))
