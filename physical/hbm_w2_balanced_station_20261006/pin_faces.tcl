# Reused ODB carries IO constraints. Apply this run's actual ABI faces here,
# after loading its real checkpoint, without replaying floorplanning.
clear_io_pin_constraints
source /work/io_constraints.tcl
puts "ACTUAL_STATION_PIN_FACES_REBOUND"
