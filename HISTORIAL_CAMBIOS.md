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

## 🎯 Próximas Mejoras Previstas

- [ ] Exportación de reportes (CSV/PDF)
- [ ] Integración con directorio LDAP institucional
- [ ] Notificaciones por email
- [ ] Dashboard de participación por trimestre
- [ ] Asignación de aulas y recursos
- [ ] API REST para integración con otros sistemas
- [ ] Autenticación de dos factores (2FA) para admin
- [ ] Sistema de rechazos y aprobaciones de matrículas

---

**Última actualización**: Abril 9, 2026  
**Versión actual**: 1.0  
**Estado**: En producción en PythonAnywhere
