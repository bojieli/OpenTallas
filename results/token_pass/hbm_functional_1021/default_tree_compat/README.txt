Pure compiler proof; no hardware build or simulation.

python3 tools/hbm_layer_vehicle/verify_default_tree_compat.py --fixtures /home/ubuntu/scratch/tok-func-hbm/rsrc --qop /home/ubuntu/scratch/tok-func-hbm/qop --boundary /home/ubuntu/scratch/tok-func-hbm/r15phaseall/bundle/slice/boundary.json --out /home/ubuntu/scratch/tok-func-hbm/default_compat_verified

Baseline8e14d6cd includes true prestate snapshot correction. Both compiler revisions consume the same frozen priced/programme fixtures and boundary. Candidate default mode does not enable the new SU/HC implementations. Every drive/preload/check event and cycle compares numerically equal, all6533 quarter programme words equal, and new upper48 tree bits are zero. Expanded ABI representation introduces no numerical default command change. Explicit connected mode remains separate source-only until coupled execution.
