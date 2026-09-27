# Read-only hosted demo of MPLADS-GUARD (Hugging Face Docker Space, free CPU tier).
# The data, analysis code and built interface arrive at startup as one verified
# bundle (see deploy/pack_release.py), so this image only needs Python and the
# two libraries the server imports.
FROM python:3.12-slim

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR /home/user/app
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt
COPY --chown=user start.py .

EXPOSE 7860
CMD ["python", "start.py"]
