
grab: grab.cpp write_jpg.cpp compute_backtrace_gdb.cpp
	g++ -g -Wall --std=c++20 -I /usr/include/libcamera -DBOOST_STACKTRACE_USE_BACKTRACE \
		$^ -o grab \
		-lcamera -lcamera-base -lboost_program_options -lexif -ljpeg -lfmt
