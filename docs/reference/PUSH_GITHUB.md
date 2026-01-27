# 🚀 Push a GitHub - Guía Paso a Paso

**IMPORTANTE:** Vamos a excluir credenciales sensibles del repositorio

---

## ✅ PASO 1: Verificar estado actual

```bash
cd "/Users/jpchacon/Scoring Interno"
git status
```

Verás muchos archivos nuevos en rojo.

---

## ✅ PASO 2: Crear/Actualizar .gitignore

Primero, asegurémonos de NO subir credenciales:

```bash
# Crear o actualizar .gitignore
cat >> .gitignore << 'EOF'

# Credenciales y secretos
config/.env
*.env
.env.*
**/secrets/
**/*secret*
**/*credential*

# Archivos temporales
*.pyc
__pycache__/
.DS_Store
*.swp
*.swo
*~

# Datos locales
data/
*.csv
*.json.bak

# Logs
*.log
logs/

# Dependencias locales
venv/
env/
node_modules/

EOF
```

---

## ✅ PASO 3: Verificar que .env NO se subirá

```bash
# Verificar que config/.env está ignorado
git check-ignore config/.env
```

Debe mostrar: `config/.env` ← Esto significa que NO se subirá

---

## ✅ PASO 4: Agregar archivos al staging

```bash
# Agregar TODOS los archivos (excepto los que están en .gitignore)
git add .

# Verificar qué se va a subir
git status
```

**IMPORTANTE:** Verifica que `config/.env` NO aparezca en la lista verde.

---

## ✅ PASO 5: Crear commit

```bash
git commit -m "feat: Sistema completo de scoring en tiempo real

- Cloud Function con integración S3 y Vertex AI
- Queries SQL optimizadas para n8n
- Scripts de deployment automático
- Documentación completa
- Instrucciones para configurar n8n con IA

Componentes:
- main.py: Cloud Function (S3 + HCPN + ML)
- deploy_auto.sh: Deployment con credenciales automáticas
- INSTRUCCIONES_N8N_PARA_LLM.md: Guía paso a paso para n8n
- N8N_QUERIES_FINALES.md: Queries SQL completas
- Documentación: INICIO_RAPIDO.md, MAPA_COMPLETO.md, etc.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## ✅ PASO 6: Push a GitHub

```bash
# Push a la rama main
git push origin main
```

---

## ✅ PASO 7: Verificar en GitHub

1. Ve a tu repositorio en GitHub
2. Verifica que los nuevos archivos están ahí
3. **IMPORTANTE:** Verifica que `config/.env` NO esté visible

---

## ⚠️ SI YA SUBISTE .env POR ERROR

Si accidentalmente ya subiste el archivo con credenciales antes:

```bash
# Remover del historial (CUIDADO: esto reescribe historia)
git rm --cached config/.env
git commit -m "chore: Remove credentials file from repository"

# Force push (solo si es necesario)
git push origin main --force
```

Luego:
1. Ve a GitHub → Settings → Secrets
2. Regenera las credenciales AWS (por seguridad)

---

## ✅ PASO 8: Crear README en GitHub (Opcional)

Si quieres que tu repo se vea bien:

```bash
# Copiar el archivo de inicio rápido como README principal
cp INICIO_RAPIDO.md README.md

git add README.md
git commit -m "docs: Add README with quick start guide"
git push origin main
```

---

## 📋 CHECKLIST DE SEGURIDAD

Antes de hacer push, verifica:

- [ ] `.gitignore` incluye `config/.env`
- [ ] `git status` NO muestra `config/.env` en verde
- [ ] `git check-ignore config/.env` devuelve el nombre del archivo
- [ ] No hay otros archivos con credenciales (*.secret, *.key, etc.)

---

## 🎯 DESPUÉS DEL PUSH

Una vez hecho el push a GitHub, continúa con:

**PASO SIGUIENTE:** Deploy Cloud Function

```bash
cd "/Users/jpchacon/Scoring Interno/cloud_function_calculate_scores"
./deploy_auto.sh
```

---

## 💡 TIPS

### ¿Qué archivos SÍ se suben?

✅ Todo el código (.py, .sh, .md)
✅ Documentación completa
✅ Queries SQL
✅ Requirements.txt
✅ Estructura del proyecto

### ¿Qué archivos NO se suben?

❌ config/.env (credenciales)
❌ Archivos .pyc (compilados)
❌ __pycache__/ (cache de Python)
❌ data/ (datos locales)

---

## 🆘 TROUBLESHOOTING

### Error: "Permission denied (publickey)"

```bash
# Verificar SSH key
ssh -T git@github.com

# Si falla, usar HTTPS en vez de SSH
git remote set-url origin https://github.com/TU_USUARIO/TU_REPO.git
```

### Error: "Updates were rejected"

```bash
# Pull primero, luego push
git pull origin main --rebase
git push origin main
```

### Error: "Failed to push some refs"

```bash
# Ver qué pasó
git status

# Si hay conflictos, resolverlos
git pull origin main
# Resolver conflictos manualmente
git add .
git commit -m "fix: Resolve merge conflicts"
git push origin main
```

---

**Creado:** 2026-01-26
**Siguiente paso:** Deploy Cloud Function
