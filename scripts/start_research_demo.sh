#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

python -m pip install -e '.[servers,openai]' >/dev/null

if [[ ! -f data/Chinook.sqlite ]]; then
  mkdir -p data
  curl --fail --location --silent --show-error \
    https://vanna.ai/Chinook.sqlite \
    --output data/Chinook.sqlite
fi

if [[ ! -f frontends/webcomponent/node_modules/.bin/vite ]]; then
  npm --prefix frontends/webcomponent install
fi
npm --prefix frontends/webcomponent run build >/dev/null

exec python -m vanna.servers \
  --dev \
  --static-folder frontends/webcomponent/dist \
  --host 0.0.0.0 \
  --port "${PORT:-8000}"