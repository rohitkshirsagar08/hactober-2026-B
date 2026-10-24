
import streamlit as st
import pytesseract
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

st.set_page_config(
    page_title="Pesticide Label Reader",
    page_icon="🌱",
    layout="wide"
)

TEXT = {
    "हिन्दी": {
        "title": "🌱 कीटनाशक लेबल रीडर",
        "subtitle": "किसानों के लिए आसान जानकारी",
        "description": "लेबल की साफ़ फोटो अपलोड करें।",
        "upload": "लेबल की फोटो अपलोड करें",
        "read": "टेक्स्ट पढ़ें",
        "result": "पहचाना गया टेक्स्ट",
        "empty": "टेक्स्ट नहीं मिला। दूसरी फोटो आज़माएँ।",
        "safety": "सुरक्षा: खुराक और प्रतीक्षा अवधि की पुष्टि मूल लेबल से करें। OCR की गलतियों के आधार पर कीटनाशक का उपयोग न करें।",
        "mode": "टेक्स्ट पढ़ने का तरीका",
        "mode1": "सामान्य टेक्स्ट",
        "mode2": "अलग-अलग टेक्स्ट क्षेत्र",
        "image": "मूल लेबल",
        "error": "त्रुटि:"
    },
    "मराठी": {
        "title": "🌱 कीटकनाशक लेबल वाचक",
        "subtitle": "शेतकऱ्यांसाठी सोपी माहिती",
        "description": "लेबलचा स्पष्ट फोटो अपलोड करा.",
        "upload": "लेबलचा फोटो अपलोड करा",
        "read": "मजकूर वाचा",
        "result": "ओळखलेला मजकूर",
        "empty": "मजकूर सापडला नाही. दुसरा फोटो वापरून पाहा.",
        "safety": "सुरक्षितता: डोस आणि प्रतीक्षा कालावधी मूळ लेबलवरून तपासा. OCR मधील चुकांवरून कीटकनाशक वापरू नका.",
        "mode": "मजकूर वाचण्याची पद्धत",
        "mode1": "सामान्य मजकूर",
        "mode2": "वेगवेगळे मजकूर भाग",
        "image": "मूळ लेबल",
        "error": "त्रुटी:"
    },
    "English": {
        "title": "🌱 Pesticide Label Reader",
        "subtitle": "Simple information for farmers",
        "description": "Upload a clear photo of a pesticide label.",
        "upload": "Upload label photo",
        "read": "Read text",
        "result": "Recognized text",
        "empty": "No text found. Try another photo.",
        "safety": "Safety: Verify dosage and waiting periods on the original label. Never use a pesticide based on potentially incorrect OCR.",
        "mode": "Text reading mode",
        "mode1": "Normal text",
        "mode2": "Separate text regions",
        "image": "Original label",
        "error": "Error:"
    }
}

language = st.selectbox(
    "🌐 भाषा / Language",
    ["हिन्दी", "मराठी", "English"]
)

t = TEXT[language]

ocr_language = {
    "हिन्दी": "hin",
    "मराठी": "mar",
    "English": "eng"
}[language]

st.title(t["title"])
st.subheader(t["subtitle"])
st.write(t["description"])

uploaded_file = st.file_uploader(
    t["upload"],
    type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    try:
        image = Image.open(uploaded_file).convert("RGB")

        left, right = st.columns(2)

        with left:
            st.image(image, caption=t["image"], use_container_width=True)

        with right:
            mode = st.radio(
                t["mode"],
                [t["mode1"], t["mode2"]]
            )

            if st.button(t["read"]):
                processed = ImageOps.grayscale(image)
                processed = ImageOps.autocontrast(processed)
                processed = ImageEnhance.Contrast(processed).enhance(1.5)

                # Enlarge small print
                processed = processed.resize(
                    (processed.width * 2, processed.height * 2)
                )
                processed = processed.filter(ImageFilter.SHARPEN)

                psm = "6" if mode == t["mode1"] else "11"

                with st.spinner("Reading text..."):
                    result = pytesseract.image_to_string(
                        processed,
                        lang=ocr_language,
                        config=f"--psm {psm}"
                    )

                if result.strip():
                    st.session_state["ocr_result"] = result
                else:
                    st.warning(t["empty"])

        if st.session_state.get("ocr_result"):
            st.subheader(t["result"])
            st.text_area(
                t["result"],
                st.session_state["ocr_result"],
                height=350
            )

    except Exception as error:
        st.error(f'{t["error"]} {error}')

st.warning("⚠️ " + t["safety"])
