# Guía de Implementación: Scores Empresariales Experian

**Fecha:** 6 de enero de 2026
**Estado:** Pendiente de consulta Experian para empresas

---

## 📊 Situación Actual

### Empresas en el Sistema
- **Total empresas:** 90 (4.9% de la base)
- **Con score Experian:** 0 (ninguna)
- **Score actual:** 100% PLATAM V2.0 (sin componente HCPN)

### Problema Identificado
Las empresas NO tienen scores de Experian porque:
1. No se consultó Experian para personas jurídicas (solo para personas naturales)
2. El CSV `export-historial_credito-19-12-2025.csv` solo contiene:
   - 1,931 "Solicitud de cupo" (personas naturales)
   - 175 "Solicitud de cupo PN" (personas naturales)
   - 32 "Solicitud de cupo PJ accionista" (accionistas, no empresas)

---

## 📝 Listado de Empresas para Consulta

**Archivo generado:** `EMPRESAS_PARA_EXPERIAN.csv`
- Total NITs: 90
- Columnas: NIT, Nombre_Empresa, Email, Teléfono, Ciudad, Cupo_Total, Estado, Total_Pagos, Meses_Historial

### Top 5 Empresas Prioritarias (mayor cupo)

1. **RAMIREZ TRUJILLO Y CIA SAS**
   - NIT: 805003019
   - Cupo: $200,000,000
   - Ciudad: CALI (VALLE)

2. **TECNOLOGIA SOLAR DE COLOMBIA S A S BIC**
   - NIT: 900525196
   - Cupo: $100,000,000
   - Ciudad: PALMIRA (VALLE)

3. **GAMA INGENIERIA Y SERVICIOS 1 A S A S**
   - NIT: 901184611
   - Cupo: $100,000,000
   - Ciudad: CALI (VALLE)

4. **COVECO DE COLOMBIA S A S**
   - NIT: 900443090
   - Cupo: $50,000,000
   - Ciudad: CARTAGENA (BOL)

5. **CONSTRUCTORA ANAYA GIRALDO SAS**
   - NIT: 900530150
   - Cupo: $50,000,000
   - Ciudad: SOLEDAD (ATL)

### Primeros 5 NITs para Prueba Inicial

1. **901973300** - GLOW PREMANENT SAS ZOMAC
2. **901809312** - DOTACIONES Y BORDADOS PRYCA SAS
3. **901932123** - VOLT UP SAS
4. **901256954** - CLINICA VETERINARIA VITAL PET S.A.S
5. **900953782** - ECOECOEQUIPOS COLOMBIA SAS

---

## 🔧 Formato de Score Experian Empresarial

### Escala Esperada
**Score Experian Empresas: 0-5**
- **0** = Sin información
- **1** = Excelente (mejor score)
- **2** = Bueno
- **3** = Regular
- **4** = Malo
- **5** = Muy malo (peor score)

⚠️ **NOTA IMPORTANTE:** Esta escala es INVERSA a la de personas naturales (0-924 donde mayor es mejor).

---

## 📐 Normalización a Escala 0-1000

### Fórmula de Conversión Propuesta

```python
def normalize_business_experian_score(score):
    """
    Normaliza score empresarial Experian (0-5) a escala 0-1000

    Escala inversa: 1=mejor, 5=peor

    Args:
        score: Score Experian (0-5)

    Returns:
        Score normalizado (0-1000)
    """
    if pd.isna(score) or score == 0:
        # Sin información = base conservadora
        return 500

    # Mapeo inverso: 1 → 1000, 5 → 0
    # Fórmula: 1000 - ((score - 1) * 250)

    if score == 1:
        return 1000  # Excelente
    elif score == 2:
        return 750   # Bueno
    elif score == 3:
        return 500   # Regular
    elif score == 4:
        return 250   # Malo
    elif score == 5:
        return 0     # Muy malo
    else:
        # Interpolación lineal para valores intermedios
        return max(0, min(1000, 1000 - ((score - 1) * 250)))
```

### Tabla de Conversión

| Score Experian | Interpretación | Score Normalizado (0-1000) | Rating |
|----------------|----------------|----------------------------|--------|
| 0              | Sin información | 500 (base conservadora)   | C      |
| 1              | Excelente      | 1000                       | A+     |
| 2              | Bueno          | 750                        | B+     |
| 3              | Regular        | 500                        | C      |
| 4              | Malo           | 250                        | D      |
| 5              | Muy malo       | 0                          | F      |

---

## 🔄 Pasos para Implementar

### Fase 1: Consulta Experian (Tu responsabilidad)

1. **Consultar Experian para empresas:**
   - Usar archivo: `EMPRESAS_PARA_EXPERIAN.csv`
   - Tipo de documento: NIT
   - Tipo de consulta: Persona Jurídica (PJ)
   - Score esperado: Escala 0-5

2. **Guardar resultados:**
   - Formato recomendado: CSV con columnas `NIT` y `score_experian_pj`
   - Nombre sugerido: `export-experian-empresas-[FECHA].csv`

### Fase 2: Integración al Sistema (Automática)

Una vez tengas el CSV con los scores empresariales:

```bash
# 1. Colocar CSV en la raíz del proyecto
cp /ruta/al/export-experian-empresas-2026-01-XX.csv /Users/jpchacon/Scoring\ Interno/

# 2. Ejecutar script de integración (por crear)
python scripts/integrate_business_experian_scores.py

# 3. Recalcular scores híbridos
python scripts/fix_payment_plans_and_recalculate.py
```

**Script a crear:** `scripts/integrate_business_experian_scores.py`
- Lee CSV de scores empresariales
- Normaliza escala 0-5 → 0-1000
- Actualiza `master_dataset.csv`
- Actualiza `platam_scores.csv` con scores normalizados

---

## 📊 Impacto Esperado

### Antes (actual)
- Empresas: 100% PLATAM score
- Score promedio empresas: 709.7 pts
- No diferenciación por historial crediticio externo

### Después (con Experian)
- Empresas: Híbrido PLATAM + Experian normalizado
- Mejor evaluación de riesgo
- Pesos dinámicos según madurez:
  - Muy nuevas (<3 meses): 30% PLATAM, 70% Experian
  - Establecidas (>12 meses): 60% PLATAM, 40% Experian

---

## 🚨 Casos Especiales

### Empresas sin Score Experian (0)
- Usar base de **500 pts** (conservador, rating C)
- Híbrido usa 100% PLATAM hasta obtener información

### Empresas Nuevas con Score Excelente (1)
- Score normalizado: 1000 pts
- Híbrido: 70% Experian (1000) + 30% PLATAM
- Beneficia a empresas con buen historial externo pero sin pagos internos

---

## 📋 Checklist de Implementación

- [x] Generar listado de 90 empresas
- [x] Crear CSV: `EMPRESAS_PARA_EXPERIAN.csv`
- [x] Documentar fórmula de normalización
- [ ] **Consultar Experian para empresas** ← **PENDIENTE**
- [ ] Recibir CSV con scores empresariales (0-5)
- [ ] Crear script `integrate_business_experian_scores.py`
- [ ] Ejecutar integración
- [ ] Recalcular scores híbridos
- [ ] Validar resultados
- [ ] Actualizar `CONTEXTO_PARA_CLAUDE.md`
- [ ] Commit y push cambios

---

## 📞 Contacto para Consulta Experian

**Proveedor:** Experian Colombia
**Tipo de consulta:** Persona Jurídica (HCPN-PJ)
**Documentos:** NITs en `EMPRESAS_PARA_EXPERIAN.csv`

---

## 📚 Referencias

- **Documentación PLATAM Scoring:** `PLATAM_SCORING_DOCUMENTATION.md`
- **Guía de Scoring Híbrido:** `HYBRID_SCORING_GUIDE.md`
- **Contexto del Proyecto:** `CONTEXTO_PARA_CLAUDE.md`
- **Listado de Empresas:** `EMPRESAS_PARA_EXPERIAN.csv`

---

**Última actualización:** 6 enero 2026
**Autor:** Sistema de Scoring PLATAM V2.0
