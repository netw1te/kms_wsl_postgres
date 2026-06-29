from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
import whisper
from app.auth import CurrentUser, get_current_user
import os
import sys
import shutil
import imageio_ffmpeg

try:
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)

    canonical_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    canonical_path = os.path.join(ffmpeg_dir, canonical_name)

    if not os.path.exists(canonical_path):
        shutil.copy2(ffmpeg_exe, canonical_path)

    if ffmpeg_dir not in os.environ["PATH"]:
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]
except Exception as e:
    sys.stderr.write(f"Ошибка инициализации локального бинарника ffmpeg: {str(e)}\n")

router = APIRouter(prefix="/audio", tags=["Аудиозаметки"])

_model = None


def get_whisper_model():
    global _model
    if _model is None:
        _model = whisper.load_model("base", device="cpu")
    return _model


@router.post("/transcribe")
async def transcribe_audio(
        file: UploadFile = File(...),
        current_user: CurrentUser = Depends(get_current_user)
):
    if not file.filename.endswith(('.mp3', '.wav', '.m4a', '.webm', '.ogg')):
        raise HTTPException(status_code=400, detail="Неподдерживаемый формат аудиофайла")

    temp_filename = f"temp_{current_user.id}_{file.filename}"
    with open(temp_filename, "wb") as f:
        f.write(await file.read())

    try:
        model = get_whisper_model()
        result = model.transcribe(temp_filename, language="ru", fp16=False)
        transcription_text = result.get("text", "").strip()
        return {"text": transcription_text}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка транскрибации: {str(e)}")
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)