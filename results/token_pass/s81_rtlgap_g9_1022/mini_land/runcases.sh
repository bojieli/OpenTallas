while read c n K F N G R0; do
  if grep -qx $n long.txt; then D=8; KW=6; else D=4; KW=3; fi
  for RL in 0 2; do
   GD=$((G)); RD=$((R0));  # netlist release edges; tb shifts both by the same root offset
   iverilog -g2012 -o c_$$.vvp -s mtb -Pmtb.GD=$GD -Pmtb.RD=$RD -Pmtb.N=$N -Pmtb.F=$F -Pmtb.K=$K -Pmtb.RL=$RL -Pmtb.D=$D -Pmtb.KW=$KW tb_rl.sv flight.sv ot_s81_land.sv dsfd_rly_masters_dvh.sv ot_s81_rly.sv cells_used.v
   r=$(vvp -n c_$$.vvp | grep -o "fault_cycles=[0-9]*" | cut -d= -f2); eval "f$RL=$r"
  done
  echo "$c $n K=$K F=$F N=$N R0-G=$((R0-G)) RL0_fault=$f0 RL2_fault=$f2"
done < cases.txt
