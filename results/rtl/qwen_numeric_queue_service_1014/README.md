The frozen b66fe0230 mailbox-based queue passes six 128-word component scenes.
Both typed D2 and D8 produce 128 words over 381 intervals: one word per three
base edges. The one-unacknowledged output publication is the bottleneck; FIFO
depth does not remove it. D8 untyped produces one word per base edge, while D2
untyped needs 190 edges for 127 intervals because its pending-post reservation
introduces bubbles. Full sink stalls reach actual capacities two and eight and
recover. Earliest produced-word to real pop is two base edges.

Yosys 0.68 exact logical census is 1211 Q bits at D2 and 4829 at D8. Scripts
expect the frozen queue and fixture staged under their basename in the job
working directory. Raw logs and tool commands are retained. Simulation unit
oth-ubuntu-2099637-1791975656 and census unit oth-ubuntu-2127275-1791976093 both
exit zero. This is a component service measurement, with no physical clock
phase, native layer cost, area, CTS, or source architecture adoption claim.
