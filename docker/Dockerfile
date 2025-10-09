# Use Node base and install Python for orchestrator
FROM node:20-bullseye as base

# Install Python 3 and pip
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

# Install root JS dev tool (concurrently)
RUN npm ci

# Entrypoint script to generate and run
RUN printf '#!/usr/bin/env bash\nset -e\nPROMPT="${DEMO_PROMPT:-Build a sample app with a list and API}"\npython3 /app/main.py --prompt "$PROMPT" --output output\n# install deps\nif [ -f /app/output/backend/app/package.json ]; then npm --prefix /app/output/backend/app ci; fi\nif [ -f /app/output/frontend/app/package.json ]; then npm --prefix /app/output/frontend/app ci; fi\n# run both\nexec npm run dev\n' > /usr/local/bin/start-autodevos && chmod +x /usr/local/bin/start-autodevos

EXPOSE 3000 5173
CMD ["/usr/local/bin/start-autodevos"]
