from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from pgvector.django import VectorField, HnswIndex
import uuid

class Organisation(models.Model):
    organisation_name = models.CharField(max_length=255)
    subscription_tier = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.organisation_name


class User(models.Model):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name="users"
    )

    manager = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    salesperson_name = models.CharField(max_length=255)

    email = models.EmailField(unique=True)

    password_hash = models.TextField()

    role = models.CharField(max_length=50)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.salesperson_name


class Customer(models.Model):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name="customers"
    )

    salesperson = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="customers"
    )

    customer_name = models.CharField(max_length=255)

    email = models.EmailField(unique=True, null= True, blank=True) # Remove he null = true an blank = true in production

    industry = models.CharField(
        max_length=150,
        blank=True
    )

    website = models.URLField(
        blank=True
    )

    status = models.CharField(
        max_length=100,
        blank=True
    )

    extra_info = models.TextField(
        blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=["salesperson"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["customer_name"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["organisation", "customer_name"], name="unique_org_customer_name")
        ]

    def __str__(self):
        return self.customer_name


class Meeting(models.Model):

    class Status(models.TextChoices):
        UPLOADED = "uploaded"
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE
    )

    salesperson = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    meeting_date = models.DateTimeField()

    duration = models.DurationField()

    title = models.TextField()

    meeting_type = models.CharField(
        max_length=100
    )

    url = models.URLField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADED,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["customer"]),
            models.Index(fields=["salesperson"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["meeting_date"]),
            models.Index(fields=["meeting_type"]),
            models.Index(fields=["customer", "-meeting_date"]), 
        ]


class TranscriptReport(models.Model):
    meeting = models.OneToOneField(
        Meeting,
        on_delete=models.CASCADE,
        related_name="transcript_report"
    )

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE
    )

    transcript = models.TextField()

    summary = models.TextField()

    merged_final_report = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)


class MeetingAnalysis(models.Model):
    meeting = models.OneToOneField(
        Meeting,
        on_delete=models.CASCADE,
        related_name="analysis"
    )

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE
    )

    agent_1_report_persistent = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
        ]


class MeetingReport(models.Model):
    meeting = models.OneToOneField(
        Meeting,
        on_delete=models.CASCADE,
        related_name="html_report"
    )

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE
    )

    salesperson = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    html_report = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
        ]


class Embedding(models.Model):
    transcript_report = models.ForeignKey(
        TranscriptReport,
        on_delete=models.CASCADE,
        related_name="embeddings"
    )

    chunks = models.TextField()

    vector = VectorField(dimensions=1024)  

    metadata = models.JSONField(default=dict)

    chunk_search = SearchVectorField(null=True) # this is for keyword search

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            HnswIndex(
                name="embed_vector_idx",
                fields=["vector"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"]
            ),
            GinIndex(fields=["chunk_search"]),
        ]

class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    salesperson = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class ChatTurn(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="turns")
    
    query = models.TextField()
    answer = models.TextField()
    
    query_vector = VectorField(dimensions=1024, null=True, blank=True) 
    query_search = SearchVectorField(null=True, blank=True) 
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            HnswIndex(name='chat_query_vector_idx', fields=['query_vector'], opclasses=['vector_cosine_ops']),
            GinIndex(fields=['query_search'], name='chat_query_gin_idx'),
        ]