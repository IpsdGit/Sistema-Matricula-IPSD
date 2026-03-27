# 🚀 Guía de Configuración en PythonAnywhere

Esta guía explica cómo configurar el **Sistema de Matrícula IPSD** en PythonAnywhere manteniendo seguridad y flexibilidad.

## 📋 Requisitos Previos

- Cuenta en [PythonAnywhere](https://www.pythonanywhere.com)
- Usuario con acceso al servidor: `IPSDUNAH`
- Conocimiento básico de PythonAnywhere

## 🔧 Paso 1: Variables de Entorno en PythonAnywhere

### Acceso a Variables de Entorno

1. Inicia sesión en PythonAnywhere
2. Ve a **Web** (en el menú superior)
3. Haz clic en tu aplicación web
4. Desplázate hasta **"Web app"** sección
5. Busca **"Virtualenv"** o **"Environment variables"**

### Variables Requeridas

Configura estas variables en PythonAnywhere:

```
SECRET_KEY=<genera-una-clave-aleatoria-larga>
DATABASE_PATH=/home/IPSDUNAH/mysite/matricula.db
ADMIN_PASSWORD=<nueva-contraseña-segura>
FLASK_ENV=production
```

### Cómo Generar una Clave Secreta Segura

**En la consola de PythonAnywhere:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copia el resultado y úsalo como `SECRET_KEY`.

---

## 📁 Paso 2: Estructura de Carpetas

En PythonAnywhere, la estructura debe ser:

```
/home/IPSDUNAH/mysite/
├── application.py        # Punto de entrada para PythonAnywhere
├── app.py               # Tu aplicación Flask
├── setup_bd.py          # Script de inicialización
├── parche.py            # Script de actualización
├── matricula.db         # Base de datos (se crea automáticamente)
├── static/              # Archivos estáticos (CSS, JS)
├── templates/           # Templates HTML
└── venv/                # Entorno virtual
```

---

## 🔌 Paso 3: Archivo WebApp (WSGI)

En PythonAnywhere, tu archivo de configuración web es fundamental.

### Crear o Editar `application.py`

Si PythonAnywhere lo solicita, crea `/home/IPSDUNAH/mysite/application.py`:

```python
import os
import sys

# Agregar el directorio al path de Python
path = '/home/IPSDUNAH/mysite'
if path not in sys.path:
    sys.path.append(path)

# Importar la aplicación Flask
from app import app as application

# Asegurar que se usan las variables de entorno
application.config['ENV'] = os.environ.get('FLASK_ENV', 'production')
```

---

## 💾 Paso 4: Base de Datos

### Primera Ejecución

Ejecuta los scripts de inicialización en **Consoles** de PythonAnywhere:

```bash
# 1. Navegar al directorio
cd /home/IPSDUNAH/mysite

# 2. Inicializar la BD
python3 setup_bd.py

# 3. Aplicar el parche de seguridad
python3 parche.py
```

**Importante**: Después de ejecutar estos scripts, la BD estará en:
```
/home/IPSDUNAH/mysite/matricula.db
```

### Backup de la Base de Datos

Es recomendable hacer backups regulares. Puedes:

1. **Descargar manualmente desde PythonAnywhere**:
   - Ve a **Files** > navega a `/home/IPSDUNAH/mysite/matricula.db`
   - Descárgalo

2. **Programar backups con script**:
   ```bash
   # En una consola de PythonAnywhere
   cp /home/IPSDUNAH/mysite/matricula.db /home/IPSDUNAH/mysite/backups/matricula_$(date +%Y%m%d_%H%M%S).db
   ```

---

## 🔐 Paso 5: Seguridad en Producción

### ✅ Checklist de Seguridad

- [ ] Cambiar `SECRET_KEY` a un valor único y fuerte
- [ ] Cambiar `ADMIN_PASSWORD` a una contraseña segura
- [ ] Verificar que `FLASK_ENV=production`
- [ ] Habilitar HTTPS en configuración de PythonAnywhere
- [ ] Revisar permisos de archivos (DB debe ser accesible solo por tu usuario)

### Cambiar Contraseña de Admin Después de Desplegar

Si necesitas cambiar la contraseña sin re-ejecutar `parche.py`:

**En Consola de PythonAnywhere:**
```python
import sqlite3
from werkzeug.security import generate_password_hash
import os

db_path = os.environ.get('DATABASE_PATH', '/home/IPSDUNAH/mysite/matricula.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Cambiar contraseña de admin
nueva_clave = generate_password_hash('tu-nueva-contraseña')
cursor.execute('UPDATE admin_users SET password_hash = ? WHERE username = ?', (nueva_clave, 'admin'))

conn.commit()
conn.close()
print("✓ Contraseña actualizada")
```

---

## 🚨 Paso 6: Reload de la Aplicación

Después de cada cambio en el código o variables de entorno:

1. Ve a **Web** en PythonAnywhere
2. Haz clic en el botón **"Reload"** (rayo ⚡)
3. Espera a que se recargue

---

## 🧪 Paso 7: Verificación

Accede a tu aplicación:
- **Portal profesor**: `https://IPSDUNAH.pythonanywhere.com`
- **Panel admin**: `https://IPSDUNAH.pythonanywhere.com/login_admin`
- **Credenciales**: usuario `admin` con la contraseña que configuraste

---

## 🐛 Resolución de Problemas

### Error: "módulo no encontrado"
```
Solución: Verifica que requirements.txt esté instalado en el virtualenv
```

En **Consoles** > **Bash console**:
```bash
mkvirtualenv --python=/usr/bin/python3.10 IPSDUNAH-venv
pip install -r /home/IPSDUNAH/mysite/requirements.txt
```

### Error: "permiso denegado" en la BD
```
Solución: Verifica permisos del archivo matricula.db
```

En **Bash console**:
```bash
ls -la /home/IPSDUNAH/mysite/matricula.db
chmod 644 /home/IPSDUNAH/mysite/matricula.db
```

### Error: "variable de entorno no encontrada"
```
Solución: Verifica que esté configurada en Web app > Environment variables
```

Para verificar en Bash:
```bash
echo $SECRET_KEY
echo $DATABASE_PATH
```

### La aplicación no carga después de cambios
```
Solución: Recarga con el botón ⚡ en Web
```

---

## 📋 Tabla de Variables de Entorno

| Variable | Valor por Defecto | Producción | Notas |
|----------|-------------------|-----------|-------|
| `SECRET_KEY` | `secrets.token_hex(32)` | ✅ **Cambiar** | Generada aleatoria |
| `DATABASE_PATH` | `/home/IPSDUNAH/mysite/matricula.db` | ✅ Mantener | Ruta en servidor |
| `ADMIN_PASSWORD` | `IPSD@admin2026` | ✅ **Cambiar** | Contraseña inicial |
| `FLASK_ENV` | `production` | ✅ Mantener | Desactivar debug |

---

## 🔄 Workflow de Actualización

Cuando necesites actualizar el código:

1. **Hacer cambios locales**
2. **Subirlos a Git**
3. **En PythonAnywhere > Bash console**:
   ```bash
   cd /home/IPSDUNAH/mysite
   git pull origin main
   ```
4. **Recargar la app**: clic en ⚡ en **Web**

---

## 💡 Tips Útiles

### Monitorizar Logs
En PythonAnywhere > **Web**, desplázate hasta **Log files** y revisa:
- `error.log` - Errores de la aplicación
- `server.log` - Logs del servidor

### Consola Python Interactiva
Para probar cambios sin afectar la app:
```bash
cd /home/IPSDUNAH/mysite
python3  # Inicia interprete Python
>>> import app
>>> app.app.config  # Ver configuración
```

### Aumentar Límite de Solicitudes
Si tienes muchos usuarios, configura en PythonAnywhere > **Web** > **CPU quota**.

---

## 📞 Soporte

- **Docs de PythonAnywhere**: https://www.pythonanywhere.com/help/
- **Foro Flask**: https://flask.palletsprojects.com/
- **Documentación SQLite**: https://www.sqlite.org/docs.html

---

**Última actualización**: Marzo 2026
