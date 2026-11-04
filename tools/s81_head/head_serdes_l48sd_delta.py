#!/usr/bin/env python3
"""DIE-HEAD-59 11-04 HEAD plan event l48sd (COORD 00:4x): hd_serdes = S81 pad-clock form + signed KP4 view as a hard core.
usage: delta_l48sd.py BASE/source_plan.json RF_DIR/source_plan.json"""
import json,sys
sys.path.insert(0,sys.argv[3]+"/tools/die_plan")
p=json.load(open(sys.argv[1])); t=p["partition_types"]["hd_serdes"]; c=t["clock"]
EV=("ot_pdie_serdes.sv: pma_rck -> clk only through ot_s81_rate_match (8-deep gray-pointer FIFO, 2-flop gray pointer synchronisers both ways; "
    "KP4 SRAM 1r1w2c wclk=pma_rck rclk=clk is its storage), per-domain reset synchronisers (rs_r), 2-flop status synchronisers (lk_s/uf_s); "
    "300 ppm two-die bench tb_pdie_ucie_col. Same RTL as S81 serdes__t3 (COORD 10-31 ruling 3, COORD 11-04 00:4x)")
per=float(p["die"]["period_ps"]); lay="M7"
import schema as S, landing_contract as LC
P=S.Plan(json.load(open(sys.argv[1])),sys.argv[1])
XYR=[round(v,4) for v in LC.on_track(P,lay,1106.04,148.32)]; XYT=[round(v,4) for v in LC.on_track(P,lay,1114.68,148.32)]
# channel above the KP4 core (top 146.88), below the VDDPHY domain (150): clear of every macro, on the M7 track
c["pad_clock"]={"pins":[
 {"name":"pma_rck","dir":"in","cdc":"synchronized","cdc_evidence":EV,"period_ps":per,
  "source":"far-die PMA TX clock as recovered by the rxm CDR (ot_pdie_serdes.sv pma_rck), plesiochronous to the die clock at the die period",
  "layer":lay,"xy_um":XYR},
 {"name":"pma_tck","dir":"out","period_ps":per,"source":"ot_pdie_serdes.sv: assign pma_tck = clk","source_clock_port":"clk","layer":lay,"xy_um":XYT}]}
k=[h for h in t["hard_cores"] if h["module"]=="ot_s81_kp4_dchn"]; assert len(k)==1 and "lef" not in k[0]; k=k[0]
R="results/head_core_clockfreeze_release/kp4_e13a_corner/ot_s81_kp4_dchn"
k["lef"]=R+".lef"; k["lib"]=R+"_tt.lib"
k["note"]="SIGNED view: SIGNOFF-SPRINT-19 kp4_e13a_n (TT +2.48, FF +20.08, LEC EQUIVALENT 4217/4217, flow-20261101-n-head); 945 pins = core_pins/kp4_276x138_pins.json exact; recovered pma_rck clock domain, never parent clk"
t["cells"]=232594
t["note"]=t["note"].replace("PMA period and clock-pad adoption OWNER held.","PMA period 833 + pma_rck/pma_tck pad clocks: COORD 11-04 00:4x (l48sd); signed KP4 hard core.")
json.dump(p,open(sys.argv[2],"w"),indent=1); open(sys.argv[2],"a").write("\n")
