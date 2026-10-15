import io
import unittest
from PIL import Image
from app import app

class TestFashionAI(unittest.TestCase):
    def setUp(self): self.client=app.test_client()
    def test_home(self): self.assertEqual(self.client.get("/").status_code,200)
    def test_health(self): self.assertEqual(self.client.get("/api/health").json["catalogue_size"],24)
    def test_catalogue(self): self.assertEqual(len(self.client.get("/api/products").json),24)
    def test_search(self):
        data=self.client.post("/api/recommend",data={"description":"black casual tshirt"}).json
        self.assertEqual(len(data["results"]),8)
        self.assertEqual(data["results"][0]["category"],"t-shirt")
    def test_image_upload(self):
        b=io.BytesIO()
        Image.new("RGB",(40,40),(200,65,70)).save(b,"PNG")
        b.seek(0)
        response=self.client.post("/api/recommend",data={"image":(b,"red.png")})
        self.assertEqual(response.status_code,200)
    def test_bad_image(self):
        r=self.client.post("/api/recommend",data={"image":(io.BytesIO(b"wrong"),"wrong.png", "image/png")})
        self.assertEqual(r.status_code,400)

if __name__=="__main__": unittest.main()
