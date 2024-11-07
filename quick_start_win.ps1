# 1. Установить библиотеки из requirements.txt
Write-Output "Установка зависимостей из requirements.txt..."
pip install -r requirements.txt

# 2. Подтянуть дополнительные зависимости
Write-Output "Установка дополнительных зависимостей..."
pip install git+https://github.com/grigandal625/AT_QUEUE.git@master
pip install git+https://github.com/grigandal625/AT_SOLVER.git@master
pip install git+https://github.com/grigandal625/AT_TEMPORAL_SOLVER.git@master
pip install git+https://github.com/grigandal625/AT_BLACKBOARD.git@master

# 3. Создать контейнер с RabbitMQ
Write-Output "Создание контейнера с RabbitMQ..."
docker run --name rabbit_at_parking -p 15672:15672 -p 5672:5672 -d rabbitmq:management

# 4. Запуск компонентов в новых окнах PowerShell
Write-Output "Запуск компонентов в новых окнах PowerShell..."

Start-Process powershell -ArgumentList "python -m at_queue"
Start-Process powershell -ArgumentList "python -m at_temporal_solver"
Start-Process powershell -ArgumentList "python -m at_solver"
Start-Process powershell -ArgumentList "python -m at_blackboard"
Start-Process powershell -ArgumentList "python logic/planner/ATAgentPlanner.py"

Write-Output "Все процессы запущены."
