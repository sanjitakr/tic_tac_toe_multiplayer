import csv
from db.mysql_db import MySQLDB
from db.mongo_db import MongoDB
from scraper.scraper import fetch_image

def run_pipeline():
    mysql_db = MySQLDB()
    mongo_db = MongoDB()

    with open("batch_data.csv", "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            uid = row["uid"]
            name = row["name"]
            base_url = row["website_url"]

            if not base_url.startswith("http"):
                base_url = "https://" + base_url

            image_url = f"{base_url}/images/pfp.jpg"

            print(f"[PROCESSING] {uid}")

            image_data = fetch_image(image_url)

            # ALWAYS insert metadata (even if image fails)
            mysql_db.insert_user(uid, name)

            if image_data:
                mongo_db.upsert_image(uid, image_data)
            else:
                print(f"[SKIPPED IMAGE] {uid}")

    print("Pipeline completed")

if __name__ == "__main__":
    run_pipeline()