# S81 fold gather 2-beat transport

Implements the DEC12 1068-bit attnh lane contract for a 2133-bit gather word. Beat 0 carries the low 1067 bits including valid; beat 1 carries the remaining 1066 bits and a zero pad. The transport detects reordered/missing beats and input overrun with sticky faults. Datapath flops carry no reset. F2B defaults off; the new face masters select it explicitly.

The smallest exact scoreboard compares every transmitted beat and every reconstructed word at its fixed cycle, across 3 x 3000 random words. The swapped-beat control fails all three seeds. The production 16-slice exchange passes all three seeds (600 root words, 9600 taps and 6600 directed-fold words each), with bit-exact golden tree order; swapped beats, one-cycle input rate, and wrong leaf skew fail. SVCIK and SELCHAIN gates pass with all tested mutants caught. Four face-register variants pass. Existing lint continues on epyc1; 14 completed variants had zero errors at collection. No P&R or sign-off was run.

One fold hop adds one cycle. The composed exchange root moves from 51 to 54 cycles; maximum leaf launch offset moves from 15 to 17. Generated role/slot ROMs price those changes. The compiler must space gather words at least two cycles apart on each fold direction. TOK-DS duty confirmation and binding adoption remain open.

Logs are inherited completed jobs, collected without rerunning them. `summary.json` names the source base and run directory. The original jobs and source worktree were left untouched.

A bounded Yosys lockstep miter also proves the smallest 5-bit transport against an identity pipeline for all legal input data and valid patterns over 14 cycles, with a swapped-beat mutant rejected. It ran through ot-run on intel2; formal sources and SAT logs are in `formal/`. This is mechanism exactness evidence.
