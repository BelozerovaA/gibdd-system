FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG REACT_APP_API_URL=/api
ARG REACT_APP_FOUND_PROMPT_DELAY_MS=60000
ENV REACT_APP_API_URL=$REACT_APP_API_URL \
    REACT_APP_FOUND_PROMPT_DELAY_MS=$REACT_APP_FOUND_PROMPT_DELAY_MS \
    GENERATE_SOURCEMAP=false \
    CI=false
RUN npm run build
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80
HEALTHCHECK --interval=10s --timeout=5s --retries=6 \
    CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
