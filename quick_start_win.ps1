# 0. CREATE VIRTUAL ENVIRONMENT IF IT DOES NOT EXIST
Write-Output "CREATING VIRTUAL ENVIRONMENT VENV..."
if (!(Test-Path -Path "./venv")) {
    python -m venv venv
    Write-Output "VIRTUAL ENVIRONMENT CREATED."
} else {
    Write-Output "VIRTUAL ENVIRONMENT ALREADY EXISTS."
}

# 1. ACTIVATE VIRTUAL ENVIRONMENT
Write-Output "ACTIVATING VIRTUAL ENVIRONMENT..."
# Activation for current script
& .\venv\Scripts\Activate

# 2. INSTALL REQUIREMENTS FROM requirements.txt
Write-Output "INSTALLING DEPENDENCIES FROM requirements.txt..."
pip install -r requirements.txt

# 3. INSTALL ADDITIONAL DEPENDENCIES
Write-Output "INSTALLING ADDITIONAL DEPENDENCIES..."
pip install git+https://github.com/grigandal625/AT_QUEUE.git@master
pip install git+https://github.com/grigandal625/AT_SOLVER.git@master
pip install git+https://github.com/grigandal625/AT_TEMPORAL_SOLVER.git@master
pip install git+https://github.com/grigandal625/AT_BLACKBOARD.git@master

# 4. CREATE CONTAINER WITH RABBITMQ
Write-Output "CREATING CONTAINER WITH RABBITMQ..."
docker run --name rabbit_at_parking -p 15672:15672 -p 5672:5672 -d rabbitmq:management

# 5. LAUNCH COMPONENTS IN NEW POWERSHELL WINDOWS AND KEEP THEM OPEN
Write-Output "LAUNCHING COMPONENTS IN NEW POWERSHELL WINDOWS..."

Start-Process powershell -ArgumentList "-NoExit", "-Command", "venv\Scripts\activate; python -m at_queue; Read-Host 'PRESS ENTER TO CLOSE WINDOW'"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "venv\Scripts\activate; python -m at_temporal_solver; Read-Host 'PRESS ENTER TO CLOSE WINDOW'"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "venv\Scripts\activate; python -m at_solver; Read-Host 'PRESS ENTER TO CLOSE WINDOW'"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "venv\Scripts\activate; python -m at_blackboard; Read-Host 'PRESS ENTER TO CLOSE WINDOW'"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "venv\Scripts\activate; python logic/planner/ATAgentPlanner.py; Read-Host 'PRESS ENTER TO CLOSE WINDOW'"

Write-Output "ALL PROCESSES STARTED."
