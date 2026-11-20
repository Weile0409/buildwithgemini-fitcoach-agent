import datetime
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-31e92fc7c50b"

def seed():
    db = firestore.Client(project=PROJECT_ID)
    print(f"Connecting to Firestore for project: {PROJECT_ID}")

    # Seed exercise routines
    routines = [
        {
            "id": "full-body-strength",
            "name": "Full Body Strength Builder",
            "category": "Strength",
            "level": "Intermediate",
            "target_muscles": ["Chest", "Back", "Legs", "Core"],
            "equipment": ["Barbell", "Dumbbells", "Bench"],
            "duration_minutes": 45,
            "exercises": [
                {"name": "Barbell Squat", "sets": 4, "reps": "8-10"},
                {"name": "Flat Bench Press", "sets": 4, "reps": "8-10"},
                {"name": "Bent-over Barbell Row", "sets": 3, "reps": "10-12"},
                {"name": "Hanging Knee Raises", "sets": 3, "reps": "15"}
            ],
            "description": "Comprehensive full body workout to build foundational strength and muscle mass."
        },
        {
            "id": "hiit-cardio-blast",
            "name": "High-Intensity Cardio Blast",
            "category": "Cardio",
            "level": "Beginner to Intermediate",
            "target_muscles": ["Full Body", "Heart/Lungs"],
            "equipment": ["Bodyweight", "Jump Rope"],
            "duration_minutes": 25,
            "exercises": [
                {"name": "Jump Rope Intervals", "sets": 5, "reps": "45s work / 15s rest"},
                {"name": "Mountain Climbers", "sets": 4, "reps": "40s work / 20s rest"},
                {"name": "Burpees", "sets": 4, "reps": "30s work / 30s rest"},
                {"name": "Plank Jacks", "sets": 3, "reps": "45s work / 15s rest"}
            ],
            "description": "High-calorie burn session designed to boost cardiovascular endurance without weights."
        },
        {
            "id": "half-marathon-tempo",
            "name": "Half Marathon Tempo Run",
            "category": "Running",
            "level": "Intermediate",
            "target_muscles": ["Quads", "Hamstrings", "Calves"],
            "equipment": ["Running Shoes", "GPS Watch"],
            "duration_minutes": 50,
            "exercises": [
                {"name": "Warmup Jog", "sets": 1, "reps": "10 mins easy"},
                {"name": "Tempo Pace Sustained", "sets": 1, "reps": "30 mins at threshold"},
                {"name": "Cooldown Walk/Jog", "sets": 1, "reps": "10 mins easy"}
            ],
            "description": "Lactate threshold building session tailored for half marathon endurance."
        },
        {
            "id": "mobility-recovery-flow",
            "name": "Mobility & Active Recovery Flow",
            "category": "Mobility",
            "level": "All Levels",
            "target_muscles": ["Hips", "Hamstrings", "Spine", "Shoulders"],
            "equipment": ["Yoga Mat", "Foam Roller"],
            "duration_minutes": 20,
            "exercises": [
                {"name": "World's Greatest Stretch", "sets": 2, "reps": "5 each side"},
                {"name": "Cat-Cow & Thread the Needle", "sets": 2, "reps": "10 reps"},
                {"name": "Foam Roll Quads & Upper Back", "sets": 1, "reps": "5 mins total"},
                {"name": "Pigeon Pose", "sets": 2, "reps": "60s hold each side"}
            ],
            "description": "Active recovery routine to relieve muscle stiffness and improve mobility."
        }
    ]

    for routine in routines:
        doc_id = routine["id"]
        db.collection("routines").document(doc_id).set(routine)
        print(f"Seeded routine: {doc_id}")

    # Seed sample workout log
    sample_log = {
        "user_id": "athlete_1",
        "routine_id": "full-body-strength",
        "routine_name": "Full Body Strength Builder",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "notes": "Felt strong on squats. Hit 225 lbs for 8 reps on the last set.",
        "duration_minutes": 47,
        "completed_exercises": ["Barbell Squat", "Flat Bench Press", "Bent-over Barbell Row", "Hanging Knee Raises"]
    }
    db.collection("workout_logs").add(sample_log)
    print("Seeded sample workout log.")

    print("Firestore seeding complete!")

if __name__ == "__main__":
    seed()
