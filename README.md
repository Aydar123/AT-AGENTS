# AT-AGENTS
## Установка продовой версии проекта (prod 1.0)

## 1. Склонируй репозиторий:
```bash
git clone https://github.com/Aydar123/AT-AGENTS.git
```
## 2. Развертывание и запуск проекта:
### 2.1: Собери образы:
```bash
docker compose build
```
### 2.2: Запусти контейнеры в фоновом режиме:
```bash
docker compose up -d
```
## 3*. Дополнительно:
### 3.1: Остановить контейнеры:
```bash
docker compose stop
```
### 3.2: Удалить контейнеры:
```bash
docker compose down
```