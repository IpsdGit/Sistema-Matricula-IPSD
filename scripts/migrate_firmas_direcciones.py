import argparse
import os
import shutil
import sqlite3
import sys

project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from config import DB_PATH, UPLOAD_FOLDER  # noqa: E402


def _tabla_tiene_columna(conn, tabla, columna):
    try:
        columnas = conn.execute(f"PRAGMA table_info({tabla})").fetchall()
        return any(col[1] == columna for col in columnas)
    except sqlite3.Error:
        return False


def migrar_firmas(force=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if not _tabla_tiene_columna(conn, "direcciones", "ruta_firma_img"):
        cursor.execute(
            "ALTER TABLE direcciones ADD COLUMN ruta_firma_img TEXT NOT NULL DEFAULT ''"
        )

    if not _tabla_tiene_columna(conn, "plantillas_certificados", "ruta_firma_img"):
        print("La tabla plantillas_certificados no tiene ruta_firma_img. Nada que migrar.")
        conn.close()
        return

    dest_dir = os.path.join(UPLOAD_FOLDER, "direcciones")
    os.makedirs(dest_dir, exist_ok=True)

    origen_dir = os.path.join(project_root, "static", "certificados", "firmas")

    direcciones = cursor.execute(
        "SELECT codigo, ruta_firma_img FROM direcciones ORDER BY codigo"
    ).fetchall()

    if not direcciones:
        print("No hay direcciones registradas para migrar.")
        conn.close()
        return

    for row in direcciones:
        codigo = (row["codigo"] or "").strip().upper()
        if not codigo:
            continue

        ruta_actual = (row["ruta_firma_img"] or "").strip()

        plantilla = cursor.execute(
            """
            SELECT ruta_firma_img
            FROM plantillas_certificados
            WHERE direccion_codigo = ?
              AND activo = 1
              AND TRIM(COALESCE(ruta_firma_img, '')) <> ''
            ORDER BY id DESC
            LIMIT 1
            """,
            (codigo,),
        ).fetchone()

        if not plantilla:
            print(f"[WARN] {codigo}: sin firma en plantillas activas.")
            continue

        ruta_web = (plantilla["ruta_firma_img"] or "").strip()
        ruta_src = ''

        if ruta_web:
            ruta_rel = ruta_web.lstrip("/").replace("/", os.sep)
            ruta_src = os.path.normpath(os.path.join(project_root, ruta_rel))
            if not os.path.exists(ruta_src):
                ruta_src = ''

        if not ruta_src and os.path.isdir(origen_dir):
            candidatos = [
                f for f in os.listdir(origen_dir)
                if f.upper().startswith(f"{codigo}_FIRMA_") and f.lower().endswith(".png")
            ]
            if candidatos:
                candidatos.sort(
                    key=lambda f: os.path.getmtime(os.path.join(origen_dir, f)),
                    reverse=True,
                )
                ruta_src = os.path.join(origen_dir, candidatos[0])

        if not ruta_src or not os.path.exists(ruta_src):
            print(f"[WARN] {codigo}: firma no encontrada para migrar.")
            continue

        nombre_archivo = f"{codigo}_firma.png"
        ruta_destino = os.path.join(dest_dir, nombre_archivo)
        if os.path.exists(ruta_destino):
            if os.path.normpath(ruta_src) != os.path.normpath(ruta_destino):
                try:
                    os.remove(ruta_src)
                except OSError:
                    print(f"[WARN] {codigo}: no se pudo eliminar {ruta_src}.")
        else:
            shutil.move(ruta_src, ruta_destino)

        ruta_dest_web = f"/uploads/direcciones/{nombre_archivo}"
        if force or not ruta_actual or ruta_actual != ruta_dest_web:
            cursor.execute(
                "UPDATE direcciones SET ruta_firma_img = ? WHERE codigo = ?",
                (ruta_dest_web, codigo),
            )
            print(f"[OK] {codigo}: {ruta_dest_web}")
        else:
            print(f"[OK] {codigo}: firma ya configurada ({ruta_actual}).")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migra firmas desde plantillas_certificados a direcciones y copia archivos a uploads/direcciones."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sobrescribe firmas existentes en direcciones.",
    )
    args = parser.parse_args()
    migrar_firmas(force=args.force)
