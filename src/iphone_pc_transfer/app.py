import os
import csv
import json
import time
import socket
import shutil
import zipfile
import random
import locale
import threading
import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk
import qrcode
from PIL import Image

# Optional Windows notification integration
TOAST_ACTIVO = False
try:
    from win10toast import ToastNotifier
    TOAST_ACTIVO = True
except Exception:
    TOAST_ACTIVO = False


from flask import (
    Flask, request, send_from_directory, render_template_string,
    redirect, url_for, session
)
from werkzeug.utils import secure_filename
from werkzeug.serving import make_server

# Optional drag and drop integration
DND_ACTIVO = False
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_ACTIVO = True
except Exception:
    DND_ACTIVO = False


# ============================================================
# GENERAL CONFIGURATION
# ============================================================

try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()

CARPETA_BASE = os.path.join(BASE_DIR, "TRANSFERENCIA_IPHONE_PC")
CARPETA_PC_A_IPHONE = os.path.join(CARPETA_BASE, "PC_A_IPHONE")
CARPETA_IPHONE_A_PC = os.path.join(CARPETA_BASE, "IPHONE_A_PC")
CARPETA_HISTORIAL = os.path.join(CARPETA_BASE, "HISTORIAL")
CARPETA_CONFIG = os.path.join(CARPETA_BASE, "CONFIG")

for carpeta in [CARPETA_BASE, CARPETA_PC_A_IPHONE, CARPETA_IPHONE_A_PC, CARPETA_HISTORIAL, CARPETA_CONFIG]:
    os.makedirs(carpeta, exist_ok=True)

HISTORIAL_CSV = os.path.join(CARPETA_HISTORIAL, "historial_transferencias.csv")
CONFIG_JSON = os.path.join(CARPETA_CONFIG, "configuracion.json")
SESION_JSON = os.path.join(CARPETA_CONFIG, "sesion_anterior.json")

PUERTO = 5000

CONFIG_DEFAULT = {
    "nombre_servidor": "PC de Usuario",
    "usar_password": False,
    "password": "",
    "usar_codigo_temporal": False,
    "codigo_temporal": "",
    "modo_permisos": "Ambos",
    "permitir_eliminar_desde_iphone": False,
    "abrir_carpeta_al_recibir": False,
    "limite_mb": 0,
    "modo_privado": False,
    "apariencia": "dark",
    "texto_compartido_pc": "",
    "borrar_enviados_horas": 0,
    "borrar_recibidos_horas": 0,
    "idioma": "auto"
}

CONFIG = CONFIG_DEFAULT.copy()

DISPOSITIVOS_CONECTADOS = {}
EVENTOS = []
EVENTOS_LOG = []
EVENTOS_LOCK = threading.Lock()

# ============================================================
# LANGUAGES
# ============================================================

IDIOMAS = {
    "es": "Español",
    "en": "English",
    "zh": "中文",
    "hi": "हिन्दी",
    "ar": "العربية",
    "fr": "Français",
}

TRADUCCIONES = {
    "es": {"language": "Idioma", "restart": "Idioma actualizado. Reinicia el programa para aplicar todos los textos."},
    "en": {"language": "Language", "restart": "Language updated. Restart the program to apply all texts."},
    "zh": {"language": "语言", "restart": "语言已更新。请重启程序以应用所有文本。"},
    "hi": {"language": "भाषा", "restart": "भाषा अपडेट हो गई। सभी पाठ लागू करने के लिए प्रोग्राम पुनः शुरू करें।"},
    "ar": {"language": "اللغة", "restart": "تم تحديث اللغة. أعد تشغيل البرنامج لتطبيق كل النصوص."},
    "fr": {"language": "Langue", "restart": "Langue mise à jour. Redémarrez le programme pour appliquer tous les textes."},
}

def detectar_idioma_sistema():
    try:
        lang = locale.getdefaultlocale()[0] or ""
        lang = lang.lower()

        if lang.startswith("es"):
            return "es"
        if lang.startswith("en"):
            return "en"
        if lang.startswith("zh"):
            return "zh"
        if lang.startswith("hi"):
            return "hi"
        if lang.startswith("ar"):
            return "ar"
        if lang.startswith("fr"):
            return "fr"

    except Exception:
        pass

    return "en"

def idioma_actual():
    idioma = CONFIG.get("idioma", "auto")
    if idioma == "auto":
        idioma = detectar_idioma_sistema()

    if idioma not in IDIOMAS:
        idioma = "en"

    return idioma

def t(clave):
    idioma = idioma_actual()
    return TRADUCCIONES.get(idioma, TRADUCCIONES["en"]).get(
        clave,
        TRADUCCIONES["es"].get(clave, clave)
    )




# ============================================================
# WEB INTERFACE LANGUAGES
# ============================================================

WEB_TRANSLATIONS = {
    "es": {
        "access_protected": "Acceso protegido", "enter_password": "Ingresa la contraseña o código temporal para continuar",
        "password_placeholder": "Contraseña o código temporal", "enter": "Entrar", "incorrect_key": "Clave incorrecta.",
        "logout": "Cerrar acceso", "main_title": "Transferencia inalámbrica iPhone ↔ PC",
        "upload_files_title": "Enviar archivos del iPhone a la PC", "send_files": "Enviar archivos a la PC",
        "upload_disabled": "La PC tiene desactivada la recepción de archivos.", "camera_title": "Cámara directa del iPhone",
        "take_photo": "Tomar foto y enviar", "record_video": "Grabar video y enviar",
        "camera_hint": "Si la cámara no se abre, actualiza esta página en Safari y vuelve a tocar el botón.",
        "shared_text": "Texto compartido", "text_from_pc": "Texto enviado desde la PC",
        "write_text": "Escribe un texto para enviar a la PC", "send_text": "Enviar texto a la PC",
        "gallery": "Galería de imágenes disponibles", "no_images": "No hay imágenes para mostrar.",
        "download_title": "Descargar archivos enviados desde la PC", "preview_pdf": "Ver PDF sin descargar",
        "download": "Descargar en iPhone", "delete_from_iphone": "Eliminar desde iPhone",
        "delete_confirm": "¿Eliminar este archivo de la PC?", "no_files": "Todavía no hay archivos enviados desde la PC.",
        "download_disabled": "La PC tiene desactivada la descarga de archivos.", "refresh": "Actualizar lista",
        "current_mode": "Modo actual", "usage_hint": "Puedes enviar archivos, descargar archivos y compartir texto rápido.",
        "language": "Idioma"
    },
    "en": {
        "access_protected": "Protected access", "enter_password": "Enter the password or temporary code to continue",
        "password_placeholder": "Password or temporary code", "enter": "Enter", "incorrect_key": "Incorrect key.",
        "logout": "Log out", "main_title": "Wireless iPhone ↔ PC Transfer",
        "upload_files_title": "Send files from iPhone to PC", "send_files": "Send files to PC",
        "upload_disabled": "File reception is disabled on the PC.", "camera_title": "Direct iPhone camera",
        "take_photo": "Take photo and send", "record_video": "Record video and send",
        "camera_hint": "If the camera does not open, refresh this page in Safari and tap the button again.",
        "shared_text": "Shared text", "text_from_pc": "Text sent from the PC",
        "write_text": "Write text to send to the PC", "send_text": "Send text to PC",
        "gallery": "Available image gallery", "no_images": "No images to display.",
        "download_title": "Download files sent from the PC", "preview_pdf": "Preview PDF without downloading",
        "download": "Download on iPhone", "delete_from_iphone": "Delete from iPhone",
        "delete_confirm": "Delete this file from the PC?", "no_files": "There are no files sent from the PC yet.",
        "download_disabled": "File download is disabled on the PC.", "refresh": "Refresh list",
        "current_mode": "Current mode", "usage_hint": "You can send files, download files and share quick text.",
        "language": "Language"
    },
    "zh": {
        "access_protected": "受保护访问", "enter_password": "请输入密码或临时代码继续",
        "password_placeholder": "密码或临时代码", "enter": "进入", "incorrect_key": "密钥错误。",
        "logout": "退出", "main_title": "iPhone ↔ PC 无线传输",
        "upload_files_title": "从 iPhone 发送文件到 PC", "send_files": "发送文件到 PC",
        "upload_disabled": "PC 已禁用文件接收。", "camera_title": "iPhone 直接相机",
        "take_photo": "拍照并发送", "record_video": "录制视频并发送",
        "camera_hint": "如果相机没有打开，请在 Safari 中刷新页面，然后再次点击按钮。",
        "shared_text": "共享文本", "text_from_pc": "来自 PC 的文本",
        "write_text": "输入要发送到 PC 的文本", "send_text": "发送文本到 PC",
        "gallery": "可用图片图库", "no_images": "没有可显示的图片。",
        "download_title": "下载 PC 发送的文件", "preview_pdf": "不下载预览 PDF",
        "download": "在 iPhone 下载", "delete_from_iphone": "从 iPhone 删除",
        "delete_confirm": "从 PC 删除此文件？", "no_files": "还没有从 PC 发送的文件。",
        "download_disabled": "PC 已禁用文件下载。", "refresh": "刷新列表",
        "current_mode": "当前模式", "usage_hint": "可以发送文件、下载文件并共享快速文本。",
        "language": "语言"
    },
    "hi": {
        "access_protected": "सुरक्षित प्रवेश", "enter_password": "जारी रखने के लिए पासवर्ड या अस्थायी कोड दर्ज करें",
        "password_placeholder": "पासवर्ड या अस्थायी कोड", "enter": "प्रवेश करें", "incorrect_key": "गलत कुंजी।",
        "logout": "लॉग आउट", "main_title": "iPhone ↔ PC वायरलेस ट्रांसफर",
        "upload_files_title": "iPhone से PC में फाइलें भेजें", "send_files": "PC में फाइलें भेजें",
        "upload_disabled": "PC पर फाइल प्राप्त करना बंद है।", "camera_title": "iPhone कैमरा",
        "take_photo": "फोटो लें और भेजें", "record_video": "वीडियो रिकॉर्ड करें और भेजें",
        "camera_hint": "यदि कैमरा नहीं खुलता, Safari में पेज रीफ्रेश करें और फिर बटन दबाएँ।",
        "shared_text": "साझा टेक्स्ट", "text_from_pc": "PC से भेजा गया टेक्स्ट",
        "write_text": "PC को भेजने के लिए टेक्स्ट लिखें", "send_text": "PC को टेक्स्ट भेजें",
        "gallery": "उपलब्ध छवि गैलरी", "no_images": "दिखाने के लिए कोई छवि नहीं।",
        "download_title": "PC से भेजी गई फाइलें डाउनलोड करें", "preview_pdf": "डाउनलोड किए बिना PDF देखें",
        "download": "iPhone पर डाउनलोड करें", "delete_from_iphone": "iPhone से हटाएँ",
        "delete_confirm": "क्या इस फाइल को PC से हटाना है?", "no_files": "PC से भेजी गई कोई फाइल अभी नहीं है।",
        "download_disabled": "PC पर फाइल डाउनलोड बंद है।", "refresh": "सूची रीफ्रेश करें",
        "current_mode": "वर्तमान मोड", "usage_hint": "आप फाइलें भेज सकते हैं, डाउनलोड कर सकते हैं और त्वरित टेक्स्ट साझा कर सकते हैं।",
        "language": "भाषा"
    },
    "ar": {
        "access_protected": "وصول محمي", "enter_password": "أدخل كلمة المرور أو الرمز المؤقت للمتابعة",
        "password_placeholder": "كلمة المرور أو الرمز المؤقت", "enter": "دخول", "incorrect_key": "المفتاح غير صحيح.",
        "logout": "تسجيل الخروج", "main_title": "نقل لاسلكي iPhone ↔ PC",
        "upload_files_title": "إرسال ملفات من iPhone إلى PC", "send_files": "إرسال الملفات إلى PC",
        "upload_disabled": "استقبال الملفات معطل على PC.", "camera_title": "كاميرا iPhone مباشرة",
        "take_photo": "التقاط صورة وإرسالها", "record_video": "تسجيل فيديو وإرساله",
        "camera_hint": "إذا لم تفتح الكاميرا، حدّث الصفحة في Safari ثم اضغط الزر مرة أخرى.",
        "shared_text": "نص مشترك", "text_from_pc": "نص مرسل من PC",
        "write_text": "اكتب نصًا لإرساله إلى PC", "send_text": "إرسال النص إلى PC",
        "gallery": "معرض الصور المتاحة", "no_images": "لا توجد صور للعرض.",
        "download_title": "تنزيل الملفات المرسلة من PC", "preview_pdf": "عرض PDF دون تنزيل",
        "download": "تنزيل على iPhone", "delete_from_iphone": "حذف من iPhone",
        "delete_confirm": "هل تريد حذف هذا الملف من PC؟", "no_files": "لا توجد ملفات مرسلة من PC بعد.",
        "download_disabled": "تنزيل الملفات معطل على PC.", "refresh": "تحديث القائمة",
        "current_mode": "الوضع الحالي", "usage_hint": "يمكنك إرسال الملفات وتنزيلها ومشاركة نص سريع.",
        "language": "اللغة"
    },
    "fr": {
        "access_protected": "Accès protégé", "enter_password": "Saisissez le mot de passe ou le code temporaire pour continuer",
        "password_placeholder": "Mot de passe ou code temporaire", "enter": "Entrer", "incorrect_key": "Clé incorrecte.",
        "logout": "Se déconnecter", "main_title": "Transfert sans fil iPhone ↔ PC",
        "upload_files_title": "Envoyer des fichiers de l’iPhone vers le PC", "send_files": "Envoyer les fichiers au PC",
        "upload_disabled": "La réception des fichiers est désactivée sur le PC.", "camera_title": "Caméra directe de l’iPhone",
        "take_photo": "Prendre une photo et envoyer", "record_video": "Enregistrer une vidéo et envoyer",
        "camera_hint": "Si la caméra ne s’ouvre pas, actualisez cette page dans Safari puis touchez à nouveau le bouton.",
        "shared_text": "Texte partagé", "text_from_pc": "Texte envoyé depuis le PC",
        "write_text": "Écrivez un texte à envoyer au PC", "send_text": "Envoyer le texte au PC",
        "gallery": "Galerie d’images disponibles", "no_images": "Aucune image à afficher.",
        "download_title": "Télécharger les fichiers envoyés depuis le PC", "preview_pdf": "Voir le PDF sans téléchargement",
        "download": "Télécharger sur iPhone", "delete_from_iphone": "Supprimer depuis iPhone",
        "delete_confirm": "Supprimer ce fichier du PC ?", "no_files": "Aucun fichier envoyé depuis le PC pour le moment.",
        "download_disabled": "Le téléchargement de fichiers est désactivé sur le PC.", "refresh": "Actualiser la liste",
        "current_mode": "Mode actuel", "usage_hint": "Vous pouvez envoyer des fichiers, télécharger des fichiers et partager du texte rapide.",
        "language": "Langue"
    }
}

def detectar_idioma_navegador():
    """Detect the preferred language from the browser Accept-Language header."""
    try:
        header = request.headers.get("Accept-Language", "").lower()

        if header.startswith("es") or ",es" in header:
            return "es"
        if header.startswith("en") or ",en" in header:
            return "en"
        if header.startswith("zh") or ",zh" in header:
            return "zh"
        if header.startswith("hi") or ",hi" in header:
            return "hi"
        if header.startswith("ar") or ",ar" in header:
            return "ar"
        if header.startswith("fr") or ",fr" in header:
            return "fr"

    except Exception:
        pass

    return idioma_actual()

def idioma_web_actual():
    """Return the language selected in the browser session or detect it from the browser."""
    idioma = session.get("web_lang")

    if not idioma:
        idioma = detectar_idioma_navegador()
        session["web_lang"] = idioma

    if idioma not in WEB_TRANSLATIONS:
        idioma = "en"

    return idioma

def wt(clave):
    idioma = idioma_web_actual()
    return WEB_TRANSLATIONS.get(idioma, WEB_TRANSLATIONS["en"]).get(
        clave,
        WEB_TRANSLATIONS["en"].get(clave, clave)
    )

def web_contexto_idioma():
    idioma = idioma_web_actual()
    return {
        "wt": wt,
        "web_lang": idioma,
        "web_languages": IDIOMAS
    }


# ============================================================
# UTILIDADES
# ============================================================

def cargar_configuracion():
    global CONFIG
    try:
        if os.path.exists(CONFIG_JSON):
            with open(CONFIG_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            CONFIG.update(data)
    except Exception as e:
        print("No se pudo cargar configuración:", e)


def guardar_configuracion():
    try:
        data = CONFIG.copy()
        data["codigo_temporal"] = ""
        with open(CONFIG_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("No se pudo guardar configuración:", e)


def guardar_estado_sesion():
    """
    Store a summary of the last session to restore context when the application is opened again.
    """
    try:
        estado = {
            "fecha_cierre": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "nombre_servidor": CONFIG.get("nombre_servidor", "PC Local"),
            "modo_permisos": CONFIG.get("modo_permisos", "Ambos"),
            "texto_compartido_pc": CONFIG.get("texto_compartido_pc", ""),
            "archivos_enviados_pendientes": len(listar_archivos(CARPETA_PC_A_IPHONE)),
            "archivos_recibidos": len(listar_archivos(CARPETA_IPHONE_A_PC)),
            "dispositivos_conectados": len(DISPOSITIVOS_CONECTADOS)
        }
        with open(SESION_JSON, "w", encoding="utf-8") as f:
            json.dump(estado, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("No se pudo guardar estado de sesión:", e)


def cargar_estado_sesion():
    try:
        if os.path.exists(SESION_JSON):
            with open(SESION_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print("No se pudo cargar estado de sesión:", e)
    return None


def obtener_ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def formatear_tamano(bytes_size):
    try:
        bytes_size = float(bytes_size)
        for unidad in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_size < 1024:
                return f"{bytes_size:.2f} {unidad}"
            bytes_size /= 1024
        return f"{bytes_size:.2f} PB"
    except Exception:
        return "0 B"


def listar_archivos(carpeta):
    """
    List files recursively.
    This allows received files to be organized by date without disappearing from the interface.
    """
    archivos = []
    try:
        for raiz, _, nombres in os.walk(carpeta):
            for nombre in nombres:
                ruta = os.path.join(raiz, nombre)
                if os.path.isfile(ruta):
                    relativo = os.path.relpath(ruta, carpeta)
                    archivos.append({
                        "nombre": nombre,
                        "relativo": relativo,
                        "ruta": ruta,
                        "tamano": os.path.getsize(ruta),
                        "fecha": datetime.fromtimestamp(os.path.getmtime(ruta)).strftime("%d/%m/%Y %H:%M"),
                        "mtime": os.path.getmtime(ruta),
                        "tipo": obtener_tipo_archivo(nombre)
                    })
        archivos.sort(key=lambda x: x["mtime"], reverse=True)
    except Exception as error:
        print("Error al listar archivos:", error)
    return archivos


def crear_nombre_unico(carpeta, nombre_archivo):
    nombre_archivo = secure_filename(nombre_archivo)
    if not nombre_archivo:
        nombre_archivo = f"archivo_{int(time.time())}"
    nombre_base, extension = os.path.splitext(nombre_archivo)
    destino = os.path.join(carpeta, nombre_archivo)
    contador = 1
    while os.path.exists(destino):
        nuevo_nombre = f"{nombre_base}_{contador}{extension}"
        destino = os.path.join(carpeta, nuevo_nombre)
        contador += 1
    return destino


def abrir_ruta(ruta):
    try:
        os.startfile(ruta)
    except Exception:
        try:
            webbrowser.open(ruta)
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo abrir:\n{error}")


def obtener_tipo_archivo(nombre):
    ext = os.path.splitext(nombre.lower())[1]
    if ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic"]:
        return "Imagen"
    if ext in [".mp4", ".mov", ".avi", ".mkv", ".wmv"]:
        return "Video"
    if ext in [".mp3", ".wav", ".aac", ".m4a", ".flac"]:
        return "Audio"
    if ext == ".pdf":
        return "PDF"
    if ext in [".doc", ".docx"]:
        return "Word"
    if ext in [".xls", ".xlsx", ".csv"]:
        return "Excel"
    if ext in [".ppt", ".pptx"]:
        return "PowerPoint"
    if ext in [".zip", ".rar", ".7z"]:
        return "Comprimido"
    if ext in [".txt", ".md"]:
        return "Texto"
    if ext in [".py", ".js", ".html", ".css", ".json", ".xml"]:
        return "Código"
    return "Otro"


def obtener_icono_archivo(nombre):
    tipo = obtener_tipo_archivo(nombre)
    return {
        "Imagen": "📷",
        "Video": "🎥",
        "Audio": "🎵",
        "PDF": "📄",
        "Word": "📝",
        "Excel": "📊",
        "PowerPoint": "📑",
        "Comprimido": "📦",
        "Texto": "📋",
        "Código": "💻",
        "Otro": "📁"
    }.get(tipo, "📁")


def agregar_historial(archivo, origen, destino, tamano, estado):
    existe = os.path.exists(HISTORIAL_CSV)
    try:
        with open(HISTORIAL_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not existe:
                writer.writerow(["fecha", "archivo", "origen", "destino", "tamano", "bytes", "estado"])
            writer.writerow([
                datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                archivo,
                origen,
                destino,
                formatear_tamano(tamano),
                tamano,
                estado
            ])
    except Exception as error:
        print("Error historial:", error)


def leer_historial():
    registros = []
    if not os.path.exists(HISTORIAL_CSV):
        return registros
    try:
        with open(HISTORIAL_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            registros = list(reader)
        registros.reverse()
    except Exception as error:
        print("Error leyendo historial:", error)
    return registros


def agregar_evento(tipo, mensaje, ruta=None):
    evento = {
        "tipo": tipo,
        "mensaje": mensaje,
        "ruta": ruta,
        "fecha": datetime.now().strftime("%H:%M:%S"),
        "fecha_completa": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }
    with EVENTOS_LOCK:
        EVENTOS.append(evento)
        EVENTOS_LOG.insert(0, evento)
        del EVENTOS_LOG[200:]


def registrar_dispositivo():
    ip = request.remote_addr or "desconocido"
    user_agent = request.headers.get("User-Agent", "desconocido")
    DISPOSITIVOS_CONECTADOS[ip] = {
        "ip": ip,
        "user_agent": user_agent[:120],
        "ultimo_acceso": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }


def generar_codigo_temporal():
    return str(random.randint(100000, 999999))


def puede_subir():
    return CONFIG["modo_permisos"] in ["Ambos", "Solo recibir desde iPhone"]


def puede_descargar():
    return CONFIG["modo_permisos"] in ["Ambos", "Solo enviar al iPhone"]


def limpiar_por_expiracion():
    ahora = time.time()
    reglas = [
        (CARPETA_PC_A_IPHONE, int(CONFIG.get("borrar_enviados_horas", 0) or 0)),
        (CARPETA_IPHONE_A_PC, int(CONFIG.get("borrar_recibidos_horas", 0) or 0))
    ]
    for carpeta, horas in reglas:
        if horas <= 0:
            continue
        limite = horas * 3600
        try:
            for nombre in os.listdir(carpeta):
                ruta = os.path.join(carpeta, nombre)
                if os.path.isfile(ruta) and ahora - os.path.getmtime(ruta) > limite:
                    os.remove(ruta)
        except Exception as e:
            print("Error limpiando por expiración:", e)


cargar_configuracion()
ctk.set_appearance_mode(CONFIG.get("apariencia", "dark"))
ctk.set_default_color_theme("blue")


# ============================================================
# HTML WEB IPHONE
# ============================================================

HTML_LOGIN = """
<!DOCTYPE html>
<html lang="{{ web_lang }}">
<head>
    <meta charset="UTF-8">
    <title>{{ wt("access_protected") }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate, max-age=0">
    <meta http-equiv="Pragma" content="no-cache">
    <script>
        function prepararCamara(idInput) {
            const input = document.getElementById(idInput);
            if (input) {
                input.value = "";
            }
        }

        function enviarCamara(formId, inputId) {
            const input = document.getElementById(inputId);
            const form = document.getElementById(formId);

            if (input && form && input.files && input.files.length > 0) {
                form.submit();

                setTimeout(function() {
                    input.value = "";
                }, 500);
            }
        }

        window.addEventListener("pageshow", function() {
            const foto = document.getElementById("camera_photo_input");
            const video = document.getElementById("camera_video_input");

            if (foto) foto.value = "";
            if (video) video.value = "";
        });
    </script>
    <style>
        * { box-sizing: border-box; }
        body {
            margin:0; font-family:-apple-system,BlinkMacSystemFont,Arial,sans-serif;
            background:radial-gradient(circle at top,#2563eb,#020617 70%);
            color:white; min-height:100vh; display:flex; align-items:center; justify-content:center; padding:18px;
        }
        .card { width:100%; max-width:430px; background:rgba(15,23,42,.94); border:1px solid rgba(148,163,184,.28); border-radius:24px; padding:24px; box-shadow:0 14px 35px rgba(0,0,0,.4);}
        h1{text-align:center;font-size:26px;margin-bottom:8px;} p{text-align:center;color:#cbd5e1;font-size:15px;margin-bottom:22px;}
        input{width:100%;padding:15px;border-radius:15px;background:#020617;color:white;border:1px solid #334155;margin-bottom:14px;font-size:16px;}
        button{width:100%;padding:15px;border:none;border-radius:15px;background:linear-gradient(135deg,#2563eb,#06b6d4);color:white;font-size:16px;font-weight:bold;}
        .error{color:#fecaca;background:rgba(220,38,38,.18);border:1px solid rgba(248,113,113,.35);padding:12px;border-radius:14px;text-align:center;margin-bottom:14px;font-size:14px;}
        .hint{color:#94a3b8;font-size:13px;text-align:center;margin-top:12px;}
        .language-select-login{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:12px}
        .language-select-login a{color:#bfdbfe;text-decoration:none;background:rgba(37,99,235,.22);border:1px solid rgba(147,197,253,.25);padding:7px 10px;border-radius:999px;font-size:13px;font-weight:600}
        .language-select-login a.active{background:#2563eb;color:white}
    </style>
</head>
<body>
    <div class="card">
        <h1>{{ wt("access_protected") }}</h1>
        <p>{{ wt("enter_password") }}<br>{{ nombre_servidor }}</p>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST" action="/login">
            <input type="password" name="clave" placeholder="{{ wt('password_placeholder') }}" required>
            <button type="submit">{{ wt("enter") }}</button>
        </form>
        <div class="hint">{{ wt("language") }}</div>
        <div class="language-select-login">
            {% for code, name in web_languages.items() %}
                <a href="/set_language/{{ code }}?next={{ request.path }}" class="{% if code == web_lang %}active{% endif %}">{{ name }}</a>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

HTML_IPHONE = """
<!DOCTYPE html>
<html lang="{{ web_lang }}">
<head>
    <meta charset="UTF-8">
    <title>{{ nombre_servidor }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-store, no-cache, must-revalidate, max-age=0">
    <meta http-equiv="Pragma" content="no-cache">
    <script>
        function prepararCamara(idInput) {
            const input = document.getElementById(idInput);
            if (input) {
                input.value = "";
            }
        }

        function enviarCamara(formId, inputId) {
            const input = document.getElementById(inputId);
            const form = document.getElementById(formId);

            if (input && form && input.files && input.files.length > 0) {
                form.submit();

                setTimeout(function() {
                    input.value = "";
                }, 500);
            }
        }

        window.addEventListener("pageshow", function() {
            const foto = document.getElementById("camera_photo_input");
            const video = document.getElementById("camera_video_input");

            if (foto) foto.value = "";
            if (video) video.value = "";
        });
    </script>
    <style>
        *{box-sizing:border-box}
        body{margin:0;font-family:-apple-system,BlinkMacSystemFont,Arial,sans-serif;background:radial-gradient(circle at top,#2563eb,#020617 70%);color:white;min-height:100vh}
        .container{max-width:900px;margin:auto;padding:18px}
        .header{text-align:center;padding:18px 0}.header h1{margin:0;font-size:30px}.header p{color:#cbd5e1;margin-top:8px;font-size:15px}
        .card{background:rgba(15,23,42,.92);border:1px solid rgba(148,163,184,.25);border-radius:22px;padding:20px;margin-bottom:18px;box-shadow:0 14px 35px rgba(0,0,0,.35)}
        .card h2{margin-top:0;color:#e0f2fe;font-size:20px}
        input[type=file], textarea{width:100%;padding:14px;border-radius:15px;background:#020617;color:white;border:1px solid #334155;margin-bottom:14px;font-size:15px}
        #camera_photo_input,
        #camera_video_input {
            display: none;
        }
        textarea{min-height:110px}
        button{width:100%;padding:15px;border:none;border-radius:15px;background:linear-gradient(135deg,#2563eb,#06b6d4);color:white;font-size:16px;font-weight:bold}
        .file-list{list-style:none;padding:0;margin:0}.file-item{background:rgba(2,6,23,.88);border:1px solid rgba(148,163,184,.18);margin-bottom:10px;padding:14px;border-radius:15px}
        .file-name{display:block;word-break:break-word;font-size:15px;margin-bottom:10px}
        .download{display:block;background:#16a34a;color:white;text-align:center;text-decoration:none;padding:11px 13px;border-radius:12px;font-size:14px;font-weight:bold;margin-bottom:8px}
        .previewpdf{display:block;background:#2563eb;color:white;text-align:center;text-decoration:none;padding:11px 13px;border-radius:12px;font-size:14px;font-weight:bold;margin-bottom:8px}
        .delete{display:block;background:#dc2626;color:white;text-align:center;text-decoration:none;padding:11px 13px;border-radius:12px;font-size:14px;font-weight:bold}
        .empty{color:#94a3b8;text-align:center;padding:18px;background:rgba(2,6,23,.5);border-radius:14px}
        .info{background:rgba(59,130,246,.16);border:1px solid rgba(147,197,253,.25);padding:15px;border-radius:14px;color:#dbeafe;font-size:14px;line-height:1.6}
        .refresh,.logout{display:inline-block;margin-top:10px;color:#93c5fd;text-decoration:none;font-weight:bold}.logout{color:#fca5a5;font-size:14px}
        .disabled{color:#fca5a5;background:rgba(220,38,38,.14);border:1px solid rgba(248,113,113,.30);padding:14px;border-radius:14px;text-align:center}
        .gallery{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.gallery img{width:100%;height:150px;object-fit:cover;border-radius:14px;border:1px solid #334155}
        .txtbox{white-space:pre-wrap;background:#020617;border:1px solid #334155;padding:12px;border-radius:14px;color:#e5e7eb}
        @media(max-width:650px){.container{padding:14px}.header h1{font-size:25px}.gallery{grid-template-columns:1fr}}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ nombre_servidor }}</h1>
            <p>{{ wt("main_title") }}</p>
            <div class="language-select">
                {% for code, name in web_languages.items() %}
                    <a href="/set_language/{{ code }}?next={{ request.path }}" class="{% if code == web_lang %}active{% endif %}">{{ name }}</a>
                {% endfor %}
            </div>
            {% if protected %}<a class="logout" href="/logout">{{ wt("logout") }}</a>{% endif %}
        </div>

        <div class="card">
            <h2>{{ wt("upload_files_title") }}</h2>
            {% if allow_upload %}
                <form method="POST" action="/upload" enctype="multipart/form-data">
                    <input type="file" name="file" multiple required>
                    <button type="submit">{{ wt("send_files") }}</button>
                </form>
            {% else %}
                <div class="disabled">{{ wt("upload_disabled") }}</div>
            {% endif %}
        </div>

        <div class="card">
            <h2>{{ wt("camera_title") }}</h2>
            {% if allow_upload %}
                <form id="camera_photo_form" method="POST" action="/upload" enctype="multipart/form-data">
                    <input
                        id="camera_photo_input"
                        type="file"
                        name="file"
                        accept="image/*"
                        capture="environment"
                        required
                        onclick="prepararCamara('camera_photo_input')"
                        onchange="enviarCamara('camera_photo_form', 'camera_photo_input')"
                    >
                    <button type="button" onclick="prepararCamara('camera_photo_input'); document.getElementById('camera_photo_input').click();">
                        {{ wt("take_photo") }}
                    </button>
                </form>

                <br>

                <form id="camera_video_form" method="POST" action="/upload" enctype="multipart/form-data">
                    <input
                        id="camera_video_input"
                        type="file"
                        name="file"
                        accept="video/*"
                        capture="environment"
                        required
                        onclick="prepararCamara('camera_video_input')"
                        onchange="enviarCamara('camera_video_form', 'camera_video_input')"
                    >
                    <button type="button" onclick="prepararCamara('camera_video_input'); document.getElementById('camera_video_input').click();">
                        {{ wt("record_video") }}
                    </button>
                </form>

                <div class="info" style="margin-top:14px;">
                    {{ wt("camera_hint") }}
                </div>
            {% else %}
                <div class="disabled">{{ wt("upload_disabled") }}</div>
            {% endif %}
        </div>

        <div class="card">
            <h2>{{ wt("shared_text") }}</h2>
            <div class="info"><strong>{{ wt("text_from_pc") }}:</strong></div><br>
            <div class="txtbox">{{ texto_pc }}</div><br>
            <form method="POST" action="/texto_iphone">
                <textarea name="texto" placeholder="{{ wt('write_text') }}"></textarea>
                <button type="submit">{{ wt("send_text") }}</button>
            </form>
        </div>

        <div class="card">
            <h2>{{ wt("gallery") }}</h2>
            {% if imagenes %}
                <div class="gallery">
                    {% for img in imagenes %}
                        <a href="/download/{{ img }}"><img src="/preview/{{ img }}" alt="{{ img }}"></a>
                    {% endfor %}
                </div>
            {% else %}
                <div class="empty">{{ wt("no_images") }}</div>
            {% endif %}
        </div>

        <div class="card">
            <h2>{{ wt("download_title") }}</h2>
            {% if allow_download %}
                {% if files %}
                    <ul class="file-list">
                        {% for file in files %}
                            <li class="file-item">
                                <span class="file-name">{{ file.icon }} {{ file.name }}</span>
                                {% if file.type == "PDF" %}
                                    <a class="previewpdf" href="/preview_pdf/{{ file.name }}" target="_blank">{{ wt("preview_pdf") }}</a>
                                {% endif %}

                                <a class="download" href="/download/{{ file.name }}">{{ wt("download") }}</a>
                                {% if allow_delete %}
                                    <a class="delete" href="/delete_pc_file/{{ file.name }}" onclick="return confirm('{{ wt("delete_confirm") }}')">{{ wt("delete_from_iphone") }}</a>
                                {% endif %}
                            </li>
                        {% endfor %}
                    </ul>
                {% else %}
                    <div class="empty">{{ wt("no_files") }}</div>
                {% endif %}
            {% else %}
                <div class="disabled">{{ wt("download_disabled") }}</div>
            {% endif %}
            <a class="refresh" href="/">{{ wt("refresh") }}</a>
        </div>

        <div class="card">
            <div class="info">
                <strong>{{ wt("current_mode") }}:</strong> {{ modo_permisos }}<br>
                {{ wt("usage_hint") }}
            </div>
        </div>
    </div>
</body>
</html>
"""


# ============================================================
# FLASK
# ============================================================

flask_app = Flask(__name__)
flask_app.secret_key = "clave_local_transferencia_iphone_pc_2026"

@flask_app.after_request
def agregar_headers_no_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response



@flask_app.before_request
def before_request():
    registrar_dispositivo()


def acceso_protegido():
    return CONFIG["usar_password"] or CONFIG["usar_codigo_temporal"]


def necesita_login():
    if not acceso_protegido():
        return False
    return not session.get("autenticado", False)


def clave_valida(clave):
    claves = []
    if CONFIG["usar_password"] and CONFIG["password"]:
        claves.append(CONFIG["password"])
    if CONFIG["usar_codigo_temporal"] and CONFIG["codigo_temporal"]:
        claves.append(CONFIG["codigo_temporal"])
    return clave in claves



@flask_app.route("/set_language/<lang>")
def set_language(lang):
    """Store the selected browser language in the current web session."""
    if lang in WEB_TRANSLATIONS:
        session["web_lang"] = lang

    destino = request.args.get("next") or request.referrer or url_for("index")
    return redirect(destino)


@flask_app.route("/login", methods=["GET", "POST"])
def login():
    if not acceso_protegido():
        return redirect(url_for("index"))
    error = ""
    if request.method == "POST":
        clave = request.form.get("clave", "")
        if clave_valida(clave):
            session["autenticado"] = True
            return redirect(url_for("index"))
        error = wt("incorrect_key")
    return render_template_string(HTML_LOGIN, error=error, nombre_servidor=CONFIG["nombre_servidor"], **web_contexto_idioma())


@flask_app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@flask_app.route("/")
def index():
    if necesita_login():
        return redirect(url_for("login"))
    limpiar_por_expiracion()
    archivos_pc = listar_archivos(CARPETA_PC_A_IPHONE)
    files = [
        {
            "name": a["nombre"],
            "icon": obtener_icono_archivo(a["nombre"]),
            "type": a.get("tipo", obtener_tipo_archivo(a["nombre"]))
        }
        for a in archivos_pc
    ]
    imagenes = [a["nombre"] for a in archivos_pc if a["tipo"] == "Imagen"]
    return render_template_string(
        HTML_IPHONE,
        files=files,
        imagenes=imagenes,
        protected=acceso_protegido(),
        allow_upload=puede_subir(),
        allow_download=puede_descargar(),
        allow_delete=CONFIG["permitir_eliminar_desde_iphone"],
        modo_permisos=CONFIG["modo_permisos"],
        nombre_servidor=CONFIG["nombre_servidor"],
        texto_pc=CONFIG.get("texto_compartido_pc", ""),
        **web_contexto_idioma()
    )


@flask_app.route("/texto_iphone", methods=["POST"])
def texto_iphone():
    if necesita_login():
        return redirect(url_for("login"))
    texto = request.form.get("texto", "").strip()
    if texto:
        agregar_evento("texto", f"Texto recibido desde iPhone: {texto[:80]}", None)
        agregar_historial("Texto desde iPhone", "iPhone", "PC", len(texto.encode("utf-8")), "Texto recibido")
        with open(os.path.join(CARPETA_HISTORIAL, "textos_iphone.txt"), "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}]\n{texto}\n")
    return redirect(url_for("index"))


@flask_app.route("/upload", methods=["POST"])
def upload():
    if necesita_login():
        return redirect(url_for("login"))
    if not puede_subir():
        return redirect(url_for("index"))

    try:
        archivos = request.files.getlist("file")

        if not archivos:
            return redirect(url_for("index"))

        limite_mb = int(CONFIG.get("limite_mb", 0) or 0)
        content_length = request.content_length or 0

        if limite_mb > 0 and content_length > limite_mb * 1024 * 1024:
            agregar_evento("error", f"Archivo rechazado por superar límite de {limite_mb} MB")
            return "Archivo demasiado grande para el límite configurado.", 413

        recibidos = 0
        ultimo_destino = None

        for archivo in archivos:
            if not archivo or archivo.filename == "":
                continue

            carpeta_fecha = os.path.join(CARPETA_IPHONE_A_PC, datetime.now().strftime("%Y-%m-%d"))
            os.makedirs(carpeta_fecha, exist_ok=True)
            destino = crear_nombre_unico(carpeta_fecha, archivo.filename)
            archivo.save(destino)

            nombre = os.path.basename(destino)
            tamano = os.path.getsize(destino)

            agregar_historial(nombre, "iPhone", "PC", tamano, "Recibido")
            recibidos += 1
            ultimo_destino = destino

        if recibidos == 1 and ultimo_destino:
            agregar_evento("recibido", f"Nuevo archivo recibido desde iPhone: {os.path.basename(ultimo_destino)}", ultimo_destino)
        elif recibidos > 1:
            agregar_evento("recibido", f"{recibidos} archivos recibidos desde iPhone", ultimo_destino)

    except Exception as error:
        print("Error al subir archivo:", error)
        agregar_evento("error", f"Error al recibir archivo: {error}")

    return redirect(url_for("index"))


@flask_app.route("/preview_pdf/<filename>")
def preview_pdf(filename):
    """
    Display a PDF directly in Safari/browser without forcing a download.
    """
    if necesita_login():
        return redirect(url_for("login"))

    if not puede_descargar():
        return redirect(url_for("index"))

    try:
        nombre_seguro = secure_filename(filename)
        ruta = os.path.join(CARPETA_PC_A_IPHONE, nombre_seguro)

        if not os.path.exists(ruta):
            return "Archivo no encontrado.", 404

        if obtener_tipo_archivo(nombre_seguro) != "PDF":
            return redirect(url_for("download", filename=nombre_seguro))

        agregar_historial(
            nombre_seguro,
            "PC",
            "iPhone/Safari",
            os.path.getsize(ruta),
            "Vista previa PDF"
        )

        respuesta = send_from_directory(
            CARPETA_PC_A_IPHONE,
            nombre_seguro,
            as_attachment=False,
            mimetype="application/pdf"
        )

        respuesta.headers["Content-Disposition"] = f'inline; filename="{nombre_seguro}"'
        return respuesta

    except Exception as error:
        print("Error en vista previa PDF:", error)
        return redirect(url_for("index"))


@flask_app.route("/download/<filename>")
def download(filename):
    if necesita_login():
        return redirect(url_for("login"))
    if not puede_descargar():
        return redirect(url_for("index"))
    try:
        nombre_seguro = secure_filename(filename)
        ruta = os.path.join(CARPETA_PC_A_IPHONE, nombre_seguro)
        if os.path.exists(ruta):
            agregar_historial(nombre_seguro, "PC", "iPhone", os.path.getsize(ruta), "Descargado")
        return send_from_directory(CARPETA_PC_A_IPHONE, nombre_seguro, as_attachment=True)
    except Exception as error:
        print("Error al descargar archivo:", error)
        return redirect(url_for("index"))


@flask_app.route("/preview/<filename>")
def preview(filename):
    if necesita_login():
        return redirect(url_for("login"))
    nombre_seguro = secure_filename(filename)
    return send_from_directory(CARPETA_PC_A_IPHONE, nombre_seguro)


@flask_app.route("/delete_pc_file/<filename>")
def delete_pc_file(filename):
    if necesita_login():
        return redirect(url_for("login"))
    if not CONFIG["permitir_eliminar_desde_iphone"]:
        return redirect(url_for("index"))
    try:
        nombre_seguro = secure_filename(filename)
        ruta = os.path.join(CARPETA_PC_A_IPHONE, nombre_seguro)
        if os.path.exists(ruta) and os.path.isfile(ruta):
            tamano = os.path.getsize(ruta)
            os.remove(ruta)
            agregar_historial(nombre_seguro, "iPhone", "PC_A_IPHONE", tamano, "Eliminado desde iPhone")
    except Exception as error:
        print("Error al eliminar desde iPhone:", error)
    return redirect(url_for("index"))


class ServidorFlaskThread(threading.Thread):
    def __init__(self, app, host="0.0.0.0", port=5000):
        super().__init__()
        self.daemon = True
        self.app = app
        self.host = host
        self.port = port
        self.server = None

    def run(self):
        try:
            self.server = make_server(self.host, self.port, self.app, threaded=True)
            self.server.serve_forever()
        except Exception as error:
            print("Error en servidor:", error)

    def detener(self):
        if self.server:
            self.server.shutdown()


# ============================================================
# CUSTOMTKINTER APPLICATION
# ============================================================

class AppTransferencia(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Activar soporte Drag & Drop sin romper CustomTkinter.
        # No se debe heredar de TkinterDnD.Tk junto con ctk.CTk.
        if DND_ACTIVO:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
            except Exception as e:
                print("Drag & Drop no disponible:", e)

        self.title("Transferencia iPhone - PC")
        self.geometry("1200x720")
        self.minsize(1050, 650)

        self.ip_local = obtener_ip_local()
        self.url = f"http://{self.ip_local}:{PUERTO}"

        self.servidor = None
        self.servidor_activo = False
        self.qr_image = None
        self.cancelar_transferencia = False
        self.preview_refs = []
        self.seleccionados = set()
        self.estado_anterior = cargar_estado_sesion()
        self.toast = ToastNotifier() if TOAST_ACTIVO else None

        self.usar_password_var = ctk.BooleanVar(value=CONFIG.get("usar_password", False))
        self.usar_codigo_var = ctk.BooleanVar(value=CONFIG.get("usar_codigo_temporal", False))
        self.eliminar_web_var = ctk.BooleanVar(value=CONFIG.get("permitir_eliminar_desde_iphone", False))
        self.auto_abrir_var = ctk.BooleanVar(value=CONFIG.get("abrir_carpeta_al_recibir", False))
        self.modo_privado_var = ctk.BooleanVar(value=CONFIG.get("modo_privado", False))

        self.crear_interfaz()
        self.generar_qr()
        self.actualizar_todo()

        self.after(1500, self.revisar_eventos)
        self.after(4000, self.auto_actualizar)
        self.protocol("WM_DELETE_WINDOW", self.cerrar_app)

    # ---------------- INTERFACE ----------------

    def crear_interfaz(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.header = ctk.CTkFrame(self, corner_radius=24)
        self.header.grid(row=0, column=0, columnspan=2, padx=14, pady=(12, 8), sticky="ew")
        self.header.grid_columnconfigure(0, weight=1)

        self.header_text = ctk.CTkFrame(self.header, fg_color="transparent")
        self.header_text.grid(row=0, column=0, padx=18, pady=12, sticky="nsew")

        ctk.CTkLabel(
            self.header_text,
            text="Transferencia inalámbrica iPhone ↔ PC",
            font=("Arial", 24, "bold"),
            anchor="w"
        ).pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            self.header_text,
            text="Arrastra archivos, usa cola de transferencias, comparte texto, revisa historial, galería y estadísticas.",
            font=("Arial", 13),
            text_color=("#334155", "#AAB7C4"),
            anchor="w"
        ).pack(fill="x", pady=(0, 12))

        self.url_frame = ctk.CTkFrame(self.header_text, fg_color="transparent")
        self.url_frame.pack(fill="x")
        self.url_frame.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(self.url_frame, height=38, font=("Arial", 13), justify="center")
        self.url_entry.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self.url_entry.insert(0, self.url)
        self.url_entry.configure(state="readonly")

        ctk.CTkButton(self.url_frame, text="Copiar", width=82, height=32, command=self.copiar_url).grid(row=0, column=1, padx=4)
        ctk.CTkButton(self.url_frame, text="Probar PC", width=88, height=32, command=lambda: webbrowser.open(self.url)).grid(row=0, column=2, padx=4)

        self.idioma_menu = ctk.CTkOptionMenu(
            self.url_frame,
            values=[IDIOMAS[k] for k in ["es", "en", "zh", "hi", "ar", "fr"]],
            width=130,
            height=32,
            command=self.cambiar_idioma
        )
        self.idioma_menu.grid(row=0, column=3, padx=(10, 0))
        self.idioma_menu.set(IDIOMAS.get(idioma_actual(), "English"))

        self.qr_container = ctk.CTkFrame(self.header, width=150, height=150, corner_radius=20, fg_color="#FFFFFF", border_width=2, border_color="#CBD5E1")
        self.qr_container.grid(row=0, column=1, padx=(6, 18), pady=12, sticky="e")
        self.qr_container.grid_propagate(False)

        self.qr_label = ctk.CTkLabel(self.qr_container, text="", width=96, height=96, fg_color="#FFFFFF")
        self.qr_label.place(relx=0.5, rely=0.5, anchor="center")

        # IZQUIERDA
        self.panel_izquierdo = ctk.CTkFrame(self, width=300, corner_radius=22)
        self.panel_izquierdo.grid(row=1, column=0, padx=(14, 7), pady=(6, 14), sticky="ns")
        self.panel_izquierdo.grid_propagate(False)

        ctk.CTkLabel(self.panel_izquierdo, text="Servidor local", font=("Arial", 18, "bold")).pack(pady=(18, 4))
        self.estado_label = ctk.CTkLabel(self.panel_izquierdo, text="Detenido", font=("Arial", 13, "bold"), text_color=("#B91C1C", "#EF4444"))
        self.estado_label.pack(pady=(0, 10))

        self.btn_iniciar = ctk.CTkButton(self.panel_izquierdo, text="Iniciar servidor", height=32, font=("Arial", 12, "bold"), command=self.iniciar_servidor)
        self.btn_iniciar.pack(fill="x", padx=18, pady=3)
        self.btn_detener = ctk.CTkButton(self.panel_izquierdo, text="Detener servidor", height=32, font=("Arial", 12, "bold"), fg_color="#B91C1C", hover_color="#991B1B", state="disabled", command=self.detener_servidor)
        self.btn_detener.pack(fill="x", padx=18, pady=3)

        self.info_servidor = ctk.CTkLabel(self.panel_izquierdo, text="Configura las opciones y luego inicia el servidor.", font=("Arial", 12), text_color=("#334155", "#AAB7C4"), wraplength=250, justify="center")
        self.info_servidor.pack(pady=(8, 6), padx=18)

        texto_sesion = "Sin sesión anterior registrada."
        if self.estado_anterior:
            texto_sesion = (
                f"Última sesión: {self.estado_anterior.get('fecha_cierre', '')}\n"
                f"Pendientes: {self.estado_anterior.get('archivos_enviados_pendientes', 0)} | "
                f"Recibidos: {self.estado_anterior.get('archivos_recibidos', 0)}"
            )

        self.sesion_label = ctk.CTkLabel(
            self.panel_izquierdo,
            text=texto_sesion,
            font=("Arial", 10),
            text_color=("#475569", "#94A3B8"),
            wraplength=250,
            justify="center"
        )
        self.sesion_label.pack(pady=(0, 8), padx=18)

        self.config_frame = ctk.CTkScrollableFrame(self.panel_izquierdo, corner_radius=16, height=410)
        self.config_frame.pack(fill="both", expand=True, padx=14, pady=(4, 10))
        self.crear_configuracion()

        # DERECHA
        self.panel_derecho = ctk.CTkFrame(self, corner_radius=24)
        self.panel_derecho.grid(row=1, column=1, padx=(7, 14), pady=(6, 14), sticky="nsew")
        self.panel_derecho.grid_columnconfigure(0, weight=1)
        self.panel_derecho.grid_rowconfigure(0, weight=1)

        self.tabs = ctk.CTkTabview(self.panel_derecho, corner_radius=18)
        self.tabs.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")

        self.tab_enviar = self.tabs.add("Enviar PC → iPhone")
        self.tab_recibir = self.tabs.add("Recibidos")
        self.tab_cola = self.tabs.add("Cola")
        self.tab_texto = self.tabs.add("Texto")
        self.tab_historial = self.tabs.add("Historial")
        self.tab_dispositivos = self.tabs.add("Dispositivos")
        self.tab_actividad = self.tabs.add("Actividad")
        self.tab_stats = self.tabs.add("Estadísticas")

        self.crear_tab_enviar()
        self.crear_tab_recibir()
        self.crear_tab_cola()
        self.crear_tab_texto()
        self.crear_tab_historial()
        self.crear_tab_dispositivos()
        self.crear_tab_actividad()
        self.crear_tab_stats()

    def crear_configuracion(self):
        ctk.CTkLabel(self.config_frame, text="Opciones", font=("Arial", 17, "bold")).pack(pady=(10, 8))

        ctk.CTkLabel(self.config_frame, text="Nombre del servidor", font=("Arial", 12, "bold"), anchor="w").pack(fill="x", padx=10, pady=(3, 1))
        self.nombre_entry = ctk.CTkEntry(self.config_frame, height=32)
        self.nombre_entry.pack(fill="x", padx=10, pady=(0, 6))
        self.nombre_entry.insert(0, CONFIG["nombre_servidor"])

        self.password_check = ctk.CTkCheckBox(self.config_frame, text="Usar contraseña", variable=self.usar_password_var, command=self.actualizar_estado_password)
        self.password_check.pack(anchor="w", padx=10, pady=3)

        self.password_entry = ctk.CTkEntry(self.config_frame, placeholder_text="Contraseña para Safari", show="*", height=32)
        self.password_entry.pack(fill="x", padx=10, pady=(0, 6))
        self.password_entry.insert(0, CONFIG.get("password", ""))
        self.password_entry.configure(state="normal" if self.usar_password_var.get() else "disabled")

        self.codigo_check = ctk.CTkCheckBox(self.config_frame, text="Usar código temporal automático", variable=self.usar_codigo_var)
        self.codigo_check.pack(anchor="w", padx=10, pady=3)

        self.codigo_label = ctk.CTkLabel(self.config_frame, text="Código temporal: desactivado", font=("Arial", 12, "bold"), text_color=("#92400E", "#FACC15"))
        self.codigo_label.pack(fill="x", padx=10, pady=(0, 6))

        ctk.CTkLabel(self.config_frame, text="Modo de permisos", font=("Arial", 12, "bold"), anchor="w").pack(fill="x", padx=12, pady=(6, 2))
        self.modo_menu = ctk.CTkOptionMenu(self.config_frame, values=["Ambos", "Solo enviar al iPhone", "Solo recibir desde iPhone"])
        self.modo_menu.pack(fill="x", padx=10, pady=(0, 6))
        self.modo_menu.set(CONFIG.get("modo_permisos", "Ambos"))

        self.eliminar_web_check = ctk.CTkCheckBox(self.config_frame, text="Permitir eliminar desde iPhone", variable=self.eliminar_web_var)
        self.eliminar_web_check.pack(anchor="w", padx=10, pady=3)

        self.auto_abrir_check = ctk.CTkCheckBox(self.config_frame, text="Abrir carpeta al recibir archivo", variable=self.auto_abrir_var)
        self.auto_abrir_check.pack(anchor="w", padx=10, pady=3)

        self.modo_privado_check = ctk.CTkCheckBox(self.config_frame, text="Modo privado al cerrar", variable=self.modo_privado_var)
        self.modo_privado_check.pack(anchor="w", padx=10, pady=3)

        ctk.CTkLabel(self.config_frame, text="Tema de interfaz", font=("Arial", 12, "bold"), anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        self.tema_menu = ctk.CTkOptionMenu(self.config_frame, values=["dark", "light", "system"], command=self.cambiar_tema)
        self.tema_menu.pack(fill="x", padx=10, pady=(0, 6))
        self.tema_menu.set(CONFIG.get("apariencia", "dark"))

        ctk.CTkLabel(self.config_frame, text="Límite máximo por archivo en MB", font=("Arial", 12, "bold"), anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        self.limite_entry = ctk.CTkEntry(self.config_frame, height=32)
        self.limite_entry.pack(fill="x", padx=10, pady=(0, 6))
        self.limite_entry.insert(0, str(CONFIG.get("limite_mb", 0)))

        ctk.CTkLabel(self.config_frame, text="Expiración automática en horas", font=("Arial", 12, "bold"), anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        self.exp_enviados_entry = ctk.CTkEntry(self.config_frame, height=32, placeholder_text="Enviados, 0 = no borrar")
        self.exp_enviados_entry.pack(fill="x", padx=12, pady=(0, 5))
        self.exp_enviados_entry.insert(0, str(CONFIG.get("borrar_enviados_horas", 0)))
        self.exp_recibidos_entry = ctk.CTkEntry(self.config_frame, height=32, placeholder_text="Recibidos, 0 = no borrar")
        self.exp_recibidos_entry.pack(fill="x", padx=10, pady=(0, 6))
        self.exp_recibidos_entry.insert(0, str(CONFIG.get("borrar_recibidos_horas", 0)))

        ctk.CTkButton(self.config_frame, text="Guardar configuración", height=36, command=self.guardar_config_desde_ui).pack(fill="x", padx=10, pady=3)
        ctk.CTkButton(self.config_frame, text="Abrir carpeta principal", height=36, command=lambda: abrir_ruta(CARPETA_BASE)).pack(fill="x", padx=10, pady=3)
        ctk.CTkButton(self.config_frame, text="Limpiar todo", height=36, fg_color="#B91C1C", hover_color="#991B1B", command=self.limpiar_todo).pack(fill="x", padx=10, pady=3)

    def crear_tab_enviar(self):
        self.tab_enviar.grid_columnconfigure(0, weight=1)
        self.tab_enviar.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(self.tab_enviar, text="Archivos listos para descargar en el iPhone", font=("Arial", 18, "bold")).grid(row=0, column=0, padx=12, pady=(10, 6), sticky="w")

        self.drop_frame = ctk.CTkFrame(self.tab_enviar, corner_radius=16, border_width=2, border_color=("#2563EB", "#2563EB"))
        self.drop_frame.grid(row=1, column=0, padx=16, pady=(0, 10), sticky="ew")
        ctk.CTkLabel(
            self.drop_frame,
            text="Arrastra archivos aquí o usa el botón Agregar archivos",
            font=("Arial", 13, "bold"),
            text_color=("#1D4ED8", "#BFDBFE")
        ).pack(padx=14, pady=14)

        if DND_ACTIVO:
            try:
                self.drop_frame.drop_target_register(DND_FILES)
                self.drop_frame.dnd_bind("<<Drop>>", self.procesar_drop)
            except Exception as e:
                print("No se pudo activar drag & drop:", e)

        botones = ctk.CTkFrame(self.tab_enviar, fg_color="transparent")
        botones.grid(row=2, column=0, padx=10, pady=(0, 6), sticky="ew")
        botones.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        ctk.CTkButton(botones, text="Agregar archivos", height=32, command=self.agregar_archivos_para_iphone).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(botones, text="Enviar carpeta ZIP", height=32, command=self.agregar_carpeta_zip).grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkButton(botones, text="Abrir carpeta", height=32, command=lambda: abrir_ruta(CARPETA_PC_A_IPHONE)).grid(row=0, column=2, padx=5, sticky="ew")
        ctk.CTkButton(botones, text="Limpiar enviados", height=32, fg_color="#B91C1C", hover_color="#991B1B", command=lambda: self.limpiar_carpeta(CARPETA_PC_A_IPHONE, "enviados")).grid(row=0, column=3, padx=5, sticky="ew")
        ctk.CTkButton(botones, text="Cancelar", height=32, fg_color="#92400E", hover_color="#78350F", command=self.cancelar_copia).grid(row=0, column=4, padx=5, sticky="ew")

        self.progress = ctk.CTkProgressBar(self.tab_enviar)
        self.progress.grid(row=4, column=0, padx=12, pady=(0, 6), sticky="ew")
        self.progress.set(0)

        self.scroll_enviar = ctk.CTkScrollableFrame(self.tab_enviar, corner_radius=16)
        self.scroll_enviar.grid(row=4, column=0, padx=10, pady=(0, 6), sticky="nsew")

        filtro = ctk.CTkFrame(self.tab_enviar, fg_color="transparent")
        filtro.grid(row=5, column=0, padx=10, pady=(0, 6), sticky="ew")
        filtro.grid_columnconfigure(0, weight=1)
        self.buscar_enviar = ctk.CTkEntry(filtro, placeholder_text="Buscar archivo enviado...")
        self.buscar_enviar.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self.buscar_enviar.bind("<KeyRelease>", lambda e: self.actualizar_todo())
        self.orden_enviar = ctk.CTkOptionMenu(filtro, values=["Fecha", "Nombre", "Tamaño", "Tipo"], command=lambda v: self.actualizar_todo())
        self.orden_enviar.grid(row=0, column=1)

        self.info_enviar = ctk.CTkLabel(self.tab_enviar, text="Selecciona o arrastra archivos desde la PC. Luego en el iPhone toca Descargar.", font=("Arial", 13), text_color=("#334155", "#AAB7C4"))
        self.info_enviar.grid(row=7, column=0, padx=16, pady=(0, 6), sticky="w")

    def crear_tab_recibir(self):
        self.tab_recibir.grid_columnconfigure(0, weight=1)
        self.tab_recibir.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(self.tab_recibir, text="Archivos recibidos desde el iPhone", font=("Arial", 18, "bold")).grid(row=0, column=0, padx=12, pady=(10, 6), sticky="w")

        botones = ctk.CTkFrame(self.tab_recibir, fg_color="transparent")
        botones.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="ew")
        botones.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(botones, text="Abrir carpeta recibidos", height=32, command=lambda: abrir_ruta(CARPETA_IPHONE_A_PC)).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(botones, text="Actualizar", height=32, command=self.actualizar_todo).grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkButton(botones, text="Limpiar recibidos", height=32, fg_color="#B91C1C", hover_color="#991B1B", command=lambda: self.limpiar_carpeta(CARPETA_IPHONE_A_PC, "recibidos")).grid(row=0, column=2, padx=5, sticky="ew")

        self.scroll_recibir = ctk.CTkScrollableFrame(self.tab_recibir, corner_radius=16)
        self.scroll_recibir.grid(row=2, column=0, padx=10, pady=(0, 6), sticky="nsew")

        filtro = ctk.CTkFrame(self.tab_recibir, fg_color="transparent")
        filtro.grid(row=3, column=0, padx=10, pady=(0, 6), sticky="ew")
        filtro.grid_columnconfigure(0, weight=1)
        self.buscar_recibir = ctk.CTkEntry(filtro, placeholder_text="Buscar archivo recibido...")
        self.buscar_recibir.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self.buscar_recibir.bind("<KeyRelease>", lambda e: self.actualizar_todo())
        self.orden_recibir = ctk.CTkOptionMenu(filtro, values=["Fecha", "Nombre", "Tamaño", "Tipo"], command=lambda v: self.actualizar_todo())
        self.orden_recibir.grid(row=0, column=1)

        self.info_recibir = ctk.CTkLabel(self.tab_recibir, text="Cuando subas archivos desde Safari en el iPhone, aparecerán aquí.", font=("Arial", 13), text_color=("#334155", "#AAB7C4"))
        self.info_recibir.grid(row=4, column=0, padx=10, pady=(0, 6), sticky="w")

    def crear_tab_cola(self):
        self.tab_cola.grid_columnconfigure(0, weight=1)
        self.tab_cola.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self.tab_cola, text="Cola de transferencias", font=("Arial", 18, "bold")).grid(row=0, column=0, padx=12, pady=12, sticky="w")
        self.scroll_cola = ctk.CTkScrollableFrame(self.tab_cola, corner_radius=16)
        self.scroll_cola.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")

    def crear_tab_texto(self):
        self.tab_texto.grid_columnconfigure(0, weight=1)
        self.tab_texto.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.tab_texto, text="Texto rápido PC ↔ iPhone", font=("Arial", 18, "bold")).grid(row=0, column=0, padx=12, pady=(10, 6), sticky="w")
        self.texto_pc = ctk.CTkTextbox(self.tab_texto, height=180)
        self.texto_pc.grid(row=1, column=0, padx=16, pady=(0, 10), sticky="nsew")
        self.texto_pc.insert("1.0", CONFIG.get("texto_compartido_pc", ""))

        botones = ctk.CTkFrame(self.tab_texto, fg_color="transparent")
        botones.grid(row=2, column=0, padx=10, pady=(0, 6), sticky="ew")
        botones.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(botones, text="Guardar texto para iPhone", command=self.guardar_texto_pc).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(botones, text="Abrir textos recibidos", command=lambda: abrir_ruta(os.path.join(CARPETA_HISTORIAL, "textos_iphone.txt"))).grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkButton(botones, text="Limpiar texto", fg_color="#B91C1C", hover_color="#991B1B", command=self.limpiar_texto_pc).grid(row=0, column=2, padx=5, sticky="ew")

        self.info_texto = ctk.CTkLabel(self.tab_texto, text="El texto guardado aparecerá en Safari del iPhone.", text_color=("#334155", "#AAB7C4"))
        self.info_texto.grid(row=3, column=0, padx=12, pady=(0, 12), sticky="w")

    def crear_tab_historial(self):
        self.tab_historial.grid_columnconfigure(0, weight=1)
        self.tab_historial.grid_rowconfigure(1, weight=1)
        botones = ctk.CTkFrame(self.tab_historial, fg_color="transparent")
        botones.grid(row=0, column=0, padx=12, pady=12, sticky="ew")
        botones.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(botones, text="Actualizar historial", height=38, command=self.actualizar_historial).grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(botones, text="Limpiar historial", height=38, fg_color="#B91C1C", hover_color="#991B1B", command=self.limpiar_historial).grid(row=0, column=1, padx=5, sticky="ew")
        self.scroll_historial = ctk.CTkScrollableFrame(self.tab_historial, corner_radius=16)
        self.scroll_historial.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")

    def crear_tab_dispositivos(self):
        self.tab_dispositivos.grid_columnconfigure(0, weight=1)
        self.tab_dispositivos.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self.tab_dispositivos, text="Dispositivos conectados", font=("Arial", 18, "bold")).grid(row=0, column=0, padx=12, pady=(10, 6), sticky="w")
        self.scroll_dispositivos = ctk.CTkScrollableFrame(self.tab_dispositivos, corner_radius=16)
        self.scroll_dispositivos.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")

    def crear_tab_actividad(self):
        self.tab_actividad.grid_columnconfigure(0, weight=1)
        self.tab_actividad.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.tab_actividad,
            text="Actividad en vivo",
            font=("Arial", 18, "bold")
        ).grid(row=0, column=0, padx=12, pady=(10, 6), sticky="w")

        self.scroll_actividad = ctk.CTkScrollableFrame(self.tab_actividad, corner_radius=16)
        self.scroll_actividad.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")

    def crear_tab_stats(self):
        self.tab_stats.grid_columnconfigure(0, weight=1)
        self.tab_stats.grid_rowconfigure(0, weight=1)
        self.scroll_stats = ctk.CTkScrollableFrame(self.tab_stats, corner_radius=16)
        self.scroll_stats.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")

    # ---------------- CONFIGURATION ----------------

    def cambiar_idioma(self, nombre_idioma):
        for codigo, nombre in IDIOMAS.items():
            if nombre == nombre_idioma:
                CONFIG["idioma"] = codigo
                guardar_configuracion()
                messagebox.showinfo(t("language"), t("restart"))
                return

    def cambiar_tema(self, tema):
        ctk.set_appearance_mode(tema)
        CONFIG["apariencia"] = tema
        guardar_configuracion()

    def actualizar_estado_password(self):
        if self.usar_password_var.get():
            self.password_entry.configure(state="normal")
        else:
            self.password_entry.delete(0, "end")
            self.password_entry.configure(state="disabled")

    def guardar_config_desde_ui(self):
        if self.aplicar_configuracion(generar_codigo=False):
            guardar_configuracion()
            guardar_estado_sesion()
            self.info_servidor.configure(text="Configuración guardada correctamente.")

    def aplicar_configuracion(self, generar_codigo=True):
        nombre = self.nombre_entry.get().strip() or "PC Local"
        password = self.password_entry.get().strip()
        usar_password = self.usar_password_var.get()

        if usar_password and not password:
            messagebox.showwarning("Contraseña requerida", "Activaste contraseña, pero no escribiste ninguna clave.")
            return False

        try:
            limite = int(self.limite_entry.get().strip() or "0")
            exp_env = int(self.exp_enviados_entry.get().strip() or "0")
            exp_rec = int(self.exp_recibidos_entry.get().strip() or "0")
            limite = max(limite, 0)
            exp_env = max(exp_env, 0)
            exp_rec = max(exp_rec, 0)
        except ValueError:
            messagebox.showwarning("Valor inválido", "El límite y expiración deben ser números enteros.")
            return False

        CONFIG["nombre_servidor"] = nombre
        CONFIG["usar_password"] = usar_password
        CONFIG["password"] = password
        CONFIG["usar_codigo_temporal"] = self.usar_codigo_var.get()
        CONFIG["modo_permisos"] = self.modo_menu.get()
        CONFIG["permitir_eliminar_desde_iphone"] = self.eliminar_web_var.get()
        CONFIG["abrir_carpeta_al_recibir"] = self.auto_abrir_var.get()
        CONFIG["limite_mb"] = limite
        CONFIG["modo_privado"] = self.modo_privado_var.get()
        CONFIG["borrar_enviados_horas"] = exp_env
        CONFIG["borrar_recibidos_horas"] = exp_rec

        if CONFIG["usar_codigo_temporal"] and generar_codigo:
            CONFIG["codigo_temporal"] = generar_codigo_temporal()
            self.codigo_label.configure(text=f"Código temporal: {CONFIG['codigo_temporal']}", text_color=("#15803D", "#22C55E"))
        elif not CONFIG["usar_codigo_temporal"]:
            CONFIG["codigo_temporal"] = ""
            self.codigo_label.configure(text="Código temporal: desactivado", text_color=("#92400E", "#FACC15"))

        guardar_configuracion()
        return True

    def bloquear_configuracion(self, bloquear=True):
        estado = "disabled" if bloquear else "normal"
        widgets = [
            self.nombre_entry, self.password_check, self.codigo_check, self.modo_menu,
            self.eliminar_web_check, self.auto_abrir_check, self.modo_privado_check,
            self.tema_menu, self.limite_entry, self.exp_enviados_entry, self.exp_recibidos_entry
        ]
        for w in widgets:
            try:
                w.configure(state=estado)
            except Exception:
                pass
        if bloquear:
            self.password_entry.configure(state="disabled")
        else:
            self.password_entry.configure(state="normal" if self.usar_password_var.get() else "disabled")

    # ---------------- SERVER ----------------

    def iniciar_servidor(self):
        if self.servidor_activo:
            return
        if not self.aplicar_configuracion(generar_codigo=True):
            return
        try:
            self.servidor = ServidorFlaskThread(flask_app, host="0.0.0.0", port=PUERTO)
            self.servidor.start()
            self.servidor_activo = True
            self.estado_label.configure(text="Activo", text_color=("#15803D", "#22C55E"))
            self.btn_iniciar.configure(state="disabled")
            self.btn_detener.configure(state="normal")
            self.bloquear_configuracion(True)
            texto = f"Servidor activo. Abre en el iPhone: {self.url}"
            if CONFIG["usar_codigo_temporal"]:
                texto += f" | Código: {CONFIG['codigo_temporal']}"
            self.info_servidor.configure(text=texto)
            self.info_enviar.configure(text=texto)
        except Exception as error:
            self.estado_label.configure(text="Error", text_color=("#B91C1C", "#EF4444"))
            messagebox.showerror("Error", f"No se pudo iniciar el servidor:\n{error}")

    def detener_servidor(self):
        try:
            if self.servidor:
                self.servidor.detener()
                self.servidor = None
            self.servidor_activo = False
            self.estado_label.configure(text="Detenido", text_color=("#B91C1C", "#EF4444"))
            self.btn_iniciar.configure(state="normal")
            self.btn_detener.configure(state="disabled")
            self.bloquear_configuracion(False)
            CONFIG["codigo_temporal"] = ""
            self.codigo_label.configure(text="Código temporal: desactivado", text_color=("#92400E", "#FACC15"))
            self.info_servidor.configure(text="Servidor detenido. Puedes cambiar las opciones antes de volver a iniciar.")
            self.info_enviar.configure(text="Servidor detenido. Inicia nuevamente para transferir archivos.")
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo detener el servidor:\n{error}")

    # ---------------- QR ----------------

    def generar_qr(self):
        try:
            qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
            qr.add_data(self.url)
            qr.make(fit=True)
            img_qr = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            img_qr = img_qr.resize((96, 96), Image.Resampling.NEAREST)
            self.qr_image = ctk.CTkImage(light_image=img_qr, dark_image=img_qr, size=(96, 96))
            self.qr_label.configure(image=self.qr_image, text="")
        except Exception as error:
            self.qr_label.configure(text=f"QR no disponible\n{error}", text_color=("#111827", "#000000"))

    def copiar_url(self):
        self.clipboard_clear()
        self.clipboard_append(self.url)
        self.info_servidor.configure(text=f"Dirección copiada: {self.url}")
        self.info_enviar.configure(text=f"Dirección copiada: {self.url}")

    # ---------------- DRAG DROP AND QUEUE ----------------

    def procesar_drop(self, event):
        data = event.data
        rutas = self.parsear_rutas_drop(data)
        archivos = [r for r in rutas if os.path.isfile(r)]
        carpetas = [r for r in rutas if os.path.isdir(r)]

        if archivos:
            self.iniciar_copia_archivos(archivos)
        for carpeta in carpetas:
            self.iniciar_zip_carpeta(carpeta)

    def parsear_rutas_drop(self, data):
        # Soporta rutas con espacios entre llaves {C:/Mi archivo.pdf}
        rutas = []
        actual = ""
        dentro = False
        for ch in data:
            if ch == "{":
                dentro = True
                actual = ""
            elif ch == "}":
                dentro = False
                rutas.append(actual)
                actual = ""
            elif ch == " " and not dentro:
                if actual:
                    rutas.append(actual)
                    actual = ""
            else:
                actual += ch
        if actual:
            rutas.append(actual)
        return [r.strip() for r in rutas if r.strip()]

    def agregar_archivos_para_iphone(self):
        archivos = filedialog.askopenfilenames(title="Selecciona archivos para enviar al iPhone")
        if archivos:
            self.iniciar_copia_archivos(list(archivos))

    def iniciar_copia_archivos(self, archivos):
        self.cancelar_transferencia = False
        self.agregar_tarea_cola(f"{len(archivos)} archivo(s)", "Pendiente")
        hilo = threading.Thread(target=self.copiar_archivos_con_progreso, args=(archivos,), daemon=True)
        hilo.start()

    def copiar_archivos_con_progreso(self, archivos):
        total = len(archivos)
        copiados = 0
        for i, archivo in enumerate(archivos, start=1):
            if self.cancelar_transferencia:
                self.after(0, lambda: self.info_enviar.configure(text="Transferencia cancelada."))
                break
            try:
                nombre = os.path.basename(archivo)
                self.after(0, lambda n=nombre: self.agregar_tarea_cola(n, "Copiando"))
                destino = crear_nombre_unico(CARPETA_PC_A_IPHONE, nombre)
                tamano_total = os.path.getsize(archivo)
                copiado = 0
                inicio_copia = time.time()
                with open(archivo, "rb") as origen, open(destino, "wb") as salida:
                    while True:
                        if self.cancelar_transferencia:
                            try:
                                salida.close()
                                os.remove(destino)
                            except Exception:
                                pass
                            break
                        bloque = origen.read(1024 * 1024)
                        if not bloque:
                            break
                        salida.write(bloque)
                        copiado += len(bloque)
                        progreso_archivo = copiado / tamano_total if tamano_total > 0 else 1
                        progreso_total = ((i - 1) + progreso_archivo) / total
                        self.after(0, lambda p=progreso_total: self.progress.set(p))
                        transcurrido = max(time.time() - inicio_copia, 0.001)
                        velocidad = copiado / transcurrido
                        restante = max(tamano_total - copiado, 0)
                        eta = restante / velocidad if velocidad > 0 else 0
                        self.after(
                            0,
                            lambda n=nombre, v=velocidad, e=eta: self.info_enviar.configure(
                                text=f"Copiando {n} | Velocidad: {formatear_tamano(v)}/s | Restante: {int(e)} s"
                            )
                        )
                if self.cancelar_transferencia:
                    break
                shutil.copystat(archivo, destino)
                copiados += 1
                agregar_historial(os.path.basename(destino), "PC", "iPhone", os.path.getsize(destino), "Listo para descargar")
                self.after(0, lambda n=os.path.basename(destino): self.agregar_tarea_cola(n, "Listo"))
            except Exception as error:
                print("Error copiando:", error)
                self.after(0, lambda n=os.path.basename(archivo), e=error: self.agregar_tarea_cola(n, f"Error: {e}"))

        self.after(0, self.actualizar_todo)
        self.after(0, lambda: self.info_enviar.configure(text=f"{copiados} archivo(s) listo(s). Actualiza Safari en el iPhone y toca Descargar."))
        self.after(0, lambda: self.progress.set(0))

    def agregar_carpeta_zip(self):
        carpeta = filedialog.askdirectory(title="Selecciona una carpeta para enviar como ZIP")
        if carpeta:
            self.iniciar_zip_carpeta(carpeta)

    def iniciar_zip_carpeta(self, carpeta):
        self.cancelar_transferencia = False
        hilo = threading.Thread(target=self.comprimir_carpeta, args=(carpeta,), daemon=True)
        hilo.start()

    def comprimir_carpeta(self, carpeta):
        try:
            nombre_carpeta = os.path.basename(os.path.normpath(carpeta))
            nombre_zip = secure_filename(nombre_carpeta) or "carpeta"
            destino_zip = crear_nombre_unico(CARPETA_PC_A_IPHONE, f"{nombre_zip}.zip")
            destino_sin_ext = os.path.splitext(destino_zip)[0]
            self.after(0, lambda: self.info_enviar.configure(text="Comprimiendo carpeta en ZIP..."))
            self.after(0, lambda: self.progress.set(0.35))
            self.after(0, lambda: self.agregar_tarea_cola(os.path.basename(destino_zip), "Comprimiendo"))
            shutil.make_archive(destino_sin_ext, "zip", carpeta)
            self.after(0, lambda: self.progress.set(1))
            tamano = os.path.getsize(destino_zip)
            agregar_historial(os.path.basename(destino_zip), "PC", "iPhone", tamano, "Carpeta ZIP lista")
            self.after(0, lambda: self.agregar_tarea_cola(os.path.basename(destino_zip), "Listo"))
            self.after(0, self.actualizar_todo)
            self.after(0, lambda: self.info_enviar.configure(text=f"Carpeta comprimida y lista: {os.path.basename(destino_zip)}"))
            self.after(800, lambda: self.progress.set(0))
        except Exception as error:
            self.after(0, lambda: messagebox.showerror("Error", f"No se pudo comprimir la carpeta:\n{error}"))
            self.after(0, lambda: self.progress.set(0))

    def cancelar_copia(self):
        self.cancelar_transferencia = True
        self.info_enviar.configure(text="Cancelando transferencia...")

    def agregar_tarea_cola(self, nombre, estado):
        if not hasattr(self, "scroll_cola"):
            return
        frame = ctk.CTkFrame(self.scroll_cola, corner_radius=12)
        frame.pack(fill="x", padx=8, pady=5)
        ctk.CTkLabel(frame, text=nombre, font=("Arial", 12, "bold"), anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        ctk.CTkLabel(frame, text=f"Estado: {estado} | {datetime.now().strftime('%H:%M:%S')}", font=("Arial", 10), text_color=("#334155", "#AAB7C4"), anchor="w").pack(fill="x", padx=10, pady=(0, 6))

    # ---------------- TEXT ----------------

    def guardar_texto_pc(self):
        texto = self.texto_pc.get("1.0", "end").strip()
        CONFIG["texto_compartido_pc"] = texto
        guardar_configuracion()
        self.info_texto.configure(text="Texto guardado. Aparecerá en Safari del iPhone.")

    def limpiar_texto_pc(self):
        self.texto_pc.delete("1.0", "end")
        CONFIG["texto_compartido_pc"] = ""
        guardar_configuracion()
        self.info_texto.configure(text="Texto limpiado.")

    # ---------------- LISTS ----------------

    def ordenar_filtrar(self, archivos, busqueda, orden):
        if busqueda:
            archivos = [a for a in archivos if busqueda.lower() in a["nombre"].lower()]
        if orden == "Nombre":
            archivos.sort(key=lambda a: a["nombre"].lower())
        elif orden == "Tamaño":
            archivos.sort(key=lambda a: a["tamano"], reverse=True)
        elif orden == "Tipo":
            archivos.sort(key=lambda a: a["tipo"])
        else:
            archivos.sort(key=lambda a: a["mtime"], reverse=True)
        return archivos

    def actualizar_todo(self):
        limpiar_por_expiracion()
        if hasattr(self, "scroll_enviar"):
            archivos = self.ordenar_filtrar(
                listar_archivos(CARPETA_PC_A_IPHONE),
                self.buscar_enviar.get() if hasattr(self, "buscar_enviar") else "",
                self.orden_enviar.get() if hasattr(self, "orden_enviar") else "Fecha"
            )
            self.actualizar_lista(archivos, self.scroll_enviar, "enviar")
        if hasattr(self, "scroll_recibir"):
            archivos = self.ordenar_filtrar(
                listar_archivos(CARPETA_IPHONE_A_PC),
                self.buscar_recibir.get() if hasattr(self, "buscar_recibir") else "",
                self.orden_recibir.get() if hasattr(self, "orden_recibir") else "Fecha"
            )
            self.actualizar_lista(archivos, self.scroll_recibir, "recibir")
        self.actualizar_historial()
        self.actualizar_dispositivos()
        self.actualizar_actividad()
        self.actualizar_stats()

    def actualizar_lista(self, archivos, contenedor, tipo):
        self.preview_refs = []
        for widget in contenedor.winfo_children():
            widget.destroy()
        if not archivos:
            texto = "No hay archivos para enviar al iPhone." if tipo == "enviar" else "No hay archivos recibidos desde el iPhone."
            ctk.CTkLabel(contenedor, text=texto, font=("Arial", 13), text_color=("#475569", "#94A3B8")).pack(pady=30)
            return
        for archivo in archivos:
            self.crear_item_archivo(contenedor, archivo)

    def crear_item_archivo(self, contenedor, archivo):
        # Tarjeta compacta horizontal con selección múltiple y renombrar.
        frame = ctk.CTkFrame(contenedor, corner_radius=14)
        frame.pack(fill="x", padx=6, pady=3)
        frame.grid_columnconfigure(2, weight=1)

        nombre = archivo["nombre"]
        nombre_mostrar = archivo.get("relativo", nombre)
        ruta = archivo["ruta"]
        tamano = formatear_tamano(archivo["tamano"])
        fecha = archivo["fecha"]
        icono = obtener_icono_archivo(nombre)

        var_sel = ctk.BooleanVar(value=ruta in self.seleccionados)

        ctk.CTkCheckBox(
            frame,
            text="",
            width=26,
            variable=var_sel,
            command=lambda r=ruta, v=var_sel: self.toggle_seleccion(r, v.get())
        ).grid(row=0, column=0, rowspan=2, padx=(8, 0), pady=8)

        # Miniatura o icono compacto
        if archivo["tipo"] == "Imagen":
            try:
                img = Image.open(ruta)
                img.thumbnail((38, 38))
                thumb = ctk.CTkImage(light_image=img.copy(), dark_image=img.copy(), size=(38, 38))
                self.preview_refs.append(thumb)
                ctk.CTkLabel(frame, image=thumb, text="", width=48).grid(row=0, column=1, rowspan=2, padx=(4, 8), pady=8)
            except Exception:
                ctk.CTkLabel(frame, text=icono, font=("Arial", 22), width=48).grid(row=0, column=1, rowspan=2, padx=(4, 8), pady=8)
        else:
            ctk.CTkLabel(frame, text=icono, font=("Arial", 22), width=48).grid(row=0, column=1, rowspan=2, padx=(4, 8), pady=8)

        ctk.CTkLabel(
            frame,
            text=nombre_mostrar,
            font=("Arial", 13, "bold"),
            anchor="w"
        ).grid(row=0, column=2, sticky="ew", padx=(0, 8), pady=(8, 0))

        ctk.CTkLabel(
            frame,
            text=f"{archivo['tipo']}  •  {tamano}  •  {fecha}",
            font=("Arial", 10),
            text_color=("#334155", "#AAB7C4"),
            anchor="w"
        ).grid(row=1, column=2, sticky="ew", padx=(0, 8), pady=(0, 8))

        botones = ctk.CTkFrame(frame, fg_color="transparent")
        botones.grid(row=0, column=3, rowspan=2, padx=(0, 10), pady=8, sticky="e")
        botones.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkButton(botones, text="Abrir", width=58, height=28, command=lambda r=ruta: abrir_ruta(r)).grid(row=0, column=0, padx=2)
        ctk.CTkButton(botones, text="Carpeta", width=66, height=28, command=lambda r=os.path.dirname(ruta): abrir_ruta(r)).grid(row=0, column=1, padx=2)

        if archivo["tipo"] == "PDF":
            ctk.CTkButton(
                botones,
                text="Ver PDF",
                width=68,
                height=28,
                command=lambda n=nombre: webbrowser.open(f"{self.url}/preview_pdf/{n}")
            ).grid(row=0, column=2, padx=2)
            col_renombrar = 3
            col_eliminar = 4
        else:
            col_renombrar = 2
            col_eliminar = 3

        ctk.CTkButton(botones, text="Renombrar", width=82, height=28, command=lambda r=ruta: self.renombrar_archivo(r)).grid(row=0, column=col_renombrar, padx=2)
        ctk.CTkButton(botones, text="Eliminar", width=70, height=28, fg_color="#B91C1C", hover_color="#991B1B", command=lambda r=ruta: self.eliminar_archivo(r)).grid(row=0, column=col_eliminar, padx=2)

    # ---------------- HISTORY / DEVICES / STATS ----------------

    def actualizar_historial(self):
        if not hasattr(self, "scroll_historial"):
            return
        for widget in self.scroll_historial.winfo_children():
            widget.destroy()
        registros = leer_historial()
        if not registros:
            ctk.CTkLabel(self.scroll_historial, text="No hay historial todavía.", font=("Arial", 13), text_color=("#475569", "#94A3B8")).pack(pady=30)
            return
        for r in registros[:120]:
            frame = ctk.CTkFrame(self.scroll_historial, corner_radius=14)
            frame.pack(fill="x", padx=8, pady=5)
            ctk.CTkLabel(frame, text=r.get("archivo", ""), font=("Arial", 13, "bold"), anchor="w").pack(fill="x", padx=12, pady=(10, 2))
            detalle = f"{r.get('fecha','')} | {r.get('origen','')} → {r.get('destino','')} | {r.get('tamano','')} | {r.get('estado','')}"
            ctk.CTkLabel(frame, text=detalle, font=("Arial", 10), text_color=("#334155", "#AAB7C4"), anchor="w").pack(fill="x", padx=10, pady=(0, 6))

    def actualizar_dispositivos(self):
        if not hasattr(self, "scroll_dispositivos"):
            return
        for widget in self.scroll_dispositivos.winfo_children():
            widget.destroy()
        if not DISPOSITIVOS_CONECTADOS:
            ctk.CTkLabel(self.scroll_dispositivos, text="Todavía no hay dispositivos conectados.", font=("Arial", 13), text_color=("#475569", "#94A3B8")).pack(pady=30)
            return
        for d in DISPOSITIVOS_CONECTADOS.values():
            frame = ctk.CTkFrame(self.scroll_dispositivos, corner_radius=14)
            frame.pack(fill="x", padx=8, pady=5)
            ctk.CTkLabel(frame, text=f"📱 {d['ip']}", font=("Arial", 13, "bold"), anchor="w").pack(fill="x", padx=12, pady=(10, 2))
            ctk.CTkLabel(frame, text=f"Último acceso: {d['ultimo_acceso']}\n{d['user_agent']}", font=("Arial", 10), text_color=("#334155", "#AAB7C4"), anchor="w", justify="left").pack(fill="x", padx=10, pady=(0, 6))

    def actualizar_actividad(self):
        if not hasattr(self, "scroll_actividad"):
            return

        for widget in self.scroll_actividad.winfo_children():
            widget.destroy()

        if not EVENTOS_LOG:
            ctk.CTkLabel(
                self.scroll_actividad,
                text="Todavía no hay actividad en vivo.",
                font=("Arial", 15),
                text_color=("#475569", "#94A3B8")
            ).pack(pady=30)
            return

        for evento in EVENTOS_LOG[:80]:
            frame = ctk.CTkFrame(self.scroll_actividad, corner_radius=14)
            frame.pack(fill="x", padx=8, pady=5)

            tipo = evento.get("tipo", "evento")
            icono = "📥" if tipo == "recibido" else "📝" if tipo == "texto" else "⚠️" if tipo == "error" else "📡"

            ctk.CTkLabel(
                frame,
                text=f"{icono} {evento.get('mensaje', '')}",
                font=("Arial", 13, "bold"),
                anchor="w"
            ).pack(fill="x", padx=12, pady=(8, 2))

            ctk.CTkLabel(
                frame,
                text=evento.get("fecha_completa", evento.get("fecha", "")),
                font=("Arial", 10),
                text_color=("#334155", "#AAB7C4"),
                anchor="w"
            ).pack(fill="x", padx=12, pady=(0, 8))

    def actualizar_stats(self):
        if not hasattr(self, "scroll_stats"):
            return
        for widget in self.scroll_stats.winfo_children():
            widget.destroy()

        enviados = listar_archivos(CARPETA_PC_A_IPHONE)
        recibidos = listar_archivos(CARPETA_IPHONE_A_PC)
        historial = leer_historial()
        total_bytes = 0
        for r in historial:
            try:
                total_bytes += int(float(r.get("bytes", 0)))
            except Exception:
                pass

        stats = [
            ("Archivos listos para iPhone", str(len(enviados))),
            ("Archivos recibidos desde iPhone", str(len(recibidos))),
            ("Dispositivos conectados", str(len(DISPOSITIVOS_CONECTADOS))),
            ("Registros en historial", str(len(historial))),
            ("Total transferido registrado", formatear_tamano(total_bytes)),
            ("Almacenamiento en enviados", formatear_tamano(sum(a["tamano"] for a in enviados))),
            ("Almacenamiento en recibidos", formatear_tamano(sum(a["tamano"] for a in recibidos))),
            ("Almacenamiento total local", formatear_tamano(sum(a["tamano"] for a in enviados) + sum(a["tamano"] for a in recibidos))),
            ("Organización recibidos", "Por fecha automática en IPHONE_A_PC/YYYY-MM-DD"),
            ("Eventos en actividad", str(len(EVENTOS_LOG))),
            ("Modo de permisos", CONFIG.get("modo_permisos", "Ambos")),
            ("Protección activa", "Sí" if (CONFIG.get("usar_password") or CONFIG.get("usar_codigo_temporal")) else "No"),
            ("Drag & Drop", "Activo" if DND_ACTIVO else "No disponible. Instala tkinterdnd2")
        ]

        for titulo, valor in stats:
            frame = ctk.CTkFrame(self.scroll_stats, corner_radius=14)
            frame.pack(fill="x", padx=8, pady=6)
            ctk.CTkLabel(frame, text=titulo, font=("Arial", 13, "bold"), anchor="w").pack(fill="x", padx=12, pady=(10, 2))
            ctk.CTkLabel(frame, text=valor, font=("Arial", 16), text_color=("#1D4ED8", "#BFDBFE"), anchor="w").pack(fill="x", padx=10, pady=(0, 6))

    # ---------------- CLEANUP ----------------

    def toggle_seleccion(self, ruta, seleccionado):
        if seleccionado:
            self.seleccionados.add(ruta)
        else:
            self.seleccionados.discard(ruta)

    def limpiar_seleccion(self):
        self.seleccionados.clear()
        self.actualizar_todo()

    def eliminar_seleccionados(self):
        if not self.seleccionados:
            messagebox.showinfo("Selección vacía", "No hay archivos seleccionados.")
            return

        confirmar = messagebox.askyesno(
            "Eliminar seleccionados",
            f"¿Deseas eliminar {len(self.seleccionados)} archivo(s) seleccionado(s)?"
        )

        if not confirmar:
            return

        for ruta in list(self.seleccionados):
            try:
                if os.path.exists(ruta) and os.path.isfile(ruta):
                    tamano = os.path.getsize(ruta)
                    nombre = os.path.basename(ruta)
                    os.remove(ruta)
                    agregar_historial(nombre, "PC", "Local", tamano, "Eliminado seleccionado")
            except Exception as e:
                print("Error eliminando seleccionado:", e)

        self.seleccionados.clear()
        self.actualizar_todo()

    def zip_seleccionados(self):
        rutas = [r for r in self.seleccionados if os.path.exists(r) and os.path.isfile(r)]

        if not rutas:
            messagebox.showinfo("Selección vacía", "No hay archivos seleccionados para comprimir.")
            return

        nombre_zip = simpledialog.askstring(
            "Nombre del ZIP",
            "Escribe el nombre del paquete ZIP:",
            initialvalue="paquete_para_iphone.zip"
        )

        if not nombre_zip:
            return

        if not nombre_zip.lower().endswith(".zip"):
            nombre_zip += ".zip"

        destino_zip = crear_nombre_unico(CARPETA_PC_A_IPHONE, nombre_zip)

        try:
            with zipfile.ZipFile(destino_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
                for ruta in rutas:
                    zipf.write(ruta, arcname=os.path.basename(ruta))

            agregar_historial(
                os.path.basename(destino_zip),
                "PC",
                "iPhone",
                os.path.getsize(destino_zip),
                "ZIP de seleccionados listo"
            )

            self.seleccionados.clear()
            self.actualizar_todo()
            self.info_enviar.configure(text=f"ZIP creado: {os.path.basename(destino_zip)}")

        except Exception as error:
            messagebox.showerror("Error", f"No se pudo crear el ZIP:\n{error}")

    def renombrar_archivo(self, ruta):
        if not os.path.exists(ruta):
            messagebox.showerror("Error", "El archivo ya no existe.")
            return

        carpeta = os.path.dirname(ruta)
        nombre_actual = os.path.basename(ruta)

        nuevo_nombre = simpledialog.askstring(
            "Renombrar archivo",
            "Nuevo nombre:",
            initialvalue=nombre_actual
        )

        if not nuevo_nombre:
            return

        nuevo_nombre = secure_filename(nuevo_nombre)

        if not nuevo_nombre:
            messagebox.showwarning("Nombre inválido", "El nombre ingresado no es válido.")
            return

        destino = os.path.join(carpeta, nuevo_nombre)

        if os.path.exists(destino):
            messagebox.showwarning("Ya existe", "Ya existe un archivo con ese nombre.")
            return

        try:
            os.rename(ruta, destino)
            self.seleccionados.discard(ruta)
            agregar_historial(nuevo_nombre, "PC", "Local", os.path.getsize(destino), "Renombrado")
            self.actualizar_todo()
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo renombrar el archivo:\n{error}")

    def eliminar_archivo(self, ruta):
        try:
            if os.path.exists(ruta):
                tamano = os.path.getsize(ruta)
                nombre = os.path.basename(ruta)
                os.remove(ruta)
                agregar_historial(nombre, "PC", "Local", tamano, "Eliminado")
            self.actualizar_todo()
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo eliminar el archivo:\n{error}")

    def limpiar_carpeta(self, carpeta, nombre):
        confirmar = messagebox.askyesno("Confirmar limpieza", f"¿Deseas eliminar todos los archivos {nombre}?")
        if not confirmar:
            return
        try:
            for archivo in os.listdir(carpeta):
                ruta = os.path.join(carpeta, archivo)
                if os.path.isfile(ruta):
                    os.remove(ruta)
            self.actualizar_todo()
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo limpiar la carpeta:\n{error}")

    def limpiar_todo(self):
        confirmar = messagebox.askyesno("Limpiar todo", "¿Deseas eliminar enviados, recibidos e historial?")
        if not confirmar:
            return
        try:
            for carpeta in [CARPETA_PC_A_IPHONE, CARPETA_IPHONE_A_PC]:
                for archivo in os.listdir(carpeta):
                    ruta = os.path.join(carpeta, archivo)
                    if os.path.isfile(ruta):
                        os.remove(ruta)
            if os.path.exists(HISTORIAL_CSV):
                os.remove(HISTORIAL_CSV)
            textos = os.path.join(CARPETA_HISTORIAL, "textos_iphone.txt")
            if os.path.exists(textos):
                os.remove(textos)
            self.actualizar_todo()
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo limpiar todo:\n{error}")

    def limpiar_historial(self):
        confirmar = messagebox.askyesno("Limpiar historial", "¿Deseas eliminar todo el historial?")
        if not confirmar:
            return
        try:
            if os.path.exists(HISTORIAL_CSV):
                os.remove(HISTORIAL_CSV)
            self.actualizar_historial()
        except Exception as error:
            messagebox.showerror("Error", f"No se pudo limpiar el historial:\n{error}")

    # ---------------- EVENTS / AUTO-REFRESH ----------------

    def revisar_eventos(self):
        eventos_locales = []
        with EVENTOS_LOCK:
            while EVENTOS:
                eventos_locales.append(EVENTOS.pop(0))
        for evento in eventos_locales:
            mensaje = evento["mensaje"]
            ruta = evento.get("ruta")
            if hasattr(self, "info_recibir"):
                self.info_recibir.configure(text=mensaje)
            self.estado_label.configure(text="Actividad detectada", text_color=("#0369A1", "#38BDF8"))
            try:
                self.bell()
            except Exception:
                pass

            if self.toast:
                try:
                    self.toast.show_toast(
                        "Transferencia iPhone ↔ PC",
                        mensaje,
                        duration=5,
                        threaded=True
                    )
                except Exception:
                    pass
            if CONFIG.get("abrir_carpeta_al_recibir") and ruta:
                abrir_ruta(CARPETA_IPHONE_A_PC)
        if eventos_locales:
            self.actualizar_todo()
        self.after(1500, self.revisar_eventos)

    def auto_actualizar(self):
        self.actualizar_todo()
        self.after(4000, self.auto_actualizar)

    def cerrar_app(self):
        try:
            if self.servidor:
                self.servidor.detener()
        except Exception:
            pass

        if self.aplicar_configuracion(generar_codigo=False):
            guardar_configuracion()
            guardar_estado_sesion()

        if CONFIG.get("modo_privado"):
            try:
                for carpeta in [CARPETA_PC_A_IPHONE, CARPETA_IPHONE_A_PC]:
                    for archivo in os.listdir(carpeta):
                        ruta = os.path.join(carpeta, archivo)
                        if os.path.isfile(ruta):
                            os.remove(ruta)
                if os.path.exists(HISTORIAL_CSV):
                    os.remove(HISTORIAL_CSV)
            except Exception as e:
                print("Error en modo privado:", e)

        self.destroy()


# Ejecución principal
if __name__ == "__main__":
    app = AppTransferencia()
    app.mainloop()
