import numpy as np
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input, decode_predictions
from tensorflow.keras.preprocessing import image as keras_image
from PIL import Image
import io
from haversine import haversine
from .models import Report, Match
from difflib import SequenceMatcher

# Load the model once when the server starts (Standard Practice)
model = MobileNetV2(weights='imagenet')

def analyze_image(image_field):
    """
    Takes a Django ImageField, processes it, and returns top 3 AI labels.
    """
    try:
        # 1. Convert Django ImageField to PIL Image
        img = Image.open(image_field)
        img = img.convert('RGB')
        img = img.resize((224, 224)) # MobileNetV2 expects 224x224

        # 2. Convert to Array
        x = keras_image.img_to_array(img)
        x = np.expand_dims(x, axis=0)
        x = preprocess_input(x)

        # 3. Predict
        preds = model.predict(x)
        decoded = decode_predictions(preds, top=3)[0]

        # 4. Format as a clean dictionary for our JSONField
        # Returns: {"label1": "backpack", "confidence1": 0.85, ...}
        tags = {}
        for i, (imagenet_id, label, score) in enumerate(decoded):
            tags[f"label_{i+1}"] = label.replace('_', ' ')
            tags[f"confidence_{i+1}"] = float(round(score, 2))
        
        return tags
    except Exception as e:
        print(f"AI Error: {e}")
        return {"error": "Could not analyze image"}
    
def calculate_match_score(report1, report2):
    # 1. Distance Check (Max 5km)
    loc1 = (float(report1.latitude), float(report1.longitude))
    loc2 = (float(report2.latitude), float(report2.longitude))
    distance = haversine(loc1, loc2)
    
    if distance > 5: # Too far away to be a match
        return 0
    
    # 2. AI Tag Overlap
    tags1 = set(report1.item.ai_tags.values())
    tags2 = set(report2.item.ai_tags.values())
    common_tags = tags1.intersection(tags2)
    
    # Logic: More common tags + closer distance = higher score
    score = (len(common_tags) * 20) + (5 - distance)
    return score


def find_potential_matches(new_report):
    # 1. Find reports of the opposite type (if I'm 'lost', look for 'found')
    target_type = 'found' if new_report.report_type == 'lost' else 'lost'
    potential_targets = Report.objects.filter(report_type=target_type, is_resolved=False)

    for target in potential_targets:
        score = 0
        
        # Logic A: Same Category (Huge boost)
        if new_report.item.category == target.item.category:
            score += 50
            
        # Logic B: AI Tag Overlap (We will implement the real AI later, for now, let's mock it)
        # If the titles are similar
        if new_report.item.title.lower() in target.item.title.lower() or target.item.title.lower() in new_report.item.title.lower():
            score += 40

        # 2. If the score is high enough, create a Match entry
        if score >= 50:
            Match.objects.get_or_create(
                lost_report=new_report if new_report.report_type == 'lost' else target,
                found_report=target if new_report.report_type == 'lost' else new_report,
                defaults={'score': score}
            )



def calculate_similarity(text1, text2):
    t1 = str(text1 or "").strip().lower()
    t2 = str(text2 or "").strip().lower()
    if not t1 or not t2:
        return 0.0
    # Returns a float between 0.0 and 1.0
    return SequenceMatcher(None, t1, t2).ratio()

def run_matching_engine(new_report):
    from .models import Report, Match 
    
    target_type = 'found' if new_report.report_type == 'lost' else 'lost'
    
    # Filtering for the opposite type, same category, and NOT already resolved
    candidates = Report.objects.filter(
        report_type=target_type,
        item__category=new_report.item.category,
        is_resolved=False  
    ).exclude(id=new_report.id)

    for candidate in candidates:
        # FIX: Reach through the 'item' to get the description
        title_score = calculate_similarity(new_report.item.title, candidate.item.title)
        
        # Change 'new_report.description' to 'new_report.item.description'
        desc_score = calculate_similarity(new_report.item.description, candidate.item.description)
        
        # Weighted score: Title is usually more reliable than description
        final_score = (title_score * 0.7) + (desc_score * 0.3)

        if final_score > 0.4:
            Match.objects.get_or_create(
                lost_report=new_report if new_report.report_type == 'lost' else candidate,
                found_report=candidate if new_report.report_type == 'lost' else new_report,
                defaults={'score': final_score}
            )