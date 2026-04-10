# 📝 Historial de Cambios - Sistema de Matrícula IPSD

---

## 📌 Estructura y Propósito del Documento

Este archivo documenta todos los cambios realizados en el proyecto **Sistema-Matricula-IPSD**. Cada entrada contiene:
- **QUÉ**: Descripción detallada del cambio
- **POR QUÉ**: Justificación del cambio (requisitos, problemas resueltos, mejoras)
- **PARA QUÉ**: Beneficio o funcionalidad que se logró

---

## 🚀 Versión 1.0 - Base del Proyecto

### Cambio 1.1: Creación de la estructura base del proyecto
**Fecha**: Enero 2026  
**Archivos afectados**: `app.py`, `setup_bd.py`, `requirements.txt`, estructura de directorios

**QUÉ**:
- Configuración inicial de la aplicación Flask
- Creación de directorios: `/static` (JavaScript, CSS) y `/templates` (HTML)
- Instalación de dependencias base: Flask 2.3.3 y Werkzeug 2.3.7

**POR QUÉ**:
- Se necesitaba un framework web para crear el portal de matrícula
- Flask fue elegido por ser ligero, flexible y fácil de desplegar en PythonAnywhere
- La separación de directorios permite una estructura escalable y mantenible

**PARA QUÉ**:
- Proporcionar la base técnica para desarrollar tanto el portal de profesores como el panel administrador
- Facilitar la organización del código frontend y backend

---

### Cambio 1.2: Implementación del modelo de datos (BD)
**Fecha**: Enero 2026  
**Archivos afectados**: `setup_bd.py`, `app.py`

**QUÉ**:
- Creación de 4 tablas en SQLite:
  - `capacitaciones`: Almacena cursos disponibles con año, trimestre y mes
  - `horarios_curso`: Horarios específicos para cada capacitación
  - `matriculas`: Registra inscripciones de profesores en cursos
  - `admin_users`: Credenciales de administradores con contraseñas hasheadas

**POR QUÉ**:
- Se requería estructurar los datos para manejar:
  - Múltiples capacitaciones por período
  - Flexibilidad en horarios (varios horarios por curso)
  - Rastreo de quién se inscribió en qué curso
  - Autenticación segura del administrador

**PARA QUÉ**:
- Permitir que profesores vean y se inscriban en capacitaciones disponibles
- Permitir que administradores gestionen cursos, horarios y matrículas
- Mantener un registro permanente de inscripciones para reportes

---

## 🔐 Seguridad

### Cambio 2.1: Implementación de Headers de Seguridad HTTP
**Fecha**: Enero-Febrero 2026  
**Archivos afectados**: `app.py`

**QUÉ**:
```python
- X-Frame-Options: SAMEORIGIN       # Previene clickjacking
- X-Content-Type-Options: nosniff   # Previene MIME sniffing
- Referrer-Policy: strict-origin    # Controla información de referencia
- X-XSS-Protection: 1; mode=block   # Protección contra XSS
```

**POR QUÉ**:
- La aplicación maneja datos sensibles de profesores y matrículas
- Se requería cumplir con estándares OWASP (Open Web Application Security Project)
- Es buena práctica de seguridad en aplicaciones web modernas

**PARA QUÉ**:
- Prevenir ataques comunes como XSS (Cross-Site Scripting) y clickjacking
- Proteger la integridad de las sesiones de administrador
- Aumentar la confianza de usuarios en la plataforma

---

### Cambio 2.2: Protección contra ataques CSRF
**Fecha**: Febrero 2026  
**Archivos afectados**: `app.py`, `base.html`, todos los formularios

**QUÉ**:
- Generación de tokens CSRF únicos por sesión (`generar_csrf_token()`)
- Validación de tokens CSRF en todas las rutas POST/PUT/DELETE
- Integración de tokens en todos los formularios HTML

**POR QUÉ**:
- Sin CSRF protection, un atacante podría engañar a un usuario autenticado para ejecutar acciones no autorizadas
- Es especialmente crítico en operaciones sensibles (crear cursos, eliminar matrículas)

**PARA QUÉ**:
- Garantizar que los cambios en la BD provienen únicamente de usuarios legítimos
- Evitar que sitios maliciosos realicen acciones en nombre de administradores

---

### Cambio 2.3: Password Hashing para administradores
**Fecha**: Febrero 2026  
**Archivos afectados**: `setup_bd.py`, `app.py`

**QUÉ**:
- Uso de `werkzeug.security` para hashear contraseñas
- Las contraseñas nunca se almacenan en texto plano
- Función `check_password_hash()` para validar en login

**POR QUÉ**:
- Si la BD fuera comprometida, las contraseñas en texto plano serían accesibles
- Werkzeug usa algoritmos seguros (pbkdf2 por defecto)

**PARA QUÉ**:
- Proteger las credenciales del administrador incluso si la BD es robada
- Cumplir con estándares de seguridad para aplicaciones de gestión

---

## 👨‍🏫 Portal de Profesores

### Cambio 3.1: Interfaz de portal principal
**Fecha**: Febrero 2026  
**Archivos afectados**: `index.html`, `style.css`, `main.js`

**QUÉ**:
- Página de acceso con ingreso de número de empleado
- Validación en cliente (4-12 dígitos) y servidor
- Interfaz responsiva y accesible

**POR QUÉ**:
- Los profesores necesitaban una forma simple de acceder sin crear contraseña
- El número de empleado es el único dato requerido para autenticación

**PARA QUÉ**:
- Reducir fricción en el login de profesores
- Permitir que cualquier profesor se inscriba sin registro previo

---

### Cambio 3.2: Dashboard de profesor con búsqueda de capacitaciones
**Fecha**: Febrero-Marzo 2026  
**Archivos afectados**: `dashboard.html`, `main.js`, `app.py` (rutas /dashboard, /matricular)

**QUÉ**:
- Vista de:
  - Capacitaciones disponibles con filtros (año, trimestre, mes)
  - Horarios disponibles por curso
  - Matrículas actuales del profesor
- Botones para inscribirse o cancelar
- Validaciones: no permitir inscripción duplicada

**POR QUÉ**:
- Los profesores necesitaban ver qué cursos estaban disponibles en cada período
- Se requería flexibilidad de horarios (un corso podría tener 3-4 horarios disponibles)

**PARA QUÉ**:
- Permitir que profesores se inscriban en capacitaciones según su disponibilidad
- Proporcionar una experiencia clara y organizada

---

### Cambio 3.3: Cancelación de matrículas
**Fecha**: Marzo 2026  
**Archivos afectados**: `dashboard.html`, `main.js`, `app.py` (ruta /cancelar_matricula)

**QUÉ**:
- Funcionalidad para que profesores cancelen sus inscripciones
- Confirmación de cancelación antes de procesar
- Mensaje de éxito/error al usuario

**POR QUÉ**:
- Los profesores podían cambiar de opinión sobre sus inscripciones
- Se necesaba una forma segura de eliminación (con confirmación)

**PARA QUÉ**:
- Dar flexibilidad a los profesores en su participación
- Mantener la integridad de datos con confirmación explícita

---

## 👨‍💼 Panel Administrador

### Cambio 4.1: Sistema de autenticación admin
**Fecha**: Marzo 2026  
**Archivos afectados**: `admin_login.html`, `app.py` (rutas /login_admin, /logout_admin)

**QUÉ**:
- Página de login exclusiva para administradores
- Usuario: `admin`
- Contraseña hasheada en BD
- Token de sesión tras login exitoso
- Decorador `@admin_requerido` para proteger rutas

**POR QUÉ**:
- El panel admin requiere autenticación robusta
- Solo administradores autorizados deben gestionar cursos y matrículas

**PARA QUÉ**:
- Prevenir acceso no autorizado al panel de gestión
- Crear una barrera de seguridad clara entre profesores y administradores

---

### Cambio 4.2: CRUD de Capacitaciones
**Fecha**: Marzo 2026  
**Archivos afectados**: `admin.html`, `main.js`, `app.py` (rutas /admin/crear_curso, /admin/eliminar_curso)

**QUÉ**:
- Crear: Formulario para agregar nuevas capacitaciones
- Read: Tabla de cursos existentes con detalles
- Update: Edición de datos de cursos (previsto para versiones futuras)
- Delete: Eliminar cursos con confirmación

**POR QUÉ**:
- Los administradores necesitaban control total sobre la oferta académica
- Los cursos cambian periódicamente (nuevos trimestres, cambios de contenido)

**PARA QUÉ**:
- Permitir que administradores mantengan un catálogo actualizado de capacitaciones
- Soportar múltiples períodos (trimestres, meses)

---

### Cambio 4.3: Gestión de Horarios
**Fecha**: Marzo 2026  
**Archivos afectados**: `admin.html`, `main.js`, `app.py` (rutas POST de horarios)

**QUÉ**:
- Agregar múltiples horarios a cada capacitación
- Mostrar horarios disponibles por curso
- Eliminar horarios específicos

**POR QUÉ**:
- Un mismo curso puede ofertarse en varios horarios
- Profesores tienen diferentes disponibilidades
- Los administradores necesitan flexibilidad en la programación

**PARA QUÉ**:
- Maximizar la participación de profesores
- Evitar conflictos de horarios
- Ofrecer opciones de flexibilidad

---

### Cambio 4.4: Dashboard de Estadísticas
**Fecha**: Marzo-Abril 2026  
**Archivos afectados**: `admin.html`, `main.js`, `app.py` (ruta /admin/stats)

**QUÉ**:
- Métricas en tiempo real:
  - Total de matrículas activas
  - Cantidad de cursos disponibles
  - Número de profesores inscritos
- Gráficos interactivos con Chart.js
- Filtros por año, trimestre y mes

**POR QUÉ**:
- Los administradores necesitaban visibilidad sobre la utilización del sistema
- Los datos de ocupación ayudan a planificar futuras capacitaciones
- Los gráficos visuales hacen más fácil identificar tendencias

**PARA QUÉ**:
- Proporcionar reportes visuales de participación
- Facilitar tomas de decisión basadas en datos
- Monitorear la salud del sistema

---

### Cambio 4.5: Gestión de Matrículas (Admin)
**Fecha**: Abril 2026  
**Archivos afectados**: `admin.html`, `main.js`, `app.py` (rutas /admin/eliminar_matricula, /admin/vaciar_matriculas)

**QUÉ**:
- Ver todas las matrículas activas por profesor y curso
- Eliminar matrículas individuales (si un profesor debe ser removido)
- Opción de vaciar todas las matrículas (limpieza de BD para nuevo período)

**POR QUÉ**:
- A veces se cometen errores de inscripción que requieren corrección
- Al iniciar un nuevo trimestre/período, se necesita limpiar las matrículas antiguas

**PARA QUÉ**:
- Dar control total a administradores sobre la integridad de datos
- Facilitar transiciones entre períodos académicos

---

## ⚙️ Configuración y Deployment

### Cambio 5.1: Variables de Entorno
**Fecha**: Abril 2026  
**Archivos afectados**: `app.py`, `setup_bd.py`

**QUÉ**:
- `SECRET_KEY`: Clave aleatoria por sesión
- `DATABASE_PATH`: Ruta configurable de la BD
- `ADMIN_PASSWORD`: Contraseña inicial del admin
- `FLASK_ENV`: Modo desarrollo vs producción

**POR QUÉ**:
- La misma codebase se ejecuta en desarrollo local y en PythonAnywhere
- Se requiere seguridad (secret key única por instalación)
- Los administradores pueden customizar credenciales

**PARA QUÉ**:
- Hacer la aplicación portable y segura en diferentes entornos
- Evitar hardcodear credenciales en el código

---

### Cambio 5.2: Detección automática de ruta BD (PythonAnywhere vs Local)
**Fecha**: Abril 2026  
**Archivos afectados**: `app.py`

**QUÉ**:
```python
# Intenta en este orden:
1. Variable de entorno DATABASE_PATH
2. Ruta local: ./matricula.db
3. Ruta PythonAnywhere: /home/IPSDUNAH/mysite/matricula.db
4. Fallback: ruta local
```

**POR QUÉ**:
- PythonAnywhere requiere rutas específicas diferente a desarrollo local
- Se necesaba automatizar esto para reducir manual config

**PARA QUÉ**:
- Permitir deployment con un mínimo de cambios de configuración
- Reducir errores causados por rutas incorrectas de BD

---

### Cambio 5.3: Auto-reload de templates en desarrollo
**Fecha**: Abril 2026  
**Archivos afectados**: `app.py`

**QUÉ**:
```python
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True
```

**POR QUÉ**:
- Durante desarrollo, cambios en HTML requería reiniciar servidor manualmente
- Esto ralentizaba el ciclo de desarrollo

**PARA QUÉ**:
- Mejorar experiencia de desarrollo
- Ver cambios de templates instantáneamente

---

## 📦 Documentación del Proyecto

### Cambio 6.1: README.md
**Fecha**: Abril 2026  
**Archivos afectados**: `README.md`

**QUÉ**:
- Guía de instalación
- Instrucciones de setup para desarrollo local y PythonAnywhere
- Credenciales iniciales
- Requisitos del sistema
- Características principales

**POR QUÉ**:
- Nuevo desarrolladores necesitaban instrucciones claras
- La instalación implica pasos específicos (venv, pip install, setup_bd.py)

**PARA QUÉ**:
- Facilitar onboarding de nuevos desarrolladores
- Documentar flujo de deployment

---

### Cambio 6.2: ANALISIS_PROYECTO.md
**Fecha**: Abril 2026  
**Archivos afectados**: `ANALISIS_PROYECTO.md`

**QUÉ**:
- Descripción general del proyecto
- Stack tecnológico
- Modelo E-R de la BD
- Rutas disponibles (GET/POST)
- Funcionalidades por rol (profesor/admin)
- Características de seguridad

**POR QUÉ**:
- Proporcionaba referencia técnica completa
- Facilitaba auditorías de seguridad
- Documentaba arquitectura para mantenimiento futuro

**PARA QUÉ**:
- Servir como blueprint técnico del proyecto
- Facilitar escalabilidad futura

---

## 🔧 Mantenimiento y Parches

### Cambio 7.1: Script de actualización (parche.py)
**Fecha**: Abril 2026  
**Archivos afectados**: `parche.py`

**QUÉ**:
- Script que aplica cambios a la BD para actualizaciones futuras
- Permite migraciones sin perder datos
- Ejecutable después de despliegue

**POR QUÉ**:
- Las aplicaciones requieren mantenimiento y actualizaciones
- Necesitábamos un método seguro para actualizar BD sin perder datos históricos

**PARA QUÉ**:
- Facilitar rolling updates con cambios de BD
- Mantener integridad de datos durante upgrades

---

## 👥 Control de Acceso Basado en Rol y Dirección (RBAC)

### Cambio 8.1: Introducción de roles de administrador
**Fecha**: Abril 9, 2026  
**Archivos afectados**: `app.py`, `setup_bd.py`, `parche.py`, `admin.html`

**QUÉ**:
- Nueva arquitectura con dos roles administrativos:
  - **Superadmin**: Acceso global a toda la institución (IPSD completa)
  - **Admin**: Acceso limitado a su dirección asignada
- Tabla `admin_users` con columnas `rol` y `direccion`
- Decorador `@superadmin_requerido` para operaciones globales
- Restricción automática de vistas de cursos y matrículas según dirección del admin

**POR QUÉ**:
- IPSD es una institución con múltiples direcciones autónomas
- Cada dirección necesita gestionar sus propios cursos sin interferencia
- Se requería un sistema escalable de gobernanza de datos
- El superadmin debe poder auditar y respaldar globalmente

**PARA QUÉ**:
- Permitir que cada dirección gestione su oferta académica independientemente
- Mantener aislamiento de datos entre direcciones (privacidad)
- Facilitar delegación de responsabilidades administrativas
- Proporcionar un punto de supervisión central (superadmin)

---

### Cambio 8.2: Tabla de catálogo de direcciones
**Fecha**: Abril 9, 2026  
**Archivos afectados**: `app.py`, `setup_bd.py`, `parche.py`

**QUÉ**:
- Nueva tabla `direcciones` con campos:
  - `codigo`: Código único de dirección (ej. DEGT, DEGS)
  - `nombre`: Nombre completo de la dirección
- Funciones helper: `obtener_direcciones()`, `direccion_existe()`, `normalizar_direccion()`
- Validaciones para evitar códigos malformados, reservados o duplicados

**POR QUÉ**:
- Evitar hardcodear lista de direcciones en app.py
- Permitir agregar direcciones sin reiniciar aplicación
- Centralizar la fuente de verdad sobre direcciones válidas

**PARA QUÉ**:
- Hacer el sistema extensible a nuevas direcciones
- Facilitar auditoria de estructura organizacional
- Validar integridad referencial en usuarios y cursos

---

### Cambio 8.3: Autogeneración inteligente de IDs de curso
**Fecha**: Abril 9, 2026  
**Archivos afectados**: `app.py`, `admin.html`

**QUÉ**:
- Nuevo formato de ID de curso: `AF-DIRECCION-MODALIDAD-NUMERO`
  - Ejemplo: `AF-DEGT-V-001` (Dirección DEGT, Virtual, curso 001)
- Función `generar_id_curso()` que:
  - Busca el último número secuencial para esa combinación
  - Evita duplicados automáticamente
  - Soporta múltiples modalidades (V=Virtual, P=Presencial)
- Preview en tiempo real del código en el formulario

**POR QUÉ**:
- IDs legibles y self-descriptivos
- Elimina carga cognitiva del usuario (no ingresa ID manualmente)
- Estructura permite identificar dirección y modalidad de un curso a simple vista
- Previene conflictos de nomenclatura entre direcciones

**PARA QUÉ**:
- Automatizar generación de IDs únicos
- Mejorar trazabilidad de cursos
- Facilitarauditoria a través del naming

---

## 📋 Nuevos Campos en Modelo de Datos

### Cambio 9.1: Campos de detalle de capacitación
**Fecha**: Abril 9, 2026  
**Archivos afectados**: `setup_bd.py`, `parche.py`, `app.py`

**QUÉ**:
Se agregaron 3 columnas a tabla `capacitaciones`:
- `dia` (TEXT): Día del mes en que inicia el curso
- `modalidad` (TEXT): 'Virtual' o 'Presencial'
- `cupos_maximos` (INTEGER): Número máximo de inscritos permitidos

**POR QUÉ**:
- Los cursos tienen fechas específicas, no solo mes/trimestre
- Hay demanda de formatos de capacitación diferentes (online vs presencial)
- Los cupos limitan la capacidad física/virtual de la dirección

**PARA QUÉ**:
- Proporcionar información más precisa sobre horarios
- Permitir gestión de capacidad y recursos
- Preparar base para futuros reportes de utilización por modalidad

---

## 🛡️ Gestión de Usuarios Administradores (Superadmin)

### Cambio 10.1: Rutas de gestión de usuarios admin
**Fecha**: Abril 9, 2026  
**Archivos afectados**: `app.py`, `admin.html`

**QUÉ**:
Nuevas rutas protected (superadmin-only):
- `POST /admin/crear_admin`: Crear nuevo admin limitado a dirección
- `POST /admin/actualizar_admin`: Cambiar dirección / contraseña
- `POST /admin/eliminar_admin`: Remover usuario admin
- Interfaz UI con tabla de gestión en admin panel

**POR QUÉ**:
- Superadmin necesita capacidad de crear/eliminar admins
- Cada admin debe poder cambiar su contraseña
- Auditoría de cambios en estructura administrativa

**PARA QUÉ**:
- Delegar autoridad administrativa por dirección
- Mecanismo de onboarding/offboarding en IPSD
- Seguridad: todos los cambios requieren CSRF token

---

### Cambio 10.2: Rutas de gestión de direcciones
**Fecha**: Abril 9, 2026  
**Archivos afectados**: `app.py`, `admin.html`

**QUÉ**:
Nuevas rutas protected (superadmin-only):
- `POST /admin/crear_direccion`: Agregar nueva dirección
- `POST /admin/actualizar_direccion`: Renombrar o cambiar código (con migraciones en cascada)
- `POST /admin/eliminar_direccion`: Remover dirección si no tiene datos asociados

**Características**:
- Validaciones: Código debe ser único, no puede ser 'GLOBAL'
- Migraciones automáticas: Si cambia código, se renombran cursos, matriculas y admins
- Protecciones: No permite eliminar si hay cursos o admins activos

**POR QUÉ**:
- Direcciones pueden cambiar de código (reestructuraciones institucionales)
- Se necesita mecanismo seguro de migración de datos
- Sistema debe proteger integridad referencial

**PARA QUÉ**:
- Permitir que IPSD evolucione su estructura organizacional
- Minimizar riesgo de pérdida de datos durante cambios
- Auditoría de cambios estructurales

---

## 🎨 Interfaz de Usuario - Panel Admin Mejorado

### Cambio 11.1: Sistema de vistas tabuleadas (tabs)
**Fecha**: Abril 9, 2026  
**Archivos afectados**: `admin.html`, `main.js` (agregado en templates)

**QUÉ**:
- Reformateo del sidebar para sistema de navegación entre vistas
- Vistas: Dashboard, Cursos, Matrículas, Usuarios (solo superadmin)
- Navegación por data-attributes y localStorage
- Persistencia de vista seleccionada entre recargas

**POR QUÉ**:
- El admin panel crecia demasiado (scroll infinito)
- Mejora de UX: usuario ve solo la sección relevante
- Las pestañas hacen más intuitiva la navegación

**PARA QUÉ**:
- Organizar mejor el flujo de trabajo en admin
- Reducir ruido visual
- Facilitar acceso rápido a funciones específicas

---

### Cambio 11.2: Tabla de gestión de usuarios admin (UI)
**Fecha**: Abril 9, 2026  
**Archivos afectados**: `admin.html`

**QUÉ**:
- Tabla interactiva de usuarios con columnas:
  - Usuario
  - Rol (badge visual)
  - Dirección asignada
  - Acciones (editar dirección, cambiar password, eliminar)
- Protecciones visuales: Superadmin no se puede eliminar

**POR QUÉ**:
- Superadmin necesita visibilidad de quién administra qué
- Interfaz directa para cambios de asignación

**PARA QUÉ**:
- Facilitar auditoría de estructura administrative
- Rápido acceso a cambios de permisos

---

### Cambio 11.3: Tabla de gestión de direcciones (UI)
**Fecha**: Abril 9, 2026  
**Archivos afectados**: `admin.html`

**QUÉ**:
- Tabla de direcciones con estadísticas:
  - Código (editable)
  - Nombre (editable)
  - # de admins asociados
  - # de cursos asociados
  - Botón eliminar (deshabilitado si hay datos)

**POR QUÉ**:
- Visibilidad de estructura organizacional
- Indicadores de uso (para evitar eliminaciones accidentales)

**PARA QUÉ**:
- Permitir gestión centralizada de direcciones
- Prevenir errores (no permite eliminar si hay dependencias)

---

### Cambio 11.4: Formulario mejorado para crear curso
**Fecha**: Abril 9, 2026  
**Archivos afectados**: `admin.html`

**QUÉ**:
- ID autogenerado (no ingresable por usuario)
- Nuevos campos: Día, Modalidad (dropdown), Cupos máximos
- Si es superadmin: dropdown de dirección; si no: dirección autoasignada
- Preview en tiempo real del código que se generará
- Modal con más campos organizados en grid

**POR QUÉ**:
- Simplifica formulario al no pedir ID
- Preview reduce confusión sobre naming
- Cupos y modalidad son datos operacionales importantes

**PARA QUÉ**:
- Mejor experiencia usuario en creación de cursos
- Menos errores de entrada manual

---

## 🔄 Migraciones Automáticas y Compatibilidad

### Cambio 12.1: Función `asegurar_migraciones_minimas()`
**Fecha**: Abril 9, 2026  
**Archivos afectados**: `app.py`

**QUÉ**:
- Se ejecuta al iniciar app.py
- Crea tablas si no existen (fail-safe)
- Agrega columnas faltantes mediante ALTER TABLE
- Crea dirección "GLOBAL" si no existe
- Crea/actualiza superadmin si no existe
- No lanza excepciones críticas si BD no está lista

**POR QUÉ**:
- Permite despliegue sin ejecutar setup_bd.py primero
- Aumenta compatibilidad entre versiones
- Protege contra corrupción de BD parcial

**PARA QUÉ**:
- Deployment más robusto
- Reducir necesidad de scripts manuales
- Auto-healing de estructura de BD

---

### Cambio 12.2: Compatibilidad hacia atrás en login
**Fecha**: Abril 9, 2026  
**Archivos afectados**: `app.py`

**QUÉ**:
- Try/except en ruta `/login_admin` para capturar `OperationalError`
- Si tablas antiguas no tienen `rol` ni `direccion`, asume valores por defecto
- Asegura login funcione incluso con BD vieja

**POR QUÉ**:
- Usuarios con BD antigua no quedan bloqueados
- Transición gradual a nuevo esquema

**PARA QUÉ**:
- Zero-downtime upgrade
- Mejor experiencia en deployment

---

## 🔐 Seguridad Mejorada

### Cambio 13.1: Restricciones de acceso por dirección
**Fecha**: Abril 9, 2026  
**Archivos afectados**: `app.py` (múltiples rutas)

**QUÉ**:
- Admins no-superadmin solo ven/modifican datos de su dirección
- Queries SQL incluyen cláusula `WHERE c.id LIKE 'AF-DIRECCION-%'`
- Rutas `/admin/eliminar_curso`, `/admin/eliminar_matricula` validan permisos
- Export CSV respeta permisos de dirección

**POR QUÉ**:
- Seguridad crítica: impide que admin vea datos de otra dirección
- Cumple principio de menor privilegio
- HIPAA/GDPR-like concept para educación

**PARA QUÉ**:
- Proteger privacidad de datos por dirección
- Prevenir accesos no autorizados
- Compliance con políticas institucionales

---

### Cambio 13.2: Restricciones en operaciones destructivas
**Fecha**: Abril 9, 2026  
**Archivos afectados**: `app.py`

**QUÉ**:
- `POST /admin/vaciar_matriculas` cambió de `@admin_requerido` a `@superadmin_requerido`
- Solo superadmin puede limpiar todas las matrículas
- Intención: proteger contra eliminación accidental de datos históricos

**POR QUÉ**:
- Vaciar todas las matrículas es operación irreversible
- Requiere nivel máximo de autoridad

**PARA QUÉ**:
- Auditoría de cambios destructivos
- Reducir riesgo de sabotaje accidental

---

## 📊 Estadísticas Mejoradas

### Cambio 14.1: Stats filtradas por dirección
**Fecha**: Abril 9, 2026  
**Archivos afectados**: `app.py`

**QUÉ**:
- Dashboard muestra stats relevantes al rol del usuario:
  - Superadmin: números globales de toda IPSD
  - Admin: números solo de su dirección
- Queries separadas para superadmin vs admin

**POR QUÉ**:
- Información accionable para cada rol
- Superadmin ve panorama general; admin ve su sector

**PARA QUÉ**:
- Toma de decisiones contextualizada
- Reportes significativos por dirección

---

## � Sistema de Evaluación y Calificación de Matrículas

### Cambio 15.1: Campo de resultado (aprobado) en matrículas
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `app.py`, `setup_bd.py`, `parche.py`, `admin.html`, `dashboard.html`

**QUÉ**:
- Nueva columna `aprobado` en tabla `matriculas` (INTEGER, nullable):
  - NULL = Pendiente (estado inicial)
  - 1 = Aprobado
  - 0 = No aprobado
  - 2 = Abandonó
- Interfaz en admin para cambiar resultado por matrícula
- Filtros de búsqueda por resultado (Aprobado, No aprobado, Abandono, Pendiente)
- Export CSV incluye columna de resultado

**POR QUÉ**:
- Las capacitaciones de IPSD requieren evaluación y registro de desempeño
- Admins necesitan herramienta para documentar resultados de cursos
- Profesores deben saber el estado de sus matrículas

**PARA QUÉ**:
- Mantener registro oficial de aprobaciones/reprobaciones
- Audit trail de calificaciones
- Base para sistema de oportunidades y límites de intentos

---

### Cambio 15.2: Sistema de límites de repetición por curso (2/3)
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `app.py`, `dashboard.html`

**QUÉ**:
- Constantes:
  - `LIMITE_REPROBADO = 3`: Máximo 3 no-aprobaciones
  - `LIMITE_ABANDONO = 2`: Máximo 2 abandonos
- Función `obtener_resumen_intentos_por_curso()`: Cuenta intentos por nombre de curso
- Validaciones en `/matricular`: Impide re-matrícula si se alcanzó límite
- Excepciones:
  - Si ya fue aprobado: se bloquea definitivamente (no re-matricula)
  - Si tiene pendiente: no permite nueva matrícula

**POR QUÉ**:
- IPSD necesita control de oportunidades para profesores
- Límites evitan abuso del sistema (ej. profesores tomando indefinidamente)
- Política educativa: máximo 3 intentos de reprobación

**PARA QUÉ**:
- Enforcer límite de repeticiones
- Mantener integridad académica
- Reportes de estudiantes bloqueados por límites

---

### Cambio 15.3: Avisos de oportunidades en dashboard de profesor
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `dashboard.html`, `app.py`

**QUÉ**:
- Sección "Avisos de Oportunidades" en dashboard
- Muestra cursos donde profesor alcanzó límites (reprobado 3x o abandono 2x)
- Mensajes descriptivos:
  - Cursos bloqueados por límite de reprobación
  - Cursos bloqueados por límite de abandono
  - Cursos completados (aprobado)
- Codificación de colores: rojo si bloqueado, naranja si advertencia

**POR QUÉ**:
- Profesores necesitan visibilidad sobre restricciones
- Reduce confusión de "por qué no puedo matricularme"
- Mejora UX educativa

**PARA QUÉ**:
- Comunicar restricciones claramente
- Evitar intentos fallidos de re-matrícula
- Orientar profesores sobre disponibilidad de cursos

---

### Cambio 15.4: Indicadores de estado en matrículas actuales
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `dashboard.html`

**QUÉ**:
- Badges de estado junto a cada matrícula actual:
  - ✅ Aprobado (verde)
  - ❌ No aprobado (rojo)
  - 🟧 Abandonó (naranja)
  - ⏳ Pendiente (gris)
- Matrículas con resultado muestran 🔒 (cerrada)
- Botón cancelar solo disponible si está pendiente

**POR QUÉ**:
- Claridad visual del estado de cada matrícula
- Diferencia entre pendientes y finalizadas

**PARA QUÉ**:
- Mejor navegación del dashboard
- Información de estado inmediata

---

## 🔗 Campos Adicionales para Modalidad Virtual

### Cambio 16.1: Campo enlace_virtual en capacitaciones
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `app.py`, `setup_bd.py`, `parche.py`, `admin.html`

**QUÉ**:
- Nueva columna `enlace_virtual` en tabla `capacitaciones` (TEXT)
- Requerido si modalidad es Virtual, ignorado si Presencial
- Validación: debe ser URL válida (http:// o https://)
- En admin panel, mostrar botón "Abrir enlace de la sesión" para virtuales
- En formulario crear curso: campo de enlace que se habilita/deshabilita según modalidad

**POR QUÉ**:
- Cursos virtuales requieren link de acceso (Zoom, Meet, etc.)
- Facilita acceso rápido desde admin/lista de cursos
- Auditoría de dónde se dicta cada sesión

**PARA QUÉ**:
- Centralizar enlaces de acceso por curso
- Evitar que profesores tengan que buscar enlaces en emails

---

## 🎨 Interfaz Mejorada del Panel Administrador

### Cambio 17.1: Sistema de vistas tabuleadas persistentes
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `admin.html`, `main.js` (templates)

**QUÉ**:
- Navegación entre vistas con URL sync:
  - `/admin?view=dashboard`
  - `/admin?view=cursos`
  - `/admin?view=matriculas`
  - `/admin?view=usuarios` (solo superadmin)
- Historial del navegador (back/forward) funciona
- localStorage persiste vista entre sesiones
- Data-attributes en links para navegación

**POR QUÉ**:
- URLs permiteny guardar/compartir estados específicos
- Back button funciona intuitivamente
- UX más estándar de web moderna

**PARA QUÉ**:
- Mejorar navegabilidad del admin
- Permitir bookmarking de secciones específicas

---

### Cambio 17.2: Modales para edición de entidades
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `admin.html`, `main.js`

**QUÉ**:
Nuevos modales de edición modal:
- Modal: Editar Dirección (código, nombre)
- Modal: Editar Usuario Admin (username, rol, dirección, contraseña)
- Modal: Editar Curso (nombre, fecha, trimestre, modalidad, enlace, cupos)

**Características**:
- Botones pequeños con iconos (✏️ editar, 🗑️ eliminar)
- Pre-rellena datos del formulario modal
- Validaciones en cliente
- Rutas POST: `/admin/actualizar_curso`, `/admin/actualizar_admin`, `/admin/actualizar_direccion`

**POR QUÉ**:
- Tablas eran demasiado grandes con formularios inline
- Modales concentran interfaz y reducen visual clutter
- Edición inline causa confusión de qué se está modificando

**PARA QUÉ**:
- Mejor UX en edición
- Menos errores de entrada accidental
- Interfaz más limpia

---

### Cambio 17.3: Mejora en formulario de crear curso
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `admin.html`, `main.js`

**QUÉ**:
- Fecha única (input date) en lugar de Año/Mes/Día separados
- Soporte para fechas adicionales (crear mismo curso en múltiples fechas)
- Selector dinámico de horarios según día de la semana
- Validación de URL para enlace virtual
- Campo de cupos máximos

**Cambios UX**:
- Day picker calcula automáticamente día de la semana
- Horarios se filtran por día seleccionado (ej: "Lunes 08:00 AM - 10:00 AM")
- Ayuda contextual: "Se crearán X fechas para este curso"

**POR QUÉ**:
- Seleccionar fecha directa es más intuitivo que mes/año/día
- Crear varios cursos en fechas distintas es caso común
- Horarios específicos por día mejoran claridad

**PARA QUÉ**:
- Reducir errores en fechas
- Facilitar creación de capacitaciones multi-fecha
- Mejor validación de horarios

---

### Cambio 17.4: Menú de usuario mejorado en topbar
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `admin.html`, `main.js`

**QUÉ**:
- Chip de usuario en esquina superior derecha:
  - Avatar con inicia (círculo de color)
  - Nombre y rol
  - Dropdown: Cerrar sesión
- Botón de notificaciones (placeholder)
- Diseño moderno con hover effects

**POR QUÉ**:
- UX de dashboard web moderno
- Visibilidad de quién está logueado

**PARA QUÉ**:
- Mejor orientación del usuario
- Acceso rápido a logout

---

### Cambio 17.5: Sistema de actualización AJAX de resultados
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `admin.html`, `app.py`, `main.js`

**QUÉ**:
- Tabla de matrículas con selector de resultado (dropdown)
- Al cambiar: se envía via AJAX (sin recargar página)
- Estados visuales:
  - Pendiente: gris
  - Aprobado: verde
  - No aprobado: rojo
  - Abandono: naranja
- Indicador de status: "Guardando..." → "Guardado" → "Listo"
- Nueva ruta: `POST /admin/actualizar_resultado_matricula` (AJAX-friendly)

**POR QUÉ**:
- Cambiar resultado frecuentemente sin 10 recargas es tedioso
- AJAX mejora experiencia significativamente
- Estados visuales dan feedback inmediato

**PARA QUÉ**:
- Workflow más rápido para admins
- Validación visual de cambios
- Reducir clicks/recargas

---

### Cambio 17.6: Filtros mejorados de matrículas
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `admin.html`, `app.py`

**QUÉ**:
- Nuevos filtros en sección matrículas:
  - Año, Trimestre, Mes (existentes)
  - **Resultado**: Aprobado, No aprobado, Abandono, Pendiente (nuevo)
- Exportación CSV respeta filtro de resultado
- URL mantiene estado de filtros

**POR QUÉ**:
- Admins necesitan reportes desglosados por resultado
- Búsqueda de "solo aprobados" o "solo rechazados" es común

**PARA QUÉ**:
- Reporte de desempeño por resultado
- Auditoría focalizada en matrículas problemáticas

---

## 🧠 Lógica Mejorada de Contexto del Profesor

### Cambio 18.1: Función de contexto centralizada
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `app.py`

**QUÉ**:
- Función `cargar_contexto_dashboard_docente()`: Prepara todo contexto en una sola llamada
  - Cursos matriculados con aprobados (actualiza estado)
  - Cursos disponibles filtrados por bloques activos
  - Resumen de intentos por curso normalizado
- Reemplaza consultas repetidas dispersas en código

**POR QUÉ**:
- Reduce duplicación de logic
- Centraliza validaciones de límites
- Facilita mantenimiento

**PARA QUÉ**:
- Código más limpio y mantenible
- Consistencia en cálculos de estado

---

## 🔧 Constantes y Helpers Nuevos

### Cambio 19.1: Constantes globales de configuración
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `app.py`

**QUÉ**:
```python
MESES_ES = ['Enero', 'Febrero', ..., 'Diciembre']
DIAS_SEMANA = ['Lunes', 'Martes', ..., 'Domingo']
HORARIOS_BASE = ['08:00 AM - 10:00 AM', ...]  # 6 franjas
LIMITE_REPROBADO = 3
LIMITE_ABANDONO = 2
VISTAS_ADMIN_PERMITIDAS = {'dashboard', 'cursos', 'matriculas', 'usuarios'}
```

**POR QUÉ**:
- Centralizar configuración para fácil ajuste
- Evitar strings hardcodeados dispersos
- Single source of truth

**PARA QUÉ**:
- Cambiar límites o horarios en un lugar
- Facilitar internacionalización futura

---

### Cambio 19.2: Funciones helper adicionales
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `app.py`

**QUÉ**:
- `normalizar_nombre_curso()`: Estandariza nombres para comparación
- `validar_enlace_virtual()`: Valida URL formato http(s)://
- `normalizar_vista_admin()`: Estandariza vista seleccionada
- `redireccion_admin_vista()`: Redirige permaneciendo en vista actual
- `obtener_resumen_intentos_por_curso()`: Agrupa intentos por curso
- `construir_mensaje_oportunidades()`: Texto descriptivo de restricciones

**POR QUÉ**:
- DRY principle: Code reuse
- Lógica compleja encapsulada
- Mantenimiento centralizado

**PARA QUÉ**:
- Reducir bugs por inconsistencia
- Facilitar testing de lógica aislada

---

## 🎯 Próximas Mejoras Previstas

- [ ] Edición de horarios de cursos en modal
- [ ] Exportación de reportes (PDF) con branding por dirección
- [ ] Integración con directorio LDAP institucional
- [ ] Notificaciones por email a profesores (aprobaciones, abandonos)
- [ ] Dashboard de estadísticas de participación por período
- [ ] Gráficos de tasa de aprobación/abandono por curso
- [ ] Asignación automática de aulas y recursos
- [ ] API REST para integración con otros sistemas IPSD
- [ ] Autenticación de dos factores (2FA) para superadmin
- [ ] Sistema de auditoría detallada de cambios (quién, qué, cuándo)
- [ ] Manejo de excepciones de horarios especiales
- [ ] Reportes de cobertura de capacitaciones por dirección/período
- [ ] Descarga de nóminas de participantes por curso
- [ ] Funcionalidad de apelación de calificaciones

---

**Última actualización**: Abril 10, 2026  
**Versión actual**: 1.2 (Sistema de Evaluación y UX Mejorada)  
**Estado**: Development - Testing de evaluaciones
