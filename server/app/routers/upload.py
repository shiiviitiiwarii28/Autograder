from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
import aiofiles
import os
from uuid import uuid4
from typing import List, Dict, Any
from app.database.connection import get_supabase, get_supabase_admin
from app.core.config import settings
from app.services.ocr_service import OCRService
import asyncio
import zipfile
import tempfile
import shutil

router = APIRouter()
ocr_service = OCRService()

# app/routers/upload.py (UPDATE ONLY THE STUDENT LOOKUP PART)

@router.post("/upload/batch/{exam_id}")
async def batch_upload_exam_papers(
    exam_id: str,
    files: List[UploadFile] = File(...),
    student_ids: str = Form(...),
    teacher_id: str = Form(...),
    supabase_client = Depends(get_supabase)
):
    """Batch upload multiple exam papers by teacher"""
    print(f"\n{'='*60}")
    print(f"🚀 BATCH UPLOAD STARTED")
    print(f"{'='*60}")
    print(f"Exam ID: {exam_id}")
    print(f"Teacher ID: {teacher_id}")
    print(f"Number of files: {len(files)}")
    print(f"Student IDs received: {student_ids}")
    # Parse student IDs
    student_id_list = [sid.strip() for sid in student_ids.split(',')]
    print(f"Parsed student IDs: {student_id_list}")
    print(f"Number of student IDs: {len(student_id_list)}")

    if len(files) != len(student_id_list):
        raise HTTPException(
            status_code=400, 
            detail=f"Number of files ({len(files)}) must match number of student IDs ({len(student_id_list)})"
        )
    
    # Verify exam exists
    exam_result = supabase_client.table("exams").select("*").eq("id", exam_id).execute()
    if not exam_result.data:
        raise HTTPException(status_code=404, detail="Exam not found")

    print(f"✅ Exam verified: {exam_result.data[0].get('exam_name', 'Unknown')}")

    upload_results = []
    failed_uploads = []
    
    for idx, (file, student_id) in enumerate(zip(files, student_id_list)):
        try:
            # ✅ IMPROVED: Better student lookup with error handling
            print(f"Looking up student: {student_id}")
            
            student_result = supabase_client.table("students").select("id, student_id, full_name").eq("student_id", student_id).execute()
            
            print(f"Student lookup result: {student_result.data}")
            
            if not student_result.data or len(student_result.data) == 0:
                print(f"❌ Student not found: {student_id}")
                failed_uploads.append({
                    "file": file.filename,
                    "student_id": student_id,
                    "error": f"Student with ID '{student_id}' not found in database"
                })
                continue
            
            student_uuid = student_result.data[0]["id"]
            print(f"✅ Found student: {student_result.data[0]['full_name']} (UUID: {student_uuid})")
            
            # Validate file
            if not file.filename:
                failed_uploads.append({
                    "file": "unknown",
                    "student_id": student_id,
                    "error": "No filename provided"
                })
                continue
            
            file_extension = file.filename.split('.')[-1].lower()
            
            # ✅ IMPROVED: Add 'txt' to allowed extensions if missing
            allowed_extensions = settings.ALLOWED_EXTENSIONS.split(',')
            if 'txt' not in allowed_extensions:
                allowed_extensions.append('txt')
            
            if file_extension not in allowed_extensions:
                failed_uploads.append({
                    "file": file.filename,
                    "student_id": student_id,
                    "error": f"Invalid file type: {file_extension}. Allowed: {', '.join(allowed_extensions)}"
                })
                continue
            
            # Read file content
            content = await file.read()
            await file.seek(0)
            
            if len(content) > settings.MAX_FILE_SIZE:
                failed_uploads.append({
                    "file": file.filename,
                    "student_id": student_id,
                    "error": f"File too large: {len(content)} bytes (max: {settings.MAX_FILE_SIZE})"
                })
                continue
            
            # Generate unique filename
            unique_filename = f"{uuid4()}.{file_extension}"
            file_path = f"{settings.UPLOAD_PATH}{exam_id}/{student_id}/{unique_filename}"
            
            # Create directory
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            print(f"✅ File saved: {file_path}")
            
            # Create upload record
            upload_data = {
                "exam_id": exam_id,
                "student_id": student_uuid,
                "uploaded_by_teacher_id": teacher_id,
                "file_name": file.filename,
                "file_path": file_path,
                "file_size": len(content),
                "file_type": file_extension,
                "processing_status": "uploaded"
            }
            
            result = supabase_client.table("exam_uploads").insert(upload_data).execute()
            
            if not result.data:
                raise Exception("Failed to create upload record")
            
            upload_id = result.data[0]["id"]
            print(f"✅ Upload record created: {upload_id}")
            
            # Start OCR processing in background
            asyncio.create_task(process_upload_async(upload_id, file_path, file_extension))
            
            upload_results.append({
                "upload_id": upload_id,
                "student_id": student_id,
                "file_name": file.filename,
                "status": "processing"
            })
            
        except Exception as e:
            print(f"❌ Error processing file {file.filename}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            failed_uploads.append({
                "file": file.filename,
                "student_id": student_id,
                "error": str(e)
            })
    
    print(f"\n{'='*60}")
    print(f"📊 UPLOAD SUMMARY")
    print(f"{'='*60}")
    print(f"Total files: {len(files)}")
    print(f"Successful: {len(upload_results)}")
    print(f"Failed: {len(failed_uploads)}")
    print(f"{'='*60}\n")
    return {
        "exam_id": exam_id,
        "total_files": len(files),
        "successful_uploads": len(upload_results),
        "failed_uploads": len(failed_uploads),
        "uploads": upload_results,
        "failures": failed_uploads,
        "message": f"Uploaded {len(upload_results)} out of {len(files)} files successfully"
    }

@router.post("/upload/zip/{exam_id}")
async def upload_exam_papers_zip(
    exam_id: str,
    zip_file: UploadFile = File(...),
    teacher_id: str = Form(...),
    supabase_client = Depends(get_supabase)
):
    """
    Upload multiple exam papers as a ZIP file
    File naming convention: studentID_filename.ext
    Example: STU001_exam.pdf, STU002_exam.jpg
    """
    
    if not zip_file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a ZIP archive")
    
    # Verify exam exists
    exam_result = supabase_client.table("exams").select("*").eq("id", exam_id).execute()
    if not exam_result.data:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    upload_results = []
    failed_uploads = []
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Save ZIP file temporarily
        zip_path = os.path.join(temp_dir, "upload.zip")
        content = await zip_file.read()
        
        async with aiofiles.open(zip_path, 'wb') as f:
            await f.write(content)
        
        # Extract ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Process each file
        for root, dirs, files in os.walk(temp_dir):
            for filename in files:
                if filename == "upload.zip" or filename.startswith('.'):
                    continue
                
                try:
                    # Parse student ID from filename (format: studentID_filename.ext)
                    if '_' not in filename:
                        failed_uploads.append({
                            "file": filename,
                            "error": "Invalid filename format. Expected: studentID_filename.ext"
                        })
                        continue
                    
                    student_id = filename.split('_')[0]
                    file_path_temp = os.path.join(root, filename)
                    
                    # Verify student exists
                    student_result = supabase_client.table("students").select("id").eq("student_id", student_id).execute()
                    if not student_result.data:
                        failed_uploads.append({
                            "file": filename,
                            "student_id": student_id,
                            "error": "Student not found"
                        })
                        continue
                    
                    student_uuid = student_result.data[0]["id"]
                    
                    # Validate file extension
                    file_extension = filename.split('.')[-1].lower()
                    if file_extension not in settings.ALLOWED_EXTENSIONS.split(','):
                        failed_uploads.append({
                            "file": filename,
                            "student_id": student_id,
                            "error": "Invalid file type"
                        })
                        continue
                    
                    # Read file
                    async with aiofiles.open(file_path_temp, 'rb') as f:
                        file_content = await f.read()
                    
                    if len(file_content) > settings.MAX_FILE_SIZE:
                        failed_uploads.append({
                            "file": filename,
                            "student_id": student_id,
                            "error": "File too large"
                        })
                        continue
                    
                    # Generate unique filename and save
                    unique_filename = f"{uuid4()}.{file_extension}"
                    final_path = f"{settings.UPLOAD_PATH}{exam_id}/{student_id}/{unique_filename}"
                    
                    os.makedirs(os.path.dirname(final_path), exist_ok=True)
                    
                    async with aiofiles.open(final_path, 'wb') as f:
                        await f.write(file_content)
                    
                    # Create upload record
                    upload_data = {
                        "exam_id": exam_id,
                        "student_id": student_uuid,
                        "uploaded_by_teacher_id": teacher_id,
                        "file_name": filename,
                        "file_path": final_path,
                        "file_size": len(file_content),
                        "file_type": file_extension,
                        "processing_status": "uploaded"
                    }
                    
                    result = supabase_client.table("exam_uploads").insert(upload_data).execute()
                    upload_id = result.data[0]["id"]
                    
                    # Start OCR processing
                    asyncio.create_task(process_upload_async(upload_id, final_path, file_extension))
                    
                    upload_results.append({
                        "upload_id": upload_id,
                        "student_id": student_id,
                        "file_name": filename,
                        "status": "processing"
                    })
                    
                except Exception as e:
                    failed_uploads.append({
                        "file": filename,
                        "error": str(e)
                    })
        
    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    return {
        "exam_id": exam_id,
        "successful_uploads": len(upload_results),
        "failed_uploads": len(failed_uploads),
        "uploads": upload_results,
        "failures": failed_uploads,
        "message": f"Processed ZIP file: {len(upload_results)} successful, {len(failed_uploads)} failed"
    }


async def process_upload_async(upload_id: str, file_path: str, file_extension: str):
    """Background task to process uploaded file and trigger grading"""
    supabase_admin = get_supabase_admin()
    
    try:
        print(f"\n{'='*60}")
        print(f"🔄 PROCESSING UPLOAD: {upload_id}")
        print(f"{'='*60}")
        
        # Update status to processing
        supabase_admin.table("exam_uploads").update({
            "processing_status": "processing"
        }).eq("id", upload_id).execute()
        
        print(f"📄 Reading file: {file_path}")
        
        # Read file based on type
        if file_extension == 'txt':
            ocr_result = await ocr_service.extract_text_from_txt(file_path)
        elif file_extension == 'pdf':
            async with aiofiles.open(file_path, 'rb') as f:
                file_content = await f.read()
            ocr_result = await ocr_service.extract_text_from_pdf(file_content)
        else:
            async with aiofiles.open(file_path, 'rb') as f:
                file_content = await f.read()
            ocr_result = await ocr_service.extract_text_from_image(file_content)
        
        print(f"📝 OCR Result: {ocr_result['status']}")
        print(f"📊 Confidence: {ocr_result.get('confidence', 0.0)}")
        print(f"📄 Text preview: {ocr_result['text'][:100]}...")
        
        # Check if OCR was successful
        if ocr_result["status"] != "success" or not ocr_result["text"].strip():
            print(f"❌ OCR failed: No text extracted")
            supabase_admin.table("exam_uploads").update({
                "processing_status": "failed",
                "error_message": "No text extracted",
                "ocr_extracted_text": "",
                "confidence_score": ocr_result.get("confidence", 0.0),
                "processed_at": "now()"
            }).eq("id", upload_id).execute()
            return
        
        # Update with OCR results
        supabase_admin.table("exam_uploads").update({
            "processing_status": "processed",
            "ocr_extracted_text": ocr_result["text"],
            "confidence_score": ocr_result["confidence"],
            "processed_at": "now()"
        }).eq("id", upload_id).execute()
        
        print(f"✅ OCR completed successfully")
        
        # Now trigger auto-grading
        print(f"🤖 Starting auto-grading...")
        await auto_grade_upload(upload_id, supabase_admin)
        
    except Exception as e:
        print(f"❌ Error processing upload {upload_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        supabase_admin.table("exam_uploads").update({
            "processing_status": "failed",
            "error_message": str(e)
        }).eq("id", upload_id).execute()


async def auto_grade_upload(upload_id: str, supabase_admin):
    """Automatically grade an upload after OCR processing"""
    try:
        print(f"\n{'='*60}")
        print(f"🎓 AUTO-GRADING UPLOAD: {upload_id}")
        print(f"{'='*60}")
        
        # Get upload details first
        upload_result = supabase_admin.table("exam_uploads").select("*").eq("id", upload_id).execute()
        
        if not upload_result.data:
            print(f"❌ Upload {upload_id} not found")
            return
        
        upload = upload_result.data[0]
        exam_id = upload.get("exam_id")
        
        if not exam_id:
            print(f"❌ No exam_id in upload record")
            return
        
        print(f"📋 Exam ID: {exam_id}")
        
        # Get exam details
        exam_result = supabase_admin.table("exams").select(
            "id, exam_name, total_marks"
        ).eq("id", exam_id).execute()
        
        if not exam_result.data:
            print(f"❌ Exam {exam_id} not found")
            return
        
        exam = exam_result.data[0]
        print(f"📋 Exam: {exam['exam_name']}")
        
        # Get questions separately
        questions_result = supabase_admin.table("questions").select(
            "id, question_number, question_text, max_marks, marking_scheme, sample_answer, keywords"
        ).eq("exam_id", exam_id).order("question_number").execute()
        
        questions = questions_result.data if questions_result.data else []
        
        if not questions:
            print(f"❌ No questions found for exam {exam_id}")
            print(f"Debug: Checking if questions table has any data...")
            
            # Debug: Check if questions exist at all
            all_questions = supabase_admin.table("questions").select("id, exam_id").limit(5).execute()
            print(f"Sample questions in database: {all_questions.data}")
            
            # Check if this specific exam has questions
            exam_questions_check = supabase_admin.table("questions").select("count").eq("exam_id", exam_id).execute()
            print(f"Questions count for exam {exam_id}: {exam_questions_check}")
            
            return
        
        print(f"📝 Questions found: {len(questions)}")
        
        ocr_text = upload.get("ocr_extracted_text", "")
        
        if not ocr_text:
            print(f"❌ No OCR text found")
            return
        
        print(f"📄 OCR Text preview: {ocr_text[:200]}...")
        
        # Parse answers from OCR text
        parsed_answers = ocr_service._parse_answers_botanical(ocr_text)
        
        print(f"✅ Parsed {len(parsed_answers)} answers: {list(parsed_answers.keys())}")
        
        # Grade each question
        from app.services.ai_service import AIGradingService
        ai_service = AIGradingService()
        
        graded_count = 0
        
        for question in questions:
            question_key = f"question_{question['question_number']}"
            student_answer = parsed_answers.get(question_key, "")
            
            print(f"\n{'─'*60}")
            print(f"📝 Question {question['question_number']}")
            
            if not student_answer:
                print(f"⚠️  No answer found for {question_key}")
                continue
            
            print(f"   Answer preview: {student_answer[:100]}...")
            
            # Prepare question data for grading
            question_data = {
                "question": question["question_text"],
                "model_answer": question.get("sample_answer", ""),
                "marks": float(question["max_marks"]),
                "question_number": question["question_number"],
                "keywords": question.get("keywords", []) if question.get("keywords") else [],
                "type": "descriptive"
            }
            
            # Grade the question
            print(f"   🤖 Grading in progress...")
            result = await ai_service.grade_question(question_data, student_answer)
            
            # Save student answer
            answer_data = {
                "upload_id": upload_id,
                "question_id": question["id"],
                "student_id": upload["student_id"],
                "extracted_answer": student_answer,
                "confidence_score": float(result.confidence_score)
            }
            
            answer_result = supabase_admin.table("student_answers").insert(answer_data).execute()
            
            if not answer_result.data:
                print(f"   ❌ Failed to save answer")
                continue
            
            # Save grading result
            grading_data = {
                "student_answer_id": answer_result.data[0]["id"],
                "exam_id": exam["id"],
                "student_id": upload["student_id"],
                "question_id": question["id"],
                "ai_assigned_marks": float(result.marks_obtained),
                "final_marks": float(result.marks_obtained),
                "ai_feedback": result.feedback,
                "similarity_score": 0.0,
                "ai_confidence": float(result.confidence_score),
                "is_reviewed_by_teacher": False
            }
            
            supabase_admin.table("grading_results").insert(grading_data).execute()
            
            print(f"   ✅ Marks: {result.marks_obtained}/{question['max_marks']}")
            print(f"   💬 Feedback: {result.feedback[:100]}...")
            
            graded_count += 1
        
        print(f"\n{'='*60}")
        print(f"🎉 GRADING COMPLETE")
        print(f"{'='*60}")
        print(f"Total questions: {len(questions)}")
        print(f"Graded: {graded_count}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error in auto-grading: {str(e)}")
        import traceback
        traceback.print_exc()

@router.get("/upload/exam/{exam_id}/status")
async def get_exam_upload_status(exam_id: str, supabase_client = Depends(get_supabase)):
    """Get upload status for all students in an exam"""
    
    results = supabase_client.table("exam_uploads").select("""
        *,
        students (student_id, full_name)
    """).eq("exam_id", exam_id).order("created_at", desc=True).execute()
    
    return {
        "exam_id": exam_id,
        "total_uploads": len(results.data),
        "uploads": results.data
    }

@router.get("/upload/status/{upload_id}")
async def get_upload_status(upload_id: str, supabase_client = Depends(get_supabase)):
    """Get upload processing status"""
    
    result = supabase_client.table("exam_uploads").select("*").eq("id", upload_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    return result.data[0]

@router.delete("/upload/{upload_id}")
async def delete_upload(
    upload_id: str,
    teacher_id: str = Form(...),
    supabase_client = Depends(get_supabase)
):
    """Delete an upload (only by teacher who uploaded it)"""
    
    # Verify upload exists and was uploaded by this teacher
    upload = supabase_client.table("exam_uploads").select("*").eq("id", upload_id).execute()
    
    if not upload.data:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    if upload.data[0].get("uploaded_by_teacher_id") != teacher_id:
        raise HTTPException(status_code=403, detail="Unauthorized to delete this upload")
    
    # Delete file from disk
    file_path = upload.data[0]["file_path"]
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete from database (cascades to related records)
    supabase_client.table("exam_uploads").delete().eq("id", upload_id).execute()
    
    return {"message": "Upload deleted successfully", "upload_id": upload_id}

# Add this to your upload.py file

@router.post("/upload/{upload_id}/reprocess")
async def reprocess_upload(upload_id: str):
    """Manually trigger reprocessing and grading for an upload"""
    supabase_admin = get_supabase_admin()
    
    try:
        # Get upload details
        upload_result = supabase_admin.table("exam_uploads").select("*").eq("id", upload_id).execute()
        
        if not upload_result.data:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        upload = upload_result.data[0]
        
        print(f"\n{'='*60}")
        print(f"🔄 MANUAL REPROCESSING: {upload_id}")
        print(f"{'='*60}")
        print(f"Student ID: {upload['student_id']}")
        print(f"Exam ID: {upload['exam_id']}")
        print(f"File: {upload['file_path']}")
        print(f"Current status: {upload['processing_status']}")
        
        # Trigger auto-grading
        await auto_grade_upload(upload_id, supabase_admin)
        
        return {
            "message": "Reprocessing completed",
            "upload_id": upload_id,
            "status": "success"
        }
        
    except Exception as e:
        print(f"❌ Reprocessing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exam/{exam_id}/regrade-all")
async def regrade_all_uploads(exam_id: str):
    """Manually regrade all uploads for an exam"""
    supabase_admin = get_supabase_admin()
    
    try:
        # Get all processed uploads for this exam
        uploads_result = supabase_admin.table("exam_uploads").select("id").eq(
            "exam_id", exam_id
        ).eq("processing_status", "processed").execute()
        
        if not uploads_result.data:
            raise HTTPException(status_code=404, detail="No processed uploads found")
        
        print(f"\n{'='*60}")
        print(f"🔄 REGRADING ALL UPLOADS FOR EXAM: {exam_id}")
        print(f"{'='*60}")
        print(f"Found {len(uploads_result.data)} uploads to regrade")
        
        results = []
        
        for upload in uploads_result.data:
            upload_id = upload['id']
            print(f"\n📝 Regrading upload: {upload_id}")
            
            try:
                await auto_grade_upload(upload_id, supabase_admin)
                results.append({
                    "upload_id": upload_id,
                    "status": "success"
                })
                print(f"✅ Success: {upload_id}")
            except Exception as e:
                print(f"❌ Failed: {upload_id} - {str(e)}")
                results.append({
                    "upload_id": upload_id,
                    "status": "failed",
                    "error": str(e)
                })
        
        successful = len([r for r in results if r['status'] == 'success'])
        failed = len(results) - successful
        
        print(f"\n{'='*60}")
        print(f"📊 REGRADING SUMMARY")
        print(f"{'='*60}")
        print(f"Total: {len(results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"{'='*60}\n")
        
        return {
            "exam_id": exam_id,
            "total_uploads": len(results),
            "successful": successful,
            "failed": failed,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Regrade all failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exam/{exam_id}/grading-status")
async def get_exam_grading_status(exam_id: str):
    """Get detailed grading status for an exam"""
    supabase_admin = get_supabase_admin()
    
    try:
        # Get uploads
        uploads = supabase_admin.table("exam_uploads").select("""
            id,
            student_id,
            processing_status,
            ocr_extracted_text,
            students (student_id, full_name)
        """).eq("exam_id", exam_id).execute()
        
        status_summary = []
        
        for upload in uploads.data:
            student = supabase_admin.table("students").select("full_name").eq(
        "id", upload["student_id"]
    ).maybe_single().execute()
            
            status_summary.append({
        "upload_id": upload["id"],
        "student_id": upload["student_id"],
        "student_name": student.data["full_name"] if student.data else None,
        "processing_status": upload["processing_status"],
        "has_ocr_text": len(upload.get("ocr_extracted_text", "")) > 0,
        "student_answers_count": len(
            supabase_admin.table("student_answers")
            .select("id")
            .eq("upload_id", upload["id"])
            .execute().data
        ),
        "grading_results_count": len(
            supabase_admin.table("grading_results")
            .select("id")
            .eq("exam_id", exam_id)
            .eq("student_id", upload["student_id"])
            .execute().data
        ),
        "is_graded": len(
            supabase_admin.table("grading_results")
            .select("id")
            .eq("exam_id", exam_id)
            .eq("student_id", upload["student_id"])
            .execute().data
        ) > 0
            
            })
        
        return {
            "exam_id": exam_id,
            "total_uploads": len(status_summary),
            "uploads": status_summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))