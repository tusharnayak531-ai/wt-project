# FashionAI — Fashion Recommendations
Working mini-project: search 24 fashion demo products by natural-language product descriptions or uploaded clothing photo. Ranking uses weighted word-vector cosine similarity and dominant colour comparison. This free deployment uses a lightweight, offline retrieval baseline; it is NOT a pretrained neural network/CLIP embedding search. Synthetic SVG garment illustrations are generated dynamically. For production, replace demo data with real product images and add a trained vision/text embedding model.

## Run
pip install -r requirements.txt
python app.py
Open http://127.0.0.1:5000.
Health check: GET /api/health.

## Render Free
Root repository: tusharnayak531-ai/wt-project
Branch: fashionai-recommendation-2026
Build: cd FashionAI && pip install -r requirements.txt
Start: cd FashionAI && gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120
