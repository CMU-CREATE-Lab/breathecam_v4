#include <sys/mman.h>
#include <sys/time.h>
#include <unistd.h>

#include <iostream>
#include <fmt/core.h>

#include <libcamera/base/span.h>
#include <libcamera/camera.h>
#include <libcamera/camera_manager.h>
#include <libcamera/control_ids.h>
#include <libcamera/controls.h>
#include <libcamera/formats.h>
#include <libcamera/framebuffer_allocator.h>
#include <libcamera/property_ids.h>
#include <libcamera/stream.h>

#include "write_jpg.h"

typedef unsigned long long uint64;

std::shared_ptr<libcamera::Camera> camera;

std::string control_name_from_id(int id) {
	switch (id) {
		case libcamera::controls::AE_ENABLE: return "AE_ENABLE";
		case libcamera::controls::AE_LOCKED: return "AE_LOCKED";
		case libcamera::controls::AE_METERING_MODE: return "AE_METERING_MODE";
		case libcamera::controls::AE_CONSTRAINT_MODE: return "AE_CONSTRAINT_MODE";
		case libcamera::controls::AE_EXPOSURE_MODE: return "AE_EXPOSURE_MODE";
		case libcamera::controls::EXPOSURE_VALUE: return "EXPOSURE_VALUE";
		case libcamera::controls::EXPOSURE_TIME: return "EXPOSURE_TIME";
		case libcamera::controls::ANALOGUE_GAIN: return "ANALOGUE_GAIN";
		case libcamera::controls::BRIGHTNESS: return "BRIGHTNESS";
		case libcamera::controls::CONTRAST: return "CONTRAST";
		case libcamera::controls::LUX: return "LUX";
		case libcamera::controls::AWB_ENABLE: return "AWB_ENABLE";
		case libcamera::controls::AWB_MODE: return "AWB_MODE";
		case libcamera::controls::AWB_LOCKED: return "AWB_LOCKED";
		case libcamera::controls::COLOUR_GAINS: return "COLOUR_GAINS";
		case libcamera::controls::COLOUR_TEMPERATURE: return "COLOUR_TEMPERATURE";
		case libcamera::controls::SATURATION: return "SATURATION";
		case libcamera::controls::SENSOR_BLACK_LEVELS: return "SENSOR_BLACK_LEVELS";
		case libcamera::controls::SHARPNESS: return "SHARPNESS";
		case libcamera::controls::FOCUS_FO_M: return "FOCUS_FO_M";
		case libcamera::controls::COLOUR_CORRECTION_MATRIX: return "COLOUR_CORRECTION_MATRIX";
		case libcamera::controls::SCALER_CROP: return "SCALER_CROP";
		case libcamera::controls::DIGITAL_GAIN: return "DIGITAL_GAIN";
		case libcamera::controls::FRAME_DURATION: return "FRAME_DURATION";
		case libcamera::controls::FRAME_DURATION_LIMITS: return "FRAME_DURATION_LIMITS";
		case libcamera::controls::SENSOR_TEMPERATURE: return "SENSOR_TEMPERATURE";
		case libcamera::controls::SENSOR_TIMESTAMP: return "SENSOR_TIMESTAMP";
		case libcamera::controls::AF_MODE: return "AF_MODE";
		case libcamera::controls::AF_RANGE: return "AF_RANGE";
		case libcamera::controls::AF_SPEED: return "AF_SPEED";
		case libcamera::controls::AF_METERING: return "AF_METERING";
		case libcamera::controls::AF_WINDOWS: return "AF_WINDOWS";
		case libcamera::controls::AF_TRIGGER: return "AF_TRIGGER";
		case libcamera::controls::AF_PAUSE: return "AF_PAUSE";
		case libcamera::controls::LENS_POSITION: return "LENS_POSITION";
		case libcamera::controls::AF_STATE: return "AF_STATE";
		case libcamera::controls::AF_PAUSE_STATE: return "AF_PAUSE_STATE";
		case libcamera::controls::AE_PRECAPTURE_TRIGGER: return "AE_PRECAPTURE_TRIGGER";
		case libcamera::controls::NOISE_REDUCTION_MODE: return "NOISE_REDUCTION_MODE";
		case libcamera::controls::COLOR_CORRECTION_ABERRATION_MODE: return "COLOR_CORRECTION_ABERRATION_MODE";
		case libcamera::controls::AE_STATE: return "AE_STATE";
		case libcamera::controls::AWB_STATE: return "AWB_STATE";
		case libcamera::controls::SENSOR_ROLLING_SHUTTER_SKEW: return "SENSOR_ROLLING_SHUTTER_SKEW";
		case libcamera::controls::LENS_SHADING_MAP_MODE: return "LENS_SHADING_MAP_MODE";
		case libcamera::controls::SCENE_FLICKER: return "SCENE_FLICKER";
		case libcamera::controls::PIPELINE_DEPTH: return "PIPELINE_DEPTH";
		case libcamera::controls::MAX_LATENCY: return "MAX_LATENCY";
		case libcamera::controls::TEST_PATTERN_MODE: return "TEST_PATTERN_MODE";
		default: return "UNKNOWN";
	};
}

bool capture_in_progress = false; // TODO: fix possible race condition at end of request service
libcamera::FrameBuffer *frame_buffer;
std::map<libcamera::FrameBuffer *, std::vector<libcamera::Span<uint8_t>>> mapped_buffers_;
libcamera::Stream *stream;
long advertised_capture_time;

std::vector<libcamera::Span<uint8_t>> Mmap(libcamera::FrameBuffer *buffer)
{
	auto item = mapped_buffers_.find(buffer);
	if (item == mapped_buffers_.end())
		return {};
	return item->second;
}

int width = 4056; // TODO: how to detect these?
int height= 3040;
int stride = 0;

uint64 boot_time_ms() {
	struct timespec ts;
	clock_gettime(CLOCK_BOOTTIME, &ts);
	return ts.tv_sec * (uint64)1000 + ts.tv_nsec / 1000000;
}

uint64 epoch_time_ms() {
	struct timeval tv;
	gettimeofday(&tv, NULL);
	return tv.tv_sec * (uint64)1000 + tv.tv_usec / 1000;
}

uint64 boot_time_ns_to_epoch_time_ms(uint64 boot_time_ns) {
	struct timespec ts;
	clock_gettime(CLOCK_BOOTTIME, &ts);
	uint64 boot_time_us = ts.tv_sec * (uint64)1000000 + ts.tv_nsec / 1000;

	struct timeval tv;
	gettimeofday(&tv, NULL);
	return tv.tv_sec * (uint64)1000 + tv.tv_usec / 1000;
	uint64 epoch_time_us = tv.tv_sec * (uint64)1000000 + tv.tv_usec;

	return (boot_time_ns / 1000 - boot_time_us + epoch_time_us) / 1000;
}

uint64 start_capture_time_ms;

std::string format_ms(uint64 ms) {
	return fmt::format("{}.{:03}", ms / 1000, ms % 1000);
}

template <typename S, typename... Args>
void log(const S& format, Args&&... args) {
	std::string msg = fmt::vformat(format, fmt::make_format_args(args...));
  	std::cerr << fmt::format("{}: {}\n", format_ms(epoch_time_ms()), msg);
}

void msleep(uint64 ms) {
	usleep(ms * 1000);
}

void request_complete(libcamera::Request *request) {
	uint64 end_capture_time_ms = epoch_time_ms();
    log("Capture complete in {}s with status {}.  Metadata:", format_ms(end_capture_time_ms - start_capture_time_ms), request->status());
	for (auto &[id, value]: request->metadata()) {
		std::string val_str = value.toString();
		if (id == libcamera::controls::SENSOR_TIMESTAMP) {
			val_str = format_ms(boot_time_ns_to_epoch_time_ms(atoll(val_str.c_str())));
		}
		log(fmt::format("   {}({}): {}", id, control_name_from_id(id), val_str));
	}

	const std::vector<libcamera::Span<uint8_t>> mem = Mmap(frame_buffer);

	std::string output_filename(fmt::format("{}.jpg", advertised_capture_time));
	int jpg_quality = 90;
	bool verbose = false;

	jpeg_save(
	 	mem,
		stream->configuration().size.width,
		stream->configuration().size.height,
		stream->configuration().stride,
		stream->configuration().pixelFormat,
		//stream->configuration().colorSpace,
   	    libcamera::ColorSpace::Jpeg,
	 	request->metadata(),
	 	output_filename,
	 	"foo", // cam name
		jpg_quality, 
		0, // restart
		verbose);
	log("Wrote image to {}", output_filename);

	// Address possible race condition here -- can we actually start a new request before this function returns?
	assert(capture_in_progress);
	capture_in_progress = false;
}




int main(int argc, char **argv) {
	//std::cerr << "Main pid=" << getpid() << " tid=" << gettid() << "\n";
    libcamera::CameraManager manager;
    int ret = manager.start();
 	if (ret) {
 		throw std::runtime_error("camera manager failed to start, code " + std::to_string(-ret));
    }

	std::vector<std::shared_ptr<libcamera::Camera>> cameras = manager.cameras();
	// Do not show USB webcams as these are not supported in libcamera-apps!
	auto rem = std::remove_if(cameras.begin(), cameras.end(),
							  [](auto &cam) { return cam->id().find("/usb") != std::string::npos; });
	cameras.erase(rem, cameras.end());
    printf("%d non-USB cameras found\n", cameras.size());

	if (cameras.size() != 1) {
		throw std::runtime_error("Number of cameras != 1, aborting");
    }

	std::string const &cam_id = cameras[0]->id();
	camera = manager.get(cam_id);

	if (!camera) {
		throw std::runtime_error("failed to find camera " + cam_id);
    }

	if (camera->acquire()) {
		throw std::runtime_error("failed to acquire camera " + cam_id);
    }

	log("Acquired camera {}", cam_id);

    log("Configuring still capture...");

	// Always request a raw stream as this forces the full resolution capture mode.
	// (options_->mode can override the choice of camera mode, however.)
	libcamera::StreamRoles stream_roles = 
		{ libcamera::StreamRole::StillCapture, libcamera::StreamRole::Raw };
	std::unique_ptr<libcamera::CameraConfiguration> camera_config = camera->generateConfiguration(stream_roles);
	if (!camera_config)
		throw std::runtime_error("failed to generate still capture configuration");
	camera_config->transform = libcamera::Transform::HVFlip;

	auto pixel_format = libcamera::formats::YUV420;
	libcamera::StreamConfiguration &stream_config=camera_config->at(0);

    stream_config.pixelFormat = pixel_format;
	stream_config.bufferCount = 1; // or 2 or 3

	// Is this for a more recent version of libcamera?
	//auto colour_space = libcamera::ColorSpace::Jpeg;
	//configuration->at(0).colorSpace = libcamera::ColorSpace::Jpeg;

    libcamera::CameraConfiguration::Status validation = camera_config->validate();
	if (validation == libcamera::CameraConfiguration::Invalid)
		throw std::runtime_error("failed to valid stream configurations");
	else if (validation == libcamera::CameraConfiguration::Adjusted)
		log("Stream configuration adjusted");

	if (camera->configure(camera_config.get()) < 0)
		throw std::runtime_error("failed to configure streams");
    
    log("Camera streams configured");

	log("Available controls:");
	for (auto const &[id, info] : camera->controls()) {
	 	log("    {}: {}", id->name(), info.toString());
	}

	log("Found {} stream configurations", camera_config->size());

	stream = camera_config->at(0).stream();
	if (!stream)
		throw std::runtime_error("no stream");

    // Configure camera?
    //
    // libcamera::CameraConfiguration::Status validation = configuration_->validate();
	// if (validation == libcamera::CameraConfiguration::Invalid)
	// 	throw std::runtime_error("failed to valid stream configurations");
	// else if (validation == libcamera::CameraConfiguration::Adjusted)
	// 	std::cerr << "Stream configuration adjusted" << std::endl;

	// if (camera_->configure(configuration_.get()) < 0)
	// 	throw std::runtime_error("failed to configure streams");
	// if (options_->verbose)
	// 	std::cerr << "Camera streams configured" << std::endl;

	// Framerate is a bit weird. If it was set programmatically, we go with that, but
	// otherwise it applies only to preview/video modes. For stills capture we set it
	// as long as possible so that we get whatever the exposure profile wants.
	// controls_.set(controls::FrameDurationLimits, { INT64_C(100), INT64_C(1000000000) });
		// else if (options_->framerate > 0)
		// {
		// 	int64_t frame_time = 1000000 / options_->framerate; // in us
		// 	controls_.set(controls::FrameDurationLimits, { frame_time, frame_time });
		// }
	
	// if (!controls_.contains(controls::ExposureTime) && options_->shutter)
	// 	controls_.set(controls::ExposureTime, options_->shutter);
	// if (!controls_.contains(controls::AnalogueGain) && options_->gain)
	// 	controls_.set(controls::AnalogueGain, options_->gain);
	// if (!controls_.contains(controls::AeMeteringMode))
	// 	controls_.set(controls::AeMeteringMode, options_->metering_index);
	// if (!controls_.contains(controls::AeExposureMode))
	// 	controls_.set(controls::AeExposureMode, options_->exposure_index);
	// if (!controls_.contains(controls::ExposureValue))
	// 	controls_.set(controls::ExposureValue, options_->ev);
	// if (!controls_.contains(controls::AwbMode))
	// 	controls_.set(controls::AwbMode, options_->awb_index);
	// if (!controls_.contains(controls::ColourGains) && options_->awb_gain_r && options_->awb_gain_b)
	// 	controls_.set(controls::ColourGains, { options_->awb_gain_r, options_->awb_gain_b });
	// if (!controls_.contains(controls::Brightness))
	// 	controls_.set(controls::Brightness, options_->brightness);
	// if (!controls_.contains(controls::Contrast))
	// 	controls_.set(controls::Contrast, options_->contrast);
	// if (!controls_.contains(controls::Saturation))
	// 	controls_.set(controls::Saturation, options_->saturation);
	// if (!controls_.contains(controls::Sharpness))
	// 	controls_.set(controls::Sharpness, options_->sharpness);


	auto allocator_ = new libcamera::FrameBufferAllocator(camera);
	// for (StreamConfiguration &config : *configuration_)
	// {
	//libcamera::Stream *stream = config.stream();

	log("Allocating frame buffers");
	if (allocator_->allocate(stream) < 0)
		throw std::runtime_error("failed to allocate capture buffers");

	for (const std::unique_ptr<libcamera::FrameBuffer> &buffer : allocator_->buffers(stream))
	{
		log("Allocating framebuffer {}", (void*)&buffer);
		// "Single plane" buffers appear as multi-plane here, but we can spot them because then
		// planes all share the same fd. We accumulate them so as to mmap the buffer only once.
		size_t buffer_size = 0;
		for (unsigned i = 0; i < buffer->planes().size(); i++)
		{
			const libcamera::FrameBuffer::Plane &plane = buffer->planes()[i];
			buffer_size += plane.length;
			if (i == buffer->planes().size() - 1 || plane.fd.get() != buffer->planes()[i + 1].fd.get())
			{
				void *memory = mmap(NULL, buffer_size, PROT_READ | PROT_WRITE, MAP_SHARED, plane.fd.get(), 0);
				mapped_buffers_[buffer.get()].push_back(
					libcamera::Span<uint8_t>(static_cast<uint8_t *>(memory), buffer_size));
				buffer_size = 0;
			}
		}
		frame_buffer = buffer.get();
		//frame_buffers_[stream].push(buffer.get());
	}

	// if (options_->verbose)
	// 	std::cerr << "Buffers allocated and mapped" << std::endl;

    libcamera::ControlList control_list(camera->controls());

	log("Starting camera");
	if (camera->start(&control_list)) 
		throw std::runtime_error("failed to start camera");

	camera->requestCompleted.connect(request_complete);

	int cadence_factor = 1;
	int cadence_ms = 2000; // ms
	std::unique_ptr<libcamera::Request> request;

	while (1) {
		uint64 current_time_ms = epoch_time_ms();
		uint64 desired_capture_time_ms = (current_time_ms + cadence_ms) / cadence_ms * cadence_ms;
		uint64 sleep_time_ms = desired_capture_time_ms - current_time_ms;
		log("Sleeping {}s until {}", format_ms(sleep_time_ms), format_ms(desired_capture_time_ms));
		msleep(sleep_time_ms);
		if (capture_in_progress) {
			cadence_factor = 2;
			log("Capture taking too long; doubling cadence for next capture to {}s", format_ms(cadence_ms * cadence_factor));
			continue;
		} else {
			cadence_factor = 1;
		}

		advertised_capture_time = desired_capture_time_ms / 1000;
		log("Queueing request to capture {}", advertised_capture_time);
		request = camera->createRequest();
		request->addBuffer(stream, frame_buffer);

		start_capture_time_ms = epoch_time_ms();
		
		capture_in_progress = true;
		if (camera->queueRequest(request.get()) < 0)
			throw std::runtime_error("Failed to queue request");
	}

	log("Stopping camera");
	camera->stop();
	
    log("Releasing camera");
    camera->release();
    log("Camera released");
    return 0;
}


// void LibcameraApp::OpenCamera()
// {
// 	// Make a preview window.
// 	preview_ = std::unique_ptr<Preview>(make_preview(options_.get()));
// 	preview_->SetDoneCallback(std::bind(&LibcameraApp::previewDoneCallback, this, std::placeholders::_1));

// 	if (options_->verbose)
// 		std::cerr << "Opening camera..." << std::endl;

// 	camera_manager_ = std::make_unique<CameraManager>();
// 	int ret = camera_manager_->start();
// 	if (ret)
// 		throw std::runtime_error("camera manager failed to start, code " + std::to_string(-ret));

// 	std::vector<std::shared_ptr<libcamera::Camera>> cameras = camera_manager_->cameras();
// 	// Do not show USB webcams as these are not supported in libcamera-apps!
// 	auto rem = std::remove_if(cameras.begin(), cameras.end(),
// 							  [](auto &cam) { return cam->id().find("/usb") != std::string::npos; });
// 	cameras.erase(rem, cameras.end());

// 	if (cameras.size() == 0)
// 		throw std::runtime_error("no cameras available");
// 	if (options_->camera >= cameras.size())
// 		throw std::runtime_error("selected camera is not available");

// 	std::string const &cam_id = cameras[options_->camera]->id();
// 	camera_ = camera_manager_->get(cam_id);
// 	if (!camera_)
// 		throw std::runtime_error("failed to find camera " + cam_id);

// 	if (camera_->acquire())
// 		throw std::runtime_error("failed to acquire camera " + cam_id);
// 	camera_acquired_ = true;

// 	if (options_->verbose)
// 		std::cerr << "Acquired camera " << cam_id << std::endl;

// 	if (!options_->post_process_file.empty())
// 		post_processor_.Read(options_->post_process_file);
// 	// The queue takes over ownership from the post-processor.
// 	post_processor_.SetCallback(
// 		[this](CompletedRequestPtr &r) { this->msg_queue_.Post(Msg(MsgType::RequestComplete, std::move(r))); });
// }
