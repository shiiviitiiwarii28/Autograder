from fastapi import APIRouter, HTTPException, Depends
from app.database.connection import get_supabase, get_supabase_admin
from typing import List, Dict, Any
from decimal import Decimal

router = APIRouter()

@router.get("/results/student/{student_id}")
async def get_student_results(student_id: str, supabase_client = Depends(get_supabase)):
    """Get all results for a student"""
    
    results = supabase_client.table("grading_results").select("""
        *,
        exams (exam_name, exam_type, exam_date, total_marks),
        questions (question_number, question_text, max_marks)
    """).eq("student_id", student_id).execute()
    
    if not results.data:
        return {"student_id": student_id, "exams": []}
    
    # Group results by exam
    exams_dict = {}
    for result in results.data:
        exam_id = result["exam_id"]
        if exam_id not in exams_dict:
            exams_dict[exam_id] = {
                "exam_id": exam_id,
                "exam_name": result["exams"]["exam_name"],
                "exam_type": result["exams"]["exam_type"],
                "exam_date": result["exams"]["exam_date"],
                "total_marks": result["exams"]["total_marks"],
                "obtained_marks": 0,
                "questions": []
            }
        
        exams_dict[exam_id]["obtained_marks"] += float(result["final_marks"] or 0)
        exams_dict[exam_id]["questions"].append({
            "question_number": result["questions"]["question_number"],
            "question_text": result["questions"]["question_text"],
            "max_marks": result["questions"]["max_marks"],
            "obtained_marks": result["final_marks"],
            "ai_feedback": result["ai_feedback"],
            "is_reviewed": result["is_reviewed_by_teacher"]
        })
    
    # Calculate percentages
    for exam in exams_dict.values():
        total = exam["total_marks"]
        obtained = exam["obtained_marks"]
        exam["percentage"] = round((obtained / total * 100), 2) if total > 0 else 0
        exam["grade"] = calculate_grade(exam["percentage"])
    
    return {
        "student_id": student_id,
        "exams": list(exams_dict.values())
    }

@router.get("/results/exam/{exam_id}")
async def get_exam_results(exam_id: str, supabase_client = Depends(get_supabase)):
    """Get results for all students in an exam"""
    
    # Get grading results
    results = supabase_client.table("grading_results").select("*").eq("exam_id", exam_id).execute()
    
    if not results.data:
        return {"exam_id": exam_id, "students": []}
    
    # Get unique student IDs
    student_ids = list(set([r["student_id"] for r in results.data]))
    
    # Get student details separately
    students_response = supabase_client.table("students").select("id, student_id, full_name").in_("id", student_ids).execute()
    students_map = {s["id"]: s for s in students_response.data} if students_response.data else {}
    
    # Get question details separately
    question_ids = list(set([r["question_id"] for r in results.data]))
    questions_response = supabase_client.table("questions").select("id, question_number, max_marks").in_("id", question_ids).execute()
    questions_map = {q["id"]: q for q in questions_response.data} if questions_response.data else {}
    
    # Group by student
    students_dict = {}
    for result in results.data:
        student_id = result["student_id"]
        student_info = students_map.get(student_id, {"student_id": "N/A", "full_name": "Unknown"})
        question_info = questions_map.get(result["question_id"], {"question_number": 0, "max_marks": 0})
        
        if student_id not in students_dict:
            students_dict[student_id] = {
                "student_id": student_info["student_id"],
                "student_name": student_info["full_name"],
                "total_marks": 0,
                "questions_graded": 0,
                "questions": []
            }
        
        students_dict[student_id]["total_marks"] += float(result["final_marks"] or 0)
        students_dict[student_id]["questions_graded"] += 1
        students_dict[student_id]["questions"].append({
            "question_number": question_info["question_number"],
            "max_marks": question_info["max_marks"],
            "obtained_marks": result["final_marks"],
            "ai_confidence": result.get("ai_confidence", 0),
            "needs_review": float(result.get("ai_confidence", 0)) < 0.7
        })
    
    return {
        "exam_id": exam_id,
        "students": list(students_dict.values())
    }

@router.get("/results/exam/{exam_id}/summary")
async def get_exam_summary(exam_id: str, supabase_client = Depends(get_supabase)):
    """Get complete exam summary with statistics - QUICK FIX"""
    
    from app.database.connection import get_supabase_admin
    
    # USE ADMIN CLIENT to bypass RLS
    supabase_admin = get_supabase_admin()
    
    # Step 1: Get exam info with separate queries
    exam_result = supabase_admin.table("exams").select("*").eq("id", exam_id).execute()
    
    if not exam_result.data or len(exam_result.data) == 0:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    exam_info = exam_result.data[0]
    
    # Step 2: Get subject info separately
    subject_info = {"subject_name": "N/A", "subject_code": "N/A"}
    if exam_info.get("subject_id"):
        subject_result = supabase_client.table("subjects").select("subject_name, subject_code").eq("id", exam_info["subject_id"]).execute()
        if subject_result.data:
            subject_info = subject_result.data[0]
    
    # Step 3: Get total questions
    questions_result = supabase_client.table("questions").select("id", count="exact").eq("exam_id", exam_id).execute()
    total_questions = questions_result.count or 0
    
    # Step 4: Get ALL grading results - Try multiple approaches
    # First try by exam_id
    grading_results = supabase_client.table("grading_results").select("*").eq("exam_id", exam_id).execute()
    
    # If no results, try getting via student_ids from uploads
    if not grading_results.data:
        # Get student IDs from uploads
        upload_student_ids = [u["student_id"] for u in exam_result.data[0].get("uploads", [])] if exam_result.data else []
        
        if not upload_student_ids:
            # Get from exam_uploads table
            uploads = supabase_client.table("exam_uploads").select("student_id").eq("exam_id", exam_id).execute()
            upload_student_ids = [u["student_id"] for u in uploads.data] if uploads.data else []
        
        if upload_student_ids:
            # Try to get grading results by student_ids
            grading_results = supabase_client.table("grading_results").select("*").in_("student_id", upload_student_ids).execute()
    
    if not grading_results.data:
        return {
            "exam_info": {
                "exam_id": exam_info["id"],
                "exam_name": exam_info["exam_name"],
                "exam_code": exam_info["exam_code"],
                "subject_name": subject_info["subject_name"],
                "subject_code": subject_info["subject_code"],
                "total_marks": exam_info["total_marks"],
                "total_questions": total_questions,
                "total_students": 0
            },
            "statistics": {
                "average_score": 0,
                "grade_distribution": {"A+": 0, "A": 0, "B+": 0, "B": 0, "C": 0, "F": 0},
                "students_needing_review": 0
            },
            "students": []
        }
    
    # Step 5: Get unique student IDs from grading results
    student_ids = list(set([r["student_id"] for r in grading_results.data]))
    
    # Step 6: Get student details in separate query
    students_response = supabase_admin.table("students").select("id, student_id, full_name").in_("id", student_ids).execute()
    
    students_map = {}
    if students_response.data:
        for student in students_response.data:
            students_map[student["id"]] = student
    
    # Step 7: Process student data
    students_data = {}
    total_score_sum = 0
    grade_distribution = {"A+": 0, "A": 0, "B+": 0, "B": 0, "C": 0, "F": 0}
    students_needing_review = 0
    
    for result in grading_results.data:
        student_uuid = result["student_id"]
        
        # Get student info from map
        student_info = students_map.get(student_uuid, {"student_id": "N/A", "full_name": "Unknown"})
        
        # Initialize student if not exists
        if student_uuid not in students_data:
            students_data[student_uuid] = {
                "student_id": student_info["student_id"],
                "student_name": student_info["full_name"],
                "obtained_marks": 0,
                "questions_answered": 0,
                "needs_review": False
            }
        
        # Accumulate marks
        final_marks = result.get("final_marks")
        if final_marks:
            students_data[student_uuid]["obtained_marks"] += float(final_marks)
        students_data[student_uuid]["questions_answered"] += 1
        
        # Check if needs review
        confidence = result.get("ai_confidence")
        is_reviewed = result.get("is_reviewed_by_teacher", False)
        if confidence and float(confidence) < 0.7 and not is_reviewed:
            students_data[student_uuid]["needs_review"] = True
    
    # Step 8: Calculate percentages and grades for each student
    students_list = []
    for student in students_data.values():
        percentage = (student["obtained_marks"] / exam_info["total_marks"] * 100) if exam_info["total_marks"] > 0 else 0
        grade = calculate_grade(percentage)
        
        student["percentage"] = round(percentage, 2)
        student["grade"] = grade
        
        # Update statistics
        total_score_sum += percentage
        grade_distribution[grade] += 1
        if student["needs_review"]:
            students_needing_review += 1
        
        students_list.append(student)
    
    # Step 9: Calculate average
    total_students = len(students_data)
    average_score = round(total_score_sum / total_students, 2) if total_students > 0 else 0
    
    return {
        "exam_info": {
            "exam_id": exam_info["id"],
            "exam_name": exam_info["exam_name"],
            "exam_code": exam_info["exam_code"],
            "subject_name": subject_info["subject_name"],
            "subject_code": subject_info["subject_code"],
            "total_marks": exam_info["total_marks"],
            "total_questions": total_questions,
            "total_students": total_students
        },
        "statistics": {
            "average_score": average_score,
            "grade_distribution": grade_distribution,
            "students_needing_review": students_needing_review
        },
        "students": students_list
    }

@router.put("/results/review/{result_id}")
async def review_grading_result(
    result_id: str,
    teacher_marks: float,
    teacher_feedback: str,
    supabase_client = Depends(get_supabase)
):
    """Teacher review and update grading result"""
    
    update_data = {
        "teacher_assigned_marks": teacher_marks,
        "final_marks": teacher_marks,
        "teacher_feedback": teacher_feedback,
        "is_reviewed_by_teacher": True,
        "reviewed_at": "now()"
    }
    
    result = supabase_client.table("grading_results").update(update_data).eq("id", result_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Result not found")
    
    return {"message": "Result updated successfully", "result_id": result_id}

def calculate_grade(percentage: float) -> str:
    """Calculate letter grade from percentage"""
    if percentage >= 85:
        return "A+"
    elif percentage >= 75:
        return "A"
    elif percentage >= 65:
        return "B+"
    elif percentage >= 55:
        return "B"
    elif percentage >= 45:
        return "C"
    else:
        return "F"