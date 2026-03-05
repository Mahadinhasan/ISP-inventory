from django.shortcuts import render
from isp_inventory.models import UserProfile

# Create your views here.
def noc_dashboard(request):
    return render(request, 'noc/dashboard.html')