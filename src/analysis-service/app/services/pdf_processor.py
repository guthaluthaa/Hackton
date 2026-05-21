import base64
import logging
from typing import List

logger = logging.getLogger(__name__)

MAX_PAGES = 3
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB por página


def pdf_to_images(pdf_bytes: bytes) -> List[str]:
    """
    Converte páginas de um PDF em imagens PNG codificadas em base64.
    Limita a MAX_PAGES páginas para controle de custo e latência.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images: List[str] = []

    page_count = min(doc.page_count, MAX_PAGES)
    logger.info(f"Convertendo {page_count}/{doc.page_count} páginas do PDF")

    for page_num in range(page_count):
        page = doc[page_num]

        # 150 DPI — boa qualidade sem peso excessivo
        mat = fitz.Matrix(150 / 72, 150 / 72)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")

        # Reduz resolução se ainda muito grande
        if len(img_bytes) > MAX_IMAGE_BYTES:
            mat = fitz.Matrix(100 / 72, 100 / 72)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")

        images.append(base64.standard_b64encode(img_bytes).decode("utf-8"))
        logger.info(f"Página {page_num + 1} convertida ({len(img_bytes):,} bytes)")

    doc.close()
    return images


def image_to_base64(image_bytes: bytes) -> str:
    """Converte bytes de imagem para string base64."""
    return base64.standard_b64encode(image_bytes).decode("utf-8")
