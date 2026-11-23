import unittest
from app import app, distance_from_rssi, trilaterate

class SonarTests(unittest.TestCase):
    def setUp(self): self.client = app.test_client()
    def test_home(self): self.assertEqual(self.client.get('/').status_code, 200)
    def test_state(self):
        data=self.client.get('/api/state').get_json(); self.assertIn('target',data); self.assertEqual(len(data['anchors']),4)
    def test_ingest_validation(self): self.assertEqual(self.client.post('/api/readings',json={'anchor_id':'bad','rssi':-60}).status_code,400)
    def test_distance_monotonic(self): self.assertLess(distance_from_rssi(-50),distance_from_rssi(-70))
    def test_trilateration_center(self):
        x,y,c=trilaterate({'north-west':3.05,'north-east':3.05,'south-east':3.05,'south-west':3.05}); self.assertAlmostEqual(x,3,delta=.2); self.assertAlmostEqual(y,2,delta=.2)

if __name__ == '__main__': unittest.main()

