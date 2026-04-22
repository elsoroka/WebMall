for shop in 1 2 3 4; do
  apptainer instance stop wordpress_shop${shop}
  apptainer instance stop mariadb_shop${shop}
done
apptainer instance stop elasticsearch
apptainer instance stop webmall_frontend
