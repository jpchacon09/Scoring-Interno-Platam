# Comparación Visual: Score PLATAM vs Score Experian

**Versión simple y visual** - 6 gráficos con explicaciones claras

---

## 📊 Gráfico 1: ¿Dónde están los clientes?

![Scatter con zonas](charts/01_scatter_zonas.png)

### ¿Qué muestra este gráfico?

Cada **punto azul = 1 cliente**. El gráfico compara su score PLATAM (eje vertical) vs su score Experian (eje horizontal).

### ¿Cómo leerlo?

- **Línea negra diagonal:** Igualdad perfecta (si un cliente está aquí, ambos scores son iguales)
- **Zona verde:** Diferencia aceptable (±100 puntos entre scores)
- **Puntos ABAJO de la línea (zona roja):** PLATAM es más estricto que Experian
- **Puntos ARRIBA de la línea (zona verde clara):** PLATAM es más generoso que Experian

### Color de los puntos:
- **Verde:** Scores muy similares (poca diferencia)
- **Amarillo/Naranja:** Diferencia moderada
- **Rojo:** Gran diferencia entre scores

### ¿Qué vemos?

**La mayoría de los puntos están DEBAJO de la línea negra** → PLATAM es más estricto que Experian.

**Correlación: 0.263** → Muy baja. Significa que los scores están midiendo cosas MUY diferentes.

---

## 📊 Gráfico 2: ¿Qué dice Experian de tus ratings PLATAM?

![Promedios por rating](charts/02_promedios_por_rating.png)

### ¿Qué muestra este gráfico?

Para cada rating que da PLATAM (A+, A, B, C, D, F), muestra:
- **Barra azul:** Score promedio PLATAM de clientes con ese rating
- **Barra roja:** Score promedio Experian de los MISMOS clientes
- **n=XX:** Cantidad de clientes en cada rating

### ¿Cómo leerlo?

Compara las dos barras en cada rating. Si la barra roja (Experian) es mucho más alta que la azul (PLATAM), significa que Experian ve a esos clientes como MEJOR riesgo.

### ¿Qué vemos?

**PROBLEMA:** Los clientes con rating D, D+ y F según PLATAM tienen score Experian promedio de **~650-750** (¡Bueno!).

Esto significa que **PLATAM está siendo muy duro** con clientes que Experian considera buenos.

**Ejemplo:**
- Rating PLATAM D: Score PLATAM promedio = 414
- Pero su Experian promedio = 665 (¡Bueno!)

---

## 📊 Gráfico 3: ¿Quién es más estricto?

![Histograma de diferencias](charts/03_diferencias_histogram.png)

### ¿Qué muestra este gráfico?

La **diferencia** entre scores: PLATAM - Experian

### ¿Cómo leerlo?

- **Eje X (horizontal):**
  - Negativo = PLATAM más bajo que Experian (más estricto)
  - Positivo = PLATAM más alto que Experian (más generoso)
  - Cero = Iguales

- **Eje Y (vertical):** Cantidad de clientes

### Colores:
- **Rojo:** PLATAM mucho más bajo (-100 o menos)
- **Naranja:** PLATAM ligeramente más bajo
- **Verde:** Similares (±100 puntos)
- **Azul:** PLATAM más alto

### ¿Qué vemos?

**La mayoría del gráfico está del lado IZQUIERDO (negativo)** = PLATAM más estricto.

**Línea verde (promedio): -140.6 puntos** → En promedio, PLATAM da 140 puntos MENOS que Experian.

**Estadísticas en el recuadro:**
- **47.2% de clientes:** PLATAM -100 o menos (mucho más estricto)
- **30.5% de clientes:** Similar (±100)
- **6.7% de clientes:** PLATAM +100 o más (más generoso)

**Conclusión:** PLATAM es MUCHO más conservador que Experian.

---

## 📊 Gráfico 4: Distribuciones Completas

![Boxplot comparativo](charts/04_boxplot_comparativo.png)

### ¿Qué muestra este gráfico?

Las "cajas" muestran toda la distribución de scores.

### ¿Cómo leerlo?

- **Línea roja (gruesa):** Mediana (el punto medio - 50% arriba, 50% abajo)
- **Línea verde (punteada):** Media (promedio)
- **Caja:** 50% de los clientes están aquí (del percentil 25 al 75)
- **Líneas verticales:** Rango de variación (hasta los extremos)

### ¿Qué vemos?

**Caja azul (PLATAM):** Más baja y compacta
- Media: 622 puntos
- Mediana: 660 puntos

**Caja roja (Experian):** Más alta y dispersa
- Media: 762 puntos
- Mediana: 812 puntos

**Gap:** ~140 puntos de diferencia en promedio.

**Conclusión:** Toda la distribución de PLATAM está desplazada hacia ABAJO comparada con Experian.

---

## 📊 Gráfico 5: Casos Extremos

![Casos extremos](charts/05_casos_extremos.png)

### ¿Qué muestra este gráfico?

Los **Top 10** casos más extremos en cada dirección:
- **Izquierda:** Clientes donde PLATAM es MUCHO más bajo que Experian
- **Derecha:** Clientes donde PLATAM es MUCHO más alto que Experian

### ¿Cómo leerlo?

Cada fila = 1 cliente (anónimo).
- **Barra roja:** Su score Experian
- **Barra azul:** Su score PLATAM
- **Δ = Diferencia**

### ¿Qué vemos?

**Lado izquierdo (PLATAM más bajo):**
- Diferencias de hasta **-600 puntos**
- Ejemplo: Cliente 1 tiene Experian ~830 pero PLATAM ~230
- **Problema:** Clientes con buen historial externo (Experian alto) pero poca actividad interna reciben score PLATAM muy bajo

**Lado derecho (PLATAM más alto):**
- Diferencias de hasta **+300 puntos**
- Ejemplo: Cliente con Experian ~500 pero PLATAM ~800
- **Explicación:** Clientes con mal historial externo pero excelente comportamiento interno reciente

**Conclusión:** Los extremos muestran que PLATAM y Experian están evaluando aspectos MUY diferentes del riesgo.

---

## 📊 Gráfico 6: ¿Coinciden las Categorías?

![Mapa de categorización](charts/06_mapa_categorizacion.png)

### ¿Qué muestra este gráfico?

Tabla cruzada de categorías. Agrupa scores en 4 categorías:
- **Excelente:** 800+ puntos
- **Bueno:** 650-799 puntos
- **Regular:** 500-649 puntos
- **Malo:** <500 puntos

### ¿Cómo leerlo?

- **Filas:** Categoría según PLATAM
- **Columnas:** Categoría según Experian
- **Números:** Cantidad de clientes en cada combinación
- **Cuadros azules (diagonal):** Coincidencia perfecta - ambos scores dan la misma categoría

### ¿Qué vemos?

**Diagonal (coincidencias):**
- Excelente-Excelente: 68 clientes
- Bueno-Bueno: 378 clientes
- Regular-Regular: 96 clientes
- Malo-Malo: 11 clientes

**Total coincidencias: ~553 clientes (35.5%)**

**PROBLEMA - Fuera de la diagonal:**

**Casos donde PLATAM dice "Malo" pero Experian dice "Bueno": 189 clientes**
- Estos clientes están siendo rechazados o limitados por PLATAM
- Pero Experian los ve como buen riesgo

**Casos donde PLATAM dice "Regular" pero Experian dice "Bueno": 192 clientes**

**Conclusión:**
- Solo **35.5% de clientes** caen en la misma categoría
- **64.5% tienen desacuerdo** entre PLATAM y Experian
- Principalmente, PLATAM categoriza MÁS BAJO que Experian

---

## 🎯 Resumen de los 6 Gráficos

### Principales Hallazgos:

1. **PLATAM es ~140 puntos más estricto** que Experian en promedio (Gráfico 3)

2. **Baja correlación (0.263)** - Los scores miden cosas muy diferentes (Gráfico 1)

3. **47% de clientes penalizados excesivamente** - PLATAM -150 puntos o más vs Experian (Gráfico 3)

4. **Clientes con rating D/F en PLATAM tienen Experian ~660** (Bueno) (Gráfico 2)

5. **Casos extremos** muestran diferencias de hasta 600 puntos (Gráfico 5)

6. **Solo 35% de coincidencia** en categorías (Gráfico 6)

### ¿Por qué pasa esto?

**PLATAM está penalizando mucho a clientes que:**
- Tienen poca frecuencia de compras (componente Purchase Consistency)
- Usan poco su cupo (componente Utilization)
- Tienen poco historial interno (pocos pagos registrados)

**PERO** estos clientes pueden tener excelente historial externo (Experian alto).

### ¿Qué hacer?

1. **Ajustar componentes débiles** (Purchase Consistency y Utilization)
2. **No penalizar tanto** por baja frecuencia o baja utilización
3. **Crear score híbrido:** Combinar PLATAM + Experian
4. **Dar más peso a Experian** cuando el cliente tiene poco historial interno

---

**Archivos:** Todos los gráficos están en la carpeta `charts/`

**Siguiente paso:** ¿Quieres que ajuste los componentes y recalcule los scores?
