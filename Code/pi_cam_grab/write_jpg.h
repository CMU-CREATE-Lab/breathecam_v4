#pragma once

#include <optional>

#include <libcamera/control_ids.h>
#include <libcamera/controls.h>
#include <libcamera/formats.h>
#include <libcamera/color_space.h>

void jpeg_save(std::vector<libcamera::Span<uint8_t>> const &mem, 
			  unsigned int width, unsigned int height, unsigned int stride, libcamera::PixelFormat pixel_format, libcamera::ColorSpace colour_space,
		      libcamera::ControlList const &metadata, std::string const &filename,
			  std::string const &cam_name, int quality, int restart, bool verbose);
