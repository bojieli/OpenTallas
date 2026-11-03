Packet4 corrects only the finite bench's interpretation of raw PART1 output.
Packet3's actual terminal baseline failure reported firstvalidc3174c00 against
finalK7goldc3312600. That rawK0 value matched an independent genuine-code/H
calculation. Native t_vout carries every K prefix; actual selected STN KC8
filters the first seven K blocks.

The existing outputs counter now counts raw ordinals0..1599. Only raw%64>=56
compares golden vector(raw/64)*8+raw%8, retaining the same3200 finalK7 golden
values. Per-chunk raw counts are512/512/512/64; total1600raw vectors,
200selected vectors/3200checked values. No new public arrays or state was added.
Native RTL, masks, gold,833ps clock,XOFF3 and8000edge watchdog are unchanged.
The firstK0 value is printed diagnostically; the same-ELF wrong-weight control
still requires the independently predicted firstfinalK7 mismatchc32f0600.

Portable packet /home/ubuntu/coord/tmp/codex-native-head-leaf-packet4
manifest9ad290adae8524503d8d8d476a31cfdbbdae61e7f1448864dbda0e471614b973.
No build or dispatch performed. Parent reviews one normal4GB/1thread/disk2
successor; prior actual build peak2452728KB and7m40.49s support this admission.

Cached runner run_gate_cached.sh TERMINAL_PACKET3_DIR guards exact old packet3
manifest, all native source/ROM/gold bytes, old ELF and known terminal failure.
It copies the old ELF/logs into a new preservation directory, reflinks or copies
old objects into NEW obj (never hardlinks or modifies old files), regenerates
with explicitVL5.050 --cc --exe --main, then runs make-j1. Generated C++/header
identity and changed-file lists are recorded; reuse is measured, not presumed.
The original packet3, objects, ELF and immutable failure remain unchanged.
