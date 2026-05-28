from django.contrib import admin
from .models import Trainer, Batch

class BatchInline(admin.TabularInline):
    model = Batch
    extra = 1

@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = ('name', 'course', 'branch')
    list_filter = ('branch', 'course')
    search_fields = ('name', 'course', 'branch')
    inlines = [BatchInline]
    class Media:
        css = {
            'all': ('css/admin_filters.css', 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css')
        }
        js = ('js/admin_filters.js',)

from django import forms
from django.utils.safestring import mark_safe

class DatalistWidget(forms.TextInput):
    def __init__(self, datalist, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.datalist = datalist
        self.name = name

    def render(self, name, value, attrs=None, renderer=None):
        attrs['list'] = self.name
        html = super().render(name, value, attrs, renderer)
        datalist_html = f'<datalist id="{self.name}">'
        for item in self.datalist:
            datalist_html += f'<option value="{item}">'
        datalist_html += '</datalist>'
        return mark_safe(html + datalist_html)

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('trainer', 'batch_name', 'batch_type', 'timing', 'start_date', 'end_date')
    list_filter = ('batch_type', 'month', 'year')
    search_fields = ('trainer__name',)
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'batch_name':
            choices = [c[0] for c in Batch.BATCH_NAMES]
            kwargs['widget'] = DatalistWidget(datalist=choices, name='batch_name_list')
        return super().formfield_for_dbfield(db_field, request, **kwargs)
    class Media:
        css = {
            'all': ('css/admin_filters.css', 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css')
        }
        js = ('js/admin_filters.js',)
