#!/bin/bash
set -e  # Exit immediately if any command exits with a non-zero status.

# LOAD the .env file
source ../.env

chmod +x fix_urls.sh
BACKUP_DIR="$(pwd)/backup"
CONFIG_DIR="$(pwd)/deployed_wp_config_local"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

echo "=== Downloading backup files from remote server ==="
BACKUP_URL="https://data.dws.informatik.uni-mannheim.de/webmall/backup"

# List of files to download
FILES=(
  "mariadb_data_shop1.tar.gz"
  "mariadb_data_shop2.tar.gz"
  "mariadb_data_shop3.tar.gz"
  "mariadb_data_shop4.tar.gz"
  "wordpress_data_shop1.tar.gz"
  "wordpress_data_shop2.tar.gz"
  "wordpress_data_shop3.tar.gz"
  "wordpress_data_shop4.tar.gz"
)

# Download each file if it doesn't already exist
for file in "${FILES[@]}"; do
  if [ ! -f "${BACKUP_DIR}/${file}" ]; then
    echo "Downloading ${file}..."
    curl -L --progress-bar "${BACKUP_URL}/${file}" -o "${BACKUP_DIR}/${file}"
    echo "Downloaded ${file}"
  else
    echo "${file} already exists, skipping download"
  fi
done

echo "=== All backup files downloaded successfully ==="

# Function to restore a single shop
restore_shop() {
  SHOP_ID=$1
  WORDPRESS_VOLUME="woocommerce_wordpress_data_shop${SHOP_ID}"
  MARIADB_VOLUME="woocommerce_mariadb_data_shop${SHOP_ID}"

  echo "=== Creating Docker Volumes for Shop ${SHOP_ID} (if not already created) ==="
  docker volume create ${WORDPRESS_VOLUME} || true
  docker volume create ${MARIADB_VOLUME} || true

  echo "=== Restoring WordPress Volume Data for Shop ${SHOP_ID} ==="
  docker run --rm \
    -v ${WORDPRESS_VOLUME}:/volume \
    -v "${BACKUP_DIR}":/backup \
    busybox \
    tar xzf /backup/wordpress_data_shop${SHOP_ID}.tar.gz -C /volume

    echo "=== Copying the wpconfig.php file for Shop ${SHOP_ID} ==="
    
    # Create temporary config file with port replacement
    TEMP_CONFIG="/tmp/shop_${SHOP_ID}_temp.php"
    SHOP_PORT_VAR="SHOP${SHOP_ID}_PORT"
    SHOP_PORT_VALUE="${!SHOP_PORT_VAR}"
    
    # Replace placeholder with actual port value
    sed "s/SHOP${SHOP_ID}_PORT_PLACEHOLDER/${SHOP_PORT_VALUE}/g" "${CONFIG_DIR}/shop_${SHOP_ID}.php" > "${TEMP_CONFIG}"
    
    docker run --rm \
        -v ${WORDPRESS_VOLUME}:/volume \
        -v "/tmp":/temp_config \
        busybox \
        cp /temp_config/shop_${SHOP_ID}_temp.php /volume/wp-config.php
    
    # Clean up temporary file
    rm "${TEMP_CONFIG}"

  echo "=== Restoring MariaDB Volume Data for Shop ${SHOP_ID} ==="
  docker run --rm \
    -v ${MARIADB_VOLUME}:/volume \
    -v "${BACKUP_DIR}":/backup \
    busybox \
    tar xzf /backup/mariadb_data_shop${SHOP_ID}.tar.gz -C /volume

}

# Restore data for all four shops
for SHOP in 1 2 3 4; do
  restore_shop ${SHOP}
done

echo "=== Starting Containers with Docker Compose ==="
docker compose --env-file ../.env up -d

echo "=== Waiting for all containers to be healthy ==="
sleep 5


echo "=== Fixing URLs ==="
docker exec WebMall_wordpress_shop1 /bin/bash -c "/usr/local/bin/fix_urls_deploy.sh  'https://webmall-1.informatik.uni-mannheim.de/'  'http://localhost:${SHOP1_PORT}'"
docker exec WebMall_wordpress_shop2 /bin/bash -c "/usr/local/bin/fix_urls_deploy.sh  'https://webmall-2.informatik.uni-mannheim.de/'  'http://localhost:${SHOP2_PORT}'"
docker exec WebMall_wordpress_shop3 /bin/bash -c "/usr/local/bin/fix_urls_deploy.sh 'https://webmall-3.informatik.uni-mannheim.de/'  'http://localhost:${SHOP3_PORT}'"
docker exec WebMall_wordpress_shop4 /bin/bash -c "/usr/local/bin/fix_urls_deploy.sh 'https://webmall-4.informatik.uni-mannheim.de/'  'http://localhost:${SHOP4_PORT}'"

# Restart the containers to apply the new config
docker compose --env-file ../.env restart
