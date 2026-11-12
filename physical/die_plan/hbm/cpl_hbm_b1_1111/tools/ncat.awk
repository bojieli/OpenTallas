# per-category cell counts of a flat type-top synth netlist: DFF and INV by instance prefix class
/^ *(input|output|wire|module|endmodule|assign)/ {next}
/^ *[A-Za-z_][A-Za-z0-9_]* +[^ ]+ *\(/ {
  m=$1; n=$2; gsub(/\\/,"",n)
  cls="other"
  if (n ~ /u_ist_/) cls="ist"; else if (n ~ /u_ft_/) cls="ft"; else if (n ~ /u_bin_|u_bout_/) cls="bio"; else if (n ~ /u_rrl_|rst/) cls="rst"
  if (m ~ /^DFF/) k="DFF"; else if (m ~ /^INV/) k="INV"; else if (m ~ /^ot_/) k="MACRO"; else k="LOGIC"
  c[cls" "k]++; t++
}
END { for (x in c) print x, c[x]; print "total", t }
