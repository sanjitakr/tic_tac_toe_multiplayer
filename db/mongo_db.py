from pymongo import MongoClient, ReadPreference
import base64
from config import MONGO_URI, MONGO_DB, MONGO_COLLECTION

class MongoDB:
    def __init__(self):
        if not MONGO_URI:
            raise ValueError("MONGO_URI not found in .env")

        import certifi
        self.client = MongoClient(
            MONGO_URI,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=5000,
            # This tells MongoDB to use a Secondary if the Primary is busy or unreachable
            readPreference='primaryPreferred'
        )
        self.db = self.client[MONGO_DB]
        self.collection = self.db[MONGO_COLLECTION]

    def upsert_image(self, uid, image_bytes):
        try:
            encoded_image = base64.b64encode(image_bytes).decode("utf-8")

            self.collection.update_one(
                {"uid": uid},
                {"$set": {"image": encoded_image}},
                upsert=True
            )

            print(f"[MongoDB] Stored image for {uid}")

        except Exception as e:
            print(f"[Mongo ERROR] {uid}: {e}")

            
   # In mongo_db.py
    def get_all_images(self):
        try:
            db_images_dict = {}
            print("[MongoDB] Starting cursor fetch...")
            count = 0
            for doc in self.collection.find():
                db_images_dict[doc["uid"]] = doc["image"]
                count += 1
                if count % 5 == 0: # Log every 5 images so you know it's alive
                    print(f"[MongoDB] Downloaded {count} images...")
            
            print(f"[MongoDB] Fetch complete. Total: {count} images.")
            return db_images_dict
        except Exception as e:
            print(f"[Mongo ERROR]: {e}")
            return {}