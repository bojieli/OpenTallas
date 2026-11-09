K=/srv/opentallas-scratch2/claude/dh88/lep_dt/gen/hd_lep0N
O=/srv/opentallas-scratch2/claude/dh88/lep_probe_dt; mkdir -p $O
sed -e '/^set w \[sta::time_sta_ui/,$d' -e 's#\[file dirname \[file normalize \[info script\]\]\]#/work#g' $K/hold_gate.tcl > $O/p.tcl
cat >> $O/p.tcl <<'P'
puts "HG_WNS [sta::worst_slack_cmd min] N [sta::endpoint_violation_count min]"
report_checks -path_delay min -format full_clock_expanded -digits 1
report_clock_skew -hold
set f [open /out/hold_eps.txt w]
foreach pe [find_timing_paths -path_delay min -group_path_count 45000 -unique_paths_to_endpoint -slack_max 0] {
  puts $f "[format %.1f [expr [get_property $pe slack]]] [get_full_name [get_property $pe startpoint]] [get_full_name [get_property $pe endpoint]]"
}
close $f
puts PROBE_DONE
P
grep -E '^(override )?export ' $K/config.mk | sed -E 's/^(override )?export //; s/ *= */=/' | grep -vE '^(ODB|SDC)=' > $O/env
cat >> $O/env <<X
ODB=/work/run/results/asap7/dp_hd_lep0N/base/4_1_cts.odb
SDC=/work/run/results/asap7/dp_hd_lep0N/base/4_cts.sdc
PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7
LAYER_PARASITICS_FILE=/work/setRC_rcx.tcl
X
cat > $O/run.sh <<'R'
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
export PLIBS="$(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_FF_nldm_* /work/macros/*_ff.lib | tr '\n' ' ')"
cd /out; openroad -no_splash -exit -threads 8 /out/p.tcl > /out/probe.log 2>&1
R
docker run -d --rm --name dh88-lep-probe-dt --memory 48g --cpus 8 --env-file $O/env -v $K:/work:ro -v $O:/out -w /out openroad/orfs:asap7lock bash /out/run.sh
sed -n 1,4p $O/env | cut -c1-80
