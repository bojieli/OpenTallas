set -eu
# on intel2
W=/srv/opentallas-scratch2/claude/hbm-hard-9
R=$W/repo
POR=$R/physical/die_plan/hbm/plan_of_record
T=$W/gqi_ev; rm -rf $T; mkdir -p $T/cores
cp $POR/d44v_epm/die_plan.json.gz $T/
cp $POR/d44v/cores/ot_hgi_coll_gqi_issue__172.8x233.28__d44v_split.json.gz $T/cores/
K=intel1:/srv/opentallas-scratch2/claude/hbm-hard-6/eco/gqi_vLF2_np1/i1
mkdir -p $W/gqi_input
rsync -a -e 'ssh -o ControlPath=none' $K/face_shell.json $K/rtl/ot_hgi_coll_gqi_issue__fshell.sv $K/pins.json $W/gqi_input/
OLD=cores/ot_hgi_coll_gqi_issue__172.8x233.28__d44v_split.json
NEW=cores/ot_hgi_coll_gqi_issue__172.8x233.28__d44v_gqi8.json
cat > $W/gqi_input/note.json <<NOTE
{"counted_record": "intel1:/srv/opentallas-scratch2/claude/hbm-hard-6/resign/gqi_vLF2_np1_fc", "record_kind": "resign flow-20261108-fc-hbm SIGNED LOCAL_PASS_NEEDS_PARENT", "dead_input_proof": "HBM-HARD-7 18:31: gate-level Yosys on ebab948a68 issue.sv (sha256 964fdabc775ecd66): only aq0_e[9:8], aq1_e[9:8] input bits dead on the module; RTL line 263 truncates aq_e_q to 8 bits. [CHECKED epyc6 hbm-hard-7/gqi_dead/p2.ys, out2.json]", "kit_rtl_shell": "shell feeds .aq0_e({2'd0, aq0_e__fq}) and .aq1_e({2'd0, aq1_e__fq})", "parent_effect": "the four q_hub_ne/nw u_hcollgi_Q__q{0,1}__i instances: the 4 bits per core are unread; a parent net driving them has no load at these pins"}
NOTE
python3 -I $R/tools/die_plan/drop_face_shell_pins.py $T --module ot_hgi_coll_gqi_issue --old-table $OLD --new-table $NEW --face-shell $W/gqi_input/face_shell.json --shell-rtl $W/gqi_input/ot_hgi_coll_gqi_issue__fshell.sv --kit-pins $W/gqi_input/pins.json --event gqi8_1108 --by HBM-HARD-9 --ruling "scope HBM-HARD-9 item 4, plan event after HBM-HARD-7 spec 18:31 and HBM-HARD-8 22:21; DIE-HBM-94 CONFIRM before landing" --note-file $W/gqi_input/note.json
ls -la $T $T/cores
