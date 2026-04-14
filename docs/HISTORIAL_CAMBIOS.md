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

**Última actualización**: Abril 14, 2026  
**Versión actual**: 1.6 (Centro de Notificaciones para Docentes)  
**Estado**: Development - Sistema completo de notificaciones, modal feedback post-matricula
