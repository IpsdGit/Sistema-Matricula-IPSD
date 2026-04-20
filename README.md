# 📚 Sistema de Matrícula IPSD

Sistema web de gestión de matrículas en capacitaciones para profesores de IPSD (Instituto Pedagógico de la Universidad Nacional Autónoma de Honduras).

## 🎯 Características

### 👨‍🏫 Funciones de Profesor

- Ingreso con número de empleado
- Visualización de capacitaciones disponibles
- Inscripción en cursos con selección de horario
- Gestión de matrículas actuales
- Cancelación de inscripciones

### 👨‍💼 Funciones de Administrador

- Autenticación segura
- CRUD de capacitaciones
- Gestión de horarios por curso
- Administración de matrículas
- Estadísticas en tiempo real
- Gráficos interactivos (Chart.js)
- Filtros por período (año, trimestre, mes)

## 🛠️ Requisitos

- Python 3.7+
- pip (gestor de paquetes Python)

**Nota**: Este proyecto está configurado para ejecutarse en **PythonAnywhere**. Ver [docs/PYTHONANYWHERE_SETUP.md](docs/PYTHONANYWHERE_SETUP.md) para instrucciones específicas.

## 📦 Instalación

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd Sistema-Matricula-IPSD
```

### 2. Crear entorno virtual (recomendado)

```bash
python -m venv venv

# En Windows:
venv\Scripts\activate

# En Linux/Mac:
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Inicializar la base de datos

```bash
python scripts/setup_bd.py
```

### 5. Aplicar actualizaciones (parche de seguridad)

```bash
python scripts/parche.py
```

### 6. Ejecutar la aplicación

```bash
python app.py
```

La aplicación estará disponible en: **<http://localhost:5000>**

## 🔑 Variables de Entorno

Puedes configurar estas variables para personalizar la aplicación:

```bash
# Copia el archivo de ejemplo
cp .env.example .env

# Edita .env con tus valores
# En PythonAnywhere: Ve a Web > Environment variables
```

**Variables disponibles:**

- `SECRET_KEY`: Clave secreta para sesiones Flask
- `DATABASE_PATH`: Ruta de la base de datos (fallback: `/home/IPSDUNAH/mysite/matricula.db`)
- `ADMIN_PASSWORD`: Contraseña inicial del administrador
- `FLASK_ENV`: Ambiente (development/production)

## 🔑 Credenciales Iniciales

### Portal de Profesor

- Acceso: `http://localhost:5000`
- Cualquier número de empleado de 4-12 dígitos

### Panel Administrador

- URL: `http://localhost:5000/login_admin`
- Usuario: `admin`
- Contraseña: `IPSD@admin2026`

> ⚠️ **IMPORTANTE**: Cambiar la contraseña en producción

## 📁 Estructura del Proyecto

```
Sistema-Matricula-IPSD/
├── app.py                   # Bootstrap de Flask (registro de rutas y handlers)
├── config.py                # Configuración y constantes globales
├── database.py              # Conexión y migraciones mínimas
├── utils.py                 # Validaciones, helpers y utilidades compartidas
├── requirements.txt         # Dependencias Python
├── scripts/
│   ├── setup_bd.py          # Script de inicialización de BD
│   └── parche.py            # Script de actualización de BD
├── routes/
│   ├── admin.py             # Endpoints HTTP panel admin
│   └── portal.py            # Endpoints HTTP portal docente
├── services/
│   ├── admin_service.py     # Lógica de datos para admin
│   └── portal_service.py    # Lógica de datos para portal docente
├── tests/
│   └── test_smoke.py        # Pruebas de humo de rutas principales
├── docs/
│   ├── PYTHONANYWHERE_SETUP.md
│   ├── ANALISIS_PROYECTO.md
│   └── HISTORIAL_CAMBIOS.md
├── static/
│   ├── main.js              # JavaScript del cliente
│   └── style.css            # Estilos CSS
└── templates/
    ├── base.html            # Template base
    ├── index.html           # Portal principal
    ├── dashboard.html       # Panel profesor
    ├── admin_login.html     # Login admin
    ├── admin.html           # Panel admin
    ├── matricula_exitosa.html
    └── matricula_cancelada.html
```

## 🗄️ Base de Datos

### Tablas

#### `capacitaciones`

- `id`: Identificador único del curso
- `nombre`: Nombre de la capacitación
- `anio`: Año
- `trimestre`: Trimestre
- `mes`: Mes

#### `horarios_curso`

- `id`: Identificador
- `id_capacitacion`: Referencia a capacitaciones
- `horario`: Horario disponible

#### `matriculas`

- `id`: Identificador
- `numero_empleado`: ID del profesor
- `id_capacitacion`: Referencia al curso
- `horario_elegido`: Horario seleccionado
- `fecha_matricula`: Timestamp de inscripción

#### `admin_users`

- `id`: Identificador
- `username`: Usuario administrativo
- `password_hash`: Contraseña encriptada

## 🔐 Seguridad

- ✅ CSRF tokens en formularios
- ✅ Contraseñas hasheadas (werkzeug)
- ✅ Headers HTTP de seguridad
- ✅ Validación de entrada en servidor
- ✅ Prepared statements para prevenir inyección SQL
- ✅ Autenticación de administrador requerida

## 🚀 Despliegue en Producción

### PythonAnywhere

Este proyecto está preparado específicamente para ejecutarse en **PythonAnywhere**.

**Instrucciones completas**: Ver [docs/PYTHONANYWHERE_SETUP.md](docs/PYTHONANYWHERE_SETUP.md)

**Quick Start en PythonAnywhere:**

1. Configura las variables de entorno en **Web > Environment variables**
2. Carga el código en `/home/IPSDUNAH/mysite/`
3. Ejecuta `python3 scripts/setup_bd.py` y `python3 scripts/parche.py`
4. Recarga la app con el botón ⚡

### Otros Servidores (Heroku, AWS, etc.)

Si despliegas en otro servidor:

1. Configura las variables de entorno según tu plataforma
2. Asegúrate de que `DATABASE_PATH` apunte a una ruta válida
3. Instala dependencias: `pip install -r requirements.txt`
4. Usa un servidor WSGI (Gunicorn, uWSGI)

## 📝 Notas de Desarrollo

### Estructura de Rutas

- **Públicas**: `/`, `/dashboard`, `/matricular`, `/cancelar_matricula`
- **Privadas**: `/login_admin`, `/admin*` (requieren autenticación)

### Validaciones

- Número de empleado: 4-12 dígitos
- ID de curso: Alfanumérico con guiones

## 🤝 Contribución

Para reportar bugs o sugerir mejoras, cree un issue en el repositorio.

## 📄 Licencia

[Especificar licencia aquí]

## 👥 Autor

Proyecto desarrollado para: **Instituto Pedagógico de la Universidad Nacional Autónoma de Honduras (IPSD)**

---

**Última actualización**: Marzo 2026
