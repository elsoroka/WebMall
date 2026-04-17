source ../.env

mkdir -p backup
BACKUP_URL="https://data.dws.informatik.uni-mannheim.de/webmall/backup"
for shop in 1 2 3 4; do
  for type in wordpress mariadb; do
    file="${type}_data_shop${shop}.tar.gz"
    if [ ! -f "backup/${file}" ]; then
      echo "Downloading ${file}..."
      curl -L --progress-bar "${BACKUP_URL}/${file}" -o "backup/${file}"
    fi
  done
done

# Extract backups directly into data directories (no busybox needed)
for shop in 1 2 3 4; do
  echo "Restoring shop ${shop}..."
  tar xzf backup/wordpress_data_shop${shop}.tar.gz -C apptainer_data/wordpress_data_shop${shop}
  tar xzf backup/mariadb_data_shop${shop}.tar.gz   -C apptainer_data/mariadb_data_shop${shop}

  # Patch wp-config.php with the correct port for this shop
  SHOP_PORT_VAR="SHOP${shop}_PORT"
  SHOP_PORT_VALUE="${!SHOP_PORT_VAR}"
  sed "s/SHOP${shop}_PORT_PLACEHOLDER/${SHOP_PORT_VALUE}/g" \
    deployed_wp_config_local/shop_${shop}.php \
    > apptainer_data/wordpress_data_shop${shop}/wp-config.php
done