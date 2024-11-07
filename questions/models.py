from django.db import models


class Tenant(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    address_line_1 = models.CharField(max_length=255, blank=True, null=True)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    zip = models.CharField(max_length=255, blank=True, null=True)
    timezone = models.CharField(max_length=255, blank=True, null=True)
    created_date = models.DateTimeField()
    last_updated_date = models.DateTimeField()
    updated_by = models.IntegerField()
    primary_contact_phone = models.CharField(max_length=255, blank=True, null=True)
    primary_contact_email = models.CharField(max_length=255, blank=True, null=True)
    active = models.IntegerField()
    deleted = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'tenant'

class BotJobCandidateQuestion(models.Model):
    tenant = models.ForeignKey('Tenant', models.DO_NOTHING)
    job = models.ForeignKey('JobPosting', models.DO_NOTHING)
    candidate = models.ForeignKey('Candidate', models.DO_NOTHING, blank=True, null=True)
    bot_question_source = models.IntegerField()
    question = models.TextField()
    active = models.IntegerField()
    deleted = models.IntegerField()
    created_date = models.DateTimeField(blank=True, null=True)
    last_updated_date = models.DateTimeField(auto_now=True)
    updated_by = models.IntegerField()
    schedule=models.ForeignKey('InterviewSchedule', models.DO_NOTHING)
    class Meta:
        managed = False
        db_table = 'bot_job_candidate_question'


class Candidate(models.Model):
    tenant = models.ForeignKey('Tenant', models.DO_NOTHING)
    candidate_email = models.CharField(max_length=255)
    candidate_phone = models.CharField(max_length=255, blank=True, null=True)
    preferred_timezone = models.CharField(max_length=255, blank=True, null=True)
    resume_s3_path = models.CharField(max_length=255, blank=True, null=True)
    active = models.IntegerField()
    deleted = models.IntegerField()
    created_date = models.DateTimeField(blank=True, null=True)
    last_updated_date = models.DateTimeField()
    updated_by = models.IntegerField()
    tenant_user_id = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'candidate'
        unique_together = (('candidate_email', 'tenant'),)

class InterviewSchedule(models.Model):
    tenant = models.ForeignKey('Tenant', models.DO_NOTHING)
    job = models.ForeignKey('JobPosting', models.DO_NOTHING)
    candidate = models.ForeignKey(Candidate, models.DO_NOTHING)
    schedule_start_date = models.DateTimeField(blank=True, null=True)
    interview_period_minutes = models.IntegerField()
    schedule_status_id = models.IntegerField()
    active = models.IntegerField()
    deleted = models.IntegerField()
    created_date = models.DateTimeField(blank=True, null=True)
    last_updated_date = models.DateTimeField()
    updated_by = models.IntegerField()
    # resume = models.ForeignKey('Resume', models.DO_NOTHING, blank=True, null=True)
    resume = models.ForeignKey('Resume', models.DO_NOTHING, blank=True, null=True, related_name='interview_schedules')

    class Meta:
        managed = False
        db_table = 'interview_schedule'

class JobPosting(models.Model):
    tenant = models.ForeignKey('Tenant', models.DO_NOTHING)
    job_header = models.CharField(max_length=255, blank=True, null=True)
    job_description = models.CharField(max_length=255, blank=True, null=True)
    jd_s3_path = models.CharField(max_length=255, blank=True, null=True)
    job_interview_period_in_minutes = models.IntegerField()
    active = models.IntegerField()
    deleted = models.IntegerField()
    created_date = models.DateTimeField(blank=True, null=True)
    last_updated_date = models.DateTimeField()
    updated_by = models.IntegerField()
    job_location = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'job_posting'



class Resume(models.Model):
    id = models.BigAutoField(primary_key=True)
    active = models.IntegerField()
    content = models.TextField(blank=True, null=True)
    deleted = models.IntegerField()
    name = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    candidate = models.ForeignKey(Candidate, models.DO_NOTHING, blank=True, null=True)
    created_date = models.DateTimeField(blank=True, null=True)
    last_updated_date = models.DateTimeField(blank=True, null=True)
    updated_by = models.IntegerField(blank=True, null=True)
    
    class Meta:
        managed = False
        db_table = 'resume'
 