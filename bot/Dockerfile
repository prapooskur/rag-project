FROM node:24-alpine

# COPY . /app
WORKDIR /app

# stage 1 install deps
COPY package.json /app
COPY pnpm-lock.yaml /app
RUN corepack enable && corepack prepare pnpm@latest --activate
RUN pnpm install
RUN pnpm install typescript

# stage 2 compile
COPY . /app
RUN pnpm exec tsc

CMD ["pnpm", "run", "start"]