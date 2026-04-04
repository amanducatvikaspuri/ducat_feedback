from django.contrib import admin
from .models import Trainer, Batch

class BatchInline(admin.TabularInline):
    model = Batch
    extra = 1

@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = ('name', 'course')
    search_fields = ('name', 'course')
    inlines = [BatchInline]
    class Media:
        css = {
            'all': ('css/admin_filters.css', 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css')
        }
        js = ('js/admin_filters.js',)

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('trainer', 'batch_name', 'batch_type', 'timing', 'start_date', 'end_date')
    list_filter = ('batch_type', 'month', 'year')
    search_fields = ('trainer__name',)
    class Media:
        css = {
            'all': ('css/admin_filters.css', 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css')
        }
        js = ('js/admin_filters.js',)
