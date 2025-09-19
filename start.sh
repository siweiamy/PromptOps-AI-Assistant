#!/bin/bash

# Source credentials from Vault
if [ -f /vault/secrets/config ]; then
  . /vault/secrets/config
fi

exec gunicorn --bind 0.0.0.0:${PORT:-5000} app:app
