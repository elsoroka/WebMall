echo "#### Elasticsearch instance ####"

apptainer instance start \
  --env discovery.type=single-node \
  --env xpack.security.enabled=false \
  --env "ES_JAVA_OPTS=-Xms512m -Xmx512m -XX:UseSVE=0" \
  --bind apptainer_data/esdata:/usr/share/elasticsearch/data \
  sif/elasticsearch.sif \
  elasticsearch

echo "#### MariaDB instances (shops 1–4) ####"

for shop in 1 2 3 4; do
  MARIADB_PORT=$((3306 + shop))   # 3307, 3308, 3309, 3310
  apptainer instance start \
    --env MARIADB_ROOT_PASSWORD=rootpassword \
    --env MARIADB_USER=bn_wordpress \
    --env MARIADB_PASSWORD=wordpress_db_password \
    --env MARIADB_DATABASE=bitnami_wordpress \
    --env MARIADB_PORT_NUMBER=${MARIADB_PORT} \
    --bind apptainer_data/mariadb_data_shop${shop}:/bitnami/mariadb \
    sif/mariadb.sif \
    mariadb_shop${shop}
done

echo "#### WordPress instances (shops 1–4) ####"

source ../.env

for shop in 1 2 3 4; do
  MARIADB_PORT=$((3306 + shop))
  SHOP_PORT_VAR="SHOP${shop}_PORT"
  SHOP_PORT=${!SHOP_PORT_VAR}

  apptainer instance start \
    --env WORDPRESS_DATABASE_HOST=localhost \
    --env WORDPRESS_DATABASE_PORT_NUMBER=${MARIADB_PORT} \
    --env WORDPRESS_DATABASE_USER=bn_wordpress \
    --env WORDPRESS_DATABASE_PASSWORD=wordpress_db_password \
    --env WORDPRESS_DATABASE_NAME=bitnami_wordpress \
    --env WORDPRESS_USERNAME=admin \
    --env WORDPRESS_PASSWORD=admin \
    --env WORDPRESS_EMAIL=user@example.com \
    --env WORDPRESS_HTTP_PORT_NUMBER=${SHOP_PORT} \
    --env "WORDPRESS_CONFIG_EXTRA=define('EP_HOST','http://localhost:9200'); define('EP_INDEX_PREFIX','shop${shop}_');" \
    --bind apptainer_data/wordpress_data_shop${shop}:/bitnami/wordpress \
    --bind ./fix_urls.sh:/usr/local/bin/fix_urls.sh \
    --bind ./fix_urls_deploy.sh:/usr/local/bin/fix_urls_deploy.sh \
    sif/wordpress.sif \
    wordpress_shop${shop}
done

echo "#### Frontend (Nginx) ####"

source ../.env
apptainer instance start \
  --bind ./index.html:/usr/share/nginx/html/index.html \
  sif/nginx.sif \
  webmall_frontend