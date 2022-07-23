grab: grab.cpp
#	g++ --std=c++17 -I /usr/include/libcamera grab.cpp -o grab -Lcamera_app -Lcamera -Lcamera-base
	g++ -g -Wall --std=c++20 -I /usr/include/libcamera write_jpg.cpp grab.cpp -o grab /usr/lib/arm-linux-gnueabihf/libcamera.so /usr/lib/arm-linux-gnueabihf/libcamera-base.so /usr/lib/arm-linux-gnueabihf/libcamera_app.so -lexif -ljpeg -lfmt
