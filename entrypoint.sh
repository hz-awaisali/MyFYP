#!/usr/bin/env bash
set -e

# Run database migrations on startup (idempotent). Coolify can also run this
# as a one-shot pre-deploy command instead.
echo "Running database migrations..."
alembic upgrade head

# Optionally seed baseline data when SEED_ON_START=true.
if [ "${SEED_ON_START:-false}" = "true" ]; then
  echo "Seeding baseline data..."
  python -m scripts.seed
fi

echo "Starting application..."
exec "$@"
