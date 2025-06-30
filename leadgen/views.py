from django.shortcuts import render
from .utils.scraper import LeadInsightScraper
import re

def home_view(request):
    error = None
    if request.method == 'POST':
        url = request.POST.get('url')
        # Strict URL validation
        if not url or not re.match(r'^https?://.+', url):
            error = 'Please enter a valid URL starting with http:// or https://'
            return render(request, 'home.html', {'error': error, 'url': url})
        scraper = LeadInsightScraper(url)
        insights = scraper.run()
        return render(request, 'result.html', {'insights': insights, 'url': url})
    return render(request, 'home.html')
 