"""Names for points at sea.

Reverse geocoding returns a Plus Code and no country over water, so a clicked
point in the ocean has no name to show. These bounding boxes supply one.

They are deliberately coarse: a box is a rectangle and a sea is not, so a point
near a boundary can take its neighbour's name. That is accepted — naming the
Mediterranean "Mediterranean Sea" is worth more than naming it "Atlantic Ocean",
which is what an ocean-only fallback would do. Order matters: enclosed seas are
matched before the oceans that contain them.
"""

# (name, lat_min, lat_max, lng_min, lng_max)
SEAS = (
    # The Black Sea sits inside the Mediterranean's box, so it is matched first.
    ("Black Sea", 40.0, 47.5, 27.0, 42.0),
    ("Mediterranean Sea", 30.0, 46.0, -6.0, 36.5),
    ("Red Sea", 12.0, 30.0, 32.0, 44.0),
    ("Persian Gulf", 23.0, 30.5, 47.5, 57.0),
    ("Andaman Sea", 5.0, 17.0, 92.0, 99.0),
    ("Bay of Bengal", 5.0, 23.0, 78.0, 95.0),
    ("Arabian Sea", 0.0, 25.0, 51.0, 78.0),
    ("South China Sea", 0.0, 23.5, 104.0, 121.0),
    ("East China Sea", 24.0, 33.5, 120.0, 131.0),
    ("Sea of Japan", 33.0, 52.0, 127.0, 142.0),
    ("Philippine Sea", 5.0, 25.0, 121.0, 135.0),
    ("Coral Sea", -24.0, -10.0, 145.0, 165.0),
    ("Tasman Sea", -45.0, -30.0, 150.0, 175.0),
    ("Caribbean Sea", 9.0, 22.0, -88.0, -60.0),
    ("Gulf of Mexico", 18.0, 31.0, -98.0, -80.0),
    ("North Sea", 51.0, 61.5, -4.0, 9.0),
    ("Baltic Sea", 53.0, 66.0, 9.0, 30.0),
    ("Hudson Bay", 51.0, 64.0, -95.0, -75.0),
    ("Gulf of Guinea", -5.0, 5.5, -5.0, 10.0),
)
UNKNOWN_WATER = "Open water"


def name_water_body(latitude: float, longitude: float) -> str:
    """Name the sea or ocean containing a point."""
    for name, lat_min, lat_max, lng_min, lng_max in SEAS:
        if lat_min <= latitude <= lat_max and lng_min <= longitude <= lng_max:
            return name

    if latitude <= -60.0:
        return "Southern Ocean"
    if latitude >= 66.5:
        return "Arctic Ocean"
    # The Pacific spans the date line, so it is the two outer longitude bands.
    if longitude >= 147.0 or longitude <= -70.0:
        return "Pacific Ocean"
    if 20.0 <= longitude < 147.0 and latitude <= 30.0:
        return "Indian Ocean"
    if -70.0 < longitude < 20.0:
        return "Atlantic Ocean"
    return UNKNOWN_WATER
