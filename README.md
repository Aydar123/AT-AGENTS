# AT-AGENTS
## Установка локальной версии проекта (local 1.0)

## 1. Склонируйте репозиторий:
```bash
git clone --branch local --single-branch https://github.com/Aydar123/AT-AGENTS.git
```
## 2. Создайте виртуальное окружение и установите зависимости:
### 2.1: Создайте .venv
##### 2.1.1: Windows:
```bash
python -m venv .venv
```
##### 2.1.2: MacOS:
```bash
python3 -m venv .venv
```

### 2.2: Активируйте venv
##### 2.2.1: Windows:
```bash
venv\Scripts\activate
```
##### 2.2.2: MacOS:
```bash
source .venv/bin/activate
```

### 2.3: Установите poetry
```bash
pip install poetry
```
### 2.4: Установите зависимости в проект
```bash
poetry install --no-root
```

## 3. Создайте контейнер с RabbitMQ:
```bash 
docker run --name rabbit_at -p 15672:15672 -p 5672:5672 rabbitmq:management
```

## 4. Запустите в нескольких терминалах следующие 5 компонентов:
### 1. Компонент "Брокер сообщений"
#### 1: Windows & MacOS
```bash
python -m at_queue
```

### 2. Компонент "Темпоральный решатель"
#### 2.1: Windows:
```bash
python -m at_temporal_solver
```
##### 2.2: MacOS: 
```bash
sudo python -m at_temporal_solver
```

### 3. Компонент "АТ-РЕШАТЕЛЬ"
#### 3.1: Windows:
```bash
python -m at_solver
```
#### 3.2: MacOS: 
```bash
sudo python -m at_solver
```

### 4. Компонент "Классная доска"
#### 4.1: Windows:
```bash
python -m at_blackboard
```
#### 4.2: MacOS: 
```bash
sudo python -m at_blackboard
```

### 5. Компонент "Интеллектуальный планировщик"
#### 5.1: Windows:
```bash
python logic/planner/ATAgentPlanner.py
```
#### 5.1: MacOS:
```bash
sudo python logic/planner/ATAgentPlanner.py
```