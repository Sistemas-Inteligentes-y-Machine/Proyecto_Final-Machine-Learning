import tkinter as tk
from tkinter import scrolledtext
import cv2
import pyttsx3
import easyocr
import numpy as np
import re
import threading
from PIL import Image, ImageTk
import speech_recognition as sr
import os
import platform
import subprocess
from datetime import datetime
from reportlab.pdfgen import canvas

# ========== CREAR CARPETA EXPORTADOS ==========
EXPORT_FOLDER = "exportados"
if not os.path.exists(EXPORT_FOLDER):
    os.makedirs(EXPORT_FOLDER)

# ======== VARIABLE GLOBAL PARA GUARDAR EL ÚLTIMO TEXTO LEÍDO ========
ultimo_texto_leido = ""

# === Configuración OCR ===
try:
    reader = easyocr.Reader(['es'], gpu=True)
except:
    reader = easyocr.Reader(['es'], gpu=False)

# === Configuración de cámara ===
USE_PHONE_CAMERA = False
PHONE_CAMERA_URL = "http://10.252.1.205:8080/video"
ALLOWLIST = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZáéíóúÁÉÍÓÚüÜñÑ0123456789.,:;!?¡¿()[]{}-_/\\&%$#@+*=<> "

cap = cv2.VideoCapture(PHONE_CAMERA_URL if USE_PHONE_CAMERA else 0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)


# ====== FUNCIONES PARA EXPORTAR ======

def save_text_to_txt(text):
    try:
        if not text.strip():
            output_box.insert(tk.END, "⚠️ No hay texto leído para guardar.\n")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{EXPORT_FOLDER}/ocr_{timestamp}.txt"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(text)

        output_box.insert(tk.END, f"💾 TXT guardado en: {filename}\n")

    except Exception as e:
        output_box.insert(tk.END, f"❌ Error al guardar TXT: {e}\n")


def save_text_to_pdf(text):
    try:
        if not text.strip():
            output_box.insert(tk.END, "⚠️ No hay texto leído para guardar.\n")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{EXPORT_FOLDER}/ocr_{timestamp}.pdf"

        c = canvas.Canvas(filename)
        c.setFont("Helvetica", 12)

        y = 800
        for line in text.split("\n"):
            c.drawString(30, y, line)
            y -= 20
            if y < 40:
                c.showPage()
                c.setFont("Helvetica", 12)
                y = 800

        c.save()
        output_box.insert(tk.END, f"📄 PDF guardado en: {filename}\n")

    except Exception as e:
        output_box.insert(tk.END, f"❌ Error al guardar PDF: {e}\n")


def open_export_folder():
    try:
        if platform.system() == "Windows":
            os.startfile(EXPORT_FOLDER)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", EXPORT_FOLDER])
        else:
            subprocess.Popen(["xdg-open", EXPORT_FOLDER])
    except Exception as e:
        output_box.insert(tk.END, f"❌ Error al abrir carpeta: {e}\n")


# ====== FUNCIONES DE PROCESAMIENTO ======

def resize_for_ocr(img, target_w=600):
    h, w = img.shape[:2]
    if w >= target_w:
        return img
    scale = target_w / float(w)
    return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)


def clean_text(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9áéíóúÁÉÍÓÚüÜñÑ\.,:;!¡?¿()\[\]{}\-_/&%$#@+*=<>\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def postprocess_text(text):
    replacements = {'0': 'O', '1': 'I', '2': 'Z', '3': 'E', '4': 'A', '5': 'S', '6': 'G', '7': 'T', '8': 'B', '9': 'g',
                    '|': 'I', '@': 'a'}
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)
    return re.sub(r'\s+', ' ', text).strip()


# ====== CÁMARA ======

def update_camera():
    ret, frame = cap.read()
    if ret:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(image=img)
        camera_label.imgtk = imgtk
        camera_label.configure(image=imgtk)
    ventana.after(80, update_camera)


def capture_and_process():
    global ultimo_texto_leido

    ret, frame = cap.read()
    if not ret:
        output_box.insert(tk.END, "❌ No hay frame disponible.\n")
        return

    resized = resize_for_ocr(frame, 600)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    results = reader.readtext(cv2.cvtColor(th, cv2.COLOR_GRAY2BGR), allowlist=ALLOWLIST)
    textos = [text for _, text, conf in results if conf >= 0.2]

    raw_text = " ".join(textos)
    texto_final = clean_text(postprocess_text(raw_text))

    if texto_final:
        ultimo_texto_leido = texto_final  # GUARDAR TEXTO LEÍDO
        output_box.insert(tk.END, f"✅ Texto detectado: {texto_final}\n")
    else:
        output_box.insert(tk.END, "⚠️ No se detectó texto legible.\n")

    # Reproducir voz
    try:
        if texto_final:
            engine = pyttsx3.init()
            engine.setProperty('rate', 160)
            engine.say(texto_final)
            engine.runAndWait()
            engine.stop()
    except Exception as e:
        output_box.insert(tk.END, f"⚠️ Error TTS: {e}\n")


def capture_and_process_async():
    threading.Thread(target=capture_and_process, daemon=True).start()


# ====== ASISTENTE DE VOZ MEJORADO ======

def voice_listener_sr():
    output_box.insert(tk.END,
                      "🎤 Asistente de voz mejorado. Di 'asistente capturar', 'asistente guardar pdf', 'asistente guardar txt' o 'asistente salir'.\n")

    r = sr.Recognizer()
    mic = sr.Microphone()

    # Ajuste inicial de ruido
    with mic as source:
        r.dynamic_energy_threshold = True
        r.energy_threshold = 3000
        r.adjust_for_ambient_noise(source, duration=2)

    while True:
        with mic as source:
            try:
                audio = r.listen(source, phrase_time_limit=4)
            except:
                continue

        try:
            command = r.recognize_google(audio, language="es-ES").lower()
            output_box.insert(tk.END, f"🎙️ Detectado: {command}\n")

            # VALIDACIÓN: Debe empezar con "asistente"
            if not command.startswith("asistente"):
                output_box.insert(tk.END, "⚠️ Ignorado: no se detectó la palabra clave 'asistente'.\n")
                continue

            # Limpiar la hotword
            command = command.replace("asistente", "").strip()

            # FILTRO DE COMANDOS
            if "capturar" in command:
                output_box.insert(tk.END, "🔧 Ejecutando: CAPTURAR\n")
                capture_and_process_async()

            elif "guardar pdf" in command:
                output_box.insert(tk.END, "🔧 Ejecutando: GUARDAR PDF\n")
                save_text_to_pdf(ultimo_texto_leido)

            elif "guardar txt" in command:
                output_box.insert(tk.END, "🔧 Ejecutando: GUARDAR TXT\n")
                save_text_to_txt(ultimo_texto_leido)

            elif "salir" in command or "cerrar" in command:
                output_box.insert(tk.END, "👋 Cerrando aplicación...\n")
                ventana.quit()
                break

            else:
                output_box.insert(tk.END, "⚠️ Ignorado: Comando no reconocido.\n")

        except sr.UnknownValueError:
            output_box.insert(tk.END, "🔇 No se entendió el audio (ruido o silencio).\n")
            continue

        except sr.RequestError as e:
            output_box.insert(tk.END, f"⚠️ Error de voz: {e}\n")


# ====== INTERFAZ TKINTER ======

ventana = tk.Tk()
ventana.title("OCR con EasyOCR + Cámara + Asistente de Voz")
ventana.geometry("1100x780")
ventana.configure(bg="#1e1e1e")

frame_camera = tk.Frame(ventana, bg="#1e1e1e")
frame_camera.pack(pady=5)
camera_label = tk.Label(frame_camera, bg="black", width=480, height=320)
camera_label.pack()

frame_output = tk.Frame(ventana, bg="#1e1e1e")
frame_output.pack(pady=10, fill="both", expand=True)
output_box = scrolledtext.ScrolledText(frame_output, font=("Consolas", 12), width=120, height=20, bg="#252526",
                                       fg="#D4D4D4", insertbackground="white")
output_box.pack(pady=10, fill="both", expand=True)

# ====== BOTONES ======
frame_buttons = tk.Frame(ventana, bg="#1e1e1e")
frame_buttons.pack(pady=5)

tk.Button(frame_buttons, text="Guardar TXT", command=lambda: save_text_to_txt(ultimo_texto_leido), bg="#007ACC",
          fg="white", width=15).grid(row=0, column=0, padx=5)
tk.Button(frame_buttons, text="Guardar PDF", command=lambda: save_text_to_pdf(ultimo_texto_leido), bg="#28A745",
          fg="white", width=15).grid(row=0, column=1, padx=5)
tk.Button(frame_buttons, text="Abrir Carpeta", command=open_export_folder, bg="#FF9800", fg="white", width=15).grid(
    row=0, column=2, padx=5)

update_camera()
threading.Thread(target=voice_listener_sr, daemon=True).start()

ventana.mainloop()
cap.release()




