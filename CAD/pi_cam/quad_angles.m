% Script to compute the camera angles for overlapping fields of view with a
% particular lens FOV.

% Lens FOV in degrees.  You can use:
%    https://www.scantips.com/lights/fieldofview.html
% 
% but it is very confusing UI.  The sensor format for the Pi HQ camera is
% 1/2.3.  With this you can find the FOV for a particular focal length.
%fov = 14; % 25mm
fov = 21.83; % 16mm

% Overlap fraction between camera FOVs
%overlap = 0.1
overlap = 0.05;

% Find camera angles relative to the theta(1) edge of the FOV (outer edge
% of camera 1).
theta(1) = fov/2;
for ix = 2:4
  theta(ix) = theta(ix-1) + fov - (fov*overlap);
end

% Center the angles between camera 2 and 3 (i.e. in the middle of total
% FOV).
theta = theta - (theta(2) + theta(3))/2

% This is the total FOV from one side to the other.
fov_total = (theta(4) + fov/2) - (theta(1) - fov/2)
