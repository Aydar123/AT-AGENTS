#!/bin/bash

# 1. Установить библиотеки из requirements.txt
echo "Установка зависимостей из requirements.txt..."
pip install -r requirements.txt

# 2. Подтянуть дополнительные зависимости
echo "Установка дополнительных зависимостей..."
pip install git+https://github.com/grigandal625/AT_QUEUE.git@master
pip install git+https://github.com/grigandal625/AT_SOLVER.git@master
pip install git+https://github.com/grigandal625/AT_TEMPORAL_SOLVER.git@master
pip install git+https://github.com/grigandal625/AT_BLACKBOARD.git@master

# 3. Создать контейнер с RabbitMQ
echo "Создание контейнера с RabbitMQ..."
docker run --name rabbit_at_parking -p 15672:15672 -p 5672:5672 -d rabbitmq:management

# 4. Запустить компоненты в новых терминалах
echo "Запуск компонентов в новых терминалах..."

gnome-terminal -- bash -c "python -m at_queue; exec bash"
gnome-terminal -- bash -c "python -m at_temporal_solver; exec bash"
gnome-terminal -- bash -c "python -m at_solver; exec bash"
gnome-terminal -- bash -c "python -m at_blackboard; exec bash"
gnome-terminal -- bash -c "python logic/planner/ATAgentPlanner.py; exec bash"

echo "Все процессы запущены."
