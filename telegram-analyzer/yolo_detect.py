import os
import csv
import glob
from ultralytics import YOLO

IMAGES_BASE_DIR = os.path.join("data", "raw", "images")
OUTPUT_CSV = "yolo_detections.csv"
CONFIDENCE_THRESHOLD = 0.5  # ignore detections the model isn't at least 50% sure about

# YOLO's 80 built-in classes don't include "skincare bottle" or "medicine box" -
# we approximate "product container" using its closest generic classes.
PRODUCT_CLASSES = {"bottle", "cup", "wine glass", "vase", "bowl"}
PERSON_CLASSES = {"person"}


def classify_image(detected_classes):
    """
    Apply the classification scheme from the task:
    - promotional: person + product
    - product_display: product, no person
    - lifestyle: person, no product
    - other: neither
    """
    has_person = bool(detected_classes & PERSON_CLASSES)
    has_product = bool(detected_classes & PRODUCT_CLASSES)

    if has_person and has_product:
        return "promotional"
    elif has_product:
        return "product_display"
    elif has_person:
        return "lifestyle"
    else:
        return "other"


def find_all_images():
    """
    Find every downloaded image, returning (file_path, channel_name, message_id).
    Mirrors the folder structure from Task 1:
    data/raw/images/{channel_name}/{message_id}.jpg
    """
    pattern = os.path.join(IMAGES_BASE_DIR, "*", "*.jpg")
    files = glob.glob(pattern)

    results = []
    for file_path in files:
        parts = file_path.split(os.sep)
        channel_name = parts[-2]
        message_id = parts[-1].replace(".jpg", "")
        results.append((file_path, channel_name, message_id))

    return results


def main():
    model = YOLO("yolov8n.pt")
    images = find_all_images()
    print(f"Found {len(images)} image(s) to process.\n")

    rows = []

    for file_path, channel_name, message_id in images:
        results = model(file_path, verbose=False)  # verbose=False quiets the per-image log line

        detected_classes = set()

        for result in results:
            for box in result.boxes:
                confidence = float(box.conf[0])
                if confidence < CONFIDENCE_THRESHOLD:
                    continue  # skip low-confidence guesses

                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                detected_classes.add(class_name)

                rows.append({
                    "channel": channel_name,
                    "message_id": message_id,
                    "detected_class": class_name,
                    "confidence_score": round(confidence, 4),
                })

        # If NO objects passed the confidence threshold at all, still record
        # the image with a blank detection row, so it's not silently missing.
        if not detected_classes:
            rows.append({
                "channel": channel_name,
                "message_id": message_id,
                "detected_class": "",
                "confidence_score": "",
            })

        image_category = classify_image(detected_classes)
        print(f"  {channel_name}/{message_id}.jpg -> {sorted(detected_classes) or 'nothing detected'} -> {image_category}")

    # Write every individual detection to CSV (one row per detected object,
    # so a photo with both a person AND a bottle produces 2 rows)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "channel", "message_id", "detected_class", "confidence_score"
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone! Saved {len(rows)} detection rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()