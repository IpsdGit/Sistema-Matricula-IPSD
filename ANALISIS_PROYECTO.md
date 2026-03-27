# Análisis del Proyecto: Sistema-Matricula-IPSD

## 📋 Descripción General

**Sistema de Matrícula en Línea para IPSD** - Plataforma web desarrollada en Flask que permite a profesores/empleados inscribirse en capacitaciones y a administradores gestionar cursos, horarios y matrículas.

## 🎯 Objetivo

Proporcionar un portal intuitivo y seguro donde:
- **Profesores**: Puedan buscar, inscribirse y cancelar matrículas en capacitaciones
- **Administradores**: Puedan crear/eliminar cursos, gestionar horarios y consultar estadísticas

---

## 🏗️ Arquitectura del Proyecto

### Stack Tecnológico
- **Backend**: Python 3.x con Flask
- **Base de Datos**: SQLite3
- **Frontend**: HTML5, CSS3, JavaScript
- **Seguridad**: CSRF tokens, Password hashing (werkzeug)

### Estructura de Directorios
```
Sistema-Matricula-IPSD/
├── app.py                          # Aplicación principal Flask
├── setup_bd.py                     # Script de inicialización de BD
├── parche.py                       # Script de actualización de BD
├── matricula.db                    # Base de datos SQLite [NO SUBIR]
├── static/
│   ├── main.js                     # Lógica JavaScript del cliente
│   └── style.css                   # Estilos CSS
├── templates/
│   ├── base.html                   # Template base (herencia)
│   ├── index.html                  # Portal principal
│   ├── dashboard.html              # Dashboard profesor
│   ├── matricula_exitosa.html      # Confirmación exitosa
│   ├── matricula_cancelada.html    # Confirmación cancelación
│   ├── admin_login.html            # Login administrador
│   └── admin.html                  # Panel administración
└── ANALISIS_PROYECTO.md            # Este archivo
```

---

## 📊 Modelo de Datos

### Tablas de la Base de Datos

#### 1. `capacitaciones`
```
- id (TEXT, PRIMARY KEY)           # ID único del curso (ej: "IPSD-001")
- nombre (TEXT)                    # Nombre del curso
- anio (TEXT)                      # Año de la capacitación
- trimestre (TEXT)                 # Trimestre (I, II, III, IV)
- mes (TEXT)                       # Mes específico
```

#### 2. `horarios_curso`
```
- id (INTEGER, PRIMARY KEY)
- id_capacitacion (TEXT, FK)       # Referencia a capacitaciones
- horario (TEXT)                   # Horario disponible (ej: "9:00 AM - 11:00 AM")
```

#### 3. `matriculas`
```
- id (INTEGER, PRIMARY KEY)
- numero_empleado (TEXT)           # ID del profesor/empleado (4-12 dígitos)
- id_capacitacion (TEXT, FK)       # Referencia a capacitaciones
- horario_elegido (TEXT)           # Horario seleccionado por el empleado
- fecha_matricula (DATETIME)       # Timestamp de inscripción
```

#### 4. `admin_users`
```
- id (INTEGER, PRIMARY KEY)
- username (TEXT, UNIQUE)          # Usuario administrador
- password_hash (TEXT)             # Contraseña hasheada
```

---

## 🔐 Características de Seguridad

### ✅ Implementadas
1. **CSRF Tokens**: Token único por sesión para prevenir ataques CSRF
2. **Password Hashing**: Contraseñas de admin encriptadas con werkzeug
3. **Headers HTTP Seguro**:
   - `X-Frame-Options: SAMEORIGIN` (previene clickjacking)
   - `X-Content-Type-Options: nosniff`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `X-XSS-Protection: 1; mode=block`

4. **Validación de Entrada**:
   - Número de empleado: 4-12 dígitos
   - ID de curso: Alfanumérico con guiones
   - Inyección SQL prevenida con prepared statements

5. **Autenticación Admin**:
   - Token de sesión después de login exitoso
   - Decorador `@admin_requerido` en rutas protegidas

---

## 🔀 Rutas de la Aplicación

### Públicas (Portal de Profesores)
| Ruta | Método | Descripción |
|------|--------|-------------|
| `/` | GET | Portal principal |
| `/dashboard` | POST | Muestra cursos disponibles y matriculados |
| `/matricular` | POST | Inscribe profesor en curso |
| `/cancelar_matricula` | POST | Cancela matrícula de profesor |

### Privadas (Panel Administrador)
| Ruta | Método | Descripción |
|------|--------|-------------|
| `/login_admin` | GET/POST | Login administrador |
| `/logout_admin` | GET | Cierra sesión |
| `/admin` | GET | Dashboard principal admin |
| `/admin/stats` | GET | API JSON para gráficos |
| `/admin/crear_curso` | POST | Crea nuevo curso |
| `/admin/eliminar_curso` | POST | Elimina curso |
| `/admin/eliminar_matricula` | POST | Elimina matrícula individual |
| `/admin/vaciar_matriculas` | POST | Elimina todas las matrículas |

---

## ⚙️ Funcionalidades Principales

### Portal de Profesores (index.html + dashboard.html)
- ✅ Ingreso de número de empleado
- ✅ Visualización de cursos disponibles y matrículas actuales
- ✅ Inscripción en capacitaciones con selección de horario
- ✅ Cancelación de matrículas
- ✅ Filtros por año, trimestre y mes

### Panel Administrador
- ✅ **Dashboard**: Estadísticas en tiempo real (total matrículas, cursos, profesores)
- ✅ **Gráficos**: Chart.js con datos de inscritos por curso y período
- ✅ **Gestión de Cursos**: CRUD completo con horarios
- ✅ **Gestión de Matrículas**: Ver, eliminar inscripciones individuales
- ✅ **Limpieza de Datos**: Vaciar todas las matrículas con confirmación
- ✅ **Filtrado**: Por año, trimestre y mes

---

## 🚀 Instalación y Ejecución

### Requisitos
```bash
python 3.7+
pip install flask werkzeug
```

### Pasos
1. **Inicializar la BD**:
   ```bash
   python setup_bd.py
   ```

2. **Aplicar parche de seguridad** (crear tabla de admin):
   ```bash
   python parche.py
   ```

3. **Ejecutar la aplicación**:
   ```bash
   python app.py
   ```

4. **Acceder**:
   - Portal profesor: `http://localhost:5000`
   - Panel admin: `http://localhost:5000/login_admin`
   - Credenciales por defecto: `admin` / `IPSD@admin2026`

---

## 📝 Variables de Entorno Importantes

En `app.py` línea 26-27:
```python
DB_PATH = '/home/IPSDUNAH/mysite/matricula.db'  # Ruta en servidor de producción
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
```

⚠️ **NOTA**: Estas rutas están configuradas para un servidor en producción. Para desarrollo local, considere usar rutas relativas.

---

## 🔍 Dependencias del Proyecto

| Paquete | Versión | Uso |
|---------|---------|-----|
| Flask | 2.x | Framework web |
| Werkzeug | 2.x | Password hashing y seguridad |
| SQLite3 | (Built-in) | Base de datos |

---

## 📊 Casos de Uso Principales

### Caso 1: Profesor se matricula en curso
```
1. Accede a / (index.html)
2. Ingresa número de empleado (validado: 4-12 dígitos)
3. Visualiza cursos disponibles y actuales (dashboard.html)
4. Selecciona curso y horario
5. Confirma matrícula
6. Recibe confirmación
```

### Caso 2: Admin gestiona cursos
```
1. Autenticarse en /login_admin
2. Accede a /admin (panel principal)
3. Crear curso: Ingresa ID, nombre, período, horarios
4. Ver estadísticas: Gráficos y métricas en tiempo real
5. Eliminar matrículas o limpiar datos
```

---

## ⚠️ Problemas Potenciales Encontrados

### 1. **Rutas de BD Hardcodeadas**
- Línea 26 (app.py) y línea 5 (parche.py) tienen ruta absoluta
- **Solución**: Usar variables de entorno o rutas relativas

### 2. **No hay requirements.txt**
- **Solución**: Crear `requirements.txt` con dependencias

### 3. **No hay .gitignore**
- **Solución**: Crear `.gitignore` para excluir BD, env y cache

### 4. **Contraseña por defecto visible**
- Línea 28 en `parche.py`: Contraseña hardcodeada
- **Solución**: Usar variables de entorno

### 5. **Sin logging**
- No hay registro de errores ni accesos
- **Solución**: Implementar logging

---

## ✨ Recomendaciones para Git

### Archivos a NO subir (.gitignore)
```
# Base de Datos
*.db
maestro.db
matricula.db

# Entorno Python
venv/
env/
__pycache__/
*.pyc
*.pyo
*.egg-info/

# IDE
.vscode/
.idea/
*.swp

# Variables de entorno
.env
.env.local

# OS
.DS_Store
Thumbs.db
```

### Archivos Recomendados para Git
```
✅ app.py
✅ setup_bd.py
✅ parche.py
✅ requirements.txt (CREAR)
✅ .gitignore (CREAR)
✅ README.md (MEJORAR)
✅ templates/
✅ static/
```

---

## 🎬 Próximos Pasos Sugeridos

1. **Crear `requirements.txt`**:
   ```
   Flask==2.3.x
   Werkzeug==2.3.x
   ```

2. **Crear `.gitignore` adecuado**

3. **Mejorar README.md** con instrucciones de despliegue

4. **Implementar logging** para debugging en producción

5. **Usar variables de entorno** para rutas y credenciales

6. **Agregar migraciones de BD** para cambios futuros

7. **Documentar modelos de BD** en más detalle

---

## 📚 Conclusión

Es un proyecto bien estructurado para un **Sistema de Gestión de Matrículas** con características de seguridad básicas pero funcionales. Está listo para ser versionado en Git una vez se realicen las mejoras recomendadas de seguridad y configuración.

**Complejidad**: ⭐⭐ (Medio-Bajo)  
**Completitud**: ⭐⭐⭐⭐ (Bien implementado)  
**Seguridad**: ⭐⭐⭐ (Media - necesita mejoras)
