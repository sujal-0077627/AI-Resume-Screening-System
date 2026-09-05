"""Document text extraction supporting PDF (pdfplumber + OCR), DOCX (python-docx + zip xml fallback), and TXT."""
import os
import zipfile
import xml.etree.ElementTree as ET
import pdfplumber


def _configure_tesseract():
    """
    Configure pytesseract to find the Tesseract binary on Windows.
    Tesseract is usually installed at C:\\Program Files\\Tesseract-OCR\\tesseract.exe
    """
    try:
        import pytesseract
        # Common Windows install locations
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break
        # Ensure tessdata directory exists (eng.traineddata)
        # If the default tessdata is missing language files, point to user-level tessdata
        default_tessdata = os.path.join(os.path.dirname(pytesseract.pytesseract.tesseract_cmd), "tessdata")
        # Try USERPROFILE env var first (more reliable on some Windows setups)
        user_home = os.environ.get('USERPROFILE') or os.path.expanduser('~')
        user_tessdata = os.path.join(user_home, "tessdata")
        if not os.path.exists(os.path.join(default_tessdata, "eng.traineddata")) and os.path.exists(os.path.join(user_tessdata, "eng.traineddata")):
            os.environ["TESSDATA_PREFIX"] = user_tessdata
        return pytesseract
    except ImportError:
        return None


def _extract_text_with_ocr(pdf_path):
    """
    Extract text from image-based/scanned PDFs using OCR (Tesseract).
    Falls back gracefully if OCR is not available.

    Uses pypdfium2 for PDF-to-image rendering (pure Python, no Poppler needed).

    Args:
        pdf_path (str): Path to the PDF file.

    Returns:
        str: Extracted text from all pages via OCR.
    """
    try:
        pytesseract = _configure_tesseract()
        if pytesseract is None:
            return None
        import pypdfium2 as pdfium
        from PIL import Image
    except ImportError:
        # OCR dependencies not installed - try pdfplumber only
        return None

    try:
        text = ""
        # Open PDF with pypdfium2 (pure Python, no external binary needed)
        pdf = pdfium.PdfDocument(pdf_path)
        for page in pdf:
            # Render page to a bitmap at 200 DPI for good OCR quality
            bitmap = page.render(scale=200 / 72)
            pil_image = bitmap.to_pil()
            page_text = pytesseract.image_to_string(pil_image)
            if page_text:
                text += page_text + "\n"
        pdf.close()
        return text.strip() if text.strip() else None
    except Exception:
        # Tesseract binary not found or other OCR errors - return None
        # so caller can fall back to pdfplumber or raise a helpful error
        return None


def extract_text_from_pdf(pdf_path):
    """
    Extract all text from a PDF file using pdfplumber.

    If the PDF is image-based (scanned), automatically falls back
    to OCR using Tesseract.

    Args:
        pdf_path (str): Path to the PDF file.

    Returns:
        str: Extracted text from all pages.

    Raises:
        ValueError: If no text can be extracted from the PDF.
    """
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {e}")

    # If pdfplumber found no text, the PDF may be image-based/scanned
    if not text.strip():
        # Try OCR as fallback
        ocr_text = _extract_text_with_ocr(pdf_path)
        if ocr_text:
            return ocr_text.strip()
        raise ValueError(
            "No text could be extracted from the PDF. "
            "The file may be scanned/image-based and OCR is not available. "
            "Please install Tesseract OCR and pdf2image for image-based PDF support."
        )

    return text.strip()


def extract_text_from_docx(docx_path):
    """
    Extract text from a Word document (.docx).
    Uses python-docx if available, otherwise falls back to pure Python zip XML extraction.
    """
    # Attempt 1: python-docx
    try:
        import docx
        doc = docx.Document(docx_path)
        full_text = []
        for para in doc.paragraphs:
            if para.text:
                full_text.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    full_text.append(" | ".join(row_text))
        if full_text:
            return "\n".join(full_text).strip()
    except Exception:
        pass

    # Attempt 2: Pure-Python zipfile extraction of word/document.xml
    try:
        with zipfile.ZipFile(docx_path) as z:
            xml_content = z.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            # Namespace for Word XML
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            paragraphs = []
            for p in tree.iterfind('.//w:p', ns):
                texts = [node.text for node in p.iterfind('.//w:t', ns) if node.text]
                if texts:
                    paragraphs.append(''.join(texts))
            if paragraphs:
                return "\n".join(paragraphs).strip()
    except Exception as e:
        raise ValueError(f"Failed to extract text from DOCX file: {e}")

    raise ValueError("No text could be extracted from the Word (.docx) document.")


def extract_text_from_txt(txt_path):
    """Extract text from plain text file (.txt)."""
    encodings = ['utf-8', 'latin-1', 'cp1252']
    for enc in encodings:
        try:
            with open(txt_path, 'r', encoding=enc) as f:
                text = f.read()
                if text.strip():
                    return text.strip()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            raise ValueError(f"Failed to read text file: {e}")
    raise ValueError("Could not decode text file with standard encodings.")


def extract_text_from_document(file_path):
    """
    Auto-detect file type (.pdf, .docx, .txt) and extract text.
    """
    lower = file_path.lower()
    if lower.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif lower.endswith('.docx') or lower.endswith('.doc'):
        return extract_text_from_docx(file_path)
    elif lower.endswith('.txt') or lower.endswith('.rtf'):
        return extract_text_from_txt(file_path)
    else:
        # Default try PDF first, fallback to text
        try:
            return extract_text_from_pdf(file_path)
        except Exception:
            return extract_text_from_txt(file_path)