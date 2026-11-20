#!/bin/bash
# usage: run1.sh MODULE   -> /tmp/sfq-cland/res_MODULE.json ; single thread, nice, <8 GB
M=$1; E=/home/ubuntu/signed-export-1114/qwen_compute/$M; P=/home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7/lib/NLDM; W=/tmp/sfq-cland
python3 - $E $W/$M.spef <<'PY'
import re,sys
t=open(sys.argv[1]+"/6_final.spef").read()
i=t.index("*NAME_MAP"); j=t.index("\n*PORTS") if "\n*PORTS" in t else t.index("\n*D_NET")
nm=re.sub(r"^(\*\d+ )(\S+)$",lambda m:m.group(1)+m.group(2).replace("/","\\/").replace("\\\\/","\\/"),t[i:j],flags=re.M)
open(sys.argv[2],"w").write(t[:i]+nm+t[j:])
PY
for C in TT FF; do
cat > $W/s_$M_$C.tcl <<T
foreach f [glob $P/asap7sc7p5t_{SIMPLE,INVBUF,AO,OA}_RVT_${C}_nldm_2*.lib*] { if {[string match *250407* \$f]} continue; read_liberty \$f }
foreach f [glob $P/asap7sc7p5t_SEQ_RVT_${C}_nldm_2*.lib*] { read_liberty \$f }
read_verilog $E/6_final.v
link_design $M
read_sdc $E/6_final.sdc
read_spef $W/$M.spef
foreach c {clk fclk} {
 foreach p [all_registers -clock_pins -clock [get_clocks \$c]] {
  puts "PIN \$c [get_full_name \$p]"
  report_arrival \$p
 }
}
T
( ulimit -v 8000000; nice -n 19 sta -no_splash -threads 1 -exit $W/s_$M_$C.tcl 2>&1 | grep -E "^PIN|\((clk|fclk) \^\)|not found|Error" > $W/o_${M}_$C.txt )
done
python3 - $M <<'PY'
import re,sys,json,statistics as S
M=sys.argv[1];out={}
for C in ("TT","FF"):
    L=open(f"/tmp/sfq-cland/o_{M}_{C}.txt").read().splitlines(); rows=[];cur=None;nf=0
    for l in L:
        if "not found" in l or l.startswith("Error"): nf+=1; continue
        if l.startswith("PIN"): cur=l.split(); continue
        m=re.search(r"\((clk|fclk) \^\) r ([\d.]+):([\d.]+)",l)
        if m and cur: rows.append((cur[1],float(m.group(2)),float(m.group(3))))
    for c in ("clk","fclk"):
        r=[x for x in rows if x[0]==c]
        out[f"{C.lower()}_{c}"]=dict(n=len(r),mean_max=round(S.mean(x[2] for x in r),3) if r else None,mean_min=round(S.mean(x[1] for x in r),3) if r else None,not_found=nf)
so=json.load(open(f"/home/ubuntu/signed-export-1114/qwen_compute/{M}/signoff.json"))["corners"]
out["signoff_pinflops_mean"]={k:so[k]["insertion_pinflops"]["mean"] for k in ("tt","ff")}
out["signoff_pinflops_n"]=so["tt"]["insertion_pinflops"]["n"]
json.dump(out,open(f"/tmp/sfq-cland/res_{M}.json","w"),indent=1)
PY
