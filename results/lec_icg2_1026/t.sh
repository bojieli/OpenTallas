cd $1
for fe in slang verilog; do
  if [ $fe = slang ]; then R="read_slang --compat=vcs oob.sv"; else R="read_verilog -sv oob.sv"; fi
  yosys -q -p "$R; hierarchy -top oob; proc; opt_expr -keepdc; opt_clean; memory -nomap; memory_map; opt_expr -keepdc; opt_clean; flatten; techmap; opt_clean; write_verilog -noattr $fe.v" 2>&1 | tail -3
  echo "== $fe"; grep -E "assign|always|<=" $fe.v | head -30
done
