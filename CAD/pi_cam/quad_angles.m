% Script to compute the camera angles for overlapping fields of view with a
% particular lens FOV.

% Sensor size in mm, for 1/2.3 Sony chips like IMX477 in Pi HQ
% camera. Other 1/2.3 sensors vary slightly.
sensor_size = [6.287, 4.712];

% Image size in pixels
pixel_size = [4056, 3040];

portrait = true

if (portrait)
  sensor_size = fliplr(sensor_size);
  pixel_size = fliplr(pixel_size);
end

% Focal length in mm.
focal_length = 16
%focal_length = 25

% Camera arrangement, number of cameras in the X and Y directions
%layout = [2 2]
layout = [4 1]

% Angular field of view, see:
% https://www.edmundoptics.com/knowledge-center/application-notes/imaging/understanding-focal-length-and-field-of-view/
fov = 2*atan(sensor_size ./ (2*focal_length)) * (180/pi)

% Overlap in pixels between camera FOVs
overlap_pix = 250
overlap_mm = overlap_pix / pixel_size(1) * sensor_size(1);
overlap_fov = 2*atan(overlap_mm ./ (2*focal_length)) * (180/pi);

fov_total = [];
theta = [];

% Find camera angles relative to the center of the FOV (at zero degrees)
for (dir = 1:2)
  ncams = layout(dir);
  fov_total(dir) = fov(dir) * ncams - ((ncams - 1) * overlap_fov);
  theta(1, dir) = -(fov_total(dir)/2) + fov(dir)/2;
  for (ix = 2:ncams)
    theta(ix, dir) = theta(ix - 1, dir) + fov(dir) - overlap_fov;
  end
end

fov_total
theta
