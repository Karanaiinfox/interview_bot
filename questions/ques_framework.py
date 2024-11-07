import openai
import os
import fitz  # PyMuPDF
from fuzzywuzzy import process
import re
from django.core.files.uploadedfile import InMemoryUploadedFile
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from decouple import config
import logging
from docx import Document
import pandas as pd
from questions.llm_model import *
import tiktoken
logger = logging.getLogger(__name__)

OPENAI_API_KEY = config('OPENAI_API_KEY')
emb_model=config('emb_model')

max_tokens=config('max_tokens')
temperature=config('temperature')
top_p=config("top_p")
frequency_penalty=config('frequency_penalty')
presence_penalty=config('presence_penalty')

openai.api_key = OPENAI_API_KEY
 
summary_dir='summary_files'
resume_dir='resume_summary'
if not os.path.exists(summary_dir):
        os.makedirs(summary_dir)
 
if not os.path.exists(resume_dir):
        os.makedirs(resume_dir)
 
embeddings = HuggingFaceEmbeddings(model_name=emb_model)
 
persist_directory =  'chroma_db_files/'




def excel_to_vectorDB(subject,questions):
    try:
        db = Chroma.from_texts(collection_name=f"{subject}",
                                texts=questions,
                                embedding=embeddings,
                                persist_directory=persist_directory)
    
        return db
    except Exception as e:
            logger.exception("Error creating vector DB.")
            return None
 
 
def connect_to_vectorDB(subject):
    try:
        vector_db = Chroma(collection_name=f"{subject}", persist_directory=persist_directory, embedding_function=embeddings)
        logger.info(f"Connected to vector DB for subject: {subject}")
        return vector_db
    except Exception as e:
        logger.exception("Error connecting to vector DB.")
        return None

 
def save_questions_to_vectorDB(questions,subject="interview_questions"):
    try:
        vector_db = excel_to_vectorDB(subject, questions)
        if vector_db:
            logger.info("Questions added successfully to vector DB.")
        else:
            logger.error("Failed to add questions to vector DB.")
    except Exception as e:
        logger.exception("Error while saving questions to vector DB")
 
def extract_text_from_file(uploaded_file):
    try:
     
            
        pdf = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        for page in pdf:
            text += page.get_text()

        return text

    except Exception as e:
        logger.exception("Error extracting text from file.")
        return str(e)

 

 
def summarize_resume(resume_text,resume_filename):
    try:
        prompt = f"Summarize the resume:\n\n{resume_text}"
        response = call_openai_api(prompt,max_tokens,temperature,top_p,frequency_penalty,presence_penalty)
        summary = response.choices[0].message['content']
        calculate_token_cost(prompt,summary)
        resume_filename = f"{resume_dir}/{resume_filename}_history.txt"
        with open(resume_filename, 'w') as file:
                file.write(summary)
        logger.info(f"Resume summarized and saved to {resume_filename}")
    except Exception as e:
        logger.exception("Error summarizing resume.")
    
 
def cal_experience(resume_text):
    try:
        prompt = f"calculate the total years of experience from the resume and categorize it (Junior, Mid-level, Senior). Assume current month April and year 2024.\n\n{resume_text}"
        response = call_openai_api(prompt,max_tokens,temperature,top_p,frequency_penalty,presence_penalty)
        experience = response.choices[0].message['content'].strip()
        calculate_token_cost(prompt,experience)

        return experience
    except Exception as e:
        logger.exception("Error calculating experience.")
        return None
 
def extract_skills(text):
    try:
        prompt = f"Extract all the skills that the  text have :\n\n{text}"
        response = call_openai_api(prompt,max_tokens,temperature,top_p,frequency_penalty,presence_penalty)
        extracted_skills = response.choices[0].message['content'].split('\n')
        calculate_token_cost(prompt,extracted_skills)

        skills = [skill.strip().lower() for skill in extracted_skills if skill.strip()]
        return skills
    except Exception as e:
        logger.exception("Error extracting skills.")
        return []
 
def normalize_skills(skills):
    normalized_skills = set()
    for skill in skills:
        clean_skill = re.sub(r"^\W*\d*[-\.]\s*|\W*$", "", skill)
        if clean_skill and clean_skill.lower() not in ["the technical skills mentioned in the text are",
                                                       "the skills mentioned in the text are",
                                                       "the skills extracted from the text are"]:
            normalized_skills.add(clean_skill.lower())
    return normalized_skills
 
 
def match_skills(resume_skills, job_skills, threshold=80):
    try:
        matched_skills = []
        normalized_resume_skills = normalize_skills(resume_skills)
        normalized_job_skills = normalize_skills(job_skills)
    
        for skill in normalized_resume_skills:
            best_match, score = process.extractOne(skill, normalized_job_skills)
            if score >= threshold:
                matched_skills.append(best_match)
        matched_skills = set(matched_skills)
        matched_skills = list(matched_skills)
        logger.info(f"Skills matched: {matched_skills}")

        return matched_skills
    except Exception as e:
        logger.exception("Error matching skills.")
        return []
    
 

def generate_questions(skill, related_skills,experience_level,num_questions):
    try:
        basic_prompt = f"Generate 5 basic interview questions ."
        basic_response = call_openai_api(basic_prompt,max_tokens,temperature,top_p,frequency_penalty,presence_penalty)
        
        basic_questions = basic_response.choices[0].message['content'].strip().split('\n')
        calculate_token_cost(basic_prompt,basic_questions)

        basic_questions=[re.sub(r'^\d+\.', '', element.strip()) for element in basic_questions]
        basic_questions = [q.strip() for q in basic_questions if q and q.strip() != ""]
        if experience_level == 'Junior':
            difficulty = "basic"
        elif experience_level == 'Mid-level':
            difficulty = "intermediate"
        elif experience_level == 'Senior':
            difficulty = "advanced"
        else:
            difficulty = "basic"

        prompt = (f"Generate {num_questions} {difficulty} level technical interview questions  without any headings or titles "
                f"for the primary skill: {skill}. "
                f"Also consider related skills: {related_skills}. "
                f"Ensure that the questions are interrelated with  the primary skill {skill} "
                f"and the related skills: {related_skills}.")
        response = call_openai_api(prompt,config('max_tokens_genrated_que'),config('temperature_genrated_que'),config('top_p_genrated_que'),config('frequency_penalty_genrated_que'),config('presence_penalty_genrated_que'))
        questions = response.choices[0].message['content'].strip().split('\n')
        calculate_token_cost(prompt,questions)
        questions = [re.sub(r'^\d+\.', '', element.strip()) for element in questions]
    
        question1 = [q.strip() for q in questions if q and q.strip() != ""]
        all_questions = basic_questions + question1
        return all_questions
    except Exception as e:
        logger.exception(f"Error generating questions for skill: {skill}")
        return []

 
 

def generate_interview_questions(matched_skills,related_skill, experience_level, num_questions, vector_db=None):
    questions = {}
    existing_questions = set()
 
    if vector_db:
        if vector_db:
            try:
                vector_data = vector_db.get()  
                existing_questions = set(vector_data['documents'])  
            except Exception as e:
                logger.exception("Error fetching existing questions from vector DB.")

    for skill in matched_skills:
        skill_questions = []
        generated_questions = generate_questions(matched_skills, related_skill,experience_level,num_questions)
        
        for question in generated_questions:
            question1 = question.lower().strip()
            skill_questions.append(question)
            
 
        questions[skill] = skill_questions
    return questions
 
def delete_texts_from_vectorDB(subject, texts):
    try:
        vector_db = connect_to_vectorDB(subject)
        if not vector_db:
            return
        existing_data = vector_db.get()
        existing_texts = existing_data['documents']
        existing_ids = existing_data['ids']
    
        text_id_map = {text: doc_id for text, doc_id in zip(existing_texts, existing_ids)}
        ids_to_delete = [text_id_map[text] for text in texts if text in text_id_map]
    
        if ids_to_delete:
            vector_db.delete(ids=ids_to_delete)
            vector_db.persist()
            logger.info(f"Deleted texts from vector DB for subject: {subject}")
    except Exception as e:
        logger.exception("Error deleting texts from vector DB.")

    

 
def update_texts_in_vectorDB(subject, old_text, new_text):
    try:
        vector_db = connect_to_vectorDB(subject)
        if not vector_db:
            return {'success': False, 'error': 'Unable to connect to the database'}
    
    
        existing_data = vector_db.get()
        existing_texts = existing_data['documents']
        existing_ids = existing_data['ids']
        
        text_id_map = {text: doc_id for text, doc_id in zip(existing_texts, existing_ids)}
        index = text_id_map[old_text[0]]
        existing_texts[index] = new_text
        vector_db.delete(ids=index)
        vector_db.persist()
        vector_db.add_texts(texts=existing_texts, ids=existing_ids)
        vector_db.persist()
        logger.info(f"Updated text in vector DB for subject: {subject}")

        return {'success': True, 'message': 'Text updated successfully'}
    except Exception as e:
        logger.exception("Error updating text in vector DB.")
        return {'success': False, 'error': str(e)}
def generate_answers(questions):

    prompt = f"genrate a meaning full answer related to given {questions} "
    response = call_openai_api(prompt,max_tokens,temperature,top_p,frequency_penalty,presence_penalty)

    answer = response.choices[0].message['content'].strip()
    calculate_token_cost(prompt,answer)
    
    logger.info("Question: %s | Generated Answer: %s", questions, answer)

    return answer




