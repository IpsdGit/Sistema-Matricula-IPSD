# 🔄 Guía de Actualización y Sincronización

Esta guía detalla los pasos necesarios para actualizar el código y la base de datos en una nueva computadora o entorno de desarrollo, asegurando que todas las nuevas funcionalidades (como el sistema QR) funcionen correctamente.

---

## 1. Actualización del Código
Si estás usando Git, el primer paso es obtener los últimos cambios:
```powershell
git pull origin main
```

## 2. Actualización de Dependencias
Hemos agregado nuevas librerías (como `qrcode` para los certificados). Es vital actualizar el entorno virtual:
```powershell
# Activa tu entorno virtual primero
.\.venv\Scripts\activate

# Instala las nuevas dependencias
pip install -r requirements.txt
```

## 3. Migración de la Base de Datos
El sistema cuenta con una función de **auto-migración** en `app.py`. 
- Al iniciar la aplicación (`python app.py`), el sistema detectará y creará automáticamente las nuevas tablas del núcleo: `catalogo_acciones`, `ediciones_formativas` y `sesiones_curso`.
- **Importante**: Si estás migrando una base de datos existente desde la versión 1.13 o anterior, es **obligatorio** ejecutar el script de reparación de llaves foráneas (ver sección 6).

## 4. Dependencias del Sistema (PDF)
Para que la generación de PDFs y códigos QR funcione, la nueva computadora **debe tener instalado wkhtmltopdf**:
1. Descargar desde: [wkhtmltopdf.org/downloads.html](https://wkhtmltopdf.org/downloads.html)
2. Durante la instalación, anotar la ruta (usualmente `C:\Program Files\wkhtmltopdf`).
3. El sistema buscará automáticamente en esa ruta, pero si la instalación es diferente, deberás configurar la variable de entorno `WKHTMLTOPDF_PATH`.

## 5. Variables de Entorno
Asegúrate de tener el archivo `.env` en la raíz del proyecto con las claves necesarias:
```env
GOOGLE_GEMINI_API_KEY=tu_clave_aqui
```

## 6. Scripts de Mantenimiento y Migración
Si estás configurando el proyecto con datos existentes o necesitas aplicar parches:
- **Sincronizar Docentes**: `python scripts/sync_docentes_excel.py` (Carga masiva desde archivo Excel).
- **Reparar Estructura y FKs**: `python scripts/migrate_db_fks.py`
  - *Uso*: `python scripts/migrate_db_fks.py --backup`
  - *Propósito*: Reestructura las tablas de matrículas y asistencias para que apunten correctamente a las nuevas **Ediciones** y **Sesiones**.

---

## 🏁 Checklist de Verificación
Para confirmar que todo está bien en la nueva PC:
1. [ ] El servidor inicia sin errores de "ModuleNotFoundError".
2. [ ] El Panel Admin muestra las nuevas pestañas de **Catálogos** y **Ediciones**.
3. [ ] Puedes crear un Catálogo y programar una Edición con al menos una sesión.
4. [ ] Al generar un certificado, los metadatos de horas y fechas se calculan automáticamente.
5. [ ] Al escanear el QR, la URL redirige correctamente al validador.

---
**Última revisión**: Mayo 12, 2026  
**Versión actual**: 1.14.0 (Arquitectura Catálogos/Ediciones y Sesiones)  
**Estado**: Production Ready - Núcleo de datos refactorizado.
