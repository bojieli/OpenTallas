# PATH-S81/HCORE swr: count ot_hdc_f12_swsel instances in the synthesised netlist (kept hierarchy).  31 f12 LAT-4 adders x 4
# replicas = 124 expected; exit 1 if fewer than 124 (replicas merged / hierarchy flattened = the fix is gone).
import re, sys
t = open(sys.argv[1]).read()
n = len(re.findall(r'^\s*\\?ot_hdc_f12_swsel\S*\s+\S+\s*\(', t, re.M))
print(f"PATH_S81_HCORE swsel instances {n} (need >= 124)")
sys.exit(0 if n >= 124 else 1)
