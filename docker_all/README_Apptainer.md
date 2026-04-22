# WebMall Apptainer Setup (HPC)

This guide replaces the Docker-based setup with [Apptainer](https://apptainer.org/) for use on HPC clusters where Docker is unavailable. Apptainer is rootless and widely supported on academic HPC systems.

## Key Differences from Docker

| Docker | Apptainer |
|--------|-----------|
| Named volumes | Bind-mounted directories on the filesystem |
| Docker network (container-to-container hostnames) | Host network (all containers share localhost) |
| `docker compose up` | Individual `apptainer instance start` commands |
| `docker exec` | `apptainer exec instance://<name>` |
| Port conflicts managed by Compose | MariaDB instances need different host ports (3307–3310) |

Because all Apptainer instances share the host network namespace, you cannot use container names (e.g. `mariadb_shop1`) as hostnames. Instead, each MariaDB instance listens on a unique port on `localhost`.

## Prerequisites

- Apptainer 1.1+ (`apptainer --version`)
- At least 20GB of scratch space for images and data
- Ports 8081–8084, 3307–3310, 9200, and your chosen frontend port available

## Setup

### 1. Fix OpenSSL (required on many HPC clusters)

```bash
export OPENSSL_CONF=/dev/null
```

Add this to your `~/.bashrc` or job script so it persists.

### 2. Environment Configuration

```bash
cp ../.env.example ../.env
cp .env.example .env
```

Edit `../.env` and set the shop ports. The defaults (8081–8084) are fine if those ports are free on your compute node.

### 3. Pull Container Images

Pull all images once and save them as `.sif` files. This avoids re-downloading on every run.

```bash
cd docker_all
mkdir -p sif

apptainer pull sif/mariadb.sif     docker://bitnami/mariadb:latest
apptainer pull sif/wordpress.sif   docker://bitnami/wordpress:latest
apptainer pull sif/elasticsearch.sif docker://docker.elastic.co/elasticsearch/elasticsearch:8.10.2
apptainer pull sif/nginx.sif       docker://nginx:latest
```

This may take a while. Do it on a compute node if your cluster restricts network access on login nodes.

### 4. Create Data Directories (replacing Docker volumes)

```bash
mkdir -p apptainer_data/{wordpress,mariadb}_data_shop{1,2,3,4} apptainer_data/esdata
```

### 5. Download and Restore Backup Data

```bash
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
```

### 6. Start All Services

Each MariaDB instance uses a unique port (3307–3310) to avoid conflicts on the shared host network.

#### Elasticsearch

```bash
apptainer instance start \
  --env discovery.type=single-node \
  --env xpack.security.enabled=false \
  --env "ES_JAVA_OPTS=-Xms512m -Xmx512m -XX:UseSVE=0" \
  --bind apptainer_data/esdata:/usr/share/elasticsearch/data \
  sif/elasticsearch.sif \
  elasticsearch
```

#### MariaDB instances (shops 1–4)

```bash
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
```

#### WordPress instances (shops 1–4)

```bash
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
```

#### Frontend (Nginx)

```bash
source ../.env
apptainer instance start \
  --bind ./index.html:/usr/share/nginx/html/index.html \
  sif/nginx.sif \
  webmall_frontend
```

### 7. Wait and Fix URLs

```bash
source ../.env
sleep 30   # Wait for WordPress to initialize

apptainer exec instance://wordpress_shop1 /bin/bash -c \
  "/usr/local/bin/fix_urls_deploy.sh 'https://webmall-1.informatik.uni-mannheim.de/' 'http://localhost:${SHOP1_PORT}'"
apptainer exec instance://wordpress_shop2 /bin/bash -c \
  "/usr/local/bin/fix_urls_deploy.sh 'https://webmall-2.informatik.uni-mannheim.de/' 'http://localhost:${SHOP2_PORT}'"
apptainer exec instance://wordpress_shop3 /bin/bash -c \
  "/usr/local/bin/fix_urls_deploy.sh 'https://webmall-3.informatik.uni-mannheim.de/' 'http://localhost:${SHOP3_PORT}'"
apptainer exec instance://wordpress_shop4 /bin/bash -c \
  "/usr/local/bin/fix_urls_deploy.sh 'https://webmall-4.informatik.uni-mannheim.de/' 'http://localhost:${SHOP4_PORT}'"
```

### 8. Verify Installation

After starting, access:

- **Shop 1**: http://localhost:8081 (or your configured SHOP1_PORT)
- **Shop 2**: http://localhost:8082
- **Shop 3**: http://localhost:8083
- **Shop 4**: http://localhost:8084
- **Frontend**: http://localhost:3000 (or your FRONTEND_PORT)
- **Elasticsearch**: http://localhost:9200

## Container Management

### List Running Instances

```bash
apptainer instance list
```

### Stop All Instances

```bash
for shop in 1 2 3 4; do
  apptainer instance stop wordpress_shop${shop}
  apptainer instance stop mariadb_shop${shop}
done
apptainer instance stop elasticsearch
apptainer instance stop webmall_frontend
```

### View Logs

Apptainer instance logs are written to `~/.apptainer/instances/logs/`:

```bash
# Logs for a specific instance
cat ~/.apptainer/instances/logs/$(hostname)/$(whoami)/wordpress_shop1.out
cat ~/.apptainer/instances/logs/$(hostname)/$(whoami)/wordpress_shop1.err
```

### Execute Commands Inside an Instance

```bash
apptainer exec instance://wordpress_shop1 wp core is-installed --path=/opt/bitnami/wordpress
```

### Reset Password

```bash
apptainer exec instance://wordpress_shop1 \
  wp user update admin --user_pass='choose-a-new-password' --path=/opt/bitnami/wordpress
```

## Troubleshooting

### OpenSSL Error on Playwright / Apptainer Pull

```bash
export OPENSSL_CONF=/dev/null
```

### Port Already in Use

Check what is using the port:
```bash
netstat -tulpn | grep :8081
# or
ss -tulpn | grep :8081
```

Update `../.env` with free ports and re-run the WordPress instance start commands.

### MariaDB Port Conflicts

If ports 3307–3310 are taken, change `MARIADB_PORT=$((3306 + shop))` in the startup commands to any available port range and use the same values in `WORDPRESS_DATABASE_PORT_NUMBER`.

### WordPress Can't Connect to MariaDB

Bitnami images may not support `WORDPRESS_DATABASE_PORT_NUMBER` in all versions. If WordPress fails to connect, confirm the MariaDB instance is running and the port is correct:

```bash
apptainer instance list
curl http://localhost:3307   # Should get a response (or TCP error, not "Connection refused")
```

### Permission Issues on Data Directories

Apptainer runs as your user. If backup extraction leaves files owned by root (e.g. from a previous Docker run), fix with:

```bash
chmod -R u+rw apptainer_data/
```

### Fakeroot (if Bitnami images require root internally)

Some Bitnami images expect to run internal setup scripts as root. If an instance fails to start, try adding `--fakeroot` to the `apptainer instance start` command. Check whether your cluster admin has enabled fakeroot for your account:

```bash
apptainer config fakeroot --list
```

### Reset Everything

```bash
# Stop all instances
for shop in 1 2 3 4; do
  apptainer instance stop wordpress_shop${shop} 2>/dev/null || true
  apptainer instance stop mariadb_shop${shop}   2>/dev/null || true
done
apptainer instance stop elasticsearch 2>/dev/null || true
apptainer instance stop webmall_frontend 2>/dev/null || true

# Delete data (WARNING: deletes all shop data)
rm -rf apptainer_data/

# Start fresh from Step 4
```

## Running on a Compute Node (Recommended)

HPC login nodes are often restricted. Run the shops on a compute node with a long-running job:

```bash
# Example SLURM job (adjust as needed for your cluster)
srun --time=24:00:00 --mem=16G --cpus-per-task=8 --pty bash

# Then inside the job, run the startup commands above
cd /path/to/WebMall/docker_all
source ../.env
# ... start instances ...
```

The agent benchmark (run from another terminal) can connect to the shops via the compute node's hostname or via SSH port forwarding.

## Architecture

Same as the Docker setup, but running as Apptainer instances on the host network:

- **4 WordPress Shops**: Bitnami WordPress SIF, ports 8081–8084
- **4 MariaDB Databases**: Bitnami MariaDB SIF, ports 3307–3310 (host-local)
- **Elasticsearch**: Elasticsearch SIF, port 9200
- **Frontend**: Nginx SIF, port 3000
- **Networking**: Host network (no virtual Docker bridge needed)

## File Structure

```
docker_all/
├── sif/                            # Apptainer SIF image files (pulled once)
│   ├── mariadb.sif
│   ├── wordpress.sif
│   ├── elasticsearch.sif
│   └── nginx.sif
├── apptainer_data/                 # Persistent data (replaces Docker volumes)
│   ├── wordpress_data_shop[1-4]/
│   ├── mariadb_data_shop[1-4]/
│   └── esdata/
├── backup/                         # Downloaded backup archives
├── deployed_wp_config_local/       # WordPress configuration templates
├── fix_urls.sh
├── fix_urls_deploy.sh
├── index.html
├── README.md                       # Original Docker setup guide
└── README_Apptainer.md             # This file
```
