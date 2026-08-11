# Mateja Plazinic 2022/0335
from geopy.geocoders import Nominatim
from math import radians, cos, sin, asin, sqrt

def adresa_u_koordinate(adresa):
    geolocator = Nominatim(user_agent="projekat_doktori")
    lokacija = geolocator.geocode(adresa)
    if lokacija:
        return lokacija.latitude, lokacija.longitude
    return None, None

def haversine(lat1, lon1, lat2, lon2):
    """
    Računa udaljenost između dve geografske tačke (km)
    """
    # Pretvori stepene u radijane
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # poluprečnik Zemlje u km
    return c * r