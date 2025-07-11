from haystack import component
import requests
import re

@component
class LocationRetriever:
    def __init__(self, api_key):
        self.api_key = api_key

    def _get_location_from_coordinates(self, latitude, longitude):
        """
        Get human-readable location description using OpenStreetMap Nominatim API.
        """
        try:
            url = 'https://nominatim.openstreetmap.org/reverse'
            params = {
                'lat': latitude,
                'lon': longitude,
                'format': 'json',
                'zoom': 18,
                'addressdetails': 1,
                'accept-language': 'en',
            }
            
            response = requests.get(url, params=params, headers={'User-Agent': 'PerceptoAI Location Service'})
            if response.status_code != 200:
                return 'Location description unavailable'
            
            data = response.json()
            components = {
                'location_name': data.get('display_name'),
                'city': data['address'].get('city'),
                'state': data['address'].get('state'),
                'neighbourhood': data['address'].get('neighbourhood'),
                'road': data['address'].get('road'),
                'postcode': data['address'].get('postcode'),
                'country': data['address'].get('country')
            }

            return components or 'Location unavailable'
        
        except Exception as e:
            print(f"Error getting location description: {e}")
            return 'Location description unavailable'
    
    def get_user_location(self):
        """
        Determine location using Google Maps Geocoding API.
        """    
        try:
            url = f'https://www.googleapis.com/geolocation/v1/geolocate?key={self.api_key}'
            response = requests.post(url)
            
            
            if response.status_code != 200:
                print(f'Google Geolocation error: Received status code {response.status_code}')
                return None
            
            res = response.json()
            coords = res.get('location', {})
            latitude = str(coords.get('lat'))
            longitude = str(coords.get('lng'))

            location_data = self._get_location_from_coordinates(latitude, longitude) if latitude and longitude else 'Location description unavailable'
            # location_data {'location_name': 'TPL GOLF, Street 1, IVORYHILL, Sheikh Zayed, Giza, 12573, Egypt', 'city': 'Sheikh Zayed', 'state': 'Giza', 'neighbourhood': 'IVORYHILL', 'road': 'Street 1', 'postcode': '12573', 'country': 'Egypt'}
                
            return location_data['location_name']
        
        except Exception as e:
            print(f"Error determining location: {e}")
            return None

    @component.output_types(user_location=dict)
    def run(self, query: str = None) -> dict:
        location = self.get_user_location()
        return {"content": f"Based on your location, you are at {location}."}

@component
class DateTimeRetriever:
    def __init__(self, api_key: str):
        self.api_key = api_key

    @component.output_types(datetime=dict)
    def run(self, query: str) -> dict:
        match = re.search(r"(?:date|time).*?(?:in|at|for)\s+([a-zA-Z\s]+)", query, re.IGNORECASE)
        extracted = match.group(1).strip() if match else ""

        filler_terms = {"time", "date", "today", "now", "it", "is", "this", ""}
        if extracted.lower() in filler_terms:
            location = "Cairo" 
        else:
            location = extracted.title() 

        url = f"http://api.weatherapi.com/v1/timezone.json?key={self.api_key}&q={location}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            location_name = data['location']['name']
            country = data['location']['country']
            localtime = data['location']['localtime']

            date_part, time_part = localtime.split()
            include_date = "date" in query.lower()
            include_time = "time" in query.lower()

            if not include_date and not include_time:
                include_date = include_time = True

            parts = []
            if include_date:
                parts.append(f"the date is {date_part}")
            if include_time:
                parts.append(f"the time is {time_part}")

            joined = " and ".join(parts)
            content = f"In {location_name}, {country}, {joined}."

            result = {'content': content, 'url': "https://www.weatherapi.com/"}
        else:
            result = {'content': "Sorry, I couldn't retrieve the time.", 'url': ""}

        return result

@component
class WeatherRetriever:
    def __init__(self, api_key: str):
        self.api_key = api_key

    @component.output_types(weather=dict)
    def run(self, query: str) -> dict:
        location_patterns = [
            r"(?:in|at|for)\s+([a-zA-Z\s]+)", 
        ]
        
        location = None
        for pattern in location_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                if len(extracted) > 2 and extracted.lower() not in ["it", "is", "today", "now"]:
                    location = extracted.title()
                    break

        if not location:
            try:
                ip_data = requests.get("http://ip-api.com/json/").json()
                location = ip_data.get("city", "Cairo")
            except:
                location = "Cairo"  

        url = f"http://api.weatherapi.com/v1/current.json?key={self.api_key}&q={location}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            location_name = data['location']['name']
            country = data['location']['country']
            condition = data['current']['condition']['text']
            temp_c = data['current']['temp_c']
            humidity = data['current']['humidity']
            wind_kph = data['current']['wind_kph']

            content = (
                f"The current weather in {location_name}, {country} is {condition} "
                f"with a temperature of {temp_c}°C, humidity at {humidity}%, "
                f"and wind speed of {wind_kph} kph."
            )
            result = {'content': content, 'url': "https://www.weatherapi.com/"}
        else:
            result = {'content': "I'm sorry, I couldn't retrieve the weather right now.", 'url': ""}

        return result

@component
class SerpAPIWebSearch:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def truncate_text(self, text: str) -> str:
        """Truncate the text after the second period."""
        periods = text.split('.')
        if len(periods) > 2:
            return '.'.join(periods[:2]) + '.'
        return text

    @component.output_types(web_documents=dict)
    def run(self, query: str) -> dict:
        print("Searching the web..")
        search_url = f"https://serpapi.com/search?q={query}&api_key={self.api_key}"
        response = requests.get(search_url)
        documents = {}

        if response.status_code == 200:
            search_results = response.json()
            top_results = search_results.get('organic_results', [])[:3]
            merged_snippet = ' '.join([
                self.truncate_text(result.get('snippet', '')) 
                for result in top_results
            ])
            links = [result.get('link', '') for result in top_results]
            documents['content'] = "I have searched the web and found the following: " + merged_snippet
            documents['url'] = ', '.join(links)
        else:
            documents['content'] = "I couldn't find any relevant information through web search."
            documents['url'] = ""

        return {"web_documents": documents}