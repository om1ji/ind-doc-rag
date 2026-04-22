#!/bin/bash
set -e

mkdir -p models

# ── Определяем платформу ────────────────────────────────────────────────────
NATIVE_LLAMA=0

if nvidia-smi > /dev/null 2>&1; then
  export LLAMA_IMAGE_SUFFIX="-cuda"
  export GPU_LAYERS=99
  export COMPOSE_FILE="docker-compose.yml:docker-compose.gpu.yml"
  echo "=== GPU режим (NVIDIA CUDA) ==="
elif [ "$(uname)" = "Darwin" ] && command -v llama-server > /dev/null 2>&1; then
  NATIVE_LLAMA=1
  export LLM_URL="http://host.docker.internal:8080"
  export EMBED_URL="http://host.docker.internal:8081"
  export COMPOSE_FILE="docker-compose.yml"
  echo "=== Mac + Metal (нативный llama-server) ==="
else
  export LLAMA_IMAGE_SUFFIX=""
  export GPU_LAYERS=0
  export COMPOSE_FILE="docker-compose.yml"
  if [ "$(uname)" = "Darwin" ]; then
    echo "=== CPU режим (llama-server не найден; установи: brew install llama.cpp) ==="
  else
    echo "=== CPU режим ==="
  fi
fi

# ── Загрузка моделей ────────────────────────────────────────────────────────
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

# ── Запуск сервисов ─────────────────────────────────────────────────────────
echo "=== Запуск сервисов ==="
if [ "$NATIVE_LLAMA" = "1" ]; then
  # llama-server запускается нативно — Docker не нужен для llama-контейнеров
  docker compose up -d qdrant docs-api

  echo "=== Запуск нативных llama-server (Metal) ==="
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

  # chat
  if ! curl -sf http://localhost:8080/health > /dev/null 2>&1; then
    llama-server \
      -m "$SCRIPT_DIR/models/qwen3-8b-q4_k_m.gguf" \
      --host 0.0.0.0 --port 8080 \
      --ctx-size 16384 -n -1 --jinja -ngl 99 \
      > /tmp/llama-chat.log 2>&1 &
    echo "  llama-chat запущен (PID $!), лог: /tmp/llama-chat.log"
  else
    echo "  llama-chat уже запущен"
  fi

  # embed
  if ! curl -sf http://localhost:8081/health > /dev/null 2>&1; then
    llama-server \
      -m "$SCRIPT_DIR/models/bge-m3-q4_k_m.gguf" \
      --host 0.0.0.0 --port 8081 \
      --embedding --ctx-size 8192 --batch-size 2048 -ngl 99 \
      > /tmp/llama-embed.log 2>&1 &
    echo "  llama-embed запущен (PID $!), лог: /tmp/llama-embed.log"
  else
    echo "  llama-embed уже запущен"
  fi
else
  docker compose up -d qdrant docs-api llama-chat llama-embed
fi

# ── Ожидание Qdrant ─────────────────────────────────────────────────────────
echo "=== Ожидание Qdrant ==="
until curl -sf http://localhost:6333/healthz > /dev/null 2>&1; do
  sleep 2
done

# ── Восстановление базы Qdrant ───────────────────────────────────────────────
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

# ── Ожидание llama-chat ──────────────────────────────────────────────────────
echo "=== Ожидание llama-chat (загрузка модели) ==="
until curl -sf http://localhost:8080/health | grep -q '"status":"ok"'; do
  echo -n "."
  sleep 3
done
echo " готово"

# ── Агент и фронтенд ─────────────────────────────────────────────────────────
echo "=== Запуск агента и фронтенда ==="
docker compose up -d agent frontend nginx

echo ""
echo "Готово. Открыть: http://localhost"
