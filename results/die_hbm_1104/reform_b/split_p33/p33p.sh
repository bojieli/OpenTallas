set -e
A=/srv/opentallas-scratch2/claude/hbm-reform-b5; W=/srv/opentallas-scratch3/claude/hbm-reform-b3/wt; cd $W; export PYTHONDONTWRITEBYTECODE=1
C=ot_hfd_coll_q2n2_body_core; Q=results/die_hbm_1104/reform_b/split_p33; R=rtl/hbm_accel/cores_split/reform_1105b; G=$A/q2n/gen
mkdir -p $Q; cp $G/ot_q2nf_split.sv $G/ot_q2nf_rest.sv $R/; cp $G/comp/$C.__p33* $Q/ 2>/dev/null || cp $G/comp/${C}__p33* $Q/
cp $A/q2n/mk_spec.py $A/q2n/gen_q2n.py $A/q2n/gen_comp.py $A/q2n/ext.sh $A/q2n/wrap.sh $A/q2n/run_q2n.sh $A/q2n/run_core.sh $A/q2n/tb_q2n.sv $Q/ 2>&1 | head -3
bash results/die_hbm_1103/reform/split_p6/netlist2.sh $A/p33nl.json $C $Q/${C}__p33glue.sv $Q/${C}__p33comp.sv $R/ot_q2nf_split.sv $R/ot_q2nf_rest.sv 2>&1 | tail -3 | cut -c1-260
python3 -I results/die_hbm_1103/reform/split_p6/split_conn.py $A/p33nl.json $C $Q/$C.conn.json 2>&1 | tail -2 | cut -c1-300
rm -rf $A/plan33; cp -a $A/plan26r $A/plan33
python3 -I $Q/mk_spec.py $A/plan33 $Q/split_p33.json
python3 -I results/die_hbm_1103/reform/mk_split.py $A/plan33 $Q/split_p33.json $Q 2>&1 | tail -4 | cut -c1-500
python3 -I $Q/mk_p33.py $A/plan33 $Q/q2n_seam.json
