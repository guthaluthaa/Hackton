import logging

from minio import Minio

from app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._bucket = settings.minio_bucket

    def download_file(self, file_path: str) -> tuple[bytes, str]:
        """
        Baixa arquivo do MinIO.
        Retorna (bytes, content_type).
        O Upload Service salva o path como "{bucket}/{guid}/{file}", então
        removemos o prefixo do bucket antes de chamar get_object.
        """
        object_name = file_path
        prefix = f"{self._bucket}/"
        if object_name.startswith(prefix):
            object_name = object_name[len(prefix):]

        try:
            response = self._client.get_object(self._bucket, object_name)
            data = response.read()
            content_type = response.headers.get("Content-Type", "application/octet-stream")
            response.close()
            response.release_conn()
            logger.info(f"Arquivo baixado: {file_path} ({len(data)} bytes, {content_type})")
            return data, content_type
        except Exception as e:
            logger.error(f"Falha ao baixar arquivo {file_path}: {e}")
            raise
