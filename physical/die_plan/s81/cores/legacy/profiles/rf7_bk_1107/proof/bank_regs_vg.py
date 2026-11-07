import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text()
old = """  } elseif {[regexp {^u_q\\.(u_s\\.u_h[cf]\\.gq|s_b[cf])\\[} $nm]} {"""
assert t.count(old) == 1
new = """  } elseif {[regexp {^u_q\\.u_s\\.u_h[cf]\\.g_bank\\[[0-9]+\\]\\.s_(dg|en|v|rn|clr|g)(\\[|\\$)} $nm]} {
    # S81-BKSEL-RF7 vG (OT_BKQ_BSTG): the last input stage sits FIRM at the bank pin(s) it drives (one hop, on the macro tap).
    set pins [br_fwd_macro [br_qnet $i]]
    if {![llength $pins]} { dict incr br_n stg_none; continue }
    set sx 0; set sy 0
    foreach p $pins { lassign [br_itxy $p] px py; incr sx $px; incr sy $py }
    br_put $i [expr {$sx/[llength $pins]}] [expr {$sy/[llength $pins]}] stg
""" + old
t = t.replace(old, new)
old2 = "proc br_center {i} {"
assert t.count(old2) == 1
t = t.replace(old2, """# macro input pins reached forward through BUF/INV only
proc br_fwd_macro {net} {
  set todo [list $net]; set seen {}; set out {}
  while {[llength $todo]} {
    set n [lindex $todo 0]; set todo [lrange $todo 1 end]
    if {$n eq "NULL" || $n eq "" || [dict exists $seen $n]} continue
    dict set seen $n 1
    foreach it [$n getITerms] {
      if {[[$it getMTerm] getIoType] ne "INPUT"} continue
      set i [$it getInst]
      if {[[$i getMaster] isBlock]} { lappend out $it; continue }
      set m [[$i getMaster] getName]
      if {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "HB*" $m]} {
        foreach o [$i getITerms] { if {[[$o getMTerm] getIoType] eq "OUTPUT"} { lappend todo [$o getNet] } }
      }
    }
  }
  return $out
}
""" + old2)
old3 = "set br_n [dict create gq 0"
assert t.count(old3) == 1
t = t.replace(old3, "set br_n [dict create stg 0 stg_none 0 gq 0")
p.write_text(t)
print("bank_regs patched")
