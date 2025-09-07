# Stage 1: Build the client application
FROM node:18-alpine as client-builder

# Set the working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json first to cache dependencies
COPY package*.json ./

# Install dependencies (using `npm ci` for clean install based on lock file)
RUN npm ci --silent

# Copy ALL necessary files for the build
COPY ./src ./src
COPY ./public ./public
COPY index.html ./
COPY vite.config.js ./
COPY postcss.config.js ./
COPY tailwind.config.js ./

# Build the application
RUN npm run build

# Stage 2: Serve the production build
FROM nginx:alpine as client-production

# Copy the built files from the previous stage into the Nginx directory
COPY --from=client-builder /app/dist /usr/share/nginx/html

# Copy nginx configuration if it exists
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port 80 for the Nginx server
EXPOSE 80

# Command to run Nginx when the container starts
CMD ["nginx", "-g", "daemon off;"]
