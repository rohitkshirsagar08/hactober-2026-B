
import re
import csv
import io
from datetime import datetime

import streamlit as st
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


# ==================== PAGE CONFIG ====================

st.set_page_config(
    page_title="AgriScan",
    page_icon="🌿",
    layout="wide",
)

# ==================== THEME ====================

st.markdown("""
<style>
.stApp {
    background-color: #111310;
    color: #F1F1E9;
}
[data-testid="stHeader"] {
    background-color: #111310;
}
[data-testid="stSidebar"] {
    background-color: #1B1D18;
}
h1, h2, h3 {
    color: #D0D7A5 !important;
}
p, label, li {
    color: #E6E8DD;
}
.stButton > button {
    background-color: #687747;
    color: white;
    border: 1px solid #879663;
    border-radius: 8px;
}
.stButton > button:hover {
    background-color: #82915C;
    color: white;
}
div[data-testid="stMetric"] {
    background-color: #1B1D18;
    border: 1px solid #424936;
    padding: 16px;
    border-radius: 10px;
}
textarea, input {
    background-color: #20221D !important;
    color: #F1F1E9 !important;
}
</style>
""", unsafe_allow_html=True)


# ==================== HEADER ====================

st.title("🌿 AgriScan")
st.subheader("Smart Pesticide Label Reader")

st.write(
    "Upload a pesticide label to extract its text and identify "
    "important product information using OCR."
)

st.info(
    "Educational tool only. Always verify extracted information "
    "against the original product label."
)


# ==================== HELPER FUNCTIONS ====================

def clean_value(value):
    value = re.sub(r"\s+", " ", value)
    return value.strip(" \t:;,-|")


def find_field(text, patterns):
    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE | re.MULTILINE
        )
        if match:
            value = clean_value(match.group(1))
            if value:
                return value[:200]

    return "Not detected"


# ==================== INFORMATION DETECTION ====================

def detect_information(text):
    text = text.replace("\r", "\n")
    text = text.replace("：", ":")
    text = text.replace("—", "-")

    lines = [
        clean_value(line)
        for line in text.splitlines()
        if clean_value(line)
    ]

    # Product name
    product = find_field(text, [
        r"(?:product\s*name|trade\s*name|brand\s*name)"
        r"\s*[:\-]?\s*([^\n]+)"
    ])

    if product == "Not detected":
        for line in lines[:8]:
            if (
                3 <= len(line) <= 70
                and not re.search(
                    r"warning|caution|ingredient|concentration|"
                    r"manufacturer|manufactured|marketed|dosage|"
                    r"quantity|batch|license|bio pesticide",
                    line,
                    re.IGNORECASE
                )
            ):
                product = line
                break

    # Active ingredient
    ingredient = find_field(text, [
        r"(?:active\s*ingredients?|technical\s*name|"
        r"chemical\s*composition|composition)"
        r"\s*[:\-]?\s*([^\n]+)"
    ])

    # Concentration
    concentration = find_field(text, [
        r"(?:concentration|formulation\s*strength|strength|"
        r"active\s*ingredient\s*content)"
        r"\s*[:\-]\s*([^\n]+)",

        r"(?:active\s*ingredient|composition|contains)"
        r"[^\n]{0,120}?(\d+(?:\.\d+)?\s*%"
        r"(?:\s*(?:w/w|w/v|v/v))?)",

        r"(?:active\s*ingredient|composition|contains)"
        r"[^\n]{0,120}?(\d+(?:\.\d+)?\s*"
        r"(?:g/L|g/kg|mg/L))",
    ])

    if concentration == "Not detected":
        for line in lines:
            if re.search(
                r"\b\d+(?:\.\d+)?\s*%"
                r"(?:\s*(?:w/w|w/v|v/v))?\b|"
                r"\b\d+(?:\.\d+)?\s*(?:g/L|g/kg|mg/L)\b",
                line,
                re.IGNORECASE
            ):
                concentration = line[:200]
                break

    # Manufacturer patterns: common label wording
    manufacturer_patterns = [
        r"manufactured\s*(?:and|&)\s*marketed\s*by"
        r"\s*[:\-]?\s*([^\n]+)",

        r"manufactured\s*by\s*[:\-]?\s*([^\n]+)",

        r"manufacturer(?:s)?\s*[:\-]?\s*([^\n]+)",

        r"marketed\s*by\s*[:\-]?\s*([^\n]+)",

        r"packed\s*(?:and\s*marketed\s*)?by"
        r"\s*[:\-]?\s*([^\n]+)",

        r"distributed\s*by\s*[:\-]?\s*([^\n]+)",

        r"supplied\s*by\s*[:\-]?\s*([^\n]+)",

        r"produced\s*by\s*[:\-]?\s*([^\n]+)",

        r"mfg\.?\s*by\s*[:\-]?\s*([^\n]+)",

        r"mfd\.?\s*by\s*[:\-]?\s*([^\n]+)",
    ]

    manufacturer = find_field(text, manufacturer_patterns)

    # If the manufacturer name appears on the following line
    if manufacturer == "Not detected":
        for i, line in enumerate(lines):
            if re.search(
                r"manufactur|marketed\s*by|distributed\s*by|"
                r"supplied\s*by|packed\s*by|produced\s*by|"
                r"\bmfg\.?|\bmfd\.?",
                line,
                re.IGNORECASE
            ):
                remainder = re.sub(
                    r"(?i)^.*?(?:manufactured\s*"
                    r"(?:(?:and|&)\s*marketed\s*)?by|"
                    r"manufacturer(?:s)?|marketed\s*by|"
                    r"distributed\s*by|supplied\s*by|"
                    r"packed\s*(?:and\s*marketed\s*)?by|"
                    r"produced\s*by|mfg\.?\s*by|mfd\.?\s*by)"
                    r"\s*[:\-]?\s*",
                    "",
                    line
                )

                remainder = clean_value(remainder)

                if len(remainder) >= 3:
                    manufacturer = remainder[:200]

                elif i + 1 < len(lines):
                    next_line = lines[i + 1]

                    if not re.search(
                        r"license|registration|batch|expiry|"
                        r"warning|caution|dosage",
                        next_line,
                        re.IGNORECASE
                    ):
                        manufacturer = next_line[:200]

                break

    # Never guess a manufacturer from unrelated text.
    return {
        "Product Name": product,
        "Active Ingredient": ingredient,
        "Concentration": concentration,
        "Manufacturer": manufacturer,
    }


# ==================== IMAGE PROCESSING ====================

def prepare_image(image, enhance=True):
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")

    if enhance:
        image = ImageOps.grayscale(image)
        image = ImageEnhance.Contrast(image).enhance(2.0)
        image = ImageEnhance.Sharpness(image).enhance(2.0)
        image = image.filter(ImageFilter.SHARPEN)

    return image


# ==================== OCR ====================

def extract_text(image, language, psm, enhance=True):
    processed = prepare_image(image, enhance)
    config = f"--oem 3 --psm {psm}"

    return pytesseract.image_to_string(
        processed,
        lang=language,
        config=config
    )


# ==================== SIDEBAR ====================

with st.sidebar:
    st.header("⚙️ Scan Settings")

    language_choice = st.selectbox(
        "Label language",
        [
            "English",
            "Hindi",
            "Marathi",
            "English + Hindi",
            "English + Marathi",
            "English + Hindi + Marathi",
        ]
    )

    language_map = {
        "English": "eng",
        "Hindi": "hin",
        "Marathi": "mar",
        "English + Hindi": "eng+hin",
        "English + Marathi": "eng+mar",
        "English + Hindi + Marathi": "eng+hin+mar",
    }

    psm = st.selectbox(
        "OCR layout mode",
        [3, 6, 11, 12],
        index=1,
        help="Try another mode if some text is missing."
    )

    enhance = st.checkbox(
        "Enhance image for OCR",
        value=True
    )


# ==================== IMAGE UPLOAD ====================

uploaded_file = st.file_uploader(
    "Upload pesticide label image",
    type=["png", "jpg", "jpeg", "webp"]
)

if uploaded_file:
    try:
        original_image = Image.open(uploaded_file)

        st.subheader("Label Preview")
        st.image(
            original_image,
            caption="Uploaded pesticide label",
            width=500
        )

        if st.button("🔍 Scan Label", type="primary"):
            with st.spinner("Reading pesticide label..."):
                extracted_text = extract_text(
                    original_image,
                    language_map[language_choice],
                    psm,
                    enhance
                )

            if not extracted_text.strip():
                st.warning(
                    "No text detected. Try a clearer image "
                    "or a different OCR layout mode."
                )
            else:
                info = detect_information(extracted_text)

                st.session_state["agriscan_text"] = extracted_text
                st.session_state["agriscan_info"] = info
                st.session_state["agriscan_time"] = (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )

                history = st.session_state.get(
                    "agriscan_history", []
                )

                history.insert(0, {
                    "Time": st.session_state["agriscan_time"],
                    "Product": info["Product Name"],
                    "Manufacturer": info["Manufacturer"],
                })

                st.session_state["agriscan_history"] = history[:10]

    except pytesseract.TesseractNotFoundError:
        st.error(
            "Tesseract OCR was not found. Check that it is installed "
            "and available in your PATH."
        )

    except pytesseract.TesseractError as error:
        st.error(f"OCR error: {error}")

    except Exception as error:
        st.error(f"Could not process the image: {error}")


# ==================== RESULTS ====================

if "agriscan_info" in st.session_state:
    st.divider()
    st.header("📋 Extracted Information")

    info = st.session_state["agriscan_info"]

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Product Name", info["Product Name"])
        st.metric("Active Ingredient", info["Active Ingredient"])

    with col2:
        st.metric("Concentration", info["Concentration"])
        st.metric("Manufacturer", info["Manufacturer"])

    st.subheader("📝 Extracted Text")

    st.text_area(
        "OCR output",
        value=st.session_state["agriscan_text"],
        height=250
    )

    st.caption(
        "If a field is incorrect or missing, compare the OCR output "
        "with the original label."
    )

    # Text report
    report = io.StringIO()
    report.write("AgriScan Report\n")
    report.write(
        f"Scan time: {st.session_state['agriscan_time']}\n\n"
    )

    for key, value in info.items():
        report.write(f"{key}: {value}\n")

    report.write("\nExtracted OCR text:\n")
    report.write(st.session_state["agriscan_text"])

    st.download_button(
        "⬇️ Download Text Report",
        data=report.getvalue(),
        file_name="agriscan_report.txt",
        mime="text/plain"
    )

    # CSV report
    csv_buffer = io.StringIO()
    writer = csv.DictWriter(
        csv_buffer,
        fieldnames=list(info.keys())
    )
    writer.writeheader()
    writer.writerow(info)

    st.download_button(
        "⬇️ Download CSV",
        data=csv_buffer.getvalue(),
        file_name="agriscan_results.csv",
        mime="text/csv"
    )


# ==================== SCAN HISTORY ====================

if st.session_state.get("agriscan_history"):
    st.divider()
    st.subheader("🕘 Recent Scans")

    st.dataframe(
        st.session_state["agriscan_history"],
        use_container_width=True,
        hide_index=True
    )

    st.caption("Scan history is stored only for the current session.")


# ==================== FOOTER ====================

st.divider()

st.caption(
    "AgriScan is an educational project. OCR can make mistakes. "
    "Verify the product identity, concentration, dosage, and safety "
    "instructions against the original label and trusted agricultural guidance."
)
