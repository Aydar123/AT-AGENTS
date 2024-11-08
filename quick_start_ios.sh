#!/bin/bash

# 1. CREATE VIRTUAL ENVIRONMENT IF IT DOES NOT EXIST
echo "CREATING VIRTUAL ENVIRONMENT VENV..."
if [ ! -d "./venv" ]; then
    python3 -m venv venv
    echo "VIRTUAL ENVIRONMENT CREATED."
else
    echo "VIRTUAL ENVIRONMENT ALREADY EXISTS."
fi

# 2. ACTIVATE VIRTUAL ENVIRONMENT
echo "ACTIVATING VIRTUAL ENVIRONMENT..."
source ./venv/bin/activate

# 3. INSTALL REQUIREMENTS FROM requirements.txt
echo "INSTALLING DEPENDENCIES FROM requirements.txt..."
pip install -r requirements.txt

# 4. INSTALL ADDITIONAL DEPENDENCIES
echo "INSTALLING ADDITIONAL DEPENDENCIES..."
pip install git+https://github.com/grigandal625/AT_QUEUE.git@master
pip install git+https://github.com/grigandal625/AT_SOLVER.git@master
pip install git+https://github.com/grigandal625/AT_TEMPORAL_SOLVER.git@master
pip install git+https://github.com/grigandal625/AT_BLACKBOARD.git@master

# 5. CREATE CONTAINER WITH RABBITMQ
echo "CREATING CONTAINER WITH RABBITMQ..."
docker run --name rabbit_at_parking -p 15672:15672 -p 5672:5672 -d rabbitmq:management

# # 6. LAUNCH COMPONENTS IN NEW TERMINAL WINDOWS AND KEEP THEM OPEN
#echo "LAUNCHING COMPONENTS IN NEW TERMINAL WINDOWS..."
#
## Function to open a new Terminal tab and run a command
#run_in_new_terminal() {
#    osascript <<EOF
#    tell application "Terminal"
#        do script "cd \"$(pwd)\"; source ./venv/bin/activate; $1; echo 'PRESS ENTER TO CLOSE WINDOW'; read"
#    end tell
#EOF
#}
#
## Run each command in a new terminal tab
#run_in_new_terminal "python -m at_queue"
#run_in_new_terminal "sudo python -m at_temporal_solver"
#run_in_new_terminal "sudo python -m at_solver"
#run_in_new_terminal "sudo python -m at_blackboard"
#run_in_new_terminal "python logic/planner/ATAgentPlanner.py"

echo "ALL PROCESSES STARTED."
