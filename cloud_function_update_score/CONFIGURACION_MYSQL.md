# ⚙️ Configuración de MySQL para Cloud Function

## 📋 Tablas Requeridas

La Cloud Function necesita acceso a estas tablas. **AJUSTA LOS NOMBRES SEGÚN TU BD:**

### 1. Tabla Principal: `wp_jet_cct_clientes`

**Columnas necesarias:**

```sql
CREATE TABLE IF NOT EXISTS wp_jet_cct_clientes (
  _ID INT PRIMARY KEY AUTO_INCREMENT,
  cl_cedula VARCHAR(50) NOT NULL,
  cl_nombre VARCHAR(255),
  cl_email VARCHAR(255),
  cl_ciudad VARCHAR(100),
  cl_genero CHAR(1),  -- 'M' o 'F'
  cl_edad INT,

  -- Features demográficas (de Experian/HCPN)
  cl_cuota_mensual DECIMAL(15,2),
  cl_creditos_vigentes INT,
  cl_creditos_mora INT,
  cl_hist_neg_12m INT,

  -- Scores calculados
  cl_platam_score DECIMAL(10,2),
  cl_hybrid_score DECIMAL(10,2),
  cl_experian_score DECIMAL(10,2),
  cl_ml_probability_default DECIMAL(5,4),
  cl_ml_risk_level VARCHAR(20),

  -- Scores por componente
  cl_score_payment_performance DECIMAL(10,2),
  cl_score_payment_plan DECIMAL(10,2),
  cl_score_deterioration DECIMAL(10,2),

  -- Pesos usados
  cl_peso_platam DECIMAL(5,2),
  cl_peso_experian DECIMAL(5,2),

  -- Metadatos
  cl_months_as_client INT DEFAULT 0,
  cl_last_update_trigger VARCHAR(50),
  cl_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  INDEX idx_cedula (cl_cedula),
  INDEX idx_modified (cl_modified)
);
```

### 2. Tabla de Pagos: `wp_pagos`

**Columnas necesarias:**

```sql
CREATE TABLE IF NOT EXISTS wp_pagos (
  payment_id INT PRIMARY KEY AUTO_INCREMENT,
  client_cedula VARCHAR(50) NOT NULL,
  payment_date DATE NOT NULL,
  due_date DATE NOT NULL,
  payment_amount DECIMAL(15,2),
  payment_status VARCHAR(50),

  INDEX idx_client_cedula (client_cedula),
  INDEX idx_payment_date (payment_date)
);
```

**La Cloud Function calcula automáticamente:**
- `days_past_due` = `DATEDIFF(payment_date, due_date)`

### 3. Tabla de Planes de Pago: `wp_payment_plans`

**Columnas necesarias:**

```sql
CREATE TABLE IF NOT EXISTS wp_payment_plans (
  plan_id INT PRIMARY KEY AUTO_INCREMENT,
  client_cedula VARCHAR(50) NOT NULL,
  plan_start_date DATE NOT NULL,
  plan_end_date DATE,
  plan_status VARCHAR(50),  -- 'active', 'completed', 'defaulted'
  plan_amount DECIMAL(15,2),

  INDEX idx_client_cedula (client_cedula),
  INDEX idx_plan_status (plan_status)
);
```

---

## 🔧 Ajustar Nombres de Tablas

Si tus tablas tienen nombres diferentes, edita `main.py`:

### Ejemplo 1: Tu tabla de clientes se llama `clientes`

**En `main.py`, línea ~305, buscar:**
```python
FROM wp_jet_cct_clientes
```

**Cambiar a:**
```python
FROM clientes
```

### Ejemplo 2: Tu tabla de pagos se llama `historial_pagos`

**En `main.py`, línea ~340, buscar:**
```python
FROM wp_pagos
```

**Cambiar a:**
```python
FROM historial_pagos
```

### Ejemplo 3: Tus columnas tienen prefijos diferentes

**Si en lugar de `cl_cedula` usas `cliente_cedula`, en `main.py` buscar:**
```python
cl_cedula as cedula,
cl_nombre as client_name,
```

**Cambiar a:**
```python
cliente_cedula as cedula,
cliente_nombre as client_name,
```

---

## 🔐 Credenciales MySQL

### Opción 1: Variables de Entorno (Recomendado)

**Al hacer el deployment, el script `deploy.sh` te pide:**
- `MYSQL_HOST`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DATABASE`

**Estas se guardan como environment variables en la Cloud Function.**

### Opción 2: Cloud SQL Connector (Más seguro)

Si usas **Cloud SQL de GCP**, puedes conectarte vía socket Unix:

**Editar `main.py`:**
```python
# Reemplazar MYSQL_CONFIG por:
MYSQL_CONFIG = {
    'unix_socket': f'/cloudsql/{PROJECT_ID}:{REGION}:{INSTANCE_NAME}',
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': os.getenv('MYSQL_DATABASE'),
    'charset': 'utf8mb4'
}
```

**Y agregar en `deploy.sh`:**
```bash
--set-cloudsql-instances="$PROJECT_ID:$REGION:$INSTANCE_NAME"
```

---

## 🚦 Permitir Conexiones desde Cloud Functions

Cloud Functions usa IPs dinámicas. Dos opciones:

### Opción 1: Permitir rango de IPs de GCP (menos seguro)

**En tu MySQL server, permitir rango de IPs de Cloud Functions:**

```sql
-- Ejemplo para MySQL
CREATE USER 'platam_cf'@'%' IDENTIFIED BY 'strong_password';
GRANT SELECT, UPDATE ON platam_db.* TO 'platam_cf'@'%';
FLUSH PRIVILEGES;
```

**Luego, en tu firewall/security group:**
- Permitir IPs de `us-central1` (rango de GCP)
- Ver lista oficial: https://cloud.google.com/compute/docs/faq#find_ip_range

### Opción 2: VPC Connector (más seguro)

**Crea un VPC Connector:**
```bash
gcloud compute networks vpc-access connectors create platam-connector \
  --region=us-central1 \
  --range=10.8.0.0/28
```

**Editar `deploy.sh`:**
```bash
--vpc-connector=platam-connector \
--egress-settings=private-ranges-only
```

**Ventaja:** MySQL solo necesita permitir IPs del VPC (fijo)

---

## 🧪 Probar Conexión MySQL

### Test 1: Desde tu máquina local

```bash
# Instalar cliente MySQL
brew install mysql  # macOS
apt-get install mysql-client  # Linux

# Conectar
mysql -h TU_HOST -u TU_USUARIO -p platam_db

# Probar query
SELECT _ID, cl_cedula, cl_nombre FROM wp_jet_cct_clientes LIMIT 5;
```

### Test 2: Desde Cloud Function (logs)

**Después de deployment, ver logs:**
```bash
gcloud functions logs read update-client-score \
  --region=us-central1 \
  --gen2 \
  --limit=20
```

**Buscar:**
```
✓ Cliente encontrado: 128282
✓ 25 pagos encontrados
✓ 3 planes encontrados
```

---

## 📊 Queries Optimizadas

### 1. Índices Recomendados

**Para `wp_jet_cct_clientes`:**
```sql
CREATE INDEX idx_id ON wp_jet_cct_clientes(_ID);
CREATE INDEX idx_cedula ON wp_jet_cct_clientes(cl_cedula);
```

**Para `wp_pagos`:**
```sql
CREATE INDEX idx_client_payment ON wp_pagos(client_cedula, payment_date DESC);
```

**Para `wp_payment_plans`:**
```sql
CREATE INDEX idx_client_plan ON wp_payment_plans(client_cedula, plan_start_date DESC);
```

### 2. Limitar Historial (Performance)

La Cloud Function limita queries por defecto:

**Pagos: últimos 100**
```python
LIMIT 100
```

**Si tienes clientes con >100 pagos, considera:**
- Limitar a últimos 6 meses: `WHERE payment_date >= DATE_SUB(NOW(), INTERVAL 6 MONTH)`
- O aumentar límite si tienes suficiente memoria

---

## 🔄 Sincronización con CSV Existente

Actualmente tienes `SCORES_V2_ANALISIS_COMPLETO.csv`. Dos opciones:

### Opción A: Migrar CSV inicial a MySQL (una sola vez)

```python
import pandas as pd
import pymysql

# Leer CSV
df = pd.read_csv('SCORES_V2_ANALISIS_COMPLETO.csv')

# Conectar a MySQL
conn = pymysql.connect(host='...', user='...', password='...', database='...')

# Insertar todos los clientes
for _, row in df.iterrows():
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO wp_jet_cct_clientes
        (cl_cedula, cl_nombre, cl_platam_score, cl_hybrid_score, ...)
        VALUES (%s, %s, %s, %s, ...)
        ON DUPLICATE KEY UPDATE
        cl_platam_score = VALUES(cl_platam_score),
        ...
    """, (row['cedula'], row['client_name'], ...))

conn.commit()
conn.close()
```

### Opción B: Mantener ambos sistemas (batch + real-time)

**Batch (MLBASE.png):** Sigue usando CSV para recalculo masivo semanal

**Real-time (ActualizarML):** Usa Cloud Function para eventos individuales

**Ambos actualizan MySQL, frontend lee de MySQL siempre.**

---

## ⚠️ Consideraciones Importantes

### 1. Transacciones Seguras

La Cloud Function usa `UPDATE` simple. Si necesitas transacciones:

```python
conn = get_db_connection()
cursor = conn.cursor()

try:
    # Iniciar transacción
    conn.begin()

    # Update 1
    cursor.execute("UPDATE ...")

    # Update 2
    cursor.execute("UPDATE ...")

    # Commit si todo OK
    conn.commit()
except Exception as e:
    conn.rollback()
    raise e
finally:
    conn.close()
```

### 2. Manejo de Concurrencia

Si dos triggers llegan simultáneamente para el mismo cliente:

**Problema:** Race condition → scores inconsistentes

**Solución:** Usar `SELECT ... FOR UPDATE`:

```python
cursor.execute(f"""
    SELECT _ID FROM wp_jet_cct_clientes
    WHERE _ID = {client_id}
    FOR UPDATE
""")
# Ahora el registro está bloqueado hasta el UPDATE
```

### 3. Retry Logic

Si MySQL está temporalmente no disponible:

**Agregar retry en `main.py`:**
```python
import time

def get_db_connection_with_retry(max_retries=3):
    for attempt in range(max_retries):
        try:
            return pymysql.connect(**MYSQL_CONFIG)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise e
```

---

## 📝 Checklist de Verificación

- [ ] Tablas MySQL creadas con todas las columnas necesarias
- [ ] Índices creados en `_ID`, `cl_cedula`, `client_cedula`
- [ ] Usuario MySQL creado con permisos `SELECT`, `UPDATE`
- [ ] Firewall MySQL permite IPs de Cloud Functions
- [ ] Probado conexión desde local con mismas credenciales
- [ ] Nombres de tablas/columnas actualizados en `main.py`
- [ ] Variables de entorno configuradas en Cloud Function

---

## 🆘 Errores Comunes

### Error: "Unknown column 'cl_ciudad'"

**Causa:** Tu tabla no tiene esa columna

**Solución:**
- O agregar la columna: `ALTER TABLE wp_jet_cct_clientes ADD cl_ciudad VARCHAR(100);`
- O comentar en `main.py`: `# cl_ciudad as ciudad,`

### Error: "Access denied for user"

**Causa:** Permisos insuficientes

**Solución:**
```sql
GRANT SELECT, UPDATE ON platam_db.wp_jet_cct_clientes TO 'platam_cf'@'%';
GRANT SELECT ON platam_db.wp_pagos TO 'platam_cf'@'%';
GRANT SELECT ON platam_db.wp_payment_plans TO 'platam_cf'@'%';
FLUSH PRIVILEGES;
```

### Error: "Can't connect to MySQL server"

**Causa:** Firewall bloqueando

**Solución:**
- Verificar que IP de Cloud Function está permitida
- Probar con `telnet TU_HOST 3306` desde Cloud Shell

---

**✅ Configuración MySQL completada. Ahora puedes deployar la Cloud Function!**
