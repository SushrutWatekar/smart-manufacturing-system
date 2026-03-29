# Use the official Nginx image as the base image
FROM nginx:alpine

# Set the working directory to /usr/share/nginx/html
WORKDIR /usr/share/nginx/html

# Remove the default Nginx static files
RUN rm -rf ./*

# Copy static files (index.html, scripts.js, styles.css) from the current directory to the container
COPY . .

# Expose port 80 to allow traffic to the container
EXPOSE 80

# Start Nginx server
CMD ["nginx", "-g", "daemon off;"]
