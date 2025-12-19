# Configuración

## Setup Inicial

1. Copia `.env.template` a `.env`:
   ```bash
   cp config/.env.template config/.env
   ```

2. Edita `config/.env` con tus credenciales reales de AWS

3. IMPORTANTE: `.env` está en `.gitignore` - nunca lo subas a Git

4. Verifica que tienes acceso a los buckets S3:
   ```bash
   python scripts/test_aws_connection.py
   ```

## Secrets de AWS

Necesitas permisos para:
- `s3:GetObject` en bucket `platam-hcpn`
- `s3:ListBucket` en bucket `platam-hcpn`
- `s3:PutObject` en bucket `platam-ml-data` (si vas a subir CSVs)

## Variables de Entorno

- `AWS_ACCESS_KEY_ID`: Access key de usuario IAM con permisos S3
- `AWS_SECRET_ACCESS_KEY`: Secret key correspondiente
- `S3_HCPN_BUCKET`: Nombre del bucket donde están los HCPN
- `S3_DATA_BUCKET`: Nombre del bucket donde subirás los CSVs procesados
