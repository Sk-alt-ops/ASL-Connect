"""
URL Configuration -- Admin Dashboard
======================================
Maps API endpoints for the admin panel to their corresponding view
functions.

Each group covers a functional area:

  - Dashboard           statistics / recent activity
  - Users               list + search
  - Contact Messages    inbox, reply, mark-read
  - Support Tickets     list, respond, status update
  - Design Settings     global design singleton CRUD
  - Page Design         per-page design CRUD
  - Section Design      per-section landing-page design CRUD
  - File Upload         section image/video upload
"""

from django.urls import path

from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    # -------------------------------------------------------------------
    # Admin Panel Main View
    # -------------------------------------------------------------------
    path('', views.admin_panel, name='admin_panel'),

    # -------------------------------------------------------------------
    # Dashboard APIs
    # -------------------------------------------------------------------
    path('api/dashboard/stats/', views.dashboard_stats,
         name='dashboard_stats'),
    path('api/dashboard/recent-activity/', views.dashboard_recent_activity,
         name='dashboard_recent_activity'),

    # -------------------------------------------------------------------
    # User Management APIs
    # -------------------------------------------------------------------
    path('api/users/', views.users_list, name='users_list'),
    path('api/users/<int:user_id>/', views.user_detail, name='user_detail'),

    # -------------------------------------------------------------------
    # Contact Message APIs
    # -------------------------------------------------------------------
    path('api/contact-messages/', views.contact_messages_list,
         name='contact_messages_list'),
    path('api/contact-messages/<int:message_id>/reply/',
         views.contact_message_reply, name='contact_message_reply'),
    path('api/contact-messages/<int:message_id>/mark-read/',
         views.contact_message_mark_read, name='contact_message_mark_read'),

    # -------------------------------------------------------------------
    # Support Ticket APIs
    # -------------------------------------------------------------------
    path('api/support-tickets/', views.support_tickets_list,
         name='support_tickets_list'),
    path('api/support-tickets/<int:ticket_id>/respond/',
         views.support_ticket_respond, name='support_ticket_respond'),
    path('api/support-tickets/<int:ticket_id>/status/',
         views.support_ticket_status, name='support_ticket_status'),

    # -------------------------------------------------------------------
    # Design Settings APIs (global singleton)
    # -------------------------------------------------------------------
    path('api/design-settings/', views.design_settings_get,
         name='design_settings_get'),
    path('api/design-settings/update/', views.design_settings_update,
         name='design_settings_update'),

    # -------------------------------------------------------------------
    # Page Design APIs (per-page overrides)
    # -------------------------------------------------------------------
    path('api/page-design/', views.page_design_list,
         name='page_design_list'),
    path('api/page-design/<str:page_name>/', views.page_design_get,
         name='page_design_get'),
    path('api/page-design/<str:page_name>/save/', views.page_design_save,
         name='page_design_save'),
    path('api/page-design/<str:page_name>/publish/',
         views.page_design_publish, name='page_design_publish'),
    path('api/page-design/<str:page_name>/reset/', views.page_design_reset,
         name='page_design_reset'),

    # -------------------------------------------------------------------
    # Section Design APIs (per-section overrides for landing page)
    # -------------------------------------------------------------------
    path('api/section-design/', views.section_design_list,
         name='section_design_list'),
    path('api/section-design/<str:section_name>/', views.section_design_get,
         name='section_design_get'),
    path('api/section-design/<str:section_name>/save/',
         views.section_design_save, name='section_design_save'),
    path('api/section-design/<str:section_name>/reset/',
         views.section_design_reset, name='section_design_reset'),
    path('api/section-design/upload/', views.section_upload_file,
         name='section_upload_file'),
]
