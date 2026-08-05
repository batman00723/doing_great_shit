from django.contrib import admin
from .models import (
    Organisation,
    User,
    Customer,
    Meeting,
    TranscriptReport,
    MeetingAnalysis,
    MeetingReport,
    Embedding,
)

admin.site.register(Organisation)
admin.site.register(User)
admin.site.register(Customer)
admin.site.register(Meeting)
admin.site.register(TranscriptReport)
admin.site.register(MeetingAnalysis)
admin.site.register(MeetingReport)
admin.site.register(Embedding)
