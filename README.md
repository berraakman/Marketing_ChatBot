If PDFs are updated:
rm -rf backend/data/chroma

uvicorn backend.app:app --reload
open fronted/index.html
