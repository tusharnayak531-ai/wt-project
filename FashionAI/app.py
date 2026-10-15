"""FashionAI demo: text and product-image retrieval on a small fashion catalogue."""
import csv
import io
import math
import os
import re
import statistics
from collections import Counter
from pathlib import Path
from flask import Flask, request, jsonify, render_template, Response
from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
COLORS = {"black": (35, 38, 45), "white": (234, 234, 231), "red": (202, 66, 74), "blue": (65, 112, 180), "green": (76, 146, 109), "yellow": (222, 183, 69), "pink": (213, 133, 161), "brown": (139, 94, 69), "gray": (132, 136, 142), "navy": (50, 63, 104), "beige": (205, 187, 156)}
STOP = set("a an for the and or to with of in on your my find show me nice good casual outfit clothing style fashion wear comfortable fashionable".split())
with (ROOT / "data" / "products.csv").open(encoding="utf-8", newline="") as stream:
    PRODUCTS = list(csv.DictReader(stream))
for p in PRODUCTS:
    p["image"] = "/item/%s.svg" % p["id"]

def words(text):
    text = text.lower().replace("t-shirt", "tshirt").replace("t shirt", "tshirt")
    text = text.replace("tee", "tshirt").replace("pants", "trousers").replace("grey", "gray")
    return [w for w in re.findall(r"[a-z]+", text) if len(w) > 1 and w not in STOP]

DOCUMENTS = [Counter(words(" ".join(p.get(k,"") for k in ("name","category","description","color","gender","style")))) for p in PRODUCTS]
DOC_FREQUENCY = Counter()
for doc in DOCUMENTS:
    DOC_FREQUENCY.update(doc.keys())
N = len(PRODUCTS)
IDF = {word: math.log(1 + (N+1)/(freq+1)) for word,freq in DOC_FREQUENCY.items()}
def vector(doc):
    return {word: (1 + math.log(count)) * IDF.get(word, 1) for word,count in doc.items()}
DOCUMENT_VECTORS = [vector(doc) for doc in DOCUMENTS]
def cosine(a,b):
    norm_a = math.sqrt(sum(x*x for x in a.values()))
    norm_b = math.sqrt(sum(x*x for x in b.values()))
    return sum(value*b.get(word,0) for word,value in a.items())/max(norm_a*norm_b,1e-9)

def dominant_color(img):
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((96,96))
    pixels = list(img.getdata())
    # Ignore near-white photograph backgrounds so garment colour has priority.
    candidates = [px for px in pixels if (sum(px)/3 < 240 and (max(px)-min(px)>22 or sum(px)/3<170))]
    pixels = candidates if len(candidates)>50 else pixels
    if not pixels:
        return (128,128,128)
    return tuple(statistics.median(px[i] for px in pixels) for i in range(3))
def image_score(rgb, target):
    return max(0, 1 - math.sqrt(sum((a-b)**2 for a,b in zip(rgb,target)))/340)

def recommend(text="", image=None, count=8):
    qwords = words(text)
    qvec = vector(Counter(qwords))
    mentioned_colors = [name for name in COLORS if name in qwords]
    has_image = image is not None
    photo_rgb = dominant_color(image) if has_image else None
    results=[]
    for idx,p in enumerate(PRODUCTS):
        color_rgb = COLORS[p["color"]]
        text_score = cosine(qvec, DOCUMENT_VECTORS[idx]) if qwords else 0
        if mentioned_colors:
            text_score += (0.20 if p["color"] == mentioned_colors[0] else 0)
        photo_score = image_score(photo_rgb,color_rgb) if has_image else 0
        if qwords and has_image:
            score = 0.66*text_score + 0.34*photo_score
        elif qwords:
            score = text_score
        else:
            score = photo_score
        results.append({**p, "score": round(float(score),3)})
    return sorted(results, key=lambda p:(-p["score"],int(p["id"])))[:count]

PATHS = {
"t-shirt":"M80 55 L116 35 L140 52 L164 35 L200 55 L232 97 L199 117 L182 98 L182 270 L98 270 L98 98 L81 117 L48 97 Z",
"polo":"M80 55 L116 35 L140 52 L164 35 L200 55 L232 97 L199 117 L182 98 L182 270 L98 270 L98 98 L81 117 L48 97 Z",
"shirt":"M84 48 L118 35 L140 55 L162 35 L199 48 L228 99 L196 116 L182 91 L182 270 L98 270 L98 91 L84 116 L52 99 Z",
"dress":"M112 42 L140 57 L168 42 L192 71 L178 123 L220 274 L60 274 L102 123 L88 71 Z",
"hoodie":"M94 47 Q140 -10 186 47 L206 53 L232 96 L196 120 L183 99 L183 275 L97 275 L97 99 L84 120 L48 96 L74 53 Z",
"jeans":"M91 43 L189 43 L195 268 L152 268 L140 142 L128 268 L85 268 Z",
"trousers":"M91 43 L189 43 L196 270 L154 270 L140 141 L126 270 L84 270 Z",
"joggers":"M93 43 L187 43 L194 265 L155 265 L140 150 L125 265 L86 265 Z",
"jacket":"M91 52 L117 34 L140 55 L164 34 L190 52 L227 102 L200 119 L182 96 L182 270 L98 270 L98 96 L80 119 L53 102 Z",
"sweater":"M85 59 L116 41 L140 53 L164 41 L195 59 L230 101 L200 120 L182 96 L182 268 L98 268 L98 96 L80 120 L50 101 Z",
}
def picture_svg(p):
    category = p["category"]
    rgb = COLORS[p["color"]]
    primary = "rgb(%d,%d,%d)" % rgb
    path = PATHS.get(category,PATHS["t-shirt"])
    detail = '<path d="M140 54 L140 268" stroke="#ffffff" stroke-opacity=".27" stroke-width="3"/>' if category in ("shirt","jacket") else ""
    detail += '<rect x="111" y="110" width="58" height="23" rx="10" fill="#ffffff" fill-opacity=".11"/>' if category=="hoodie" else ""
    detail += '<path d="M108 48 L140 82 L172 48" stroke="#fff" stroke-opacity=".5" fill="none" stroke-width="3"/>' if category=="polo" else ""
    detail += '<path d="M140 142 L140 255" stroke="#ffffff" stroke-opacity=".20" stroke-width="3"/>' if category in ("jeans","trousers","joggers") else ""
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="300" height="340" viewBox="0 0 280 320">'
            '<rect width="280" height="320" fill="#f3f0eb"/><circle cx="220" cy="65" r="92" fill="#ece5dc" opacity=".55"/>'
            '<ellipse cx="140" cy="289" rx="80" ry="12" fill="#000" opacity=".07"/>'
            '<path d="%s" fill="%s" stroke="#171923" stroke-opacity=".13" stroke-width="3" stroke-linejoin="round"/>%s'
            '</svg>') % (path,primary,detail)

@app.get("/")
def index():
    return render_template("index.html", count=len(PRODUCTS))
@app.get("/api/health")
def health():
    return jsonify(status="ok",catalogue_size=len(PRODUCTS),mode="text vectors + colour-based image retrieval")
@app.get("/api/products")
def catalogue():
    return jsonify(PRODUCTS)
@app.get("/item/<int:item_id>.svg")
def product_image(item_id):
    if item_id < 1 or item_id > len(PRODUCTS):
        return Response(status=404)
    return Response(picture_svg(PRODUCTS[item_id-1]), mimetype="image/svg+xml", headers={"Cache-Control":"public, max-age=86400"})
@app.post("/api/recommend")
def recommendations():
    text = request.form.get("description","").strip()
    incoming = request.files.get("image")
    photo = None
    if incoming and incoming.filename:
        if incoming.mimetype not in ("image/png","image/jpeg","image/webp"):
            return jsonify(error="Please upload a JPG, PNG or WEBP image."),400
        payload=incoming.read()
        if not payload:
            return jsonify(error="The uploaded image is empty."),400
        try:
            with Image.open(io.BytesIO(payload)) as test:
                test.verify()
            photo = Image.open(io.BytesIO(payload))
            photo.load()
        except (UnidentifiedImageError,OSError,ValueError):
            return jsonify(error="This is not a valid image file."),400
    if not text and photo is None:
        return jsonify(error="Enter a description or upload a fashion image."),400
    results = recommend(text,photo)
    return jsonify(results=results,count=len(results),mode="text vectors + colour-based image retrieval")
@app.errorhandler(413)
def too_large(error):
    return jsonify(error="Image file is too large (maximum 5 MB)."),413

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")))
