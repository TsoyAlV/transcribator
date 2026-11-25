from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import logging
import threading
import time

import streamlit as st

from transcribe import timestamp, transcribe_file, validate_upload

st.set_page_config(page_title="Транскрибатор", page_icon="🎙️", layout="centered")
st.markdown("""<style>
.stApp { background: #f7f8fc; }
.block-container { max-width: 850px; padding-top: 3.2rem; }
h1 { letter-spacing: -0.05em; }
[data-testid="stFileUploader"] { background: white; border-radius: 16px; padding: 14px; }
.stButton > button { border-radius: 10px; min-height: 46px; }
</style>""", unsafe_allow_html=True)


@st.cache_resource(max_entries=1, show_spinner=False)
def load_model(name: str):
    from faster_whisper import WhisperModel
    return WhisperModel(name, device="cpu", compute_type="int8"), threading.Lock()


st.caption("АУДИО И ВИДЕО → ТЕКСТ")
st.title("Транскрибатор")
st.write("Загрузите запись — получите текст, который можно отредактировать и скачать.")
st.caption("Локальное распознавание • без API-ключей • до 500 МБ")

upload = st.file_uploader("Перетащите файл сюда или выберите на компьютере", type=["m4a", "mp4", "mp3"])
left, right = st.columns(2)
language_label = left.selectbox("Язык записи", ["Автоопределение", "Русский", "English", "한국어", "中文", "日本語"])
language = {"Автоопределение": None, "Русский": "ru", "English": "en", "한국어": "ko", "中文": "zh", "日本語": "ja"}[language_label]
model_label = right.selectbox("Качество распознавания", ["Баланс · small", "Быстро · base", "Точнее · medium", "Максимум · large-v3"])
model_name = model_label.split(" · ")[1]
st.caption("Первый запуск скачает выбранную модель. Большие модели требуют больше памяти и времени; распознавание работает на CPU.")

identity = None
if upload is not None:
    try:
        suffix = validate_upload(upload.name, upload.size)
    except ValueError as error:
        st.error(str(error))
        st.stop()
    identity = (sha256(upload.getbuffer()).hexdigest(), language, model_name)
    st.caption(f"{upload.name} · {upload.size / (1024 * 1024):.1f} МБ")

# Changing the recording or recognition settings invalidates the old transcript.
if st.session_state.get("identity") != identity:
    for key in ("result", "editor", "editor_mode", "elapsed"):
        st.session_state.pop(key, None)
    st.session_state.identity = identity

if st.button("Распознать запись", type="primary", disabled=upload is None, use_container_width=True):
    for key in ("result", "editor", "editor_mode", "elapsed"):
        st.session_state.pop(key, None)
    start = time.perf_counter()
    try:
        with st.spinner("Подготовка модели. При первом запуске потребуется интернет…"):
            model, lock = load_model(model_name)
        bar = st.progress(0.0, text="Подготовка аудиодорожки…")
        with TemporaryDirectory(prefix="transcriber-") as directory:
            # Never use a user-controlled filename as a filesystem path.
            path = Path(directory) / f"recording{suffix}"
            with path.open("wb") as output:
                output.write(upload.getbuffer())
            with st.spinner("Распознавание речи…"):
                with lock:
                    result = transcribe_file(model, path, language, lambda p: bar.progress(p, text="Распознавание записи…"))
        bar.empty()
        st.session_state.result = result
        st.session_state.elapsed = time.perf_counter() - start
    except Exception as error:
        logging.exception("Transcription failed")
        st.error("Не удалось обработать запись. Проверьте, что в файле есть исправная аудиодорожка. Если модель ещё не скачана, проверьте интернет и повторите запуск.")
        with st.expander("Подробности ошибки"):
            st.code(f"{type(error).__name__}: {error}")

result = st.session_state.get("result")
if result is not None:
    if not result.text:
        st.warning("Речь не обнаружена. Проверьте запись или выберите язык вручную.")
    else:
        st.success("Готово! Текст можно исправить перед скачиванием.")
        st.caption(f"Язык: {result.language} · Длительность: {timestamp(result.duration)} · Обработка: {st.session_state.elapsed:.0f} с")
        timed = st.checkbox("Добавить временные метки", help="При переключении восстановится исходный текст выбранного вида; ручные правки будут сброшены.")
        if st.session_state.get("editor_mode") != timed:
            st.session_state.editor = result.timed_text if timed else result.text
            st.session_state.editor_mode = timed
        edited = st.text_area("Текст записи", key="editor", height=340)
        st.download_button(
            "Скачать TXT", data=edited.encode("utf-8-sig"),
            file_name=f"{Path(upload.name).stem}.txt", mime="text/plain; charset=utf-8",
            type="primary", use_container_width=True,
        )

st.divider()
st.caption("Записи обрабатываются на этом компьютере. Временная копия удаляется после обработки; результат хранится в текущей сессии.")
