write_db /work/capacity_snapshot.odb
set ::env(CUT_ODB) /work/capacity_snapshot.odb
set ::env(CUT_CAPACITY) /work/current_cut_capacity.json
puts [exec openroad -threads 1 -exit -python /report/capacity.py 2>@1]
