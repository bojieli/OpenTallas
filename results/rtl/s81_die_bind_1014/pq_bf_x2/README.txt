Die-approved full-rate BF x lane, exact gate vs bare production ot_s81_pq_core_native.
Source command: tools/s81/pq_die_n_bench.py --bf-x2 --jobs 4 --work <positive>
Negative control: same command --mut X2; swaps extension bit0/bit1; observed FAIL test1 cycle75.
Positive: 5536 cycle comparisons,2304 BF beats (2261 back-to-back),2304 q beats,16 go,16 cfg,2304 x reads.
Every xw/xe565 and x2w/x2e537 bit compared against independent native-broadcast encoding one cycle earlier.
Map: physical/s81_die_pins/v20/bf_x2_lane.json (recovered S-DIE map1da2c4a9a).
Compile DSFD_PQ_BF_X2 for the PQ die master when the die carries x2w/e and x2ws/es.
Native phase start has go+go_bf concurrently; legacy cc preserved on this control beat.
This verifies encoder RTL and full-rate source behavior. It does not qualify the still-unbuilt die
transport: separate FIFOs/stations must preserve BF beat alignment at the front, and native pin,
reset, clock and TT/FF closure checks remain required.
