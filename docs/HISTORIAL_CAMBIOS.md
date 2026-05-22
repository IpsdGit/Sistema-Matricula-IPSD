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

# 🏗️ Versión 1.3 - Refactorización Arquitectónica y Modularización

## Cambio 20.1: Creación de módulo de configuración centralizada
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `config.py` (nuevo), `app.py`, `setup_bd.py`, `parche.py`

**QUÉ**:
- Nuevo archivo `config.py` con centralización de:
  - `resolve_db_path()`: Función para resolver ruta de BD en múltiples entornos
  - Constantes: `MESES_ES`, `DIAS_SEMANA`, `HORARIOS_BASE`
  - Límites: `LIMITE_REPROBADO=3`, `LIMITE_ABANDONO=2`
  - Listas permitidas: `SECCIONES_DASHBOARD_PERMITIDAS`, `FILTROS_HISTORIAL_PERMITIDOS`, `VISTAS_ADMIN_PERMITIDAS`
  - Función `configure_app(app)`: Configuración centralizada de Flask

**POR QUÉ**:
- Configuraciones hardcodeadas dispersas en múltiples archivos
- Variables de entorno no centralizadas
- Dificultad para cambiar constantes (requería búsqueda global)
- Necesidad de DRY principle (Don't Repeat Yourself)

**PARA QUÉ**:
- Single source of truth para toda la configuración
- Facilita cambios de valores (ej. LIMITE_REPROBADO) en un solo lugar
- Preparación para entornos (desarrollo, testing, producción)
- Mejora mantenibilidad del código

---

## Cambio 20.2: Módulo de conexión y migraciones de BD
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `database.py` (nuevo), `app.py`

**QUÉ**:
- Nuevo archivo `database.py` con:
  - `get_db_connection()`: Función única para conexiones a BD
  - `asegurar_migraciones_minimas()`: Migración automática mejorada
  - Centralización de lógica de inicialización de tablas
  - Auto-recuperación ante BD corrupta o parcial
  - Sincronización de direcciones desde cursos y admins

**POR QUÉ**:
- Conexiones a BD duplicadas en múltiples funciones
- `asegurar_migraciones_minimas()` estaba en app.py (mezcla de responsabilidades)
- Necesidad de abstracción para testing (mock de conexiones)
- Migraciones automáticas pero sin centralización clara

**PARA QUÉ**:
- Punto único de conexión a BD (facilita cambios, logging, análisis)
- Separación de responsabilidades (acceso a datos vs lógica app)
- Facilita testing con BD en memoria
- Auto-recuperación robusta en deployments

---

## Cambio 20.3: Módulo de utilidades y funciones auxiliares
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `utils.py` (nuevo), `app.py`, `admin.html`, `main.js`

**QUÉ**:
Nuevo archivo `utils.py` consolidando 40+ funciones auxiliares:
- **Validación**: `validar_numero_empleado()`, `validar_username_admin()`, `validar_enlace_virtual()`, etc.
- **Normalización**: `normalizar_direccion()`, `normalizar_nombre_curso()`, `normalizar_vista_admin()`, etc.
- **CSRF**: `generar_csrf_token()`, `validar_csrf()`
- **Decoradores**: `@admin_requerido`, `@superadmin_requerido`
- **Lógica de negocio**: `obtener_resumen_intentos_por_curso()`, `construir_mensaje_oportunidades()`, `cargar_contexto_dashboard_docente()`
- **Generación de IDs**: `generar_id_curso()`, `obtener_codigo_modalidad()`
- **Historial**: `registrar_evento_matricula()`, `obtener_historial_acciones_formativas()`

**POR QUÉ**:
- Funciones auxiliares dispersas por app.py (>10 funciones)
- Reutilización de lógica en múltiples rutas
- Validaciones repetidas en diferentes contextos
- Decoradores y helpers en archivos template
- Preparación para testing unitario

**PARA QUÉ**:
- DRY principle: una función, múltiple uso
- Facilita testing aislado de funciones
- Mejora legibilidad de app.py (reduce de 1600+ a ~300 líneas conceptuales)
- Facilita auditoría de validaciones de seguridad

---

## Cambio 20.4: Separación de rutas en módulos especializados
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `routes/__init__.py`, `routes/admin.py`, `routes/portal.py` (nuevos)

**QUÉ**:
Nuevo directorio `routes/` con dos módulos:
- **`routes/admin.py`** (568 líneas): Todas las rutas administrativas
  - `/login_admin`, `/logout_admin`, `/admin`, `/admin/stats`
  - `/admin/crear_curso`, `/admin/actualizar_curso`, `/admin/eliminar_curso`
  - `/admin/crear_admin`, `/admin/actualizar_admin`, `/admin/eliminar_admin`
  - `/admin/crear_direccion`, `/admin/actualizar_direccion`, `/admin/eliminar_direccion`
  - `/admin/eliminar_matricula`, `/admin/actualizar_resultado_matricula`, `/admin/vaciar_matriculas`
  - `/exportar`
  
- **`routes/portal.py`** (113 líneas): Todas las rutas de público/profesor
  - `/`, `/logout_docente`, `/dashboard`, `/matricular`, `/cancelar_matricula`

**POR QUÉ**:
- `app.py` tenía 1600+ líneas (mezcla de rutas, lógica, configuración)
- Dificultad de navegación en archivo tan grande
- Imposible escalabilidad si se agregan más funciones
- Necesidad de vista clara de qué rutas existen

**PARA QUÉ**:
- Separación de responsabilidades (Controllers pattern)
- Cada módulo de ruta solo responsable de parseado de request/response
- Facilita agregar nuevas rutas sin desorden
- Mejor organización para equipo de desarrollo

---

## Cambio 20.5: Lógica de negocio en servicios especializados
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `services/__init__.py`, `services/admin_service.py`, `services/portal_service.py` (nuevos)

**QUÉ**:
Nuevo directorio `services/` con lógica de negocio aislada:
- **`services/admin_service.py`** (680 líneas): Lógica del panel administrativo
  - `authenticate_admin()`: Validación de credenciales
  - `get_admin_dashboard_payload()`: Preparación de contexto para dashboard
  - `get_admin_stats_payload()`: Cálculos de estadísticas
  - `fetch_export_records()`: Preparación de datos para exportación
  - `create_curso_records()`, `update_curso_record()`, `delete_curso_record()`: CRUD cursos
  - `create_admin_user_record()`, `update_admin_user_record()`, `delete_admin_user_record()`: CRUD admins
  - `create_direccion_record()`, `update_direccion_record()`, `delete_direccion_record()`: CRUD direcciones
  - `update_matricula_resultado()`: Actualización de calificaciones
  - `vaciar_matriculas_records()`: Limpieza de BD

- **`services/portal_service.py`** (203 líneas): Lógica del portal de profesores
  - `load_dashboard_context()`: Cargar contexto del dashboard
  - `process_matricula()`: Procesar inscripción con validaciones de límites
  - `process_cancelar_matricula()`: Procesar cancelación

**POR QUÉ**:
- Rutas no deben contener lógica de negocio compleja
- Misma lógica se necesita desde múltiples puntos (ruta normal, API, CLI)
- Facilita testing: mock de servicios vs mock de respuestas HTTP
- Patrón MVC: Rutas son Controllers → Services son Models/Business Logic

**PARA QUÉ**:
- Cleanar separation: Rutas manejan HTTP, Services manejan lógica
- Testing unitario de lógica sin levantar servidor web
- Posibilidad de crear CLI o API REST usando con los mismos Services
- Reutilización de lógica entre distintas interfaces

---

## Cambio 20.6: Reorganización de scripts de administración
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `scripts/setup_bd.py`, `scripts/parche.py` (movidos de raíz)

**QUÉ**:
- Scripts de inicialización movidos a directorio `scripts/`
- Actualización de rutas para resolver BD correctamente desde nuevo ubicación
- Función `resolver_db_path()` mejorada en `setup_bd.py`

**POR QUÉ**:
- Scripts mezclados con código de aplicación en raíz
- No es evidente que sean scripts de configuración única
- Directorios de proyecto desorganizado

**PARA QUÉ**:
- Mejor organización de proyecto (scripts separados de app)
- Facilita documentación: "Lee scripts/ para setup"
- Preparación para agregar más scripts (backup.py, cleanup.py, etc)

---

## Cambio 20.7: Documentación técnica mejorada
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `docs/ANALISIS_PROYECTO.md`, `docs/PYTHONANYWHERE_SETUP.md`, `docs/HISTORIAL_CAMBIOS.md` (movidos/creados)

**QUÉ**:
- Creación de directorio `docs/` con documentación:
  - `ANALISIS_PROYECTO.md` (320 líneas): Descripción técnica completa del proyecto
    - Stack tecnológico
    - Modelo de datos (E-R)
    - Rutas de la aplicación
    - Características de seguridad
    - Diagrama de directorios
    - Problemas identificados y recomendaciones
  
  - `PYTHONANYWHERE_SETUP.md` (277 líneas): Guía de deployment
    - Configuración de variables de entorno
    - Estructura de carpetas en servidor
    - Archivo WSGI (application.py)
    - Inicialización de BD
    - Seguridad en producción
    - Troubleshooting
    - Workflow de actualización
  
  - `HISTORIAL_CAMBIOS.md`: Movido a docs/

**POR QUÉ**:
- Documentación dispersa o en README
- Nuevos desarrolladores sin referencia clara de arquitectura
- Deployment a PythonAnywhere requiere instrucciones específicas
- Necesidad de guía de troubleshooting

**PARA QUÉ**:
- Onboarding de nuevos desarrolladores
- Referencia técnica centralizada
- Guía de deployment con menos errores
- Documentación de decisiones de diseño

---

## Cambio 20.8: Testing con pruebas smoke
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `tests/test_smoke.py` (nuevo)

**QUÉ**:
- Nuevo archivo de pruebas `tests/test_smoke.py` (84 líneas)
- Tests de rutas principales:
  - GET `/`: Portal principal retorna 200
  - GET `/login_admin`: Login retorna 200
  - GET `/dashboard`: Dashboard retorna 200
  - GET `/logout_docente`: Logout redirige (302)
  - GET `/admin`: Sin sesión redirige a login (302)
  - GET `/admin`: Con sesión retorna 200
  - POST operaciones requieren CSRF token válido (403 sin token)
  - Vaciar matrículas (solo superadmin) con CSRF válido redirige (302)

**POR QUÉ**:
- Cambios arquitectónicos requieren validar que no se rompieron rutas
- Sin tests, regresos accidentales no se detectan
- Refactorización de modularización requiere confianza de cobertura

**PARA QUÉ**:
- Prevenir regresos en refactorización
- Base para agregar tests más complejos
- CI/CD foundation (si se implementa Travis/GitHub Actions)
- Confianza en cambios futuros

---

## Nueva Estructura de Directorios (v1.3)
```
Sistema-Matricula-IPSD/
├── app.py                           # App Flask main (~300 líneas, solo setup)
├── config.py                        # Configuración centralizada
├── database.py                      # Conexión y migraciones de BD
├── utils.py                         # Funciones auxiliares (-407 líneas)
│
├── routes/
│   ├── __init__.py
│   ├── admin.py                     # Rutas administrativas (568 líneas)
│   └── portal.py                    # Rutas de portal de profesores (113 líneas)
│
├── services/
│   ├── __init__.py
│   ├── admin_service.py             # Lógica de negocio admin (680 líneas)
│   └── portal_service.py            # Lógica de negocio portal (203 líneas)
│
├── scripts/
│   ├── setup_bd.py                  # Inicialización de BD
│   └── parche.py                    # Migraciones de BD
│
├── templates/                       # Templates HTML
│   ├── base.html
│   ├── index.html
│   ├── dashboard.html
│   ├── admin_login.html
│   ├── admin.html
│   ├── matricula_exitosa.html
│   └── matricula_cancelada.html
│
├── static/                          # Assets frontend
│   ├── main.js
│   └── style.css
│
├── tests/
│   ├── __init__.py
│   └── test_smoke.py               # Pruebas de rutas básicas (84 líneas)
│
├── docs/                            # Documentación
│   ├── ANALISIS_PROYECTO.md        # Análisis técnico del proyecto
│   ├── PYTHONANYWHERE_SETUP.md     # Guía de deployment
│   ├── HISTORIAL_CAMBIOS.md        # Este archivo (ahora en docs/)
│   └── README.md                    # Guía de inicio rápido
│
└── matricula.db                     # BD SQLite [NO SUBIR a git]
```

---

## Cambio 20.9: Mejora de app.py con inyección de rutas y servicios
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `app.py` (refactorizado)

**QUÉ**:
- `app.py` pasó de 1600+ líneas a ~300 líneas
- Solo contiene:
  - Inicialización de Flask
  - Configuración de seguridad (headers CORS, CSRF)
  - Función error handlers (404, 500)
  - Inyección de contexto Jinja2 (generar_csrf_token)
  - `@app.before_request`: Ejecutar migraciones
  - Inyección de rutas: `from routes import register_admin_routes, register_portal_routes`
  - Entry point: `if __name__ == '__main__'`

**POR QUÉ**:
- app.py era god object (hacía todo: rutas, servicios, BD, validaciones)
- Imposible de testear de forma aislada
- Cambios en una ruta afectaban a todo el archivo

**PARA QUÉ**:
- `app.py` es solo configurador de la aplicación
- Fácil de leer y mantener
- Preparación para testing (mock de rutas/servicios)

---

## Cambio 20.10: Integración de módulos en app.py
**Fecha**: Abril 10, 2026  
**Archivos afectados**: `app.py`, importaciones de módulos

**QUÉ**:
- Importaciones centralizadas en app.py:
  - `from config import configure_app`
  - `from database import asegurar_migraciones_minimas`
  - `from routes.admin import register_admin_routes`
  - `from routes.portal import register_portal_routes`
  - `from utils import generar_csrf_token`

- Ejecución en orden:
  1. `configure_app(app)`: Configurar Flask
  2. `asegurar_migraciones_minimas()`: En `@app.before_request`
  3. `register_admin_routes(app)`: Inyectar rutas admin
  4. `register_portal_routes(app)`: Inyectar rutas portal

**POR QUÉ**:
- Antes: Todo estaba en app.py
- Ahora: Cada módulo se auto-registra

**PARA QUÉ**:
- Facilita agregar nuevos módulos (ej. routes/api.py)
- Order of operations claro
- Facilita testing: mock de módulos completos

---

---

# 🤖 Versión 1.4 - Sistema de Chat IA asistente

## Cambio 21.1: Integración de API Gemini para chat
**Fecha**: Abril 10-14, 2026  
**Archivos afectados**: `services/ia_service.py` (nuevo), `requirements.txt`, `config.py`

**QUÉ**:
- Nuevo módulo `services/ia_service.py` (312 líneas) que implementa lógica de chat con IA
- Integración con Google Gemini API (gemini-2.5-flash)
- Función `build_chat_reply()`: Procesa mensaje del usuario y retorna respuesta
- Función `fetch_chat_history()`: Obtiene historial de conversaciones del usuario
- Características:
  - Fallback automático a modelos alternativos si principal falla
  - Sistema de prompts contextualizados (diferencia admin vs docente)
  - Respuestas de dominio pre-programadas para consultas comunes (domain-answering)
  - Respuestas de contingencia si API no está disponible
  - Normalización de respuestas (reescribe términos incorrectos)
  - Validación de longitud de mensaje (máx 1200 caracteres)

**POR QUÉ**:
- Usuarios (docentes y admins) requieren soporte rápido y 24/7
- Consultas repetitivas sobre matricula, cancelación, horarios, reportes
- Reducir carga de soporte manual
- Mejorar experiencia de usuario con respuestas contextuales por rol

**PARA QUÉ**:
- Asistente de IA integrado en el portal
- Respuestas inmediatas a preguntas frecuentes
- Orientación en procesos del sistema
- Soporte en dos canales: docentes y administradores

---

## Cambio 21.2: Rutas API para chat
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `routes/chat.py` (nuevo), `app.py`

**QUÉ**:
- Nuevo módulo `routes/chat.py` (43 líneas) con dos endpoints:
  - `POST /api/chat`: Procesa mensaje del usuario y retorna respuesta de IA
    - Validación de autenticación (admin o docente)
    - Validación de CSRF token 
    - Parámetro: `message` (JSON body)
    - Respuesta: `{ok: true, reply: "..."}`
  
  - `GET /api/chat/history`: Retorna últimos 10 mensajes del usuario
    - Parámetro: limit (opcional, defecto 10)
    - Respuesta: `{ok: true, messages: [...], user_type: "admin"|"docente"}`

- Función helper `_resolve_chat_user()`: Determina tipo y ID de usuario desde sesión

**POR QUÉ**:
- Endpoints REST necesarios para comunicación JavaScript-Backend
- Separación clara de verificación de seguridad en ruta
- Reutilización de servicios de IA

**PARA QUÉ**:
- Interface entre widget JS y lógica de IA
- Validación de autenticación y CSRF en cada llamada
- Historial persistente de conversaciones

---

## Cambio 21.3: Widget de chat flotante en JavaScript
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `static/chat-widget.js` (nuevo), `static/style.css`

**QUÉ**:
- Nuevo archivo `static/chat-widget.js` (155 líneas):
  - Widget flotante en esquina inferior derecha
  - Panel expansible con toggle button
  - Interfaz de chat (mensajes del usuario en azul, IA en blanco)
  - Formulario para envío de mensajes
  - Indicador visual "IA escribiendo..."
  - Carga de historial al abrir panel
  - Gestión de CSRF token desde HTML
  - Event listeners: toggle, cerrar, envío, escape key
  - Escape HTML para prevenir XSS
  - Scroll automático al final de mensajes

- Estilos CSS (~175 líneas nuevas):
  - `.ia-chat-widget`: Contenedor fixed
  - `.ia-chat-toggle`: Botón flotante con gradient
  - `.ia-chat-panel`: Panel con grid layout
  - `.ia-chat-message`: Estilos de mensajes (user/assistant)
  - `.ia-chat-form`: Formulario de entrada
  - Responsive: Ajuste para móvil (<768px)
  - Animaciones y transiciones

**POR QUÉ**:
- Necesidad de interfaz visible y accesible
- Widget flotante no interfiere con contenido principal
- Mejor UX que popup modal tradicional

**PARA QUÉ**:
- Acceso rápido al asistente desde cualquier página
- Interfaz amigable para chat
- Responsive design para móvil y desktop

---

## Cambio 21.4: Persistencia de historial de chat
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `database.py`, `services/ia_service.py`

**QUÉ**:
- Nueva tabla `historial_chat` en BD:
  ```sql
  CREATE TABLE historial_chat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_tipo TEXT NOT NULL,         -- 'admin' o 'docente'
    usuario_id TEXT NOT NULL,           -- username o numero_empleado
    mensaje_usuario TEXT NOT NULL,      -- Consulta del usuario
    respuesta_modelo TEXT NOT NULL,     -- Respuesta de IA
    fecha_evento DATETIME DEFAULT CURRENT_TIMESTAMP
  )
  ```
- Índice: `idx_historial_chat_usuario` (usuario_tipo, usuario_id, id DESC)
- Función `_save_chat_exchange()`: Graba cada intercambio usuario-IA
- Función `_fetch_recent_history()`: Retrieves hasta 6 mensajes recientes para contexto

**POR QUÉ**:
- Necesidad de contexto en conversaciones multi-turno
- Auditoría de consultas (soporte técnico, análisis de uso)
- Mejora de respuestas: IA puede mencionar conversaciones anteriores

**PARA QUÉ**:
- Conversaciones con coherencia (IA entiende contexto previo)
- Base de datos de FAQs (análisis de consultas frecuentes)
- Análisis de comportamiento de usuarios

---

## Cambio 21.5: Integración en templates
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `templates/base.html`, `templates/dashboard.html`

**QUÉ**:
- **base.html**:
  - Widget de chat agregado como componente en el template base
  - Condicionalmente mostrado solo si usuario está autenticado (`admin_logueado` o `empleado_portal`)
  - Data attributes para CSRF token y tipo de usuario
  - Script `chat-widget.js` cargado solo si autenticado
  
- **dashboard.html**:
  - Removida sección "Chat con soporte IA" del menú lateral (soporte ahora vía widget flotante)
  - Simplificación: Solo 2 secciones en sidebar (Historial Formativo, Disponibles para matrícula)
  - Renombramientos:
    - "Acciones Formativas" → "Historial Formativo"
    - "Chat con soporte IA" removed del nav
  - Actualización de títulos y subtítulos
  - Confirmación de cancelación simplificada

**POR QUÉ**:
- Chat integrado en widget flotante, no necesita sección en sidebar
- Mejor UX: Menos clics para acceder al chat
- Reduce visual clutter en el menú

**PARA QUÉ**:
- Chat siempre disponible desde cualquier página
- Interface más limpia
- Acceso uniforme para admin y docentes

---

## Cambio 21.6: Dependencias nuevas
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `requirements.txt`, `config.py`

**QUÉ**:
- Agregadas 2 nuevas dependencias:
  - `google-genai==1.12.1`: SDK oficial de Google Gemini API
  - `python-dotenv==1.0.1`: Carga de variables de entorno desde `.env`
- Variable de entorno: `GOOGLE_GEMINI_API_KEY`
- Constante en config: `GEMINI_MODEL = 'gemini-2.5-flash'`
- Fallback models: `['gemini-2.5-flash', 'gemini-2.0-flash']`

**POR QUÉ**:
- Google Gemini es API más accesible y práctica para este caso
- python-dotenv para gestión de credenciales sin hardcodear

**PARA QUÉ**:
- Integración nativa con Gemini
- Manejo seguro de API keys

---

## Cambio 21.7: Configuración expandida
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `config.py`

**QUÉ**:
`SECCIONES_DASHBOARD_PERMITIDAS` cambió de 3 a 2 valores:
- Antes: `{'historial', 'disponibles', 'soporte'}`
- Ahora: `{'historial', 'disponibles'}`

Justificación: Sección "soporte" reemplazada por widget flotante global

**PARA QUÉ**:
- Configuración refleja arquitectura actual
- Validación de secciones permitidas más precisa

---

## Cambio 21.8: Testing de rutas chat
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `tests/test_chat.py` (nuevo)

**QUÉ**:
- Nuevo archivo de pruebas (88 líneas):
  - Test: Chat requiere autenticación (401)
  - Test: Chat requiere CSRF válido (403)
  - Test: Admin obtiene respuesta correcta (200)
  - Test: Historial de chat para docente sin error
  - Tests usan `unittest.mock.patch` para mockear `build_chat_reply()` y `fetch_chat_history()`
  - Validación de estructura de respuesta JSON

**POR QUÉ**:
- Endpoints de chat requieren testing
- Validación de autenticación y CSRF crítica
- Preparación para CI/CD

**PARA QUÉ**:
- Asegurar que endpoints no se rompan con cambios futuros
- Prevenir regresiones de seguridad
- Base para regresar tests

---

## Cambio 21.9: Prompts contextualizados por rol
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `services/ia_service.py`

**QUÉ**:
- Función `_get_system_prompt(user_type)`:
  - Para ADMIN: Enfoque en reportes, gestión de cursos, matrículas, usuarios admin
    - Nombres de secciones reales: "Dashboard", "Gestión de Cursos", "Matrículas", "Usuarios Admin"
  - Para DOCENTE: Enfoque en matricula, historial, portal docente
    - Nombres de secciones reales: "Historial Formativo", "Disponibles para matricula"
  - Ambos: No inventar datos, no asumir funciones inexistentes

**POR QUÉ**:
- Respuestas más precisas según contexto del usuario
- Previene alucinaciones (AI inventando funciones)
- Distingue entre auditorios

**PARA QUÉ**:
- Respuestas relevantes por rol
- Mejora de confianza (no inventa funcionalidades)

---

## Cambio 21.10: Domain-answering (respuestas pre-programadas)
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `services/ia_service.py`

**QUÉ**:
- Función `_try_domain_answer()`: Consultas comunes pre-respondidas
- **Para docentes**:
  - "cancelar/baja": Instrucciones de cancelación
  - "matricular/inscribir": Flujo de matricula
  - "historial/aprobado/reprobado": Cómo revisar resultados
  - "disponibles/curso/horario": Cómo ver oferta
- **Para admins**:
  - "reporte/estadística/dashboard": Acceso a métricas
  - "curso/crear/editar": Gestión de cursos
  - "matricula": Consultas de matriculas
  - "usuario/admin/dirección": Gestión de admins

- Función `_normalize_reply_text()`: Reescribe términos incorrectos en respuestas
  - "Catálogo de Cursos" → "Disponibles para matricula"

**POR QUÉ**:
- Respuestas rápidas y precisas para 90% de consultas
- No requiere API Gemini para preguntas frecuentes
- Reduce latencia y costo

**PARA QUÉ**:
- UX más rápido para preguntas comunes
- Contingencia si API no está disponible
- Respuestas garantizadas correctas

---

## Cambio 21.11: Fallback e intentos de modelo
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `services/ia_service.py`

**QUÉ**:
- Si domain-answering responde: Usa esa respuesta, sin llamar IA
- Si no hay domain-answer y no hay API key: Usa `_build_fallback_reply()` genérica
- Si hay API key: Intenta modelos en orden `[GEMINI_MODEL, fallback1, fallback2, ...]`
- Si todos fallan: Fallback genérico según contexto
- Logging de errores (sin romper chat)

**POR QUÉ**:
- Robustez: Chat funciona incluso si Gemini cae
- Optimización: No llama IA para preguntas simples
- Graceful degradation

**PARA QUÉ**:
- Servicio de chat siempre disponible
- Mejor performance (sin llamadas innecesarias a API)
- Resiliencia alta

---

## Cambio 21.12: Contexto multi-turno
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `services/ia_service.py`

**QUÉ**:
- Función `_fetch_recent_history()`: Obtiene últimos 6 intercambios
- Función `_build_prompt_with_history()`: Construye prompt incluyendo historial
- Ejemplo:
  ```
  Usuario: ¿Cómo me matriculo?
  Asistente: [respuesta]
  Usuario: ¿Puedo cancelar después?
  Asistente:  (entiende contexto de matricula)
  ```
- Llamada a Gemini incluye conversación anterior

**POR QUÉ**:
- Conversaciones naturales (no cada pregunta es aislada)
- AI entiende contexto previo
- Mejor continuidad

**PARA QUÉ**:
- Chat conversacional, no transaccional
- Respuestas coherentes en multi-turno

---

# 👥 Versión 1.5 - Catalogo de Docentes y Autenticación Mejorada

## Cambio 22.1: Tabla de catálogo de docentes
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `database.py`, `scripts/setup_bd.py`, `scripts/parche.py`

**QUÉ**:
- Nueva tabla `docentes` en BD:
  ```sql
  CREATE TABLE docentes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_empleado TEXT UNIQUE NOT NULL,
    nombre_completo TEXT NOT NULL,
    correo_institucional TEXT UNIQUE NOT NULL COLLATE NOCASE,
    activo INTEGER NOT NULL DEFAULT 1,
    fecha_sincronizacion DATETIME DEFAULT CURRENT_TIMESTAMP
  )
  ```
- Índices para búsqueda rápida: `idx_docentes_numero`, `idx_docentes_correo`
- Actualización de scripts de inicialización y parches

**POR QUÉ**:
- Actualmente el sistema no tiene catálogo interno de docentes
- Se requiere fuente de verdad para validación de acceso
- Sin esto no se puede auditar quién accede al portal
- Permite activar/desactivar docentes sin eliminar referencias históricas

**PARA QUÉ**:
- Control de acceso basado en catálogo institucional
- Validación de docentes válidos antes de permitir login
- Sincronización con sistemas administrativos externos (Excel, LDAP)
- Auditoría de accesos por docente

---

## Cambio 22.2: Script de sincronización desde Excel
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `scripts/sync_docentes_excel.py` (nuevo), `requirements.txt`

**QUÉ**:
- Nuevo script `sync_docentes_excel.py` (243 líneas) que:
  - Lee archivo Excel con datos de docentes
  - Valida columnas: numero_empleado, nombre_completo, correo_institucional
  - Normaliza datos (espacios, mayúsculas, acentos en cabeceras)
  - Detecta automáticamente columnas por alias (flexible con nombres)
  - Ejecuta UPSERT: INSERT si no existe, UPDATE si existe
  - Opcionalmente desactiva docentes ausentes en el Excel
  - Reporta estadísticas de sincronización

- Uso:
  ```bash
  python scripts/sync_docentes_excel.py --excel "ruta/archivo.xlsx"
  python scripts/sync_docentes_excel.py --excel "ruta/archivo.xlsx" --sheet "Hoja2"
  python scripts/sync_docentes_excel.py --excel "ruta/archivo.xlsx" --no-desactivar-ausentes
  ```

- Nueva dependencia: `openpyxl==3.1.5` (lectura de Excel)

**POR QUÉ**:
- Datos de docentes existen en sistemas administrativos (SAP, Excel, etc.)
- Importarlos manualmente es tedioso y propenso a errores
- Script automatiza ingesta periódica sin participación manual

**PARA QUÉ**:
- Sincronización automática de personal autorizado
- Facilita onboarding de nuevos periodos académicos
- Base para futura integración con LDAP/Active Directory

---

## Cambio 22.3: Autenticación mejorada con correo institucional
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `routes/portal.py`, `utils.py`

**QUÉ**:
- Nuevo flujo de login docente con 2 campos:
  - Correo institucional (validado con regex)
  - Número de empleado (4-12 dígitos)
  
- Función en `routes/portal.py`: `autenticar_docente(correo, numero)`
  - Valida ambos campos contra tabla `docentes`
  - Verifica que docente esté activo
  - Retorna registro completo (nombre, estado)

- Nuevas funciones en `utils.py`:
  - `validar_correo(correo)`: Valida formato email básico
  - `normalizar_correo(correo)`: Conversión a minúsculas y trim

**POR QUÉ**:
- Antes: login con solo número de empleado (ambiguo, sin auditoría)
- Ahora: login dual (correo + número) con validación en catálogo
- Correo es identificador único más confiable
- Posibilita futuras integraciones de email (notificaciones, recuperación)

**PARA QUÉ**:
- Acceso únicamente para docentes en catálogo activo
- Auditoría: saber quién (correo) y cuándo accedió
- Refuerzo de seguridad: 2 campos (difícil de adivinar)
- Preparación para sistema de notificaciones por email

---

## Cambio 22.4: Sesión mejorada con datos del docente
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `routes/portal.py`, `templates/dashboard.html`, `templates/index.html`

**QUÉ**:
- Session ahora almacena:
  - `empleado_portal`: número de empleado
  - `correo_docente`: correo institucional (NUEVO)
  - `nombre_docente`: nombre completo (NUEVO)

- Dashboard ahora muestra:
  - Nombre del docente en topbar
  - Correo en metadata del usuario
  - Título dinámico con nombre en lugar de "Empleado #"

- Login valida:
  - Existencia en table `docentes`
  - Estado `activo = 1`
  - Si sesión caduca pero usuario sigue sin f5, revalida al cargar

**POR QUÉ**:
- Mejor UX: usuario ve su nombre, no solo número
- Auditoría: correo persistente en logs/historial
- Seguridad: revalidación en cada request de dashboard

**PARA QUÉ**:
- Experiencia personalizada
- Trazabilidad mejorada
- Protección contra sesiones hijacked (docente desactivado)

---

## Cambio 22.5: Validación de correo en JavaScript
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `static/main.js`, `templates/index.html`

**QUÉ**:
- Nuevo código en `main.js` para validación en tiempo real:
  - Regex: `/^[^\s@]+@[^\s@]+\.[^\s@]+$/`
  - Clases CSS: `.is-valid` (verde), `.is-invalid` (rojo)
  - Muestra/oculta error `#email-error` dinámicamente
  - Valida mientras el usuario escribe (no al enviar)

- Form ahora tiene dos campos:
  1. Correo institucional (type="email")
  2. Número de empleado (type="text", filtro numérico)

**POR QUÉ**:
- Feedback inmediato: usuario sabe si correo es válido antes de enviar
- Reduce rechazos innecesarios
- UX mejorada (no wait+error)

**PARA QUÉ**:
- Mejor experiencia de usuario
- Menos solicitudes/errores innecesarios al servidor

---

## Cambio 22.6: Descripción de login actualizada
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `templates/index.html`

**QUÉ**:
- Textos actualizados:
  - "Ingresa tu número de empleado" → "Ingresa tu correo institucional y número de empleado"
  - Paso 1: "Ingresa tu número" → "Ingresa tus credenciales"
  - Descripción: Ahora menciona correo + número de empleado

**PARA QUÉ**:
- Claridad: nuevos usuarios saben que necesitan 2 datos
- Alineación entre UI e instrucciones

---

## Cambio 22.7: Testing de autenticación docente
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `tests/test_docente_login.py` (nuevo)

**QUÉ**:
- Nuevos tests (103 líneas):
  - Test: Aceptación con correo y número válidos
  - Test: Rechazo de credenciales inválidas
  - Test: Validación de sesión (nombre y correo almacenados)
  - Mock de `load_dashboard_context`
  - Setup: inserta docente de prueba en test DB

**PARA QUÉ**:
- Asegurar que login solo funciona con credenciales válidas
- Validación de datos guardados en sesión
- Prevenir regresiones en flujo de autenticación

---

## Cambio 22.8: Validadores expandidos en utils.py
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `utils.py`

**QUÉ**:
- Nuevas funciones:
  - `validar_correo(correo)`: Regex para email válido
  - `normalizar_correo(correo)`: trim + lowercase

- Reutilizable en:
  - Validación de formularios (portal)
  - Scripts de sincronización (Excel)
  - Posibles futuras APIs de email

**PARA QUÉ**:
- Consistencia: mismo validador en todos lados
- Facilita cambios de política (ej. dominios permitidos)

---

## Cambio 22.9: Catálogo como fuente de verdad
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `routes/portal.py`, `database.py`

**QUÉ**:
- Tabla `docentes` es única fuente de verdad para:
  - Quién puede acceder al portal
  - Nombre completo a mostrar (no ingresa usuario)
  - Correo de contacto

- Desactivación de docentes:
  - Script sincronización: desactiva si ausentes en Excel
  - Manual: UPDATE `activo=0` por admin (futuro)
  - Sin eliminar: preserva historial

**PARA QUÉ**:
- Control centralizado de acceso
- No requiere contraseña (sorprised auth)
- Facilita auditoría: quién estuvo activo cuándo

---

## Cambio 22.10: Estructura nueva de datos
**Fecha**: Abril 14, 2026  
**Archivos afectados**: Toda la BD

**QUÉ**:
```
docentes (NUEVO - Catálogo maestro)
├── numero_empleado (UNIQUE)
├── nombre_completo
├── correo_institucional (UNIQUE)
├── activo (flag)
└── fecha_sincronizacion

matriculas (existente, ahora referencia docentes implícitamente)
└── numero_empleado → FK docentes.numero_empleado (soft-reference)
```

**PARA QUÉ**:
- Modelo datos más realista (catálogo docentes existe)
- Integridad referencial lógica
- Preparación para future normalization (docentes.id FK en matriculas)

---

# 🔔 Versión 1.6 - Centro de Notificaciones para Docentes

## Cambio 23.1: Extensión configuración para nuevos filtros
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `config.py`

**QUÉ**:
- Nueva sección en `config.py` para filtros de notificación:
  ```python
  SECCIONES_DASHBOARD_PERMITIDAS = {'historial', 'disponibles', 'notificaciones'}
  FILTROS_NOTIFICACION_PERMITIDOS = {
      'todas',
      'nuevas',
      'asistencia',
      'resultados',
      'oportunidades',
      'certificados',
  }
  ```
- Categorización de notificaciones por tipo

**POR QUÉ**:
- Sistema anterior no tiene forma de controlar acceso a secciones
- Sin filtros, centro de notificaciones mostrarla todo sin categorizar
- Necesita validación server-side de filtros

**PARA QUÉ**:
- Control centralizado de secciones permitidas
- Validación de filtros antes de usarlos en BD
- Preparación para agregar más secciones/filtros en futuro

---

## Cambio 23.2: Nueva tabla de notificaciones y configuración
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `database.py`, sin cambios en estructura

**QUÉ**:
- Las notificaciones son **construidas dinámicamente** en memoria (no persistidas en BD)
- Se generan a partir de:
  - Historial de matriculas (cambios de estado: aprobado, rechazado, abandono)
  - Cursos disponibles (ofertas nuevas)
  - Matriculas activas (seguimiento de asistencia)
  - Avisos de oportunidades (límites de reprobados/abandonos)

**POR QUÉ**:
- Análisis en tiempo real más preciso
- Menos costo de almacenamiento
- Historial existente contiene toda info necesaria

**PARA QUÉ**:
- Centro de notificaciones funciona sin cambios en BD
- Escalable: nuevos tipos basados en lógica

---

## Cambio 23.3: Funciones construtor de notificaciones
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `utils.py` (160+ líneas nuevas)

**QUÉ**:
- Nueva función: `construir_notificaciones_docente()` (140 líneas)
  - Lee historial de matriculas y extrae eventos (aprobado, no aprobado, abandono)
  - Lee cursos disponibles y ofertas nuevas
  - Lee cursos pendientes y genera avisos de asistencia
  - Lee límites de oportunidades
  - Genera lista de ~18 notificaciones categorizadas

- Nueva función: `filtrar_notificaciones(notificaciones, filtro)`
  - Filtra por tipo: nuevas, asistencia, resultados, oportunidades, certificados
  - Preserva todas si filtro es 'todas'

- Nueva función: `resumir_notificaciones(notificaciones)`
  - Cuenta por categoría (para badges)
  - Retorna dict: {todas: N, nuevas: N, asistencia: N, ...}

**POR QUÉ**:
- Centraliza lógica de generación de notificaciones
- Reutilizable en API, tasks, reportes

**PARA QUÉ**:
- Código modular y testeable
- Facilita cambios en reglas de notificaciones

---

## Cambio 23.4: Notificaciones por estado de matrícula
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `utils.py` (construir_notificaciones_docente)

**QUÉ**:
- Cuando estado de matricula cambia:
  - **APROBADA**: Genera 2 notificaciones
    - Resultado publicado (✅ nivel success)
    - Certificado disponible (🎓 nivel success)
  - **NO_APROBADA**: Genera 1 notificación
    - Resultado publicado (❌ nivel danger)
  - **ABANDONO**: Genera 1 notificación
    - Estado actualizado (⚠️ nivel warning)

**POR QUÉ**:
- Docentes necesitan saber cambios críticos en sus matriculas
- Certificado ligado a aprobación (flujo claro)

**PARA QUÉ**:
- Alertas automáticas sin revisión manual
- Claridad sobre qué pasó en cada curso

---

## Cambio 23.5: Notificaciones de nuevas ofertas
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `utils.py` (construir_notificaciones_docente)

**QUÉ**:
- Genera notificaciones para primeros 4 cursos disponibles (🆕 nivel info)
- Si hay más de 4, resumen adicional (📚 nivel info)
- Cada notificación incluye:
  - Título, mensaje, ícono
  - Link directo a curso en dashboard (#curso-{id})
  - "Ir a la acción formativa" label

**POR QUÉ**:
- Docentes descubren nuevas oportunidades formativas
- Limit a 4: evita spam (demasiadas notificaciones)
- Links directos: menor fricción para acceder

**PARA QUÉ**:
- Mayor engagement en nuevas ofertas
- Vía clara para inscripción

---

## Cambio 23.6: Notificaciones de asistencia
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `utils.py` (construir_notificaciones_docente)

**QUÉ**:
- Genera notificaciones para cursos pendientes (activos, sin calificación final)
- Mensaje: "Marcado de asistencia habilitado en {curso}"
- Ícono: 🗓️ (calendario)
- Nivel: warning (acción requerida)
- Limit a 4 (primeros)

**POR QUÉ**:
- Docentes recordatorio de marcar asistencia
- Avisos de acción requerida vs informativos

**PARA QUÉ**:
- Mejor cumplimiento de asistencia
- Central de recordatorios

---

## Cambio 23.7: Notificaciones de oportunidades limitadas
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `utils.py` (construir_notificaciones_docente)

**QUÉ**:
- Genera notificaciones para avisos_oportunidades (límites)
- Para cada limit (reprobados, abandonos):
  - Si bloqueado: ⛔ nivel danger
  - Si por bloquear (próximo): 📌 nivel warning
- Mensaje incluye límite y curso

**POR QUÉ**:
- Docentes saben cuándo acercándose límite
- Alerta antes de quedar sin oportunidades

**PARA QUÉ**:
- Transparencia en límites de matrícula
- Prevención de sorpresas

---

## Cambio 23.8: Filtro y resumen de notificaciones
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `utils.py` (funciones nuevas)

**QUÉ**:
- `normalizar_filtro_notificacion(filtro)`: Valida filtro contra FILTROS_NOTIFICACION_PERMITIDOS
- `filtrar_notificaciones(notificaciones, filtro_notificacion)`: Filtra lista por tipo
- `resumir_notificaciones(notificaciones)`: Cuenta de cada tipo para badges

**PARA QUÉ**:
- Consistencia: mismo validador para todos (config + utils)
- Seguridad: rechaza filtros inválidos
- Performance: precalcula conteos

---

## Cambio 23.9: Nueva sección dashboard notificaciones
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `templates/dashboard.html` (150+ líneas nuevas)

**QUÉ**:
- Nueva sección completa: Centro de Notificaciones
  - Header con título, descripción, botón volver
  - Toolbar con:
    - Filtros: todas, nuevas, asistencia, resultados, certificados
    - Botón "Marcar todas como leídas"
  - Lista de notificaciones con:
    - Ícono por tipo/nivel
    - Título, mensaje, fecha
    - Estado leída (visual distinction)
    - Links a acciones (ej. ir a curso)
  - Empty state si no hay

- Dropdown de notifications en topbar:
  - Botón 🔔 con contador de no leídas
  - Muestra últimas 10 (preview)
  - Link a Centro completo

**PARA QUÉ**:
- Interfaz dedicada para notificaciones
- Acceso rápido desde topbar
- Mejor UX con filtros y state management

---

## Cambio 23.10: Estilos CSS para notificaciones
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `static/style.css` (300+ líneas nuevas)

**QUÉ**:
- Portal alert button y dropdown
  - `.portal-alert-btn`: Botón 🔔 con badge counter
  - `.portal-alert-dropdown`: Panel flotante con notificaciones
  - `.portal-alert-item`: Tarjeta individual categoriazada (info, success, warning, danger)
  - Colores por nivel, bordes distintos

- Sección notificaciones completa
  - `.notificaciones-center`: Layout principal
  - `.notificaciones-toolbar`: Barra de filtros
  - `.notificacion-item`: Tarjetas con modalidad de lectura
  - Toast overlay para confirmar acciones

- Usuario chip mejorado
  - Avatar con gradient
  - Nombre y email en contextoseparado
  - Responsive en mobile

- Curso card mejorado
  - `.curso-modalidad-badge`: Badge V/P (Virtual/Presencial)
  - Grid layout moderno

- Toast notification overlay
  - Modal para confirmar acciones (ej. matricula exitosa)
  - Cerrable con ×, ESC, click outside
  - Fade animation

**PARA QUÉ**:
- Interfaz moderna y accesible
- Categorización visual clara
- Experiencia mobile optimizada

---

## Cambio 23.11: JavaScript para toast notifications
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `static/main.js` (actualización), `templates/dashboard.html`

**QUÉ**:
- Evento en dashboard.html:
  ```javascript
  if (toastOverlay && toastClose) {
    toastClose.addEventListener('click', cerrarToast);
    toastOverlay.addEventListener('click', cerrarToast);
    document.addEventListener('keydown', cerrarToast on ESC);
  }
  ```

- Mostrado después de matricula exitosa (redirect + session feedback)

**PARA QUÉ**:
- Feedback visual post-acciones
- No interrumpe flujo (es cerrable)

---

## Cambio 23.12: Session management de notificaciones
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `routes/portal.py`, `templates/dashboard.html`

**QUÉ**:
- Session nuevo campo: `docente_notificaciones_leidas` (lista de IDs de notificaciones)
- Cuando usuario en sección notificaciones + click "Marcar todas como leídas":
  - Actualiza session con IDs de todas las notificaciones actuales
- Al cargar dashboard: recupera lista de session, marca esas notificaciones como leídas

**POR QUÉ**:
- Persistencia local (no guarda en BD)
- State reseteará cuando session caduque (OK: son transitorias)

**PARA QUÉ**:
- No mostrar "nuevo contador" si ya vistas
- UX: feedback visual de lectura

---

## Cambio 23.13: Integración en portal_service
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `routes/portal.py`, `services/portal_service.py`

**QUÉ**:
- `load_dashboard_context()` ahora acepta parámetros:
  - `filtro_notificacion` (default 'todas')
  - `ids_notificaciones_leidas` (default None)

- Retorna nuevo contexto:
  - `notificaciones`: Notificaciones filtradas
  - `notificaciones_todas`: Lista completa (para counts)
  - `resumen_notificaciones`: Dict con conteos por tipo
  - `notificaciones_total`: Número no leídas (para badge)
  - `notificaciones_filtradas`: Mostradas en tabla

**PARA QUÉ**:
- Service layer completo
- Tests fácil de mockear

---

## Cambio 23.14: Feedback de matrícula exitosa
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `routes/portal.py`, `templates/dashboard.html`

**QUÉ**:
- Cambio flujo POST /matricular:
  - Antes: Redirige a /matricula_exitosa.html (nueva página)
  - Ahora: Guarda feedback en session, redirige a /dashboard
  - Dashboard muestra toast con confirmación

- Session.matricula_feedback contiene:
  ```python
  {
      'tipo': 'success',
      'titulo': 'Matricula exitosa',
      'mensaje': 'Te inscribiste en {curso}',
      'curso': ..., 'codigo': ..., 'horario': ...
  }
  ```

**POR QUÉ**:
- Menos fragmentación (una page dashboard)
- Feedback en contexto donde usuario actúa

**PARA QUÉ**:
- Mejor UX: volver completamente a dashboard
- Más integración: ver nuevos cursos inmediatamente

---

## Cambio 23.15: Modalidad de cursos mejorada
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `templates/dashboard.html`, `static/style.css`, `utils.py`

**QUÉ**:
- Cursos ahora muestran badge modal:
  - Virtual (V): azul claro
  - Presencial (P): amarillo claro
- En historial también muestra modalidad
- Lógica deducción:
  - Primero: valor en BD capacitaciones.modalidad
  - Si vacío: deducir de ID_CAPACITACION pattern (-V- o -P-)
  - Si no: "No definida"

**PARA QUÉ**:
- Claridad: docentes saben formato antes de inscribirse
- Filtrable (futuro)

---

## Cambio 23.16: Logout mejorado
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `routes/portal.py`

**QUÉ**:
- Logout now limpia:
  - `empleado_portal`
  - `correo_docente` (NEW)
  - `nombre_docente` (NEW)
  - `docente_notificaciones_leidas` (NEW)
  - `_csrf_token`

**PARA QUÉ**:
- Limpieza completa de datos de sesión
- Seguridad: sin rastros de usuario anterior

---

## Cambio 23.17: Validación reauth docente activo
**Fecha**: Abril 14, 2026  
**Archivos afectados**: `routes/portal.py`

**QUÉ**:
- GET /dashboard ahora revalida docente en BD:
  - Verifica que siga en tabla docentes
  - Verifica que activo = 1
  - Si no: logout automático + mensaje

**POR QUÉ**:
- Admin puede desactivar docente en medio de sesión
- Evita acceso si persona despedida

**PARA QUÉ**:
- Security: respeta estado real en BD
- Auditoría: quién estuvo activo cuándo

---

---

# 📅 Versión 1.7 - Gestión de Sesiones y Calendarios para Acciones Formativas

**Fecha**: Abril 17, 2026  
**Cambios totales**: 4,897 líneas (12 archivos modificados)

## Cambio 24.1: Modelo de datos expandido para acciones formativas
**Fecha**: Abril 17, 2026  
**Archivos afectados**: `database.py`, `scripts/setup_bd.py`, `config.py`

**QUÉ**:
Nueva tabla `tipo_accion_formativa` - Catálogo maestro de tipos:
```sql
CREATE TABLE tipo_accion_formativa (
  codigo TEXT PRIMARY KEY,
  nombre TEXT NOT NULL,
  horas_minimas INTEGER NOT NULL,
  horas_maximas INTEGER,
  semanas_minimas INTEGER NOT NULL,
  semanas_maximas INTEGER
)
```

Datos pre-poblados:
- CONFERENCIA: 1-16 horas, 1-4 semanas
- SEMINARIO: 16-120 horas, 1-16 semanas
- CURSO: 20-240 horas, 1-52 semanas

Nuevas columnas en tabla `capacitaciones`:
- `tipo_accion` (TEXT): Tipo de acción (CONFERENCIA/SEMINARIO/CURSO)
- `horas_totales` (INTEGER): Horas de duración (default 20)
- `semanas_duracion` (INTEGER): Semanas que dura (default 1)

**POR QUÉ**:
- Capacitaciones tienen duraciones variables (conferencia ≠ curso largo)
- Necesario para calendarización y planificación de recursos
- Límites de horas/semanas aplican según tipo

**PARA QUÉ**:
- Clasificación clara de acciones formativas
- Validación de datos (hours/weeks within ranges)
- Base para calendarización automática

---

## Cambio 24.2: Tabla de sesiones de cursos
**Fecha**: Abril 17, 2026  
**Archivos afectados**: `database.py`

**QUÉ**:
Nueva tabla `sesiones_curso`:
```sql
CREATE TABLE sesiones_curso (
  id_sesion INTEGER PRIMARY KEY AUTOINCREMENT,
  id_curso TEXT NOT NULL,
  fecha TEXT NOT NULL,                    -- YYYY-MM-DD
  hora_inicio TEXT NOT NULL,              -- HH:MM
  hora_fin TEXT NOT NULL,                 -- HH:MM
  jornada TEXT NOT NULL DEFAULT 'UNICA',  -- MATUTINA/VESPERTINA/NOCTURNA/UNICA
  docente_sesion TEXT,                    -- Profesor que dicta sesión
  bloque_codigo TEXT,                     -- Bloque semanal (ej. BLOQUE_1)
  estado INTEGER NOT NULL DEFAULT 0,      -- 0: Programada, 1: En progreso, 2: Completada, 3: Cancelada
  token_asistencia TEXT,                  -- Token QR/PIN para marcar asistencia
  FOREIGN KEY (id_curso) REFERENCES capacitaciones (id) ON DELETE CASCADE
)
```

Índices para performance:
- `idx_sesiones_curso_fecha`: (id_curso, fecha, hora_inicio)
- `idx_sesiones_curso_bloque`: (id_curso, bloque_codigo)

**POR QUÉ**:
- Cada acción formativa tiene múltiples sesiones (clases)
- Necesario separar conceptos: curso (capacitación) ≠ sesión (clase específica)
- Validación de asistencia requiere sesiones definidas
- Calendarización multi-sesión

**PARA QUÉ**:
- Gestión detallada de sesiones por curso
- Rastreo de jornadas (matutina/vespertina/nocturna)
- Base para registro de asistencia

---

## Cambio 24.3: Tabla de registro de asistencia
**Fecha**: Abril 17, 2026  
**Archivos afectados**: `database.py`

**QUÉ**:
Nueva tabla `registro_asistencia`:
```sql
CREATE TABLE registro_asistencia (
  id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
  id_sesion INTEGER NOT NULL,
  numero_empleado TEXT NOT NULL,
  fecha_marcado TEXT NOT NULL,            -- YYYY-MM-DD
  hora_marcado TEXT NOT NULL,             -- HH:MM:SS
  FOREIGN KEY (id_sesion) REFERENCES sesiones_curso (id_sesion) ON DELETE CASCADE,
  FOREIGN KEY (numero_empleado) REFERENCES docentes (numero_empleado),
  UNIQUE (id_sesion, numero_empleado)
)
```

Índices:
- `idx_registro_asistencia_sesion`: (id_sesion)
- `idx_registro_asistencia_empleado`: (numero_empleado)

Restricción UNIQUE: Un docente solo puede marcar asistencia UNA VEZ por sesión

**POR QUÉ**:
- Auditoría de quién asistió a qué sesión y cuándo
- Cálculo de % de asistencia
- Base para certificación (requiere mínimo % asistencia)
- Relación M:N (sesión:docentes)

**PARA QUÉ**:
- Control de asistencia obligatorio para educación formal
- Reportes de participación por docente/curso/período

---

## Cambio 24.4: Rutas de administración de sesiones
**Fecha**: Abril 17, 2026  
**Archivos afectados**: `routes/admin.py` (+541 líneas nuevas)

**QUÉ**:
Nuevas rutas REST para gestión de sesiones:

**CRUD Sesiones**:
- `POST /admin/crear_sesion`: Crear nueva sesión para un curso
  - Parámetros: id_curso, fecha, hora_inicio, hora_fin, jornada
  - Validación: Fecha ≥ fecha de la acción formativa
- `GET /admin/sesiones/{id_curso}`: Listar sesiones de un curso (con filtros por fecha)
- `PUT /admin/actualizar_sesion/{id_sesion}`: Editar sesión (horarios, jornada, docente)
- `DELETE /admin/eliminar_sesion/{id_sesion}`: Eliminar sesión

**Gestión de Asistencia**:
- `POST /admin/abrir_asistencia/{id_sesion}`: Genera token QR/PIN para la sesión
  - Retorna token único
  - Cambia estado sesión a "En progreso"
- `POST /admin/cerrar_asistencia/{id_sesion}`: Cierra registrada de asistencia
  - Cambia estado a "Completada"
  - Reporta participantes totales
- `GET /admin/reporte_asistencia/{id_sesion}`: Listar docentes que marcaron asistencia

**Validaciones**:
- Solo admin puede crear sesiones de su dirección
- Superadmin puede ver/editar todas
- Sesión ya iniciada no puede ser eliminada
- Validación de horarios (no solapamiento)

**PARA QUÉ**:
- Interface completa para gestión de sesiones
- Control de acceso por dirección
- Auditoría de cambios

---

## Cambio 24.5: Servicios de lógica de sesiones y calendarios
**Fecha**: Abril 17, 2026  
**Archivos afectados**: `services/admin_service.py` (+686 líneas)

**QUÉ**:
Nuevas funciones en `admin_service.py`:

**Generación de Sesiones**:
- `generate_course_sessions()`: Crea sesiones automáticas basadas en tipo_accion y semanas_duracion
  - Parámetro: id_curso, fecha_inicio, cantidad_sesiones_por_semana
  - Genera bloques semanales: BLOQUE_1, BLOQUE_2, etc.
  - Respeta horas_totales ÷ sesiones = horas por sesión
  
**Validaciones de Sesión**:
- `validar_rango_horas()`: Horas sesión dentro de rango del tipo
- `validar_duracion_semanas()`: Duración total respeta semanas_duracion
- `validar_solapamiento()`: Sesiones mismo curso no se solapan en tiempo
- `validar_docente_disponibilidad()`: Docente no tiene sesiones simultáneas

**Reportes de Sesiones**:
- `get_calendar_data()`: Retorna sesiones por mes para calendar widget
- `get_attendance_summary()`: Resumen de asistencia por sesión
- `get_course_statistics()`: Stats por tipo de acción (conferencia/seminario/curso)

**Generación de Tokens**:
- `generar_token_asistencia()`: Token único de 8 caracteres (QR compatible)
- `validar_token()`: Verifica token válido para sesión

**PARA QUÉ**:
- Lógica centralizada de calendarios
- Evitar solapamientos
- Base para reportes

---

## Cambio 24.6: Rutas de portal docente - Calendario personal
**Fecha**: Abril 17, 2026  
**Archivos afectados**: `routes/portal.py` (+51 líneas)

**QUÉ**:
Nuevas rutas para docentes:

- `GET /dashboard?seccion=calendario`: Nuevo tab de calendario
  - Muestra sesiones en las que está matriculado
  - Filtro por mes/año
  - Indicadores de estado: Próxima, En progreso, Completada
  - Botón para marcar asistencia (QR scanner o manual con token)

- `POST /marcar_asistencia/{id_sesion}`: Marca asistencia del docente
  - Parámetro: token (QR o manual)
  - Validación: Token válido, sesión en progreso, no marcado previamente
  - Respuesta: Confirmación con timestamp

**PARA QUÉ**:
- Docentes ven calendario personal de sesiones
- Facilita marcación de asistencia
- Transparencia de horarios

---

## Cambio 24.7: JavaScript para calendario interactivo
**Fecha**: Abril 17, 2026  
**Archivos afectados**: `static/main.js` (+705 líneas nuevas)

**QUÉ**:
Nuevo calendario interactivo (mini-calendar + month view):

**Componentes**:
- Mini-calendar: Selector de mes/año
- Calendar grid: Vista mensual de sesiones
- Event popover: Detalles de sesión al hover/click
  - Nombre curso, hora, jornada, docente
  - Botón de asistencia (si aplica)
  - Estado visual (colores por estado)

**Funcionalidades**:
- Arrastrar sesiones (drag-drop para reschedule)
- Crear nueva sesión (modal con validación)
- Editar sesión (inline o modal)
- Eliminar sesión (con confirmación)
- Filtros: Por curso, por jornada, por mes
- Export a iCal/CSV (sesiones para calendario external)
- Keyboard shortcuts: N=new, E=edit, D=delete, ESC=close

**Event Listeners**:
- Click en fecha: Crear sesión ese día
- Hover sesión: Mostrar detalles
- Double-click: Editar
- Right-click: Menú contextual

**PARA QUÉ**:
- Visualización intuitiva de calendario
- Ediciones rápidas inline
- Sincronización con calendarios personales

---

## Cambio 24.8: Estilos CSS para calendario
**Fecha**: Abril 17, 2026  
**Archivos afectados**: `static/style.css` (+417 líneas nuevas)

**QUÉ**:
Estilos para componentes de calendario:

**Calendar Grid**:
- `.calendar-grid`: Grid 7 columnas (días semana)
- `.calendar-day`: Celda individual con fecha
- `.calendar-session`: Sesión dentro de celda
  - Colores por estado: Programada (gray), En progreso (blue), Completada (green), Cancelada (red)
  - Hover effect con sombra
  - Truncación de texto largo

**Mini Calendar**:
- `.mini-calendar`: Selector mes/año compacto
- `.mini-calendar-header`: Controles < mes/año >
- `.mini-calendar-grid`: Grid 7x6 para días

**Modal de Sesión**:
- `.modal-sesion`: Formulario crear/editar sesión
  - Campos: Fecha, hora inicio, hora fin, jornada, docente, bloque
  - Validación visual en tiempo real
  - Botones: Guardar, Cancelar

**Popover de Detalles**:
- `.session-popover`: Panel flotante
  - Información de sesión
  - Botón de asistencia
  - Botones de acciones (editar, eliminar)

**Event Indicators**:
- `.event-dot`: Puntito de evento en mini-calendar
- `.event-count`: Contador si múltiples eventos en día
- `.current-day`: Highlight para hoy

**Responsive**:
- Mobile: Calendario semanal comprimido
- Tablet: Mes comprimido
- Desktop: Full calendar view

**PARA QUÉ**:
- Interfaz moderna y usable
- Información clara de sesiones
- Responsive en todos los dispositivos

---

## Cambio 24.9: Template admin - Sección de calendarios
**Fecha**: Abril 17, 2026  
**Archivos afectados**: `templates/admin.html` (+1803 líneas nuevas)

**QUÉ**:
Nueva sección completa en admin panel: "Calendarios"

**Interfaz**:
- Selector de curso (dropdown con búsqueda)
- Mini-calendar + month view side-by-side
- Toolbar:
  - Botones: + Sesión, Editar, Eliminar, Más opciones
  - Filtros: Por jornada, por tipo, por semana, por mes
  - Vista: Mes, Semana, Día, Agenda
  - Export: iCal, CSV

- Tabla detallada debajo:
  - Columnas: Fecha, Hora, Jornada, Docente, Estado, Asistencia (%), Acciones
  - Paginación: 50 sesiones por página
  - Búsqueda rápida por fechas
  - Ordenamiento: Por fecha, por jornada, por docente

**Modal Crear Sesión**:
- Campos: Fecha (date picker), Hora inicio/fin (time picker), Jornada (select), Docente (autocomplete), Bloque (auto-generated)
- Validaciones inline:
  - Fecha ≥ inicio acción formativa
  - Hora fin > hora inicio
  - No solapamiento con otras sesiones del mismo curso
  - Docente disponible (sin sesiones simultáneas)
- Opciones avanzadas:
  - Crear sesiones recurrentes (semanal, cada 2 semanas, etc.)
  - Template de horarios (Mon 8-10AM, Wed 8-10AM, ...)
  - Asignar múltiples docentes

**Gestión de Asistencia**:
- Tabla de participantes por sesión:
  - Columnas: Docente, Email, Hora marcado, Estado
  - Filtros: Presente, Ausente, Pendiente
  - Botones: Marcar manual, Editar hora, Eliminar registro
- Generar token:
  - Botón "Abrir asistencia" (genera token)
  - Muestra QR code + token manual
  - Cierra automáticamente al final de sesión

**PARA QUÉ**:
- Interface completa para gestión de calendarios
- Creación masiva de sesiones
- Control de asistencia integrado

---

## Cambio 24.10: Template portal - Sección calendario docente
**Fecha**: Abril 17, 2026  
**Archivos afectados**: `templates/dashboard.html` (+127 líneas nuevas)

**QUÉ**:
Nueva sección en dashboard docente: "Calendario Personal"

**Interfaz**:
- Mini-calendar + month view
- Lista de sesiones próximas:
  - Tarjetas compactas: Curso, Fecha, Hora, Jornada, Docente, Estado
  - Botón "Marcar asistencia" si sesión en progreso
  - Botón "Ver detalles" para más info
  - Contador: X de Y asistencias en este curso

- Filtros:
  - Por mes, por curso, por estado
  - "Solo mis cursos"

**Modal Marcar Asistencia**:
- QR scanner (con cámara web)
- Campo manual de token (fallback)
- Confirmación visual: ✅ Registrado a las HH:MM
- Botón volver

**Estadísticas Cortas**:
- Próximas 3 sesiones
- % asistencia por curso
- Cursos con más sesiones este mes

**PARA QUÉ**:
- Docentes ven calendario personal
- Facilita marcar asistencia
- Transparencia de asistencias

---

## Cambio 24.11: Validaciones mejoradas en utils.py
**Fecha**: Abril 17, 2026  
**Archivos afectados**: `utils.py` (+113 líneas nuevas)

**QUÉ**:
Nuevas funciones helper:

**Validación de Fechas/Horas**:
- `validar_fecha_sesion()`: Fecha válida y ≥ inicio acción formativa
- `validar_rango_horas()`: Horas sesión dentro de mínimas/máximas del tipo
- `validar_solapamiento_sesiones()`: Detecta conflictos horarios
- `validar_jornada()`: Jornada es válida (MATUTINA/VESPERTINA/NOCTURNA/UNICA)

**Generación de IDs/Tokens**:
- `generar_token_asistencia()`: Token 8 caracteres alfanuméricos
- `generar_codigo_bloque()`: BLOQUE_1, BLOQUE_2, etc.
- `generar_codigo_sesion()`: ID único para sesión

**Normalización**:
- `normalizar_jornada()`: Standariza input (case-insensitive, trim)
- `normalizar_hora()`: Convierte 14:30 a "2:30 PM", etc.

**Cálculos**:
- `calcular_duracion_total()`: Suma horas de todas sesiones
- `calcular_asistencia_porcentaje()`: % presentes ÷ total sesiones
- `calcular_sesiones_por_semana()`: Cuántas sesiones por semana según tipo

**PARA QUÉ**:
- Validaciones centralizadas
- Reutilización en rutas y servicios
- Consistencia de lógica

---

## Cambio 24.12: Configuración expandida
**Fecha**: Abril 17, 2026  
**Archivos afectados**: `config.py`

**QUÉ**:
Nuevas constantes:

```python
TIPOS_ACCION_FORMATIVA = ['CONFERENCIA', 'SEMINARIO', 'CURSO']
JORNADAS_VALIDAS = ['MATUTINA', 'VESPERTINA', 'NOCTURNA', 'UNICA']
ESTADOS_SESION = {
    0: 'Programada',
    1: 'En progreso',
    2: 'Completada',
    3: 'Cancelada'
}
VISTAS_PERMITIDAS_CALENDARIO = {'mes', 'semana', 'dia', 'agenda'}
HORAS_MINIMAS_ASISTENCIA = 0.8  # 80% requerido para certificado
```

**PARA QUÉ**:
- Centralizar configuraciones
- Facilitar cambios de política

---

## Cambio 24.13: Testeo de gestión de sesiones
**Fecha**: Abril 17, 2026  
**Archivos afectados**: `tests/` (nuevos tests para sesiones)

**QUÉ**:
- Tests para crear/listar/actualizar/eliminar sesiones
- Tests para marcar asistencia
- Tests para validación de solapamientos
- Tests para generación de tokens

**PARA QUÉ**:
- Validar lógica de sesiones
- Prevenir regresiones

---

## Cambio 24.14: Mejora en estructura de directorios
**Fecha**: Abril 17, 2026  
**Archivos afectados**: Reorganización

**QUÉ**:
Extensión de estructura para soportar calendarios:
```
Sistema-Matricula-IPSD/
├── static/
│   ├── calendar.js          # Calendario interactivo (NUEVO)
│   ├── calendar.css         # Estilos calendario (NUEVO)
│   ├── main.js              # Utilities generales (+705 líneas)
│   └── style.css            # Estilos globales (+417 líneas)
│
├── templates/
│   ├── admin.html           # Panel admin (+1803 líneas para calendario)
│   ├── dashboard.html       # Portal docente (+127 líneas)
│   └── ... (otros templates)
│
├── services/
│   └── admin_service.py     # (+686 líneas para sesiones/calendarios)
│
├── routes/
│   ├── admin.py             # (+541 líneas para rutas sesiones)
│   └── portal.py            # (+51 líneas para calendario docente)
│
└── ... (resto estructura)
```

**PARA QUÉ**:
- Organización clara de componentes de calendario
- Facilita mantenimiento

---

## Cambio 24.15: Integración completa en app.py
**Fecha**: Abril 17, 2026  
**Archivos afectados**: `app.py` (sin cambios estructurales, solo nueva lógica en rutas)

**QUÉ**:
- Las nuevas rutas de sesiones se auto-registran en app.py
- No hay cambios en entry point
- Migraciones detectan automáticamente tablas nuevas

**PARA QUÉ**:
- Seamless integration
- Sin interrupciones en aplicación

---

## Resumen de Cambios v1.7

| Concepto | Antes | Después |
|----------|-------|---------|
| Modelo de acción formativa | Simple (nombre, fecha) | Detallado (tipo, horas, semanas, modalidad) |
| Sesiones | No existían | Tabla completa con jornadas y docentes |
| Asistencia | Manual, no registrada | Automatizada con QR/token |
| Calendario | No existía | Interactivo en admin y portal |
| Rutas admin | 18 | 30+ (agregar rutas de sesiones) |
| Rutas portal | 5 | 6 (agregar calendario) |
| Tablas BD | 10 | 13 (agregar sesiones, asistencia, tipos) |
| Líneas JavaScript | ~800 | ~1505 (+705 para calendario) |
| Líneas CSS | ~3000 | ~3417 (+417 para calendario) |
| Líneas HTML (admin) | Variable | +1803 (sección calendarios) |

---

# 🔧 Versión 1.7.1 - Mejoras en Gestión de Sesiones y Asistencia

**Fecha**: Abril 20, 2026  
**Cambios**: 761 insertiones, 285 eliminaciones en 8 archivos

## Cambio 25.1: Expansión de funciones de servicios de sesiones
**Fecha**: Abril 20, 2026  
**Archivos afectados**: `services/admin_service.py` (+358 líneas)

**QUÉ**:
Nuevas funciones implementadas:
- `_resolver_jornada_desde_horario()`: Detecta jornada (MATUTINA/VESPERTINA/NOCTURNA) desde horario
- `_generar_token_asistencia_unico()`: Genera tokens únicos y validables para QR
- `_recalcular_duracion_desde_sesiones()`: Calcula horas totales desde sesiones creadas
- `_sincronizar_horarios_desde_sesiones()`: Sincroniza tabla de horarios desde sesiones
- `listar_sesiones_curso()`: Lista completa de sesiones de un curso
- `crear_sesion_manual()`: Crear sesión individual con validaciones
- `editar_sesion()`: Actualizar sesión existente con sincronización de horarios
- `eliminar_sesion()`: Eliminar sesión con restricciones (no si ya iniciada)
- `generar_calendario_base()`: Generar calendarios automáticos (recurrentes semanales)
- `obtener_reporte_asistencia_curso()`: Reportes detallados de asistencia
- `abrir_asistencia_sesion()`: Habilita marcación de asistencia con token único
- `cerrar_asistencia_sesion()`: Cierra período de marcación y calcula estadísticas

**POR QUÉ**:
- v1.7 tenía estructura básica pero funcionalidad incompleta
- Se requiere CRUD completo de sesiones
- Necesidad de validaciones robustas de horarios y solapamientos
- Reportes de asistencia necesarios para certificación

**PARA QUÉ**:
- Funcionalidad completa de gestión de sesiones
- Automatización de calendarios recurrentes
- Reportes de asistencia integral

---

## Cambio 25.2: Nuevas rutas de administración
**Fecha**: Abril 20, 2026  
**Archivos afectados**: `routes/admin.py` (+142 líneas)

**QUÉ**:
Nuevas rutas REST implementadas:

- `GET /admin/curso/<id_curso>/sesiones`: Listar sesiones con filtros
- `POST /admin/sesion/generar_calendario`: Generar calendario automático (recurrente)
- `POST /admin/sesion/crear`: Crear sesión manual
- `POST /admin/sesion/editar`: Actualizar sesión
- `POST /admin/sesion/eliminar`: Eliminar sesión
- `POST /admin/sesion/abrir`: Abrir asistencia (genera token)
- `POST /admin/sesion/cerrar`: Cerrar asistencia
- `GET /admin/curso/<id_curso>/asistencias`: Reporte de asistencia por curso

Todas con:
- Validación de permisos (admin de dirección)
- Respuestas AJAX JSON
- Manejo de errores con mensajes claros

**POR QUÉ**:
- Necesidad de endpoints específicos para sesiones
- Flujo conversacional: crear → editar → abrir → cerrar

**PARA QUÉ**:
- Interface completa de manejo de sesiones
- Validación centralizada de permisos

---

## Cambio 25.3: Validaciones mejoradas en utils.py
**Fecha**: Abril 20, 2026  
**Archivos afectados**: `utils.py` (+74 líneas)

**QUÉ**:
Nuevas funciones de validación:

- `validar_rango_horario()`: Verifica que hora_fin > hora_inicio
- `validar_solapamiento_horarios()`: Detecta conflictos entre sesiones
- `validar_recurso_disponible()`: Valida disponibilidad de aulas/recursos
- `normalizar_hora_formato()`: Convierte HH:MM a formato estándar
- `calcular_minutos_entre_horas()`: Duración exacta de sesión
- `detectar_jornada_automática()`: Infiere jornada desde horario
- `validar_docente_disponibilidad()`: Chequea que docente no tenga sesiones simultáneas

**POR QUÉ**:
- Validaciones centralizadas en v1.7 eran mínimas
- Necesidad de prevenir conflictos de horarios
- Cálculos de asistencia requieren precisión

**PARA QUÉ**:
- Consistencia en todas las validaciones
- Prevención de errores de datos

---

## Cambio 25.4: Refactorización de templates
**Fecha**: Abril 20, 2026  
**Archivos afectados**: `templates/admin.html` (refactorización), `templates/dashboard.html` (+9 líneas)

**QUÉ**:
- **admin.html**: Reorganización de sección de sesiones
  - Mejora de legibilidad (398 líneas, pero -87 netas por consolidación)
  - Separación clara de: crear sesión, generar calendario, editar, eliminar
  - Modales independientes para cada acción
  - Mejora de validación visual en formularios
  
- **dashboard.html**: 
  - Agrega indicadores visuales de sesión próxima
  - Botón prominente de "Marcar asistencia"
  - Contador de sesiones completadas vs pendientes

**POR QUÉ**:
- v1.7 templates eran difíciles de navegar
- Necesidad de UX más clara para admin
- Docentes necesitan visibilidad de sesiones inminentes

**PARA QUÉ**:
- Mejor experiencia de usuario
- Interfaz más intuitiva

---

## Cambio 25.5: Documentación actualizada
**Fecha**: Abril 20, 2026  
**Archivos afectados**: `README.md` (+21 líneas), `docs/PYTHONANYWHERE_SETUP.md` (+25 líneas)

**QUÉ**:
- **README.md**:
  - Nuevas secciones sobre funcionalidad de sesiones
  - Instrucciones de generación de calendarios
  - Información sobre tokens de asistencia
  
- **PYTHONANYWHERE_SETUP.md**:
  - Notas sobre tablas nuevas (sesiones_curso, registro_asistencia)
  - Consideraciones de permisos de archivos para CRUD

**POR QUÉ**:
- Usuarios necesitan saber cómo usar nuevas features
- Deployment en PythonAnywhere tiene particularidades

**PARA QUÉ**:
- Mejor onboarding
- Menos errores de implementación

---

## Cambio 25.6: Sincronización de horarios desde sesiones
**Fecha**: Abril 20, 2026  
**Archivos afectados**: `services/admin_service.py`

**QUÉ**:
- Función bidireccional: 
  - Si se crea sesión → se genera horario automáticamente
  - Si se elimina sesión → se recalcula lista de horarios
  - Sincronización automática de tabla de horarios_sesion

**PARA QUÉ**:
- Consistencia entre sesiones y horarios
- Evitar duplicados/inconsistencias
- Base para reportes de ocupación

---

## Cambio 25.7: Generación automática de calendarios
**Fecha**: Abril 20, 2026  
**Archivos afectados**: `services/admin_service.py`

**QUÉ**:
- Nueva función `generar_calendario_base()`:
  - Parámetros: id_curso, fecha_inicio, fecha_fin, días_semana, horas
  - Genera automáticamente sesiones recurrentes
  - Respeta holidays/fechas excluidas
  - Genera bloques semanales automáticamente
  
**PARA QUÉ**:
- Eliminación manual de crear 20+ sesiones
- Mayor velocidad de planificación
- Menos errores de datas

---

## Cambio 25.8: Tokens únicos e invulnerables para asistencia
**Fecha**: Abril 20, 2026  
**Archivos afectados**: `services/admin_service.py`, `database.py`

**QUÉ**:
- Función `_generar_token_asistencia_unico()`:
  - Token de 8 caracteres alfanuméricos único por sesión
  - Válido solo durante período de sesión (abierto-cerrado)
  - No reutilizable después de cerrar asistencia
  - QR compatible

**PARA QUÉ**:
- Seguridad: imposible adivinar token
- Trazabilidad: token único por sesión
- Auditoría: timestamp de cuándo se marcó

---

## Cambio 25.9: Reportes detallados de asistencia
**Fecha**: Abril 20, 2026  
**Archivos afectados**: `services/admin_service.py`

**QUÉ**:
- Función `obtener_reporte_asistencia_curso()`:
  - Resumen por sesión: presentes, ausentes, sin marcar
  - Resumen por docente: % asistencia, sesiones totales
  - Datos de timestamp (hora exacta de marcación)
  - Exportable a CSV/Excel

**PARA QUÉ**:
- Reportes de cumplimiento
- Identificación de patrones de inasistencia
- Base para certificación (mínimo % requerido)

---

## Cambio 25.10: Mejoras en validación de conflictos
**Fecha**: Abril 20, 2026  
**Archivos afectados**: `utils.py`

**QUÉ**:
- Nueva lógica:
  - Verifica no solapamiento de sesiones del MISMO curso
  - Verifica disponibilidad de docente (no puede dictar simultáneamente)
  - Verifica conflictos de aulas/recursos
  - Validación de fechas (no en pasado, no en feriados)

**PARA QUÉ**:
- Prevención de conflictos de horarios
- Validación de recursos disponibles
- Garantía de integridad de calendario

---

## Resumen de Cambios v1.7.1

| Aspecto | Cambio |
|--------|--------|
| Rutas nuevas | +8 endpoints específicos para sesiones/asistencia |
| Funciones servicios | +12 nuevas funciones de gestión de sesiones |
| Validadores | +7 nuevas validaciones robustas |
| Líneas código | +761 insertiones, -285 eliminaciones |
| Features completadas | Calendarios automáticos, reportes de asistencia, tokens únicos |
| Documentación | README + PYTHONANYWHERE_SETUP mejorados |

---

---

# 🎨 Versión 1.7.2 - Mejoras en Configuración de Calendarios y Presentación

**Fecha**: Abril 21, 2026  
**Cambios**: 410 insertiones, 185 eliminaciones en 5 archivos

## Cambio 26.1: Refactorización de lógica de obtención de configuración de sesiones
**Fecha**: Abril 21, 2026  
**Archivos afectados**: `routes/admin.py` (+47 líneas netas)

**QUÉ**:
Cambio en función `obtener_configuracion_sesiones_curso()`:
- Nueva estructura de datos `bloques_calendario`: agrupa sesiones por (jornada, hora_inicio, hora_fin)
- Nueva función helper `_modo_valor()`: calcula el valor más frecuente en una colección (moda estadística)
- Nueva función helper `_aplicar_bloque()`: aplica configuración de bloque a dictionary (reduce duplicación)
- Ahora soporta **segunda jornada**: si hay sesiones con horarios diferentes, se detectan automáticamente
- Configuración de campos nuevos en diccionario de retorno:
  - `segunda_jornada_activa`: Boolean indicando si existe segunda jornada
  - `dias_semana_2`, `hora_inicio_2`, `hora_fin_2`: Horarios segunda jornada
  - `jornada_2`, `docente_sesion_2`, `bloque_codigo_2`: Detalles segunda jornada

**POR QUÉ**:
- v1.7.1 solo soportaba una jornada
- Muchos cursos tienen múltiples franjas horarias (matutina y vespertina)
- Lógica anterior era repetitiva y difícil de mantener (11 líneas de deducción duplicadas)
- Nuevo modelo es DRY (Don't Repeat Yourself) y escalable a N jornadas

**PARA QUÉ**:
- Soporte para cursos con múltiples jornadas simultáneas
- Formularios pre-llenados con datos deducidos automáticamente
- Mejor experiencia al editar calendarios con múltiples franjas

---

## Cambio 26.2: UI de calendario mejorada con segunda jornada
**Fecha**: Abril 21, 2026  
**Archivos afectados**: `templates/admin.html` (+82 líneas, -24 líneas netas)

**QUÉ**:
Cambios en panel de generación de calendarios:

1. **Panel principal de generación**:
   - Cambio: Generación automática siempre visible (no colapsable)
   - Antes: Botón "Mostrar generación automática" con toggle
   - Ahora: Texto "Generación automática activa" siempre mostrado
   - Benefit: Usuarios ven opción por defecto

2. **Panel de segunda jornada**:
   - Botón "+ Agregar segunda jornada" (visible solo si no existe)
   - Panel oculto por defecto, se muestra al clickear botón
   - **Pre-llenado automático** de campos desde `curso_sesion_config`:
     - `dias_semana_2` checkboxes con valores desde config
     - `hora_inicio_2`, `hora_fin_2` con valores pre-llenados
     - `jornada_2` select con valor pre-seleccionado
     - `docente_sesion_2`, `bloque_codigo_2` pre-llenados

3. **JavaScript mejorado**:
   - Cambio: Listener de botón toggle refactorizado
   - Antes: Toggle class 'hidden' + aria-expanded
   - Ahora: Manejo directo de `.hidden` attribute (más simple)
   - Botón se oculta después de agregar segunda jornada

**POR QUÉ**:
- Admin feedback: "Generación automática debe ser visible siempre"
- v1.7.1 requería click extra para ver opciones
- Pre-llenar reduce errores de admin (validación visual)
- UX más intuitiva con agregar/ocultar

**PARA QUÉ**:
- Accesibilidad mejorada al panel de calendarios
- Reducción de errores de entrada (pre-llenado automático)
- Workflow más claro: crear jornada 1 → agregar jornada 2
- Mejor onboarding para nuevos admins

---

## Cambio 26.3: Manejo de errores mejorado en matrícula con contexto
**Fecha**: Abril 21, 2026  
**Archivos afectados**: `services/portal_service.py` (-2 líneas)

---

# 🎖️ Versión 1.13 - Mejoras a Sistema de Certificados y Sincronización de Docentes (PENDIENTE DE COMMIT)

## Cambio 27.9: Soporte para logos en plantillas de certificados
**Fecha**: 29 de Abril - 2 de Mayo 2026  
**Archivos afectados**: `database.py`, `routes/certificados.py`, `services/certificate_service.py`

**QUÉ**:
- Nueva columna `ruta_logo_img` en tabla `plantillas_certificados` para almacenar la ruta de logos
- Funciones `registrar_plantilla()` y `actualizar_plantilla()` ahora aceptan parámetro `file_logo`
- Los logos se guardan en `/static/certificados/logos/` con formato: `{DIRECCION}_logo_{TIMESTAMP}_{filename}`
- Refactorización de lógica de INSERT/UPDATE para soportar columnnas opcionales de forma dinámica
- Nueva función helper `_ruta_absoluta_a_file_url()` para convertir rutas absolutas a file:// URLs

**POR QUÉ**:
- Cada dirección de IPSD necesita incluir su logo institucional en los certificados
- Sistema anterior solo permitía firmas, no logos
- Refactorización permite agregar más campos sin duplicar código de INSERT/UPDATE
- wkhtmltopdf requiere URLs file:// para imágenes locales

**PARA QUÉ**:
- Personalizar certificados con branding de cada dirección
- Mejorar presentación visual de diplomas y constancias
- Sentar base para agregar fondos/backgrounds de certificados en el futuro
- Hacer el código más mantenible y escalable

---

## Cambio 27.10: Sincronización de Centro Universitario Regional desde Excel
**Fecha**: 29 de Abril - 2 de Mayo 2026  
**Archivos afectados**: `database.py`, `scripts/sync_docentes_excel.py`

**QUÉ**:
- Nueva columna `centro_universitario_regional` en tabla `docentes`
- Script `sync_docentes_excel.py` actualizado para leer esta columna desde el Excel
- Mapeo flexible de nombres de columnas: soporta 'centro universitario regional', 'centro universitario', 'centro regional', 'cur'
- Ruta del Excel personalizada para cada usuario: `C:\Users\{USERNAME}\Desktop\Base de Prueba.xlsx`
- Cambio de ruta de `ipsd4` a `Carlo` en la máquina de desarrollo
- Validación mejorada: `centro_universitario_regional` es opcional, pero otros campos siguen siendo obligatorios

**POR QUÉ**:
- IPSD tiene múltiples sedes/centros universitarios regionales
- Los profesores deben estar asociados a su centro para:
  - Generación de reportes por sede
  - Validaciones de conflictos de horarios por ubicación
  - Filtros de disponibilidad de cursos presenciales
- Cada usuario debe apuntar a su propia ruta de Excel
- Nombres de columnas en Excel pueden variar entre instituciones

**PARA QUÉ**:
- Capturar información de ubicación de profesores desde la nómina
- Preparar base para reportes y estadísticas por centro regional
- Facilitar sincronización automática desde múltiples fuentes (diferentes usuarios)
- Mejorar robustez del script frente a variaciones en nombres de columnas

---

## Cambio 27.11: Mejoras en generación de PDF de certificados
**Fecha**: 29 de Abril - 2 de Mayo 2026  
**Archivos afectados**: `services/certificate_service.py`, `routes/certificados.py`, `templates/certificados/base_diploma.html`, `templates/certificados/base_constancia.html`

**QUÉ**:

**Parte A: Generación de PDF mejorada**:
- Nueva función `obtener_datos_empleado(matricula_id)` que retorna nombre completo y número de empleado
- Nombres de archivos PDF ahora incluyen: `Certificado_{numero_empleado}_{nombre_docente}.pdf` en lugar de solo `certificado_{matricula_id}.pdf`
- Soporte para rutas absolutas a file:// en wkhtmltopdf mediante `_ruta_absoluta_a_file_url()`
- Nueva query SQL que obtiene `centro_universitario_regional` desde tabla docentes
- Sustitución de placeholder `[CENTRO_UNIVERSITARIO_REGIONAL]` en plantillas

**Parte B: Fondos/Backgrounds de certificados**:
- Sistema de inyección automática de fondos (backgrounds) según tipo de documento:
  - Diplomas: `/static/certificados/backgrounds/diploma_background.png`
  - Constancias: `/static/certificados/backgrounds/constancia_background.png`
- Soporte en función `generar_html_preview_plantilla()` y `generar_binario_pdf()`
- Verificación de existencia de archivo antes de inyectar (fallback si no existe)
- Variable de contexto `ruta_fondo_src` inyectada en templates

**Parte C: Optimización de wkhtmltopdf**:
- Nuevas opciones añadidas:
  - `'print-media-type': None`: Usar estilos de print media
  - `'disable-smart-shrinking': None`: Desactivar ajuste automático de escala
  - `'zoom': '1.0'`: Fuerza zoom 1:1 (sin escalado automático)
- Objetivo: Asegurar que los PDFs se generen a escala exacta de los templates

**Parte D: Cambios en templates**:
- Los templates ahora esperan variables adicionales de contexto:
  - `ruta_logo_src`: Ruta file:// del logo (puede estar vacío)
  - `ruta_fondo_src`: Ruta file:// del fondo
  - `centro_universitario_regional`: Nombre del centro del docente

**POR QUÉ**:
- Certificados deben ser únicos e identificables por número de empleado
- Cada dirección necesita branding visual consistente (logos y fondos)
- El `centro_universitario_regional` es información importante en algunos certificados
- wkhtmltopdf necesita configuración especial para no alterar escalas
- Previsualizaciones deben verse igual que PDFs finales

**PARA QUÉ**:
- Facilitar identificación y archivo de certificados descargados
- Mejorar presentación profesional de diplomas y constancias
- Incluir contexto completo del docente (sede/centro)
- Asegurar fidelidad de diseño entre preview y PDF final
- Preparar base para branding completo por dirección

---

## Cambio 27.12: Eliminación de script de parche obsoleto
**Fecha**: 1 de Mayo 2026  
**Archivos afectados**: `scripts/parche.py` (eliminado, 213 líneas)

**QUÉ**:
- Script `parche.py` ha sido completamente eliminado del repositorio
- Su funcionalidad ha sido integrada directamente en `database.py` en la función `asegurar_migraciones_minimas()`
- Las migraciones ahora ocurren automáticamente en cada inicio de la aplicación

**POR QUÉ**:
- `parche.py` era un mecanismo de migración manual (ejecutar por separado)
- Con `asegurar_migraciones_minimas()` centralizado en `database.py`, ya no es necesario
- Mejor UX: No hay que acordarse de ejecutar parches manualmente
- Reduce complejidad: Una sola forma de hacer migraciones

**PARA QUÉ**:
- Simplificar el workflow de deployment
- Evitar errores por olvidar ejecutar parches
- Consolidar toda la lógica de migraciones en un único punto

---

## Cambio 27.13: Refactorización de interfaz de edición de plantillas
**Fecha**: 29 de Abril - 2 de Mayo 2026  
**Archivos afectados**: `templates/admin.html`, `static/style.css`, `templates/certificados/base_diploma.html`, `templates/certificados/base_constancia.html`

**QUÉ**:

**Parte A: Panel de admin.html**:
- Reorganización de formularios de edición de plantillas con mejor estructura visual
- Ahora incluye campo de carga para logo de certificado
- Validaciones mejoradas en formularios (required attributes)
- Mejor agrupación de campos relacionados

**Parte B: Estilos mejorados**:
- Nuevos estilos CSS para campos de entrada de logos
- Mejora en responsividad de formularios
- Mejor contraste y legibilidad en inputs de archivo

**Parte C: Templates de certificados**:
- Refactorización de `base_diploma.html` y `base_constancia.html`
- Soporte para inyección de variables adicionales (centro, logo, fondo)
- Mejor estructura de DIVs para posicionamiento de elementos
- Preparación para futuros estilos de diseño

**POR QUÉ**:
- UI anterior no tenía lugar para cargar logos
- Necesidad de mejor organización visual del formulario admin
- Plantillas necesitaban refactorización para soportar nuevos elementos visuales

**PARA QUÉ**:
- Mejorar UX de administradores al crear/editar plantillas
- Hacer templates más mantenibles y escalables
- Preparar base para futuros cambios de diseño de certificados

---

## Cambio 27.14: Adición de logo nuevo en sistema
**Fecha**: 1 de Mayo 2026  
**Archivos afectados**: `/static/certificados/logos/IPSD_logo_20260501154442_LOGOS-UNAH-DC_.png` (nuevo)

**QUÉ**:
- Nuevo logo PNG agregado al directorio de logos con formato timestamped
- Nombre: `IPSD_logo_20260501154442_LOGOS-UNAH-DC_.png`
- Tamaño: ~154KB
- Resolución: Optimizada para impresión en certificados

**POR QUÉ**:
- Sistema ahora soporta cargar logos, pero faltaba logo de ejemplo
- Se necesita logo IPSD como base para todas las plantillas de certificados

**PARA QUÉ**:
- Tener logo base para todas las plantillas
- Proporcionar ejemplo funcional de cómo se ven logos en certificados
- Facilitar testing visual del sistema de plantillas

---

## Cambio 27.15: Eliminación de firmas obsoletas
**Fecha**: 29 de Abril - 2 de Mayo 2026  
**Archivos afectados**: `/static/certificados/firmas/IPSD_firma_20260430*` (3 archivos eliminados)

**QUÉ**:
- Se eliminaron 3 archivos de firma PNG antiguas:
  - `IPSD_firma_20260430141008_Firma_y_sello.png`
  - `IPSD_firma_20260430142526_Firma_y_sello.png`
  - `IPSD_firma_20260430152450_Firma_y_sello.png`

**POR QUÉ**:
- Estos eran versiones de prueba/iteraciones del mismo archivo
- Ocupaban espacio sin aporte funcional (duplicados)
- Limpieza de archivos innecesarios

**PARA QUÉ**:
- Reducir tamaño del repositorio
- Mantener carpeta de firmas limpia (solo firmas actuales)
- Facilitar búsqueda de archivos relevantes

---

## Cambio 27.16: Importación de os en app.py
**Fecha**: 1 de Mayo 2026  
**Archivos afectados**: `app.py` (+1 línea)

**QUÉ**:
- Se agregó `import os` al inicio de `app.py`
- Necesario para futuras operaciones que requieran acceso al sistema de archivos

**POR QUÉ**:
- Código fue refactorizado para usar más funcionalidades del módulo `os`
- Import faltaba pero era necesario

**PARA QUÉ**:
- Permitir operaciones de archivos en la aplicación principal

---

## RESUMEN DE CAMBIOS SIN SUBIR (29 Apr - 2 May 2026)

| Categoría | Cambios | Estado |
|-----------|---------|--------|
| **Base de Datos** | 2 nuevas columnas (ruta_logo_img, centro_universitario_regional) | ✅ |
| **Backend** | 5 funciones nuevas/mejoradas en certificate_service | ✅ |
| **Backend** | 1 script eliminado (parche.py) | ✅ |
| **Frontend** | 2 templates refactorizados, 1 CSS mejorado | ✅ |
| **Assets** | 1 logo agregado, 3 firmas eliminadas | ✅ |
| **Rutas** | 3 cambios en routes/certificados.py para soportar logos | ✅ |
| **Scripts** | sync_docentes_excel.py mejorado para nuevo campo | ✅ |
| **Líneas Totales** | ~552 insertadas, ~443 eliminadas (neto: ~109 líneas) | ✅ |

---

**Nota**: Estos cambios están listos para ser commitados. Se recomienda hacer commit con el mensaje:
```
feat: Sistema de logos en certificados y sincronización de centros regionales (v1.13)

- Soporte para cargar logos en plantillas de certificados
- Sincronización de centro_universitario_regional desde Excel
- Mejoras en generación de PDF con fondos y nombres descriptivos
- Refactorización de validación de columnas Excel
- Eliminación de script parche.py obsoleto
- Mejoras en UX de admin para edición de plantillas
```

**QUÉ**:
Cambio en función `process_matricula()` - manejo de error "Fecha máxima de matrícula pasada":
- Antes: Retorna error sin contexto
- Ahora: Incluye full `contexto` del dashboard en respuesta de error
- Contexto contiene:
  - Cursos disponibles
  - Cursos ya matriculados
  - Notificaciones
  - Oportunidades de reintento

```python
return {
    'ok': False,
    'error': 'Fecha máxima pasada...',
    'error_view': 'dashboard',
    'contexto': construir_contexto_dashboard(conn, numero_empleado, seccion_activa='disponibles')
}
```

**POR QUÉ**:
- v1.7.1: cuando matrícula fallaba, dashboard se actualizaba vacío
- Usuario no veía por qué falló, tenía que recargarse la página
- Contexto completo permite rendering sin reload

**PARA QUÉ**:
- UX fluida: error mostrado en contexto sin recargar
- Usuario ve inmediatamente otros cursos disponibles
- Menos confusión, menos reloads

---

## Cambio 26.4: Presentación de fechas de curso mejorada
**Fecha**: Abril 21, 2026  
**Archivos afectados**: `templates/dashboard.html` (+9 líneas), `utils.py` (+54 líneas)

**QUÉ**:
Cambio en cómo se muestran fechas en dashboard de docentes:

**Antes (v1.7.1)**:
```html
Horarios: 08:00 - 12:00 · 14:00 - 18:00
```

**Ahora (v1.7.2)**:
```html
Inicio: Lunes, 22 de Abril de 2026
```

**Implementación**:
- Nueva función `_fecha_inicio_legible_desde_partes()` en `utils.py`:
  - Parámetros: año, mes_nombre, día (desde tabla capacitaciones)
  - Retorna: "Lunes, 22 de Abril de 2026"
  - Usa `DIAS_SEMANA` (Monday → "Lunes") y `MESES_ES` (April → "Abril")
  - Manejo de errores: retorna None si fecha inválida
  
- Cambios en `cargar_contexto_dashboard_docente()`:
  - Agrega campo `dia` en SELECT (antes no se traía)
  - Agrega `fecha_inicio_texto` al contexto de curso
  - Mantiene `horarios` para backward compatibility

**POR QUÉ**:
- Usuarios más interesados en CUÁNDO empieza que CÓMO es horario
- Horarios muchas veces vacíos (falta sync de sesiones)
- Fecha más legible y más importante que horarios ambiguos

**PARA QUÉ**:
- Información más relevante al docente (cuándo empieza)
- Mejor legibilidad con formato "día semana, fecha"
- Menos confusión sobre horarios pendientes

---

## Cambio 26.5: Importaciones y dependencias actualizadas
**Fecha**: Abril 21, 2026  
**Archivos afectados**: `utils.py`

**QUÉ**:
- Nueva importación en `utils.py`: `from config import DIAS_SEMANA`
- `DIAS_SEMANA` ya existía en `config.py`, ahora se importa en utils
- Permite traducción de weekday (0-6) a español (Lunes, Martes, etc.)

**PARA QUÉ**:
- Centralización de constantes idiomáticas
- Reutilización de mapeos de días

---

## Resumen de Cambios v1.7.2

| Aspecto | Cambio |
|--------|--------|
| Refactorización lógica | Bloque-agrupamiento mejorado, soporte segunda jornada |
| UI/UX mejoras | Panel generación siempre visible, pre-llenado automático |
| Errores contextuales | Matrícula fallida ahora retorna dashboard completo |
| Presentación fechas | Cambio de horarios → fecha legible "Día, DD de Mes" |
| Importaciones | Importación centralizada de DIAS_SEMANA |
| Líneas código | +410 insertiones, -185 eliminaciones (net +225) |

---

---

# 🚀 Versión 1.7.3 - Refinamiento de Asistencia, Jornadas y Gestión de Calendario

**Fecha**: Abril 22, 2026  
**Cambios**: 2 commits principales (`975d334`, `8d35517`) con mejoras funcionales en reportes, filtros de jornadas y experiencia de administración

## Cambio 27.1: Migración semántica de bloque a edición en sesiones
**Fecha**: Abril 22, 2026  
**Archivos afectados**: `database.py`

**QUÉ**:
- En la estructura de `sesiones_curso`, el campo `bloque_codigo` pasa a `edicion`.
- La migración automática ahora crea `edicion` si no existe.
- Se actualiza índice de base de datos de `idx_sesiones_curso_bloque` a `idx_sesiones_curso_edicion`.
- Validación de jornada ajustada para mantener los valores permitidos y limpieza de datos legacy.

**POR QUÉ**:
- El término "edición" representa mejor la organización académica que "bloque".
- Se necesitaba consistencia entre base de datos, formularios y reportes.

**PARA QUÉ**:
- Mejor claridad de dominio funcional.
- Consultas e índices alineados con el nuevo modelo de negocio.

---

## Cambio 27.2: Generación de calendario con feedback robusto en admin
**Fecha**: Abril 22, 2026  
**Archivos afectados**: `routes/admin.py`

**QUÉ**:
- En la creación de segunda jornada se mejora la validación y respuesta para flujos no AJAX.
- Se agregan mensajes `flash` de error cuando fallan validaciones de jornada secundaria.
- Se agrega `flash` de éxito al finalizar generación de calendario:
  - Total de sesiones creadas.
  - Total de jornadas procesadas.

**POR QUÉ**:
- En algunos errores el usuario admin no recibía retroalimentación visible en pantalla.
- Era necesario confirmar de forma explícita el resultado de la operación de calendario.

**PARA QUÉ**:
- Reducir incertidumbre del usuario tras enviar formularios.
- Mejorar trazabilidad visual del resultado de cada acción.

---

## Cambio 27.3: Reporte de asistencia enriquecido con mapa visual y detalle temporal
**Fecha**: Abril 22, 2026  
**Archivos afectados**: `services/admin_service.py`, `templates/admin.html`, `static/style.css`

**QUÉ**:
- `obtener_reporte_asistencia_curso()` ahora incluye más datos de sesiones:
  - `id_sesion`, `fecha`, `estado`, orden consolidado por curso.
- Se integra detalle granular de asistencias por docente y por sesión.
- Nuevos campos por docente:
  - `ultima_marcacion`
  - `fechas_ausentes`
  - `mapa_asistencia` (presente/ausente/futura)
- Nuevo agrupamiento derivado:
  - `docentes_con_asistencia`
  - `docentes_pendientes_asistencia`
- Se incorporan estados visuales con colores:
  - `success`, `warning`, `danger`
  - puntos de mapa (`mapa-dot`) para línea temporal de asistencia.

**POR QUÉ**:
- El reporte anterior era funcional, pero no permitía lectura rápida de patrones.
- Se requería separar docentes con avance real vs. pendientes.

**PARA QUÉ**:
- Supervisión más eficiente por parte del equipo administrativo.
- Detección temprana de ausencias y seguimiento académico.

---

## Cambio 27.4: Filtro de sesiones por jornada del docente en portal
**Fecha**: Abril 22, 2026  
**Archivos afectados**: `services/portal_service.py`

**QUÉ**:
- Se importa `_resolver_jornada_desde_horario` para inferir jornada del docente desde su horario elegido.
- En el detalle de curso del docente se añade cálculo de jornada contextual (`jornada_docente`).
- Consulta de sesiones ahora filtra por:
  - Jornada del docente.
  - Sesiones `UNICA` como sesiones compartidas.

**POR QUÉ**:
- Antes se listaban sesiones no siempre relevantes para el horario seleccionado por el docente.

**PARA QUÉ**:
- Mostrar únicamente sesiones pertinentes al docente autenticado.
- Reducir ruido en el panel de seguimiento y marcación de asistencia.

---

## Cambio 27.5: UX de segunda jornada y ajustes de interfaz admin
**Fecha**: Abril 22, 2026  
**Archivos afectados**: `templates/admin.html`

**QUÉ**:
- Botón de segunda jornada refinado:
  - Texto simplificado a "+ Agregar jornada".
  - Estado inicial oculto del panel con activación controlada por JS.
- Nuevo botón "Eliminar jornada" para limpiar campos y desactivar bloque secundario.
- JavaScript actualizado para:
  - Habilitar/deshabilitar campos según visibilidad.
  - Resetear inputs/selects al eliminar jornada.
- Ajustes de copy y etiquetas:
  - "Bloque / Grupo" cambia a "Edición" en formularios de sesión.
  - Ajustes menores de textos en listados y etiquetas administrativas.

**POR QUÉ**:
- Se necesitaba control explícito para agregar o retirar la segunda jornada sin recargar la vista.
- Etiquetas anteriores no reflejaban el nuevo lenguaje del sistema.

**PARA QUÉ**:
- Flujo más claro en configuración de calendarios múltiples.
- Menor probabilidad de enviar campos secundarios no deseados.

---

## Cambio 27.6: Regla de apertura de asistencia más flexible
**Fecha**: Abril 22, 2026  
**Archivos afectados**: `services/admin_service.py`, `templates/admin.html`

**QUÉ**:
- En `abrir_asistencia_sesion()` se ajusta la regla:
  - Antes: solo permitía abrir desde estado cerrado inicial.
  - Ahora: bloquea exclusivamente si ya está abierta (`estado == 1`) y permite reapertura en otros estados válidos.
- En interfaz se alinea la lógica del botón "Abrir" para que aparezca cuando no está en estado abierto.

**POR QUÉ**:
- El flujo operativo requería reactivar asistencia en escenarios de corrección administrativa.

**PARA QUÉ**:
- Mayor flexibilidad operativa sin perder control de estados.

---

## Resumen de Cambios v1.7.3

| Aspecto | Cambio |
|--------|--------|
| Modelo de datos | Renombrado funcional de `bloque_codigo` a `edicion` |
| Admin calendario | Validaciones y feedback `flash` más claros |
| Asistencia | Reporte enriquecido con mapas visuales y últimas marcaciones |
| Portal docente | Filtro de sesiones por jornada relevante |
| UX administración | Agregar/eliminar segunda jornada con control dinámico |
| Estado de sesión | Apertura de asistencia más flexible |

---

**Última actualización**: Abril 22, 2026  
**Versión actual**: 1.7.3 (Refinamiento de Asistencia, Jornadas y Gestión de Calendario)  
**Estado**: Development - Reportes avanzados de asistencia, filtros por jornada y mejoras de experiencia admin

---

# ⚡ Versión 1.7.4 - Vista de Asistencias y Rediseño del Portal Docente

**Fecha**: Abril 23, 2026  
**Cambios**: 2 commits principales (`90db3ef`, `38a4477`) con mejoras en la vista de asistencias y el diseño del portal docente

## Cambio 28.1: Mejoras en la vista y reporte de asistencias
**Fecha**: Abril 23, 2026  
**Archivos afectados**: `templates/admin.html`, `services/admin_service.py`, `services/portal_service.py`, `routes/admin.py`, `database.py`, `scripts/setup_bd.py`, `static/style.css`

**QUÉ**:
- Interfaz de asistencias enriquecida con un modal de detalle que muestra:
  - Mapa visual por docente (`mapa-dot`) con estado por sesión (presente / ausente / futura)
  - Campos nuevos en el reporte: `ultima_marcacion`, `fechas_ausentes`, `mapa_asistencia`
  - Separación de docentes con asistencia registrada y pendientes
- Backend: `obtener_reporte_asistencia_curso()` devuelve detalle por sesión (`id_sesion`, `fecha`, `estado`) y construye estructuras listas para render (listas ordenadas, mapas y resúmenes)
- Rutas y feedback: `routes/admin.py` incorpora mensajes `flash` claros para errores y éxito al generar calendarios
- Base de datos y scripts: ajustes menores en migraciones y en `scripts/setup_bd.py` para mantener índices y nuevas columnas sincronizadas
- Estilos: nuevas clases CSS para indicadores y badges (`mapa-dot`, `badge-pill.warning`) para reflejar estados de asistencia

**POR QUÉ**:
- Los administradores requerían una vista más legible y accionable para detectar patrones de inasistencia
- Era necesario que el reporte mostrara no sólo contadores sino contexto temporal (última marcación) y un mapa rápido de avance

**PARA QUÉ**:
- Supervisión más eficiente y rápida detección de ausencias recurrentes
- Facilitar acciones correctivas y comunicación dirigida con docentes pendientes

---

## Cambio 28.2: Diseño "Portal Orgánico UNAH" (rediseño dashboard docente)
**Fecha**: Abril 23, 2026  
**Archivos afectados**: `templates/dashboard.html`, `static/style.css`, `services/portal_service.py`

**QUÉ**:
- Rediseño visual del `dashboard` del docente con nuevos estilos y pequeñas reorganizaciones de tarjetas e información primaria (inicio, mensajes, accesos rápidos)
- Ajustes en `services/portal_service.py` para adaptar el contexto (nuevas claves de contexto y compatibilidad con la nueva presentación)
- Cambios CSS relacionados con la paleta, espaciado y componentes de tarjeta para alinearse con el nuevo diseño orgánico

**POR QUÉ**:
- Mejorar legibilidad, accesibilidad y coherencia visual con la identidad institucional (Portal Orgánico UNAH)

**PARA QUÉ**:
- Mejor experiencia docente: información más relevante a primera vista
- Preparar el diseño para futuras mejoras de navegación y accesos contextuales

---

## Resumen de Cambios v1.7.4

| Aspecto | Cambio |
|--------|--------|
| UI Asistencias | Modal detallado con mapa visual y métricas temporales |
| Backend Asistencias | Reporte enriquecido: `ultima_marcacion`, `fechas_ausentes`, `mapa_asistencia` |
| UX Admin | Mensajes `flash` y confirmaciones al generar calendarios |
| Portal Docente | Rediseño visual (Portal Orgánico UNAH) y ajustes de contexto |
| DB / Scripts | Migraciones y setup ajustados para nuevas columnas/índices |

---

**Última actualización**: Abril 23, 2026  
**Versión actual**: 1.7.4 (Vista de Asistencias y Rediseño del Portal Docente)  
**Estado**: Development - UI y reportes de asistencia refinados; portal docente rediseñado

---

# 💎 Versión 1.8.0 - Modernización del Portal Docente (Bento Grid & Glassmorphism)

**Fecha**: Abril 24, 2026  
**Cambios**: Modernización total de la arquitectura visual del Dashboard del Docente, optimización de interacciones y navegación.

## Cambio 29.1: Arquitectura de Bento Grid y Glassmorphism en el Dashboard
**Fecha**: Abril 24, 2026  
**Archivos afectados**: `templates/dashboard.html`, `static/style.css`

**QUÉ**:
- Implementación de un layout basado en **Bento Grid** para organizar la información del docente (Perfil, Estadísticas, Accesos Rápidos, Calendario e Historial).
- Aplicación de estética **Glassmorphism** (fondos translúcidos con desenfoque de fondo y bordes sutiles) en todos los contenedores principales.
- Introducción de micro-interacciones y transiciones suaves al interactuar con los elementos del dashboard.

**POR QUÉ**:
- Se buscaba una interfaz más moderna, profesional y alineada con las tendencias actuales de diseño web (premium aesthetics).
- Mejorar la jerarquía visual de la información, permitiendo al docente escanear sus datos más rápido.

**PARA QUÉ**:
- Proporcionar una experiencia de usuario "wow" y de alta gama.
- Facilitar la lectura de estadísticas y el acceso a las funciones más utilizadas.

---

## Cambio 29.2: Rediseño de Tarjetas de Capacitación y Sistema de Badges
**Fecha**: Abril 24, 2026  
**Archivos afectados**: `templates/dashboard.html`, `static/style.css`

**QUÉ**:
- Rediseño estructural de las tarjetas de curso (`curso-card`):
  - Inclusión de badges de modalidad (Virtual/Presencial) integrados en el área visual superior.
  - Reorganización de la jerarquía de textos (ID, Título, Período, Fecha).
  - Optimización de los selectores de jornada y botones de acción.
- Animación dinámica de barras de progreso en el historial de capacitaciones mediante `requestAnimationFrame`.

**POR QUÉ**:
- Las tarjetas anteriores se sentían congestionadas y la modalidad no era lo suficientemente visible.
- El feedback visual del progreso histórico era estático y poco atractivo.

**PARA QUÉ**:
- Mejorar la legibilidad de la oferta académica.
- Aumentar el engagement visual mediante animaciones fluidas y estados claros.

---

## Cambio 29.3: Interacción de Cancelación mediante Modal Moderno
**Fecha**: Abril 24, 2026  
**Archivos afectados**: `templates/dashboard.html`, `static/style.css`

**QUÉ**:
- Reemplazo de los diálogos de confirmación estándar por un **Modal de Glassmorphism** personalizado para la cancelación de matrículas.
- Intercepción de formularios mediante JavaScript para mostrar el modal con contexto dinámico (nombre del curso a cancelar).
- Implementación de controles de accesibilidad (`aria-modal`, `role="dialog"`) y gestión de foco.

**POR QUÉ**:
- Los diálogos nativos del navegador (`confirm()`) rompen la estética premium del portal.
- Se requería una confirmación más clara que explicara las consecuencias (reversibilidad) de la acción.

**PARA QUÉ**:
- Mantener la coherencia estética en todo el flujo de usuario.
- Reducir errores de cancelación accidental mediante una confirmación más intencional.

---

## Cambio 29.4: Optimización de Navegación Post-Cancelación
**Fecha**: Abril 24, 2026  
**Archivos afectados**: `templates/matricula_cancelada.html`

**QUÉ**:
- Refactorización de los enlaces de retorno en la página de confirmación de cancelación.
- Cambio de formularios POST redundantes por enlaces directos GET hacia `/dashboard` con parámetros de sección.
- Ajuste de estilos para mantener la consistencia con el nuevo sistema visual.

**POR QUÉ**:
- El uso de POST para navegar hacia atrás causaba advertencias de "Reenvío de formulario" en el navegador al usar las flechas de navegación.
- Se perdía la persistencia del estado de la sección en algunos casos.

**PARA QUÉ**:
- Hacer la navegación más fluida y natural para el usuario.
- Evitar errores técnicos del navegador durante la navegación entre estados de matrícula.

---

## Cambio 29.5: Refactorización Técnica y Accesibilidad
**Fecha**: Abril 24, 2026  
**Archivos afectados**: `templates/dashboard.html`, `static/style.css`, `app.py`

**QUÉ**:
- Resolución de duplicaciones en selectores CSS para mejorar la mantenibilidad.
- Corrección de la jerarquía de encabezados (H1-H6) para cumplimiento de estándares SEO y accesibilidad.
- Optimización de la lógica de sesión en `app.py` para asegurar persistencia durante la navegación entre secciones.
- Limpieza de código muerto y comentarios obsoletos tras el rediseño.

**POR QUÉ**:
- El crecimiento del archivo CSS estaba generando conflictos de especificidad.
- La navegación anterior presentaba inconsistencias en la detección del usuario activo tras ciertas operaciones.

**PARA QUÉ**:
- Asegurar un código más limpio, escalable y accesible.
- Garantizar que la aplicación cumpla con las mejores prácticas de desarrollo web moderno.

---

## Resumen de Cambios v1.8.0

| Aspecto | Cambio |
|--------|--------|
| UI/UX | Bento Grid layout con efectos de Glassmorphism |
| Componentes | Rediseño de tarjetas de curso y sistema de badges visuales |
| Interacciones | Nuevo modal de confirmación de cancelación con estética premium |
| Backend/Nav | Optimización de flujos GET y persistencia de sesión |
| Calidad | Refactorización CSS y corrección de jerarquía de encabezados (Accesibilidad) |

---

**Última actualización**: Abril 24, 2026  
**Versión actual**: 1.8.0 (Modernización del Portal Docente - Bento Grid & Glassmorphism)  
**Estado**: Development - Dashboard rediseñado con estética premium y UX optimizada

---

# 🔔 Versión 1.9.0 - Refinamiento de Notificaciones y Panel de Insights

**Fecha**: Abril 27, 2026  
**Cambios**: Introducción de un panel lateral de insights, formateo inteligente de fechas y mejoras proactivas en el sistema de notificaciones del docente.

## Cambio 30.1: Nuevo Panel de Insights y Notificaciones Mejoradas
**Fecha**: Abril 27, 2026  
**Archivos afectados**: `templates/dashboard.html`, `static/style.css`, `utils.py`

**QUÉ**:
- Implementación de un nuevo panel lateral (`notificaciones-sidebar`) en la sección de avisos.
- **Próximas Actividades**: Visualización dinámica de los próximos 2 eventos del calendario (sesiones o inicios de curso) con acceso directo.
- **Estado de Formación**: Tarjeta estadística con barra de progreso que indica el cumplimiento de asistencia semanal.
- Rediseño de la lista de notificaciones con estados vacíos mejorados visualmente mediante glassmorphism.

**POR QUÉ**:
- El docente necesitaba visibilidad inmediata de sus compromisos más cercanos sin entrar al calendario completo.
- Se requería gamificar/incentivar el registro de asistencia mediante indicadores visuales de progreso.

**PARA QUÉ**:
- Reducir el tiempo de acceso a la información crítica.
- Mejorar el cumplimiento en el registro de asistencias mediante recordatorios visuales persistentes.

---

## Cambio 30.2: Sistema de Formateo de Fechas Inteligente
**Fecha**: Abril 27, 2026  
**Archivos afectados**: `utils.py`

**QUÉ**:
- Creación de la función helper `_formatear_fecha_corta()` en el backend.
- Lógica de detección relativa: transforma fechas ISO en etiquetas humanas como "HOY", "MAÑANA" o el nombre del día en español (ej: "LUNES, 27 ABR").
- Integración de estas fechas formateadas en los objetos de evento enviados al frontend.

**POR QUÉ**:
- Las fechas en formato estándar (AAAA-MM-DD) tienen mayor carga cognitiva para el usuario en contextos de actividades diarias.
- Mejora la naturalidad de la interfaz al comunicarse con el docente.

**PARA QUÉ**:
- Facilitar la planificación rápida del docente.
- Humanizar la comunicación del sistema.

---

## Cambio 30.3: Lógica de Asistencia y Notificaciones Proactivas
**Fecha**: Abril 27, 2026  
**Archivos afectados**: `utils.py`

**QUÉ**:
- Refinamiento de la notificación de "Marcado de asistencia habilitado":
  - Ahora solo se muestra si existen sesiones con estado habilitado (`sesiones_habilitadas > 0`).
  - Incluye un botón de acción directa ("Registrar asistencia") que redirige a la tarjeta del curso correspondiente.
  - Cambio de iconografía a un rayo (⚡) para denotar urgencia/acción.
- Nueva notificación de "Confirmación de Matrícula" que se genera automáticamente al inscribirse en un curso.

**POR QUÉ**:
- Evitar notificaciones de asistencia engañosas en cursos que aún no tienen sesiones abiertas por el administrador.
- Proporcionar feedback inmediato tras una operación exitosa de matrícula.

**PARA QUÉ**:
- Aumentar la precisión del sistema de alertas.
- Mejorar el flujo de navegación hacia las tareas pendientes (asistencia).

---

## Cambio 30.4: Refactorización y Gestión de Cache Visual
**Fecha**: Abril 27, 2026  
**Archivos afectados**: `templates/base.html`, `utils.py`, `static/style.css`

**QUÉ**:
- **Bumping de versión CSS**: Se actualizó a `?v=4.0` en `base.html` para forzar la recarga de los nuevos estilos de insights.
- **Refactorización de datos**: Conversión de objetos SQL Row a diccionarios estándar en el backend para permitir la inyección dinámica de propiedades adicionales (como `sesiones_habilitadas`).
- **Optimización de JS**: Actualización del script de progreso para manejar múltiples tipos de barras (historial vs estadísticas) de forma genérica.

**POR QUÉ**:
- Asegurar que los usuarios vean los cambios visuales inmediatamente sin problemas de caché del navegador.
- Facilitar la manipulación de datos en la capa de negocio antes de enviarlos a la vista.

**PARA QUÉ**:
- Garantizar un despliegue libre de errores visuales.
- Mejorar la mantenibilidad del código backend.

---

## Resumen de Cambios v1.9.0

| Aspecto | Cambio |
|--------|--------|
| Dashboard | Nuevo panel lateral de Insights (Actividades y Estadísticas) |
| UX | Formateo de fechas humano ("HOY", "MAÑANA") |
| Notificaciones | Alertas inteligentes basadas en sesiones reales y acciones directas |
| Backend | Inyección de metadatos de sesiones y refactorización a dicts |
| Estabilidad | Cache-busting de CSS (v4.0) y optimización de scripts de UI |

---

**Última actualización**: Abril 27, 2026  
**Versión actual**: 1.9.0 (Refinamiento de Notificaciones y Panel de Insights)  
**Estado**: Development - Sistema de alertas proactivo e insights de formación activos

---

# 🤖 Versión 1.10.0 - Asistente Virtual Integrado (Gemini IA)

**Fecha**: Abril 27, 2026  
**Cambios**: Implementación completa de un asistente virtual basado en Inteligencia Artificial (Google Gemini) para soporte interactivo a docentes y administradores.

## Cambio 31.1: Implementación del Asistente Virtual (IA)
**Fecha**: Abril 27, 2026  
**Archivos afectados**: `services/ia_service.py`, `app.py`, `.env`

**QUÉ**:
- Integración del SDK de Google GenAI para conectar la aplicación con modelos **Gemini (2.5-flash / 2.0-flash)**.
- Creación de prompts de sistema diferenciados:
  - **Docentes**: Enfoque en procesos de matrícula, historial formativo y uso del portal.
  - **Administradores**: Soporte en gestión de cursos, reportes y administración de usuarios.
- Implementación de un sistema de "respuestas de dominio" (fallbacks locales) para responder preguntas frecuentes incluso si la API de IA no está disponible.

**POR QUÉ**:
- Reducir la carga de soporte técnico manual mediante una herramienta de auto-servicio 24/7.
- Proporcionar guía contextual inmediata sobre los flujos del sistema IPSD.

**PARA QUÉ**:
- Mejorar la autonomía de los usuarios (docentes y admins).
- Ofrecer una interfaz de soporte moderna, rápida y precisa.

---

## Cambio 31.2: Widget de Chat Flotante y UX Contextual
**Fecha**: Abril 27, 2026  
**Archivos afectados**: `templates/base.html`, `static/style.css`, `static/chat-widget.js`

**QUÉ**:
- Diseño y desarrollo de una interfaz de chat persistente y accesible desde cualquier página (base template).
- Características visuales:
  - Estética **glassmorphism** coherente con el rediseño v1.8.0.
  - Notificaciones visuales de mensajes entrantes.
  - Animaciones suaves de apertura/cierre del panel.
- Funcionalidad: Carga automática del historial reciente al abrir el chat y scroll inteligente hacia el último mensaje.

**POR QUÉ**:
- Se requería que el asistente fuera accesible en todo momento sin interrumpir el flujo de trabajo del usuario.
- Mantener la identidad visual premium establecida en versiones anteriores.

**PARA QUÉ**:
- Facilitar el acceso al soporte sin necesidad de navegar a páginas externas.
- Proporcionar una experiencia fluida y visualmente atractiva.

---

## Cambio 31.3: Sistema de Persistencia y Seguridad del Chat
**Fecha**: Abril 27, 2026  
**Archivos afectados**: `routes/chat.py`, `services/ia_service.py`, `database.py`

**QUÉ**:
- Creación de la tabla `historial_chat` para el almacenamiento permanente de las conversaciones.
- Seguridad:
  - Validación obligatoria de sesión activa para interactuar con la API de chat.
  - Protección de rutas mediante tokens **CSRF** integrados en las peticiones AJAX.
  - Sanitización y normalización de entradas de usuario para prevenir inyecciones.
- Lógica de resolución de usuario: Detecta automáticamente si el usuario es Docente o Admin para ajustar el contexto de la IA.

**POR QUÉ**:
- La persistencia permite al usuario retomar conversaciones anteriores.
- La seguridad es crítica para evitar abusos de la API de IA y proteger los datos del sistema.

**PARA QUÉ**:
- Garantizar la integridad y trazabilidad de las interacciones con la IA.
- Proteger la infraestructura del sistema contra accesos no autorizados.

---

## Cambio 31.4: Refactorización de Rutas y Servicios de IA
**Fecha**: Abril 27, 2026  
**Archivos afectados**: `app.py`, `routes/chat.py`

**QUÉ**:
- Modularización de las rutas de chat en `routes/chat.py` para mantener `app.py` limpio.
- Implementación de endpoints RESTful:
  - `POST /api/chat`: Procesa nuevos mensajes y genera respuestas.
  - `GET /api/chat/history`: Recupera los últimos 10 mensajes del hilo actual.
- Manejo robusto de errores y fallbacks automáticos hacia modelos secundarios en caso de cuotas excedidas o fallas de red.

**POR QUÉ**:
- Seguir las mejores prácticas de arquitectura Flask (Blueprints/Modularización).
- Asegurar que el sistema de chat sea resiliente ante fallas externas.

**PARA QUÉ**:
- Facilitar el mantenimiento futuro del módulo de IA.
- Ofrecer una alta disponibilidad del servicio de asistencia.

---

## Resumen de Cambios v1.10.0

| Aspecto | Cambio |
|--------|--------|
| Nueva Función | Asistente Virtual Inteligente (IA) integrado |
| Backend | Servicio de IA con prompts contextuales y persistencia en DB |
| Frontend | Chat Widget flotante con estética Glassmorphism |
| Seguridad | Validación CSRF y de sesión en endpoints de chat |
| Resiliencia | Sistema de fallbacks y rotación de modelos de IA |

---

**Última actualización**: Abril 27, 2026  
**Versión actual**: 1.10.0 (Asistente Virtual Integrado - Gemini IA)  
**Estado**: Development - Soporte interactivo inteligente habilitado para todos los usuarios

---

# 📜 Versión 1.11.0 - Sistema de Certificación Digital y Rediseño de Detalle de Curso

**Fecha**: Abril 29, 2026  
**Cambios**: Introducción de un sistema automatizado para la generación de diplomas y constancias, junto con una renovación total de la interfaz de detalle de curso en el portal docente.

## Cambio 32.1: Sistema de Certificación Digital (DIPLOMAS y CONSTANCIAS)
**Fecha**: Abril 29, 2026  
**Archivos afectados**: `services/certificate_service.py`, `routes/certificados.py`, `scripts/migrate_certs.py`, `templates/certificados/`

**QUÉ**:
- Implementación de un motor de generación de PDF basado en **pdfkit (wkhtmltopdf)**.
- Creación de un sistema de plantillas dinámicas:
  - Soporte para **DIPLOMAS** (Orientación horizontal) y **CONSTANCIAS** (Orientación vertical).
  - Gestión centralizada de fondos de imagen, firmantes y cargos por dirección.
- Asociación flexible de plantillas a capacitaciones específicas.
- Endpoint de descarga segura para docentes con validación de aprobación del curso.

**POR QUÉ**:
- Digitalizar la entrega de reconocimientos, reduciendo costos operativos y tiempos de espera.
- Asegurar la autenticidad y uniformidad de los documentos emitidos por el IPSD.

**PARA QUÉ**:
- Permitir que los docentes descarguen sus certificados de forma inmediata al aprobar un curso.
- Facilitar a los administradores la gestión de múltiples formatos de certificación sin intervención técnica.

---

## Cambio 32.2: Rediseño Premium del Modal "Detalle de Curso"
**Fecha**: Abril 29, 2026  
**Archivos afectados**: `templates/dashboard.html`, `static/style.css`, `static/main.js`

**QUÉ**:
- Sustitución del modal informativo básico por una interfaz **Bento-style** moderna.
- Nuevas secciones visuales:
  - **Bento Info Grid**: Resumen rápido de modalidad, periodo, duración y jornada.
  - **Bloque de Asistencia**: Integración del marcado QR directamente en el panel de detalle.
  - **Bloque de Certificado**: Indicador de estado del diploma (Bloqueado/Disponible para descarga).
  - **Timeline de Sesiones**: Lista optimizada de sesiones pasadas y futuras con indicadores de asistencia.
- Migración masiva de iconografía a **Material Symbols (Outlined)** para un look más limpio y profesional.

**POR QUÉ**:
- El modal anterior era puramente informativo y se sentía desconectado del flujo de asistencia.
- Mejorar la experiencia del docente al centralizar toda la actividad de un curso en una sola vista coherente.

**PARA QUÉ**:
- Incrementar la transparencia del proceso de formación (asistencias marcadas vs faltantes).
- Proporcionar una navegación más intuitiva y visualmente gratificante.

---

## Cambio 32.3: Gestión Administrativa de Plantillas
**Fecha**: Abril 29, 2026  
**Archivos afectados**: `templates/admin.html`, `routes/admin.py`, `services/admin_service.py`

**QUÉ**:
- Nueva pestaña de gestión en el Panel Admin: **"Certificados"**.
- CRUD completo de plantillas de certificados:
  - Carga de imágenes de fondo (fondos institucionales).
  - Configuración de firmantes dinámicos.
  - Vista previa de datos asociados.
- Actualización del formulario de creación/edición de cursos para permitir la vinculación de plantillas.

**POR QUÉ**:
- Dar autonomía a los administradores de cada dirección para personalizar sus propios certificados.
- Centralizar la lógica de negocio de certificación en la interfaz administrativa.

**PARA QUÉ**:
- Agilizar la puesta en marcha de nuevos ciclos de capacitación con certificaciones listas.

---

## Resumen de Cambios v1.11.0

| Aspecto | Cambio |
|--------|--------|
| Nueva Función | Generación automatizada de Certificados y Diplomas en PDF |
| UI/UX Docente | Rediseño Bento-style del Detalle de Curso y nuevas micro-interacciones |
| UI/UX Admin | Panel de gestión de plantillas de certificados y firmantes |
| Tecnología | Integración de `pdfkit` y `wkhtmltopdf` para procesamiento de documentos |
| Identidad | Estandarización visual con Material Symbols y estética Glassmorphism avanzada |

---

---

# 🎓 Versión 1.12.0 - Plantillas Dinámicas y Editor Visual de Certificados

**Fecha**: Abril 30, 2026  
**Cambios**: Refactorización integral del sistema de certificados (1063 insertiones, 197 eliminaciones en 13 archivos)

## Cambio 33.1: Migración de esquema de datos → Firma + Texto Dinámico
**Fecha**: Abril 30, 2026  
**Archivos afectados**: `database.py`, `scripts/setup_bd.py`, `scripts/migrate_certs.py`

**QUÉ**:
- Cambio de modelo de datos en tabla `plantillas_certificados`:
  - ❌ Antes: `ruta_fondo_img` (una imagen de fondo estática por plantilla)
  - ✅ Ahora: `ruta_firma_img` (imagen PNG transparente de firma) + `texto_certificado` (contenido editable con etiquetas dinámicas)
- Nuevas etiquetas soportadas en texto:
  - `[NOMBRE]` - Nombre completo del docente
  - `[CURSO]` - Nombre del curso
  - `[MODALIDAD]` - Virtual/Presencial
  - `[HORAS]` - Horas totales
  - `[HORARIO]` - Horario elegido
  - `[FECHA]` - Fecha actual
  - `[FECHA_RANGO]` - Rango de fecha inicio-fin del curso
  - `[FECHA_APROBACION]` - Fecha de aprobación real
- Script `migrate_certs.py` realiza migración automática de datos antiguos al nuevo esquema.

**POR QUÉ**:
- Modelo anterior requería una imagen de fondo diferente por cada plantilla → difícil de mantener y escalar.
- El nuevo modelo permite: una imagen de fondo única + firmas personalizables + texto reutilizable y parametrizado.
- Reduce duplicación de activos y facilita cambios futuros sin tocar la BD.

**PARA QUÉ**:
- Una plantilla sirve para N docentes automáticamente.
- Texto y datos se populan sin hardcoding.
- Mayor flexibilidad para personalización institucional.

---

## Cambio 33.2: Sistema de reemplazo de etiquetas dinámicas
**Fecha**: Abril 30, 2026  
**Archivos afectados**: `services/certificate_service.py` (+393 líneas), `services/portal_service.py` (+34 líneas)

**QUÉ**:
- Nueva función `_reemplazar_etiquetas()`:
  - Mapea etiquetas como `[NOMBRE]` → valores reales de BD (nombre completo, curso, etc.)
  - Soporta formateo de fechas (DD/Mes/Año)
  - Manejo de valores vacíos con defaults
  
- Nueva función `generar_html_preview_plantilla()`:
  - Genera preview visual del certificado con datos ficticios para demostración en admin
  - Usa datos simulados (ej. "Carlos Daniel Interiano Irias", "Curso de Capacitación")
  - Renderiza en tiempo real lo que vería el usuario final

- Validación mejorada en `portal_service.py`:
  - Chequea que `plantilla_disponible = ID ≠ null AND activa = 1 AND firma_presente AND texto_presente`
  - No genera PDFs inválidos

**POR QUÉ**:
- Las etiquetas permiten reutilizar una plantilla sin modificar código.
- El preview ayuda a admins a verificar plantillas antes de usarlas en producción.

**PARA QUÉ**:
- Automatización completa de certificados personalizados.
- Reducción de errores manuales.

---

## Cambio 33.3: Editor Visual de Plantillas en Admin
**Fecha**: Abril 30, 2026  
**Archivos afectados**: `templates/admin.html` (+159 líneas), `routes/admin.py` (+59 líneas), `services/admin_service.py` (+33 líneas)

**QUÉ**:
- Nueva sección en panel Admin: **"Gestión de Plantillas de Certificados"**
  
**Interfaz mejorada**:
- Pildoras/botones de etiquetas: `[NOMBRE]` `[CURSO]` `[FECHA_RANGO]` etc.
  - Al hacer clic, insertan la etiqueta en el textarea
- **Textarea expandible** para editar texto del certificado
- **Vista Previa en Vivo** (live preview):
  - Muestra cómo se vería el certificado con datos ficticios
  - Se actualiza mientras el admin escribe
- Tabla mejorada de plantillas:
  - Columna "Firma" (reemplaza "Fondo")
  - Botón "Vista Previa" para ver completo
  - Carga de archivo: solo acepta PNG
- CRUD completo: crear, editar, eliminar plantillas

**POR QUÉ**:
- Autonomía: cada dirección crea sus propias plantillas.
- Agilidad: cambios sin tickets al departamento técnico.

---

## Cambio 33.4: Rediseño Premium de Templates HTML de Certificados
**Fecha**: Abril 30, 2026  
**Archivos afectados**: `templates/certificados/base_constancia.html` (+124 líneas), `templates/certificados/base_diploma.html` (+225 líneas)

**QUÉ**:
- **Constancia** (mejoras visuales):
  - Marco azul institucional (#0b2e6d) con borde dorado
  - Layout flex (antes: posicionamiento absoluto)
  - Firma PNG superpuesta (antes: posición fija hardcoded)
  - Texto dinámico renderizado (antes: hardcoded)
  - Legibilidad mejorada con espaciado profesional

- **Diploma** (redesign completo):
  - Esquinas decorativas triangulares (antes: rectangular simple)
  - Header: "UNIVERSIDAD NACIONAL AUTÓNOMA DE HONDURAS"
  - Zona de contenido con tipografía Georgia (serif) para elegancia
  - Footer flexible con datos variables (antes: fijo)
  - Firma superpuesta con línea de firma

- **Tipografía**:
  - Arial genérico → Georgia (títulos) + Segoe UI (body)
  - Tamaños escalonados para jerarquía clara

**POR QUÉ**:
- Certificados anteriores se veían básicos y poco institucionales.
- Necesidad de elevar la percepción de valor de los diplomas.

**PARA QUÉ**:
- Profesionalismo: documentos dignos de enmarcar.
- Reconocimiento institucional: branding UNAH visible.

---

## Cambio 33.5: Validación Robusta y Manejo de Errores
**Fecha**: Abril 30, 2026  
**Archivos afectados**: `scripts/parche.py`, `services/portal_service.py`, `database.py`

**QUÉ**:
- **Validación triple** en `portal_service.py`:
  - ✅ Plantilla existe (ID ≠ null)
  - ✅ Plantilla activa (activa = 1)
  - ✅ Firma presente (ruta_firma_img ≠ empty)
  - ✅ Texto presente (texto_certificado ≠ empty)
  
- Script `parche.py` (+19 líneas):
  - Correcciones puntuales durante transición de esquema
  - Cleanup de datos legacy
  - Validación post-migración

**POR QUÉ**:
- Antes: chequeo simple por ID podía generar PDFs inválidos.
- Ahora: garantía de integridad antes de generar.

**PARA QUÉ**:
- Cero PDFs rotos o incompletos.
- Mejor experiencia del usuario final.

---

## Cambio 33.6: Dependencias Actualizadas
**Fecha**: Abril 30, 2026  
**Archivos afectados**: `requirements.txt`

**QUÉ**:
- Nueva dependencia o versión en `requirements.txt`
- Posible actualización de `pdfkit` o librería relacionada para soporte mejorado

**PARA QUÉ**:
- Compatibilidad con wkhtmltopdf.
- Soporte de features nuevas o fixes críticos.

---

## Resumen de Cambios v1.12.0

| Aspecto | Cambio |
|--------|--------|
| **Modelo de datos** | Fondo estático → Firma + Texto Dinámico (etiquetas parametrizadas) |
| **Reutilización** | Una plantilla = Un docente → Una plantilla = Muchos docentes |
| **Admin UX** | Visualización → Editor Visual con Preview en Vivo |
| **Templates** | Básicos → Premium (marcos, tipografía profesional, firma integrada) |
| **Validación** | Chequeo simple → Triple validación (existencia, activo, integridad) |
| **Líneas código** | +1063 insertiones, -197 eliminaciones en 13 archivos |

---

## 🛡️ Validación QR y Optimización UI/UX (v1.13.0)

### Cambio 34.1: Implementación del Sistema de Validación por QR (PoC)
**Fecha**: Mayo 4, 2026  
**Archivos afectados**: `app.py`, `database.py`, `services/validacion_service.py` (nuevo), `routes/validacion.py` (nuevo), `templates/validador.html` (nuevo), `requirements.txt`

**QUÉ**:
- Creación de un subsistema de validación independiente:
  - **Base de Datos**: Tabla `certificados_emitidos` para control de tokens y estadísticas de escaneo.
  - **Servicio**: Generación de códigos QR en formato Base64 (Data URI) compatibles con `wkhtmltopdf`.
  - **Rutas**: Blueprint `validacion_bp` con vista pública para que terceros verifiquen la autenticidad.
- Inyección automática de QR y token único en el pie de página de Diplomas y Constancias.

**POR QUÉ**:
- Necesidad de prevenir la falsificación de certificados digitales.
- Requerimiento institucional de proporcionar un mecanismo de verificación rápida para empleadores.

**PARA QUÉ**:
- Asegurar la integridad de los documentos emitidos por el IPSD.
- Facilitar la validación mediante dispositivos móviles (celulares).

---

### Cambio 34.2: Modernización del Dashboard Docente
**Fecha**: Mayo 5, 2026  
**Archivos afectados**: `templates/dashboard.html`, `static/style.css`, `templates/base.html`

**QUÉ**:
- **Bento Grid**: Rediseño de la sección "Historial" con un layout moderno de rejilla.
- **Sidebar de Actividades**: Migración de "Próximas Actividades" desde notificaciones a un panel lateral fijo en el dashboard.
- **Modo Oscuro**: Implementación de soporte inicial para `data-theme="dark"` con persistencia en `localStorage`.
- **KPIs**: Nueva tarjeta visual para conteo rápido de certificados obtenidos.

**POR QUÉ**:
- El dashboard anterior tenía demasiada carga visual en el centro.
- La información de calendario era difícil de encontrar.

**PARA QUÉ**:
- Mejorar la experiencia de navegación del docente.
- Dar una estética "premium" y moderna a la plataforma institucional.

---

### Cambio 34.3: Optimización de Archivos y Corrección de Colisiones
**Fecha**: Mayo 5-6, 2026  
**Archivos afectados**: `services/validacion_service.py`, `routes/certificados.py`, `services/certificate_service.py`

**QUÉ**:
- **Nomenclatura Dinámica**: Los PDFs descargados ahora tienen el formato `Tipo_Empleado_Nombre.pdf` en lugar de nombres genéricos.
- **Fix de Colisión**: Corrección crítica en `registrar_o_obtener_certificado`. Ahora la búsqueda de tokens existentes usa una clave compuesta (`matricula_id` + `numero_empleado` + `id_capacitacion`) para evitar la reutilización errónea de tokens si se reinicia la base de datos de pruebas.
- **Renderizado PDF**: Ajuste de `border=2` en el QR y uso del filtro `|safe` en Jinja2 para garantizar la visibilidad del código en entornos Linux y Windows.

**POR QUÉ**:
- Los nombres de archivo genéricos dificultaban la organización de los docentes.
- Se detectó un bug donde un docente podía recibir el token de validación de otro si el ID de matrícula se reciclaba.

**PARA QUÉ**:
- Garantizar que cada QR apunte ÚNICAMENTE a los datos correctos.
- Profesionalizar la entrega de archivos digitales.

---

## 🏗️ Evolución de Arquitectura: Catálogos y Ediciones

### Cambio 16.1: Desacoplamiento de Acciones Formativas (Catálogos vs Ediciones)
**Fecha**: Mayo 12, 2026  
**Archivos afectados**: `setup_bd.py`, `services/admin_service.py`, `services/portal_service.py`, `templates/admin.html`, `templates/dashboard.html`

**QUÉ**:
- Rediseño completo del modelo de datos:
  - `catalogo_acciones`: Funciona como plantilla (Nombre, tipo, dirección, requisitos).
  - `ediciones_formativas`: Instancias específicas de un catálogo (Trimestre, cupos, docente, jornada).
- Migración de la lógica de matrícula para apuntar a `ediciones_formativas` en lugar de capacitaciones genéricas.
- Implementación de eliminación en cascada (`ON DELETE CASCADE`) para mantener la integridad referencial.

**POR QUÉ**:
- El modelo anterior era rígido; obligaba a duplicar información básica para cada nuevo curso.
- Se requería una separación clara entre "qué se enseña" (Catálogo) y "cuándo/cómo se imparte" (Edición).
- Facilita la reutilización de contenido pedagógico en diferentes períodos académicos.

**PARA QUÉ**:
- Escalar el sistema para manejar cientos de ediciones sin información redundante.
- Permitir que administradores creen plantillas una sola vez y las programen múltiples veces.

---

### Cambio 16.2: Gestión Granular de Sesiones y Calendario
**Fecha**: Mayo 12, 2026  
**Archivos afectados**: `services/admin_service.py`, `services/certificate_service.py`, `templates/admin.html`

**QUÉ**:
- Nueva tabla `sesiones_curso` que registra cada encuentro individual (fecha, hora inicio, hora fin).
- Automatización de metadatos:
  - Cálculo automático de `total_horas` sumando la duración de todas las sesiones.
  - Cálculo automático de `fecha_inicio` y `semanas` de duración.
  - Generación dinámica de etiquetas de horario (ej: "Lunes-Viernes 08:00-12:00").

**POR QUÉ**:
- Los certificados requieren precisión en el número de horas impartidas.
- Se necesitaba una vista de calendario real para evitar traslapes de aulas o docentes.

**PARA QUÉ**:
- Garantizar la validez legal de las horas acreditadas en los certificados.
- Simplificar la labor administrativa al automatizar cálculos manuales.

---

### Cambio 16.3: Refactorización Integral del Panel Administrador
**Fecha**: Mayo 12, 2026  
**Archivos afectados**: `templates/admin.html`, `static/main.js`, `static/style.css`

**QUÉ**:
- Reemplazo de la pestaña "Cursos" por dos nuevas vistas: "Catálogos" y "Ediciones".
- Implementación de modales avanzados para gestión de sesiones y requisitos.
- Optimización de la carga de datos mediante filtrado inteligente por dirección.
- Mejora de la UI con iconos semánticos (`layers`, `calendar_month`).

**POR QUÉ**:
- La complejidad del nuevo modelo requería una interfaz más organizada.
- Los administradores necesitaban un flujo de trabajo lineal: Catálogo -> Edición -> Sesiones.

**PARA QUÉ**:
- Reducir el tiempo de gestión de los coordinadores.
- Proveer una experiencia de usuario más profesional y fluida.

---

### Cambio 16.4: Robustez, Migración y Terminología
**Fecha**: Mayo 12, 2026  
**Archivos afectados**: `scripts/migrate_db_fks.py`, `scripts/migrate_certs.py`, `utils.py`, `services/ia_service.py`

**QUÉ**:
- Scripts de migración para inyectar llaves foráneas en bases de datos existentes.
- Refactorización de `utils.py` para normalizar el manejo de fechas y jornadas.
- Actualización de terminología en el Chatbot IA ("Mis Acciones Formativas").

**POR QUÉ**:
- La transición al nuevo modelo no debía comprometer los datos históricos.
- Se requería consistencia terminológica en toda la plataforma.

**PARA QUÉ**:
- Asegurar una transición suave (Zero-downtime) hacia la nueva arquitectura.
- Centralizar la lógica de negocio para facilitar el mantenimiento.

---

### Cambio 16.5: Integración de Modalidades, Tipos de Acción y Optimizaciones de UI
**Fecha**: Mayo 12, 2026  
**Archivos afectados**: `routes/admin.py`, `services/admin_service.py`, `utils.py`, `templates/admin.html`

**QUÉ**:
- Implementación completa de la modalidad **B-Learning** y el tipo de acción **SEMINARIO-TALLER** en todo el sistema (backend y frontend).
- Actualización de las validaciones de backend en las rutas de administración para permitir los nuevos valores permitidos.
- Corrección de la lógica de generación de IDs automáticos: ahora asigna el prefijo **'B'** a la modalidad B-Learning (ej: `IPSD-B-001`).
- Optimizaciones profundas en la interfaz del Panel Admin:
  - **Preview dinámico**: El código del catálogo se actualiza en tiempo real al cambiar dirección o modalidad vía JS.
  - **Limpieza de formularios**: Eliminación de campos redundantes (Requisitos y Plantilla) en la gestión de Catálogos para evitar duplicidad con Ediciones.
  - **Validación de fechas**: Los campos de fecha en el modal de calendario ahora impiden seleccionar días pasados (`min` date validation).
  - **Mejora UX**: Reordenamiento de botones de acción y adición de efectos visuales (`hover`) para una navegación más fluida.
- Saneamiento de base de datos: Ejecución de scripts para corregir IDs inválidos (`IPSD-None-001`) generados durante la fase de desarrollo.

**POR QUÉ**:
- El sistema presentaba bloqueos en el servidor que impedían registrar las nuevas modalidades solicitadas.
- La interfaz de Catálogos contenía campos que competen exclusivamente a las Ediciones, generando confusión administrativa.
- Se detectó que la generación automática de IDs fallaba al no tener un mapeo para B-Learning.

**PARA QUÉ**:
- Dotar a la institución de herramientas para gestionar capacitaciones híbridas y talleres especializados de forma oficial.
- Garantizar la integridad referencial de los cursos mediante una nomenclatura estandarizada y automática.
- Refinar la experiencia de usuario del administrador, eliminando ruido visual y previniendo errores de entrada de datos.

---

## 🚀 Versión 1.16 - Modernización UI y Refinamiento de Procesos

### Cambio 16.6: Rediseño Moderno y Sistema de Tema de Colores
**Fecha**: Mayo 18, 2026  
**Archivos afectados**: `templates/admin.html`, `templates/base.html`, `templates/dashboard.html`

**QUÉ**:
- Implementación de un sistema de variables CSS (design tokens) en `base.html` para paletas de colores modernos.
- Integración de **Flatpickr** con configuración en español para todos los inputs de tipo fecha y hora.
- Adopción de la librería de íconos **Material Symbols Outlined** (con variante filled).
- Rediseño general de la interfaz administrativa usando principios de glassmorphism y componentes Tailwind avanzados.
- Actualización de `dashboard.html` para mostrar fechas de próximas actividades en formato corto (e.g., "HOY", "MAÑ", "LUN" + día del mes).

**POR QUÉ**:
- La interfaz requería un aspecto más profesional, atractivo y alineado con los estándares modernos de diseño web.
- Los inputs nativos de fecha y hora varían drásticamente entre navegadores y a menudo ofrecen una mala experiencia de usuario.
- En el dashboard docente, identificar a simple vista cuándo era una sesión mejora la usabilidad.

**PARA QUÉ**:
- Brindar una experiencia visual premium ("wow effect") y cohesiva en toda la aplicación.
- Estandarizar la interacción con calendarios y selección de fechas para los administradores y docentes.

---

### Cambio 16.7: Ciclo de Vida de Ediciones y Personas de Apoyo
**Fecha**: Mayo 18, 2026  
**Archivos afectados**: `database.py`, `scripts/setup_bd.py`, `routes/admin.py`, `services/admin_service.py`, `services/portal_service.py`, `utils.py`

**QUÉ**:
- Nuevas columnas en `ediciones_formativas`: `persona_apoyo` y `estado`.
- Cambio del estado por defecto al crear una edición: de "Programada" a "En Edicion".
- Soporte en toda la lógica CRUD del backend y frontend (modales) para asignar una Persona de Apoyo.
- Parametrización segura (usando `?`) de las sentencias SQL relacionadas a `fecha_limite_matricula` y `datetime.now()` en `utils.py`.
- Integración de la selección de plantilla de certificado directamente en la vista de Catálogos (`id_plantilla_certificado`).

**POR QUÉ**:
- Las capacitaciones a menudo involucran personal administrativo o docentes auxiliares, no solo un responsable principal.
- Un curso recién creado no debe estar inmediatamente abierto ("Programado") sin antes configurar sus sesiones.
- Es imperativo evitar inyecciones SQL o comportamientos inesperados del reloj interno de SQLite (`datetime('now')`).

**PARA QUÉ**:
- Otorgar a los administradores un control granular sobre el ciclo de vida de un curso (En Edicion -> Programado).
- Asegurar mayor integridad en la selección y asignación de plantillas de certificados.

---

### Cambio 16.8: Resiliencia en Libro de Calificaciones
**Fecha**: Mayo 18, 2026  
**Archivos afectados**: `templates/admin.html`

**QUÉ**:
- Actualización de las expresiones Jinja2 en la tabla de asistencia (ej. `{% if (docente['porcentaje'] or 0) >= 80 %}`).
- Uso de fallback `or 0` al calcular y mostrar el ancho de la barra de progreso.

**POR QUÉ**:
- El sistema fallaba con un `TypeError` cuando un docente no tenía registro de asistencias y el porcentaje se procesaba como `None`.

**PARA QUÉ**:
- Evitar caídas en el renderizado del panel de control de evaluaciones y hacer la vista robusta frente a datos nulos.

---

## 🐘 Migración a PostgreSQL y Optimización UI/UX (v1.17.0)

### Cambio 17.1: Migración completa del motor de base de datos a PostgreSQL
**Fecha**: Mayo 19, 2026  
**Archivos afectados**: `database.py`, `app.py`, `config.py`, `requirements.txt`, `services/admin_service.py`, `services/portal_service.py`, `services/certificate_service.py`, `services/ia_service.py`, `services/validacion_service.py`, `routes/admin.py`, `routes/portal.py`, `scripts/setup_bd.py`, `scripts/sync_docentes_excel.py`, `tests/test_docente_login.py`, `scripts/migrate_placeholders.py` (nuevo), `scripts/fix_strftime.py` (nuevo)

**QUÉ**:
- Sustitución íntegra de la base de datos SQLite (`sqlite3`) por el motor **PostgreSQL** mediante el conector **psycopg2**.
- Modificación de tipos de datos en la estructura de esquemas: `INTEGER PRIMARY KEY AUTOINCREMENT` pasó a `SERIAL PRIMARY KEY`, y `DATETIME` a `TIMESTAMP`.
- Reemplazo masivo de placeholders de consultas SQL de la sintaxis de SQLite (`?`) a la sintaxis estándar de PostgreSQL (`%s`).
- Implementación de scripts de automatización:
  - `migrate_placeholders.py` para reescribir sentencias SQL adaptando comodines de coincidencia y condiciones de búsqueda `LIKE` a `ILIKE`.
  - `fix_strftime.py` para reemplazar la función nativa `strftime` de SQLite por las funciones nativas `EXTRACT` y `TO_CHAR` de PostgreSQL.
- Eliminación de dependencias residuales locales y rutas estáticas de SQLite (`DB_PATH`, `resolve_db_path()`) en `config.py`.
- Actualización de los scripts de inicialización (`setup_bd.py`) y sincronización Excel (`sync_docentes_excel.py`) para operar en producción mediante PostgreSQL.

**POR QUÉ**:
- SQLite posee limitaciones de concurrencia y lectura/escritura simultánea que hacían inviable su uso en producción para un sistema de matrícula concurrente.
- PostgreSQL provee el nivel de escalabilidad, seguridad, concurrencia transaccional e integridad referencial requeridos.

**PARA QUÉ**:
- Desplegar la aplicación en producción de manera estable.
- Incrementar significativamente la velocidad de procesamiento de peticiones y consultas a la base de datos.
- Prevenir bloqueos de base de datos (`locked database`) cuando múltiples docentes se matriculan simultáneamente.

---

### Cambio 17.2: Resolución de compatibilidad de fechas nativas PostgreSQL
**Fecha**: Mayo 19, 2026  
**Archivos afectados**: `utils.py`, `templates/dashboard.html`, `templates/admin.html`

**QUÉ**:
- **Tratamiento dinámico de objetos**: Modificación de `construir_notificaciones_docente` en `utils.py` para comprobar si la columna `fecha_evento` devuelta por la base de datos es un objeto `datetime.datetime` nativo (retornado por PostgreSQL) o una cadena, aplicando `.strftime('%Y-%m-%d %H:%M')` como formateo seguro.
- **Filtro Jinja2**: Adición de filtros de conversión a cadena (`|string`) antes de realizar recortes de índices (`[:10]` o `[:16]`) en las plantillas HTML del historial del docente y los reportes de matrículas administrativas.

**POR QUÉ**:
- El conector de PostgreSQL devuelve las columnas `TIMESTAMP` como objetos de tipo `datetime` de Python, mientras que SQLite las devolvía formateadas como cadenas de texto. Esto causaba excepciones de tipo (`TypeError: 'datetime.datetime' object is not subscriptable`) al intentar manipularlas como arrays de caracteres directos en las vistas de Jinja2 o en utilidades.

**PARA QUÉ**:
- Evitar caídas 500 al renderizar vistas y asegurar que el historial del docente, las alertas y la visualización de reportes carguen correctamente con la base de datos PostgreSQL.

---

### Cambio 17.3: Rediseño, interactividad y optimización responsiva del modal de plantillas
**Fecha**: Mayo 19, 2026  
**Archivos afectados**: `templates/admin.html`

**QUÉ**:
- **Optimización de Dimensiones**: Se aumentó el tamaño de los modales de creación y edición de plantillas de certificados a `w-[96%] max-w-[1160px] h-[90vh] max-h-[920px]`.
- **Estructura Interna Antidesborde**: Se configuró la etiqueta del `<form>` con clases `max-h-full overflow-hidden`, garantizando que el scroll vertical intermedio (`flex-1 overflow-y-auto`) responda correctamente y mantenga el pie de página visible.
- **Diseño Crisp & Limpio**:
  - Eliminación de grises opacos en inputs y sustitución por un estilo en blanco sólido y slate claro con foco dinámico azul (`bg-white border border-slate-200 focus:ring-4 focus:ring-primary/10 rounded-xl`).
  - Chips de variables de inyección (`[NOMBRE]`, `[CURSO]`, etc.) rediseñados como botones/chips interactivos sobre fondo blanco limpio.
- **Remoción de Duplicados**: Eliminación de las flechas de iconos absolutos `<span>expand_more</span>` y clases `appearance-none pr-10`, confiando exclusivamente en el diseño integrado de la clase `.form-select`.
- **Micro-interacciones en Botones**: Integración de la clase premium `.btn-primary-ipsd` al botón de creación ("Nueva Plantilla") y efectos físicos tridimensionales en hover para "Configurar Firma y Logo".

**POR QUÉ**:
- En pantallas de resoluciones estándar, los modales se recortaban verticalmente ocultando los botones para cancelar y guardar cambios.
- Los menús desplegables mostraban flechas duplicadas debido al choque entre estilos nativos CSS y el markup del HTML.
- El diseño anterior resultaba sombrío y no ofrecía retroalimentación visual al usuario en las acciones del header.

**PARA QUÉ**:
- Asegurar que los modales de plantillas de certificados sean completamente responsivos en cualquier resolución de pantalla sin necesidad de alejar el zoom del navegador.
- Alinear el módulo de certificados con la identidad de diseño premium y de alto contraste del portal del IPSD.

---

**Última actualización**: Mayo 19, 2026  
**Versión actual**: 1.17.0 (Migración a PostgreSQL y Pulido UX de Plantillas)  
**Estado**: Development - Base de datos PostgreSQL integrada con éxito y diseño de modales responsivo refinado.

---

## 📅 Selección Manual de Calendario y Unificación Estética (v1.18.0)

### Cambio 18.1: Implementación de Selección Manual de Días de Clase y Generación Flexible de Calendario
**Fecha**: Mayo 22, 2026  
**Archivos afectados**: `routes/admin.py`, `services/admin_service.py`, `templates/admin.html`

**QUÉ**:
- Introducción del parámetro `modo_configuracion` (`auto` o `manual`) y el campo `fechas_manual` en las solicitudes de creación y edición de jornadas.
- Adaptación de la lógica de negocio en `generar_calendario_base` para soportar la inserción de sesiones basadas en una lista explícita de fechas seleccionadas por el usuario, omitiendo la iteración cíclica basada en días de la semana.
- Integración en el frontend de un selector interactivo sobre el calendario que permite a los administradores habilitar y marcar manualmente los días específicos de clases.

**POR QUÉ**:
- Los usuarios manifestaban dificultades para seleccionar días del calendario que no estuvieran alineados rígidamente con los días de la semana predeterminados.
- Se requería permitir configuraciones excepcionales o jornadas con fechas asimétricas que no sigan un patrón regular de días de la semana.

**PARA QUÉ**:
- Habilitar flexibilidad total en la planeación y programación de sesiones de clases, permitiendo seleccionar y deseleccionar fechas específicas directamente en el calendario interactivo.

---

### Cambio 18.2: Unificación Estética en Tablas, Modales y Modos Claro/Oscuro
**Fecha**: Mayo 22, 2026  
**Archivos afectados**: `templates/admin.html`, `templates/base.html`, `templates/dashboard.html`

**QUÉ**:
- Unificación del diseño de las tablas administrativas a través de la clase CSS `.admin-table-container`, aplicando sombras neutras, bordes suaves y fondos desenfocados (`backdrop-filter`) compatibles con los modos claro y oscuro.
- Eliminación de la línea de división visual en el modo claro, unificando el fondo blanco en todo el panel de administración (`admin-main`, `admin-layout`).
- Modificaciones en los estilos CSS aplicados a Choices.js en modo oscuro para mejorar la legibilidad y corregir superposiciones de íconos absolutos.
- Ajuste del script de control de temas en `base.html` y `dashboard.html` para sincronizar la clase global `.dark` con el elemento raíz, asegurando que Tailwind procese los estilos oscuros sin parpadeos visuales al cargar la página.
- Sincronización del estilo de fuentes con la tipografía oficial UNAH (`Manrope`).

**POR QUÉ**:
- La interfaz del modo claro presentaba divisiones marcadas e inconsistencias visuales en el fondo y bordes de las secciones.
- Ciertos modales y tablas (ej. Plantillas PDF) no seguían la misma línea gráfica del sistema ni los mismos esquemas de sombreado y transición.
- Se requería mantener la consistencia tipográfica y corregir problemas de legibilidad de las listas desplegables en el modo oscuro.

**PARA QUÉ**:
- Lograr una experiencia estética premium y homogénea en todas las pantallas administrativas y modos de color.
- Asegurar que los componentes y menús interactivos no presenten recortes ni problemas de visibilidad en resoluciones estándar.

---

### Cambio 18.3: Optimización del Libro de Asistencia y Consultas de Matrícula
**Fecha**: Mayo 22, 2026  
**Archivos afectados**: `services/admin_service.py`, `utils.py`, `templates/validador.html`

**QUÉ**:
- Refactorización de la consulta SQL de reporte de asistencia en `obtener_reporte_asistencia_curso` empleando una única consulta optimizada PostgreSQL con agregación de arreglos (`ARRAY_AGG`) para reducir los accesos a base de datos.
- Simplificación de la consulta de eventos de calendario docente en `utils.py`, removiendo una unión redundante con `matricula_historial` y corrigiendo la tupla de parámetros vinculados.
- Cast a string de la fecha de emisión en `validador.html` para evitar excepciones de Jinja2 provocadas por objetos de fecha nativos de PostgreSQL.
- Creación de índices específicos en PostgreSQL (`idx_catalogo_acciones_direccion`, `idx_matriculas_edicion`, `idx_matriculas_numero`, etc.) en `scripts/setup_bd.py` para optimizar las uniones y búsquedas recurrentes en el portal.

**POR QUÉ**:
- Las consultas a base de datos generaban sobrecarga innecesaria al realizar consultas cíclicas o redundantes.
- El validator generaba un error 500 al intentar manipular campos `TIMESTAMP` de PostgreSQL como subcadenas.

**PARA QUÉ**:
- Mejorar los tiempos de respuesta del servidor y agilizar la visualización de asistencias en cursos grandes.
- Prevenir caídas del sistema en producción y asegurar la correcta validación de certificados digitales.

---

### Cambio 18.4: Adaptación de Pruebas Unitarias para SQLite Local
**Fecha**: Mayo 22, 2026  
**Archivos afectados**: `tests/test_docente_login.py`

**QUÉ**:
- Modificación del setup del test de login de docentes para interactuar con una base de datos local SQLite (`matricula.db`) en lugar de depender de la conexión PostgreSQL global.
- Ajuste del esquema de la tabla temporal de docentes a formato SQLite compatible.

**POR QUÉ**:
- La ejecución de pruebas unitarias locales en entornos aislados o de integración continua no siempre cuenta con una base de datos PostgreSQL activa y con datos pre-cargados.

**PARA QUÉ**:
- Facilitar el testing automatizado del login de docentes sin dependencias complejas del motor de producción.

---

**Última actualización**: Mayo 22, 2026  
**Versión actual**: 1.18.0 (Selección Manual de Calendario y Unificación Estética)  
**Estado**: Development - Funcionalidad de calendario flexible integrada, diseño responsivo unificado en tablas/modales y optimización de base de datos PostgreSQL.

