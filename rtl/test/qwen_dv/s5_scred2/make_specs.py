#!/usr/bin/env python3
"""Write the QW-SLICE7-LEAVES SCRED kit specs (main + fallback per leaf). Usage: make_specs.py CFG RED_AREA SC_AREA
CFG = LA/LM tag of the bounded netlist (e.g. 44); *_AREA = mapped Liberty std area (um2) of that netlist."""
import json,sys,math
from pathlib import Path
cfg,ra,sa=sys.argv[1],float(sys.argv[2]),float(sys.argv[3])
G=43.2/4  # 10.8 um outline grid
def side(area,util,aspect):
    a=area/util; w=math.sqrt(a*aspect); h=a/w
    r=lambda x: round(math.ceil(x/G)*G,1)
    return r(w),r(h)
HDC=["rtl/hdc/ot_hdc_vreduce.sv","rtl/hdc/ot_hdc_fastfp.sv","rtl/hdc/ot_hdc_fp32_add_lat.sv","rtl/hdc/ot_hdc_fp32_mul_lat.sv",
     "rtl/hdc/ot_hdc_prefix.sv","rtl/hdc/ot_hdc_delay.sv","rtl/hdc/ot_hdc_sfu.sv","rtl/hdc/ot_hdc_sfu_q.sv"]
LA,LM=int(cfg[0]),int(cfg[1])
PRICE={'red':f"red_we/red_addr/red_data/fault +{(LM-3)+11*(LA-3)} edges per reduction result vs the old kit qfd_dv_s5_red (OFF {(LM-3)+11*(LA-3)+2} vs the bare module); rd_v +0; reset release +1 boot (ring phases +2)",
       'sc':f"chain pass / own words / taps +0; root argmax->tok/TOK +2; root total->w1 +{5*(LA-3)}; fused rsqrt->RB/w1 +{5*(LA-3)+(LM-3)+(LA-3)+3*(3*(LM-3)+(LA-3))}; sc_cfg apply +1 (two face stages); reset release +4 boot (rc..rf) and ring phases +2"}
def spec(kind,name,w,h,cfgname):
    top=f"qfd_dv_s5_{kind}2_leaf"
    srcs=[f"rtl/qwen_dv/s5/{top}.sv",f"rtl/qwen_dv/s5/{cfgname}.sv",f"rtl/qwen_dv/s5/{cfgname}_helpers.sv"]
    if kind=='red':
        pins={"N":["l_ov","l_out","l_red0","l_redsq0","l_last0","l_raddr0"],"W":["ck","rst_n"],"S":["red_we","red_addr","red_data","rd_v","busy","fault"]}
        purpose="QW-SLICE7 Q.STA.SLICE.2: SU reducer leaf red2 (bounded native fanout, LA/LM-cut FP, kept rings) of the hardened one-level slice"
    else:
        pins={"W":["sc_cfg","am_v","am_idx","am_val","am_u","w1_we","w1_addr","w1_data","tok_v","tok_idx","tok_own","tok_val","tok_user","busy","fault","up_i","dn_o"],
              "N":["red_we","red_addr","red_data","vm_we","vm_win0","vm_wdata0"],"E":["dn_i","up_o"],"S":["ck","rst_n"]}
        purpose="QW-SLICE7 Q.STA.SLICE.2: slice2 scalar face sc2 (parallel argmax compares, bounded native fanout, LA/LM-cut FP) of the hardened one-level slice"
    wit=f"results/arch/qw_slice6_1019/scred2_1020/kitbench/{kind}{cfg}_mut.log"
    return {"name":name,"top":top,"kind":"tile","sources":srcs+HDC,"params":{},"clock_port":"ck","reset_ports":["rst_n"],
      "outline":{"w":w,"h":h,"exact":True},"pins":pins,"layer_cap":"M5","recipe":4,"hold_budget":"die",
      "pin_regs":{"enable":False,"reason":"the RTL registers every input in one face register and launches every output from a face register (same in+1/out+1 as the old kit's flow wrapper); a flow wrapper would add a second, unpriced +1"},
      "reset_landing":{"enable":False,"reason":"the RTL lands rst_n in 2 registered stages (qfd_dv_s5_rst2) then the rc stage the constructor replicates into <=32-load relays"},
      "keep_pin_regs":True,"inhold":False,"outhold":False,"io_flop_at_pins":{"cols":4,"allow_none":True},
      "route":{"pd":0.5,"threads":16,"peak_ram_gb":64,"hold_margin_ns":0.03,"io_hold_margin_ns":0.03,"pin_balance":{"group_max":1,"h":"M4","v":"M5"},"macro_halo_um":5.4},
      "structural_change":f"QW-SLICE7-LEAVES successor of qfd_dv_s5_{kind}/{kind}b after their mapped census FAIL (reset 740-3064 / data 504-742 loads, depth 775-1030 ps): qfd_dv_s5_{kind}2 RTL #(LA {LA}, LM {LM}) bounded by tools/qwen_dv/bound_math_netlist.py --load-cap 8 --transparent-inverters --retain-mux --shared-helpers --retain-keep"+(" --reuse-copies; two-stage sc_cfg landing, reset relays rc..rf, landed argmax edge candidates (QW-S5-SCRED)" if kind=="sc" else ""),
      "safe_design_checklist":"see physical/ref_tile/%s/README.md (numbers from results/arch/qw_slice6_1019/scred2_1020)"%name,
      "children":[],"inter":[],"macros":[],
      "job":{"owner":"Claude:QW-S5-SCRED","branch":"claude/qw-s5-scred-1021","tag":name.replace('qfd_dv_s5_','')+'k',
        "purpose":purpose+"; price "+PRICE[kind],"extra_paths":["rtl","results/arch/qw_slice6_1019/scred2_1020","tools/qwen_dv/bound_math_netlist.py"],
        "benches":[
          {"name":f"{kind}2_kit_eq","cmd":f"bash rtl/test/qwen_dv/s5_scred2/run_kit.sh {{RUN}}/bench/eq {kind} eq {cfg}","expect":"pass","pass_regex":("RED2_EQ PASS results=3000" if kind=='red' else "SC2_EQ PASS"),"threads":16,"peak_ram_gb":64,"needs":["verilator"]},
          {"name":f"{kind}2_kit_mut","cmd":f"bash rtl/test/qwen_dv/s5_scred2/run_kit.sh {{RUN}}/bench/mut {kind} mut {cfg}","expect":"fail","fail_regex":("RED2_EQ FAIL errors=" if kind=='red' else "SC2_EQ FAIL errors="),"threads":16,"peak_ram_gb":96,"needs":["verilator"],"fail_witness":wit}],
        "views_to":f"physical/ref_tile/{name}/views","record_to":f"results/rtl/ref_tile/{name}"}}
out=Path('tools/ref_tile/specs_qw_slice7');out.mkdir(parents=True,exist_ok=True)
for kind,area in [(k,a) for k,a in (("red",ra),("sc",sa)) if a>0]:
    cn=f"qfd_dv_s5_{kind}2_k{cfg}"
    for suf,util,asp in (('',0.55,1.0),('b',0.42,1.5)):
        w,h=side(area,util,asp); n=f"qfd_dv_s5_{kind}2{suf}"
        (out/f"{n}.json").write_text(json.dumps(spec(kind,n,w,h,cn),indent=1)+"\n"); print(n,w,h,round(area/(w*h),3))
