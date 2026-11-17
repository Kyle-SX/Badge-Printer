"""Badge types, assets, dimensions, and visual theme constants."""

from pathlib import Path


# Badge types and image assets
BADGE_TYPES = (
    "Contractor",
    "Visitor",
    "Casual Employee",
    "Temporary",
    "Employee",
)
SELECT_TYPE_PROMPT = "Select type"
BADGE_IMAGE_FILES = {
    "Contractor": "C (2).png",
    "Visitor": "V (2).png",
    "Casual Employee": "CE (2).png",
    "Temporary": "TE (2).png",
    }
EMPLOYEE_BADGE_TYPE = "Employee"
EMPLOYEE_LOGO_FILENAME = "GUD-holdings-logo.png"
EMPLOYEE_IMAGE_SIGNATURES = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
}

# Preview and print-sheet dimensions
BADGE_COUNT = 8
PREVIEW_SUBSAMPLE = 6
PREVIEW_WIDTH = 180
PREVIEW_HEIGHT = 116
ASSET_DIRECTORY = Path(__file__).resolve().parent.parent
GUD_YELLOW = "#f4c400"
GUD_ORANGE = "#ed7624"
GUD_RED = "#d94b35"
APP_BACKGROUND = "#fffaf0"
CARD_BACKGROUND = "#ffffff"
PREVIEW_BACKGROUND = "#fffdf7"
BRAND_PALE_YELLOW = "#fff3c4"
BRAND_HOVER_YELLOW = "#ffe6a0"
BRAND_BORDER = "#e8dcc1"
TEXT_PRIMARY = "#28231b"
TEXT_SECONDARY = "#70675a"
TEXT_ACCENT = "#62450a"
PAGE_WIDTH_MM = 217
PAGE_HEIGHT_MM = 279
BADGE_WIDTH_MM = 85
BADGE_HEIGHT_MM = 53
BADGE_STROKE_MM = 0.3
LEFT_MARGIN_MM = 17
RIGHT_MARGIN_MM = 20
TOP_MARGIN_MM = 16
BOTTOM_MARGIN_MM = 21
HORIZONTAL_GAP_MM = 10
VERTICAL_GAP_MM = 10
