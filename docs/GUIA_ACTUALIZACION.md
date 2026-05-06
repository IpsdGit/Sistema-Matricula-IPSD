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
- Simplemente al ejecutar `python app.py`, el sistema detectará si falta la nueva tabla `certificados_emitidos` y la creará automáticamente.
- **Importante**: Si vienes de una versión muy antigua, asegúrate de que no haya errores en la consola al iniciar.

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

## 6. Scripts Especiales (Si aplica)
Si necesitas sincronizar datos de docentes desde un Excel o aplicar parches manuales:
- **Sincronizar Docentes**: `python scripts/sync_docentes_excel.py`
- **Reparar Claves Foráneas**: `python scripts/migrate_db_fks.py`

---

## 🏁 Checklist de Verificación
Para confirmar que todo está bien en la nueva PC:
1. [ ] El servidor inicia sin errores de "ModuleNotFoundError".
2. [ ] Puedes entrar al Dashboard y ver el nuevo diseño de "Bento Grid".
3. [ ] Al generar un certificado, el código QR es visible en el PDF.
4. [ ] Al escanear el QR, la URL redirige correctamente (verificar configuración de Ngrok si es prueba local).

---
**Última revisión**: Mayo 6, 2026  
**Cambios clave incluidos**: Tabla `certificados_emitidos`, librería `qrcode`, nombres de archivo dinámicos.
