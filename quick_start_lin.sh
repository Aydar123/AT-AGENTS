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
## Запуск каждого компонента в новом терминале с ожиданием
#gnome-terminal -- bash -c "source ./venv/bin/activate; python -m at_queue; echo 'PRESS ENTER TO CLOSE WINDOW'; read"
#gnome-terminal -- bash -c "source ./venv/bin/activate; python -m at_temporal_solver; echo 'PRESS ENTER TO CLOSE WINDOW'; read"
#gnome-terminal -- bash -c "source ./venv/bin/activate; python -m at_solver; echo 'PRESS ENTER TO CLOSE WINDOW'; read"
#gnome-terminal -- bash -c "source ./venv/bin/activate; python -m at_blackboard; echo 'PRESS ENTER TO CLOSE WINDOW'; read"
#gnome-terminal -- bash -c "source ./venv/bin/activate; python logic/planner/ATAgentPlanner.py; echo 'PRESS ENTER TO CLOSE WINDOW'; read"

echo "ALL PROCESSES STARTED."
