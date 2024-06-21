
!/bin/bash

# Function to start a Python script in the background
start_script() {
    local script_name=$1
    echo "Starting $script_name"
    python $script_name &
}

# Start all the Python scripts
start_script main.py
start_script arrrived.py
start_script custom.py
start_script backup.py
start_script delete.py
start_script admin.py
start_script sim.py

# Wait for all background jobs to complete
wait
bash run