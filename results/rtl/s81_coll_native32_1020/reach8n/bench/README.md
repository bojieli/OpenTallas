DRIVE-S81-NTF 10-20: tb_coll_reach7 with OT_COLL_REACH8N=1 (DUT pair = dsfd_coll_lane_{w,e}_safe8_ntf, param-free tf-less
REACH=2 MU-die tops; reference pair safe4), Verilator 5.050, fleet ot-run (ot-epyc5), source = branch claude/s81-ntf-1020.
m0 PASS received=37274/36912 errors=0, mean lo->li latency 117.12 (ref4 122.51; identical to the safe8 reach8 m0).
m5/m6/m7/m8 FAIL as required (m8: 'COLL FIFO group state differs group0').
cmd: OT_COLL_NATIVE32=1 OT_COLL_NATIVE32_OFF=1 OT_COLL_REACH8N=1 bash tools/xdie_s81/coll_reach7.sh <out> <m>
