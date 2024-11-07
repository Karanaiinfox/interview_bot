from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Candidate, JobPosting, BotJobCandidateQuestion,InterviewSchedule,Resume
from questions.ques_framework import *
import os
import threading
from werkzeug.utils import secure_filename
from django.conf import settings
from .utils import log_function_call
from django.utils.deprecation import MiddlewareMixin
import uuid 
import boto3
from decouple import config
import logging
from io import BytesIO
from PyPDF2.errors import PdfReadError
import base64
import PyPDF2

logger = logging.getLogger(__name__)
sqs = boto3.client(
    'sqs',
    aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY'),
    region_name=config('AWS_REGION', 'us-east-1')  
)
class CorrelationIdMiddleware(MiddlewareMixin):
    def process_request(self, request):
        try:
            request.correlation_id = str(uuid.uuid4())
            logger.info(f"Generated Correlation ID: {request.correlation_id} for request path: {request.path}")
        except Exception as e:
            logger.exception("Error generating Correlation ID.")
            request.correlation_id = None  # Fallback in case of error

    def process_response(self, request, response):
        try:
            response['X-Correlation-ID'] = request.correlation_id
            logger.info(f"Added Correlation ID: {request.correlation_id} to response for request path: {request.path}")
        except Exception as e:
            logger.exception("Error adding Correlation ID to response.")
        return response




class QuestionsView(APIView):
    permission_classes = [AllowAny]
    @log_function_call
    def extract_text_from_blob(self, pdf_data):
        if isinstance(pdf_data, str):
            pdf_bytes = base64.b64decode(pdf_data)
        else:
            pdf_bytes = pdf_data
        temp_pdf_path = 'temp_file.pdf'
        with open(temp_pdf_path, 'wb') as f:
            f.write(pdf_bytes)
        with open(temp_pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            
            for page in pdf_reader.pages:
                text += page.extract_text() if page.extract_text() else ''
                
        return text

    @log_function_call 
    def post(self, request):
        try:
            logger.info("Received POST request to generate questions.")
            schedule_id = request.data.get('schedule_id')

            result = self.generate_questions_helper(schedule_id)
            return JsonResponse(result, status=201)

        except Exception as e:
            logger.exception("Error occurred while processing POST request.")
            return JsonResponse({'error': 'An error occurred while generating the questions.'}, status=500)
    @log_function_call 
    def generate_questions_helper(self,schedule_id):
        try:
            logger.info("Generating questions.")
            # Fetch necessary objects
            vector_db = connect_to_vectorDB("interview_questions")
            schedule = get_object_or_404(InterviewSchedule, pk=schedule_id)
            candidate = schedule.candidate
            job = schedule.job
            resume=schedule.resume
            job_id = job.id
            candidate_id = candidate.id
            resume_id = resume.id
            if not job_id:
                return JsonResponse({'error': 'Job ID is required'}, status=400)

            if not candidate_id:
                return JsonResponse({'error': 'Candidate ID is required'}, status=400)

            job = get_object_or_404(JobPosting, pk=job_id)
            candidate = get_object_or_404(Candidate, pk=candidate_id)
            resume=get_object_or_404(Resume,pk=resume_id)

            job_description = job.job_description
            job_title = job.job_header
            
            if not resume:
                return JsonResponse({'error': 'No active resume found for candidate'}, status=404)

            if resume.type == 'application/pdf':
                resume_text = self.extract_text_from_blob(resume.content)  # Assuming `content` field stores BLOB
                if resume_text is None:
                    return JsonResponse({'error': 'Failed to extract text from resume PDF BLOB'}, status=500)
        
            # Start question generation process
            threading.Thread(target=self.generate_questions, args=(candidate, job, job_title, resume_text, job_description, schedule, vector_db)).start()
            return {'message': 'Questions are being generated', 'job_id': job.id, 'candidate_id': candidate.id, 'schedule': schedule.id}
        
        except Exception as e:
            logger.exception("Error generating questions.")
            return {'error': 'An error occurred while generating questions'}
    @log_function_call 
    def generate_questions(self, candidate, job, job_title, resume_text, job_description, schedule, vector_db):
        try:
            logger.info(f"Starting question generation for Candidate ID: {candidate.id}, Job Title: {job_title}")
            # resume_filename = secure_filename(resume_file.name)
            # resume_filename = os.path.splitext(resume_filename)[0]
            # resume_text = extract_text_from_file(resume_file)
            resume_skills = extract_skills(resume_text)
            experience = cal_experience(resume_text)
            job_skills = extract_skills(job_description)
            matched_skills = match_skills(resume_skills, job_skills)
            if not matched_skills:
                matched_skills = normalize_skills(job_skills)
            logger.info(f"Matched skills for Candidate ID: {candidate.id}: {matched_skills}")
            all_questions = []
            questions = []

            def process_skill(skill):
                try:
                    nonlocal questions, all_questions
                    questions_data = generate_interview_questions([skill],matched_skills,experience, num_questions=5, vector_db=vector_db)
                    for question_text in questions_data.get(skill, []):
                        # Save each question into BotJobCandidateQuestion model
                        answer=generate_answers(question_text)
                        question_entry = BotJobCandidateQuestion.objects.create(
                            tenant=candidate.tenant,  # assuming tenant is a shared field between Candidate and JobPosting
                            job=job,
                            candidate=candidate,
                            schedule=schedule,
                            bot_question_source=1,  
                            question=question_text,
                            active=1,
                            deleted=0,
                            updated_by=1,  
                        )
                        questions.append(question_text)
                        all_questions.append(question_entry.question)
                        logger.info(f"Processed skill {skill} for Candidate ID: {candidate.id} question:{question_text}")

                except Exception as e:
                    logger.exception(f"Error processing skill {skill} for Candidate ID: {candidate.id}")
            threads = []

            # Create threads for each skill to process them concurrently
            for skill in matched_skills:
                thread = threading.Thread(target=process_skill, args=(skill,))
                threads.append(thread)
                thread.start()

            # Wait for all threads to finish
            for thread in threads:
                thread.join()

            if questions:
                save_questions_to_vectorDB(questions)
                vector_db.persist()

            return all_questions
        except Exception as e:
            logger.exception(f"Error occurred during question generation for Candidate ID: {candidate.id}")


