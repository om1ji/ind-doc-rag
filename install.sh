#!/bin/bash
set -e

mkdir -p models

# Определяем платформу: GPU (Linux + NVIDIA) или CPU (всё остальное)
if nvidia-smi > /dev/null 2>&1; then
  export LLAMA_IMAGE_SUFFIX="-cuda"
  export GPU_LAYERS=99
  export COMPOSE_FILE="docker-compose.yml:docker-compose.gpu.yml"
  echo "=== GPU режим (NVIDIA) ==="
else
  export LLAMA_IMAGE_SUFFIX=""
  export GPU_LAYERS=0
  export COMPOSE_FILE="docker-compose.yml"
  echo "=== CPU режим ==="
fi

echo "=== Загрузка моделей ==="
if [ ! -f models/qwen3-8b-q4_k_m.gguf ]; then
  echo "Скачиваю qwen3-8b-q4_k_m.gguf (~5 GB)..."
  wget -c -O models/qwen3-8b-q4_k_m.gguf \
    "https://huggingface.co/Aldaris/Qwen3-8B-Q4_K_M-GGUF/resolve/main/qwen3-8b-q4_k_m.gguf"
else
  echo "qwen3-8b-q4_k_m.gguf уже есть, пропускаю"
fi

if [ ! -f models/bge-m3-q4_k_m.gguf ]; then
  echo "Скачиваю bge-m3-q4_k_m.gguf (~1.2 GB)..."
  wget -c -O models/bge-m3-q4_k_m.gguf \
    "https://huggingface.co/gpustack/bge-m3-GGUF/resolve/main/bge-m3-Q4_K_M.gguf"
else
  echo "bge-m3-q4_k_m.gguf уже есть, пропускаю"
fi

echo "=== Запуск сервисов ==="
docker compose up -d qdrant docs-api llama-chat llama-embed

echo "=== Ожидание Qdrant ==="
until curl -sf http://localhost:6333/healthz > /dev/null 2>&1; do
  sleep 2
done

echo "=== Восстановление базы Qdrant ==="
for snapshot in qdrant-snapshots/*.snapshot; do
  [ -f "$snapshot" ] || continue
  filename=$(basename "$snapshot")
  collection=$(echo "$filename" | sed 's/-[0-9].*//')
  echo "Восстанавливаю коллекцию: $collection из $filename"
  curl -sf -X POST \
    "http://localhost:6333/collections/${collection}/snapshots/upload?priority=snapshot" \
    -H "Content-Type: multipart/form-data" \
    -F "snapshot=@${snapshot}"
  echo ""
done

echo "=== Ожидание llama-chat (загрузка модели) ==="
until curl -sf http://localhost:8080/health | grep -q '"status":"ok"'; do
  echo -n "."
  sleep 3
done
echo " готово"

echo "=== Запуск агента и фронтенда ==="
docker compose up -d agent frontend nginx

echo ""
echo "Готово. Открыть: http://localhost"
