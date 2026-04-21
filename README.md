# Ассистент по промышленной безопасности

AI-ассистент для работы с технической документацией и нормативно-правовой базой в области промышленной безопасности.

## Требования к железу

| Компонент | Минимум | Рекомендуется |
|-----------|---------|---------------|
| CPU | 8 ядер | 8+ ядер |
| RAM | 16 GB | 32 GB |
| GPU | NVIDIA 8 GB VRAM | NVIDIA 12+ GB VRAM |
| Диск | 20 GB свободно | 50 GB SSD |
| ОС | Ubuntu 22.04 / 24.04 | Ubuntu 24.04 |

## Структура папки

```
.
├── models/                  # LLM модели (qwen3-8b, bge-m3)
├── qdrant-snapshots/        # База знаний (векторная БД)
├── files/                   # Исходные документы
├── agent/                   # Серверная часть (FastAPI)
├── frontend/                # Веб-интерфейс (React)
├── docker-compose.yml       # Конфигурация сервисов
├── nginx.conf               # Веб-сервер
└── install.sh               # Скрипт установки
```

---

## Установка

### Шаг 1. Установить Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

### Шаг 2. Установить NVIDIA Container Toolkit

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Проверка что GPU виден:
```bash
nvidia-smi
```

### Шаг 3. Запустить установку

```bash
chmod +x install.sh
./install.sh
```

Скрипт автоматически:
- Запустит все сервисы
- Восстановит базу знаний из снапшотов
- Соберёт и запустит веб-интерфейс

### Шаг 4. Открыть в браузере

```
http://localhost
```

---

## Управление сервисами

### Запустить

```bash
docker compose up -d
```

### Остановить

```bash
docker compose down
```

### Перезапустить один сервис

```bash
docker compose restart agent
```

### Просмотр логов

```bash
# Все сервисы
docker compose logs -f

# Конкретный сервис
docker compose logs -f llama-chat
docker compose logs -f agent
docker compose logs -f nginx
```

### Статус сервисов

```bash
docker compose ps
```

---

## Диагностика

### Сервис не запускается

```bash
docker compose logs <имя_сервиса>
```

### GPU не определяется

```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

### База знаний пустая

```bash
curl http://localhost:6333/collections
```

Если коллекции отсутствуют — повторить восстановление снапшотов:

```bash
for snapshot in qdrant-snapshots/*.snapshot; do
  filename=$(basename "$snapshot")
  collection=$(echo "$filename" | sed 's/-[0-9].*//')
  curl -X POST \
    "http://localhost:6333/collections/${collection}/snapshots/upload?priority=snapshot" \
    -H "Content-Type: multipart/form-data" \
    -F "snapshot=@${snapshot}"
done
```

### Модель отвечает медленно

Проверить что модель работает на GPU, а не CPU:
```bash
docker compose logs llama-chat | grep "ggml_cuda"
```

Если строки с `ggml_cuda` есть — GPU используется.

---

## Сервисы и порты

| Сервис | Порт | Описание |
|--------|------|----------|
| nginx | 80 | Точка входа, веб-интерфейс |
| llama-chat | 8080 | LLM (qwen3-8b) |
| llama-embed | 8081 | Эмбеддинги (bge-m3) |
| agent | 8001 | FastAPI агент |
| qdrant | 6333 | Векторная база данных |
| docs-api | 8000 | API документов |
