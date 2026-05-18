#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python3"
VENV_PIP="$ROOT_DIR/.venv/bin/pip"
BOOTSTRAP_STAMP="$ROOT_DIR/.venv/.bootstrap-complete"
BOOTSTRAP_LOCK_DIR="$ROOT_DIR/.venv/.bootstrap-lock"

require_system_tool() {
  local tool_name="$1"
  local install_hint="$2"

  if ! command -v "$tool_name" >/dev/null 2>&1; then
    echo "Error: missing required system tool: $tool_name" >&2
    echo "$install_hint" >&2
    exit 1
  fi
}

ensure_venv() {
  if [[ -x "$VENV_PYTHON" ]]; then
    return
  fi

  echo "Creating virtual environment at $VENV_DIR ..."
  python3 -m venv "$VENV_DIR"
}

bootstrap_python_dependencies() {
  echo "Installing Python dependencies into $VENV_DIR ..."
  "$VENV_PIP" install -r "$ROOT_DIR/requirements.txt"
  touch "$BOOTSTRAP_STAMP"
}

needs_bootstrap() {
  if [[ ! -f "$BOOTSTRAP_STAMP" ]]; then
    return 0
  fi

  if [[ "$ROOT_DIR/requirements.txt" -nt "$BOOTSTRAP_STAMP" ]]; then
    return 0
  fi
  return 1
}

with_bootstrap_lock() {
  local waited=0

  while ! mkdir "$BOOTSTRAP_LOCK_DIR" 2>/dev/null; do
    if [[ -f "$BOOTSTRAP_STAMP" ]] && ! needs_bootstrap; then
      return
    fi
    waited=1
    sleep 1
  done

  trap 'rmdir "$BOOTSTRAP_LOCK_DIR" 2>/dev/null || true' EXIT

  if [[ $waited -eq 1 ]]; then
    echo "Another setup is in progress, continuing after lock release ..."
  fi

  if needs_bootstrap; then
    bootstrap_python_dependencies
  fi

  rmdir "$BOOTSTRAP_LOCK_DIR" 2>/dev/null || true
  trap - EXIT
}

is_help_only() {
  if [[ $# -eq 0 ]]; then
    return 1
  fi

  for arg in "$@"; do
    if [[ "$arg" != "-h" && "$arg" != "--help" ]]; then
      return 1
    fi
  done

  return 0
}

require_system_tool "python3" "Install Python 3.10+ first."
require_system_tool "ffmpeg" "Install it with: brew install ffmpeg"
require_system_tool "ffprobe" "Install it with: brew install ffmpeg"
require_system_tool "auto-editor" "Install it with: brew install auto-editor"

ensure_venv
with_bootstrap_lock

export PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

exec "$VENV_PYTHON" -m video_roughcut.cli "$@"
