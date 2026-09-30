import pytest

from services.document_text_extractor import UnsupportedForExtraction, extract_text


def test_txt_extracted_directly():
    text = "Rack B mein cable tray ka kaam mostly complete ho gaya hai."
    assert extract_text("field-update.txt", text.encode("utf-8")) == text


def test_empty_txt_rejected_cleanly():
    with pytest.raises(UnsupportedForExtraction):
        extract_text("empty.txt", b"")


def test_unsupported_file_type_fails_cleanly_not_silently():
    with pytest.raises(UnsupportedForExtraction, match="isn't supported yet"):
        extract_text("report.docx", b"some bytes that are not read")


def test_image_type_fails_cleanly_no_ocr():
    with pytest.raises(UnsupportedForExtraction):
        extract_text("site-photo.jpg", b"\xff\xd8\xff\xe0fakejpegbytes")