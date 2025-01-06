#!/bin/bash

# Stop any running services, test image capture, and then run everything.

# Set the script directory (assumes this script is in the tools directory)
script_dir=$(realpath "$(dirname "$(realpath "$0")")/../")

# Set the virtual environment directory
venv_dir="${script_dir}/.venv"

# Activate the virtual environment
if [ -d "$venv_dir" ]; then
    echo "Activating virtual environment at $venv_dir"
    source "$venv_dir/bin/activate"
else
    echo "Virtual environment not found at $venv_dir. Exiting."
    exit 1
fi

echo "Halt breathecam services (if running)"
${script_dir}tools/kill_all.sh

echo "Testing image capture"
python3 "${script_dir}imageService.py" --test-only

echo "^C if you don't want to run_all"
sleep 5

echo "Start breathecam services"
${script_dir}run_all.sh
