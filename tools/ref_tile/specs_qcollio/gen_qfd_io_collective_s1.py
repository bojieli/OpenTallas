# Generator of tools/ref_tile/specs_qcollio/qfd_io_collective_s1.json (qwen-coll-io r5 2026-10-14): python3 THIS OUT.json
import json,sys
SL=181.44
W,H=1105.92,950.4
xA,xS,xC,xD=129.6,354.24,561.6,797.04
ys=[43.2,259.2,475.2,691.2]
ch=[]
for k,y in enumerate(ys):
    ch.append({"view":"physical/ref_tile/coll_fold_slice_rt/views/ot_coll_fold_slice","count":1,"inst":f"*g_xf?{k}?*u_fs","at":[xA,y],"orient":"R0"})
for k,y in enumerate(ys):
    ch.append({"view":"physical/ref_tile/coll_fold_slice_rt/views/ot_coll_fold_slice","count":1,"inst":f"*g_pf?{k}?*u_fs","at":[xC,y],"orient":"MY"})
mac=[]
for k,y in enumerate([86.4,259.2,432.0,604.8,777.6]):
    mac.append({"view":"physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2","count":1,"inst":f"*g_sring?{k}?*u_m","at":[xS,y],"orient":"R0"})
for nm,k,y in (("u_pring",0,86.4),("u_pring",1,259.2),("u_rring",0,604.8),("u_rring",1,777.6)):
    mac.append({"view":"physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1","count":1,"inst":f"*{nm}*g_b?{k}?*u_m","at":[xD,y],"orient":"R0"})
xclk=[f"clk_xfold{k}" for k in range(4)]; pclk=[f"clk_pfold{k}" for k in range(4)]
Eit=[("sr0_valid",1),("sr0_rec",80),("sx0_valid",1),("sx0_rec",80),("sx0_peer_slot",1),
     ("dr_valid",1),("dr_rec",76),("ur_valid",1),("ur_rec",76),("ur_peer_slot",1),
     ("dp_valid",1),("dp_rec",80),("up_valid",1),("up_rec",80),("up_slot",1)]
Wit=[("sr2_valid",1),("sr2_rec",80),("sx2_valid",1),("sx2_rec",80),("sx2_peer_slot",1),
     ("sr1_valid",1),("sr1_rec",80),("sx1_valid",1),("sx1_rec",80),("sx1_peer_slot",1)]
pins={"N":["clk","rst_n","pkg_s","die_ps","cmd_v","cmd_mode","cmd_words","cmd_tag","cmd_free","in_valid","in_data","in_last","in_mode","in_tag",
           "out_valid","out_data","out_last","out_rank","out_err","fault","fault_code"],
      "E":[n for n,_ in Eit]+pclk,"W":[n for n,_ in Wit]+xclk}
def seq(start,items,gap=0.4):
    out={};x=start
    for n,w in items: out[n]=[round(x,2),round(x+w,2)];x+=w+gap
    return out
pr={}
pr.update(seq(360.0,[("clk",2),("rst_n",2),("pkg_s",2),("die_ps",2),("fault",2),("fault_code",4)]))
pr.update(seq(580.0,[("out_valid",1),("out_data",120),("out_last",1),("out_rank",2),("out_err",1)]))
pr.update(seq(805.0,[("cmd_v",1),("cmd_mode",1),("cmd_words",4),("cmd_tag",8),("cmd_free",1),
                     ("in_valid",1),("in_data",120),("in_last",1),("in_mode",1),("in_tag",8)]))
for k,y in enumerate(ys):
    pr[f"clk_pfold{k}"]=[round(y+SL+2,2),round(y+SL+4,2)]
    pr[f"clk_xfold{k}"]=[round(y+SL+2,2),round(y+SL+4,2)]
def place(items,start):
    blocked=[(y+SL+1,y+SL+5) for y in ys]; out={};x=start
    for n,w in items:
        while True:
            hit=[b for b in blocked if not (x+w<b[0] or x>b[1])]
            if not hit: break
            x=max(b[1] for b in hit)+0.4
        out[n]=[round(x,2),round(x+w,2)];x+=w+3.0
    assert x<H-20,(x,)
    return out
pr.update(place(Eit,start=60.0)); pr.update(place(Wit,start=150.0))
spec={"name":"qfd_io_collective_s1","top":"qfd_io_collective_static","kind":"cluster",
 "sources":["rtl/physical/ot_qfd_io_collective_static.sv","rtl/rom/ot_coll_tp8_static.sv","rtl/rom/ot_coll_rst_leaf.sv",
            "rtl/rom/ot_coll_fold_slice.sv","rtl/hdc/ot_hdc_fp32_add_lat.sv","rtl/hdc/ot_hdc_prefix.sv","rtl/hdc/ot_hdc_fastfp.sv",
            "physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1_bb.v",
            "physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2_bb.v"],
 "params":{},"clock_port":"clk","reset_ports":["rst_n"],
 "clock":"hybrid_entries","clock_ports":["clk"]+pclk+xclk,"clock_cts_roots":["clk"],
 "pins":pins,"pin_ranges":pr,"pg_layer":"M7","refglob":"*",
 "route":{"pd":0.5,"threads":16,"peak_ram_gb":96,"pin_balance":{"group_max":1}},
 "outline":{"w":W,"h":H},"inter":[],"children":ch,"macros":mac,
 "why_floorplan":("static TP8 collective (OWNER 0ah, no queues/credits): W->E columns = W SerDes faces (ports 1/2) | 4 cross-fold "
   "slices R0 (src W: sr1/sr2 from the W face, sr0 + S ring from the E) | S ring 5 x 512x128 | 4 pre-fold slices MY (src E: "
   "pairing of dp + P ring; sum W: S ring + sx copies) | P ring 2 + R ring 2 x 32x546 | E faces (SerDes port 0, UCIe P/R). "
   "N: in/cmd over the rings, out over the pre-fold column, straps/reset/fault over the S ring. Fold-slice clock entries at "
   "each slice's clock-pin row (W cross, E pre); parent glue (~8.2k flops) on its own CTS root clk. Cut: tools/qwen_coll_static_cut.py."),
 "slot_change_request":("compute-die contract v1.2 slot (el1014-qwen-split-compute.log 22:10): S IO band 3,453.4 x 1,563.8 R0 "
   "@ x 12,468 y 22 -> this cluster 1,105.92 x 950.4 (1.05 mm2) inside it; band order serdes_2 | serdes_1 | collective | "
   "serdes | ucie: faces W = SerDes 1/2, E = SerDes 0 + UCIe, N = core (seq_su cmd / in, out)."),
 "job":{"owner":"Claude:qwen-coll-io-1014","branch":"claude/qwen-coll-io-1014","tag":"s1",
   "purpose":("Qwen TP8 compute-die STATIC collective cluster qfd_io_collective_static (OWNER 0ah: compiler command per message, "
     "fixed-offset rings, no credits/ready/queues; LU 37 / LS 376 = composed on the real static link RTL + R_max 7). "
     "8 CLOSED ot_coll_fold_slice children (coll_fold_slice_rt) on own clock entries, 9 SRAM macros, glue on clk."),
   "benches":[
     {"name":"static_exact_qfd","cmd":"python3 tools/qwen_coll_tp8_static_bench.py --qfd --production --latu 37 --lats 376 --out {RUN}/bench/static_exact_qfd",
      "expect":"pass","pass_regex":"^COLL_TP8S PASS cases=4","threads":16,"peak_ram_gb":48,"needs":["verilator"]},
     {"name":"static_mut_rank","cmd":"python3 tools/qwen_coll_tp8_static_bench.py --qfd --production --latu 37 --lats 376 --mutant-define OT_TP8S_MUT_RANK --out {RUN}/bench/static_mut_rank",
      "expect":"fail","fail_regex":"^COLL_TP8S FAIL mutant=OT_TP8S_MUT_RANK","threads":16,"peak_ram_gb":48,"needs":["verilator"]}],
   "extra_paths":["physical/asap7_memory_macros","rtl/test","rtl/hdc","tools/hdc_golden.py","tools/qwen_coll_tp8_bench.py","tools/qwen_coll_tp8_static_bench.py"],
   "views_to":"physical/ref_tile/qfd_io_collective_s1/views","record_to":"results/rtl/ref_tile/qfd_io_collective_s1"}}
json.dump(spec,open(sys.argv[1],'w'),indent=1)
print("ok")
