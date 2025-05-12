% Script to compute the camera angles for overlapping fields of view with a
% particular lens FOV.

% Sensor size in mm, for 1/2.3 Sony chips like IMX477 in Pi HQ
% camera. Other 1/2.3 sensors vary slightly.
sensor_size = [6.287, 4.712];

% Image size in pixels
pixel_size = [4056, 3040];

portrait = false
%portrait = true

% Distance between mount holes on the short side for Arducam mini HQ
% cam. This is used to show sensitivity of mount fabrication tolerances.
mount_baseline = 12.5e-3;

if (portrait)
  sensor_size = fliplr(sensor_size);
  pixel_size = fliplr(pixel_size);
end

% Focal length in mm.
%focal_length = 12.5
%focal_length = 16
%focal_length = 25
focal_length = 50

% Camera arrangement, number of cameras in the X and Y directions
%layout = [2 2]
%layout = [4 1]
layout = [1 1]

% Angular field of view, see:
% https://www.edmundoptics.com/knowledge-center/application-notes/imaging/understanding-focal-length-and-field-of-view/
fov = 2*atan(sensor_size ./ (2*focal_length)) * (180/pi)

% Size of a pixel FOV in radians
rad_pixel = (fov(1)/180*pi) / pixel_size(1)

% Overlap in pixels between camera FOVs
%overlap_pix = 250
overlap_pix = 300
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

% Sine plate angles, discard negative values because there should be
% symmetric positive ones.
plate_angles = theta(theta(:,1) >= 0, 1);

% Spacer stack needed to get angle with 5" sine plate
plate_stacks = [plate_angles sin(plate_angles / 180 * pi)*5]


% Sensitivity to mounting error.  What dimensional error (normal to surface)
% at the camera mounting would correspond to a pixel error of 1/4 the nominal
% overlap?  Worst case this would give only 1/2 overlap, since the adjacent
% cam could be off in the opposite direction.
err_rad = overlap_pix / 4 * rad_pixel; % Error in radians
max_mount_error_m = err_rad * mount_baseline % small angle approximation
