FROM registry.cn-hangzhou.aliyuncs.com/library/node:20-alpine AS builder
WORKDIR /app

RUN npm config set registry https://registry.npmmirror.com

COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM registry.cn-hangzhou.aliyuncs.com/library/nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
