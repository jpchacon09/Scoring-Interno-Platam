# Proceso Completo: Integración de Scores Empresariales Experian

**Fecha de implementación:** 6 de enero de 2026
**Versión del sistema:** PLATAM V2.0 + Scores Empresariales
**Estado:** ✅ Completado e integrado

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Problema Identificado](#problema-identificado)
3. [Solución Implementada](#solución-implementada)
4. [Proceso Paso a Paso](#proceso-paso-a-paso)
5. [Normalización de Scores](#normalización-de-scores)
6. [Integración con Sistema Híbrido](#integración-con-sistema-híbrido)
7. [Resultados y Métricas](#resultados-y-métricas)
8. [Comparación: Personas vs Empresas](#comparación-personas-vs-empresas)
9. [Archivos Generados](#archivos-generados)
10. [Mantenimiento Futuro](#mantenimiento-futuro)

---

## 1. Resumen Ejecutivo

### ¿Qué se hizo?

Se integró el **scoring crediticio Experian para personas jurídicas (empresas)** al sistema PLATAM V2.0, normalizando la escala 0-5 (inversa) a 0-1000 para empalmar con el sistema de personas naturales.

### Números Clave

- **90 empresas** en el sistema (4.9% de la base)
- **172 PDFs** procesados de Experian DataCrédito
- **125 scores** extraídos exitosamente (72.7%)
- **60 empresas** con scores válidos integrados al sistema
- **30 empresas** sin score (usan base conservadora de 500 pts)

### Impacto

✅ **Empresas ahora tienen scores híbridos** (PLATAM + Experian)
✅ **Mismas reglas** que personas naturales (pesos dinámicos según madurez)
✅ **Mejor evaluación de riesgo** para decisiones crediticias
✅ **Sistema unificado** para todo tipo de clientes

---

## 2. Problema Identificado

### Situación Inicial

**Antes de esta implementación:**
- ✅ Personas naturales: Scores HCPN de Experian (escala 0-924)
- ❌ Empresas: NO tenían scores de Experian
- ❌ Empresas usaban solo PLATAM score (sin componente externo)
- ❌ Evaluación de riesgo incompleta para empresas

### Por Qué No Había Scores Empresariales

El archivo `export-historial_credito-19-12-2025.csv` solo contenía:
- 1,931 consultas "Solicitud de cupo" (personas naturales)
- 175 consultas "Solicitud de cupo PN" (personas naturales)
- 32 consultas "Solicitud de cupo PJ accionista" (accionistas, NO empresas)

**Conclusión:** No se había consultado Experian para las **90 empresas** del sistema.

---

## 3. Solución Implementada

### Estrategia de 3 Fases

#### Fase 1: Obtención de Scores Experian
1. Identificación de 90 empresas en el sistema
2. Generación de listado: `EMPRESAS_PARA_EXPERIAN.csv`
3. Obtención de 172 PDFs de DataCrédito Experian
4. Scores en escala 0-5 (inversa: 1=mejor, 5=peor)

#### Fase 2: Extracción y Normalización
1. Procesamiento automático de 172 PDFs
2. Extracción de NITs y scores mediante script Python
3. Normalización de escala 0-5 → 0-1000
4. Generación de CSVs con scores normalizados

#### Fase 3: Integración al Sistema
1. Actualización de `master_dataset.csv`
2. Actualización de `platam_scores.csv`
3. Recálculo de scores híbridos
4. Regeneración de `SCORES_V2_ANALISIS_COMPLETO.csv`

---

## 4. Proceso Paso a Paso

### Paso 1: Generación del Listado de Empresas

**Script:** `scripts/generate_empresas_list.py` (ejecutado manualmente)

**Input:**
- `data/processed/master_dataset.csv` (filtro: `client_type == 'Empresa'`)

**Output:**
- `EMPRESAS_PARA_EXPERIAN.csv` (90 empresas con NIT, nombre, contacto, cupo)

**Columnas generadas:**
```
NIT, Nombre_Empresa, Email, Telefono, Ciudad, Cupo_Total, Estado, Total_Pagos, Meses_Historial
```

### Paso 2: Obtención de PDFs Experian

**Proveedor:** DataCrédito Experian Colombia
**Tipo de consulta:** Persona Jurídica (PJ)
**Documentos:** NITs de las 90 empresas

**Resultado:**
- **172 PDFs** obtenidos (algunos NITs tienen múltiples consultas)
- Formato estándar DataCrédito con sección "SCORES"
- Score en columna "Puntaje" (escala 0-5)

### Paso 3: Extracción Automática de Scores

**Script:** `scripts/extract_business_experian_scores.py`

**Proceso:**
```python
1. Leer todos los PDFs de /Desktop/PJ Experian/
2. Para cada PDF:
   a. Extraer NIT del nombre de archivo (PJ-901973300.pdf)
   b. Buscar sección "SCORES" en el texto
   c. Extraer valor de columna "Puntaje" (0-5)
3. Generar CSV con: NIT, score_experian
4. Normalizar scores (0-5 → 0-1000)
5. Generar CSV final: NIT, score_experian, score_normalized, rating
```

**Resultados:**
```
✅ Exitosos:    125/172 (72.7%)
❌ Errores:      47/172 (27.3%)
   • NIT no encontrado: 42
   • Score no encontrado: 5
```

**Archivos generados:**
- `scores_empresas_experian.csv` (scores originales 0-5)
- `scores_empresas_experian_normalized.csv` (scores 0-1000)

### Paso 4: Integración al Sistema

**Script:** `scripts/integrate_business_experian_scores.py`

**Proceso:**
```
1. Leer scores_empresas_experian_normalized.csv (125 empresas)
2. Hacer merge con master_dataset.csv por NIT (cedula)
3. Actualizar columnas:
   - experian_score (0-5)
   - experian_score_normalized (0-1000)
4. Guardar master_dataset.csv actualizado
5. Actualizar platam_scores.csv
6. Ejecutar scripts/08_calculate_hybrid_scores.py
7. Regenerar hybrid_scores.csv
```

**Resultado:**
- **60 empresas** actualizadas con scores Experian
- **30 empresas** sin score (mantienen base 500)

### Paso 5: Regeneración de Análisis Completo

**Script:** `scripts/fix_payment_plans_and_recalculate.py`

**Proceso:**
```
1. Recalcular componentes de PLATAM score
2. Recalcular scores híbridos con pesos dinámicos
3. Regenerar SCORES_V2_ANALISIS_COMPLETO.csv
4. Regenerar ESTADISTICAS_SCORES_V2.csv
```

**Resultado:**
- CSV con 1,835 clientes (1,745 personas + 90 empresas)
- Todos con scores híbridos calculados

---

## 5. Normalización de Scores

### Escala Experian Empresarial (0-5)

**Importante:** Es una escala **INVERSA** (menor número = mejor)

| Score Experian | Interpretación | Observaciones |
|----------------|----------------|---------------|
| **0** | Sin información | No hay historial crediticio |
| **1** | Excelente | Mejor calificación crediticia |
| **2** | Bueno | Bajo riesgo crediticio |
| **3** | Regular | Riesgo moderado |
| **4** | Malo | Alto riesgo |
| **5** | Muy malo | Muy alto riesgo |

### Fórmula de Normalización (0-5 → 0-1000)

```python
def normalize_business_experian_score(score):
    """
    Normaliza score empresarial Experian (0-5) a escala 0-1000

    Escala inversa: 1=mejor, 5=peor
    """
    if pd.isna(score) or score == 0:
        return 500  # Sin información = base conservadora

    # Mapeo inverso
    score_map = {
        1: 1000,  # Excelente
        2: 750,   # Bueno
        3: 500,   # Regular
        4: 250,   # Malo
        5: 0      # Muy malo
    }

    return score_map.get(int(score), 500)
```

### Tabla de Conversión Final

| Score Experian | Score Normalizado | Rating PLATAM | Interpretación |
|----------------|-------------------|---------------|----------------|
| 0 | 500 | C+ | Sin información |
| 1 | 1000 | A+ | Excelente |
| 2 | 750 | B+ | Bueno |
| 3 | 500 | C+ | Regular |
| 4 | 250 | D | Malo |
| 5 | 0 | D/F | Muy malo |

### Distribución Real de Scores (125 empresas)

| Score | Empresas | Porcentaje | Normalizado | Rating |
|-------|----------|------------|-------------|--------|
| 0 | 36 | 28.8% | 500 | C+ |
| 1 | 34 | 27.2% | 1000 | A+ |
| 2 | 21 | 16.8% | 750 | B+ |
| 3 | 15 | 12.0% | 500 | C+ |
| 4 | 8 | 6.4% | 250 | D |
| 5 | 8 | 6.4% | 0 | D |
| 6* | 3 | 2.4% | 500 | C+ |

\* **Nota:** 3 empresas tienen score "6" (fuera de rango). Se trataron como "sin información" (500 pts).

**Score promedio:** 1.69 → **630 pts normalizado**

---

## 6. Integración con Sistema Híbrido

### Pesos Dinámicos (Igual que Personas Naturales)

Las empresas ahora usan **la misma lógica de pesos dinámicos** que las personas naturales:

#### Categorías de Madurez

| Categoría | Meses en Plataforma | Peso PLATAM | Peso Experian |
|-----------|---------------------|-------------|---------------|
| **Muy nuevo** | 0-3 meses | 30% | 70% |
| **Nuevo** | 3-6 meses | 40% | 60% |
| **Intermedio** | 6-12 meses | 50% | 50% |
| **Establecido** | 12-24 meses | 60% | 40% |
| **Maduro** | >24 meses | 70% | 30% |

#### Ajustes por Cantidad de Historial

- **Poco historial (0-4 pagos):** -10% PLATAM, +10% Experian
- **Historial amplio (20+ pagos):** +10% PLATAM, -10% Experian

#### Fórmula del Score Híbrido

```python
hybrid_score = (peso_platam * platam_score) + (peso_experian * experian_score_normalized)
```

### Casos Especiales: Empresas sin Score Experian

**Situación:** 30 empresas (33.3%) sin score Experian

**Tratamiento:**
- `experian_score`: NULL
- `experian_score_normalized`: NULL
- `peso_platam_usado`: 100%
- `peso_hcpn_usado`: 0%
- **Score híbrido = Score PLATAM** (100%)

**Estrategia:** "Sin HCPN: usa 100% PLATAM V2.0"

---

## 7. Resultados y Métricas

### Resultados Globales del Sistema

**Después de la integración:**

| Métrica | Total | Personas | Empresas |
|---------|-------|----------|----------|
| **Clientes totales** | 1,835 | 1,745 (95.1%) | 90 (4.9%) |
| **Con Experian** | 1,618 | 1,558 (89.3%) | 60 (66.7%) |
| **Sin Experian** | 217 | 187 (10.7%) | 30 (33.3%) |

### Resultados Específicos: Empresas

#### Empresas CON Score Experian (60)

| Métrica | Valor |
|---------|-------|
| **Score PLATAM promedio** | 702.1 pts |
| **Score Experian promedio** | 687.5 pts |
| **Score Híbrido promedio** | 693.5 pts |

**Distribución de Ratings Híbridos:**

| Rating | Empresas | Porcentaje |
|--------|----------|------------|
| A+ | 18 | 30.0% |
| A | 1 | 1.7% |
| B+ | 3 | 5.0% |
| B | 8 | 13.3% |
| B- | 1 | 1.7% |
| C+ | 1 | 1.7% |
| C | 12 | 20.0% |
| C- | 13 | 21.7% |
| D/F | 3 | 5.0% |

**Análisis:**
- ✅ **31.7%** de empresas con ratings excelentes (A+/A)
- ⚠️ **26.7%** de empresas con ratings bajos (C-/D/F)

#### Empresas SIN Score Experian (30)

| Métrica | Valor |
|---------|-------|
| **Score PLATAM promedio** | 725.0 pts |
| **Score Híbrido** | = Score PLATAM (100%) |

**Estrategia:** Usan solo PLATAM hasta obtener consulta Experian

### Mejoras vs Sistema Anterior

**Antes (solo PLATAM):**
- Empresas: 709.7 pts promedio
- Sin diferenciación por historial crediticio externo
- Evaluación de riesgo incompleta

**Después (PLATAM + Experian):**
- Empresas con Experian: 693.5 pts promedio
- Diferenciación basada en historial crediticio oficial
- Evaluación de riesgo completa y balanceada

**Impacto:**
- Empresas con buen score Experian (1-2) suben hasta 1000 pts
- Empresas con mal score Experian (4-5) bajan hasta 250 pts
- Mayor precisión en decisiones crediticias

---

## 8. Comparación: Personas vs Empresas

### Scores Promedio

| Tipo Cliente | N | PLATAM | Experian | Híbrido |
|--------------|---|--------|----------|---------|
| **Personas** | 1,745 | 763.5 | 762.1 | 763.4 |
| **Empresas** | 90 | 710.3 | 630.0* | 704.0 |
| **Total** | 1,835 | 760.8 | 762.1 | 760.1 |

\* Promedio de empresas con score Experian (60)

### Distribución de Ratings

#### Personas Naturales (1,745)

| Rating | Personas | % |
|--------|----------|---|
| A+ | 825 | 47.3% |
| C+ | 443 | 25.4% |
| B+ | 215 | 12.3% |
| B | 68 | 3.9% |
| A | 62 | 3.6% |
| C | 61 | 3.5% |
| D | 71 | 4.1% |

#### Empresas (90)

| Rating | Empresas | % |
|--------|----------|---|
| A+ | 33 | 36.7% |
| C+ | 49 | 54.4% |
| C | 1 | 1.1% |
| B+ | 1 | 1.1% |
| B | 2 | 2.2% |
| A | 3 | 3.3% |
| D | 1 | 1.1% |

### Análisis Comparativo

**Similitudes:**
- Ambos usan la misma lógica de scoring híbrido
- Mismos pesos dinámicos según madurez
- Misma escala de ratings (A+ a D/F)

**Diferencias:**
- **Empresas:** Scores ligeramente más bajos en promedio
- **Empresas:** Mayor concentración en C+ (54.4% vs 25.4%)
- **Empresas:** 90% son "muy nuevas" (<3 meses)
- **Empresas:** Solo 2.5 pagos promedio vs 6.8 en personas

**Razón de scores más bajos:**
- Empresas son mucho más nuevas (0.7 meses vs 4.2 meses promedio)
- Menos historial interno (2.5 pagos vs 6.8 pagos)
- Menor madurez crediticia en general

---

## 9. Archivos Generados

### Archivos de Extracción

| Archivo | Descripción | Registros | Columnas |
|---------|-------------|-----------|----------|
| `EMPRESAS_PARA_EXPERIAN.csv` | Listado de empresas para consulta | 90 | NIT, Nombre, Email, Teléfono, etc. |
| `scores_empresas_experian.csv` | Scores originales (0-5) | 125 | NIT, score_experian |
| `scores_empresas_experian_normalized.csv` | Scores normalizados (0-1000) | 125 | NIT, score_experian, score_normalized, rating |

### Archivos del Sistema Actualizados

| Archivo | Descripción | Registros | Empresas con Experian |
|---------|-------------|-----------|----------------------|
| `data/processed/master_dataset.csv` | Dataset maestro con scores empresariales | 1,836 | 60 |
| `data/processed/platam_scores.csv` | Scores PLATAM V2.0 | 1,835 | 60 |
| `data/processed/hybrid_scores.csv` | Scores híbridos recalculados | 1,835 | 60 |
| `SCORES_V2_ANALISIS_COMPLETO.csv` | Análisis completo para analytics | 1,835 | 60 |
| `ESTADISTICAS_SCORES_V2.csv` | Estadísticas agregadas | - | - |

### Scripts Creados

| Script | Propósito |
|--------|-----------|
| `scripts/extract_business_experian_scores.py` | Extracción automática de scores desde PDFs |
| `scripts/integrate_business_experian_scores.py` | Integración de scores al sistema |

### Documentación

| Documento | Contenido |
|-----------|-----------|
| `GUIA_SCORES_EMPRESARIALES.md` | Guía de implementación (antes) |
| `PROCESO_SCORES_EMPRESARIALES.md` | Este documento (proceso completo) |
| `CONTEXTO_PARA_CLAUDE.md` | Actualizado con información empresarial |

---

## 10. Mantenimiento Futuro

### Consultas Periódicas de Experian

**Recomendación:** Consultar Experian empresarial cada 6 meses

**Proceso:**
1. Identificar empresas sin score o con score desactualizado
2. Generar CSV con `EMPRESAS_PARA_EXPERIAN.csv`
3. Solicitar consultas a Experian DataCrédito
4. Ejecutar script de extracción
5. Ejecutar script de integración
6. Regenerar análisis completo

**Scripts a ejecutar:**
```bash
# 1. Extraer scores de nuevos PDFs
python scripts/extract_business_experian_scores.py

# 2. Integrar al sistema
python scripts/integrate_business_experian_scores.py

# 3. Regenerar análisis completo
python scripts/fix_payment_plans_and_recalculate.py
```

### Monitoreo de Empresas sin Score

**30 empresas actualmente sin score Experian**

**Acciones:**
1. Priorizar consultas para empresas con:
   - Mayor cupo (>$50M)
   - Mayor antigüedad (>6 meses)
   - Mayor actividad de pagos

2. Documentar razones de falta de score:
   - ¿Empresa muy nueva?
   - ¿No tiene historial crediticio?
   - ¿Error en la consulta?

### Actualización de Documentación

Cuando se agreguen nuevas empresas al sistema:
1. Actualizar `EMPRESAS_PARA_EXPERIAN.csv`
2. Consultar Experian para nuevas empresas
3. Ejecutar proceso de integración
4. Actualizar esta documentación con nuevas métricas

### Validación de Scores

**Periodicidad:** Mensual

**Checklist:**
- [ ] Verificar que empresas nuevas tengan scores correctos
- [ ] Comparar scores híbridos con decisiones crediticias reales
- [ ] Ajustar umbrales si es necesario
- [ ] Documentar casos especiales

---

## Conclusiones

### ✅ Logros

1. **Sistema unificado:** Personas y empresas usan la misma lógica de scoring híbrido
2. **Normalización exitosa:** Escala 0-5 empresarial convertida a 0-1000
3. **Alta tasa de éxito:** 72.7% de PDFs procesados correctamente
4. **60 empresas** con scores Experian integrados
5. **Documentación completa** del proceso

### 📊 Métricas Clave

- **90 empresas** en el sistema (4.9% de la base)
- **60 empresas** (66.7%) con score Experian
- **30 empresas** (33.3%) sin score (usan base 500)
- **Score híbrido promedio empresas:** 704.0 pts
- **31.7%** de empresas con ratings A+/A

### 🎯 Próximos Pasos

1. **Consultar Experian para las 30 empresas restantes**
2. **Monitorear performance de scores** vs decisiones reales
3. **Actualizar scores cada 6 meses**
4. **Optimizar umbrales** basados en datos de default

---

**Fecha de actualización:** 6 de enero de 2026
**Versión:** 1.0
**Autor:** Sistema de Scoring PLATAM V2.0
