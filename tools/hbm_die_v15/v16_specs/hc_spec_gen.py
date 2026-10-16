import json,sys
Q=['SW','SE','NW','NE']
SRC_CORE='rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_q_static.sv'
SRC_PAIR='rtl/hbm_accel/generic/peers/ot_hgi_sfu_lg_pair_leaf.sv'
SRC_TGT='rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv'
BT='rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_q_static.sv header (pair k <-> banks 2k,2k+1: rq[34k+:34] wq[562k+:562] rr[514k+:514] w_done[2k+:2]); ot_hgi_sfu_lg_pair_leaf.sv; tap ot_hbm_vm_lg_static_split_term #(18,15); bench rtl/test/tb_hbm_hc_q_static.sv'
inst=[];edges=[];clocks=[];gaps=[]
def E(s,d,bits,basis): edges.append({"src":s,"dst":d,"bits":bits,"clock":"stream","basis":basis})
for qi,q in enumerate(Q):
    tid=108+qi
    inst.append({"name":f"hc_tgt_{q}","master":"ot_static_program_target","source":SRC_TGT,
      "params":{"TARGET":f"8'd{tid}","PCW":10},"slot":None,"owner":"HC owner (H-NETLIST hc)",
      "note":f"F20 programme target {tid} of the static HC quadrant client hc_{q} (HC target range 108..111 = SW,SE,NW,NE); host_cp_ingress TARGET_MASK must admit {tid}"})
    inst.append({"name":f"hc_{q}","master":"ot_hbm_hc_q_static","source":SRC_CORE,"params":{"MUT":0},
      "slot":None,"owner":"HC owner (H-NETLIST hc)",
      "note":"static HC quadrant LG client: residual reader + gathered-mix reader + result store (codex/hc-static-engine-1014 leaves) issued by a programme SRAM; pin-registered; fixed latency residual capture issue+23, gather phase 23, write-done +19 (bench tb_hbm_hc_q_static PASS + 4 mutants). No die slot yet: plan puts the HC core at port group 0 (compact660_v5 links hc_<q>k>hc_<q>0 HC_CORE)."})
    for k in range(4):
        inst.append({"name":f"hc_{q}{k}","master":"ot_hgi_sfu_lg_pair_leaf","source":SRC_PAIR,"params":{},
          "slot":f"hc_{q}{k}","owner":"HC owner (H-NETLIST hc)",
          "note":f"HC bank-pair LG boundary leaf for banks {2*k},{2*k+1} of lg_{q}_2 (generic one-edge register pair leaf reused from SFU; engine_lg_port_group_rule)"})
        E([f"hc_{q}","lg_rq",34*k,34*k+34],[f"hc_{q}{k}","c_rq"],34,BT)
        E([f"hc_{q}","lg_wq",562*k,562*k+562],[f"hc_{q}{k}","c_wq"],562,BT)
        E([f"hc_{q}{k}","c_rr"],[f"hc_{q}","lg_rr",514*k,514*k+514],514,BT)
        E([f"hc_{q}{k}","c_w_done"],[f"hc_{q}","lg_w_done",2*k,2*k+2],2,BT)
        E([f"hc_{q}{k}","lg_rq"],[f"lg_{q}_2","local_rq",34*k,34*k+34],34,BT)
        E([f"hc_{q}{k}","lg_wq"],[f"lg_{q}_2","local_wq",562*k,562*k+562],562,BT)
        E([f"lg_{q}_2","local_rr",514*k,514*k+514],[f"hc_{q}{k}","lg_rr"],514,BT)
        E([f"lg_{q}_2","local_w_done",2*k,2*k+2],[f"hc_{q}{k}","lg_w_done"],2,BT)
        clocks.append({"inst":f"hc_{q}{k}","port":"clk","domain":"stream","kind":"clock"})
        clocks.append({"inst":f"hc_{q}{k}","port":"rst_n","domain":"stream","kind":"reset"})
    TB='rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv (F20 broadcast consumer, as host_cp_ingress -> target 48); bench rtl/test/tb_hbm_hc_q_static.sv loads/launches hc via TARGET 108'
    for p,w in [("cfg_v",1),("cfg_target",8),("cfg_addr",12),("cfg_data",256),("desc_v",1),("desc_base",12),("desc_limit",13),("desc_loops",16),("launch_v",1)]:
        E(["host_cp_ingress",p],[f"hc_tgt_{q}",p],w,TB)
    E([f"hc_{q}","program_active"],[f"hc_tgt_{q}","program_active"],1,TB)
    for s,d,w in [("program_cfg_we","cfg_we",1),("program_cfg_addr","cfg_addr",10),("program_cfg_data","cfg_data",256),
                  ("program_start_v","start_v",1),("program_start_base","start_base",10),("program_start_limit","start_limit",11),("program_start_loops","start_loops",16)]:
        E([f"hc_tgt_{q}",s],[f"hc_{q}",d],w,TB)
    for i in (f"hc_tgt_{q}",f"hc_{q}"):
        clocks.append({"inst":i,"port":"clk","domain":"stream","kind":"clock"})
        clocks.append({"inst":i,"port":"rst_n","domain":"stream","kind":"reset"})
gaps.append({"id":"G-HC-ENG","owner":"HC owner (engine) / H-DIE",
  "missing_rtl":"the single static HC engine hc_eng (projection W32/K20480 + Sinkhorn tail, 64 weight + 16 residual SRAM, programme SRAM; codex/hc-static-engine-1014 a35449ada ot_hgi_hc_programmed_sys1_split_mtp_static + weight prefetch on codex/hc-weight-prefetch-1015) is not on main; it is the producer of the per-quadrant tail result (result_v, result_position[3], result[768] = 24 FP32) that hc_<q> stores to VM. Its residual input is hc_<q>.x_wave (8192 b every 4 edges) and gathered mixes, both open outputs here.",
  "affects":[[f"hc_{q}",p] for q in Q for p in ("result_v","result_position","result")],
  "note":"Binding needs (a) the engine merged to main, (b) a 4:1 quadrant select of x_wave/gathered mix at the engine (programme-phase owned) or a K-split per-quadrant projection (architecture question), (c) its 128 HBM prefetch K-ports shared with the SM service PCs (G-VM-HBM-PATH owner), (d) bases[768]/scales[96] loader. hc_<q> status outputs residual_done/gather_done/program_done/fault unconsumed (status join owner)."})
spec={"region":"hc","author":"Claude H-NETLIST sub-agent hc (2026-10-15)","basis_commit":sys.argv[1],
  "instances":inst,"retire_v15":[],"edges":edges,"drop_v15_edges":[],"clocks":clocks,"straps":[],"gaps":gaps,
  "notes":["Closes G-HC (lg_<q>_2 local_rq/local_wq, 8 ports / 9,536 bits): the far HC tap is driven by a static HC quadrant client hc_<q> (new master ot_hbm_hc_q_static x4) through 16 bank-pair pin-register leaves hc_<q><k> (existing ot_hgi_sfu_lg_pair_leaf). lg_<q>_2 local_rr/local_w_done are now consumed. local_read/local_write stay driven by calendar_<q>; the compiler programmes calendar_<q> and hc_<q> on the same edges (the tap faults on any disagreement).",
   "Programme: hc_<q> owns a 1024x256 programme SRAM (ot_vms_calendar_static W79), loaded and launched by hc_tgt_<q> = ot_static_program_target TARGET 108..111 from host_cp_ingress (F20). TARGET_MASK of host_cp_ingress must admit 108..111 (cp owner).",
   "Fixed added latency vs the codex direct-tap engine: +1 output pin, +1 pair leaf, +1 pair leaf return, +1 input pin => residual capture 23 (was 19), gathered response phase 23 (was 19), write-done 19 edges after the store output edge."]}
json.dump(spec,open(sys.argv[2],'w'),indent=1)
print(len(inst),len(edges),sum(e['bits'] for e in edges))
